#!/usr/bin/env python3
"""Extract unchanged original iPad7,1 21H461 trust modules from a local IPSW."""
import argparse
import hashlib
import json
import plistlib
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "StaticTrustCache": "da88460e6e513438d5307e5c526f76497a74754476a24da29f239f0c90120fc2",
    "Cryptex1,SystemTrustCache": "d121ba89167e03aafd00fa687c30cd8ebc4ccafd10c1408adb2ba3de12403651",
}
BUNDLE = "7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7"


def der(data, at):
    if at + 2 > len(data):
        raise ValueError("truncated DER header")
    tag, size = data[at:at + 2]
    at += 2
    if size & 128:
        count = size & 127
        if not 0 < count <= 4 or at + count > len(data):
            raise ValueError("invalid DER length")
        size = int.from_bytes(data[at:at + count], "big")
        at += count
    if at + size > len(data):
        raise ValueError("DER value exceeds input")
    return tag, data[at:at + size], at + size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ipsw", type=Path, default=ROOT / "iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw")
    parser.add_argument("--output", type=Path, default=ROOT / "out/zorn/original-trustcache")
    args = parser.parse_args()
    modules, provenance = [], []
    with zipfile.ZipFile(args.ipsw) as archive:
        manifest = plistlib.loads(archive.read("BuildManifest.plist"))
        identities = [i for i in manifest["BuildIdentities"] if i["Info"]["DeviceClass"] == "j120ap"]
        if manifest["ProductBuildVersion"] != "21H461" or len(identities) != 2:
            raise ValueError("require original iPad7,1 21H461 j120ap identities")
        for component, expected in EXPECTED.items():
            member = identities[0]["Manifest"][component]["Info"]["Path"]
            original = archive.read(member)
            digest = hashlib.sha384(original).digest()
            if any(i["Manifest"][component]["Digest"] != digest for i in identities):
                raise ValueError(f"BuildManifest digest mismatch: {component}")
            tag, sequence, end = der(original, 0)
            fields, at = [], 0
            while at < len(sequence):
                kind, value, at = der(sequence, at)
                fields.append((kind, value))
            if (tag != 0x30 or end != len(original) or
                    [kind for kind, _ in fields] != [0x16, 0x16, 0x16, 4] or fields[0][1] != b"IM4P"):
                raise ValueError("unexpected original trust cache IM4P")
            module = fields[3][1]
            if hashlib.sha256(module).hexdigest() != expected:
                raise ValueError(f"original module pin mismatch: {component}")
            count = struct.unpack_from("<I", module, 20)[0]
            if struct.unpack_from("<I", module)[0] != 2 or len(module) != 24 + count * 24:
                raise ValueError("invalid version-2 trust module")
            modules.append(module)
            provenance.append({"component": component, "member": member, "entries": count,
                               "sha256": expected, "manifest_sha384": digest.hex()})
    bundle = struct.pack("<III", 2, 12, 12 + len(modules[0])) + b"".join(modules)
    if hashlib.sha256(bundle).hexdigest() != BUNDLE:
        raise ValueError("original bundle pin mismatch")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "original-static-system.bundle").write_bytes(bundle)
    (args.output / "inputs.json").write_text(json.dumps({"modules": provenance,
        "bundle_sha256": BUNDLE, "original_modules_modified": False}, indent=2) + "\n")
    print(f"original bundle {len(bundle)} bytes, sha256 {BUNDLE}")


if __name__ == "__main__":
    main()
