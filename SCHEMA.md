# Gathered-data contract

The interface between `info_gatherer` and `info_summariser`. Keeping it in one place means either
agent's instructions can change independently as long as both agree on this shape.

## Topic slug

Both agents derive the same slug from a topic string: lowercase, trim, collapse runs of
whitespace/punctuation into a single `-`, strip leading/trailing `-`.

`"Python Decorators!"` → `python-decorators`

## Staging file

Path: `.gathered/<topic-slug>.json`. Directory is created if missing. Gitignored — this is
run-specific scraped data, not project source, and may contain copyrighted transcript text.

## Schema

```json
{
  "topic": "string — the raw topic as typed by the user",
  "slug": "string — the derived slug",
  "gathered_at": "string — ISO 8601 timestamp",
  "exhaustive_after_first_pair": "boolean",
  "videos": [
    {
      "video_id": "string — YouTube video id",
      "url": "string — full YouTube URL",
      "title": "string",
      "channel": "string",
      "transcript": "string — full transcript text"
    }
  ]
}
```

- `videos` has 2 entries if the first-pair comparison found them near-identical, otherwise up to
  4. Never more than 4.
- `exhaustive_after_first_pair` records which branch `info_gatherer` took — useful for debugging
  and for future tuning of the comparison step.

## Future extension points (v2 — not implemented, don't add fields for these speculatively)

- A `channel_subscriber_count` field per video, once the subscriber-count filter heuristic exists.
- A `duplicate_of` field, once cross-vault dedup gives `info_summariser` (or a step before it)
  awareness of existing notes.

Add these when the feature they support is actually built, not before.
