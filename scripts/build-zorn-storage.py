#!/usr/bin/env python3
"""Bind a real readonly UFS block device to the pinned original storage ABI.

The public IOStorageFamily object is an annotation instrument, never linked.
All 190 dispatch slots and actual original base functions are checked against
the current prelink. Runtime parent sizes are checked again before publication.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

TREE = Path.cwd()
DEVICE = Path(os.environ.get("UNIXNU_DEVICE") or
              json.loads((TREE.parents[1] / "state.json").read_text())["device"]).resolve()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--audit-only", action="store_true")
parser.add_argument("--component", choices=("ZornUfsBlock", "RamBlock"), default="ZornUfsBlock")
args = parser.parse_args()
component = "NativeRamBlock" if args.component == "RamBlock" else "ZornUfsBlock"
OUT = TREE / ("build/ram-block" if args.component == "RamBlock" else "build/zorn-storage")
OUT.mkdir(parents=True, exist_ok=True)
driver_source = (TREE / "drivers/RamBlock/NativeRamBlock.cpp" if args.component == "RamBlock"
                 else DEVICE / "native/ufs-read/ZornUfsBlock.cpp")
sys.path.insert(0, str(TREE / "kits/XnuPrelink"))
import native_prelink as np

REVISION = "e45fbe30a7879e0b16e26dddb78538f1b00e0bff"
STORAGE_HASH = "852b7846a9039c58fde08478416080af38ffcd5b47c08c889b28497f5f5b4061"


def require(value, message):
    if not value:
        raise SystemExit(message)


def run(command, **kwargs):
    return subprocess.check_output([str(value) for value in command], timeout=90, **kwargs)


def symbols(blob, image):
    command = next(at for kind, at, size in image["commands"] if kind == 2)
    sy, count, st, _ = struct.unpack_from("<4I", blob, command + 8)
    out = []
    for index in range(count):
        ix, kind, _, _, value = struct.unpack_from("<IBBHQ", blob, sy + index * 16)
        out.append((blob[st + ix:blob.index(b"\0", st + ix)].decode(), value, kind))
    return out


def dispatch(blob, name):
    image = np.macho(blob)
    syms = symbols(blob, image)
    table, = [value for symbol, value, kind in syms if symbol == name]
    relocations = {}
    for segment in image["segments"]:
        for section in segment["sections"]:
            if section["va"] <= table < section["va"] + section["size"]:
                at, count = struct.unpack_from("<2I", blob, section["command_offset"] + 56)
                for index in range(count):
                    address, word = struct.unpack_from("<2I", blob, at + index * 8)
                    if word >> 27 & 1 and word >> 28 == 0 and word >> 25 & 3 == 3:
                        relocations[section["va"] + address] = syms[word & 0xffffff][0]
    entries = [relocations.get(table + 16 + index * 8) for index in range(190)]
    require(all(entries) and table + 16 + 190 * 8 not in relocations, "Storage dispatch must have exactly 190 slots")
    return entries, syms


if not args.audit_only:
    candidates = [TREE / "refer/IOStorageFamily", *sorted((TREE.parents[1] / "feeds").glob("IOStorageFamily-*"))]
    source = None
    for path in candidates:
        if not (path / "IOBlockStorageDevice.cpp").is_file():
            continue
        revision = run(["git", "-C", path, "rev-parse", "HEAD"], text=True).strip()
        if revision == REVISION:
            source = path
            break
    require(source, "Fetch the pinned IOStorageFamily feed before building zorn storage")
    headers = OUT / "include/IOKit/storage"
    headers.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.h"):
        shutil.copyfile(path, headers / path.name)
    sdk = Path(run(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip())
    shutil.copyfile(sdk / "usr/include/TargetConditionals.h", OUT / "include/TargetConditionals.h")
    record = json.loads((TREE / "build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json").read_text().strip().rstrip(","))
    for current, output in [(source / "IOBlockStorageDevice.cpp", OUT / "storage-reference.o"),
                            (driver_source, OUT / (component + ".o"))]:
        command, index = [], 0
        arguments = record["arguments"]
        while index < len(arguments):
            value = arguments[index]
            if value == record["file"]:
                command.append(str(current))
            elif value == "-o":
                command += ["-o", str(output)]
                index += 1
            elif value in ("-MF", "-MJ"):
                index += 1
            elif value == "-Xclang" and arguments[index + 1].startswith("-W"):
                index += 1
            elif not value.startswith("-W") and value not in ("-MD", "-MP"):
                command.append(value)
            index += 1
        command += ["-I", OUT / "include", "-I", TREE / ".cache/xnu-work/osfmk",
                    "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-Wno-deprecated-declarations",
                    "-Wno-c99-designator", "-Wno-reorder-init-list", "-Wno-unnecessary-virtual-specifier",
                    "-Wno-deprecated-enum-enum-conversion", "-mgeneral-regs-only"]
        result = subprocess.run([str(v) for v in command], cwd=record["directory"], capture_output=True, text=True)
        output.with_suffix(".compile.log").write_text(result.stdout + result.stderr)
        require(result.returncode == 0, (result.stdout + result.stderr)[-4000:])

candidate = TREE.parent / "kernel/kernel.macho"
data = candidate.read_bytes()
image = np.macho(data)
plan = json.loads(candidate.with_suffix(".json").read_text())
require(plan["original_sha256"] == "f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7",
        "Storage ABI requires the exact iPad7,1 / 21H461 kernelcache")


def read(va, size):
    at = np.backed_offset(image["segments"], va, size, len(data))
    return data[at:at + size]


exports = np.exports(data, image)
all_by_name = {name: va for va, names in exports.items() for name in names}
# The completed kernel also exports our absolute original-class imports.
# They are checked below, never treated as independent native ABI evidence.
by_name = {name: va for name, va in all_by_name.items() if "IOBlockStorageDevice" not in name}
extents = [e for e in plan["extents"] if e["module"] == "com.apple.iokit.IOStorageFamily"]
const, = [e for e in extents if e["segment"] == "__DATA_CONST"]
text, = [e for e in extents if e["segment"] == "__TEXT_EXEC"]
require(hashlib.sha256(read(text["va"], text["size"])).hexdigest() ==
        plan["original_executable_sha256"]["com.apple.iokit.IOStorageFamily"] == STORAGE_HASH,
        "Original storage executable changed")
reference, _ = dispatch((OUT / "storage-reference.o").read_bytes(), "__ZTV20IOBlockStorageDevice")
require(reference.count("___cxa_pure_virtual") == 14 and sum(name in by_name for name in reference) == 176,
        "Pinned public storage interface changed")
found = []
blob = read(const["va"], const["size"])
for at in range(0, len(blob) - 192 * 8 + 1, 8):
    if blob[at:at + 16] != bytes(16):
        continue
    pointers = struct.unpack_from("<190Q", blob, at + 16)
    if all(pointers[index] == by_name[name] for index, name in enumerate(reference) if name in by_name):
        found.append((const["va"] + at, pointers))
require(len(found) == 1, "Cannot uniquely identify the original storage vtable")
table, pointers = found[0]


def branch(address, word):
    immediate = word & 0x3ffffff
    if immediate & 0x2000000:
        immediate -= 0x4000000
    return address + immediate * 4


def thunk_names(address):
    a, load, jump = struct.unpack("<3I", read(address, 12))
    require(a & 0x9f00001f == 0x90000010 and load & 0xffc003ff == 0xf9400210 and jump == 0xd61f0200,
            "Original storage import thunk changed")
    immediate = ((a >> 5 & 0x7ffff) << 2) | (a >> 29 & 3)
    if immediate & 0x100000:
        immediate -= 0x200000
    slot = (address & ~4095) + immediate * 4096 + (load >> 10 & 4095) * 8
    return exports.get(struct.unpack("<Q", read(slot, 8))[0], [])


constructors = []
for address in range(text["va"], text["va"] + text["size"] - 32, 4):
    words = struct.unpack("<8I", read(address, 32))
    if words[:2] != (0xa9bf7bfd, 0x910003fd) or words[2] & 0xfc000000 != 0x94000000 or \
            words[3] & 0x9f00001f != 0x90000008 or words[4] & 0xffc003ff != 0x91000108 or \
            words[5:] != (0xf9000008, 0xa8c17bfd, 0xd65f03c0):
        continue
    immediate = ((words[3] >> 5 & 0x7ffff) << 2) | (words[3] >> 29 & 3)
    if immediate & 0x100000:
        immediate -= 0x200000
    stored = ((address + 12) & ~4095) + immediate * 4096 + (words[4] >> 10 & 4095)
    if stored == table + 16:
        constructors.append((address, branch(address + 8, words[2])))
require(len(constructors) == 1 and "__ZN9IOServiceC2EPK11OSMetaClass" in thunk_names(constructors[0][1]),
        "Original protected storage constructor is not the real IOService constructor")
destructor = pointers[0] - 4
word, = struct.unpack("<I", read(destructor, 4))
require(word & 0xfc000000 == 0x14000000 and "__ZN9IOServiceD2Ev" in thunk_names(branch(destructor, word)),
        "Original base destructor changed")
require(all(read(pointers[i], 4) == struct.pack("<I", 0xd4200020) for i in (0, 1)),
        "Abstract storage complete destructors must be traps")
function = pointers[7]
a, add, ret = struct.unpack("<3I", read(function, 12))
require(a & 0x9f00001f == 0x90000000 and add & 0xffc003ff == 0x91000000 and ret == 0xd65f03c0,
        "Original storage metaclass getter changed")
immediate = ((a >> 5 & 0x7ffff) << 2) | (a >> 29 & 3)
if immediate & 0x100000:
    immediate -= 0x200000
meta = (function & ~4095) + immediate * 4096 + (add >> 10 & 4095)

obj = OUT / (component + ".o")
mangled = str(len(component)) + component
compiled, syms = dispatch(obj.read_bytes(), "__ZTV" + mangled)
require("___cxa_pure_virtual" not in compiled, "Concrete transport has unimplemented operations")
all_names = list(dict.fromkeys(reference + compiled))
demangled = run(["xcrun", "c++filt"], input="\n".join(n[1:] for n in all_names) + "\n", text=True).splitlines()
readable = dict(zip(all_names, demangled))
overrides = 0
for index, (expected, actual) in enumerate(zip(reference, compiled)):
    own = actual.startswith(("__ZN" + mangled, "__ZNK" + mangled))
    if expected == "___cxa_pure_virtual":
        require(own, "Pure storage operation is not implemented by the transport")
    elif actual != expected:
        require(own and (index in (0, 1) or readable[actual].split("::", 1)[1] == readable[expected].split("::", 1)[1]),
                f"Storage subclass dispatch differs at {index}: {actual}")
    overrides += own
possible = {name: pointers[index] for index, name in enumerate(reference) if name not in by_name}
possible.update({"__ZN20IOBlockStorageDeviceC2EPK11OSMetaClass": constructors[0][0],
                 "__ZN20IOBlockStorageDeviceD2Ev": destructor,
                 "__ZN20IOBlockStorageDevice10gMetaClassE": meta,
                 "__ZTV20IOBlockStorageDevice": table})
undefined = [name for name, value, kind in syms if kind == 1 and "IOBlockStorageDevice" in name]
require(all(name in possible and not re.search(r"IOBlockStorageDeviceD[01]Ev$", name) for name in undefined),
        "Unqualified original storage import or abstract destructor")
bindings = {name: possible[name] for name in undefined}
require(all(name not in all_by_name or all_by_name[name] == value for name, value in bindings.items()),
        "Published original-class binding differs from the independently derived storage ABI")
if not args.audit_only:
    assembly = OUT / "original-bindings.S"
    assembly.write_text("".join(f".globl {name}\n.set {name}, {value:#x}\n" for name, value in sorted(bindings.items())))
    sdk = run(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], text=True).strip()
    run(["xcrun", "clang", "-target", "arm64-apple-ios17.0", "-isysroot", sdk,
         "-c", assembly, "-o", OUT / "original-bindings.o"])
    if args.component == "RamBlock":
        shared = json.loads((TREE / "build/zorn-storage/bindings-audit.json").read_text())["bindings"]
        require(all(shared.get(name) == hex(value) for name, value in bindings.items()),
                "RAM imports must be exactly supplied by the already audited UFS original-class bindings")
        archive = OUT / "libRamBlock.a"
        archive.unlink(missing_ok=True)
        # One original-class alias set, shared with the real UFS device.
        run(["xcrun", "ar", "rcs", archive, obj])
    else:
        late = OUT / "ZornUfsBlock.late.o"
        run(["llvm-objcopy", "--remove-section=__DATA,__mod_init_func",
             "--globalize-symbol=__GLOBAL__sub_I_ZornUfsBlock.cpp", obj, late])
        def text_section(blob):
            section = next(s for seg in np.macho(blob)["segments"] for s in seg["sections"] if s["name"] == "__text")
            return blob[section["fileoff"]:section["fileoff"] + section["size"]]
        require(text_section(obj.read_bytes()) == text_section(late.read_bytes()), "Late registration changed instructions")
report = {"reference_candidate_sha256": hashlib.sha256(data).hexdigest(), "public_source_revision": REVISION,
          "original_storage_text_sha256": STORAGE_HASH, "slots_checked": 190, "concrete_overrides": overrides,
          "component": args.component, "source_sha256": hashlib.sha256(driver_source.read_bytes()).hexdigest(),
          "object_sha256": hashlib.sha256(obj.read_bytes()).hexdigest(), "bindings": {k: hex(v) for k, v in bindings.items()},
          "reference_object_linked": False, "abstract_complete_destructors_called": False, "runtime_qualified": False}
(OUT / "bindings-audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(f"PASS: 190 real storage slots, {overrides} overrides, original base constructor/destructor and imports")
