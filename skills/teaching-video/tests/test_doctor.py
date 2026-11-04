import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402


def present(name):
    return make_video.Check(name, True, "present", True)


class DoctorTest(unittest.TestCase):
    def run_doctor(self, which):
        # Playwright, edge-tts and SAPI are stubbed: launching Chromium and listing voices is slow and needs the network.
        with mock.patch.object(make_video.shutil, "which", which), \
                mock.patch.object(make_video, "_version_line", return_value="version 8.1"), \
                mock.patch.object(make_video, "check_playwright", return_value=[present("playwright"), present("chromium")]), \
                mock.patch.object(make_video, "check_edge_tts", return_value=present("edge-tts")), \
                mock.patch.object(make_video, "check_sapi", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = make_video.run_doctor("en")
        return code, out.getvalue()

    def test_missing_ffmpeg_fails_with_install_hint(self):
        code, out = self.run_doctor(lambda name: None if name == "ffmpeg" else f"/bin/{name}")
        self.assertNotEqual(code, 0)
        self.assertIn("MISSING  ffmpeg", out)
        self.assertIn("ffmpeg: winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg", out)

    def test_all_required_tools_present_succeeds(self):
        code, out = self.run_doctor(lambda name: f"/bin/{name}")
        self.assertEqual(code, 0)
        self.assertIn("every required tool is present", out)

    def test_missing_edge_tts_reports_pip_install(self):
        with mock.patch.dict(sys.modules, {"edge_tts": None}):
            check = make_video.check_edge_tts("hu")
        self.assertFalse(check.ok)
        self.assertEqual(check.install, f"{sys.executable} -m pip install edge-tts")


if __name__ == "__main__":
    unittest.main()
