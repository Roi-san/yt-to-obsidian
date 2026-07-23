# yt-to-obsidian

Type a topic, get a note. Two Claude Code subagents turn a topic into a single, information-dense
Obsidian note built from a small, self-bounded set of YouTube videos.

- **`info_gatherer`** — searches YouTube for the topic, judges candidate videos by title/description
  relevance, pulls transcripts for the top 2, and decides whether that's already exhaustive or
  whether up to 2 more videos are needed. Stages its output as `.gathered/<slug>.json`.
- **`info_summariser`** — reads that staged file, synthesizes the transcripts into one markdown
  note (tagging distinct subtopics rather than splitting into multiple files), and writes it into
  the Obsidian vault.

The two agents only talk to each other through that staged JSON file — see `SCHEMA.md` for the
exact contract. That's what makes each one testable on its own; see `TESTING.md`.

## Prerequisites

- [Claude Code](https://claude.com/claude-code)
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) available on `PATH`
- A copy of `.env.example` as `.env` with `OBSIDIAN_VAULT_PATH` set to your vault's folder

## Status

v1 (in progress): topic in → one note in the vault, written directly to the vault folder, no
external services beyond `yt-dlp`.

Deliberately out of scope for v1, deferred to a later pass:

- Filtering candidate videos by channel size/subscriber count
- Detecting and skipping duplicate concepts already in the vault
- Splitting a topic into multiple linked (`[[wikilink]]`) notes
- Writing via an Obsidian MCP server instead of a direct file write

See `CLAUDE.md` for the full architecture and the reasoning behind these boundaries.
