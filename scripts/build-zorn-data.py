#!/usr/bin/env python3
"""Build upstream RamBlock with the same independently audited storage ABI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

TREE = Path.cwd()
if "CONFIG_XNU_NATIVE_RAM_BLOCK=y" not in (TREE.parent / ".config").read_text().splitlines():
    print("RamBlock disabled for this profile")
    raise SystemExit(0)
ROOT = TREE.parents[2].parent
report_path = Path(os.environ.get("UNIXNU_ZORN_DATA_REPORT", ROOT / "out/zorn/ram-data/seed.json")).resolve()
report = json.loads(report_path.read_text())
seed = ROOT / report["seed"]
sys.path.insert(0, str(TREE / "drivers/DarwinBoot/Test"))
import packed_ramdisk
actual, header = packed_ramdisk.inspect(seed)
if any(actual[k] != report[k] for k in ("bytes", "sha256", "encoded_sha256", "encoded_bytes")) or \
        actual["bytes"] != 512 * 1024**2 or header[32:36] != b"NXSB" or not report["guest_volatile"]:
    raise SystemExit("Require the exact prepared volatile 512 MiB Data seed")
subprocess.run([sys.executable, TREE / "scripts/build-zorn-storage.py", "--component", "RamBlock"], check=True)
out = TREE / "build/ram-block"
assembly = ".section __DATA_CONST,__const\n.balign 8\n"
for name, data in [("zorn_data_expected_seed", bytes.fromhex(actual["sha256"])),
                   ("zorn_data_expected_uuid", uuid.UUID(report["volume_uuid"]).bytes)]:
    assembly += f".globl _{name}\n_{name}:\n.byte " + ",".join(str(b) for b in data) + "\n.balign 8\n"
assembly += f".globl _zorn_data_expected_bytes\n_zorn_data_expected_bytes:\n.quad {actual['bytes']}\n"
(out / "expected.S").write_text(assembly)
sdk = subprocess.check_output(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], text=True).strip()
subprocess.run(["xcrun", "clang", "-target", "arm64-apple-ios17.0", "-isysroot", sdk,
                "-c", out / "expected.S", "-o", out / "expected.o"], check=True)
subprocess.run(["xcrun", "clang", "-target", "arm64-apple-ios17.0", "-isysroot", sdk,
                "-mkernel", "-ffreestanding", "-Wall", "-Wextra", "-Werror", "-c",
                ROOT / "UniXNU-zorn/native/ufs-read/ZornVolatileData.c",
                "-o", out / "volatile.o"], check=True)
subprocess.run(["xcrun", "ar", "rcs", out / "libRamBlock.a", out / "expected.o", out / "volatile.o"], check=True)
report["archive_sha256"] = hashlib.sha256((out / "libRamBlock.a").read_bytes()).hexdigest()
(out / "seed-inputs.json").write_text(json.dumps(report, indent=2) + "\n")
print("PASS: upstream RamBlock, exact seed identity; optional bounded K80 store defaults off")
