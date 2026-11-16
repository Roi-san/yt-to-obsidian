# CLAUDE.md

Guidance for Claude Code when working in this repo.

## What this is

Learning project, tagged v1.0, public on GitHub. Keep it minimal — no filtering, dedup, or tests
beyond what's explicitly asked for.

## Setup (one-time)

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set `OBSIDIAN_VAULT_PATH`.

## Usage

`/research <topic> [max-video-minutes]` — runs the full pipeline: `info_gatherer` then
`info_summariser`, back-to-back. That's the only command a human runs directly. Defaults: videos
over 10 minutes are skipped unless you pass an override (`/research <topic> 30`).

## How it works

- **`info_gatherer`** (`.claude/agents/info_gatherer.md`) — two phases:
  - **Extract**: turns a topic into a YouTube search query, picks the 2 most relevant videos,
    fetches their timestamped transcripts via `youtube_helpers.py`, and extracts a Layer 1
    knowledge object per video (claims/definitions/examples/open_questions), staged mechanically
    via `stage-knowledge` into `.gathered/<slug>.json`. From the second video on it reads the
    already-staged statements (`claims`) and reuses their wording for restated claims, which is
    what makes `corroborated_by` count for real. The merge also builds a `link` per timestamp
    that opens the video at that moment.
  - **Reason**: reasons over the merged Layer 1 state only (never re-reads transcripts) to produce
    agreements/disagreements/remaining_questions/unexpected_findings. If something concrete is
    still missing, runs one targeted gap-driven search for one more video (hard cap 4 total), then
    calls `finalize-reasoning` to nest the merged state under `observations` and attach the
    reasoning as the final staged file.
- **`info_summariser`** (`.claude/agents/info_summariser.md`) — reads that JSON's `observations`
  and `reasoning`, checks the vault for related notes/tags via `vault_helpers.py`, writes one
  synthesized note organized by concept (each claim cited with its timestamp `link`,
  disagreements named as disagreements, and an `## Open Questions` section for anything left
  unanswered) and a content-derived title, adds
  `[[wikilinks]]` and bidirectional backlinks, then deletes the staged JSON.

See `PLAN.md` for the full schema and the reasoning behind the two-layer split — it's kept local
(gitignored), not part of the published repo, so it won't exist in a fresh clone.

Conventions worth keeping: `/research` computes the staged path once (`vault_helpers.py slug`)
and hands it to both agents, so they never derive it separately; anything bigger than a short
string (knowledge JSON, reasoning JSON, the note body) goes to the helpers on stdin via a quoted
heredoc, never as a command-line argument — apostrophes in claims broke that.

Both agents run on Haiku by default (see each file's `model:` field) — bump an agent to `sonnet`
if a topic needs sharper judgment.

`youtube_helpers.py` and `vault_helpers.py` are the only real code in the project — deterministic,
mechanical operations (search/transcript fetch; vault list/skim/write/backlink) live there as
plain functions. Everything else (which videos are relevant, which notes are related, what the
note says and is titled) is the agents' own judgment, not scripted. `vault_helpers.py`'s functions
are a plain internal API on purpose: an Obsidian MCP server, if ever wanted, could wrap these same
functions as tools without changing the underlying logic.

## Deliberately not built yet

Relevance filtering beyond the agents' own judgment, cross-vault dedup, an actual Obsidian MCP
server. Not hard — just not needed at this scale yet.
