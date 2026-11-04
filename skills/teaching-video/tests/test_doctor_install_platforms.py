import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_video  # noqa: E402


def which_only(*present):
    """A fake shutil.which that finds only the named tools."""
    return lambda name: f"/usr/bin/{name}" if name in present else None


def missing(name):
    return make_video.Check(name, False, "missing", True, "install it")


class FfmpegInstallCommandPlatformTest(unittest.TestCase):
    def install_command(self, platform, *present):
        with mock.patch.object(make_video.sys, "platform", platform), \
                mock.patch.object(make_video.shutil, "which", which_only(*present)):
            return make_video.ffmpeg_install_command()

    def test_macos_with_brew_uses_brew(self):
        self.assertEqual(self.install_command("darwin", "brew"), ["brew", "install", "ffmpeg"])

    def test_linux_with_apt_get_uses_apt_get_without_prompt(self):
        self.assertEqual(self.install_command("linux", "apt-get"),
                         ["sudo", "apt-get", "install", "-y", "ffmpeg"])

    def test_macos_with_only_apt_get_has_no_command(self):
        self.assertIsNone(self.install_command("darwin", "apt-get"))

    def test_linux_with_only_brew_has_no_command(self):
        self.assertIsNone(self.install_command("linux", "brew"))


class InstallMissingPythonTest(unittest.TestCase):
    def test_missing_python_is_reported_for_manual_install_and_ffmpeg_still_installed(self):
        runs = []

        def run(command):
            runs.append(command)
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(make_video.sys, "platform", "linux"), \
                mock.patch.object(make_video.shutil, "which", which_only("apt-get")), \
                mock.patch.object(make_video.subprocess, "run", run), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            installed = make_video.install_missing([missing("python"), missing("ffmpeg")])
        self.assertIs(installed, True)
        self.assertEqual(runs, [["sudo", "apt-get", "install", "-y", "ffmpeg"]])
        self.assertIn("doctor: install Python 3.9 or newer manually", out.getvalue().splitlines())


if __name__ == "__main__":
    unittest.main()
