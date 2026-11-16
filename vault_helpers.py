"""Tiny CLI used by the info_summariser subagent: list/read/write vault notes, manage backlinks."""
import json
import re
import sys
from datetime import date
from pathlib import Path

USAGE = """usage:
  python vault_helpers.py slug "<topic>"
  python vault_helpers.py list
  python vault_helpers.py skim <note-slug> [lines]
  python vault_helpers.py write "<title>" '<json array of source urls>' ['<json array of tags>']   (note body on stdin)
  python vault_helpers.py backlink <existing-note-slug> <new-note-slug>"""


def _vault_path() -> Path:
    env_file = Path(".env")
    if not env_file.exists():
        raise RuntimeError(
            "No .env file found. Copy .env.example to .env and set OBSIDIAN_VAULT_PATH."
        )
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("OBSIDIAN_VAULT_PATH="):
            raw_value = line.split("=", 1)[1].strip().strip("\"'")
            if not raw_value:
                raise RuntimeError("OBSIDIAN_VAULT_PATH is set but empty in .env — see .env.example.")
            vault_path = Path(raw_value)
            if not vault_path.is_dir():
                raise RuntimeError(
                    f"OBSIDIAN_VAULT_PATH is set to '{vault_path}' in .env, but that folder doesn't exist."
                )
            return vault_path
    raise RuntimeError("OBSIDIAN_VAULT_PATH not set in .env — see .env.example.")


def _note_path(slug: str) -> Path:
    path = _vault_path() / f"{slug}.md"
    if not path.exists():
        raise RuntimeError(f"No note called '{slug}' in the vault — run `list` to see the slugs that exist.")
    return path


def _unquote(value: str) -> str:
    """Frontmatter titles are written as quoted strings; older notes have them bare."""
    value = value.strip()
    if value.startswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    return value.strip("\"'")


def list_notes(head_lines: int = 15) -> list[dict]:
    notes = []
    for path in sorted(_vault_path().glob("*.md")):
        with path.open("r", encoding="utf-8", errors="replace") as f:
            text = "".join(next(f, "") for _ in range(head_lines))
        title_match = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)
        tags_match = re.search(r"^tags:\s*\[(.*)\]\s*$", text, re.MULTILINE)
        tags = [t.strip() for t in tags_match.group(1).split(",") if t.strip()] if tags_match else []
        notes.append({
            "slug": path.stem,
            "title": _unquote(title_match.group(1)) if title_match else path.stem,
            "tags": tags,
        })
    return notes


def read_note_skim(slug: str, lines: int = 20) -> str:
    return "\n".join(_note_path(slug).read_text(encoding="utf-8").splitlines()[:lines])


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def write_note(title: str, sources: list[str], body: str, tags: list[str] | None = None) -> dict:
    tag_str = ", ".join(filter(None, (slugify(t) for t in tags or [])))  # Obsidian tags can't hold spaces
    source_lines = "\n".join(f"  - {s}" for s in sources)
    frontmatter = (
        "---\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"  # quoted: a bare "A: B" title is invalid YAML
        f"created: {date.today().isoformat()}\n"
        f"tags: [{tag_str}]\n"
        "sources:\n"
        f"{source_lines}\n"
        "---\n\n"
    )
    base_slug = f"{slugify(title)}-{date.today().isoformat()}"
    new_slug = base_slug
    suffix = 2
    while (_vault_path() / f"{new_slug}.md").exists():  # never overwrite an existing note
        new_slug = f"{base_slug}-{suffix}"
        suffix += 1
    out_path = _vault_path() / f"{new_slug}.md"
    out_path.write_text(frontmatter + body.strip() + "\n", encoding="utf-8")
    return {"path": str(out_path), "slug": new_slug}


def add_backlink(note_stem: str, link_to_stem: str) -> None:
    path = _note_path(note_stem)
    text = path.read_text(encoding="utf-8")
    bullet = f"- [[{link_to_stem}]]"
    if f"[[{link_to_stem}]]" in text:
        return
    if "## Related" in text:
        text = text.replace("## Related", f"## Related\n{bullet}", 1)
    else:
        text = text.rstrip() + f"\n\n## Related\n{bullet}\n"
    path.write_text(text, encoding="utf-8")


def main(argv: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    command = argv[1] if len(argv) > 1 else ""
    if command == "slug" and len(argv) > 2:
        print(slugify(argv[2]))
    elif command == "list":
        print(json.dumps(list_notes(), ensure_ascii=False))
    elif command == "skim" and len(argv) > 2:
        print(read_note_skim(argv[2], int(argv[3]) if len(argv) > 3 else 20))
    elif command == "write" and len(argv) > 3:
        tags = json.loads(argv[4]) if len(argv) > 4 else []
        body = sys.stdin.buffer.read().decode("utf-8")
        print(json.dumps(write_note(argv[2], json.loads(argv[3]), body, tags), ensure_ascii=False))
    elif command == "backlink" and len(argv) > 3:
        add_backlink(argv[2], argv[3])
    else:
        sys.exit(USAGE)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except RuntimeError as error:  # setup/usage problems get one clear line, not a traceback
        sys.exit(f"error: {error}")
