#!/usr/bin/env python3
"""Measure shell commands with per-run timeouts and an optional shared lock.

Usage: python measure.py WORKDIR RUNS TIMEOUT_S time|stdout LOCKFILE|none COMMAND
       [--shell auto|bash|sh|powershell|pwsh|cmd] [--lock-timeout SECONDS]

COMMAND is intentional shell code; quote its paths for the selected shell. Auto
uses PowerShell on Windows and sh elsewhere. PowerShell commands that deliberately
handle a nonzero native exit (for example, a diagnostic counter) must exit 0.
The lock file persists: deleting it could let callers lock different file objects.
"""

import argparse
from contextlib import contextmanager
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def positive_integer(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


@contextmanager
def measurement_lock(path, timeout):
    if path == "none":
        yield
        return

    # Windows byte locks can cover a byte beyond EOF; no initialization race is
    # needed. Both platforms release the lock if the owning process terminates.
    with open(path, "a+b") as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                pass
            except OSError as error:
                # Windows reports a competing byte lock as EACCES/EDEADLK.
                if os.name != "nt" or error.errno not in (13, 36):
                    raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("measurement lock wait exceeded its budget")
            time.sleep(min(0.05, remaining))
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def shell_arguments(shell, command):
    if shell == "auto":
        shell = "powershell" if os.name == "nt" else "sh"
    executable = shutil.which(shell)
    if executable is None:
        raise ValueError(f"shell is not on PATH: {shell}")
    if shell in ("powershell", "pwsh"):
        command = (
            "$ErrorActionPreference = 'Stop'\n"
            + command
            + "\nif ($LASTEXITCODE -is [int]) { exit $LASTEXITCODE }\n"
        )
        return [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]
    if shell == "cmd":
        return [executable, "/d", "/s", "/c", command]
    return [executable, "-c", command]


def terminate_tree(process):
    if os.name == "nt":
        # taskkill traverses child processes before killing the shell. Killing
        # the shell first would lose that parent/child relationship.
        result = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        if result.returncode and process.poll() is None:
            sys.stderr.buffer.write(result.stderr)
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def measure(arguments, command):
    with tempfile.TemporaryFile() as output:
        start = time.perf_counter()
        process = subprocess.Popen(
            command,
            cwd=arguments.workdir,
            stdout=output,
            stderr=None,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        try:
            code = process.wait(timeout=arguments.timeout_s)
        except subprocess.TimeoutExpired:
            terminate_tree(process)
            return "TIMEOUT", 1
        except BaseException:
            terminate_tree(process)
            raise
        elapsed = time.perf_counter() - start
        if code:
            return f"FAIL {code}", 1
        if arguments.mode == "time":
            return f"{elapsed:.6f}", 0
        output.seek(0)
        values = NUMBER.findall(output.read().decode("utf-8", errors="replace"))
        if not values or not math.isfinite(float(values[-1])):
            return "FAIL no-number", 1
        return values[-1], 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", type=Path)
    parser.add_argument("runs", type=positive_integer)
    parser.add_argument("timeout_s", type=positive_seconds)
    parser.add_argument("mode", choices=("time", "stdout"))
    parser.add_argument("lockfile")
    parser.add_argument("command")
    parser.add_argument(
        "--shell", choices=("auto", "bash", "sh", "powershell", "pwsh", "cmd"), default="auto"
    )
    parser.add_argument("--lock-timeout", type=positive_seconds)
    arguments = parser.parse_args()
    arguments.workdir = arguments.workdir.resolve()
    if not arguments.workdir.is_dir() or not os.access(arguments.workdir, os.R_OK | os.W_OK):
        parser.error("workdir must be a readable, writable directory")
    try:
        command = shell_arguments(arguments.shell, arguments.command)
        for _ in range(arguments.runs):
            try:
                with measurement_lock(
                    arguments.lockfile, arguments.lock_timeout or arguments.timeout_s
                ):
                    value, status = measure(arguments, command)
            except TimeoutError:
                print("LOCK_TIMEOUT", flush=True)
                return 1
            print(value, flush=True)
            if status:
                return status
    except (OSError, ValueError) as error:
        print(f"measure: {error}", file=sys.stderr)
        print("FAIL setup", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
