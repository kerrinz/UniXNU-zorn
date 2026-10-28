#!/usr/bin/env python3
"""Prepare an isolated ArmCpu assembly fix and two-core ADT; never boot/link it."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "UniXNU-zorn/native/smp"
OUT = ROOT / "out/zorn/smp"
TREE = ROOT / "UniXNU/out/zorn/tree"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_adt(data):
    def parse(at, depth=0):
        if depth > 32 or at + 8 > len(data):
            raise ValueError("invalid ADT node")
        np, nc = struct.unpack_from("<2I", data, at)
        if np > 256 or nc > 256:
            raise ValueError("invalid ADT counts")
        at += 8
        props = []
        for _ in range(np):
            if at + 36 > len(data):
                raise ValueError("truncated ADT property")
            key, size = struct.unpack_from("<32sI", data, at)
            at += 36
            if size & 0x80000000 or at + size > len(data):
                raise ValueError("unsupported ADT property")
            props.append((key.rstrip(b"\0"), data[at:at + size]))
            at += (size + 3) & ~3
        children = []
        for _ in range(nc):
            child, at = parse(at, depth + 1)
            children.append(child)
        return [props, children], at
    tree, end = parse(0)
    if end != len(data) or emit(tree) != data:
        raise ValueError("ADT must round-trip exactly")
    return tree


def emit(node):
    props, children = node
    return struct.pack("<2I", len(props), len(children)) + b"".join(
        key.ljust(32, b"\0") + struct.pack("<I", len(value)) + value + bytes(-len(value) % 4)
        for key, value in props) + b"".join(emit(child) for child in children)


def child(node, name):
    matches = [c for c in node[1] if dict(c[0]).get(b"name") == name + b"\0"]
    if len(matches) != 1:
        raise ValueError("expected one child " + repr(name))
    return matches[0]


def disassemble(path, symbol):
    return subprocess.check_output(["xcrun", "llvm-objdump", "--disassemble",
        "--disassemble-symbols=" + symbol, str(path)], text=True).lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=ROOT / "out/zorn/builds/af82587b")
    parser.add_argument("--compile", action="store_true", help="compile isolated object with the real XNU C++ recipe")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    origin = json.loads((NATIVE / "origin.json").read_text())
    source = ROOT / "UniXNU/drivers/ArmCpu/ArmCpu.cpp"
    if sha(source) != origin["source_sha256"]:
        raise ValueError("unqualified ArmCpu source revision")
    captured = json.loads((OUT / "hardware.json").read_text())
    if sha(ROOT / captured["captured_fdt"]) != captured["sha256"]:
        raise ValueError("captured K80 device tree changed")
    if [c["affinity"] for c in captured["cpus"]] != [hex(i * 0x100) for i in range(8)]:
        raise ValueError("unqualified CPU affinities")
    if [c["capacity_dmips_mhz"] for c in captured["cpus"][:2]] != [1024, 1024] or not any(
            p["method"] == "smc" for p in captured["psci"]):
        raise ValueError("first pair/conduit differs")
    build = json.loads((args.baseline / "inputs.json").read_text())
    if build["sha256"] != "af82587ba252210bcf8533066a4a6c02df3aa047ed6de21dbe5c8bd03c992495":
        raise ValueError("require owner-confirmed Apple-logo baseline")
    expected = build["inputs"][str(ROOT / "out/zorn/payload-with-trustcache.adt")]
    baseline_adt = args.baseline / "kernel.macho.adt"
    if sha(baseline_adt) != expected:
        raise ValueError("baseline ADT identity differs")
    tree = parse_adt(baseline_adt.read_bytes())
    previous = copy.deepcopy(tree)
    cpus = child(tree, b"cpus")
    if len(cpus[1]) != 1 or dict(cpus[1][0][0]).get(b"reg") != struct.pack("<I", 0):
        raise ValueError("baseline is not CPU0 only")
    cpu1 = copy.deepcopy(cpus[1][0])
    replacements = {b"name": b"cpu1\0", b"reg": struct.pack("<I", 0x100), b"state": b"waiting\0"}
    cpu1[0] = [(key, replacements.get(key, value)) for key, value in cpu1[0]]
    cpus[1].append(cpu1)
    if any(dict(c[0]).get(b"name") == b"psci\0" for c in tree[1]):
        raise ValueError("baseline unexpectedly includes PSCI")
    tree[1].append([[(b"name", b"psci\0"), (b"compatible", b"arm,psci-1.0\0"), (b"method", b"smc\0")], []])
    candidate_adt = OUT / "two-core.adt"
    candidate_adt.write_bytes(emit(tree))
    parse_adt(candidate_adt.read_bytes())
    # Removing just the new CPU and PSCI must reproduce every baseline byte,
    # including random seed, identity, memory window and trust placeholders.
    restored = copy.deepcopy(tree)
    child(restored, b"cpus")[1].pop()
    restored[1].pop()
    assert emit(restored) == emit(previous)
    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        temp = Path(directory)
        (temp / "ArmCpu.cpp").write_bytes(source.read_bytes())
        subprocess.run(["git", "apply", "--check", str(NATIVE / "ArmCpu-assembly-newlines.patch")], cwd=temp, check=True)
        subprocess.run(["git", "apply", str(NATIVE / "ArmCpu-assembly-newlines.patch")], cwd=temp, check=True)
        candidate = OUT / "ArmCpu.cpp"
        candidate.write_bytes((temp / "ArmCpu.cpp").read_bytes())
    if sha(candidate) != origin["candidate_sha256"]:
        raise ValueError("patched ArmCpu identity differs")
    result = {"baseline_boot_sha256": build["sha256"], "captured_fdt_sha256": captured["sha256"],
              "candidate_adt_sha256": sha(candidate_adt), "candidate_source_sha256": sha(candidate),
              "two_cpu_affinities": [0, 256], "psci_method": "smc", "unrelated_adt_bytes_preserved": True,
              "default_profile_changed": False, "object_compiled": False, "hardware_smp_qualified": False,
              "remaining_gates": ["cross-core TLB invalidation", "atomic diagnostic log ownership",
                  "PSCI/per-core timer/IPI preflight", "legacy synchronization review"]}
    if args.compile:
        recipe = TREE / "build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json"
        record = json.loads(recipe.read_text().strip().rstrip(","))
        command = []
        values = record["arguments"]
        i = 0
        while i < len(values):
            value = values[i]
            if value in ("-o", "-MF", "-MJ", "-MT", "-MQ"):
                i += 2
                continue
            if value in ("-c", "-MD", "-MMD", "-MP") or value == record["file"]:
                i += 1
                continue
            command.append(value)
            i += 1
        obj = OUT / "ArmCpu.o"
        command += ["-c", str(candidate), "-o", str(obj), "-I", str(TREE / ".cache/xnu-work/osfmk")]
        (OUT / "compile-command.json").write_text(json.dumps(command, indent=2) + "\n")
        subprocess.run(command, cwd=record["directory"], check=True)
        actual = disassemble(obj, "__ZN6ArmCpu9signalCPUEP5IOCPU")
        if not re.search(r"\bdsb\s+ishst\b[\s\S]*\bmsr\s+icc_sgi1r_el1[\s\S]*\bisb\b", actual):
            raise ValueError("candidate lacks real ordered SGI instructions")
        original = disassemble(args.baseline / "kernel.macho", "__ZN6ArmCpu9signalCPUEP5IOCPU")
        if re.search(r"\bmsr\s+icc_sgi1r_el1", original):
            raise ValueError("negative baseline no longer reproduces the missing SGI")
        assert re.search(r"\bsmc\s+#0", disassemble(obj, "__ZN6ArmCpu8startCPUEmm"))
        result.update(object_compiled=True, object_sha256=sha(obj), ordered_sgi_in_actual_object=True,
                      old_linked_kernel_missing_sgi_confirmed=True, actual_psci_smc_present=True)
    (OUT / "candidate.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
