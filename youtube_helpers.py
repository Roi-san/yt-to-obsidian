"""Tiny CLI used by the info_gatherer subagent: search YouTube, fetch a transcript, stage it."""
import json
import sys
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


MAX_DURATION_SECONDS = 60 * 10  # seconds * minutes
MAX_TRANSCRIPT_CHARS = 50_000  # safety net for an override video that's much longer than expected


def search_videos(topic: str, n: int = 8, max_duration_seconds: int = MAX_DURATION_SECONDS) -> list[dict]:
    with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
        result = ydl.extract_info(f"ytsearch{n}:{topic}", download=False)
    return [
        {"id": e["id"], "title": e["title"], "url": f"https://youtube.com/watch?v={e['id']}"}
        for e in result["entries"]
        if not max_duration_seconds or (e.get("duration") or 0) <= max_duration_seconds
    ]

def get_transcript(video_id: str) -> str:
    """Fetch a transcript as plain text, chunked into ~30s blocks each prefixed with a [MM:SS]
    timestamp marker — lets whoever reads this cite an approximate source location per claim."""
    try:
        snippets = YouTubeTranscriptApi().fetch(video_id)
    except Exception:
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


def stage_knowledge(gathered_path: str, topic: str, video_knowledge_json: str) -> dict:
    """Mechanically merge one video's already-extracted Layer 1 knowledge object into the running
    merged state. No judgment happens here — the agent already did the extracting; this just
    dedupes matching claims (adds to corroborated_by) and persists. Layer 1 only: claims,
    definitions, examples, videos. Per-video open_questions are not merged here — that's Phase C's
    concern, not this script's."""
    video_obj = json.loads(video_knowledge_json)

    path = Path(gathered_path)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": 1, "topic": topic, "claims": [], "definitions": [], "examples": [], "videos": []}

    video = video_obj.get("video", {})
    video_url = video.get("url", "")
    data["videos"].append({"title": video.get("title", ""), "url": video_url})

    for claim in video_obj.get("claims", []):
        statement = claim.get("statement", "")
        existing = next(
            (c for c in data["claims"] if c["statement"].strip().lower() == statement.strip().lower()),
            None,
        )
        timestamp_entry = {"url": video_url, "time": claim.get("timestamp", "")}
        if existing:
            if video_url not in existing["corroborated_by"]:
                existing["corroborated_by"].append(video_url)
            existing["timestamps"].append(timestamp_entry)
        else:
            data["claims"].append({
                "statement": statement,
                "stated_as": claim.get("stated_as", "explicit"),
                "corroborated_by": [video_url],
                "timestamps": [timestamp_entry],
            })

    for definition in video_obj.get("definitions", []):
        if definition not in data["definitions"]:
            data["definitions"].append(definition)

    for example in video_obj.get("examples", []):
        if example not in data["examples"]:
            data["examples"].append(example)

    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"status": "staged", "video_count": len(data["videos"]), "claim_count": len(data["claims"])}


def finalize_reasoning(gathered_path: str, reasoning_json: str) -> dict:
    """Mechanical wrap-up, called once after the agent's Reason phase is done and no more videos
    will be added: nests the merged Layer 1 state under "observations" and attaches the agent's
    Layer 2 reasoning object verbatim. No judgment happens here."""
    reasoning_obj = json.loads(reasoning_json)

    path = Path(gathered_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    data["observations"] = {
        "claims": data.pop("claims"),
        "definitions": data.pop("definitions"),
        "examples": data.pop("examples"),
        "videos": data.pop("videos"),
    }
    data["reasoning"] = reasoning_obj

    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"status": "finalized", "video_count": len(data["observations"]["videos"])}


if __name__ == "__main__":
    command, arg = sys.argv[1], sys.argv[2]
    if command == "search":
        max_minutes = int(sys.argv[3]) if len(sys.argv) > 3 else None
        max_seconds = max_minutes * 60 if max_minutes else MAX_DURATION_SECONDS
        print(json.dumps(search_videos(arg, max_duration_seconds=max_seconds)))
    elif command == "transcript":
        print(get_transcript(arg))
    elif command == "stage-knowledge":
        gathered_path, topic, knowledge_json = sys.argv[2], sys.argv[3], sys.argv[4]
        print(json.dumps(stage_knowledge(gathered_path, topic, knowledge_json)))
    elif command == "finalize-reasoning":
        gathered_path, reasoning_json = sys.argv[2], sys.argv[3]
        print(json.dumps(finalize_reasoning(gathered_path, reasoning_json)))
