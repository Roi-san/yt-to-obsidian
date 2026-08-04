---
description: Research a topic from YouTube and write one note into the Obsidian vault.
argument-hint: <topic> [max-video-minutes]
---

Parse $ARGUMENTS: if the last token is a plain integer, that's an optional max video length in
minutes — set it aside and treat everything before it as the topic. Otherwise the whole thing is
the topic and there's no override.

Run the full yt-to-obsidian pipeline for that topic:

1. Invoke the `info_gatherer` subagent with the topic. If a max-video-minutes value was parsed
   out, tell it to pass that number as the optional 3rd argument to
   `python youtube_helpers.py search "<query>" <minutes>` (otherwise it relies on the script's
   own default cap). Wait for it to finish staging `.gathered/<slug>.json`.
2. Invoke the `info_summariser` subagent with the same topic to write the note into the vault.
3. Report the path of the note that was written.
