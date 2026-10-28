#!/usr/bin/env python3
"""Check actual store bridges, original transport calls and Data-file proof."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--kernel", type=Path, default=ROOT / "UniXNU/out/zorn/kernel/kernel.macho")
p.add_argument("--output", type=Path, default=ROOT / "out/zorn/data-store-link-audit.json")
a = p.parse_args()
names = {}
for line in subprocess.check_output(["xcrun", "nm", "-n", str(a.kernel)], text=True).splitlines():
    f = line.split()
    if len(f) == 3 and re.fullmatch("[0-9a-fA-F]+", f[0]):
        names[f[2]] = int(f[0], 16)


def calls(name):
    text = subprocess.check_output(["xcrun", "llvm-objdump", "--disassemble", "--disassemble-symbols=" + name, str(a.kernel)], text=True)
    return {int(x, 16) for x in re.findall(r"\b(?:b|bl)\s+0x([0-9a-f]+)", text)}


for suffix in ["mode", "open", "read", "write", "sync", "gpt_check"]:
    source, target = "_native_ufs_store_" + suffix, "_zorn_data_store_" + suffix
    assert names[target] in calls(source), "missing actual provider bridge: " + source
scsi = {v for n, v in names.items() if "hostScsiDir" in n and ".cold" not in n}
assert len(scsi) == 1 and calls("_zorn_data_store_write") & scsi and calls("_zorn_data_store_sync") & scsi
assert names["_zorn_boot_data_marker"] in calls("_zorn_boot_service_policy"), "Data marker is not reached before launchd"
marker = calls("_zorn_boot_data_marker")
required = ["_zorn_ufs_boot_policy_allowed", "_native_ufs_store_mode", "_open", "_read", "_write", "_fsync", "_sys_fstat64", "_sys_close", "_copyin", "_copyout"]
assert all(names.get(name) in marker for name in required), "marker lacks its actual guard/file/readback calls"
assert not any(names.get(name) in marker for name in ["_unlink", "_truncate", "_ftruncate"])
proof = {"kernel_sha256": hashlib.file_digest(a.kernel.open("rb"), "sha256").hexdigest(),
         "six_actual_provider_bridges": True, "actual_write_and_sync_reach_original_hostScsiDir": True,
         "actual_before_launchd_marker_guard_write_fsync_reopen_readback": True,
         "no_marker_unlink_or_truncate_calls": True, "hardware_qualified": False}
a.output.write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps(proof, indent=2))
