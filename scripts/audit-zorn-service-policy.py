#!/usr/bin/env python3
"""Verify the actual before-launchd RAM Data policy call chain."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--kernel", type=Path, default=ROOT / "UniXNU/out/zorn/kernel/kernel.macho")
parser.add_argument("--output", type=Path, default=ROOT / "out/zorn/startup-policy-audit.json")
args = parser.parse_args()
record_path = ROOT / "UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/kern_exec.o.json"
record = json.loads(record_path.read_text().strip().rstrip(","))
flags = record["arguments"]
assert "-DXNU_ZORN_STARTUP_POLICY=1" in flags or any(
    flags[i:i + 2] == ["-D", "XNU_ZORN_STARTUP_POLICY=1"] for i in range(len(flags))), "policy hook compiled out"
symbols = {}
for line in subprocess.check_output(["xcrun", "nm", "-n", str(args.kernel)], text=True).splitlines():
    fields = line.split()
    if len(fields) == 3 and re.fullmatch("[0-9a-fA-F]+", fields[0]):
        symbols[fields[2]] = int(fields[0], 16)

def calls(name):
    assembly = subprocess.check_output(["xcrun", "llvm-objdump", "--disassemble",
        "--disassemble-symbols=" + name, str(args.kernel)], text=True)
    return {int(v, 16) for v in re.findall(r"\b(?:bl|b)\s+0x([0-9a-f]+)\b", assembly)}

assert symbols["_zorn_boot_service_policy"] in calls("_load_init_program"), "launchd startup does not call policy"
targets = ("_zorn_ufs_boot_policy_allowed", "_zorn_ufs_boot_policy_result", "_fchown", "_fchmod", "_fsync", "_sys_fstat64", "_read", "_copyin")
actual = calls("_zorn_boot_service_policy")
assert all(symbols[name] in actual for name in targets), "policy lacks its real guard/metadata/readback calls"
proof = {"kernel_sha256": hashlib.sha256(args.kernel.read_bytes()).hexdigest(),
         "compile_record_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
         "compile_flag_enabled": True, "actual_before_launchd_hook": True,
         "real_volatile_guard_and_file_readback": True,
         "call_targets": {name: hex(symbols[name]) for name in targets}, "hardware_qualified": False}
args.output.write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps(proof, indent=2))
