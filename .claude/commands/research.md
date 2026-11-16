---
description: Research a topic from YouTube and write one note into the Obsidian vault.
argument-hint: <topic> [max-video-minutes]
---

Parse $ARGUMENTS: if the last token is a plain integer, that's an optional max video length in
minutes — set it aside and treat everything before it as the topic. Otherwise the whole thing is
the topic and there's no override. If there's no topic at all, ask for one and stop.

Run the full yt-to-obsidian pipeline for that topic:

1. Run `python vault_helpers.py slug "<topic>"`. The staged file path for this run is
   `.gathered/<printed-slug>.json` — give that exact path to both subagents, so neither has to
   derive it and they can't disagree about it.
2. Invoke the `info_gatherer` subagent with the topic and the staged path. If a max-video-minutes
   value was parsed out, tell it to pass that number as the optional 3rd argument to
   `python youtube_helpers.py search "<query>" <minutes>` (otherwise it relies on the script's
   own default cap).
3. Check the staged file exists and contains a `"reasoning"` key. If it doesn't, the gather didn't
   finish — report what the gatherer said and stop here; don't invoke the summariser on nothing.
4. Invoke the `info_summariser` subagent with the same topic and staged path to write the note
   into the vault.
5. Report the note's path and title, how many videos it drew on, and how many open questions it
   left — one or two lines, not a recap of the note.
