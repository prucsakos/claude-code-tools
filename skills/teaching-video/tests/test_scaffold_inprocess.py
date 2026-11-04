"""In-process scaffold tests, so coverage traces scaffold_scene, scaffold and main's --scaffold branch."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import make_video  # noqa: E402


class ScaffoldInProcessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.storyboard_path = self.root / "storyboard.json"
        self.scenes = self.root / "scenes"
        self.write_storyboard("scenes/02-next.html")

    def tearDown(self):
        self.tmp.cleanup()

    def write_storyboard(self, second_html: str):
        self.storyboard_path.write_text(json.dumps({
            "tts": "none",
            "scenes": [
                {"id": "intro", "html": "scenes/01-intro.html", "beats": [
                    {"say": "First beat.", "show": "a < b & c"},
                    {"say": "Second beat has no show text."},
                ]},
                {"id": "next", "html": second_html, "beats": [{"say": "Third beat.", "show": "done"}]},
            ],
        }), encoding="utf-8")

    def run_scaffold(self) -> str:
        storyboard = make_video.load_storyboard(self.storyboard_path, require_html=False)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            make_video.scaffold(storyboard, self.root)
        return output.getvalue()

    def run_main(self) -> str:
        output = io.StringIO()
        argv = ["make_video.py", str(self.storyboard_path), "--scaffold"]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
            make_video.main()
        return output.getvalue()

    def main_exit_message(self) -> str:
        with self.assertRaises(SystemExit) as caught:
            self.run_main()
        return str(caught.exception.code)

    def test_scaffold_writes_pages_and_theme(self):
        printed = self.run_scaffold()
        intro = (self.scenes / "01-intro.html").read_text(encoding="utf-8")
        self.assertIn('<p class="in rise" style="--at: var(--b0)">a &lt; b &amp; c</p>', intro)
        self.assertIn('<p class="in rise" style="--at: var(--b1)">Second beat has no show text.</p>', intro)
        self.assertIn("<title>intro</title>", intro)
        self.assertIn('<p class="in rise" style="--at: var(--b0)">done</p>',
                      (self.scenes / "02-next.html").read_text(encoding="utf-8"))
        self.assertEqual((self.scenes / "theme.css").read_bytes(), (SKILL_DIR / "theme.css").read_bytes())
        self.assertIn(f"created {self.scenes / 'theme.css'}", printed)
        self.assertIn(f"created intro: {self.scenes / '01-intro.html'}", printed)
        self.assertIn(f"created next: {self.scenes / '02-next.html'}", printed)

    def test_scaffold_keeps_existing_page(self):
        self.scenes.mkdir()
        existing = self.scenes / "01-intro.html"
        existing.write_bytes(b"<p>hand edited</p>\n")
        printed = self.run_scaffold()
        self.assertEqual(existing.read_bytes(), b"<p>hand edited</p>\n")
        self.assertIn(f"skipped intro: {existing} exists", printed)
        self.assertTrue((self.scenes / "02-next.html").is_file())

    def assert_scaffold_rejects(self, bad_html: str):
        self.write_storyboard(bad_html)
        with self.assertRaises(make_video.StoryboardError) as caught:
            self.run_scaffold()
        self.assertIn("scene next: html must be an .html or .htm file inside", str(caught.exception))
        # All scenes are checked before any write, so the valid first scene is not written either.
        self.assertFalse(self.scenes.exists())

    def test_scaffold_rejects_path_outside_folder(self):
        self.assert_scaffold_rejects("../escaped.html")
        self.assertFalse((self.root.parent / "escaped.html").exists())

    def test_scaffold_rejects_non_html_file(self):
        self.assert_scaffold_rejects("scenes/notes.txt")

    def test_main_scaffold_returns_after_writing(self):
        printed = self.run_main()
        self.assertTrue((self.scenes / "01-intro.html").is_file())
        self.assertTrue((self.scenes / "02-next.html").is_file())
        self.assertIn("created intro:", printed)

    def test_main_scaffold_exits_on_invalid_storyboard(self):
        self.storyboard_path.write_text(json.dumps({"tts": "bogus", "scenes": []}), encoding="utf-8")
        message = self.main_exit_message()
        self.assertTrue(message.startswith("storyboard error: tts must be one of"), message)
        self.assertFalse(self.scenes.exists())

    def test_main_scaffold_exits_on_path_outside_folder(self):
        self.write_storyboard("../escaped.html")
        message = self.main_exit_message()
        self.assertTrue(message.startswith("storyboard error: scene next: html must be an .html or .htm file inside"), message)
        self.assertFalse(self.scenes.exists())

    def test_main_scaffold_exits_on_write_failure(self):
        with mock.patch.object(make_video.Path, "write_text", side_effect=OSError("disk full")):
            message = self.main_exit_message()
        self.assertEqual(message, "scaffold error: disk full")
        self.assertFalse((self.scenes / "01-intro.html").exists())


if __name__ == "__main__":
    unittest.main()
