#!/usr/bin/env python3
"""Read the zorn UniXNU checkpoint block from recovery over adb.

Only reads /dev/block/by-name/userdata on the K80 with serial 92988a43.
The 4 KiB block is 4 MiB beyond the end of the flashed SHNGROOT image.
"""

import argparse
import subprocess
import sys
from pathlib import Path


SERIAL = "92988a43"
BLOCK_SIZE = 4096
LOG_BLOCK = 9382658048 // BLOCK_SIZE + 1024
FORMATS = {b"ZORNLOG1": (510, 8), b"ZORNLOG2": (340, 12)}


def from_recovery():
    adb = ["adb", "-s", SERIAL]
    serial = subprocess.run(adb + ["get-serialno"], capture_output=True, text=True, check=True)
    if serial.stdout.strip() != SERIAL:
        raise ValueError(f"unexpected adb serial: {serial.stdout.strip()!r}")
    dd = (f"dd if=/dev/block/by-name/userdata bs={BLOCK_SIZE} "
          f"skip={LOG_BLOCK} count=1 2>/dev/null")
    command = adb + ["exec-out", "sh", "-c", dd]
    result = subprocess.run(command, capture_output=True, check=True)
    if len(result.stdout) != BLOCK_SIZE:
        raise ValueError(f"read {len(result.stdout)} bytes, expected {BLOCK_SIZE}: {result.stderr!r}")
    return result.stdout


def decode(block):
    if len(block) != BLOCK_SIZE:
        raise ValueError(f"log block is {len(block)} bytes, expected {BLOCK_SIZE}")
    if block[:8] not in FORMATS:
        raise ValueError(f"bad log magic: {block[:8]!r}")
    capacity, width = FORMATS[block[:8]]
    count = int.from_bytes(block[8:12], "little")
    if count > capacity:
        raise ValueError(f"invalid checkpoint count: {count}")
    next_slot = int.from_bytes(block[12:16], "little") if block[:8] == b"ZORNLOG2" else 0
    if next_slot >= capacity or (block[:8] == b"ZORNLOG2" and count < capacity and next_slot != count):
        raise ValueError(f"invalid next slot: {next_slot}")
    start = next_slot if block[:8] == b"ZORNLOG2" and count == capacity else 0
    words = []
    for index in range(count):
        slot = (start + index) % capacity
        offset = 16 + width * slot
        raw = block[offset:offset + width].split(b"\0", 1)[0]
        if not raw or any(byte < 32 or byte > 126 for byte in raw):
            raise ValueError(f"invalid checkpoint at {index}: {raw!r}")
        words.append(raw.decode("ascii"))
    return words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", type=Path, help="decode an existing 4096-byte local dump")
    parser.add_argument("--save", type=Path, help="save the raw block locally after adb read")
    parser.add_argument("--tail", type=int, default=80, help="print this many latest words (default: 80)")
    args = parser.parse_args()
    if args.tail < 1:
        parser.error("--tail must be positive")
    if args.block and args.save:
        parser.error("--save is only for adb reads")
    block = args.block.read_bytes() if args.block else from_recovery()
    words = decode(block)
    if args.save:
        args.save.write_bytes(block)
    print(f"{len(words)} checkpoints; showing last {min(len(words), args.tail)}")
    for index, word in enumerate(words[max(0, len(words) - args.tail):],
                                  start=max(0, len(words) - args.tail)):
        print(f"{index:03d} {word}")
    if "PANICBEGIN" in words:
        begin = len(words) - 1 - words[::-1].index("PANICBEGIN")
        if "PANICEND" in words[begin + 1:]:
            end = words.index("PANICEND", begin + 1)
            print("panic: " + "".join(words[begin + 1:end]))
    output = []
    partial = None
    for word in words:
        if word == "USRBEGIN":
            partial = []
        elif word == "USREND":
            if partial is not None:
                output.append("".join(partial))
            partial = None
        elif partial is not None:
            partial.append(word)
    if output:
        print("user output: " + "".join(output))
    names = []
    partial = None
    for word in words:
        if word == "SCTBEGIN":
            partial = []
        elif word == "SCTEND":
            if partial is not None:
                name = "".join(partial)
                if not names or names[-1] != name:
                    names.append(name)
            partial = None
        elif partial is not None:
            partial.append(word)
    if names:
        print("sysctl names: " + " | ".join(names))


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        sys.exit(str(error))
