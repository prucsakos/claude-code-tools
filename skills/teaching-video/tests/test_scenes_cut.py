"""--scenes: a shorter cut of the named scenes, written next to the full video under .cut names."""

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


def scene(scene_id):
    return make_video.Scene(id=scene_id, html=Path(f"{scene_id}.html"),
                            beats=[make_video.Beat(say=f"Scene {scene_id}.", pause=0.35)], lead=0.4, tail=0.8)


class SelectScenesTest(unittest.TestCase):
    def setUp(self):
        self.storyboard = make_video.Storyboard(title="t", tts="none", voice="", rate="+0%", fps=30,
                                                scenes=[scene("a"), scene("b"), scene("c")])

    def test_keeps_only_the_named_scene_and_leaves_the_input_unchanged(self):
        cut = make_video.select_scenes(self.storyboard, ["b"])
        self.assertEqual([s.id for s in cut.scenes], ["b"])
        self.assertEqual([s.id for s in self.storyboard.scenes], ["a", "b", "c"])

    def test_keeps_storyboard_order(self):
        cut = make_video.select_scenes(self.storyboard, ["c", "a"])
        self.assertEqual([s.id for s in cut.scenes], ["a", "c"])

    def test_unknown_id_names_it_and_the_valid_ids(self):
        with self.assertRaises(make_video.StoryboardError) as caught:
            make_video.select_scenes(self.storyboard, ["b", "zzz"])
        message = str(caught.exception)
        self.assertIn("'zzz'", message)
        self.assertIn("a, b, c", message)

    def test_empty_selection_is_rejected(self):
        with self.assertRaises(make_video.StoryboardError):
            make_video.select_scenes(self.storyboard, [])


class ScenesFlagTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "scene.html").write_text("<html><body>scene</body></html>", encoding="utf-8")
        self.storyboard_path = self.root / "storyboard.json"
        self.storyboard_path.write_text(json.dumps({"tts": "none", "scenes": [
            {"id": "intro", "html": "scene.html", "beats": [{"say": "Hello there, learner."}]},
            {"id": "recap", "html": "scene.html", "beats": [{"say": "That was the recap."}]}]}), encoding="utf-8")
        self.render_video = self.patch("make_video.render_video")
        self.render_preview = self.patch("make_video.render_preview")
        self.patch("make_video.shutil.which", return_value="ffmpeg")
        patcher = mock.patch.dict(sys.modules, {"playwright": types.ModuleType("playwright")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def patch(self, target, **kwargs):
        patcher = mock.patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def run_main(self, *flags):
        argv = ["make_video.py", str(self.storyboard_path), *flags]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            make_video.main()

    def test_cut_renders_only_the_named_scene_to_cut_files_timed_from_zero(self):
        self.run_main("--scenes", "recap")
        captions = (self.root / "captions.cut.srt").read_text(encoding="utf-8")
        # Default lead is 0.4 s: the cut starts at the recap scene, not 3 s in where the full video has it.
        self.assertEqual(captions.splitlines()[1].split(" --> ")[0], "00:00:00,400")
        self.assertIn("That was the recap.", captions)
        self.assertNotIn("Hello there", captions)
        self.assertFalse((self.root / "captions.srt").exists())
        self.assertTrue((self.root / "build" / "narration.cut.wav").exists())
        self.assertFalse((self.root / "build" / "narration.wav").exists())
        self.assertFalse((self.root / "build" / "timeline.json").exists())
        self.render_video.assert_called_once()
        timed_scenes, *_, outputs = self.render_video.call_args.args
        self.assertEqual([ts.scene.id for ts in timed_scenes], ["recap"])
        self.assertEqual(outputs.video, "video.cut.mp4")

    def test_cut_preview_shows_only_the_named_scene(self):
        self.run_main("--scenes", "intro", "--preview")
        timed_scenes = self.render_preview.call_args.args[0]
        self.assertEqual([ts.scene.id for ts in timed_scenes], ["intro"])
        timeline = json.loads((self.root / "build" / "timeline.cut.json").read_text(encoding="utf-8"))
        self.assertEqual([entry["id"] for entry in timeline], ["intro"])

    def test_unknown_scene_id_exits_with_the_valid_ids(self):
        with self.assertRaises(SystemExit) as caught:
            self.run_main("--scenes", "outro")
        self.assertIn("storyboard error: unknown scene id 'outro'; the storyboard has: intro, recap", str(caught.exception.code))
        self.render_video.assert_not_called()


class ScenesHelpTest(unittest.TestCase):
    def test_help_lists_scenes(self):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["make_video.py", "--help"]), contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit):
                make_video.parse_args()
        self.assertIn("--scenes IDS", out.getvalue())


if __name__ == "__main__":
    unittest.main()
