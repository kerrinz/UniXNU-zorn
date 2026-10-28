#!/usr/bin/env python3
"""Verify restored VM-map lock initialization against pinned XNU and real code.

Rejects the previous non-sleepable macro and its linked bit-clear sequence.
This checks build provenance, not runtime lock correctness or desktop progress.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT / "UniXNU/out/zorn/tree"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, default=TREE / ".cache/xnu-work/osfmk/vm/vm_map.h")
parser.add_argument("--kernel", type=Path)
parser.add_argument("--output", type=Path, default=ROOT / "out/zorn/vm-map-lock-audit.json")
args = parser.parse_args()


def macro(text):
    begin = text.index("#define vm_map_lock_init(map)")
    return text[begin:text.index("\n\n", begin)].rstrip()


original = TREE / "refer/xnu/osfmk/vm/vm_map.h"
source = args.source.read_text()
assert macro(source) == macro(original.read_text()), "VM-map lock initialization differs from pinned original"
proof = {
    "vm_map_header_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
    "original_header_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
    "original_init_macro_exact": True,
    "no_post_init_forced_nonsleepable_store": True,
    "other_rwlock_and_pmap_semantics_restored": False,
    "runtime_qualified": False,
}
if args.kernel:
    nm = subprocess.check_output(["xcrun", "nm", "-n", str(args.kernel)], text=True)
    match = re.search(r"^([0-9a-f]+)\s+\S\s+_lck_rw_init$", nm, re.M)
    assert match, "original lck_rw_init missing"
    target = int(match[1], 16)
    asm = subprocess.check_output(["xcrun", "llvm-objdump", "--disassemble",
        "--disassemble-symbols=_vm_map_create_options", str(args.kernel)], text=True)
    calls = {int(v, 16) for v in re.findall(r"\bbl\s+0x([0-9a-f]+)", asm)}
    assert target in calls, "VM-map creation lacks the actual lock initializer call"
    # The previous candidate has exactly this clear of LCK_RW_CAN_SLEEP_BIT.
    assert not re.search(r"\band\s+w\d+,\s*w\d+,\s*#0xffbfffff\b", asm), "old linked sleep-bit clear remains"
    proof.update(kernel_sha256=hashlib.sha256(args.kernel.read_bytes()).hexdigest(),
                 actual_vm_map_create_calls_lck_rw_init=True,
                 old_linked_sleep_bit_clear_absent=True)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps(proof, indent=2))
