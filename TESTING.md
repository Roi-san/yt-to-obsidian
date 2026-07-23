# Testing

These are prompt-driven agents, not pure functions — "testing" here means running them against
known inputs and checking the output against a checklist, in isolation from each other wherever
possible. The staged `.gathered/<slug>.json` file (see `SCHEMA.md`) is what makes isolation
possible: it's a real, inspectable artifact between the two agents, not an implicit handoff.

## Testing info_gatherer alone

1. Invoke it with a topic you know has clear, well-covered YouTube content (e.g. "python
   decorators").
2. Check `.gathered/<slug>.json`:
   - Is `videos` non-empty, and are the videos actually about the topic (not clickbait matches)?
   - Does `transcript` contain real text, not an error message or empty string?
   - Is `exhaustive_after_first_pair` consistent with what you'd expect from skimming the
     transcripts yourself?
3. Repeat with a narrower/obscure topic to see the "extend to 4" branch trigger, and a topic with
   little to no good YouTube coverage to see the failure-handling path (should report clearly, not
   stage a garbage file).

## Testing info_summariser alone

1. Hand-write a small fixture at `.gathered/test-topic.json` (2 videos with deliberately
   overlapping content is enough) matching `SCHEMA.md`.
2. Set `OBSIDIAN_VAULT_PATH` in `.env` to a scratch folder, not your real vault, for this test.
3. Invoke `info_summariser` for `test-topic` and check the output file:
   - Nothing present in either fixture transcript is missing from the note.
   - Redundant overlap between the two fixture videos was collapsed, not repeated.
   - Frontmatter has a `sources` list with both fixture URLs.

## Testing the full pipeline

Run `info_gatherer` on a topic, then `info_summariser` on the same topic, then open the resulting
note in your real vault and read it as if you were trying to learn the topic from it — that's the
actual success criterion (see `CLAUDE.md`), and no isolated check substitutes for it.
