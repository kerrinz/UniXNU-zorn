#!/usr/bin/env python3
"""Verify the official skip-Setup/no-auto-dim copy of zorn's RAM Data."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/zorn/ram-data/desktop"
TOOL = ROOT / "UniXNU/scripts/seed-data-skip-setup.py"
BASE = ROOT / "out/zorn/ram-data/seed.json"
REPORT = OUT / "seed.json"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check-only", action="store_true")
args = parser.parse_args()
sys.path.insert(0, str(ROOT / "UniXNU/drivers/DarwinBoot/Test"))
import packed_ramdisk

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

base = json.loads(BASE.read_text())
original = ROOT / base["seed"]
metadata, _ = packed_ramdisk.inspect(original)
assert all(metadata[k] == base[k] for k in ("bytes", "sha256", "encoded_sha256", "encoded_bytes"))
assert metadata["bytes"] == 512 * 1024**2 and base["guest_volatile"] and not base["persistent_backing"]
output = OUT / "data.dbr"
actual, header = packed_ramdisk.inspect(output)
assert actual["bytes"] == metadata["bytes"] and header[32:36] == b"NXSB"
source_report = json.loads(output.with_suffix(".json").read_text())
assert source_report["build"] == "21H461" and source_report["no_auto_dim"]
assert source_report["base_sha256"] == metadata["sha256"]
assert all(source_report["output"][k] == actual[k] for k in ("bytes", "sha256", "encoded_sha256", "encoded_bytes"))
if args.check_only:
    proof = json.loads(REPORT.read_text())
    assert proof["official_tool_sha256"] == digest(TOOL)
    assert proof["base_encoded_sha256"] == metadata["encoded_sha256"]
    assert all(proof[k] == actual[k] for k in ("bytes", "sha256", "encoded_sha256", "encoded_bytes"))
    assert proof["desktop_preferences_verified"] and proof["mobile_preference_owner_verified"]
    print("Verified official desktop RAM Data copy; original seed unchanged")
    raise SystemExit(0)
if REPORT.exists():
    parser.error("refuse to replace an existing desktop report; use --check-only")

def run(*values):
    return subprocess.check_output([str(v) for v in values], stderr=subprocess.PIPE, timeout=120)

checks = {}
with tempfile.TemporaryDirectory(prefix="verify-", dir=OUT) as directory:
    directory = Path(directory)
    raw = directory / "data.raw"
    logical, extents = packed_ramdisk.regions(output.read_bytes())
    with raw.open("wb") as handle:
        handle.truncate(logical)
        for offset, data in extents:
            handle.seek(offset)
            handle.write(data)
    mount = directory / "mount"
    mount.mkdir()
    device = None
    try:
        attached = plistlib.loads(run("hdiutil", "attach", "-imagekey", "diskimage-class=CRawDiskImage", "-readonly", "-nobrowse", "-noautoopen", "-noautofsck",
            "-owners", "on", "-mountpoint", mount, "-plist", raw))
        device = attached["system-entities"][0]["dev-entry"]
        volume = next(e for e in attached["system-entities"] if e.get("mount-point") == str(mount))
        info = plistlib.loads(run("diskutil", "info", "-plist", volume["dev-entry"]))
        assert not info.get("Writable") and info["VolumeUUID"].upper() == base["volume_uuid"]
        for name in source_report["preferences"]:
            path = mount / "mobile/Library/Preferences" / (name + ".plist")
            stat = path.stat()
            assert stat.st_uid == 501 and stat.st_mode & 0o777 == 0o600
            checks[name] = {"uid": stat.st_uid, "gid": stat.st_gid, "mode": "0600",
                "sha256": digest(path), "values": plistlib.loads(path.read_bytes())}
        assert checks["com.apple.purplebuddy"]["values"]["SetupDone"]
        assert checks["com.apple.migration"]["values"]["LastSystemVersion"] == "21H461"
        for key in ("SBDisableAutoDim", "SBDontDimOrLockOnAC", "SBDisableIdleSleep"):
            assert checks["com.apple.springboard"]["values"][key] is True
    finally:
        if device:
            run("hdiutil", "detach", device)
assert digest(original) == metadata["encoded_sha256"]
proof = dict(base)
proof.update(actual)
proof.update(seed=str(output.relative_to(ROOT)), skip_setup=True, no_auto_dim=True,
    official_tool_sha256=digest(TOOL), base_encoded_sha256=metadata["encoded_sha256"],
    desktop_preferences_verified=True, mobile_preference_owner_verified=True,
    original_seed_modified=False, added_activation_records_or_keys=False, preferences=checks)
REPORT.write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps({"seed": proof["seed"], "volume_uuid": proof["volume_uuid"],
    "encoded_bytes": proof["encoded_bytes"], "preferences_verified": len(checks),
    "mobile_uid": 501, "original_seed_modified": False}, indent=2))
