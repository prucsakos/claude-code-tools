import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402


def present(name):
    return make_video.Check(name, True, "present", True)


def missing(name):
    return make_video.Check(name, False, "missing", True, "install it")


class DoctorInstallTest(unittest.TestCase):
    def run_doctor(self, check_rounds, returncode=0):
        """Runs --doctor --install where report_checks returns check_rounds in turn; records printed lines and run commands."""
        events = []
        rounds = iter(check_rounds)

        def report_checks(language):
            events.append(("check",))
            return next(rounds)

        def run(command):
            events.append(("run", command))
            return subprocess.CompletedProcess(command, returncode)

        out = io.StringIO()

        def capture_print(*args, **kwargs):
            line = " ".join(map(str, args))
            out.write(line + "\n")
            events.append(("print", line))

        with mock.patch.object(make_video, "report_checks", report_checks), \
                mock.patch.object(make_video.sys, "platform", "win32"), \
                mock.patch.object(make_video.shutil, "which", lambda name: f"C:/bin/{name}.exe"), \
                mock.patch.object(make_video.subprocess, "run", run), \
                mock.patch("builtins.print", capture_print):
            code = make_video.run_doctor("en", install=True)
        return code, events, out.getvalue()

    def test_missing_tools_are_installed_in_order_and_checked_again(self):
        code, events, out = self.run_doctor([[missing("ffmpeg"), missing("edge-tts")], []])
        self.assertEqual(code, 0)
        pip = [sys.executable, "-m", "pip", "install", "edge-tts"]
        winget = ["winget", "install", "--id", "Gyan.FFmpeg", "-e"]
        self.assertEqual([event[1] for event in events if event[0] == "run"], [pip, winget])
        for command in (pip, winget):
            printed = events.index(("print", f"doctor: running {subprocess.list2cmdline(command)}"))
            self.assertLess(printed, events.index(("run", command)))
        self.assertEqual(events[-2:], [("check",), ("print", "doctor: every required tool is present")])

    def test_nothing_missing_runs_no_install_command(self):
        code, events, out = self.run_doctor([[]])
        self.assertEqual(code, 0)
        self.assertNotIn("run", [event[0] for event in events])
        self.assertEqual([event for event in events if event[0] == "check"], [("check",)])

    def test_failing_install_command_stops_with_non_zero_exit(self):
        code, events, out = self.run_doctor([[missing("playwright"), missing("chromium")]], returncode=1)
        self.assertNotEqual(code, 0)
        self.assertEqual([event[0] for event in events].count("run"), 1)
        self.assertIn("doctor: install failed (exit code 1)", out)
        self.assertIn("pip install playwright", out)

    def test_ffmpeg_without_package_manager_prints_manual_command(self):
        with mock.patch.object(make_video.sys, "platform", "win32"), \
                mock.patch.object(make_video.shutil, "which", return_value=None), \
                mock.patch.object(make_video.subprocess, "run") as run, \
                contextlib.redirect_stdout(io.StringIO()) as out:
            installed = make_video.install_missing([missing("ffmpeg"), missing("ffprobe")])
        self.assertTrue(installed)
        run.assert_not_called()
        self.assertIn(f"install ffmpeg manually: {make_video.FFMPEG_INSTALL}", out.getvalue())

    def test_without_install_flag_nothing_is_installed(self):
        with mock.patch.object(make_video, "report_checks", return_value=[missing("edge-tts")]), \
                mock.patch.object(make_video, "install_missing") as install_missing, \
                contextlib.redirect_stdout(io.StringIO()):
            code = make_video.run_doctor("en")
        self.assertNotEqual(code, 0)
        install_missing.assert_not_called()

    def test_install_without_doctor_is_rejected(self):
        with mock.patch.object(sys, "argv", ["make_video.py", "story.json", "--install"]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            make_video.parse_args()
        self.assertNotEqual(raised.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
