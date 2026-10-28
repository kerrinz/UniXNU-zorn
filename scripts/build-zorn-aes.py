#!/usr/bin/env python3
"""Build upstream SoftwareAES and verify its ordinary iOS ABI for 21H461.

The checked source stays in the shared component. Original executable bytes
are not patched; the native subclass implements software-key AES-CBC only.
Run --audit-only after prelink as well, before packaging a bootable image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

TREE = Path.cwd()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--audit-only", action="store_true")
args = parser.parse_args()
sys.path.insert(0, str(TREE / "kits/XnuPrelink"))
import native_prelink as np

OUT = TREE / "build/native-aes"
OUT.mkdir(parents=True, exist_ok=True)
candidate = TREE.parent / "kernel/kernel.macho"
data = candidate.read_bytes()
meta = np.macho(data)
plan = json.loads(candidate.with_suffix(".json").read_text())


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def read(va, size):
    offset = np.backed_offset(meta["segments"], va, size, len(data))
    return data[offset:offset + size]


require(plan["original_sha256"] ==
        "f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7",
        "SoftwareAES requires the pinned iPad7,1 / 21H461 original kernelcache")
modules = {"com.apple.iokit.IOCryptoAcceleratorFamily":
           "ea3a832e7aa88a2d7bfeb57736c11075e4ec025c0c93596eb19d918f5d8e20d5",
           "com.apple.security.AppleImage4":
           "94eee9bff8da89bb6cd12c5c8ba0c3e2ec186783f26a2e14a8c8dba0046c1290"}
for name, digest in modules.items():
    extent, = [e for e in plan["extents"] if e["module"] == name and e["segment"] == "__TEXT_EXEC"]
    require(hashlib.sha256(read(extent["va"], extent["size"])).hexdigest() == digest,
            f"Original executable changed: {name}")

recorded = TREE / "scripts/data/native-aes-original-bindings.S"
require(hashlib.sha256(recorded.read_bytes()).hexdigest() ==
        "69576361ea9a462cfed936e36e5c08458bb8b710ed1ee523e96f7ec7cf0a960a",
        "Recorded ordinary-iOS AES binding contract changed")
bindings = {name: int(address, 16) for name, address in
            re.findall(r"^\.set (\S+), (0x[0-9a-f]+)$", recorded.read_text(), re.M)}
require(bindings["__ZN16IOAESAccelerator10gMetaClassE"] == 0xfffffff006ae52d0,
        "Original AES metaclass address changed")

if not args.audit_only:
    subprocess.run([sys.executable, TREE / "scripts/build-arm-driver.py", "SoftwareAES"], check=True)

obj_path = OUT / "NativeAES.o"
obj = obj_path.read_bytes()
obj_meta = np.macho(obj)
sym_command = next(offset for command, offset, length in obj_meta["commands"] if command == 2)
symoff, count, stroff, _ = struct.unpack_from("<4I", obj, sym_command + 8)
symbols = []
for index in range(count):
    strx, kind, _, _, value = struct.unpack_from("<IBBHQ", obj, symoff + index * 16)
    name = obj[stroff + strx:obj.index(b"\0", stroff + strx)].decode()
    symbols.append((name, value, kind))
own_vtable, = [value for name, value, kind in symbols if name == "__ZTV9NativeAES"]
relocations = {}
for segment in obj_meta["segments"]:
    for section in segment["sections"]:
        if section["va"] <= own_vtable < section["va"] + section["size"]:
            offset, count = struct.unpack_from("<II", obj, section["command_offset"] + 56)
            for index in range(count):
                address, word = struct.unpack_from("<II", obj, offset + index * 8)
                if word >> 27 & 1 and word >> 28 == 0 and word >> 25 & 3 == 3:
                    relocations[section["va"] + address] = symbols[word & 0xffffff][0]

const, = [e for e in plan["extents"] if e["module"] ==
          "com.apple.iokit.IOCryptoAcceleratorFamily" and e["segment"] == "__DATA_CONST"]
tables = []
blob = read(const["va"], const["size"])
for offset in range(0, len(blob) - 183 * 8 + 1, 8):
    if blob[offset:offset + 16] == bytes(16) and struct.unpack_from("<Q", blob, offset + 16 + 168 * 8)[0] == \
            bindings["__ZN16IOAESAccelerator16getAlgorithmNameEv"]:
        tables.append(const["va"] + offset)
require(len(tables) == 1, "Original 181-slot AES vtable is not unique")
table = tables[0]
exports = {name: va for va, names in np.exports(data, meta).items() for name in names}
overrides = {0, 1, 7, 86, 111, 117, 168, 169, 170, 171, 172}
for slot in range(181):
    symbol = relocations.get(own_vtable + 16 + slot * 8)
    require(symbol, f"Missing native AES vtable relocation at {slot}")
    actual, = struct.unpack("<Q", read(table + 16 + slot * 8, 8))
    if slot in overrides:
        require(symbol.startswith(("__ZN9NativeAES", "__ZNK9NativeAES")),
                f"Unexpected native override at {slot}: {symbol}")
    else:
        expected = bindings.get(symbol, exports.get(symbol))
        require(expected == actual, f"AES inherited slot {slot} differs: {symbol}")
require(own_vtable + 16 + 181 * 8 not in relocations, "Unexpected extra native AES vtable slot")

if not args.audit_only:
    subprocess.run([sys.executable, TREE / "scripts/build-software-aes-bindings.py",
                    "--objects-dir", OUT], check=True)

report = {"candidate_sha256": hashlib.sha256(data).hexdigest(),
          "stage": "post-prelink" if args.audit_only else "previous-candidate",
          "checked_vtable_slots": 181, "native_override_slots": sorted(overrides),
          "original_vtable": hex(table), "original_executable_sha256": modules,
          "source_sha256": hashlib.sha256((TREE / "drivers/SoftwareAES/NativeAES.cpp").read_bytes()).hexdigest(),
          "object_sha256": hashlib.sha256(obj).hexdigest(),
          "original_code_modified": False, "hardware_keys_supported": False}
(OUT / ("post-prelink-audit.json" if args.audit_only else "zorn-bindings-audit.json")).write_text(
    json.dumps(report, indent=2) + "\n")
print("PASS: upstream SoftwareAES, 181 actual original ABI slots; original Image4/crypto text unchanged")
