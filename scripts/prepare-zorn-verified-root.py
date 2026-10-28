#!/usr/bin/env python3
"""Sign and verify the two original SHNGROOT windows; never modifies the image.

The independent owner key stays in ignored host output. A policy is usable
only after the exact original complete image digest and the real C verifier
agree. This prepares inputs, not a claim of device or Apple authentication.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import uuid

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--image", type=Path, default=ROOT / "UniXNU/out/zorn/userdata/userdata-root.img")
parser.add_argument("--output", type=Path, default=ROOT / "out/zorn/verified-root")
args = parser.parse_args()
host = ROOT / "out/zorn/verified-root-host"
library = host / "verified-root.dylib"
if not library.is_file():
    raise SystemExit("Run VerifiedRoot/tests/check.py with --output out/zorn/verified-root-host first")
spec = importlib.util.spec_from_file_location("vr_manifest", ROOT / "UniXNU/kits/VerifiedRoot/tools/manifest.py")
manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest)


class View(ctypes.Structure):
    _fields_ = [("hashes", ctypes.c_void_p), ("image_bytes", ctypes.c_uint64),
                ("block_count", ctypes.c_uint64), ("generation", ctypes.c_uint64),
                ("volume_uuid", ctypes.c_uint8 * 16), ("image_sha256", ctypes.c_uint8 * 32)]


native = ctypes.CDLL(str(library))
native.vr_host_open.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint64, ctypes.POINTER(View)]
native.vr_host_open.restype = ctypes.c_int
native.vr_host_block.argtypes = [ctypes.POINTER(View), ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t]
native.vr_host_block.restype = ctypes.c_int
windows = [
    ("OS", 1048576, 6077580800, "04769D26-2CA0-4825-B443-E2E5F88300F2",
     "e5634d04a8ac35f024845f583394e0a35deb26a04cb0c00286a8674e25a9a4f2"),
    ("SystemOS", 6079643648, 3303014400, "8846FE78-2910-4297-AF97-D59BB6F8FC16",
     "b4908cde41d23e6bc05e6af51a2c9eeb00cf0f863a6a18b1600c96a3fd70414f")]


class Window:
    def __init__(self, source, start, length):
        self.source, self.remaining = source, length
        source.seek(start)

    def read(self, count):
        count = min(count, self.remaining)
        data = self.source.read(count)
        self.remaining -= len(data)
        return data


records = []
with args.image.open("rb") as source:
    header = source.read(4096)
    if args.image.stat().st_size != 9382658048 or header[:8] != b"SHNGROOT" or \
            hashlib.sha256(header[:4064]).digest() != header[4064:]:
        raise SystemExit("Wrong SHNGROOT source/header")
    for index, (name, start, length, volume, digest) in enumerate(windows):
        entry = header[24 + index * 128:24 + (index + 1) * 128]
        if entry[:32].split(b"\0")[0].decode() != name or struct.unpack_from("<QQ", entry, 32) != (start, length):
            raise SystemExit("Window layout changed")
        output = args.output / name.lower()
        output.mkdir(parents=True, exist_ok=True)
        report_path = output / "verification.json"
        report_path.unlink(missing_ok=True)
        print(f"{name}: hashing and signing {length} original bytes", flush=True)
        record = manifest.make(Window(source, start, length), length, host / "keys/owner.pem",
                               host / "keys/owner-public.pem", volume, 1, output)
        if record["image_sha256"] != digest:
            raise SystemExit(f"{name}: complete original digest changed; policy refused")
        encoded = ctypes.create_string_buffer((output / "manifest.bin").read_bytes())
        anchor = ctypes.create_string_buffer((output / "trusted-key.bin").read_bytes())
        view = View()
        if native.vr_host_open(encoded, len(encoded) - 1, anchor, 1, ctypes.byref(view)) or \
                bytes(view.volume_uuid) != uuid.UUID(volume).bytes or bytes(view.image_sha256).hex() != digest:
            raise SystemExit(f"{name}: real C signature/identity verification failed")
        print(f"{name}: C verifying every original block", flush=True)
        stream = Window(source, start, length)
        for block in range(view.block_count):
            data = stream.read(min(4096, view.image_bytes - block * 4096))
            if native.vr_host_block(ctypes.byref(view), block, data, len(data)):
                raise SystemExit(f"{name}: C block verification failed at {block}")
        if stream.remaining:
            raise SystemExit("Incomplete block verification")
        report = dict(record, real_c_signature_and_block_verification=True, blocks_verified=view.block_count,
                      manifest_sha256=hashlib.sha256(encoded.raw[:-1]).hexdigest(),
                      host_only=True, hardware_tested=False, apple_boot_authentication=False)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        records.append(report)
        print(f"{name}: verified {view.block_count} blocks", flush=True)
if (args.output / "os/trusted-key.bin").read_bytes() != (args.output / "systemos/trusted-key.bin").read_bytes():
    raise SystemExit("The two explicit owner anchors differ")
(args.output / "bundle.json").write_text(json.dumps({"windows": records, "host_only": True}, indent=2) + "\n")
print("PASS: both unchanged original windows, owner signatures and every C block check", flush=True)
