"""Preview cache: unchanged clean scenes are reused, scenes that printed warnings are shot again.

Run: python -m unittest discover -s skills/teaching-video/tests
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent

SCENE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><link rel="stylesheet" href="theme.css"></head>
<body>
  <main class="stage"><h1 class="in" style="--at: var(--b0)">{title}</h1></main>
  {script}
</body>
</html>
"""


class PreviewCacheTest(unittest.TestCase):
    def setUp(self):
        self.project = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.project)
        scenes = self.project / "scenes"
        scenes.mkdir()
        shutil.copy(SKILL / "theme.css", scenes / "theme.css")
        (scenes / "clean.html").write_text(SCENE.format(title="Clean", script=""), encoding="utf-8")
        (scenes / "broken.html").write_text(
            SCENE.format(title="Broken", script='<script>throw new Error("preview-cache-test-error")</script>'),
            encoding="utf-8")
        storyboard = {
            "title": "Preview cache test",
            "tts": "none",
            "scenes": [
                {"id": "clean", "html": "scenes/clean.html", "beats": [{"say": "A clean scene."}]},
                {"id": "broken", "html": "scenes/broken.html", "beats": [{"say": "A scene that throws."}]},
            ],
        }
        (self.project / "storyboard.json").write_text(json.dumps(storyboard), encoding="utf-8")

    def preview(self) -> str:
        result = subprocess.run(
            [sys.executable, str(SKILL / "make_video.py"), str(self.project / "storyboard.json"), "--preview"],
            capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_second_preview_reuses_clean_scene_and_reshoots_warning_scene(self):
        first = self.preview()
        self.assertIn("preview-cache-test-error", first)

        second = self.preview()
        self.assertIn("clean: unchanged, reusing cached stills", second)
        self.assertNotIn("broken: unchanged", second)
        self.assertIn("preview-cache-test-error", second)
        self.assertEqual(len(list((self.project / "build" / "preview").glob("[0-9][0-9][0-9][0-9].png"))), 2)


if __name__ == "__main__":
    unittest.main()
