"""Renders the animations demo (examples/animations) in preview mode."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


class AnimationsDemoTest(unittest.TestCase):
    def test_preview_renders_without_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            # The renderer writes build/ next to the storyboard, so render a copy to keep the repository clean.
            # The scenes link ../../../theme.css, so the copy keeps the same layout.
            root = Path(tmp)
            shutil.copy(SKILL_DIR / "theme.css", root / "theme.css")
            demo = root / "examples" / "animations"
            shutil.copytree(SKILL_DIR / "examples" / "animations", demo, ignore=shutil.ignore_patterns("build"))

            result = subprocess.run(
                [sys.executable, str(SKILL_DIR / "make_video.py"), str(demo / "storyboard.json"), "--preview"],
                capture_output=True, text=True, timeout=180,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("WARNING", result.stderr)
            self.assertEqual(len(list((demo / "build" / "preview").glob("0*.png"))), 9)


if __name__ == "__main__":
    unittest.main()
