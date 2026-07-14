---
description: Write the previous result (or the current command's result) to a file
argument-hint: <.ext | path>
---

Save results to a file instead of (only) chat.

Input: `$ARGUMENTS` — either a bare extension (`.md`, `.txt`, `.json`, `.csv`) or an explicit file path.

Resolve the target file:
- **Explicit path** (contains `/`, `\`, or a filename before the extension): use it as given, relative to the current working directory.
- **Bare extension** (e.g. `.md`): generate `./out/<topic-slug>-<YYYY-MM-DD>.<ext>` where `<topic-slug>` is a short kebab-case slug of the task/topic. Create the `out/` directory if needed.
- **No argument**: default to `.md` behavior.

What to write:
- If invoked as a standalone follow-up (`/out .md` after a previous answer): write the **full deliverable from the previous turn** — the complete findings/report, not the chat summary. Reconstruct detail from the conversation if the chat version was compressed.
- If the trailing `/out <spec>` appeared inline in **any** command's or request's arguments (e.g. `/some-command do a thing /out .md`): strip it from the task before executing, then write that task's final result to the file. This convention is universal — it requires no support from the other command.

Formatting rules:
- Match the format to the extension: `.md` → well-structured markdown with headers and a date line; `.json` → valid parseable JSON, no prose; `.csv` → header row + data rows, no prose.
- The file is the primary deliverable — make it self-contained (a reader without this chat must understand it).
- In chat, reply with just the file path and a 2–3 sentence summary; do not duplicate the full content in chat.
- Never overwrite an existing file that this conversation didn't create — pick a suffixed name (`-2`) instead.
