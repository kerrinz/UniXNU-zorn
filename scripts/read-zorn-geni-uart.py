#!/usr/bin/env python3
"""Capture the K80 GENI TX wire on a macOS USB UART adapter."""

import argparse
import os
from pathlib import Path
import re
import select
import termios
import time


def capture(port, output, seconds, *, ready_callback=None, stop_requested=None):
    if not port.is_absolute() or port.parent != Path("/dev") or not port.name.startswith("cu."):
        raise ValueError("select the connected adapter's /dev/cu.* device")
    if port.name in {"cu.Bluetooth-Incoming-Port", "cu.debug-console"}:
        raise ValueError("select the external K80 UART adapter")
    if not 0 < seconds <= 600:
        raise ValueError("capture duration must be between 1 and 600 seconds")

    fd = os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        original = termios.tcgetattr(fd)
        settings = original.copy()
        settings[6] = original[6].copy()
        settings[:6] = [0, 0, termios.CS8 | termios.CLOCAL | termios.CREAD,
                        0, termios.B115200, termios.B115200]
        settings[6][termios.VMIN] = 1
        settings[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, settings)
        try:
            with output.open("xb") as stream:
                end = time.monotonic() + seconds
                if ready_callback is not None:
                    ready_callback()
                while (remaining := end - time.monotonic()) > 0:
                    if stop_requested is not None and stop_requested():
                        break
                    ready, _, _ = select.select([fd], [], [], min(1, remaining))
                    if not ready:
                        continue
                    try:
                        data = os.read(fd, 4096)
                    except BlockingIOError:
                        continue
                    if not data:
                        break
                    stream.write(data)
                    stream.flush()
                return stream.tell()
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, original)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=int, default=360)
    parser.add_argument("--tag", help="Require the exact 32-digit trial ID in a complete GENI log line")
    args = parser.parse_args()
    if args.tag and not re.fullmatch(r"[0-9a-f]{32}", args.tag):
        parser.error("--tag must be 32 lowercase hexadecimal digits")
    count = capture(args.port, args.output, args.seconds)
    print(f"{count} bytes captured in {args.output}")
    if args.tag:
        prefix = f"K80 iOS26 GENI TX {args.tag}: ".encode("ascii")
        with args.output.open("rb") as stream:
            for line in stream:
                if line.startswith(prefix) and line.endswith(b"\r\n"):
                    print(f"Verified complete log line for {args.tag}")
                    return 0
        print(f"No complete log line for {args.tag}")
        return 1
    return 0 if count else 1


if __name__ == "__main__":
    raise SystemExit(main())
