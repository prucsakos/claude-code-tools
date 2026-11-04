"""--handout with --scenes or --translation: the handout gets the render's own names, so the full handout survives."""

import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402


class HandoutOutputPathsTest(unittest.TestCase):
    def test_full_render_keeps_its_names(self):
        self.assertEqual(make_video.FULL_OUTPUTS.handout, "handout.html")
        self.assertEqual(make_video.FULL_OUTPUTS.handout_stills, "build/handout")

    def test_cut_and_translation_get_distinct_names(self):
        cut = make_video.output_paths(cut=True)
        german = make_video.output_paths(cut=False, language="de")
        self.assertEqual((cut.handout, cut.handout_stills), ("handout.cut.html", "build/handout.cut"))
        self.assertEqual((german.handout, german.handout_stills), ("handout.de.html", "build/handout.de"))


class CutHandoutTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "scene.html").write_text("<html><body>scene</body></html>", encoding="utf-8")
        self.storyboard_path = self.root / "storyboard.json"
        self.storyboard_path.write_text(json.dumps({"tts": "none", "scenes": [
            {"id": "intro", "html": "scene.html", "beats": [{"say": "Hello there, learner."}]},
            {"id": "recap", "html": "scene.html", "beats": [{"say": "That was the recap."}]}]}), encoding="utf-8")
        self.patch("make_video.render_video")
        self.patch("make_video.shutil.which", return_value="ffmpeg")
        # A fake browser: the real render_handout_stills runs and its screenshots land where it points them.
        sync_api = types.ModuleType("playwright.sync_api")
        sync_api.sync_playwright = lambda: contextlib.nullcontext(object())
        patcher = mock.patch.dict(sys.modules, {"playwright": types.ModuleType("playwright"),
                                                "playwright.sync_api": sync_api})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.patch("make_video.launch_chromium")
        player = self.patch("make_video.ScenePlayer").return_value
        player.page.screenshot.side_effect = lambda path: Path(path).write_bytes(b"png")

    def patch(self, target, **kwargs):
        patcher = mock.patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_cut_handout_has_its_own_page_and_stills_and_leaves_the_full_handout(self):
        full_handout = self.root / "handout.html"
        full_handout.write_text("full handout", encoding="utf-8")
        argv = ["make_video.py", str(self.storyboard_path), "--scenes", "recap", "--handout"]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            make_video.main()

        page = (self.root / "handout.cut.html").read_text(encoding="utf-8")
        self.assertIn('<img src="build/handout.cut/recap.png"', page)
        self.assertTrue((self.root / "build" / "handout.cut" / "recap.png").is_file())
        self.assertFalse((self.root / "build" / "handout").exists())
        self.assertEqual(full_handout.read_text(encoding="utf-8"), "full handout")


if __name__ == "__main__":
    unittest.main()
