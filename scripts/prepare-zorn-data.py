#!/usr/bin/env python3
"""Create an isolated, volatile APFS Data seed; never accesses the phone.

Copy the initial var skeleton from the pinned readonly OS, excluding staged
apps. Add empty runtime/persona directories, not user records or key material.
DBRDISK1 retains only nonzero pages for the native RamBlock component.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/zorn/ram-data"
OUT.mkdir(parents=True, exist_ok=True)
IMAGE = OUT / "zorn-data-512.cdr"
PACKED = OUT / "zorn-data-512.dbr"
SOURCE = ROOT / "UniXNU/out/zorn/userdata/userdata-root.img"
SOURCE_MOUNT = OUT / "os-readonly"
TARGET_MOUNT = OUT / "data-seed"
DIRECTORIES = (
    "db/dslocal/nodes/Default/users", "db/dslocal/nodes/Default/groups",
    "db/dslocal/nodes/Default/config", "containers/Data/System", "containers/Data/Application",
    "containers/Shared/SystemGroup", "PersonaVolumes", "preboot", "root", "tmp", "run", "Library",
    "keybags/backup", "mobile/Library/Preferences", "mobile/Library/Caches", "mobile/Library/Logs",
    "mobile/Containers", "mobile/Documents", "mobile/Media", "mobile/tmp",
)


def run(*args):
    return subprocess.check_output([str(v) for v in args], stderr=subprocess.PIPE, timeout=120)


def attach(image, target, readonly=False, section=None):
    target.mkdir(exist_ok=True)
    args = ["hdiutil", "attach", "-nobrowse", "-noautoopen", "-noautofsck", "-owners", "off"]
    if readonly:
        args += ["-readonly", "-imagekey", "diskimage-class=CRawDiskImage"]
    if section:
        args += ["-section", section]
    info = plistlib.loads(run(*args, "-mountpoint", target, "-plist", image))
    raw = info["system-entities"][0]["dev-entry"]
    volumes = [e for e in info["system-entities"] if e.get("mount-point") == str(target)]
    if len(volumes) != 1:
        run("hdiutil", "detach", raw)
        raise SystemExit("Expected exactly one volume of our newly attached image")
    volume = plistlib.loads(run("diskutil", "info", "-plist", volumes[0]["dev-entry"]))
    if readonly and volume.get("Writable"):
        run("hdiutil", "detach", raw)
        raise SystemExit("Original OS unexpectedly writable")
    return raw, volume


if IMAGE.exists() or PACKED.exists():
    sys.exit("Refuse to overwrite an existing Data seed")
source_device = target_device = None
count = size = 0
try:
    source_device, source_info = attach(SOURCE, SOURCE_MOUNT, True, "2048,11870275")
    if source_info["VolumeUUID"].upper() != "04769D26-2CA0-4825-B443-E2E5F88300F2" or \
            hashlib.sha256((SOURCE_MOUNT / "sbin/launchd").read_bytes()).hexdigest() != \
            "8cec9a3c44a443b08e977ccc5d577850316ad428c575dc01f09b018dbd5b6a25":
        sys.exit("Require the unchanged pinned OS UUID and original launchd")
    run("hdiutil", "create", "-size", "512m", "-layout", "NONE", "-fs", "APFS",
        "-volname", "ZornData", "-type", "UDTO", IMAGE)
    target_device, volume = attach(IMAGE, TARGET_MOUNT)
    initial = SOURCE_MOUNT / "private/var"
    for current, dirs, files in os.walk(initial, followlinks=False):
        dirs[:] = [name for name in dirs if name != "staged_system_apps"]
        source_dir = Path(current)
        dest = TARGET_MOUNT / source_dir.relative_to(initial)
        dest.mkdir(exist_ok=True)
        for name in list(dirs) + files:
            src, dst = source_dir / name, dest / name
            if src.is_symlink():
                os.symlink(os.readlink(src), dst)
                if name in dirs:
                    dirs.remove(name)
            elif src.is_file():
                shutil.copy2(src, dst)
                count += 1
                size += src.stat().st_size
        os.chmod(dest, stat.S_IMODE(source_dir.stat().st_mode))
    for name in DIRECTORIES:
        (TARGET_MOUNT / name).mkdir(parents=True, exist_ok=True)
    os.chmod(TARGET_MOUNT / "tmp", 0o1777)
finally:
    if target_device:
        run("hdiutil", "detach", target_device)
    if source_device:
        run("hdiutil", "detach", source_device)

with IMAGE.open("rb") as f:
    header = f.read(4096)
if IMAGE.stat().st_size != 512 * 1024**2 or header[32:36] != b"NXSB":
    sys.exit("Expected a raw 512 MiB APFS container")
sys.path.insert(0, str(ROOT / "UniXNU/drivers/DarwinBoot/Test"))
import packed_ramdisk
metadata = packed_ramdisk.pack(IMAGE, PACKED)
if metadata["encoded_bytes"] > 48 * 1024**2:
    sys.exit("Seed is too large for the current FAT payload")
report = dict(volume_uuid=volume["VolumeUUID"].upper(), **metadata, source_regular_files=count,
              source_regular_bytes=size, source_os_readonly=True, original_os_inputs_modified=False,
              seed=str(PACKED.relative_to(ROOT)), guest_volatile=True, persistent_backing=False,
              added_user_records_or_keys=False, ownership_preserved=False,
              ownership_note="Host owns-off preparation; guest permissions require separate qualification",
              production_storage_qualified=False)
(OUT / "seed.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
