import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import make_video  # noqa: E402


def run_scaffold(storyboard: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SKILL_DIR / "make_video.py"), str(storyboard), "--scaffold"],
                          capture_output=True, text=True, timeout=60)


class ScaffoldTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.storyboard = self.root / "storyboard.json"
        self.storyboard.write_text(json.dumps({
            "tts": "none",
            "scenes": [
                {"id": "intro", "html": "scenes/01-intro.html", "beats": [
                    {"say": "First beat.", "show": "a < b & c"},
                    {"say": "Second beat has no show text."},
                ]},
                {"id": "next", "html": "scenes/02-next.html", "beats": [{"say": "Third beat.", "show": "done"}]},
            ],
        }), encoding="utf-8")
        self.scenes = self.root / "scenes"

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_scenes_and_theme(self):
        result = run_scaffold(self.storyboard)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.scenes / "02-next.html").is_file())
        self.assertEqual((self.scenes / "theme.css").read_bytes(), (SKILL_DIR / "theme.css").read_bytes())
        intro = (self.scenes / "01-intro.html").read_text(encoding="utf-8")
        self.assertIn("--at: var(--b0)", intro)
        self.assertIn("--at: var(--b1)", intro)
        self.assertIn("a &lt; b &amp; c", intro)
        self.assertIn("Second beat has no show text.", intro)
        # The scaffolded storyboard now loads for render and preview, which require the scene files.
        self.assertEqual(make_video.load_storyboard(self.storyboard).scenes[0].beats[0].show, "a < b & c")

    def test_never_overwrites(self):
        self.assertEqual(run_scaffold(self.storyboard).returncode, 0)
        edited = self.scenes / "01-intro.html"
        edited.write_bytes(b"<p>hand edited</p>\n")
        result = run_scaffold(self.storyboard)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(edited.read_bytes(), b"<p>hand edited</p>\n")
        self.assertIn("skipped intro", result.stdout)

    def test_missing_scene_still_fails_without_scaffold(self):
        with self.assertRaises(make_video.StoryboardError):
            make_video.load_storyboard(self.storyboard)


if __name__ == "__main__":
    unittest.main()
