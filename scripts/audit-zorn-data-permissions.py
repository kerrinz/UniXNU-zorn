#!/usr/bin/env python3
"""Audit actual before-launchd metadata calls and every linked numeric policy row."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--kernel", type=Path, default=ROOT / "UniXNU/out/zorn/kernel/kernel.macho")
parser.add_argument("--output", type=Path, default=ROOT / "out/zorn/data-permissions-audit.json")
args = parser.parse_args()
symbols = {}
for line in subprocess.check_output(["xcrun", "nm", "-n", str(args.kernel)], text=True).splitlines():
    fields = line.split()
    if len(fields) == 3 and re.fullmatch("[0-9a-fA-F]+", fields[0]):
        symbols[fields[2]] = int(fields[0], 16)
assert "_zorn_boot_data_permissions" in symbols and "_zorn_data_permission_specs" in symbols, "numeric Data policy missing"


def calls(name):
    text = subprocess.check_output(["xcrun", "llvm-objdump", "--disassemble", "--disassemble-symbols=" + name, str(args.kernel)], text=True)
    return {int(v, 16) for v in re.findall(r"\b(?:bl|b)\s+0x([0-9a-f]+)\b", text)}


assert symbols["_zorn_boot_data_permissions"] in calls("_zorn_boot_service_policy"), "policy does not call metadata preparation"
required = ("_zorn_ufs_boot_policy_allowed", "_open", "_fchown", "_fchmod", "_sys_fstat64", "_copyin", "_sys_close")
actual = calls("_zorn_boot_data_permissions")
assert all(symbols[name] in actual for name in required), "missing guard or real ownership/verification calls"
assert symbols["_zorn_boot_data_marker_existing"] in actual, "retained policy does not verify its marker"
existing = calls("_zorn_boot_data_marker_existing")
assert all(symbols[name] in existing for name in ("_native_ufs_store_mode", "_zorn_ufs_boot_policy_allowed", "_open", "_sys_fstat64", "_read", "_copyin", "_sys_close")), "existing marker lacks real volume/read guards"
for forbidden in ("_write", "_pwrite", "_mkdir", "_unlink", "_rename", "_fchown", "_fchmod", "_fsync"):
    assert symbols.get(forbidden) not in existing, "existing marker verification mutates Data"
for forbidden in ("_write", "_pwrite", "_mkdir", "_unlink", "_rename"):
    assert symbols.get(forbidden) not in actual, "metadata policy changes file contents/layout"
sys.path.insert(0, str(ROOT / "UniXNU/kits/XnuPrelink"))
import native_prelink as np
data = args.kernel.read_bytes()
meta = np.macho(data)


def read(va, size):
    offset = np.backed_offset(meta["segments"], va, size, len(data))
    return data[offset:offset + size]


source = ROOT / "UniXNU-zorn/native/startup-policy/data-permissions.json"
proof = json.loads(source.read_text())
base = symbols["_zorn_data_permission_specs"]
for i, expected in enumerate(proof["entries"]):
    address, uid, gid, mode, kind = struct.unpack("<Q4I", read(base + i * 24, 24))
    path = read(address, 480).split(b"\0", 1)[0].decode("ascii")
    relative = expected["relative"]
    assert path == "/private/var" + ("/" + relative if relative else "")
    assert (uid, gid, mode, kind) == tuple(expected[k] for k in ("uid", "gid", "mode", "type"))
result = {"kernel_sha256": hashlib.sha256(data).hexdigest(),
          "manifest_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "actual_before_launchd_call": True, "guard_metadata_change_and_readback_calls": True,
          "all_linked_paths_and_numeric_metadata_match": True, "checked_policy_rows": len(proof["entries"]),
          "no_file_content_or_layout_mutation_calls": True, "hardware_verified": False}
result["retained_marker_actual_readonly_calls"] = True
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
