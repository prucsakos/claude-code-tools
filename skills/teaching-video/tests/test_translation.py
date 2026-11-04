"""--translation: narration overlay validation and the language-suffixed outputs of main()."""

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


class TranslationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "scene.html").write_text("<html><body>scene</body></html>", encoding="utf-8")
        self.storyboard_path = self.root / "storyboard.json"
        self.storyboard_path.write_text(json.dumps({"tts": "none", "voice": "en-US-AndrewNeural", "scenes": [
            {"id": "intro", "html": "scene.html", "beats": [{"say": "Hello there, learner."}]}]}), encoding="utf-8")
        self.overlay_path = self.root / "storyboard.hu.json"

    def load(self, overlay):
        self.overlay_path.write_text(json.dumps(overlay), encoding="utf-8")
        storyboard = make_video.load_storyboard(self.storyboard_path)
        return storyboard, make_video.load_translation(self.overlay_path, storyboard)

    def assert_rejected(self, overlay, message):
        with self.assertRaises(make_video.StoryboardError) as caught:
            self.load(overlay)
        self.assertIn(message, str(caught.exception))

    def test_valid_overlay_replaces_texts_and_voice_and_keeps_the_original(self):
        original, (language, translated) = self.load(
            {"language": "hu", "voice": "hu-HU-NoemiNeural", "say": {"intro": ["Szia, tanuló."]}})
        self.assertEqual(language, "hu")
        self.assertEqual(translated.voice, "hu-HU-NoemiNeural")
        self.assertEqual([beat.say for beat in translated.scenes[0].beats], ["Szia, tanuló."])
        self.assertEqual(original.voice, "en-US-AndrewNeural")
        self.assertEqual(original.scenes[0].beats[0].say, "Hello there, learner.")

    def test_invalid_overlays_name_the_problem(self):
        cases = [
            ({"language": "hu", "say": {"intro": ["Szia."], "outro": ["Viszlát."]}}, "unknown scene id 'outro'"),
            ({"language": "hu", "say": {}}, "translation.say.intro is missing"),
            ({"language": "hu", "say": {"intro": ["Szia.", "Még egy."]}}, "has 2 texts but the scene has 1 beats"),
            ({"language": "../hu", "say": {"intro": ["Szia."]}}, "translation.language"),
            ({"language": "hu\\x", "say": {"intro": ["Szia."]}}, "translation.language"),
        ]
        for overlay, message in cases:
            with self.subTest(message=message):
                self.assert_rejected(overlay, message)

    def test_main_writes_language_suffixed_outputs(self):
        self.overlay_path.write_text(json.dumps({"language": "hu", "say": {"intro": ["Szia, tanuló."]}}), encoding="utf-8")
        render_video = mock.MagicMock()
        argv = ["make_video.py", str(self.storyboard_path), "--translation", str(self.overlay_path)]
        with mock.patch("make_video.render_video", render_video), \
                mock.patch("make_video.shutil.which", return_value="ffmpeg"), \
                mock.patch.dict(sys.modules, {"playwright": types.ModuleType("playwright")}), \
                mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            make_video.main()
        self.assertIn("Szia, tanuló.", (self.root / "captions.hu.srt").read_text(encoding="utf-8"))
        self.assertFalse((self.root / "captions.srt").exists())
        self.assertTrue((self.root / "build" / "narration.hu.wav").exists())
        self.assertTrue((self.root / "build" / "timeline.hu.json").exists())
        render_video.assert_called_once()
        self.assertEqual(render_video.call_args.args[4].video, "video.hu.mp4")


if __name__ == "__main__":
    unittest.main()
