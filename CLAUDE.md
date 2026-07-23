# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This is a learning project. The owner is intentionally building most of it themselves; the two
agent instruction files were written by Claude at the owner's explicit request as a starting
point for them to iterate on. Don't assume that extends to future pieces (e.g. the MCP
integration is explicitly the owner's own task, see below) — check what's actually been asked for
rather than defaulting to writing things. Prefer explaining, pointing to docs, and reviewing what
they write over writing it yourself unless asked.

## Goal & success criteria

Type a topic → get one `.md` file in the user's Obsidian vault, with no loss of the source
information, produced from a bounded (2–4 video) research pass.

## Architecture

Two Claude Code subagents, defined under `.claude/agents/`. They communicate only through a
staged JSON file (`.gathered/<slug>.json`, gitignored), whose exact shape is the contract defined
in `SCHEMA.md` — that decoupling is what makes each agent testable in isolation (see
`TESTING.md`).

1. **`info_gatherer`** — given a topic string:
   - Searches YouTube via `yt-dlp`'s `ytsearch:` to get candidate titles/descriptions (no full
     fetch yet).
   - Judges relevance from titles/descriptions only (cheap — avoids pulling transcripts for
     obviously irrelevant videos).
   - Pulls transcripts for the top 2 relevant videos.
   - Makes one LLM comparison call: if the two transcripts are near-identical, treats the topic as
     exhaustively covered and stops. If they overlap but seem incomplete, pulls transcripts for 2
     more videos (hard cap of 4 total; the second batch is not re-judged).
   - Stages the result as `.gathered/<slug>.json` per `SCHEMA.md`.
2. **`info_summariser`** — given `.gathered/<slug>.json` for one topic:
   - Synthesizes the transcripts into **one** markdown note (not split into multiple files).
   - If distinct subtopics are present, flags them via YAML frontmatter tags rather than splitting
     into separate notes.
   - Writes the note directly to a path inside the Obsidian vault folder using the `Write` tool,
     named `<slug>-<date>.md` (a vault is just a folder of markdown files — no MCP is required for
     a note to "appear" in Obsidian). The date suffix means a later rerun on the same topic adds a
     new note instead of silently overwriting — reconciling old vs. new is a v2 concern.

### Explicitly out of scope for v1 (deferred to v2)

- Subscriber-count (or other channel-quality) filtering heuristic in `info_gatherer`.
- Cross-vault duplicate/concept detection — v1 always writes a new file; topics may legitimately
  need refreshed notes as information changes, so dedup is intentionally not attempted yet.
- Wikilinks between notes / splitting a topic into multiple linked atomic notes.
- Obsidian MCP integration. The user wants to learn MCP deliberately, not as a side effect of
  debugging agent prompts, so it's sequenced *after* the two-agent pipeline is proven against a
  plain file write. In a subagent architecture the swap from `Write` to an MCP tool call is a
  small change (agent tool list + one instruction line), so deferring it costs little. No MCP
  server has been chosen yet; that selection is the user's own task.

### Known open risk

The "is this topic exhaustively covered yet" self-assessment in `info_gatherer` is a single LLM
judgment call with no ground truth — it may over- or under-fetch inconsistently across topics.
Not something to design around preemptively; worth watching once testing against real topics.

## Working in this repo

- Subagent definitions belong in `.claude/agents/*.md` (YAML frontmatter: `name`, `description`,
  `tools`, optionally `model`, followed by the system prompt).
- There is no application code and no build step — both agents work entirely through existing
  tools (`yt-dlp` via Bash, `Read`/`Write` for the staged file and the note). Changing behavior
  means editing the agent instruction files directly.
- The `info_gatherer` ↔ `info_summariser` contract lives in `SCHEMA.md`; keep both agent files in
  sync with it rather than letting either drift into its own shape.
- No automated tests — see `TESTING.md` for the manual check procedure for each agent and for the
  full pipeline.
