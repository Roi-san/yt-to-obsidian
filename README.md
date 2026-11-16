# yt-to-obsidian

Type a topic, get one synthesized note — sourced, cross-checked, and reasoned over from YouTube,
written straight into your Obsidian vault.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Why this design](#why-this-design)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage](#usage)
- [Project structure](#project-structure)
- [Status](#status)
- [License](#license)

## Overview

Two [Claude Code](https://claude.com/claude-code) subagents do the work, chained by one slash
command:

- **`info_gatherer`** turns a topic into a YouTube search, picks a couple of relevant videos,
  extracts claims/definitions/examples with timestamps, then reasons over what it found —
  agreements, disagreements, and questions the sources didn't answer. If something concrete is
  still missing, it runs one more targeted search before finishing.
- **`info_summariser`** reads that structured knowledge, checks your vault for related notes, and
  writes one note in its own words — with tags, `[[wikilinks]]`, bidirectional backlinks, and a
  clickable citation after each claim that opens the source video at the exact moment it was said.

## Architecture

```mermaid
flowchart TD
    U["/research topic"] --> IG

    subgraph IG["info_gatherer"]
        direction TB
        S[Search YouTube] --> P[Pick top videos]
        P --> T[Fetch timestamped transcript]
        T --> EX["Extract claims, definitions, examples"]
        EX --> SK["Merge into knowledge state"]
        SK --> RE{Gap in reasoning?}
        RE -- "yes, under 4 videos" --> S
        RE -- "no" --> FR["Finalize reasoning"]
    end

    FR --> GF([".gathered/slug.json"])
    GF --> IS

    subgraph IS["info_summariser"]
        direction TB
        RD["Read observations + reasoning"] --> VL["Check vault for related notes"]
        VL --> WR["Write synthesized note"]
        WR --> BL["Add bidirectional backlinks"]
        BL --> DEL["Delete staged JSON"]
    end

    IS --> V(["Obsidian vault note"])
```

## Why this design

**The value over just watching the videos yourself:** a single LLM call asked to summarize "what
does the internet say about X" from its own training data can't cite anything, can't tell you when
two sources actually disagree, and can't tell you what it doesn't know. This pipeline grounds every
claim in a real video and timestamp, keeps disagreements as disagreements instead of flattening
them into false consensus, and explicitly tracks what the gathered evidence still can't answer —
then plugs the result into your own note graph (tags, wikilinks, backlinks) instead of leaving it
as a one-off answer you'll lose in a chat log.

**Why extraction and synthesis are separate steps, not one pass:** this is a knowledge-
representation choice made for cost, not just cleanliness. Raw transcripts get read exactly once,
during extraction, and are never re-read after that. `info_gatherer` converts each one into a small
structured object — claims with citations, definitions, examples — and discards the transcript
text immediately. `info_summariser` only ever holds those compact objects, never several full
transcripts at once. That's what lets both agents run on a cheap model tier (Haiku, by default —
see each agent's `model:` field) even for a multi-video topic: neither one needs thousands of words
of raw transcript sitting in context to do its job. Reasoning about agreement and disagreement
across sources happens over that same small merged object, too — comparing a handful of claim
strings, not diffing raw text.

## Prerequisites

- **Python 3.10+**
- **The [Claude Code CLI](https://claude.com/claude-code)** — this project *is* a set of Claude
  Code subagents and a slash command, not a standalone script. Clone the repo and run Claude Code
  with this folder open as your working directory, so it picks up `.claude/agents/` and
  `.claude/commands/`.
- **A folder to write notes into.** A real Obsidian vault if you want the graph view and backlinks
  to show up visually — but Obsidian itself isn't required to run the pipeline, any existing
  folder of markdown files works.

## Setup

1. Clone the repo and move into it:
   ```
   git clone https://github.com/Roi-san/yt-to-obsidian.git
   cd yt-to-obsidian
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create your `.env` from the template, then edit it:
   ```
   cp .env.example .env        # macOS/Linux
   copy .env.example .env      # Windows (PowerShell/cmd)
   ```
   Set `OBSIDIAN_VAULT_PATH` to an **existing** folder:
   ```
   OBSIDIAN_VAULT_PATH=C:\Users\you\Documents\MyVault      # Windows
   OBSIDIAN_VAULT_PATH=/Users/you/Documents/MyVault        # macOS/Linux
   ```
   The pipeline won't create this folder for you — if `.env` is missing, the variable is unset, or
   the path doesn't exist, you'll get a clear message telling you exactly what to fix, the first
   time it tries to touch the vault.
4. Start Claude Code in this folder:
   ```
   claude
   ```

## Usage

Example usage from inside your Claude Code session:

```
/research multi-agent planning
```

Add a number to override the default 10-minute video-length cap:

```
/research <topic> 30
```

`info_gatherer` stages the knowledge it found as `.gathered/<slug>.json` before `info_summariser`
ever touches it — here's an abbreviated real one (trimmed from ~20 claims down to a couple per
section):

```json
{
  "schema_version": 1,
  "topic": "multi-agent planning",
  "observations": {
    "claims": [
      {
        "statement": "Multi-agent systems provide flexibility, scalability, domain specialization, and better performance than single agents",
        "stated_as": "explicit",
        "corroborated_by": ["https://youtube.com/watch?v=sWH0T4Zez6I"],
        "timestamps": [{"url": "https://youtube.com/watch?v=sWH0T4Zez6I", "time": "03:25", "link": "https://youtube.com/watch?v=sWH0T4Zez6I&t=205s"}]
      }
      // ... 22 more claims
    ],
    "definitions": [
      {"term": "Orchestration layer", "explanation": "The central hub that understands the main goal, assigns tasks to agents, and integrates their work"}
    ],
    "examples": ["Research team: one agent gathers data, a second analyzes for patterns, a third synthesizes into a report"],
    "open_questions": ["How do agents avoid deadlocks when their tasks depend on each other?"],
    "videos": [{"title": "Multi Agent Systems Explained", "url": "https://youtube.com/watch?v=sWH0T4Zez6I"}]
  },
  "reasoning": {
    "agreements": ["Task decomposition and agent specialization are core mechanisms for managing complex problems"],
    "disagreements": [
      {
        "topic": "Network of agents architecture suitability for production",
        "positions": [
          {"claim": "Decentralized networks enable agents to communicate with equal authority", "source": "https://youtube.com/watch?v=sWH0T4Zez6I"},
          {"claim": "Network of agents architecture is unreliable in production", "source": "https://youtube.com/watch?v=4nZl32FwU-o"}
        ],
        "likely_reason": "The first source describes a theoretical option; the second reports practical production experience"
      }
    ],
    "remaining_questions": ["What specific algorithms or techniques optimize task decomposition in multi-agent planning?"],
    "unexpected_findings": ["Theoretical architectures are rarely used as-is in production; custom cognitive architectures dominate instead"]
  }
}
```

`info_summariser` reads that and writes one note — its own synthesis of `observations.claims`
organized by concept, with `sources` pulled from `observations.videos` and a closing
`## Open Questions` section pulled from `reasoning.remaining_questions`. Each claim it uses is
followed by its timestamp `link`, so a sentence in the note reads like this:

```markdown
Multi-agent systems trade a single agent's limits for specialization and scale
([03:25](https://youtube.com/watch?v=sWH0T4Zez6I&t=205s)).
```

Two things in that JSON are counted by the script, not judged by a model: `corroborated_by` grows
when a later video restates an already-staged claim, and each `link` is built from the video url
and timestamp.

## Project structure

```
.claude/
  agents/
    info_gatherer.md      # search -> extract -> reason, stages .gathered/<slug>.json
    info_summariser.md    # reads staged knowledge, writes the vault note
  commands/
    research.md           # the /research slash command
youtube_helpers.py         # search / transcript / claims / stage-knowledge / finalize-reasoning
vault_helpers.py           # slug / list / skim / write / backlink
test_youtube_helpers.py
test_vault_helpers.py
```

Both helper scripts print their usage when run with no arguments, and `python -m pytest -q` runs
the tests for the mechanical parts (merging, corroboration, links, note writing).

## Status

The core pipeline is built and tested. Deliberately not built: relevance filtering beyond
the agents' own judgment, cross-vault duplicate detection (needs a vault with real size to design
against), and an actual Obsidian MCP server (`vault_helpers.py`'s functions are a plain internal
API on purpose, so wrapping them as MCP tools later is a small step, not a rewrite).

## License

MIT — see [LICENSE](LICENSE).
