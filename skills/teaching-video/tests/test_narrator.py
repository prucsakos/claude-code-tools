import contextlib
import io
import subprocess
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402

SOURCE_RATE = 16000
CLIP_SECONDS = 0.5
REAL_RUN = subprocess.run


def write_source_wav(path):
    """A 16 kHz stereo WAV, so the real ffmpeg conversion to 24 kHz mono has work to do."""
    with wave.open(str(path), "wb") as clip:
        clip.setnchannels(2)
        clip.setsampwidth(2)
        clip.setframerate(SOURCE_RATE)
        clip.writeframes(bytes(int(SOURCE_RATE * CLIP_SECONDS) * 2 * 2))


def fake_edge_tts(failures=0):
    """An edge_tts module whose save_sync fails `failures` times, then writes a WAV."""
    module = types.ModuleType("edge_tts")
    module.calls = []
    module.failures_left = failures

    class Communicate:
        def __init__(self, text, voice, rate):
            module.calls.append((text, voice, rate))

        def save_sync(self, path):
            if module.failures_left > 0:
                module.failures_left -= 1
                raise ConnectionError("No audio was received")
            write_source_wav(path)

    module.Communicate = Communicate
    return module


class NarratorTestCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.cache_dir = Path(temp.name)

    def narrate(self, narrator, text="Hello world"):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            pcm = narrator.pcm(text)
        return pcm, err.getvalue()

    def expected_pcm_length(self):
        return int(make_video.SAMPLE_RATE * CLIP_SECONDS) * make_video.SAMPLE_WIDTH


class EdgeNarratorTest(NarratorTestCase):
    def test_first_call_converts_and_caches_clip_then_cache_hit_skips_edge(self):
        fake = fake_edge_tts()
        narrator = make_video.Narrator("edge", "en-US-AndrewNeural", "+0%", self.cache_dir)
        with mock.patch.dict(sys.modules, {"edge_tts": fake}):
            pcm, _ = self.narrate(narrator)
        files = sorted(path.name for path in self.cache_dir.iterdir())
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0], r"^[0-9a-f]{20}\.wav$")
        self.assertAlmostEqual(len(pcm), self.expected_pcm_length(), delta=200)
        with wave.open(str(self.cache_dir / files[0]), "rb") as clip:
            self.assertEqual((clip.getnchannels(), clip.getframerate()), (1, make_video.SAMPLE_RATE))

        def broken_save(self, path):
            raise AssertionError("cache hit must not call edge-tts")

        with mock.patch.dict(sys.modules, {"edge_tts": fake}), \
                mock.patch.object(fake.Communicate, "save_sync", broken_save):
            cached, _ = self.narrate(narrator)
        self.assertEqual(cached, pcm)

    def test_voice_and_rate_are_part_of_the_cache_key(self):
        fake = fake_edge_tts()
        with mock.patch.dict(sys.modules, {"edge_tts": fake}):
            self.narrate(make_video.Narrator("edge", "en-US-AndrewNeural", "+0%", self.cache_dir))
            self.narrate(make_video.Narrator("edge", "en-GB-RyanNeural", "+0%", self.cache_dir))
            self.narrate(make_video.Narrator("edge", "en-US-AndrewNeural", "+10%", self.cache_dir))
        self.assertEqual(len(list(self.cache_dir.glob("*.wav"))), 3)
        self.assertIn(("Hello world", "en-GB-RyanNeural", "+0%"), fake.calls)
        self.assertIn(("Hello world", "en-US-AndrewNeural", "+10%"), fake.calls)

    def test_transient_failures_are_retried_with_backoff(self):
        fake = fake_edge_tts(failures=2)
        narrator = make_video.Narrator("edge", "en-US-AndrewNeural", "+0%", self.cache_dir)
        with mock.patch.dict(sys.modules, {"edge_tts": fake}), \
                mock.patch.object(make_video.time, "sleep") as sleep:
            pcm, err = self.narrate(narrator)
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(4)])
        self.assertIn("edge-tts attempt 1 failed (No audio was received); retrying", err)
        self.assertIn("edge-tts attempt 2 failed", err)
        self.assertAlmostEqual(len(pcm), self.expected_pcm_length(), delta=200)

    def test_persistent_failure_raises_after_all_attempts(self):
        fake = fake_edge_tts(failures=100)
        narrator = make_video.Narrator("edge", "en-US-AndrewNeural", "+0%", self.cache_dir)
        with mock.patch.dict(sys.modules, {"edge_tts": fake}), \
                mock.patch.object(make_video.time, "sleep") as sleep, \
                self.assertRaisesRegex(make_video.RenderError,
                                       rf"edge-tts failed {make_video.EDGE_ATTEMPTS} times \(voice 'en-US-AndrewNeural'\)"):
            self.narrate(narrator)
        self.assertEqual(sleep.call_count, make_video.EDGE_ATTEMPTS - 1)
        self.assertEqual(list(self.cache_dir.glob("*.wav")), [])

    def test_rejected_voice_fails_fast_without_retries(self):
        fake = fake_edge_tts()

        def reject(self, text, voice, rate):
            raise ValueError(f"Invalid voice '{voice}'")

        narrator = make_video.Narrator("edge", "nobody", "+0%", self.cache_dir)
        with mock.patch.dict(sys.modules, {"edge_tts": fake}), \
                mock.patch.object(fake.Communicate, "__init__", reject), \
                mock.patch.object(make_video.time, "sleep") as sleep, \
                self.assertRaisesRegex(make_video.RenderError, r"edge-tts rejected the voice or rate \(Invalid voice 'nobody'\)"):
            self.narrate(narrator)
        sleep.assert_not_called()

    def test_missing_edge_tts_names_the_pip_install(self):
        narrator = make_video.Narrator("edge", "en-US-AndrewNeural", "+0%", self.cache_dir)
        with mock.patch.dict(sys.modules, {"edge_tts": None}), \
                self.assertRaisesRegex(make_video.RenderError, r"-m pip install edge-tts"):
            self.narrate(narrator)


class SapiNarratorTest(NarratorTestCase):
    def fake_powershell(self, returncode):
        commands = []

        def run(command, **kwargs):
            if command[0] != "powershell":
                return REAL_RUN(command, **kwargs)
            commands.append(command)
            text_file = Path(command[command.index("-TextFile") + 1])
            self.assertEqual(text_file.read_text(encoding="utf-8"), "Hello world")
            if returncode == 0:
                write_source_wav(command[command.index("-OutFile") + 1])
            return subprocess.CompletedProcess(command, returncode, "", "voice not installed")

        return run, commands

    def test_sapi_is_windows_only(self):
        narrator = make_video.Narrator("sapi", "", "+0%", self.cache_dir)
        with mock.patch.object(make_video.sys, "platform", "linux"), \
                self.assertRaisesRegex(make_video.RenderError, "sapi narration runs on Windows only"):
            self.narrate(narrator)

    def test_sapi_passes_voice_removes_text_file_and_caches_clip(self):
        run, commands = self.fake_powershell(returncode=0)
        narrator = make_video.Narrator("sapi", "Microsoft Zira Desktop", "+0%", self.cache_dir)
        with mock.patch.object(make_video.sys, "platform", "win32"), \
                mock.patch.object(make_video.subprocess, "run", run):
            pcm, _ = self.narrate(narrator)
            self.narrate(narrator)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][-2:], ["-Voice", "Microsoft Zira Desktop"])
        self.assertEqual(list(self.cache_dir.glob("*.txt")), [])
        self.assertEqual(len(list(self.cache_dir.glob("*.wav"))), 1)
        self.assertAlmostEqual(len(pcm), self.expected_pcm_length(), delta=200)

    def test_sapi_without_voice_omits_voice_argument(self):
        run, commands = self.fake_powershell(returncode=0)
        narrator = make_video.Narrator("sapi", "", "+0%", self.cache_dir)
        with mock.patch.object(make_video.sys, "platform", "win32"), \
                mock.patch.object(make_video.subprocess, "run", run):
            self.narrate(narrator)
        self.assertNotIn("-Voice", commands[0])

    def test_sapi_failure_raises_with_stderr(self):
        run, _ = self.fake_powershell(returncode=1)
        narrator = make_video.Narrator("sapi", "Nobody", "+0%", self.cache_dir)
        with mock.patch.object(make_video.sys, "platform", "win32"), \
                mock.patch.object(make_video.subprocess, "run", run), \
                self.assertRaisesRegex(make_video.RenderError, r"sapi narration failed \(voice 'Nobody'\):\nvoice not installed"):
            self.narrate(narrator)
        self.assertEqual(list(self.cache_dir.glob("*.txt")), [])


class RunFfmpegTest(NarratorTestCase):
    def test_bad_input_raises_with_ffmpeg_stderr(self):
        missing = self.cache_dir / "missing.wav"
        with self.assertRaises(make_video.RenderError) as caught:
            make_video.run_ffmpeg("-i", str(missing), str(self.cache_dir / "out.wav"))
        message = str(caught.exception)
        self.assertIn("failed:\n", message)
        self.assertIn("missing.wav", message.split("failed:\n", 1)[1])


if __name__ == "__main__":
    unittest.main()
