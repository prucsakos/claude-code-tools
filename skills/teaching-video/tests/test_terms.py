import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402
from make_video import StoryboardError, Term  # noqa: E402

BUCKET = {"term": "bucket", "color": "--c1", "avoid": ["slot", "bin"]}


class TermsTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        (self.folder / "scene.html").write_text("<html></html>", encoding="utf-8")
        self.path = self.folder / "storyboard.json"

    def load(self, says, **top):
        beats = [{"say": say} for say in says]
        data = {"scenes": [{"id": "intro", "html": "scene.html", "beats": beats}], **top}
        self.path.write_text(json.dumps(data), encoding="utf-8")
        return make_video.load_storyboard(self.path)

    def test_avoid_word_warns_with_scene_id_and_beat_index(self):
        storyboard = self.load(["Each bucket holds keys.", "Slot seven is empty."], terms=[BUCKET])
        self.assertEqual(storyboard.terms, (Term(term="bucket", color="--c1", avoid=("slot", "bin")),))
        self.assertEqual(make_video.term_slips(storyboard), ["scene 'intro' beat 1: says 'slot'; use 'bucket'"])

    def test_match_is_whole_word_so_other_forms_do_not_warn(self):
        storyboard = self.load(["Two slots, one slotted key, a binary number."], terms=[BUCKET])
        self.assertEqual(make_video.term_slips(storyboard), [])

    def test_storyboard_without_terms_has_no_terms_and_no_warnings(self):
        storyboard = self.load(["Slot seven is empty."])
        self.assertEqual(storyboard.terms, ())
        self.assertEqual(make_video.term_slips(storyboard), [])

    def test_invalid_terms_raise(self):
        cases = {
            "missing term": [{"color": "--c1", "avoid": []}],
            "unknown color": [{"term": "bucket", "color": "--c9", "avoid": []}],
            "avoid not a list": [{"term": "bucket", "color": "--c1", "avoid": "slot"}],
            "terms not a list": {"term": "bucket", "color": "--c1"},
        }
        for name, terms in cases.items():
            with self.subTest(name), self.assertRaises(StoryboardError):
                self.load(["Hello."], terms=terms)

    def test_main_prints_the_warning_before_rendering(self):
        self.load(["Slot seven is empty."], terms=[BUCKET])
        output = io.StringIO()
        # ffmpeg reported missing stops main right after the storyboard checks, before any narration.
        with mock.patch.object(sys, "argv", ["make_video.py", str(self.path), "--preview"]), \
                mock.patch.object(make_video.shutil, "which", return_value=None), \
                contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            make_video.main()
        self.assertIn("warning: scene 'intro' beat 0: says 'slot'; use 'bucket'", output.getvalue())


if __name__ == "__main__":
    unittest.main()
