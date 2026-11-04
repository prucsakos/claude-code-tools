---
name: teaching-video
description: Use when the user wants a teaching, tutorial or explainer video that explains a concept, a mechanism, a procedure or any study material (notes, a chapter, a paper, code), or only the storyboard for one. Plans the lesson, writes the narration and the storyboard, builds animated HTML scenes, and renders them into an MP4 with text-to-speech narration and captions (Playwright and ffmpeg). Claude Code skill.
---

# Teaching Video

You turn material into a short narrated video that teaches it. The lesson design decides whether the video teaches anything, so spend most of the effort on sections 2 and 3. The renderer handles timing and sync.

SKILL_DIR is this skill's directory. Its files:
- `make_video.py`: renders a storyboard into the video.

In the commands below, `python` means `python3` on macOS and Linux, and `python` or `py -3` on Windows (there `python3` can be the Microsoft Store stub).
- `theme.css`: shared look and beat animations for all scenes.
- `scene-template.html`: the starting point for a scene.

## Modes

A first argument `storyboard` or `full` picks the mode.

- `full` (default): storyboard, scenes, a rendered and checked video.
- `storyboard`: stop after section 3 and show the storyboard as a table (scene, narration, visuals), then the claims summary from "Check the facts". This is the same split as the `--video storyboard|full` option of `/explain`.

## Requirements

Check them once, before section 4, with `python SKILL_DIR/make_video.py --doctor` (add `--language hu` to count the voices of the narration language). It prints one line per tool: Python, ffmpeg, ffprobe, Playwright and whether Chromium launches, edge-tts and its voices, Windows SAPI voices, and optional tools (manim, LaTeX, ImageMagick, Inkscape, mmdc, node). It exits non-zero when a required tool is missing and prints the install command for each one. When it reports a missing tool, run `python SKILL_DIR/make_video.py --doctor --install`: it prints and runs the install command for each missing tool (pip for Playwright and edge-tts, Playwright for Chromium, winget, brew or apt-get for ffmpeg), stops if one fails, then checks again and exits 0 only when every required tool is present. After a package manager installs ffmpeg, a new shell may be needed before it is on PATH. The usual commands are:

```
python -m pip install playwright edge-tts
python -m playwright install chromium
```

ffmpeg comes from the OS package manager: `winget install Gyan.FFmpeg`, `brew install ffmpeg` or `apt install ffmpeg`.

## 1. Intake

Take every input that the request or the conversation gives. Read the given material (files, URLs, code) completely before planning. Ask a question only when there is no topic or material at all. Use these defaults for the rest and list them in the final summary:

| Input | Default |
|---|---|
| Audience | A curious adult with no background in the topic |
| Objective | After the video, the viewer can explain the concept in their own words, or do the procedure |
| Length | 2–4 minutes (about 300–600 narration words). Over 8 minutes: propose a series of videos, one objective each |
| Language | English for narration, on-screen text and captions, whatever language the request is written in. Use another language only when the user names it (for example "in Hungarian") |
| Narration | `edge` with `en-US-AndrewNeural`; `hu-HU-NoemiNeural` only when the user names Hungarian; other voices: `python -m edge_tts --list-voices` |
| Project folder | `./<topic-slug>-video/` in the current directory |

**Privacy:** the `edge` backend sends the narration text to Microsoft's online speech service. When the material is confidential (internal code, customer data, unpublished work), use `sapi` (Windows voices, offline) or `none` (captions only, no voice), unless the user agrees to `edge`.

## 2. Plan the lesson

Before the storyboard, decide and write into it: the objective (one sentence), the audience, the prerequisites the viewer needs, and the misconception the viewer most likely brings.

**Concept or mechanism.** Use these parts in this order. Each part is one or more scenes:
1. **Hook**: the problem or question that the concept answers, in a concrete situation. At most 20 seconds.
2. **Intuition**: the plain-words version first, with an everyday analogy and no jargon. End it with one mapping beat: the screen pairs each analogy element with its domain term (for example `drawer → bucket`), each term in the color it keeps in later scenes. The domain terms enter through the analogy, so the Mechanism uses them without a new introduction.
3. **Mechanism**: cause, then effect, one step per beat. Show a part before you name it, and name it when it is needed.
4. **Worked example**: concrete values, walked through from start to end.
5. **Pitfall**: the common misconception, or where the concept stops applying. If the video used an analogy, also say where the analogy stops working.
6. **Recap**: at most three points, in the same words that the video used before.
7. **Check question**: one question that makes the viewer apply the idea. Pause for 3 seconds (`"pause": 3`), then give the answer.

**Audience level.** Choose the row from the intake audience. It sets the time per part; the part order stays.

| Audience | Changes to the parts |
|---|---|
| Novice (no background; the default) | The full sequence. Keep the analogy, and refer back to it in the Mechanism |
| Some background | Hook, then a short Intuition (the analogy and the mapping beat in one scene). More Mechanism beats and a second worked example |
| Expert or student of the field | Skip the analogy and the mapping beat: the Intuition is one beat in domain terms. Lead with the Mechanism; the Pitfall covers edge cases and limits |

**Procedure or tool tutorial.** Show the end result first, then the prerequisites, then the steps: one action per beat, and the state after each action. Then the most common error and its fix, then a recap. For software, use real screenshots in the scenes and highlight the control under discussion.

**Rules for every scene** (from research on multimedia learning):
- One idea per scene, one change on screen per beat.
- The narration explains and the screen shows. Do not put narration sentences on screen. The screen holds labels, key terms, numbers and diagrams: at most about 12 words added per beat.
- Show a thing in the same beat that names it, and highlight the part that the narration is about.
- Put labels next to what they label, not in a legend.
- Cut what the objective does not need: decorative images, background music, side topics.
- Use concrete values before abstract rules, and a formula only after the viewer has seen what each symbol stands for.
- Use the same term for the same thing in narration, labels and captions. Give a concept the same color in every scene.

**Narration.** Write for the ear: second person, sentences of 8–20 words, one to three sentences per beat, about 150 words per minute. Text-to-speech reads symbols and abbreviations literally, so write them as spoken words ("x squared", "for example", "seven"). The captions show the same text.

## 3. Write the storyboard

Write `<project>/storyboard.json`:

```json
{
  "title": "How a hash map finds a value",
  "objective": "The viewer can explain why a hash map finds a value in one step.",
  "audience": "Beginner programmer",
  "tts": "edge",
  "voice": "en-US-AndrewNeural",
  "fps": 30,
  "scenes": [
    {
      "id": "hook",
      "html": "scenes/01-hook.html",
      "beats": [
        {"say": "Imagine a phone book with a million names, and you need one of them.", "show": "1,000,000 names"},
        {"say": "Checking the names one by one could take a million steps.", "show": "'up to 1,000,000 steps', highlighted", "pause": 1}
      ]
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `tts` | `edge` (online neural voices), `sapi` (Windows voices, offline) or `none` (no voice: a beat lasts as long as reading its caption takes, and captions are burned in) |
| `voice` | edge: a short name such as `en-US-AndrewNeural`. sapi: an installed Windows voice such as `Microsoft Zira Desktop` (often English only); empty is the system default |
| `rate` | edge only: speaking rate such as `"-10%"`. Default `"+0%"` |
| `fps` | 24, 25, 30 (default) or 60 |
| scene `lead`, `tail` | Seconds of silence before the first beat (0.4) and after the last beat (0.8) |
| beat `say` | The narration. It is also the caption |
| beat `show` | What the screen adds in this beat. It is for you and for storyboard mode; the renderer ignores it |
| beat `pause` | Seconds of silence after the beat (0.35) |
| `sources` | Optional list of strings: the material the claims come from, such as `"notes.md, section 2"` or a URL |

`objective`, `audience` and `sources` are for you; the renderer ignores them.

**Check the facts** (both modes). Before you build scenes, list every factual claim, number and formula in the beats' `say` and `show` as a table in `<project>/claims.md`:

| Claim | Beat | Source |
|---|---|---|
| Checking names one by one takes up to 1,000,000 steps | `hook` beat 2 | computed: one check per name, 1,000,000 names |
| Most languages build their dictionaries on hash maps | `intuition` beat 1 | unsourced |

The source is the given material with its location (file and section, or URL), a computation, or general knowledge marked "unsourced". Recompute every number of the worked example with a one-off `python -c` calculation, and fix the beats where the result differs. Rewrite or cut a claim that is neither in the material nor computable; keep it only when the user must decide, and then name it in the summary. The claims summary is one line: "claims checked: n, unsourced: m", followed by the unsourced claims that remain.

In `storyboard` mode, stop here.

## 4. Build the scenes

First run `python SKILL_DIR/make_video.py <project>/storyboard.json --scaffold`. It copies `theme.css` next to the scene files and creates every missing scene file with the scene id as heading and one `in rise` block per beat, wired to that beat with `--at: var(--bN)` and holding the beat's `show` text (or its `say` text when `show` is missing). It never overwrites a file that exists. Then edit each generated scene into its real layout; `scene-template.html` in SKILL_DIR shows more of the classes below. The renderer loads each scene as a 1920×1080 page and drives it by time:

- **Beat timing.** The renderer sets `--b0`, `--b1`, … on `:root` to the start time of each beat of the scene. To reveal an element when beat 2 starts, give it an animation class and `style="--at: var(--b2)"`. Offsets work: `--at: calc(var(--b2) + .8s)`. `--dur` sets the length (default `.6s`).
- **Animation classes** (in `theme.css`): `in` (fade in), `in rise`, `in pop`, `in wipe`, `draw` (draws an SVG shape that has `pathLength="1"`), `mark` (highlights a phrase), `out` (fades out), `dim` (fades to 25%). An element takes one of these; nest elements to combine two. `rise` and `pop` move the element, so use them on block or inline-block elements.
- **Own animations.** CSS keyframe animations work: `animation: spin 2s linear var(--b3) both`. Do not use CSS transitions, `setTimeout` or `requestAnimationFrame`. The renderer pauses every animation and seeks it to each frame time, so motion that follows the wall clock does not render.
- **Motion computed in JavaScript** (canvas, simulations, plots, counters): define `window.renderAt = (t, beats) => { … }`. `t` is the seconds since the scene start and `beats` holds the beat start times. Draw the frame for `t` as a pure function of `t`, and return `false` when the frame did not change, so that the renderer can reuse the previous screenshot.
- **Techniques.** `animations.md` in SKILL_DIR is a catalog of techniques that work with this model (stagger, path drawing, motion paths, morphing, counters, simulations, camera moves, focus by dimming), each with a snippet, when it helps teaching and its caveats. `examples/animations/` renders all of them. Its section 9 shows adapters that drive GSAP, anime.js and Lottie from `renderAt` (a paused timeline seeked to `t`); `examples/libraries/` renders them.
- **Async setup** (fonts are handled; Mermaid, image decoding): assign a Promise to `window.sceneReady`. The first frame waits for it.
- **Loading.** Scenes open from `file://`. Classic `<script src>`, `<img>`, CSS and https URLs load; `fetch()` of local files and local ES-module imports fail. Put local data inline in the scene.
- **Layout.** Keep content inside the `.stage` padding: a 96 px margin and 180 px at the bottom, where captions go. Sizes: titles 80 px, body text 44 px or more, labels 32 px or more, code 34 px with at most 15 lines. Build the picture up over the beats; remove or dim earlier parts only when they distract.
- **Content.** Draw diagrams as inline SVG, so that each part can appear on its own beat. Render math with KaTeX (`https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/`). Put local images next to the scene file.

## 5. Preview and fix

```
python SKILL_DIR/make_video.py <project>/storyboard.json --preview
```

This narrates every beat (cached in `build/tts/`, so later runs narrate only changed text), writes `build/timeline.json` with the start and end of each beat, and saves one still per beat to `build/preview/`: the last frame before the next beat, so it shows everything the beat added. Contact sheets `build/preview/sheet-NN.png` hold 9 stills each in storyboard order; the command prints which still is which beat. Stills of a scene whose HTML, other files in its folder (such as `theme.css` and images) and timing did not change are reused from `build/preview/cache/`, so a preview after a fix re-shoots only the changed scenes.

Look at every contact sheet. Check for text that overflows or is cut off, elements that overlap, text that is too small, an element that appears in the wrong beat, and empty frames. Warnings for JavaScript errors and files that did not load are printed with the scene id. Fix the scenes, and preview again until every still is correct.

## 6. Render and check

```
python SKILL_DIR/make_video.py <project>/storyboard.json [--burn-captions]
```

Run it with `run_in_background: true`: the first run takes about 30–40 seconds per minute of video (narration included), longer with much animation. It writes `<project>/video.mp4` (H.264, AAC and captions as a subtitle track) and `<project>/captions.srt`. `--burn-captions` draws the captions into the picture; with `tts: none` they are always burned in. `--tts`, `--voice` and `--rate` override the storyboard, for example to render the same storyboard with a different voice.

Then check the file:
- `ffprobe -v error -show_entries stream=codec_type,duration -of compact <project>/video.mp4`: the video and audio durations agree within 0.1 s.
- Extract frames in the middle of two or three animations (times from `build/timeline.json`) and look at them: `ffmpeg -v error -ss <seconds> -i video.mp4 -frames:v 1 frame.png`.

## 7. Deliver

Report: the path of `video.mp4`, its length, one line per scene, the narration backend and voice (for `edge`, that the narration text went to Microsoft's speech service), the claims summary from section 3, and the defaults you assumed. Offer what is cheap to do next: a different voice or language (change the `say` texts and render again), burned-in captions, or a shorter cut.
