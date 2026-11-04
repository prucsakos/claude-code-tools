"""Renders the teaching components demo (examples/components) in preview mode."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# Beats per scene of examples/components/storyboard.json, in storyboard order.
SCENE_BEATS = {"steps": 3, "code-highlight": 3, "compare": 2}


class ComponentsDemoTest(unittest.TestCase):
    def test_preview_shows_each_beat_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            # The renderer writes build/ next to the storyboard, so render a copy to keep the repository clean.
            # The scenes link ../../../theme.css, so the copy keeps the same layout.
            root = Path(tmp)
            shutil.copy(SKILL_DIR / "theme.css", root / "theme.css")
            demo = root / "examples" / "components"
            shutil.copytree(SKILL_DIR / "examples" / "components", demo, ignore=shutil.ignore_patterns("build"))

            result = subprocess.run(
                [sys.executable, str(SKILL_DIR / "make_video.py"), str(demo / "storyboard.json"), "--preview"],
                capture_output=True, text=True, timeout=180,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("WARNING", result.stderr)
            stills = sorted((demo / "build" / "preview").glob("0*.png"))
            self.assertEqual(len(stills), sum(SCENE_BEATS.values()))

            # Each beat activates a new step, moves the highlight or fills in a side, so its still must differ.
            first = 0
            for scene_id, beats in SCENE_BEATS.items():
                scene_stills = [still.read_bytes() for still in stills[first:first + beats]]
                for beat in range(1, beats):
                    with self.subTest(scene=scene_id, beat=beat):
                        self.assertNotEqual(scene_stills[beat - 1], scene_stills[beat])
                first += beats


if __name__ == "__main__":
    unittest.main()
