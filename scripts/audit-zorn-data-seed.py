#!/usr/bin/env python3
"""Match the packaged RAM Data report to its actual kernel trust constants."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--report", required=True, type=Path)
p.add_argument("--kernel", type=Path, default=ROOT / "UniXNU/out/zorn/kernel/kernel.macho")
p.add_argument("--output", type=Path, default=ROOT / "out/zorn/data-seed-audit.json")
a = p.parse_args()
report = json.loads(a.report.read_text())
b = a.kernel.read_bytes()
assert struct.unpack_from("<I", b)[0] == 0xfeedfacf
segments = []
at = 32
for _ in range(struct.unpack_from("<I", b, 16)[0]):
    cmd, size = struct.unpack_from("<II", b, at)
    assert size >= 8 and at + size <= len(b)
    if cmd == 0x19:
        vm, vs, offset, length = struct.unpack_from("<4Q", b, at + 24)
        segments.append((vm, offset, length))
    at += size
names = {}
for line in subprocess.check_output(["xcrun", "nm", "-n", str(a.kernel)], text=True).splitlines():
    f = line.split()
    if len(f) == 3 and re.fullmatch("[0-9a-fA-F]+", f[0]):
        names[f[2]] = int(f[0], 16)
expected = {"_zorn_data_expected_seed": bytes.fromhex(report["sha256"]),
    "_zorn_data_expected_uuid": uuid.UUID(report["volume_uuid"]).bytes,
    "_zorn_data_expected_bytes": struct.pack("<Q", report["bytes"])}
for name, value in expected.items():
    va = names[name]
    matches = [offset + va - vm for vm, offset, length in segments if vm <= va and va + len(value) <= vm + length]
    assert len(matches) == 1 and b[matches[0]:matches[0] + len(value)] == value, name + " differs from the selected seed"
proof = {"kernel_sha256": hashlib.sha256(b).hexdigest(), "report_sha256": hashlib.sha256(a.report.read_bytes()).hexdigest(),
    "seed": report["seed"], "volume_uuid": report["volume_uuid"], "logical_bytes": report["bytes"],
    "actual_kernel_seed_sha_uuid_size_match": True, "hardware_qualified": False}
a.output.write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps(proof, indent=2))
