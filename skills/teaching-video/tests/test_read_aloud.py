"""The read-aloud check on beat text and measured beat duration, and its warnings during --preview."""

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

CLEAN = "You add the two numbers and keep the carry for the next column."


def timed(scene_id, beats):
    """A TimedScene from (text, seconds) pairs laid end to end."""
    scene = make_video.Scene(id=scene_id, html=Path("scene.html"), beats=[], lead=0, tail=0)
    t, timed_beats = 0.0, []
    for text, seconds in beats:
        timed_beats.append(make_video.TimedBeat(text=text, start=t, end=t + seconds))
        t += seconds
    return make_video.TimedScene(scene=scene, start=0.0, end=t, beats=timed_beats)


def seconds_at(text, words_per_second):
    return len(text.split()) / words_per_second


class ReadAloudTest(unittest.TestCase):
    def warnings_for(self, text, seconds=None, measured=True):
        seconds = seconds_at(text, 2.5) if seconds is None else seconds
        return make_video.read_aloud_warnings([timed("intro", [(CLEAN, seconds_at(CLEAN, 2.5)), (text, seconds)])], measured)

    def assert_one_warning(self, warnings, fragment):
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("intro beat 1:", warnings[0])
        self.assertIn(fragment, warnings[0])

    def test_clean_beat_gives_no_warning(self):
        self.assertEqual(self.warnings_for("Then each step halves the part of the list that is left."), [])

    def test_symbol_read_literally(self):
        warnings = self.warnings_for("Then the search takes O(n) steps in the worst case.")
        self.assertTrue(any("intro beat 1:" in w and "parenthesis" in w for w in warnings), warnings)
        self.assert_one_warning(self.warnings_for("Then the loop runs 1e6 times before it stops."), "1e6")

    def test_long_sentence(self):
        sentence = " ".join(["word"] * 24) + " end."
        self.assert_one_warning(self.warnings_for(sentence), "sentence of 25 words")

    def test_parenthesis(self):
        self.assert_one_warning(self.warnings_for("Then the pivot (the middle item) splits the list in two."), "parenthesis")

    def test_rushed_and_dragging(self):
        text = "Then each step halves the part of the list that is left."
        self.assert_one_warning(self.warnings_for(text, seconds_at(text, 4.5)), "rushed")
        self.assert_one_warning(self.warnings_for(text, seconds_at(text, 1.2)), "dragging")

    def test_no_rate_warning_without_measured_speech(self):
        text = "Then each step halves the part of the list that is left."
        self.assertEqual(self.warnings_for(text, seconds_at(text, 4.5), measured=False), [])

    def test_same_first_word_twice(self):
        self.assert_one_warning(self.warnings_for("You keep the carry and move one column to the left."), 'starts with "you"')


class PreviewPrintsWarningsTest(unittest.TestCase):
    def test_preview_prints_read_aloud_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scene.html").write_text("<html><body>scene</body></html>", encoding="utf-8")
            storyboard = root / "storyboard.json"
            storyboard.write_text(json.dumps({"tts": "none", "scenes": [
                {"id": "intro", "html": "scene.html", "beats": [{"say": "The cost grows as x^2 when the input doubles."}]}]}),
                encoding="utf-8")
            out = io.StringIO()
            with mock.patch("make_video.render_preview") as render_preview, \
                    mock.patch("make_video.shutil.which", return_value="ffmpeg"), \
                    mock.patch.dict(sys.modules, {"playwright": types.ModuleType("playwright")}), \
                    mock.patch.object(sys, "argv", ["make_video.py", str(storyboard), "--preview"]), \
                    contextlib.redirect_stdout(out):
                make_video.main()
            render_preview.assert_called_once()
            self.assertIn("read-aloud: intro beat 0: read literally: ^", out.getvalue())


if __name__ == "__main__":
    unittest.main()
