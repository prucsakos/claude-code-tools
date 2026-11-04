"""main() argument overrides, outputs and error exits, with the Chromium renderers patched out."""

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


class MainCliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "scene.html").write_text("<html><body>scene</body></html>", encoding="utf-8")
        self.storyboard_path = self.root / "storyboard.json"
        self.write_storyboard({"tts": "none", "scenes": [
            {"id": "intro", "html": "scene.html", "beats": [{"say": "Hello there, learner."}]}]})
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

    def write_storyboard(self, data):
        self.storyboard_path.write_text(json.dumps(data), encoding="utf-8")

    def run_main(self, *flags):
        argv = ["make_video.py", str(self.storyboard_path), *flags]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            make_video.main()

    def rendered_storyboard(self):
        self.render_video.assert_called_once()
        return self.render_video.call_args.args[1]

    def assert_exits_with(self, message, *flags):
        with self.assertRaises(SystemExit) as caught:
            self.run_main(*flags)
        self.assertIn(message, str(caught.exception.code))

    def test_tts_voice_and_rate_flags_override_the_storyboard(self):
        with mock.patch.object(make_video.Narrator, "pcm", return_value=make_video.silence(1.0)):
            self.run_main("--tts", "edge", "--voice", "X", "--rate", "-10%")
        storyboard = self.rendered_storyboard()
        self.assertEqual((storyboard.tts, storyboard.voice, storyboard.rate), ("edge", "X", "-10%"))

    def test_tts_flag_alone_resets_the_voice_to_the_backend_default(self):
        self.write_storyboard({"tts": "edge", "voice": "en-GB-SoniaNeural", "scenes": [
            {"id": "intro", "html": "scene.html", "beats": [{"say": "Hello."}]}]})
        with mock.patch.object(make_video.Narrator, "pcm", return_value=make_video.silence(1.0)):
            self.run_main("--tts", "sapi")
        storyboard = self.rendered_storyboard()
        self.assertEqual((storyboard.tts, storyboard.voice), ("sapi", make_video.DEFAULT_VOICE["sapi"]))

    def test_tts_flag_equal_to_the_storyboard_keeps_its_voice(self):
        self.write_storyboard({"tts": "edge", "voice": "en-GB-SoniaNeural", "scenes": [
            {"id": "intro", "html": "scene.html", "beats": [{"say": "Hello."}]}]})
        with mock.patch.object(make_video.Narrator, "pcm", return_value=make_video.silence(1.0)):
            self.run_main("--tts", "edge")
        storyboard = self.rendered_storyboard()
        self.assertEqual((storyboard.tts, storyboard.voice), ("edge", "en-GB-SoniaNeural"))

    def test_preview_writes_timeline_and_captions_without_rendering_video(self):
        self.run_main("--preview")
        self.render_preview.assert_called_once()
        self.render_video.assert_not_called()
        timeline = json.loads((self.root / "build" / "timeline.json").read_text(encoding="utf-8"))
        self.assertEqual([scene["id"] for scene in timeline], ["intro"])
        beat = timeline[0]["beats"][0]
        self.assertEqual(beat["say"], "Hello there, learner.")
        # Default lead is 0.4 s; three words without narration last the 1.5 s minimum.
        self.assertEqual((beat["start"], beat["end"]), (0.4, 1.9))
        self.assertIn("Hello there, learner.", (self.root / "captions.srt").read_text(encoding="utf-8"))

    def test_tts_none_always_burns_captions(self):
        self.run_main()
        self.render_video.assert_called_once()
        self.assertIs(self.render_video.call_args.args[3], True)

    def test_missing_storyboard_file_exits_with_storyboard_error(self):
        self.storyboard_path.unlink()
        self.assert_exits_with("storyboard error")

    def test_missing_ffmpeg_exits_with_install_hint(self):
        with mock.patch("make_video.shutil.which", return_value=None):
            self.assert_exits_with("ffmpeg is not on PATH")

    def test_missing_playwright_exits_with_install_hint(self):
        with mock.patch.dict(sys.modules, {"playwright": None}):
            self.assert_exits_with("Playwright is missing")

    def test_render_error_exits_with_its_message(self):
        self.render_video.side_effect = make_video.RenderError("boom")
        self.assert_exits_with("error: boom")


class LaunchChromiumTest(unittest.TestCase):
    def test_launch_failure_names_the_install_command(self):
        playwright = mock.MagicMock()
        playwright.chromium.launch.side_effect = Exception("Executable doesn't exist")
        with self.assertRaises(make_video.RenderError) as caught:
            make_video.launch_chromium(playwright)
        self.assertIn("playwright install chromium", str(caught.exception))


class ParseArgsTest(unittest.TestCase):
    def test_unknown_tts_backend_is_rejected(self):
        argv = ["make_video.py", "storyboard.json", "--tts", "foo"]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                make_video.parse_args()
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
