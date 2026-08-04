"""Tiny CLI used by the info_summariser subagent: list/read/write vault notes, manage backlinks."""
import json
import re
import sys
from datetime import date
from pathlib import Path


def _vault_path() -> Path:
    env_file = Path(".env")
    if not env_file.exists():
        raise RuntimeError(
            "No .env file found. Copy .env.example to .env and set OBSIDIAN_VAULT_PATH."
        )
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("OBSIDIAN_VAULT_PATH="):
            raw_value = line.split("=", 1)[1].strip()
            if not raw_value:
                raise RuntimeError("OBSIDIAN_VAULT_PATH is set but empty in .env — see .env.example.")
            vault_path = Path(raw_value)
            if not vault_path.is_dir():
                raise RuntimeError(
                    f"OBSIDIAN_VAULT_PATH is set to '{vault_path}' in .env, but that folder doesn't exist."
                )
            return vault_path
    raise RuntimeError("OBSIDIAN_VAULT_PATH not set in .env — see .env.example.")


def list_notes(head_lines: int = 15) -> list[dict]:
    notes = []
    for path in _vault_path().glob("*.md"):
        with path.open("r", encoding="utf-8") as f:
            text = "".join(next(f, "") for _ in range(head_lines))
        title_match = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)
        tags_match = re.search(r"^tags:\s*\[(.*)\]\s*$", text, re.MULTILINE)
        tags = [t.strip() for t in tags_match.group(1).split(",") if t.strip()] if tags_match else []
        notes.append({
            "slug": path.stem,
            "title": title_match.group(1).strip() if title_match else path.stem,
            "tags": tags,
        })
    return notes


def read_note_skim(slug: str, lines: int = 20) -> str:
    path = _vault_path() / f"{slug}.md"
    return "\n".join(path.read_text(encoding="utf-8").splitlines()[:lines])


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def write_note(title: str, sources: list[str], body: str, tags: list[str] | None = None) -> dict:
    tag_str = ", ".join(tags or [])
    source_lines = "\n".join(f"  - {s}" for s in sources)
    frontmatter = (
        "---\n"
        f"title: {title}\n"
        f"created: {date.today().isoformat()}\n"
        f"tags: [{tag_str}]\n"
        "sources:\n"
        f"{source_lines}\n"
        "---\n\n"
    )
    new_slug = f"{slugify(title)}-{date.today().isoformat()}"
    out_path = _vault_path() / f"{new_slug}.md"
    out_path.write_text(frontmatter + body, encoding="utf-8")
    return {"path": str(out_path), "slug": new_slug}


def add_backlink(note_stem: str, link_to_stem: str) -> None:
    path = _vault_path() / f"{note_stem}.md"
    text = path.read_text(encoding="utf-8")
    bullet = f"- [[{link_to_stem}]]"
    if bullet in text:
        return
    if "## Related" in text:
        text = text.replace("## Related", f"## Related\n{bullet}", 1)
    else:
        text = text.rstrip() + f"\n\n## Related\n{bullet}\n"
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "list":
        print(json.dumps(list_notes()))
    elif command == "skim":
        lines = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        print(read_note_skim(sys.argv[2], lines))
    elif command == "write":
        title, sources_json = sys.argv[2], sys.argv[3]
        tags = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
        body = sys.stdin.buffer.read().decode("utf-8")
        print(json.dumps(write_note(title, json.loads(sources_json), body, tags)))
    elif command == "backlink":
        add_backlink(sys.argv[2], sys.argv[3])
