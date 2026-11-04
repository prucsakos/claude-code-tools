"""Chapter markers: one chapter per scene in video.mp4, and chapters.txt for a YouTube description."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import make_video  # noqa: E402

SCENE_HTML = """<!doctype html>
<html><head><link rel="stylesheet" href="../theme.css"></head>
<body><main class="stage"><h1>{text}</h1></main></body></html>
"""


def timed_scene(scene_id: str, title: str, start: float, end: float) -> make_video.TimedScene:
    scene = make_video.Scene(id=scene_id, title=title, html=Path("unused.html"), beats=[], lead=0, tail=0)
    return make_video.TimedScene(scene=scene, start=start, end=end, beats=[])


class ChapterTextTest(unittest.TestCase):
    def test_lines_use_mss_and_hmmss_from_one_hour(self):
        scenes = [timed_scene("hook", "Hook", 0.0, 65.4), timed_scene("example", "Example", 65.4, 3725.9),
                  timed_scene("recap", "", 3725.9, 3800.0)]

        self.assertEqual(make_video.chapters_text(scenes), "0:00 Hook\n1:05 Example\n1:02:05 recap\n")


class ChapterRenderTest(unittest.TestCase):
    def test_video_has_one_chapter_per_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "theme.css").write_text((SKILL_DIR / "theme.css").read_text(encoding="utf-8"), encoding="utf-8")
            project = root / "project"
            (project / "scenes").mkdir(parents=True)
            for name in ("one", "two"):
                (project / "scenes" / f"{name}.html").write_text(
                    SCENE_HTML.replace("../theme.css", "../../theme.css").format(text=name), encoding="utf-8")
            storyboard = {
                "title": "Chapter test",
                "tts": "none",
                "fps": 24,
                "scenes": [
                    {"id": "hook", "title": "The hook", "html": "scenes/one.html", "lead": 0.1, "tail": 0.1,
                     "beats": [{"say": "One.", "pause": 0}]},
                    {"id": "recap", "html": "scenes/two.html", "lead": 0.1, "tail": 0.1,
                     "beats": [{"say": "Two.", "pause": 0}]},
                ],
            }
            (project / "storyboard.json").write_text(json.dumps(storyboard), encoding="utf-8")

            result = subprocess.run([sys.executable, str(SKILL_DIR / "make_video.py"), str(project / "storyboard.json")],
                                    capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stderr)

            probe = subprocess.run(["ffprobe", "-v", "error", "-show_chapters", "-show_entries", "format_tags=title",
                                    "-of", "json", str(project / "video.mp4")],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(probe.returncode, 0, probe.stderr)
            info = json.loads(probe.stdout)
            timeline = json.loads((project / "build" / "timeline.json").read_text(encoding="utf-8"))
            chapters = info["chapters"]
            self.assertEqual([chapter["tags"]["title"] for chapter in chapters], ["The hook", "recap"])
            for chapter, scene in zip(chapters, timeline):
                self.assertAlmostEqual(float(chapter["start_time"]), scene["start"], delta=1 / 24)
                self.assertAlmostEqual(float(chapter["end_time"]), scene["end"], delta=1 / 24)
            self.assertEqual(info["format"]["tags"]["title"], "Chapter test")
            self.assertEqual((project / "chapters.txt").read_text(encoding="utf-8"), "0:00 The hook\n0:01 recap\n")

    def test_scene_title_must_be_a_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "one.html").write_text("<html></html>", encoding="utf-8")
            storyboard = {"tts": "none", "scenes": [{"id": "hook", "title": 3, "html": "one.html",
                                                     "beats": [{"say": "One."}]}]}
            (project / "storyboard.json").write_text(json.dumps(storyboard), encoding="utf-8")

            with self.assertRaisesRegex(make_video.StoryboardError, r"scenes\[0\]\.title"):
                make_video.load_storyboard(project / "storyboard.json")


if __name__ == "__main__":
    unittest.main()
