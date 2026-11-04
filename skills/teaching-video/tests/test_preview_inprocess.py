import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402


class FakePage:
    def __init__(self, fake):
        self.fake = fake
        self.handlers = {}

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def goto(self, uri, wait_until):
        self.fake.loaded.append(uri)
        if any(uri.endswith(name) for name in self.fake.failing):
            for handler in self.handlers.get("pageerror", []):
                handler("boom")

    def evaluate(self, script, arg):
        return True

    def screenshot(self, path):
        Path(path).write_bytes(b"png")


class FakePlaywright:
    """Stands in for playwright.sync_api; records how often a browser was started."""

    def __init__(self):
        self.starts = 0
        self.loaded = []
        self.failing = set()
        self.closed = 0

    @contextlib.contextmanager
    def sync_playwright(self):
        self.starts += 1
        yield types.SimpleNamespace(chromium=types.SimpleNamespace(launch=self.launch))

    def launch(self, **kwargs):
        return types.SimpleNamespace(new_page=lambda viewport: FakePage(self), close=self.close)

    def close(self):
        self.closed += 1


class PreviewInProcessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(make_video.shutil.rmtree, self.tmp, True)
        scenes = self.tmp / "scenes"
        scenes.mkdir()
        self.build = self.tmp / "build"
        self.timed = []
        for index, scene_id in enumerate(["intro", "outro"]):
            html = scenes / f"{scene_id}.html"
            html.write_text(f"<p>{scene_id}</p>", encoding="utf-8")
            scene = make_video.Scene(scene_id, html, [], 0.0, 0.0)
            start = index * 4.0
            beats = [make_video.TimedBeat("a", start, start + 2), make_video.TimedBeat("b", start + 2, start + 4)]
            self.timed.append(make_video.TimedScene(scene, start, start + 4, beats))
        self.fake = FakePlaywright()
        module = types.ModuleType("playwright.sync_api")
        module.sync_playwright = self.fake.sync_playwright
        package = types.ModuleType("playwright")
        package.sync_api = module
        patcher = mock.patch.dict(sys.modules, {"playwright": package, "playwright.sync_api": module})
        patcher.start()
        self.addCleanup(patcher.stop)
        ffmpeg = mock.patch.object(make_video, "run_ffmpeg")
        self.run_ffmpeg = ffmpeg.start()
        self.addCleanup(ffmpeg.stop)

    def preview(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            make_video.render_preview(self.timed, 30, self.build)
        return out.getvalue(), err.getvalue()

    def cache_entries(self):
        return sorted(path.name.split("-")[0] for path in (self.build / "preview" / "cache").iterdir())

    def stills(self):
        return sorted(path.name for path in (self.build / "preview").glob("*.png"))

    def test_first_preview_shoots_every_scene_and_fills_cache(self):
        preview = self.build / "preview"
        preview.mkdir(parents=True)
        (preview / "0099.png").write_bytes(b"old")
        out, err = self.preview()
        self.assertEqual(self.fake.starts, 1)
        self.assertEqual(self.fake.closed, 1)
        self.assertEqual(len(self.fake.loaded), 2)
        self.assertEqual(self.cache_entries(), ["intro", "outro"])
        self.assertEqual(self.stills(), ["0001.png", "0002.png", "0003.png", "0004.png"])
        self.assertIn("0004.png  outro beat 1", out)
        self.assertNotIn("reusing", out)
        self.assertEqual(err, "")
        self.run_ffmpeg.assert_called_once()

    def test_unchanged_preview_reuses_cache_without_browser(self):
        self.preview()
        out, _ = self.preview()
        self.assertEqual(self.fake.starts, 1)
        self.assertIn("intro: unchanged, reusing cached stills", out)
        self.assertIn("outro: unchanged, reusing cached stills", out)
        self.assertEqual(self.stills(), ["0001.png", "0002.png", "0003.png", "0004.png"])

    def test_scene_with_page_error_is_not_cached(self):
        self.fake.failing.add("outro.html")
        out, err = self.preview()
        self.assertIn("outro: not cached, it printed 1 warning(s)", out)
        self.assertIn("WARNING in scene outro: JS error: boom", err)
        self.assertNotIn("intro", err)
        self.assertEqual(self.cache_entries(), ["intro"])
        self.assertEqual(self.stills(), ["0001.png", "0002.png", "0003.png", "0004.png"])

    def test_edited_scene_is_shot_again_alone(self):
        self.preview()
        self.timed[1].scene.html.write_text("<p>outro, edited</p>", encoding="utf-8")
        out, _ = self.preview()
        self.assertEqual(self.fake.starts, 2)
        self.assertEqual(len(self.fake.loaded), 3)
        self.assertTrue(self.fake.loaded[-1].endswith("outro.html"))
        self.assertIn("intro: unchanged, reusing cached stills", out)
        self.assertNotIn("outro: unchanged", out)
        self.assertEqual(self.cache_entries(), ["intro", "outro", "outro"])


if __name__ == "__main__":
    unittest.main()
