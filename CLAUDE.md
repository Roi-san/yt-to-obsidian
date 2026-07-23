# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This is a learning project. It is currently empty scaffolding — no implementation exists yet.
The owner is intentionally building this themselves to learn; do not write the agents' logic,
YouTube fetching code, or Obsidian MCP integration for them unless they explicitly ask for that
specific piece. Prefer explaining, pointing to docs, and reviewing what they write over writing
it yourself.

## Goal & success criteria

Type a topic → get one `.md` file in the user's Obsidian vault, with no loss of the source
information, produced from a bounded (2–4 video) research pass.

## Intended architecture

Two Claude Code subagents, defined under `.claude/agents/` (stub files created, instructions not
yet written — that's the owner's own work, see Project status above):

1. **`info_gatherer`** — given a topic string:
   - Searches YouTube via `yt-dlp`'s `ytsearch:` to get candidate titles/descriptions (no full
     fetch yet).
   - Judges relevance from titles/descriptions only (cheap — avoids pulling transcripts for
     obviously irrelevant videos).
   - Pulls transcripts for the top 2 relevant videos.
   - Makes one LLM comparison call: if the two transcripts are near-identical, treats the topic as
     exhaustively covered and stops. If they overlap but seem incomplete, pulls transcripts for 2
     more videos (hard cap of 4 total; the second batch is not re-judged).
   - Hands the gathered transcripts to `info_summariser`.
2. **`info_summariser`** — given the gathered transcripts for one topic:
   - Synthesizes them into **one** markdown note (not split into multiple files).
   - If distinct subtopics are present, flags them via YAML frontmatter tags rather than splitting
     into separate notes.
   - Writes the note directly to a path inside the Obsidian vault folder using the `Write` tool
     (a vault is just a folder of markdown files — no MCP is required for a note to "appear" in
     Obsidian).

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
- There are no build/lint/test commands yet since no code exists. Update this section once a
  language/toolchain is chosen for the fetching or generation logic.
