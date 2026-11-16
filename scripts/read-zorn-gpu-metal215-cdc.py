#!/usr/bin/env python3
"""Capture the fixed K80 CDC trial on macOS and verify its boot marker."""

import array
import fcntl
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import termios
from threading import Event, Thread
import time

PROBE_TAG = 'e24d087ce9994306ac3c936887498d2e' # exact signed Metal probe identity

PRODUCT = "Redmi K80 XNU CDC"


def find_port(registry, identity):
    if not all(re.search(rf'"{key}" = {value}$', registry, re.M)
               for key, value in (("idVendor", 0x1209), ("idProduct", 1))):
        return None
    serials = set(re.findall(r'"USB Serial Number" = "([^"]+)"$', registry, re.M))
    ports = set(re.findall(r'"IOCalloutDevice" = "(/dev/cu\.usbmodem[A-Za-z0-9._-]+)"$',
                           registry, re.M))
    if serials != {identity} or len(ports) != 1:
        return None
    return ports.pop()


def capture(port, output, stop, deadline):
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        fcntl.ioctl(fd, termios.TIOCEXCL)
        original = termios.tcgetattr(fd)
        attrs = termios.tcgetattr(fd)
        attrs[:6] = [0, 0, termios.CS8 | termios.CREAD | termios.CLOCAL, 0,
                     termios.B115200, termios.B115200]
        attrs[6][termios.VMIN] = 1
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        try:
            fcntl.ioctl(fd, termios.TIOCMBIS, array.array("i", [termios.TIOCM_DTR]))
            with output.open("xb") as stream:
                while not stop.is_set() and time.monotonic() < deadline:
                    ready, _, _ = select.select([fd], [], [], 0.25)
                    if not ready:
                        continue
                    try:
                        chunk = os.read(fd, 4096)
                    except BlockingIOError:
                        continue
                    except OSError as error:
                        if error.errno in (5, 6):
                            break
                        raise
                    if not chunk:
                        break
                    if stream.tell() + len(chunk) > 119808:
                        raise ValueError("unexpected CDC data volume")
                    stream.write(chunk)
                    stream.flush()
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSANOW, original)
            except (OSError, termios.error):
                pass  # The device may already have detached.
    finally:
        os.close(fd)


def main():
    from zorn_ios26_gpu_v215_metal_trial import TAG, TRIAL, validate

    bundle = TRIAL / "bundle.json"
    validate(bundle)
    out = TRIAL / "trial"
    raw = out / "cdc.raw"
    report = out / "cdc-capture.json"
    if any(path.exists() or path.is_symlink()
           for path in (raw, report, out / "one-shot.claim.json")):
        raise ValueError("CDC trial has existing evidence or a claim")
    stop, polling = Event(), Event()
    errors, ports = [], []

    def receive():
        deadline = time.monotonic() + 610
        identity = "ZORN26" + TAG[:12].upper()
        try:
            while not stop.is_set() and time.monotonic() < deadline:
                result = subprocess.run(
                    ["/usr/sbin/ioreg", "-r", "-n", PRODUCT, "-l", "-w0"],
                    text=True, timeout=3, capture_output=True, check=False,
                )
                polling.set()
                port = find_port(result.stdout, identity) if result.returncode == 0 else None
                if port:
                    ports.append(port)
                    capture(port, raw, stop, deadline)
                    return
                stop.wait(0.25)
        except (OSError, subprocess.SubprocessError, ValueError, termios.error) as error:
            errors.append(str(error))
        finally:
            polling.set()

    receiver = Thread(target=receive)
    receiver.start()
    try:
        if not polling.wait(5) or errors:
            raise RuntimeError("CDC listener could not start")
        result = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).with_name("zorn_ios26_gpu_v215_metal_trial.py")),
             "--bundle", str(bundle), "--admission", str(TRIAL / "admission.json")],
            check=False,
        )
    finally:
        stop.set()
        receiver.join()

    run_file = out / "run.json"
    run = json.loads(run_file.read_text()) if run_file.is_file() else {}
    data = raw.read_bytes() if raw.is_file() else b""
    verdict = dict(transport_frames_valid=False, frames=[], frame_count=0,
                   full_GPU_qualification=False, known_image_complete=False)
    envelope_valid = False
    try:
        from inspect_ios26_gpu_progress211 import inspect_progress
        verdict.update(inspect_progress(data, TAG, PROBE_TAG))
        from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope
        record = inspect_envelope((out / "after-log.bin").read_bytes(), bytes.fromhex(TAG),
                                  (out / "before-log.bin").read_bytes())
        envelope_valid = bool(record and result.returncode == 0 and
                              run.get("recovery_identity_after", {}).get("family"))
    except (OSError, ValueError) as error:
        errors.append(str(error))
    verified = bool(verdict["transport_frames_valid"] and envelope_valid and not errors)
    verdict.update(verified=verified, envelope_valid=envelope_valid,
                   port=ports[0] if ports else None, bytes=len(data),
                   runner_exit=result.returncode, errors=errors)
    with report.open("x") as stream:
        json.dump(verdict, stream, indent=2)
        stream.write("\n")
    print(json.dumps(verdict))
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
