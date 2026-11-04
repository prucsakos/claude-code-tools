"""The encoder pipe is fed from a writer thread: a dead ffmpeg must end the render with a clear error, not a hang.

Run: python -m unittest discover -s skills/teaching-video/tests
"""

import contextlib
import shutil
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402


class DyingPipe:
    """Accepts a few frames, then fails the way a pipe to an exited process does."""

    def __init__(self, frames_before_failure: int) -> None:
        self.frames_left = frames_before_failure
        self.closed = False

    def write(self, frame: bytes) -> None:
        if self.frames_left == 0:
            raise BrokenPipeError(32, "Broken pipe")
        self.frames_left -= 1

    def close(self) -> None:
        self.closed = True


class FakePlayer:
    def __init__(self, browser) -> None:
        self.page = types.SimpleNamespace(screenshot=lambda **options: b"jpeg")

    def load(self, timed_scene) -> None:
        pass

    def seek(self, t, prev) -> bool:
        return True


class EncoderStopsEarlyTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / "build").mkdir()

    def test_dead_encoder_raises_render_error_and_joins_writer(self):
        encoder = mock.Mock()
        encoder.stdin = DyingPipe(frames_before_failure=3)
        encoder.wait.return_value = 1
        sync_api = types.ModuleType("playwright.sync_api")
        sync_api.sync_playwright = lambda: contextlib.nullcontext(object())
        # 1000 frames, far more than the queue holds, so a writer that stopped draining would block the capture loop.
        scene = types.SimpleNamespace(start=0.0, end=40.0, scene=types.SimpleNamespace(id="s1"))
        storyboard = types.SimpleNamespace(fps=25, title="t")
        outcome = {}

        def render():
            try:
                make_video.render_video([scene], storyboard, self.root, burn_captions=True)
            except make_video.RenderError as error:
                outcome["error"] = error

        with mock.patch.dict(sys.modules, {"playwright": types.ModuleType("playwright"), "playwright.sync_api": sync_api}), \
                mock.patch.object(make_video.subprocess, "Popen", return_value=encoder), \
                mock.patch.object(make_video, "launch_chromium", return_value=mock.Mock()), \
                mock.patch.object(make_video, "ScenePlayer", FakePlayer):
            runner = threading.Thread(target=render, daemon=True)
            runner.start()
            runner.join(timeout=20)

        self.assertFalse(runner.is_alive(), "render_video hung after the encoder died")
        self.assertIn("ffmpeg stopped early", str(outcome.get("error")))
        self.assertTrue(encoder.stdin.closed)
        self.assertFalse(any(thread.name == "ffmpeg-writer" for thread in threading.enumerate()))


if __name__ == "__main__":
    unittest.main()
