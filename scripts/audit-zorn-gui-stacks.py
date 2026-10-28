#!/usr/bin/env python3
"""Check real VM/map lifetime calls in the linked, opt-in GUI sampler."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--kernel", type=Path, default=ROOT / "UniXNU/out/zorn/kernel/kernel.macho")
p.add_argument("--output", type=Path, default=ROOT / "out/zorn/gui-stack-audit.json")
a = p.parse_args()
symbols = {}
for line in subprocess.check_output(["xcrun", "nm", "-n", str(a.kernel)], text=True).splitlines():
    fields = line.split()
    if len(fields) == 3 and re.fullmatch("[0-9a-fA-F]+", fields[0]):
        symbols[fields[2]] = int(fields[0], 16)
names = ["_zorn_gui_sample_task"]
if "_zorn_gui_sample_stack" in symbols:
    names.append("_zorn_gui_sample_stack")
assembly = subprocess.check_output(["xcrun", "llvm-objdump", "--disassemble",
    "--disassemble-symbols=" + ",".join(names), str(a.kernel)], text=True)
calls = {int(v, 16) for v in re.findall(r"\b(?:bl|b)\s+0x([0-9a-f]+)\b", assembly)}
required = ["_get_task_map_reference", "_vm_map_read_user", "_vm_map_deallocate", "_zorn_ufs_gui_stack"]
assert all(symbols.get(name) in calls for name in required), "missing real map lifetime/read/record calls"
space = None
if "_zorn_gui_data_space" in symbols:
    def calls_from(name):
        body = subprocess.check_output(["xcrun", "llvm-objdump", "--disassemble",
            "--disassemble-symbols=" + name, str(a.kernel)], text=True)
        return {int(v, 16) for v in re.findall(r"\b(?:bl|b)\s+0x([0-9a-f]+)\b", body)}
    assert symbols["_zorn_gui_data_space"] in calls_from("_zorn_gui_sample_thread"), "Data space helper is not called by the scheduled observer"
    space_calls = calls_from("_zorn_gui_data_space")
    space_targets = ("_vnode_lookup", "_vnode_put", "_vfs_getattr", "_zorn_ufs_boot_policy_allowed", "_zorn_ufs_gui_data_space")
    assert all(symbols.get(name) in space_calls for name in space_targets), "missing actual readonly Data space calls"
    forbidden = ("_vfs_setattr", "_vnode_setattr", "_write", "_pwrite", "_unlink", "_mkdir")
    assert not any(symbols.get(name) in space_calls for name in forbidden), "Data space observer mutates filesystem"
    space = {"actual_scheduled_call": True, "actual_readonly_calls": {name: hex(symbols[name]) for name in space_targets},
             "no_filesystem_mutation_calls": True, "hardware_qualified": False}
final_snapshot = None
if "_zorn_ufs_gui_flush" in symbols:
    assert symbols["_zorn_ufs_gui_flush"] in calls_from("_zorn_gui_sample_thread"), "final GUI snapshot is never flushed"
    final_snapshot = {"actual_observer_flush_call": True, "hardware_qualified": False}
kernel_stack = None
if "_zorn_gui_sample_kernel_stack" in symbols:
    assert symbols["_zorn_gui_sample_kernel_stack"] in calls, "kernel stack helper is not reachable from GUI sampler"
    stack_calls = calls_from("_zorn_gui_sample_kernel_stack")
    stack_targets = ("_ml_nofault_copy", "_zorn_ufs_gui_stack")
    assert all(symbols.get(name) in stack_calls for name in stack_targets), "missing nofault stack copy/record calls"
    assert symbols.get("_thread_deallocate") in calls, "sampled thread reference is not released"
    forbidden = ("_thread_suspend", "_thread_hold", "_thread_stop", "_write", "_vnode_lookup", "_vm_map_read_user")
    assert not any(symbols.get(name) in stack_calls for name in forbidden), "kernel stack helper can wait/read user VM or mutate filesystem"
    kernel_stack = {"actual_nofault_calls": {name: hex(symbols[name]) for name in stack_targets},
                    "thread_reference_released": True, "no_target_suspension_or_io_calls": True,
                    "hardware_qualified": False}
result = {"kernel_sha256": hashlib.sha256(a.kernel.read_bytes()).hexdigest(),
          "actual_map_read_and_lifetime_calls": True,
          "call_targets": {name: hex(symbols[name]) for name in required},
          "hardware_stack_reads_qualified": False}
if space is not None:
    result["data_space_observer"] = space
if kernel_stack is not None:
    result["kernel_stack_observer"] = kernel_stack
if final_snapshot is not None:
    result["final_snapshot"] = final_snapshot
a.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
