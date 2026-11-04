import contextlib
import io
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402
from make_video import Beat, Narrator, RenderError, Scene, Storyboard, StoryboardError, TimedBeat  # noqa: E402


def valid_storyboard(**overrides):
    data = {"scenes": [{"id": "intro", "html": "scene.html", "beats": [{"say": "Hello there."}]}]}
    data.update(overrides)
    return data


class LoadStoryboardTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name) / "my-lesson"
        self.folder.mkdir()
        (self.folder / "scene.html").write_text("<html></html>", encoding="utf-8")
        self.path = self.folder / "storyboard.json"

    def load_text(self, text):
        self.path.write_text(text, encoding="utf-8")
        return make_video.load_storyboard(self.path)

    def load(self, data):
        return self.load_text(json.dumps(data))

    def with_scene(self, **scene_overrides):
        scene = {"id": "intro", "html": "scene.html", "beats": [{"say": "Hello there."}]}
        scene.update(scene_overrides)
        return valid_storyboard(scenes=[scene])

    def test_valid_storyboard_gets_defaults(self):
        storyboard = self.load(valid_storyboard())
        self.assertEqual(storyboard.tts, "edge")
        self.assertEqual(storyboard.fps, 30)
        self.assertEqual(storyboard.voice, "en-US-AndrewNeural")
        self.assertEqual(storyboard.rate, "+0%")
        self.assertEqual(storyboard.title, "my-lesson")
        scene = storyboard.scenes[0]
        self.assertEqual(scene.id, "intro")
        self.assertEqual(scene.html, (self.folder / "scene.html").resolve())
        self.assertEqual(scene.lead, 0.4)
        self.assertEqual(scene.tail, 0.8)
        self.assertEqual(scene.beats, [Beat(say="Hello there.", pause=0.35)])

    def test_invalid_json(self):
        with self.assertRaisesRegex(StoryboardError, "invalid JSON"):
            self.load_text("{not json")

    def test_top_level_list(self):
        with self.assertRaisesRegex(StoryboardError, r"storyboard must be an object"):
            self.load([])

    def test_unknown_tts(self):
        with self.assertRaisesRegex(StoryboardError, r"tts must be one of edge, sapi, none: got 'foo'"):
            self.load(valid_storyboard(tts="foo"))

    def test_fps_must_divide_sample_rate(self):
        for fps in (7, True, 0, 30.0):
            with self.subTest(fps=fps), self.assertRaisesRegex(StoryboardError, r"fps must divide 24000"):
                self.load(valid_storyboard(fps=fps))

    def test_scenes_not_a_list(self):
        with self.assertRaisesRegex(StoryboardError, r"scenes must be a non-empty list"):
            self.load(valid_storyboard(scenes={"id": "intro"}))

    def test_empty_scenes(self):
        with self.assertRaisesRegex(StoryboardError, r"scenes must be a non-empty list"):
            self.load(valid_storyboard(scenes=[]))

    def test_scene_not_an_object(self):
        with self.assertRaisesRegex(StoryboardError, r"scenes\[0\] must be an object"):
            self.load(valid_storyboard(scenes=["intro"]))

    def test_missing_id(self):
        data = valid_storyboard(scenes=[{"html": "scene.html", "beats": [{"say": "Hi."}]}])
        with self.assertRaisesRegex(StoryboardError, r"scenes\[0\]\.id must be a non-empty string"):
            self.load(data)

    def test_duplicate_id(self):
        scene = {"id": "intro", "html": "scene.html", "beats": [{"say": "Hi."}]}
        with self.assertRaisesRegex(StoryboardError, r"scenes\[1\]\.id 'intro' is used twice"):
            self.load(valid_storyboard(scenes=[scene, dict(scene)]))

    def test_missing_html_file(self):
        with self.assertRaisesRegex(StoryboardError, r"scenes\[0\]\.html: file not found"):
            self.load(self.with_scene(html="missing.html"))

    def test_beat_without_say(self):
        with self.assertRaisesRegex(StoryboardError, r"scenes\[0\]\.beats\[0\]\.say must be a non-empty string"):
            self.load(self.with_scene(beats=[{"pause": 1}]))

    def test_beat_not_an_object(self):
        with self.assertRaisesRegex(StoryboardError, r"scenes\[0\]\.beats\[0\] must be an object"):
            self.load(self.with_scene(beats=["Hello"]))

    def test_bad_pause(self):
        for pause in (-0.5, "1", True):
            with self.subTest(pause=pause), \
                    self.assertRaisesRegex(StoryboardError, r"scenes\[0\]\.beats\[0\]\.pause must be a number of seconds >= 0"):
                self.load(self.with_scene(beats=[{"say": "Hi.", "pause": pause}]))

    def test_bad_lead(self):
        with self.assertRaisesRegex(StoryboardError, r"scenes\[0\]\.lead must be a number of seconds >= 0"):
            self.load(self.with_scene(lead=-1))

    def test_non_string_voice(self):
        with self.assertRaisesRegex(StoryboardError, r"title, voice and rate must be strings"):
            self.load(valid_storyboard(voice=5))


class CaptionTest(unittest.TestCase):
    def test_short_text_is_one_chunk(self):
        self.assertEqual(make_video.caption_chunks("  Hello world.  "), ["Hello world."])

    def test_two_sentences_are_never_merged(self):
        self.assertEqual(make_video.caption_chunks("One. Two!"), ["One.", "Two!"])

    def test_long_sentence_is_split_into_balanced_cues(self):
        sentence = ("The narration track is built first, and every scene then follows its timeline frame by frame, "
                    "so the voice and the picture never drift apart at all, ever.")
        self.assertGreaterEqual(len(sentence), 150)
        chunks = make_video.caption_chunks(sentence)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            lines = chunk.split("\n")
            self.assertLessEqual(len(lines), 2, chunk)
            for line in lines:
                self.assertLessEqual(len(line), make_video.CAPTION_LINE_CHARS, line)
        self.assertGreater(len(chunks[-1].split()), 1, chunks[-1])
        self.assertEqual(" ".join(" ".join(chunks).split()), sentence)

    def test_srt_time(self):
        # Not 3661.2345: its 3661234.5 ms is an exact half, which round() takes to the even 234.
        self.assertEqual(make_video.srt_time(3661.2346), "01:01:01,235")
        self.assertEqual(make_video.srt_time(0), "00:00:00,000")

    def test_write_srt_numbers_cues_and_splits_time_by_length(self):
        beats = [
            TimedBeat(text="Hi there. This is the second one.", start=1.0, end=4.2),
            TimedBeat(text="Next.", start=5.0, end=6.0),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "captions.srt"
            make_video.write_srt(path, beats)
            text = path.read_text(encoding="utf-8")
        # "Hi there." is 9 characters and the second sentence 23, so they share 3.2 s as 0.9 s and 2.3 s.
        self.assertEqual(
            text,
            "1\n00:00:01,000 --> 00:00:01,900\nHi there.\n"
            "\n2\n00:00:01,900 --> 00:00:04,200\nThis is the second one.\n"
            "\n3\n00:00:05,000 --> 00:00:06,000\nNext.\n",
        )


class BuildTimelineTest(unittest.TestCase):
    def build(self, storyboard):
        with tempfile.TemporaryDirectory() as cache, contextlib.redirect_stdout(io.StringIO()):
            return make_video.build_timeline(storyboard, Narrator("none", "", "", Path(cache)))

    def test_none_narrator_timeline(self):
        html = Path("scene.html")
        short = "Two words."  # 2 words / 2.5 = 0.8 s, raised to the 1.5 s minimum
        long = " ".join(["word"] * 10)  # 10 words / 2.5 = 4.0 s
        scenes = [
            Scene(id="a", html=html, beats=[Beat(short, 0.35), Beat(long, 0.5)], lead=0.4, tail=0.8),
            Scene(id="b", html=html, beats=[Beat(long, 0.0)], lead=0.25, tail=0.33),
        ]
        storyboard = Storyboard(title="t", tts="none", voice="", rate="+0%", fps=24, scenes=scenes)

        timed, track = self.build(storyboard)

        first, second = timed
        self.assertEqual(first.start, 0.0)
        self.assertAlmostEqual(first.beats[0].start, 0.4)
        self.assertAlmostEqual(first.beats[0].end - first.beats[0].start, 1.5)
        self.assertAlmostEqual(first.beats[1].start, first.beats[0].end + 0.35)
        self.assertAlmostEqual(first.beats[1].end - first.beats[1].start, 4.0)
        self.assertEqual([beat.text for beat in first.beats], [short, long])
        # 0.4 + 1.5 + 0.35 + 4.0 + 0.5 + 0.8 = 7.55 s is padded up to the next frame, 182 / 24 s.
        self.assertAlmostEqual(first.end, 182 / 24)
        self.assertEqual(second.start, first.end)
        self.assertAlmostEqual(second.beats[0].start, second.start + 0.25)
        # 0.25 + 4.0 + 0.33 = 4.58 s is padded up to the next frame, 110 / 24 s.
        self.assertAlmostEqual(second.end - second.start, 110 / 24)
        for scene in timed:
            self.assertAlmostEqual(scene.end * 24, round(scene.end * 24))
        self.assertEqual(len(track), round(second.end * 24000) * 2)
        self.assertEqual(track, bytes(len(track)))

    def test_beat_offsets_are_relative_to_scene_start(self):
        html = Path("scene.html")
        scenes = [
            Scene(id="a", html=html, beats=[Beat("One.", 0.0)], lead=0.0, tail=0.0),
            Scene(id="b", html=html, beats=[Beat("One.", 0.5), Beat("Two.", 0.0)], lead=1.0, tail=0.0),
        ]
        storyboard = Storyboard(title="t", tts="none", voice="", rate="+0%", fps=30, scenes=scenes)

        timed, _ = self.build(storyboard)

        self.assertEqual(timed[0].beat_offsets(), [0.0])
        offsets = timed[1].beat_offsets()
        self.assertEqual(len(offsets), 2)
        self.assertAlmostEqual(offsets[0], 1.0)
        self.assertAlmostEqual(offsets[1], 1.0 + 1.5 + 0.5)


class WavTest(unittest.TestCase):
    def test_write_wav_read_pcm_round_trip(self):
        pcm = bytes(range(256)) * 10
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "clip.wav"
            make_video.write_wav(path, pcm)
            self.assertEqual(make_video.read_pcm(path), pcm)

    def test_read_pcm_rejects_other_sample_rates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "clip.wav"
            with wave.open(str(path), "wb") as clip:
                clip.setnchannels(1)
                clip.setsampwidth(2)
                clip.setframerate(8000)
                clip.writeframes(bytes(1600))
            with self.assertRaisesRegex(RenderError, "is not 24000 Hz 16-bit mono PCM"):
                make_video.read_pcm(path)


if __name__ == "__main__":
    unittest.main()
