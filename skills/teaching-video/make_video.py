#!/usr/bin/env python3
"""Render a teaching video from a storyboard (see SKILL.md, sections 3-6).

Narrates every beat with text-to-speech, lays the clips on one narration
track, seeks each HTML scene to every frame time with Playwright, and encodes
the frames, the narration and the captions with ffmpeg in one pass. The scenes
follow the narration timeline, not the wall clock, so picture and voice stay in
sync at any video length.

    python make_video.py STORYBOARD.json             # video.mp4 + captions.srt
    python make_video.py STORYBOARD.json --preview   # one still per beat only
    python make_video.py --doctor [--language hu]    # which tools are installed
    python make_video.py --doctor --install          # install the missing required tools

All output goes next to the storyboard: video.mp4, captions.srt and build/.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import hashlib
import importlib
import json
import math
import re
import shutil
import subprocess
import sys
import textwrap
import time
import wave
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE = 24_000
SAMPLE_WIDTH = 2  # bytes per sample: 16-bit mono PCM
WIDTH, HEIGHT = 1920, 1080
TTS_BACKENDS = ("edge", "sapi", "none")
DEFAULT_VOICE = {"edge": "en-US-AndrewNeural", "sapi": "", "none": ""}
EDGE_ATTEMPTS = 4
# Without narration a beat lasts as long as reading its caption takes.
READING_WORDS_PER_SECOND = 2.5
CAPTION_LINE_CHARS = 42
# Sizes are in libass units of a 288-pixel-high frame: 14 is about 52 px at 1080p. Two lines fit in --caption-space (theme.css).
CAPTION_STYLE = "FontName=Arial,FontSize=14,Outline=1.2,Shadow=0,MarginV=10"
PREVIEW_SHEET_TILES = "3x3"


class StoryboardError(ValueError):
    pass


class RenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Beat:
    say: str
    pause: float


@dataclass(frozen=True)
class Scene:
    id: str
    html: Path
    beats: list[Beat]
    lead: float
    tail: float


@dataclass(frozen=True)
class Storyboard:
    title: str
    tts: str
    voice: str
    rate: str
    fps: int
    scenes: list[Scene]


@dataclass(frozen=True)
class TimedBeat:
    text: str
    start: float  # seconds from the start of the video
    end: float


@dataclass(frozen=True)
class TimedScene:
    scene: Scene
    start: float
    end: float
    beats: list[TimedBeat]

    def beat_offsets(self) -> list[float]:
        """Beat start times in seconds from the start of this scene."""
        return [beat.start - self.start for beat in self.beats]


# ---------------------------------------------------------------- storyboard


def _string(obj: dict, key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise StoryboardError(f"{where}.{key} must be a non-empty string")
    return value.strip()


def _seconds(obj: dict, key: str, default: float, where: str) -> float:
    value = obj.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise StoryboardError(f"{where}.{key} must be a number of seconds >= 0")
    return float(value)


def _object(value: object, where: str) -> dict:
    if not isinstance(value, dict):
        raise StoryboardError(f"{where} must be an object")
    return value


def _list(value: object, where: str) -> list:
    if not isinstance(value, list) or not value:
        raise StoryboardError(f"{where} must be a non-empty list")
    return value


def load_storyboard(path: Path) -> Storyboard:
    try:
        data = _object(json.loads(path.read_text(encoding="utf-8")), "storyboard")
    except json.JSONDecodeError as error:
        raise StoryboardError(f"invalid JSON: {error}") from error

    tts = data.get("tts", "edge")
    if tts not in TTS_BACKENDS:
        raise StoryboardError(f"tts must be one of {', '.join(TTS_BACKENDS)}: got {tts!r}")
    fps = data.get("fps", 30)
    if isinstance(fps, bool) or not isinstance(fps, int) or fps <= 0 or SAMPLE_RATE % fps:
        raise StoryboardError(f"fps must divide {SAMPLE_RATE} (24, 25, 30 or 60): got {fps!r}")

    scenes: list[Scene] = []
    for i, raw_scene in enumerate(_list(data.get("scenes"), "scenes")):
        where = f"scenes[{i}]"
        scene = _object(raw_scene, where)
        scene_id = _string(scene, "id", where)
        if any(existing.id == scene_id for existing in scenes):
            raise StoryboardError(f"{where}.id {scene_id!r} is used twice")
        html = (path.parent / _string(scene, "html", where)).resolve()
        if not html.is_file():
            raise StoryboardError(f"{where}.html: file not found: {html}")
        beats = []
        for j, raw_beat in enumerate(_list(scene.get("beats"), f"{where}.beats")):
            beat_where = f"{where}.beats[{j}]"
            beat = _object(raw_beat, beat_where)
            beats.append(Beat(say=_string(beat, "say", beat_where), pause=_seconds(beat, "pause", 0.35, beat_where)))
        scenes.append(
            Scene(
                id=scene_id,
                html=html,
                beats=beats,
                lead=_seconds(scene, "lead", 0.4, where),
                tail=_seconds(scene, "tail", 0.8, where),
            )
        )

    voice = data.get("voice") or DEFAULT_VOICE[tts]
    rate = data.get("rate", "+0%")
    title = data.get("title") or path.parent.name
    if not all(isinstance(value, str) for value in (voice, rate, title)):
        raise StoryboardError("title, voice and rate must be strings")
    return Storyboard(title=title, tts=tts, voice=voice, rate=rate, fps=fps, scenes=scenes)


# ----------------------------------------------------------------- narration


def silence(seconds: float) -> bytes:
    return bytes(round(seconds * SAMPLE_RATE) * SAMPLE_WIDTH)


def run_ffmpeg(*args: str) -> None:
    result = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(f"ffmpeg {' '.join(args)} failed:\n{result.stderr.strip()}")


def read_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as clip:
        if (clip.getnchannels(), clip.getsampwidth(), clip.getframerate()) != (1, SAMPLE_WIDTH, SAMPLE_RATE):
            raise RenderError(f"{path} is not {SAMPLE_RATE} Hz 16-bit mono PCM")
        return clip.readframes(clip.getnframes())


def write_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as track:
        track.setnchannels(1)
        track.setsampwidth(SAMPLE_WIDTH)
        track.setframerate(SAMPLE_RATE)
        track.writeframes(pcm)


SAPI_SCRIPT = r"""
param([Parameter(Mandatory)][string]$TextFile, [Parameter(Mandatory)][string]$OutFile, [string]$Voice)
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  if ($Voice) { $synth.SelectVoice($Voice) }
  $synth.SetOutputToWaveFile($OutFile)
  $synth.Speak([IO.File]::ReadAllText($TextFile, [Text.Encoding]::UTF8))
} finally {
  $synth.Dispose()
}
"""


class Narrator:
    """Turns beat text into 24 kHz mono PCM. Clips are cached by backend, voice, rate and text,
    so re-rendering after a visual fix does not narrate again."""

    def __init__(self, tts: str, voice: str, rate: str, cache_dir: Path):
        self.tts, self.voice, self.rate, self.cache_dir = tts, voice, rate, cache_dir

    def pcm(self, text: str) -> bytes:
        if self.tts == "none":
            return silence(max(1.5, len(text.split()) / READING_WORDS_PER_SECOND))
        key = hashlib.sha256(json.dumps([self.tts, self.voice, self.rate, text]).encode()).hexdigest()[:20]
        clip = self.cache_dir / f"{key}.wav"
        if not clip.exists():
            source = self.cache_dir / f"{key}.source"
            if self.tts == "edge":
                self._edge(text, source)
            else:
                self._sapi(text, source)
            partial = self.cache_dir / f"{key}.partial.wav"
            run_ffmpeg("-i", str(source), "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(partial))
            partial.replace(clip)
            source.unlink()
        return read_pcm(clip)

    def _edge(self, text: str, out: Path) -> None:
        try:
            import edge_tts
        except ImportError as error:
            raise RenderError(f'edge narration needs edge-tts: {sys.executable} -m pip install edge-tts (or set "tts" to "sapi" or "none")') from error
        try:
            edge_tts.Communicate(text, self.voice, rate=self.rate)
        except ValueError as error:
            raise RenderError(f"edge-tts rejected the voice or rate ({error}); list voices with: python -m edge_tts --list-voices") from error
        # The online service drops requests now and then ("No audio was received"), so retry before failing.
        # A Communicate object streams only once, so every attempt needs a new one.
        for attempt in range(1, EDGE_ATTEMPTS + 1):
            try:
                edge_tts.Communicate(text, self.voice, rate=self.rate).save_sync(str(out))
                return
            except Exception as error:  # network and service errors have no common edge-tts base class
                if attempt == EDGE_ATTEMPTS:
                    raise RenderError(f"edge-tts failed {attempt} times (voice {self.voice!r}): {error}") from error
                print(f"  edge-tts attempt {attempt} failed ({error}); retrying", file=sys.stderr, flush=True)
                time.sleep(2 * attempt)

    def _sapi(self, text: str, out: Path) -> None:
        if sys.platform != "win32":
            raise RenderError('sapi narration runs on Windows only; use "edge" or "none"')
        script = self.cache_dir / "sapi.ps1"
        script.write_text(SAPI_SCRIPT, encoding="utf-8")
        text_file = out.with_suffix(".txt")
        text_file.write_text(text, encoding="utf-8")
        command = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script),
                   "-TextFile", str(text_file), "-OutFile", str(out)]
        if self.voice:
            command += ["-Voice", self.voice]
        result = subprocess.run(command, capture_output=True, text=True)
        text_file.unlink()
        if result.returncode != 0 or not out.exists():
            raise RenderError(f"sapi narration failed (voice {self.voice!r}):\n{result.stderr.strip()}")


def build_timeline(storyboard: Storyboard, narrator: Narrator) -> tuple[list[TimedScene], bytes]:
    track = bytearray()
    frame_bytes = SAMPLE_RATE // storyboard.fps * SAMPLE_WIDTH

    def now() -> float:
        return len(track) / SAMPLE_WIDTH / SAMPLE_RATE

    timed_scenes = []
    for scene in storyboard.scenes:
        start = now()
        track += silence(scene.lead)
        beats = []
        for beat in scene.beats:
            beat_start = now()
            track += narrator.pcm(beat.say)
            beats.append(TimedBeat(text=beat.say, start=beat_start, end=now()))
            track += silence(beat.pause)
        track += silence(scene.tail)
        # End every scene on a frame boundary, so that scene cuts and narration stay aligned.
        track += bytes(-len(track) % frame_bytes)
        timed_scenes.append(TimedScene(scene=scene, start=start, end=now(), beats=beats))
        print(f"narrated {scene.id}: {now() - start:.1f} s", flush=True)
    return timed_scenes, bytes(track)


# ------------------------------------------------------------------ captions


def caption_chunks(text: str) -> list[str]:
    """Split narration into cues of at most two lines; a cue never spans two sentences."""
    chunks = []
    for sentence in re.split(r"(?<=[.!?…])\s+", text.strip()):
        lines = textwrap.wrap(sentence, CAPTION_LINE_CHARS)
        if len(lines) > 2:
            cue_count = math.ceil(len(lines) / 2)
            # Re-wrap narrower so the cues share the sentence evenly instead of ending on a one-word cue.
            for width in range(math.ceil(len(sentence) / (2 * cue_count)), CAPTION_LINE_CHARS + 1):
                balanced = textwrap.wrap(sentence, width, break_long_words=False, break_on_hyphens=False)
                if len(balanced) <= 2 * cue_count:
                    lines = balanced
                    break
        chunks += ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    return chunks


def srt_time(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def write_srt(path: Path, beats: list[TimedBeat]) -> None:
    cues = []
    for beat in beats:
        chunks = caption_chunks(beat.text)
        total_chars = sum(len(chunk) for chunk in chunks)
        start = beat.start
        # A beat's caption chunks share its narration time in proportion to their length.
        for chunk in chunks:
            end = start + (beat.end - beat.start) * len(chunk) / total_chars
            cues.append(f"{len(cues) + 1}\n{srt_time(start)} --> {srt_time(end)}\n{chunk}\n")
            start = end
    path.write_text("\n".join(cues), encoding="utf-8")


# -------------------------------------------------------------------- scenes

PREPARE_SCENE_JS = """
async (beats) => {
  // A var(--bN) past the last beat is invalid, which silently drops the whole animation.
  const used = new Set([...document.documentElement.outerHTML.matchAll(/--b(\\d+)\\b/g)].map((m) => Number(m[1])));
  for (const n of used) {
    if (n >= beats.length) console.error(`var(--b${n}) is used, but this scene has only ${beats.length} beats`);
  }
  beats.forEach((t, i) => document.documentElement.style.setProperty(`--b${i}`, `${t}s`));
  await document.fonts.ready;
  if (window.sceneReady) await window.sceneReady;
  // Every animation is paused and seeked to the frame time. Returns whether the frame can differ from the
  // previous one, so that static holds reuse the last screenshot.
  window.__tvSeek = (t, prev) => {
    let changed = prev === null;
    for (const animation of document.getAnimations()) {
      animation.pause();
      animation.currentTime = t * 1000;
      const { delay, activeDuration } = animation.effect.getComputedTiming();
      if (delay + activeDuration > prev * 1000 && delay <= t * 1000) changed = true;
    }
    if (typeof window.renderAt === "function" && window.renderAt(t, beats) !== false) changed = true;
    return changed;
  };
}
"""


class ScenePlayer:
    """One Chromium page that loads scenes and seeks them to a time."""

    def __init__(self, browser):
        self.page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        self.scene_id = ""
        self.page.on("pageerror", lambda error: self._warn(f"JS error: {error}"))
        self.page.on("console", lambda message: message.type == "error" and self._warn(f"console: {message.text}"))
        self.page.on("requestfailed", lambda request: self._warn(f"failed to load {request.url}"))

    def _warn(self, message: str) -> None:
        print(f"  WARNING in scene {self.scene_id}: {message}", file=sys.stderr, flush=True)

    def load(self, timed_scene: TimedScene) -> None:
        self.scene_id = timed_scene.scene.id
        self.page.goto(timed_scene.scene.html.as_uri(), wait_until="load")
        self.page.evaluate(PREPARE_SCENE_JS, timed_scene.beat_offsets())

    def seek(self, t: float, prev: float | None) -> bool:
        return self.page.evaluate("([t, prev]) => window.__tvSeek(t, prev)", [t, prev])


def launch_chromium(playwright):
    try:
        # One renderer process and no background services: the render opens a single page at a time,
        # so extra Chromium processes only add resident memory.
        return playwright.chromium.launch(args=["--renderer-process-limit=1", "--disable-extensions",
                                                "--disable-background-networking", "--disable-component-update"])
    except Exception as error:  # Playwright raises its generic Error when the browser is missing
        raise RenderError(f"cannot start Chromium ({error}); run: python -m playwright install chromium") from error


def preview_key(timed_scene: TimedScene, fps: int, build: Path) -> str:
    """Hash of everything that can change a scene's preview stills."""
    digest = hashlib.sha256()
    timing = [timed_scene.beat_offsets(), timed_scene.end - timed_scene.start, fps, WIDTH, HEIGHT, PREPARE_SCENE_JS]
    digest.update(json.dumps(timing).encode("utf-8"))
    digest.update(timed_scene.scene.html.read_bytes())
    folder = timed_scene.scene.html.parent
    # Other HTML files are other scenes; everything else (theme.css, images) may be used by this one.
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() not in (".html", ".htm") and build not in path.parents:
            digest.update(path.relative_to(folder).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def shoot_scene(player: ScenePlayer, timed_scene: TimedScene, fps: int, folder: Path) -> None:
    player.load(timed_scene)
    ends = timed_scene.beat_offsets()[1:] + [timed_scene.end - timed_scene.start]
    for index, end in enumerate(ends):
        # The last frame before the next beat shows everything this beat added.
        player.seek(max(0.0, end - 1 / fps), None)
        player.page.screenshot(path=str(folder / f"{index:02}.png"))


def render_preview(timed_scenes: list[TimedScene], fps: int, build: Path) -> None:
    from playwright.sync_api import sync_playwright

    preview = build / "preview"
    cache = preview / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    for old in preview.glob("*.png"):
        old.unlink()
    still = 0
    with contextlib.ExitStack() as stack:
        player = None  # Chromium starts only when a scene is not in the cache.
        for timed_scene in timed_scenes:
            scene_id = timed_scene.scene.id
            folder = cache / f"{scene_id}-{preview_key(timed_scene, fps, build)}"
            if folder.is_dir():
                print(f"  {scene_id}: unchanged, reusing cached stills", flush=True)
            else:
                if player is None:
                    playwright = stack.enter_context(sync_playwright())
                    browser = launch_chromium(playwright)
                    stack.callback(browser.close)
                    player = ScenePlayer(browser)
                # Shoot into a temporary folder so an interrupted run never leaves a partial cache entry.
                partial = folder.with_name(folder.name + ".partial")
                shutil.rmtree(partial, ignore_errors=True)
                partial.mkdir()
                shoot_scene(player, timed_scene, fps, partial)
                partial.rename(folder)
            for index in range(len(timed_scene.beats)):
                still += 1
                shutil.copyfile(folder / f"{index:02}.png", preview / f"{still:04}.png")
                print(f"  {still:04}.png  {scene_id} beat {index}", flush=True)
    run_ffmpeg("-framerate", "1", "-i", str(preview / "%04d.png"),
               "-vf", f"scale=640:360,tile={PREVIEW_SHEET_TILES}:padding=8:margin=8:color=gray",
               str(preview / "sheet-%02d.png"))
    print(f"preview stills and contact sheets (9 beats each, in storyboard order): {preview}")


def render_video(timed_scenes: list[TimedScene], storyboard: Storyboard, root: Path, burn_captions: bool) -> None:
    from playwright.sync_api import sync_playwright

    command = ["ffmpeg", "-v", "error", "-y",
               "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(storyboard.fps), "-i", "-",
               "-i", "build/narration.wav"]
    if burn_captions:
        # Relative path: the subtitles filter cannot parse Windows drive letters without heavy escaping.
        command += ["-vf", f"subtitles=captions.srt:force_style='{CAPTION_STYLE}'", "-map", "0:v", "-map", "1:a"]
    else:
        command += ["-i", "captions.srt", "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:s", "mov_text"]
    command += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                # x264 defaults to ~1.5 frame threads per CPU, each holding its own 1080p frames; frames arrive
                # at about real time, so 6 threads keep up with far less memory.
                "-threads", "6",
                "-c:a", "aac", "-b:a", "160k", "-metadata", f"title={storyboard.title}",
                "-movflags", "+faststart", "video.mp4"]
    log_path = root / "build" / "ffmpeg.log"
    with log_path.open("wb") as log:
        encoder = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE, stderr=log)
        try:
            with sync_playwright() as playwright:
                browser = launch_chromium(playwright)
                try:
                    player = ScenePlayer(browser)
                    for number, timed_scene in enumerate(timed_scenes, 1):
                        player.load(timed_scene)
                        first, last = round(timed_scene.start * storyboard.fps), round(timed_scene.end * storyboard.fps)
                        frame, prev, captured = b"", None, 0
                        for index in range(first, last):
                            t = max(0.0, index / storyboard.fps - timed_scene.start)
                            if player.seek(t, prev) or not frame:
                                frame = player.page.screenshot(type="jpeg", quality=95)
                                captured += 1
                            encoder.stdin.write(frame)
                            prev = t
                        print(f"rendered {number}/{len(timed_scenes)} {timed_scene.scene.id}: "
                              f"{last - first} frames, {captured} captured", flush=True)
                finally:
                    browser.close()
        except BrokenPipeError as error:
            encoder.wait()
            raise RenderError(f"ffmpeg stopped early:\n{log_path.read_text(errors='replace')}") from error
        finally:
            if not encoder.stdin.closed:
                encoder.stdin.close()
        if encoder.wait() != 0:
            raise RenderError(f"ffmpeg failed:\n{log_path.read_text(errors='replace')}")


# ---------------------------------------------------------------------- main

FFMPEG_INSTALL = "winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg"
OPTIONAL_TOOLS = (("manim",), ("pdflatex", "latex"), ("magick",), ("inkscape",), ("mmdc",), ("node",))


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool
    install: str = ""


def _version_line(path: str, flag: str) -> str:
    result = subprocess.run([path, flag], capture_output=True, text=True)
    lines = (result.stdout or result.stderr).strip().splitlines()
    return lines[0] if lines else "found"


def check_binary(name: str) -> Check:
    path = shutil.which(name)
    if path is None:
        return Check(name, False, "missing", True, FFMPEG_INSTALL)
    return Check(name, True, _version_line(path, "-version"), True)


def check_playwright() -> list[Check]:
    pip = f"{sys.executable} -m pip install playwright"
    chromium_install = f"{sys.executable} -m playwright install chromium"
    try:
        from importlib.metadata import version
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [Check("playwright", False, "missing", True, pip),
                Check("chromium", False, "not checked (Playwright is missing)", True, chromium_install)]
    package = Check("playwright", True, version("playwright"), True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            browser_version = browser.version
            browser.close()
    except Exception as error:  # Playwright raises its generic Error when the browser is missing
        return [package, Check("chromium", False, f"does not launch ({str(error).splitlines()[0]})", True, chromium_install)]
    return [package, Check("chromium", True, f"launches ({browser_version})", True)]


def check_edge_tts(language: str) -> Check:
    try:
        from importlib.metadata import version
        import edge_tts
    except ImportError:
        return Check("edge-tts", False, "missing", True, f"{sys.executable} -m pip install edge-tts")
    package = version("edge-tts")
    try:
        manager = asyncio.run(edge_tts.VoicesManager.create())
    except Exception as error:  # edge-tts surfaces network failures as aiohttp and OS errors
        return Check("edge-tts", True, f"{package}; voices not checked (network error: {error.__class__.__name__})", True)
    voices = manager.find(Language=language)
    return Check("edge-tts", True, f"{package}; {len(voices)} voices for language {language!r}", True)


def check_sapi() -> list[Check]:
    if sys.platform != "win32":
        return []
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
               "Add-Type -AssemblyName System.Speech; "
               "(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | "
               "ForEach-Object { $_.VoiceInfo.Name }"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return [Check("sapi voices", False, f"not listed ({result.stderr.strip()})", False)]
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [Check("sapi voices", bool(names), ", ".join(names) or "none installed", False)]


def check_optional() -> list[Check]:
    checks = []
    for names in OPTIONAL_TOOLS:
        found = next((path for path in map(shutil.which, names) if path), None)
        label = " or ".join(names)
        checks.append(Check(label, found is not None, f"found ({found})" if found else "not found", False))
    return checks


def report_checks(language: str) -> list[Check]:
    """Prints one line per tool and returns the required tools that are missing."""
    python_ok = sys.version_info >= (3, 9)
    checks = [Check("python", python_ok, f"{sys.version.split()[0]} ({sys.executable})", True,
                    "" if python_ok else "install Python 3.9 or newer"),
              check_binary("ffmpeg"), check_binary("ffprobe"),
              *check_playwright(), check_edge_tts(language), *check_sapi(), *check_optional()]
    for check in checks:
        status = "ok" if check.ok else ("MISSING" if check.required else "--")
        print(f"{status:8} {check.name:18} {check.detail}")
    return [check for check in checks if check.required and not check.ok]


def ffmpeg_install_command() -> list[str] | None:
    """The OS package manager command for ffmpeg (which includes ffprobe), or None when none is on PATH."""
    if sys.platform == "win32" and shutil.which("winget"):
        return ["winget", "install", "--id", "Gyan.FFmpeg", "-e"]
    if sys.platform == "darwin" and shutil.which("brew"):
        return ["brew", "install", "ffmpeg"]
    if sys.platform.startswith("linux") and shutil.which("apt-get"):
        return ["sudo", "apt-get", "install", "-y", "ffmpeg"]
    return None


def install_missing(missing: list[Check]) -> bool:
    """Runs the install command of each missing tool; returns False when one fails."""
    names = {check.name for check in missing}
    commands = [[sys.executable, "-m", "pip", "install", package]
                for package in ("playwright", "edge-tts") if package in names]
    # Chromium is installed by Playwright, so it comes after the Playwright package.
    if "chromium" in names:
        commands.append([sys.executable, "-m", "playwright", "install", "chromium"])
    if names & {"ffmpeg", "ffprobe"}:
        ffmpeg_command = ffmpeg_install_command()
        if ffmpeg_command is None:
            print(f"doctor: no supported package manager found; install ffmpeg manually: {FFMPEG_INSTALL}")
        else:
            commands.append(ffmpeg_command)
    if "python" in names:
        print("doctor: install Python 3.9 or newer manually")
    for command in commands:
        print(f"doctor: running {subprocess.list2cmdline(command)}", flush=True)
        result = subprocess.run(command)
        if result.returncode != 0:
            print(f"doctor: install failed (exit code {result.returncode}): {subprocess.list2cmdline(command)}")
            return False
    return True


def run_doctor(language: str, install: bool = False) -> int:
    """Prints one line per tool and returns the exit code: 0 when rendering can run.

    With install, installs the missing required tools and checks again."""
    missing = report_checks(language)
    if missing and install:
        if not install_missing(missing):
            return 1
        # Packages installed during this run must be importable by the second check.
        importlib.invalidate_caches()
        print("doctor: checking again")
        missing = report_checks(language)
    if not missing:
        print("doctor: every required tool is present")
        return 0
    print("doctor: required tools are missing; install them with:")
    for check in missing:
        print(f"  {check.name}: {check.install}")
    return 1



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a teaching video from a storyboard JSON file.")
    parser.add_argument("storyboard", type=Path, nargs="?", help="storyboard.json; all output goes next to it")
    parser.add_argument("--doctor", action="store_true", help="report which tools are installed, then exit (no storyboard needed)")
    parser.add_argument("--language", default="en", help="with --doctor: language code whose edge voices are counted (default en)")
    parser.add_argument("--install", action="store_true", help="with --doctor: install the missing required tools, then check again")
    parser.add_argument("--preview", action="store_true", help="write one still per beat and contact sheets, no video")
    parser.add_argument("--burn-captions", action="store_true", help="burn captions into the picture (always on with tts none)")
    parser.add_argument("--tts", choices=TTS_BACKENDS, help="override the storyboard's tts backend")
    parser.add_argument("--voice", help="override the storyboard's voice")
    parser.add_argument("--rate", help='override the storyboard\'s edge speaking rate, e.g. "-10%%"')
    args = parser.parse_args()
    if args.storyboard is None and not args.doctor:
        parser.error("the storyboard argument is required (or use --doctor)")
    if args.install and not args.doctor:
        parser.error("--install works only together with --doctor")
    return args


def main() -> None:
    args = parse_args()
    if args.doctor:
        sys.exit(run_doctor(args.language, args.install))
    root = args.storyboard.resolve().parent
    try:
        storyboard = load_storyboard(args.storyboard.resolve())
    except (OSError, StoryboardError) as error:
        sys.exit(f"storyboard error: {error}")
    if args.tts and args.tts != storyboard.tts:
        # The storyboard's voice belongs to its own backend.
        storyboard = dataclasses.replace(storyboard, tts=args.tts, voice=DEFAULT_VOICE[args.tts])
    if args.voice:
        storyboard = dataclasses.replace(storyboard, voice=args.voice)
    if args.rate:
        storyboard = dataclasses.replace(storyboard, rate=args.rate)
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg is not on PATH (winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg)")
    try:
        import playwright  # noqa: F401  (checked here so the error comes before narration starts)
    except ImportError:
        sys.exit(f"Playwright is missing: {sys.executable} -m pip install playwright, then {sys.executable} -m playwright install chromium")

    print(f"narration: {storyboard.tts}, voice {storyboard.voice or 'system default'}", flush=True)
    build = root / "build"
    (build / "tts").mkdir(parents=True, exist_ok=True)
    try:
        narrator = Narrator(storyboard.tts, storyboard.voice, storyboard.rate, build / "tts")
        timed_scenes, track = build_timeline(storyboard, narrator)
        write_wav(build / "narration.wav", track)
        all_beats = [beat for timed_scene in timed_scenes for beat in timed_scene.beats]
        write_srt(root / "captions.srt", all_beats)
        timeline = [
            {"id": ts.scene.id, "start": round(ts.start, 3), "end": round(ts.end, 3),
             "beats": [{"start": round(b.start, 3), "end": round(b.end, 3), "say": b.text} for b in ts.beats]}
            for ts in timed_scenes
        ]
        (build / "timeline.json").write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")
        duration = timed_scenes[-1].end
        if args.preview:
            render_preview(timed_scenes, storyboard.fps, build)
        else:
            render_video(timed_scenes, storyboard, root, args.burn_captions or storyboard.tts == "none")
            print(f"video: {root / 'video.mp4'} ({duration:.1f} s, {len(all_beats)} beats, {len(timed_scenes)} scenes)")
    except RenderError as error:
        sys.exit(f"error: {error}")


if __name__ == "__main__":
    main()
