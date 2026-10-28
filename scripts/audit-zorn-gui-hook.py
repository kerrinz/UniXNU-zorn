#!/usr/bin/env python3
"""Refuse GUI diagnostic images whose compiled IPC observer is absent."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, default=ROOT / "UniXNU/out/zorn/kernel/kernel.macho")
    parser.add_argument("--compile-record", type=Path, default=ROOT / "UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/osfmk/DEVELOPMENT/ipc_kmsg.o.json")
    parser.add_argument("--iokit-compile-record", type=Path, default=ROOT / "UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOUserClient.cpo.json")
    parser.add_argument("--output", type=Path, default=ROOT / "out/zorn/gui-hook-audit.json")
    args = parser.parse_args()
    record = json.loads(args.compile_record.read_text().strip().rstrip(","))
    flags = record["arguments"]
    enabled = "-DXNU_NATIVE_LEGACY_DISPLAY=1" in flags or any(
        flags[i:i + 2] == ["-D", "XNU_NATIVE_LEGACY_DISPLAY=1"] for i in range(len(flags)))
    if not enabled:
        raise ValueError("ipc_kmsg.o lacks XNU_NATIVE_LEGACY_DISPLAY=1")
    iokit_record = json.loads(args.iokit_compile_record.read_text().strip().rstrip(","))
    iokit_flags = iokit_record["arguments"]
    if not ("-DXNU_NATIVE_LEGACY_DISPLAY=1" in iokit_flags or any(
            iokit_flags[i:i + 2] == ["-D", "XNU_NATIVE_LEGACY_DISPLAY=1"] for i in range(len(iokit_flags)))):
        raise ValueError("IOUserClient.cpo lacks XNU_NATIVE_LEGACY_DISPLAY=1")
    names = ("_zorn_ufs_gui_enabled", "_zorn_ufs_gui_ipc", "_ipc_port_get_receiver_task",
             "_zorn_ufs_gui_iokit", "_is_io_service_get_matching_services_bin")
    found = {name: set() for name in names}
    helpers = {"internal_io_service_get_matching_services": set(), "zorn_gui_iokit_match": set()}
    symbols = subprocess.check_output(["xcrun", "nm", "-n", str(args.kernel)], text=True)
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in found:
            found[fields[2]].add(int(fields[0], 16))
        if len(fields) == 3 and ".cold" not in fields[2]:
            for key in helpers:
                if key in fields[2]:
                    helpers[key].add((fields[2], int(fields[0], 16)))
    if any(len(values) != 1 for values in found.values()):
        raise ValueError("IPC observer targets missing or ambiguous in kernel")
    if any(len(values) != 1 for values in helpers.values()):
        raise ValueError("IOKit matching observer helpers missing or ambiguous")
    def calls_from(name):
        assembly = subprocess.run(["xcrun", "llvm-objdump", "--disassemble",
            "--disassemble-symbols=" + name, str(args.kernel)], capture_output=True, text=True, check=True)
        if assembly.stderr:
            raise ValueError(assembly.stderr)
        return {int(value, 16) for value in re.findall(r"\b(?:bl|b)\s+0x([0-9a-f]+)\b", assembly.stdout)}
    calls = calls_from("_ipc_kmsg_send")
    targets = {name: next(iter(values)) for name, values in found.items()}
    absent = [name for name in names[:3] if targets[name] not in calls]
    if absent:
        raise ValueError("ipc_kmsg_send does not call " + ", ".join(absent))
    internal, probe = (next(iter(helpers[key])) for key in helpers)
    if internal[1] not in calls_from("_is_io_service_get_matching_services_bin") or probe[1] not in calls_from(internal[0]):
        raise ValueError("IOKit matching API does not reach its observer")
    probe_calls = calls_from(probe[0])
    if any(targets[name] not in probe_calls for name in ("_zorn_ufs_gui_iokit", "_zorn_ufs_gui_enabled")):
        raise ValueError("IOKit matching observer does not reach the recorder")
    targets.update({key: next(iter(values))[1] for key, values in helpers.items()})
    proof = {"kernel_sha256": hashlib.sha256(args.kernel.read_bytes()).hexdigest(),
             "compile_record_sha256": hashlib.sha256(args.compile_record.read_bytes()).hexdigest(),
             "iokit_compile_record_sha256": hashlib.sha256(args.iokit_compile_record.read_bytes()).hexdigest(),
             "compile_flag_enabled": True, "actual_call_targets": {k: hex(v) for k, v in targets.items()},
             "audit": "pass", "hardware_qualified": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
