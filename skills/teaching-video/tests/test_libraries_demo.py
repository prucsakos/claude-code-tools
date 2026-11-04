"""Renders the animation libraries demo (examples/libraries) in preview mode. Needs the jsdelivr CDN."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEMO = SKILL_DIR / "examples" / "libraries"


def library_urls() -> list[str]:
    return sorted({url for scene in (DEMO / "scenes").glob("*.html")
                   for url in re.findall(r'<script src="(https://[^"]+)"', scene.read_text(encoding="utf-8"))})


def unreachable_url() -> str | None:
    for url in library_urls():
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                response.read(1)
        except OSError:
            return url
    return None


class LibrariesDemoTest(unittest.TestCase):
    def test_preview_seeks_each_library_per_beat(self):
        missing = unreachable_url()
        if missing:
            self.skipTest(f"CDN unreachable, cannot load {missing}")
        with tempfile.TemporaryDirectory() as tmp:
            # Render a copy to keep build/ out of the repository; the scenes link ../../../theme.css.
            root = Path(tmp)
            shutil.copy(SKILL_DIR / "theme.css", root / "theme.css")
            demo = root / "examples" / "libraries"
            shutil.copytree(DEMO, demo, ignore=shutil.ignore_patterns("build"))

            result = subprocess.run(
                [sys.executable, str(SKILL_DIR / "make_video.py"), str(demo / "storyboard.json"), "--preview"],
                capture_output=True, text=True, timeout=180,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("WARNING", result.stderr)
            stills = sorted((demo / "build" / "preview").glob("0*.png"))
            self.assertEqual(len(stills), 6)
            # Two beats per scene: the second still of a scene must differ from the first.
            for first, second in zip(stills[0::2], stills[1::2]):
                self.assertNotEqual(first.read_bytes(), second.read_bytes(), f"{first.name} equals {second.name}")


if __name__ == "__main__":
    unittest.main()
