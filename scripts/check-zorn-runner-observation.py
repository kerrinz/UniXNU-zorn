#!/usr/bin/env python3
"""Exercise the actual optional camera/recovery loop without any USB access."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = Path(__file__).with_name("run-zorn-debug.py")
    spec = importlib.util.spec_from_file_location("zorn_runner_checked", source)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    passed = []

    def exercise(name, recovery=None, after=30, cost=0, failure=False, adb_error=None, initial=0):
        clock = SimpleNamespace(now=0)
        shots = []

        def sleep(seconds):
            clock.now += seconds

        def state():
            if adb_error:
                raise OSError("ADB transport failure")
            if clock.now == 0:
                clock.now = initial
            return "recovery" if recovery is not None and clock.now >= recovery else None

        def capture(elapsed):
            shots.append(elapsed)
            clock.now += cost
            if failure:
                raise OSError("camera unavailable")

        error = None
        with patch.object(runner, "time", SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep)), \
                patch.object(runner, "adb_state", state), contextlib.redirect_stdout(io.StringIO()):
            try:
                runner.wait_for_recovery(120, after, capture)
            except (RuntimeError, OSError) as caught:
                error = str(caught)
        assert len(shots) <= 1, name
        assert clock.now <= 122, (name, clock.now)  # A camera cannot reset the absolute deadline.
        passed.append(name)
        return shots, error

    assert exercise("disabled", recovery=80, after=0) == ([], None)
    assert exercise("early recovery", recovery=20) == ([], None)
    assert exercise("recovery wins at capture threshold", recovery=30) == ([], None)
    assert exercise("single bounded capture", recovery=100, cost=25) == ([30], None)
    assert exercise("camera failure preserves recovery", recovery=80, failure=True) == ([30], None)
    shots, error = exercise("capture does not extend timeout", cost=25)
    assert shots == [30] and "no recovery ADB after 120 seconds" in error
    assert exercise("insufficient deadline headroom", recovery=110, initial=100) == ([], None)
    shots, error = exercise("ADB failure remains fatal", adb_error=True)
    assert not shots and error == "ADB transport failure"

    with patch.object(runner, "adb_state", lambda: "device"):
        try:
            runner.wait_for_recovery(120, 30, lambda _: None)
        except RuntimeError as error:
            assert "unexpected adb state" in str(error)
        else:
            raise AssertionError("Android/device state must remain fatal")
    passed.append("unexpected device state remains fatal")

    with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
        out = Path(folder)
        for name, outcome in [("camera success", subprocess.CompletedProcess([], 0, "frame", "")),
                              ("camera rejected", subprocess.CompletedProcess([], 1, "", "unavailable")),
                              ("camera timeout", subprocess.TimeoutExpired("camera", 25))]:
            def fake_run(command, **kwargs):
                assert command[1:] == [str(source.with_name("capture-zorn-screen.py")), "--run", str(out)]
                assert kwargs == dict(capture_output=True, text=True, timeout=25)
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome
            with patch.object(runner.subprocess, "run", fake_run):
                runner.capture_screen(out, 900)
            record = json.loads((out / "scheduled-screen-capture.json").read_text())
            assert record["audio"] is False and record["elapsed_after_boot_seconds"] == 900
            if isinstance(outcome, Exception):
                assert "error" in record
            else:
                assert record["returncode"] == outcome.returncode
            passed.append(name)

    report = {"runner_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "actual_functions_executed": ["wait_for_recovery", "capture_screen"],
              "usb_access": False, "checks": passed}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
