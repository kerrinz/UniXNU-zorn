#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Build the bounded original-PMGR adapter for iPad7,1 / 21H461.

Adapted from UniXNU-sheng scripts/build-sheng-platform-power.py and
UniXNU scripts/audit-amfi-pmgr-contract.py. Audit the previous candidate
before importing any private ABI. Requires an existing incremental build.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

TREE = Path.cwd()
STATE = TREE.parents[1] / "state.json"
DEVICE = Path(os.environ.get("UNIXNU_DEVICE") or
              json.loads(STATE.read_text())["device"]).resolve()
OUT = TREE / "build/zorn-pmgr"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(TREE / "kits/XnuPrelink"))
from native_prelink import backed_offset, exports, macho


def run(command, **kwargs):
    return subprocess.check_output([str(v) for v in command], timeout=90, **kwargs)


def require(ok, message):
    if not ok:
        raise SystemExit(message)


candidate_path = TREE.parent / "kernel/kernel.macho"
require(candidate_path.is_file(), "PMGR ABI audit requires the previous kernel.macho")
candidate = candidate_path.read_bytes()
plan = json.loads(candidate_path.with_suffix(".json").read_text())
meta = macho(candidate)
names = {name: va for va, labels in exports(candidate, meta).items() for name in labels}


def read(va, size):
    at = backed_offset(meta["segments"], va, size, len(candidate))
    return candidate[at:at + size]


def ptr(va):
    return struct.unpack("<Q", read(va, 8))[0]


def words(va, expected):
    require(struct.unpack("<" + "I" * len(expected), read(va, 4 * len(expected))) ==
            expected, f"Instruction contract changed at {va:#x}")


expected_hashes = {
    "com.apple.driver.ApplePMGR":
        "2c433279d004803b7ef02948e550ad6b77aa3f84b02a06a357e00fa738310a99",
    "com.apple.driver.AppleMobileFileIntegrity":
        "a1088aaabc259418ed503d08df29b6146470b8c962696c688122a1f60a141db6",
}
for module, digest in expected_hashes.items():
    extent, = [e for e in plan["extents"] if e["module"] == module and
               e["segment"] == "__TEXT_EXEC"]
    blob = bytearray(read(extent["va"], extent["size"]))
    if module.endswith("AppleMobileFileIntegrity"):
        # This port already has one documented null-field shim. Accept exactly
        # its BL to the exported target; restore only that word for the hash.
        site = 0xfffffff004abbe54
        instruction, = struct.unpack("<I", read(site, 4))
        if instruction != 0xf9400100:
            immediate = instruction & 0x03ffffff
            if immediate & 0x02000000:
                immediate -= 0x04000000
            require(instruction >> 26 == 0x25 and
                    site + immediate * 4 == names.get("_zorn_amfi_deref"),
                    "Unrecognized pre-existing AMFI modification")
            words(site - 4, (0xf94012a8, instruction, 0x14000008))
            struct.pack_into("<I", blob, site - extent["va"], 0xf9400100)
    require(hashlib.sha256(blob).hexdigest() ==
            plan["original_executable_sha256"][module] == digest,
            f"Original executable differs: {module}")

for slot, symbol in (
    (0xfffffff005cfad48, "__ZN9IOService15serviceMatchingEPKcP12OSDictionary"),
    (0xfffffff005cfad50, "__ZN9IOService22waitForMatchingServiceEP12OSDictionaryy"),
    (0xfffffff005cfac68, "__ZN15OSMetaClassBase12safeMetaCastEPKS_PK11OSMetaClass"),
):
    require(names.get(symbol) == ptr(slot), f"IOKit import differs: {symbol}")
require(read(0xfffffff0042dde02, 13) == b"ApplePMGRNub\0", "Matching class differs")
require(ptr(0xfffffff005cfac08) == 0xfffffff004a24adc and
        ptr(0xfffffff005cfac10) == 0xfffffff004a230ec, "PMGR imports differ")
words(0xfffffff004aaeb40, (0x94006c46, 0x321e0015, 0xaa1403e0,
                         0xaa1503e1, 0x94006c45))
words(0xfffffff004a24adc, (0xf9404400, 0xb4000080, 0xf9400008,
                         0xf9450101, 0xd61f0020, 0x12800000, 0xd65f03c0))
words(0xfffffff004a230ec, (0xf9404400, 0xb4000080, 0xf9400008,
                         0xf9450502, 0xd61f0040, 0xd65f03c0))
require(struct.unpack("<2Q", read(0xfffffff005ce26d8 + 320 * 8, 16)) ==
        (0xfffffff004a20fbc, 0xfffffff004a20fc4), "Provider AON slots differ")
words(0xfffffff004a20fbc, (0x12800000, 0xd65f03c0, 0xd65f03c0))

# Check the actual target driver's behavior in the pinned, unchanged IPSW
# cache, rather than inferring register semantics from a class name.
original_path = TREE.parents[1] / "ipsw/21H461/kernelcache.decompressed"
original = original_path.read_bytes()
require(hashlib.sha256(original).hexdigest() ==
        "f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7",
        "Wrong original iPad7,1 kernelcache")
original_meta = macho(original)


def original_read(va, size):
    at = backed_offset(original_meta["segments"], va, size, len(original))
    return original[at:at + size]


require(original_read(0xfffffff005852125, 15) == b"AppleT8011PMGR\0", "Wrong target class")
require(struct.unpack("<2Q", original_read(0xfffffff006f9da90 + 320 * 8, 16)) ==
        (0xfffffff006a577e8, 0xfffffff006a577f0), "Target AON slots differ")
require(struct.unpack("<2I", original_read(0xfffffff006a577e8, 8)) ==
        (0x12800000, 0xd65f03c0) and
        struct.unpack("<I", original_read(0xfffffff006a577f0, 4)) == (0xd65f03c0,),
        "Target AON methods must read 0xffffffff / return without MMIO")

header = """// Generated exact private ABI; storage stays opaque.
#pragma once
#include <IOKit/IOPMGR.h>
class ApplePMGR : public IOPMGR {
 OSDeclareAbstractStructors(ApplePMGR)
 unsigned char originalPrivate[0x4b8a8-sizeof(IOPMGR)];
public:
"""
guards = ""
for slot in range(177, 340):
    if slot == 320:
        header += " virtual uint32_t readAon();\n"
    elif slot == 321:
        header += " virtual void writeAon(uint64_t);\n"
    else:
        header += f" virtual void opaque{slot}() = 0;\n"
        guards += f" void opaque{slot}() override {{ unavailable({slot}); }}\n"
header += '};\nstatic_assert(sizeof(ApplePMGR)==0x4b8a8,"Original provider storage");\n'
(OUT / "OriginalPMGRABI.h").write_text(header)
(OUT / "GuardedPMGRSlots.inc").write_text(guards)

source = DEVICE / "native/pmgr/ZornPlatformPower.cpp"
obj = OUT / "ZornPlatformPower.o"
record_path = TREE / "build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json"
record = json.loads(record_path.read_text().strip().rstrip(","))
command, i = [], 0
arguments = record["arguments"]
while i < len(arguments):
    arg = arguments[i]
    if arg == record["file"]:
        command.append(source)
    elif arg == "-o":
        command += ["-o", obj]
        i += 1
    elif arg == "-Xclang" and arguments[i + 1].startswith("-W"):
        i += 1
    elif not arg.startswith("-W"):
        command.append(arg)
    i += 1
command += ["-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-Wno-c99-designator",
            "-Wno-reorder-init-list", "-Wno-deprecated-enum-enum-conversion",
            "-Wno-unnecessary-virtual-specifier", "-I", OUT, "-I", TREE / ".cache/xnu-work/osfmk"]
run(command, cwd=record["directory"])
raw = obj.read_bytes()
info = macho(raw)
require(info["kind"] == 1, "Require ordinary ARM64 subtype-0 Mach-O object")
build_version = [struct.unpack_from("<2I", raw, at + 8)
                 for cmd, at, _ in info["commands"] if cmd == 0x32]
require(build_version == [(2, 0x110000)], "Require iOS 17 build target")
sym_at = next(at for cmd, at, _ in info["commands"] if cmd == 2)
at, count, strings, _ = struct.unpack_from("<4I", raw, sym_at + 8)
symbols = []
for i in range(count):
    ix, kind, _, _, address = struct.unpack_from("<IBBHQ", raw, at + i * 16)
    symbols.append((raw[strings + ix:raw.index(b"\0", strings + ix)].decode(), address, kind))
vtable = next(va for name, va, _ in symbols if name == "__ZTV17ZornPlatformPower")
relocations = {}
for segment in info["segments"]:
    for section in segment["sections"]:
        if section["va"] <= vtable < section["va"] + section["size"]:
            at, count = struct.unpack_from("<2I", raw, section["command_offset"] + 56)
            for i in range(count):
                offset, bits = struct.unpack_from("<2I", raw, at + i * 8)
                if bits >> 27 & 1 and bits >> 28 == 0 and bits >> 25 & 3 == 3:
                    relocations[section["va"] + offset] = symbols[bits & 0xffffff][0]
entries = [relocations.get(vtable + 16 + i * 8) for i in range(340)]
require(all(entries) and vtable + 16 + 340 * 8 not in relocations,
        "Require exact 340-entry provider vtable")
bindings = {
    "__ZN9ApplePMGRC2EPK11OSMetaClass": 0xfffffff0049f003c,
    "__ZN9ApplePMGRD2Ev": 0xfffffff0049f019c,
    "__ZN9ApplePMGR10gMetaClassE": 0xfffffff006adf490,
}
for slot, name in enumerate(entries):
    if slot in (0, 1, 7) or 168 <= slot < 340 and slot not in (320, 321):
        require("17ZornPlatformPower" in name, f"Own guard/lifecycle required at slot {slot}")
    elif slot in (320, 321):
        require("9ApplePMGR" in name, "Inherit only audited original AON methods")
        bindings[name] = ptr(0xfffffff005ce26d8 + slot * 8)
    else:
        require(names.get(name) == ptr(names["__ZTV6IOPMGR"] + 16 + slot * 8),
                f"Native IOPMGR/IOService entry differs at slot {slot}")
undefined = {name for name, _, kind in symbols if kind == 1 and "ApplePMGR" in name}
require(undefined == set(bindings), "All and only audited original base imports")
bindings.update({"_zorn_original_pmgr_nub_create": 0xfffffff004a22568,
                 "_zorn_original_pmgr_nub_read": 0xfffffff004a24adc,
                 "_zorn_original_pmgr_nub_write": 0xfffffff004a230ec})
asm = OUT / "original-bindings.S"
asm.write_text("".join(f".globl {name}\n.set {name}, {va:#x}\n" for name, va in bindings.items()))
sdk = run(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], text=True).strip()
run(["xcrun", "clang", "-target", "arm64-apple-ios17.0", "-isysroot", sdk,
     "-c", asm, "-o", OUT / "original-bindings.o"])
late = OUT / "ZornPlatformPower.late.o"
run(["llvm-objcopy", "--remove-section=__DATA,__mod_init_func",
     "--globalize-symbol=__GLOBAL__sub_I_ZornPlatformPower.cpp", obj, late])


def text_section(blob):
    section = next(s for seg in macho(blob)["segments"] for s in seg["sections"] if s["name"] == "__text")
    return blob[section["fileoff"]:section["fileoff"] + section["size"]]


require(text_section(raw) == text_section(late.read_bytes()), "Late registration changed instructions")
archive = OUT / "libZornPlatformPower.a"
archive.unlink(missing_ok=True)
run(["xcrun", "ar", "rcs", archive, late, OUT / "original-bindings.o"])
report = {
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "reference_candidate_sha256": hashlib.sha256(candidate).hexdigest(),
    "original_kernelcache_sha256": hashlib.sha256(original).hexdigest(),
    "original_executable_sha256": expected_hashes,
    "accepted_existing_amfi_shim": "one BL at 0xfffffff004abbe54 to _zorn_amfi_deref",
    "bindings": {name: hex(va) for name, va in bindings.items()},
    "virtual_entries": 340,
    "functional_power_backend": False,
    "runtime_qualified": False,
}
(OUT / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")
print("PASS: pinned original PMGR/AMFI contract; exact 340-slot ABI; unsupported power operations stop")
print(archive)
