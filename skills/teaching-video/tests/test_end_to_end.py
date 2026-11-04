"""End-to-end runs of make_video.main() on a one-scene storyboard without narration."""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import make_video  # noqa: E402

FPS = 24
SCENE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><link rel="stylesheet" href="theme.css"></head>
<body>
  <h1 style="animation: tv-rise 0.3s var(--b0) both">First</h1>
  <p style="animation: tv-rise 0.3s var(--b1) both">Second</p>
  <style>@keyframes tv-rise { from { opacity: 0 } to { opacity: 1 } }</style>
</body></html>
"""
STORYBOARD = {
    "tts": "none",
    "fps": FPS,
    "scenes": [{
        "id": "s1",
        "html": "scene.html",
        "lead": 0.1,
        "tail": 0.1,
        "beats": [{"say": "One two three.", "pause": 0.1}, {"say": "Four five six seven.", "pause": 0.1}],
    }],
}


def run_main(*argv: str) -> None:
    with mock.patch.object(sys, "argv", ["make_video.py", *argv]), contextlib.redirect_stdout(io.StringIO()):
        make_video.main()


def ffprobe_durations(video: Path) -> dict[str, float]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    )
    return {stream["codec_type"]: float(stream["duration"]) for stream in json.loads(result.stdout)["streams"]}


class EndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        shutil.copy(SKILL_DIR / "theme.css", cls.root / "theme.css")
        (cls.root / "scene.html").write_text(SCENE_HTML, encoding="utf-8")
        cls.storyboard = cls.root / "storyboard.json"
        cls.storyboard.write_text(json.dumps(STORYBOARD), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def timeline_end(self) -> float:
        timeline = json.loads((self.root / "build" / "timeline.json").read_text(encoding="utf-8"))
        return timeline[-1]["end"]

    def test_preview_writes_one_still_per_beat_narration_and_captions(self):
        run_main(str(self.storyboard), "--preview")

        preview = self.root / "build" / "preview"
        self.assertTrue((preview / "0001.png").is_file())
        self.assertTrue((preview / "0002.png").is_file())
        self.assertFalse((preview / "0003.png").exists())
        self.assertTrue((preview / "sheet-01.png").is_file())

        with wave.open(str(self.root / "build" / "narration.wav"), "rb") as narration:
            frames = narration.getnframes()
            self.assertEqual(narration.getframerate(), make_video.SAMPLE_RATE)
        duration = frames / make_video.SAMPLE_RATE
        self.assertAlmostEqual(duration, self.timeline_end(), places=3)
        self.assertEqual(frames % (make_video.SAMPLE_RATE // FPS), 0)

        cues = (self.root / "captions.srt").read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(len(cues), 2)
        self.assertTrue(cues[0].split("\n")[1].startswith("00:00:00,100 --> "))
        self.assertEqual(cues[1].split("\n")[2], "Four five six seven.")

    def test_video_has_video_and_audio_streams_as_long_as_the_timeline(self):
        run_main(str(self.storyboard))

        video = self.root / "video.mp4"
        self.assertTrue(video.is_file())
        durations = ffprobe_durations(video)
        end = self.timeline_end()
        self.assertAlmostEqual(durations["video"], end, delta=0.1)
        self.assertAlmostEqual(durations["audio"], end, delta=0.1)


if __name__ == "__main__":
    unittest.main()
