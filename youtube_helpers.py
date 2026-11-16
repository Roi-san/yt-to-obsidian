"""Tiny CLI used by the info_gatherer subagent: search YouTube, fetch a transcript, stage knowledge."""
import json
import re
import sys
from pathlib import Path


MAX_DURATION_SECONDS = 60 * 10  # seconds * minutes
MAX_TRANSCRIPT_CHARS = 50_000  # safety net for an override video that's much longer than expected
REASONING_KEYS = ("agreements", "disagreements", "remaining_questions", "unexpected_findings")

USAGE = """usage:
  python youtube_helpers.py search "<query>" [max-minutes]
  python youtube_helpers.py transcript <video-id>
  python youtube_helpers.py claims <staged-path>
  python youtube_helpers.py stage-knowledge <staged-path> "<topic>"   (knowledge JSON on stdin)
  python youtube_helpers.py finalize-reasoning <staged-path>          (reasoning JSON on stdin)"""


def search_videos(topic: str, n: int = 15, max_duration_seconds: int = MAX_DURATION_SECONDS) -> list[dict]:
    """n is deliberately generous: the duration cap usually throws most results away."""
    import yt_dlp  # imported here so the staging commands don't pay for it

    for _attempt in range(2):  # YouTube search occasionally comes back empty; one retry is enough
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
            result = ydl.extract_info(f"ytsearch{n}:{topic}", download=False)
        if result["entries"]:
            break
    return [
        {
            "id": e["id"],
            "title": e["title"],
            "url": f"https://youtube.com/watch?v={e['id']}",
            "channel": e.get("channel") or e.get("uploader") or "",
            "minutes": round(e["duration"] / 60, 1) if e.get("duration") else None,
        }
        for e in result["entries"]
        if not max_duration_seconds or (e.get("duration") or 0) <= max_duration_seconds
    ]


def get_transcript(video_id: str) -> str:
    """Fetch a transcript as plain text, chunked into ~30s blocks each prefixed with a [MM:SS]
    timestamp marker — lets whoever reads this cite an approximate source location per claim.
    Returns "" if there's no usable transcript; the reason goes to stderr."""
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        snippets = YouTubeTranscriptApi().fetch(video_id)
    except Exception as error:
        print(f"no transcript for {video_id}: {type(error).__name__}", file=sys.stderr)
        return ""

    chunks = []
    chunk_start = None
    chunk_texts = []
    for s in snippets:
        if chunk_start is None:
            chunk_start = s.start
        chunk_texts.append(s.text)
        if s.start - chunk_start >= 30:
            minutes, seconds = divmod(int(chunk_start), 60)
            chunks.append(f"[{minutes:02d}:{seconds:02d}] {' '.join(chunk_texts)}")
            chunk_start = None
            chunk_texts = []
    if chunk_texts:
        minutes, seconds = divmod(int(chunk_start), 60)
        chunks.append(f"[{minutes:02d}:{seconds:02d}] {' '.join(chunk_texts)}")

    text = "\n".join(chunks)
    if len(text) > MAX_TRANSCRIPT_CHARS:
        text = text[:MAX_TRANSCRIPT_CHARS] + "\n[transcript truncated — video longer than expected]"
    return text


def timestamp_link(url: str, time: str) -> str:
    """Turn a video url + "MM:SS" (or "H:MM:SS") into a link that opens the video at that moment.
    Falls back to the plain url if the timestamp isn't usable."""
    parts = time.strip().split(":")
    if not url or len(parts) > 3 or not all(p.isdigit() for p in parts):
        return url
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return f"{url}&t={seconds}s"


def _normalize(statement: str) -> str:
    """Two statements are "the same claim" if they match ignoring case, punctuation and spacing."""
    return re.sub(r"[^a-z0-9]+", " ", statement.lower()).strip()


def _append_new(target: list, items: list) -> None:
    for item in items:
        if item and item not in target:
            target.append(item)


def list_claims(gathered_path: str) -> list[str]:
    """The claim statements staged so far — so the next video's extraction can reuse the exact
    wording of a claim it restates, which is what lets the merge count corroboration."""
    path = Path(gathered_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    claims = data.get("observations", data).get("claims", [])
    return [c["statement"] for c in claims]


def stage_knowledge(gathered_path: str, topic: str, video_knowledge_json: str) -> dict:
    """Mechanically merge one video's already-extracted Layer 1 knowledge object into the running
    merged state. No judgment happens here — the agent already did the extracting; this just
    dedupes matching claims (adds to corroborated_by), builds a clickable link per timestamp, and
    persists."""
    video_obj = json.loads(video_knowledge_json)

    path = Path(gathered_path)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": 1, "topic": topic, "claims": [], "definitions": [], "examples": [], "videos": []}
    data.setdefault("open_questions", [])

    video = video_obj.get("video", {})
    video_url = video.get("url", "")
    if video_url not in [v["url"] for v in data["videos"]]:
        data["videos"].append({"title": video.get("title", ""), "url": video_url})

    for claim in video_obj.get("claims", []):
        statement = claim.get("statement", "").strip()
        if not statement:
            continue
        existing = next(
            (c for c in data["claims"] if _normalize(c["statement"]) == _normalize(statement)),
            None,
        )
        time = claim.get("timestamp", "")
        timestamp_entry = {"url": video_url, "time": time, "link": timestamp_link(video_url, time)}
        if existing:
            if video_url not in existing["corroborated_by"]:
                existing["corroborated_by"].append(video_url)
            if timestamp_entry not in existing["timestamps"]:
                existing["timestamps"].append(timestamp_entry)
        else:
            data["claims"].append({
                "statement": statement,
                "stated_as": claim.get("stated_as", "explicit"),
                "corroborated_by": [video_url],
                "timestamps": [timestamp_entry],
            })

    _append_new(data["definitions"], video_obj.get("definitions", []))
    _append_new(data["examples"], video_obj.get("examples", []))
    _append_new(data["open_questions"], video_obj.get("open_questions", []))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "status": "staged",
        "video_count": len(data["videos"]),
        "claim_count": len(data["claims"]),
        "corroborated_claims": sum(1 for c in data["claims"] if len(c["corroborated_by"]) > 1),
    }


def finalize_reasoning(gathered_path: str, reasoning_json: str) -> dict:
    """Mechanical wrap-up, called once after the agent's Reason phase is done and no more videos
    will be added: nests the merged Layer 1 state under "observations" and attaches the agent's
    Layer 2 reasoning object. No judgment happens here. Safe to call again with revised reasoning."""
    reasoning_obj = json.loads(reasoning_json)
    for key in REASONING_KEYS:
        reasoning_obj.setdefault(key, [])

    path = Path(gathered_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    if "observations" not in data:
        data["observations"] = {
            "claims": data.pop("claims"),
            "definitions": data.pop("definitions"),
            "examples": data.pop("examples"),
            "open_questions": data.pop("open_questions", []),
            "videos": data.pop("videos"),
        }
    data["reasoning"] = reasoning_obj

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "finalized", "video_count": len(data["observations"]["videos"])}


def _read_stdin() -> str:
    return sys.stdin.buffer.read().decode("utf-8")


def main(argv: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a codepage that chokes on transcripts
    if len(argv) < 3:
        sys.exit(USAGE)
    command = argv[1]
    if command == "search":
        max_seconds = int(argv[3]) * 60 if len(argv) > 3 else MAX_DURATION_SECONDS
        print(json.dumps(search_videos(argv[2], max_duration_seconds=max_seconds), ensure_ascii=False))
    elif command == "transcript":
        print(get_transcript(argv[2]))
    elif command == "claims":
        print(json.dumps(list_claims(argv[2]), ensure_ascii=False))
    elif command == "stage-knowledge" and len(argv) > 3:
        print(json.dumps(stage_knowledge(argv[2], argv[3], _read_stdin())))
    elif command == "finalize-reasoning":
        print(json.dumps(finalize_reasoning(argv[2], _read_stdin())))
    else:
        sys.exit(USAGE)


if __name__ == "__main__":
    main(sys.argv)
