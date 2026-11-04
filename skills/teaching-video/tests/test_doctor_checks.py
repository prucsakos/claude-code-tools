import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class CheckBinaryTest(unittest.TestCase):
    def test_missing_binary_is_a_required_failure_with_install_command(self):
        with mock.patch.object(make_video.shutil, "which", return_value=None):
            check = make_video.check_binary("ffmpeg")
        self.assertEqual(check, make_video.Check("ffmpeg", False, "missing", True, make_video.FFMPEG_INSTALL))

    def test_version_falls_back_to_first_stderr_line(self):
        run = mock.Mock(return_value=completed(stdout="", stderr="ffmpeg version 7\nbuilt with gcc"))
        with mock.patch.object(make_video.shutil, "which", return_value="/bin/ffmpeg"), \
                mock.patch.object(make_video.subprocess, "run", run):
            check = make_video.check_binary("ffmpeg")
        self.assertEqual(check, make_video.Check("ffmpeg", True, "ffmpeg version 7", True))
        self.assertEqual(run.call_args.args[0], ["/bin/ffmpeg", "-version"])

    def test_version_without_output_reports_found(self):
        with mock.patch.object(make_video.shutil, "which", return_value="/bin/ffprobe"), \
                mock.patch.object(make_video.subprocess, "run", return_value=completed()):
            check = make_video.check_binary("ffprobe")
        self.assertEqual(check, make_video.Check("ffprobe", True, "found", True))


def fake_playwright(launch):
    """Builds a fake playwright.sync_api module whose chromium.launch is the given callable."""
    class Session:
        def __enter__(self):
            return types.SimpleNamespace(chromium=types.SimpleNamespace(launch=launch))

        def __exit__(self, *exc):
            return False

    module = types.ModuleType("playwright.sync_api")
    module.sync_playwright = Session
    return module


class CheckPlaywrightTest(unittest.TestCase):
    def run_check(self, sync_api):
        with mock.patch.dict(sys.modules, {"playwright": types.ModuleType("playwright"), "playwright.sync_api": sync_api}), \
                mock.patch("importlib.metadata.version", return_value="1.58.0"):
            return make_video.check_playwright()

    def test_missing_package_fails_both_checks(self):
        package, chromium = self.run_check(None)
        self.assertEqual((package.name, package.ok, package.required, package.detail), ("playwright", False, True, "missing"))
        self.assertTrue(package.install.endswith("-m pip install playwright"))
        self.assertEqual((chromium.name, chromium.ok, chromium.required), ("chromium", False, True))
        self.assertEqual(chromium.detail, "not checked (Playwright is missing)")
        self.assertTrue(chromium.install.endswith("-m playwright install chromium"))

    def test_launch_error_reports_only_its_first_line(self):
        def launch():
            raise Exception("Executable doesn't exist\nat C:/ms-playwright/chromium")

        package, chromium = self.run_check(fake_playwright(launch))
        self.assertEqual(package, make_video.Check("playwright", True, "1.58.0", True))
        self.assertFalse(chromium.ok)
        self.assertTrue(chromium.required)
        self.assertEqual(chromium.detail, "does not launch (Executable doesn't exist)")
        self.assertTrue(chromium.install.endswith("-m playwright install chromium"))

    def test_successful_launch_reports_browser_version_and_closes_it(self):
        browser = mock.Mock(version="130.0")
        package, chromium = self.run_check(fake_playwright(lambda: browser))
        self.assertEqual(package, make_video.Check("playwright", True, "1.58.0", True))
        self.assertEqual(chromium, make_video.Check("chromium", True, "launches (130.0)", True))
        browser.close.assert_called_once_with()


def fake_edge_tts(create):
    module = types.ModuleType("edge_tts")
    module.VoicesManager = types.SimpleNamespace(create=create)
    return module


class CheckEdgeTtsTest(unittest.TestCase):
    def run_check(self, module, language="en"):
        with mock.patch.dict(sys.modules, {"edge_tts": module}), \
                mock.patch("importlib.metadata.version", return_value="7.0.0"):
            return make_video.check_edge_tts(language)

    def test_missing_package_gives_pip_command(self):
        check = self.run_check(None)
        self.assertEqual((check.name, check.ok, check.required, check.detail), ("edge-tts", False, True, "missing"))
        self.assertTrue(check.install.endswith("-m pip install edge-tts"))

    def test_network_error_keeps_package_ok(self):
        async def create():
            raise OSError("no route to host")

        check = self.run_check(fake_edge_tts(create))
        self.assertEqual(check, make_video.Check("edge-tts", True, "7.0.0; voices not checked (network error: OSError)", True))

    def test_reports_voice_count_for_requested_language(self):
        manager = mock.Mock()
        manager.find.return_value = ["voice-a", "voice-b", "voice-c"]

        async def create():
            return manager

        check = self.run_check(fake_edge_tts(create), language="en")
        self.assertEqual(check, make_video.Check("edge-tts", True, "7.0.0; 3 voices for language 'en'", True))
        manager.find.assert_called_once_with(Language="en")


class CheckSapiTest(unittest.TestCase):
    def run_check(self, result):
        run = mock.Mock(return_value=result)
        with mock.patch.object(make_video.sys, "platform", "win32"), \
                mock.patch.object(make_video.subprocess, "run", run):
            return make_video.check_sapi(), run

    def test_not_windows_gives_no_checks(self):
        run = mock.Mock()
        with mock.patch.object(make_video.sys, "platform", "linux"), \
                mock.patch.object(make_video.subprocess, "run", run):
            self.assertEqual(make_video.check_sapi(), [])
        run.assert_not_called()

    def test_powershell_failure_is_optional_and_shows_stderr(self):
        checks, run = self.run_check(completed(returncode=1, stderr="  Add-Type failed\n"))
        self.assertEqual(checks, [make_video.Check("sapi voices", False, "not listed (Add-Type failed)", False)])
        self.assertEqual(run.call_args.args[0][0], "powershell")

    def test_lists_installed_voice_names(self):
        checks, _ = self.run_check(completed(stdout="Zira\n\nDavid\n"))
        self.assertEqual(checks, [make_video.Check("sapi voices", True, "Zira, David", False)])

    def test_no_voices_is_reported_as_none_installed(self):
        checks, _ = self.run_check(completed(stdout=""))
        self.assertEqual(checks, [make_video.Check("sapi voices", False, "none installed", False)])


if __name__ == "__main__":
    unittest.main()
