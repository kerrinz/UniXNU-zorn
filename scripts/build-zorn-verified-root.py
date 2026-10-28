#!/usr/bin/env python3
"""Compile upstream VerifiedRoot plus the zorn readonly provider binding."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

TREE = Path.cwd()
DEVICE = Path(os.environ.get("UNIXNU_DEVICE") or json.loads(
    (TREE.parents[1] / "state.json").read_text())["device"]).resolve()
INPUT = DEVICE.parent / "out/zorn/verified-root"
OUT = TREE / "build/zorn-verified-root"
OUT.mkdir(parents=True, exist_ok=True)
records = []
for name, expected in [("os", "e5634d04a8ac35f024845f583394e0a35deb26a04cb0c00286a8674e25a9a4f2"),
                       ("systemos", "b4908cde41d23e6bc05e6af51a2c9eeb00cf0f863a6a18b1600c96a3fd70414f")]:
    report = json.loads((INPUT / name / "verification.json").read_text())
    manifest = INPUT / name / "manifest.bin"
    key = INPUT / name / "trusted-key.bin"
    if report["image_sha256"] != expected or not report["real_c_signature_and_block_verification"] or \
            hashlib.sha256(manifest.read_bytes()).hexdigest() != report["manifest_sha256"] or \
            hashlib.sha256(key.read_bytes()).hexdigest() != report["trusted_key_sha256"]:
        raise SystemExit("Regenerate and C-verify the exact original " + name + " policy")
    records.append(report)
if (INPUT / "os/trusted-key.bin").read_bytes() != (INPUT / "systemos/trusted-key.bin").read_bytes():
    raise SystemExit("Independent owner anchors differ")

indices = [0, 1, records[0]["block_count"] // 2, records[0]["block_count"] - 1]
lengths = [min(4096, records[0]["image_bytes"] - block * 4096) for block in indices]
with (TREE.parent / "userdata/userdata-root.img").open("rb") as source:
    selected = []
    for block, length in zip(indices, lengths):
        source.seek(1048576 + block * 4096)
        data = source.read(length)
        if len(data) != length:
            raise SystemExit("Short original OS sample")
        selected.append(data.ljust(4096, b"\0"))
(OUT / "samples.bin").write_bytes(b"".join(selected))
assembly = ".section __DATA_CONST,__const\n.balign 8\n"
for symbol, path in [("verified_root_manifest", INPUT / "os/manifest.bin"),
                     ("verified_root_systemos_manifest", INPUT / "systemos/manifest.bin"),
                     ("verified_root_key", INPUT / "os/trusted-key.bin"),
                     ("verified_root_samples", OUT / "samples.bin")]:
    assembly += f'.globl _{symbol}\n_{symbol}:\n.incbin "{path}"\n.balign 8\n'
for symbol, value in [("verified_root_manifest_bytes", (INPUT / "os/manifest.bin").stat().st_size),
                      ("zorn_systemos_manifest_bytes", (INPUT / "systemos/manifest.bin").stat().st_size)]:
    assembly += f".globl _{symbol}\n_{symbol}:\n.quad {value}\n"
for symbol, values in [("verified_root_sample_indices", indices), ("verified_root_sample_lengths", lengths)]:
    assembly += f".globl _{symbol}\n_{symbol}:\n.quad " + ",".join(map(str, values)) + "\n"
(OUT / "inputs.S").write_text(assembly)

objects = []
sources = [TREE / "kits/VerifiedRoot/src/verified_root.c", TREE / "kits/VerifiedRoot/adapters/xnu_crypto.c",
           TREE / "scripts/qemu-entry/verified-root-probe.c", DEVICE / "native/ufs-read/ZornVerifiedRoot.cpp"]
for source in sources:
    cpp = source.suffix == ".cpp"
    recipe = TREE / ("build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json"
                     if cpp else "build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/bsd_init.o.json")
    record = json.loads(recipe.read_text().strip().rstrip(","))
    obj = OUT / (source.stem + ".o")
    command, index = [], 0
    arguments = record["arguments"]
    while index < len(arguments):
        value = arguments[index]
        if value == record["file"]:
            command.append(str(source))
        elif value == "-o":
            command += ["-o", str(obj)]
            index += 1
        elif value in ("-MF", "-MJ"):
            index += 1
        elif value == "-I" and not (Path(record["directory"]) / arguments[index + 1]).is_dir():
            index += 1
        elif value.startswith("-I") and len(value) > 2 and not (Path(record["directory"]) / value[2:]).is_dir():
            pass
        elif value not in ("-MD", "-MP"):
            command.append(value)
        index += 1
    command += ["-I" + str(TREE / "kits/VerifiedRoot/include"), "-Werror"]
    result = subprocess.run(command, cwd=record["directory"], capture_output=True, text=True)
    (OUT / (source.stem + ".log")).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit(result.stderr[-4000:])
    if struct.unpack_from("<4I", obj.read_bytes()) != (0xfeedfacf, 0x100000c, 0, 1):
        raise SystemExit("Unexpected VerifiedRoot object ABI")
    objects.append(obj)
sdk = subprocess.check_output(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], text=True).strip()
subprocess.run(["xcrun", "clang", "-target", "arm64-apple-ios17.0", "-isysroot", sdk, "-c",
                OUT / "inputs.S", "-o", OUT / "inputs.o"], check=True)
archive = OUT / "libZornVerifiedRoot.a"
archive.unlink(missing_ok=True)
subprocess.run(["xcrun", "ar", "rcs", archive, *objects, OUT / "inputs.o"], check=True)
(OUT / "inputs.json").write_text(json.dumps({
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "policies": records,
    "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    "includes_original_crypto_probe": True, "device_verified": False}, indent=2) + "\n")
print("PASS: VerifiedRoot C/XNU crypto, exact OS/SystemOS policies and readonly mdev mount binding")
