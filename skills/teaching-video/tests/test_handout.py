"""The --handout study notes: the HTML writer and the command-line run."""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import make_video  # noqa: E402

SCENE_HTML = "<!doctype html><html><body style='background:#fff'><h1>Scene</h1></body></html>"


def write_project(root: Path) -> Path:
    for name in ("one", "two"):
        (root / f"{name}.html").write_text(SCENE_HTML, encoding="utf-8")
    storyboard = {
        "title": "Handout test",
        "tts": "none",
        "scenes": [
            {"id": "one", "html": "one.html", "beats": [{"say": "First we see a < b."}]},
            {"id": "two", "html": "two.html", "beats": [{"say": "Then b > c."}, {"say": "Done & dusted."}]},
        ],
    }
    path = root / "sb.json"
    path.write_text(json.dumps(storyboard), encoding="utf-8")
    return path


class WriteHandoutTest(unittest.TestCase):
    def test_two_scenes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build" / "handout").mkdir(parents=True)
            for name in ("one", "two"):
                (root / "build" / "handout" / f"{name}.png").write_bytes(b"png")
            scene = lambda scene_id: make_video.Scene(id=scene_id, html=root / "x.html", beats=[], lead=0, tail=0)
            timed_scenes = [
                make_video.TimedScene(scene=scene("one"), start=0.0, end=65.0,
                                      beats=[make_video.TimedBeat(text="a < b", start=0.0, end=2.0)]),
                make_video.TimedScene(scene=scene("two"), start=65.0, end=70.0,
                                      beats=[make_video.TimedBeat(text="x & y", start=65.0, end=67.0),
                                             make_video.TimedBeat(text="done", start=67.0, end=70.0)]),
            ]

            make_video.write_handout(root / "handout.html", "T", timed_scenes)

            page = (root / "handout.html").read_text(encoding="utf-8")
            self.assertIn("0:00", page)
            self.assertIn("1:05", page)
            self.assertIn("<p>a &lt; b</p>", page)
            self.assertIn("<p>x &amp; y</p>", page)
            self.assertIn("<p>done</p>", page)
            sources = re.findall(r'<img src="([^"]+)"', page)
            self.assertEqual(len(sources), 2)
            for source in sources:
                self.assertTrue((root / source).is_file(), source)


class HandoutCommandTest(unittest.TestCase):
    def run_make_video(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SKILL_DIR / "make_video.py"), *args],
                              capture_output=True, text=True, timeout=180)

    def test_handout_with_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storyboard = write_project(root)

            result = self.run_make_video(str(storyboard), "--handout", "--preview")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "handout.html").is_file())
            stills = sorted((root / "build" / "handout").glob("*.png"))
            self.assertEqual([still.name for still in stills], ["one.png", "two.png"])
            for still in stills:
                self.assertGreater(still.stat().st_size, 0)
            self.assertEqual(len(list((root / "build" / "preview").glob("0*.png"))), 3)

    def test_no_handout_without_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storyboard = write_project(root)

            result = self.run_make_video(str(storyboard), "--preview")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / "handout.html").exists())
            self.assertFalse((root / "build" / "handout").exists())


if __name__ == "__main__":
    unittest.main()
