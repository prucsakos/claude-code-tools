import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402

SEEK_JS = "([t, prev]) => window.__tvSeek(t, prev)"


class FakePage:
    """Records calls; a seek reports a change only for the first frame of a scene (prev is None)."""

    def __init__(self):
        self.handlers = {}
        self.goto_urls = []
        self.screenshot_calls = []

    def on(self, event, callback):
        self.handlers[event] = callback

    def goto(self, url, wait_until):
        self.goto_urls.append(url)

    def evaluate(self, script, arg):
        if script == SEEK_JS:
            return arg[1] is None
        return None

    def screenshot(self, **kwargs):
        self.screenshot_calls.append(kwargs)
        if "path" in kwargs:
            Path(kwargs["path"]).write_bytes(b"png")
        return f"jpeg{len(self.screenshot_calls)}".encode()


class FakeBrowser:
    def __init__(self):
        self.page = FakePage()
        self.closed = False
        self.launch_options = None

    def new_page(self, viewport):
        return self.page

    def close(self):
        self.closed = True


def fake_playwright_module(browser):
    @contextlib.contextmanager
    def sync_playwright():
        def launch(**options):
            browser.launch_options = options
            return browser

        yield SimpleNamespace(chromium=SimpleNamespace(launch=launch))

    module = types.ModuleType("playwright.sync_api")
    module.sync_playwright = sync_playwright
    return module


class FakeStdin:
    def __init__(self, error=None):
        self.writes = []
        self.closed = False
        self.error = error

    def write(self, data):
        if self.error:
            raise self.error
        self.writes.append(data)

    def close(self):
        self.closed = True


class FakeEncoder:
    def __init__(self, command, cwd, stdin, stderr, returncode=0, write_error=None):
        self.command = command
        self.stdin = FakeStdin(write_error)
        self.returncode = returncode
        self.wait_calls = 0
        stderr.write(b"ffmpeg log text")
        stderr.flush()

    def wait(self):
        self.wait_calls += 1
        return self.returncode


def timed_scene(scene_id, start, end, html):
    scene = make_video.Scene(scene_id, html, [make_video.Beat("hello", 0.0)], 0.0, 0.0)
    return make_video.TimedScene(scene, start, end, [make_video.TimedBeat("hello", start, end)])


class RenderVideoTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "build").mkdir()
        html = self.root / "scene.html"
        html.write_text("<html></html>", encoding="utf-8")
        self.scenes = [timed_scene("intro", 0.0, 1.0, html), timed_scene("outro", 1.0, 1.5, html)]
        self.storyboard = make_video.Storyboard("Title", "none", "", "", 10, [ts.scene for ts in self.scenes])
        self.browser = FakeBrowser()
        self.encoders = []

    def render(self, burn_captions=True, **encoder_options):
        def popen(command, cwd, stdin, stderr):
            encoder = FakeEncoder(command, cwd, stdin, stderr, **encoder_options)
            self.encoders.append(encoder)
            return encoder

        with mock.patch.dict(sys.modules, {"playwright.sync_api": fake_playwright_module(self.browser)}), \
                mock.patch.object(make_video.subprocess, "Popen", popen), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            make_video.render_video(self.scenes, self.storyboard, self.root, burn_captions)
        return out.getvalue()

    def test_static_hold_reuses_one_screenshot_per_scene(self):
        out = self.render()
        encoder = self.encoders[0]
        self.assertEqual(len(self.browser.page.screenshot_calls), 2)
        self.assertEqual(encoder.stdin.writes, [b"jpeg1"] * 10 + [b"jpeg2"] * 5)
        self.assertIn("rendered 1/2 intro: 10 frames, 1 captured", out)
        self.assertIn("rendered 2/2 outro: 5 frames, 1 captured", out)
        self.assertTrue(encoder.stdin.closed)
        self.assertTrue(self.browser.closed)
        self.assertIn("--renderer-process-limit=1", self.browser.launch_options["args"])

    def test_burned_captions_use_the_subtitles_filter(self):
        self.render(burn_captions=True)
        command = self.encoders[0].command
        self.assertIn("-vf", command)
        self.assertTrue(command[command.index("-vf") + 1].startswith("subtitles=captions.srt"))
        self.assertNotIn("mov_text", command)

    def test_soft_captions_add_a_subtitle_stream_without_the_filter(self):
        self.render(burn_captions=False)
        command = self.encoders[0].command
        inputs = [command[i + 1] for i, part in enumerate(command) if part == "-i"]
        self.assertIn("captions.srt", inputs)
        subtitle_map = f"{inputs.index('captions.srt')}:s"
        self.assertEqual(command[command.index(subtitle_map) - 1], "-map")
        self.assertEqual(command[command.index("-c:s") + 1], "mov_text")
        self.assertNotIn("-vf", command)
        self.assertFalse(any(part.startswith("subtitles=") for part in command))

    def test_broken_pipe_reports_early_stop_with_the_log(self):
        with self.assertRaises(make_video.RenderError) as caught:
            self.render(write_error=BrokenPipeError())
        message = str(caught.exception)
        self.assertIn("ffmpeg stopped early", message)
        self.assertIn("ffmpeg log text", message)
        self.assertGreaterEqual(self.encoders[0].wait_calls, 1)
        self.assertTrue(self.encoders[0].stdin.closed)
        self.assertTrue(self.browser.closed)

    def test_failed_encode_reports_the_log(self):
        with self.assertRaises(make_video.RenderError) as caught:
            self.render(returncode=1)
        message = str(caught.exception)
        self.assertTrue(message.startswith("ffmpeg failed:"))
        self.assertIn("ffmpeg log text", message)


class ScenePlayerWarningTest(unittest.TestCase):
    def setUp(self):
        self.browser = FakeBrowser()
        self.player = make_video.ScenePlayer(self.browser)
        self.player.scene_id = "intro"
        self.handlers = self.browser.page.handlers

    def warnings(self, event, payload):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.handlers[event](payload)
        return err.getvalue()

    def test_page_error_names_the_scene(self):
        self.assertEqual(self.warnings("pageerror", "boom"), "  WARNING in scene intro: JS error: boom\n")

    def test_console_error_warns_and_console_log_does_not(self):
        error = SimpleNamespace(type="error", text="bad var")
        log = SimpleNamespace(type="log", text="hello")
        self.assertEqual(self.warnings("console", error), "  WARNING in scene intro: console: bad var\n")
        self.assertEqual(self.warnings("console", log), "")

    def test_failed_request_names_the_url(self):
        request = SimpleNamespace(url="file:///missing.png")
        self.assertEqual(self.warnings("requestfailed", request),
                         "  WARNING in scene intro: failed to load file:///missing.png\n")


class RenderPreviewTest(unittest.TestCase):
    def test_old_stills_are_deleted_before_new_ones_are_shot(self):
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            html = build / "scene.html"
            html.write_text("<html></html>", encoding="utf-8")
            preview = build / "preview"
            preview.mkdir()
            (preview / "0099.png").write_bytes(b"old")
            browser = FakeBrowser()
            with mock.patch.dict(sys.modules, {"playwright.sync_api": fake_playwright_module(browser)}), \
                    mock.patch.object(make_video, "run_ffmpeg") as run_ffmpeg, \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                make_video.render_preview([timed_scene("intro", 0.0, 1.0, html)], 10, build)
            self.assertEqual(sorted(path.name for path in preview.glob("*.png")), ["0001.png"])
            self.assertIn("  0001.png  intro beat 0", out.getvalue())
            run_ffmpeg.assert_called_once()
            self.assertTrue(browser.closed)


class MainArgumentsTest(unittest.TestCase):
    def test_missing_storyboard_without_doctor_exits_2(self):
        with mock.patch.object(sys, "argv", ["make_video.py"]), contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as caught:
                make_video.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("the storyboard argument is required", err.getvalue())

    def test_doctor_exits_with_its_result(self):
        with mock.patch.object(sys, "argv", ["make_video.py", "--doctor"]), \
                mock.patch.object(make_video, "run_doctor", return_value=1) as run_doctor:
            with self.assertRaises(SystemExit) as caught:
                make_video.main()
        self.assertEqual(caught.exception.code, 1)
        run_doctor.assert_called_once_with("en", False)


if __name__ == "__main__":
    unittest.main()
