"""Translation overlay errors (bad JSON, bad beat texts, main() exits) and two read-aloud checks."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402


class TranslationErrors(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "scene.html").write_text("<html><body>scene</body></html>", encoding="utf-8")
        self.storyboard_path = self.root / "storyboard.json"
        self.storyboard_path.write_text(json.dumps({"tts": "none", "voice": "en-US-AndrewNeural", "scenes": [
            {"id": "intro", "html": "scene.html", "beats": [{"say": "Hello there."}, {"say": "Goodbye now."}]}]}),
            encoding="utf-8")
        self.overlay_path = self.root / "storyboard.hu.json"

    def test_invalid_json_overlay_is_rejected(self):
        self.overlay_path.write_text("{not json", encoding="utf-8")
        storyboard = make_video.load_storyboard(self.storyboard_path)
        with self.assertRaises(make_video.StoryboardError) as caught:
            make_video.load_translation(self.overlay_path, storyboard)
        self.assertTrue(str(caught.exception).startswith("translation: invalid JSON"), str(caught.exception))

    def test_blank_or_non_string_beat_text_names_its_index(self):
        storyboard = make_video.load_storyboard(self.storyboard_path)
        cases = [(["Szia.", "   "], "translation.say.intro[1] must be a non-empty string"),
                 ([7, "Viszlát."], "translation.say.intro[0] must be a non-empty string")]
        for texts, message in cases:
            with self.subTest(texts=texts):
                self.overlay_path.write_text(json.dumps({"language": "hu", "say": {"intro": texts}}), encoding="utf-8")
                with self.assertRaises(make_video.StoryboardError) as caught:
                    make_video.load_translation(self.overlay_path, storyboard)
                self.assertEqual(str(caught.exception), message)

    def run_main_with_translation(self, overlay: Path) -> SystemExit:
        argv = ["make_video.py", str(self.storyboard_path), "--translation", str(overlay)]
        narrator = mock.Mock(side_effect=AssertionError("Narrator must not be built after a translation error"))
        with mock.patch.object(sys, "argv", argv), mock.patch.object(make_video, "Narrator", narrator):
            with self.assertRaises(SystemExit) as caught:
                make_video.main()
        narrator.assert_not_called()
        self.assertFalse((self.root / "build").exists())
        self.assertEqual(list(self.root.rglob("narration*.wav")), [])
        return caught.exception

    def test_main_exits_on_missing_overlay_without_building(self):
        exit_ = self.run_main_with_translation(self.root / "missing.json")
        self.assertIsInstance(exit_.code, str)
        self.assertTrue(exit_.code.startswith("translation error:"), exit_.code)

    def test_main_exits_on_invalid_json_overlay_without_building(self):
        self.overlay_path.write_text("{not json", encoding="utf-8")
        exit_ = self.run_main_with_translation(self.overlay_path)
        self.assertIsInstance(exit_.code, str)
        self.assertTrue(exit_.code.startswith("translation error: translation: invalid JSON"), exit_.code)


def timed(scene_id, text, seconds=4.0):
    """A one-beat TimedScene with the given text."""
    scene = make_video.Scene(id=scene_id, html=Path("scene.html"), beats=[], lead=0, tail=0)
    beat = make_video.TimedBeat(text=text, start=0.0, end=seconds)
    return make_video.TimedScene(scene=scene, start=0.0, end=seconds, beats=[beat])


class ReadAloudGaps(unittest.TestCase):
    def warnings_for(self, text):
        return make_video.read_aloud_warnings([timed("intro", text)], measured=False)

    def test_slash_gives_one_slash_problem(self):
        warnings = self.warnings_for("Speed is 5 km per hour and/or more.")
        self.assertEqual(warnings, ['read-aloud: intro beat 0: slash: write "or", "per" or "over"'])

    def test_capital_abbreviations_are_named_as_letter_by_letter(self):
        warnings = self.warnings_for("The CPU and the APIs talk.")
        self.assertEqual(warnings, ["read-aloud: intro beat 0: read letter by letter: APIs, CPU; "
                                    "spell it out unless it is said that way"])

    def test_plain_words_give_no_problem(self):
        self.assertEqual(self.warnings_for("Plain words only."), [])


if __name__ == "__main__":
    unittest.main()
