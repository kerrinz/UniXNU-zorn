#!/usr/bin/env python3
"""Read numeric metadata from the pinned OS and prepare a RAM Data-only policy."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import os
import plistlib
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "UniXNU-zorn/native/startup-policy"
REPORT = DEST / "data-permissions.json"
HEADER = DEST / "DataPermissions.h"
BASE = ROOT / "out/zorn/ram-data/desktop/seed.json"


def encode(proof):
    entries = proof["entries"]
    assert 1 <= len(entries) <= 512
    paths = set()
    rows = []
    for row in entries:
        name = row["relative"]
        assert name not in paths and len(name) < 400
        assert not name.startswith("/") and ".." not in PurePosixPath(name).parts
        assert all(32 <= ord(c) < 127 and c not in '\\"' for c in name)
        assert row["type"] in (stat.S_IFDIR, stat.S_IFREG)
        assert 0 <= row["uid"] < 100000 and 0 <= row["gid"] < 100000 and 0 <= row["mode"] <= 0o7777
        paths.add(name)
        path = "/private/var" + ("/" + name if name else "")
        rows.append(f'    {{{json.dumps(path)}, {row["uid"]}, {row["gid"]}, 0{row["mode"]:o}, 0{row["type"]:o}}},')
    return ("// Generated from readonly iPadOS 17.7.11 metadata; no file contents.\n"
            "#pragma once\nstruct ZornDataPermissionSpec { const char *path; unsigned uid, gid, mode, type; };\n"
            "static const struct ZornDataPermissionSpec zorn_data_permission_specs[] = {\n" +
            "\n".join(rows) + "\n};\n")


def run(*args):
    return subprocess.check_output(list(map(str, args)), stderr=subprocess.PIPE, timeout=90)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        proof = json.loads(REPORT.read_text())
        assert proof["os_build"] == "21H461" and proof["source_owners_on"] and proof["source_readonly"]
        assert HEADER.read_text() == encode(proof)
        print(f'Verified numeric Data policy: {len(proof["entries"])} fixed existing paths')
        return
    if REPORT.exists() or HEADER.exists():
        parser.error("refuse existing policy; use --check-only")
    sys.path.insert(0, str(ROOT / "UniXNU/drivers/DarwinBoot/Test"))
    import packed_ramdisk
    seed_report = json.loads(BASE.read_text())
    seed = ROOT / seed_report["seed"]
    assert hashlib.sha256(seed.read_bytes()).hexdigest() == seed_report["encoded_sha256"]
    source = ROOT / "UniXNU/out/zorn/userdata/userdata-root.img"
    out = ROOT / "out/zorn/ram-data"
    entries, skipped = {}, []
    devices = []
    with tempfile.TemporaryDirectory(prefix="metadata-", dir=out) as directory:
        directory = Path(directory)
        logical, extents = packed_ramdisk.regions(seed.read_bytes())
        raw = directory / "data.raw"
        with raw.open("wb") as f:
            f.truncate(logical)
            for at, data in extents:
                f.seek(at); f.write(data)
        mounts = {}
        try:
            for label, image, section, expected in (
                    ("os", source, "2048,11870275", "04769D26-2CA0-4825-B443-E2E5F88300F2"),
                    ("data", raw, None, seed_report["volume_uuid"])):
                mount = directory / label
                mount.mkdir()
                command = ["hdiutil", "attach", "-imagekey", "diskimage-class=CRawDiskImage", "-readonly",
                           "-nobrowse", "-noautoopen", "-noautofsck", "-owners", "on", "-mountpoint", mount, "-plist"]
                if section: command += ["-section", section]
                info = plistlib.loads(run(*command, image))
                devices.append(info["system-entities"][0]["dev-entry"])
                volume = next(e for e in info["system-entities"] if e.get("mount-point") == str(mount))
                metadata = plistlib.loads(run("diskutil", "info", "-plist", volume["dev-entry"]))
                assert not metadata["Writable"] and metadata["VolumeUUID"].upper() == expected
                mounts[label] = mount
            assert hashlib.sha256((mounts["os"] / "sbin/launchd").read_bytes()).hexdigest() == \
                "8cec9a3c44a443b08e977ccc5d577850316ad428c575dc01f09b018dbd5b6a25"
            accounts = {}
            passwd = mounts["os"] / "private/etc/passwd"
            for line in passwd.read_text().splitlines():
                fields = line.split(":")
                if len(fields) > 3 and fields[2].isdigit() and fields[3].isdigit():
                    if fields[0] in ("root", "mobile"):
                        accounts[fields[0]] = [int(fields[2]), int(fields[3])]
                    if int(fields[2]) == 33:
                        accounts["bundle_owner"] = [int(fields[2]), int(fields[3])]
                        bundle_account = fields[0]
            assert accounts == {"root": [0, 0], "mobile": [501, 501], "bundle_owner": [33, 33]}, accounts
            for label, base in (("os", mounts["os"] / "private/var"), ("data", mounts["data"])):
                for current, dirs, files in os.walk(base, followlinks=False):
                    dirs[:] = [n for n in dirs if n != "staged_system_apps"]
                    for path in [Path(current), *(Path(current) / n for n in files)]:
                        relative = str(path.relative_to(base))
                        if relative == ".": relative = ""
                        if relative in entries: continue
                        actual = path.lstat()
                        kind = stat.S_IFMT(actual.st_mode)
                        if kind not in (stat.S_IFDIR, stat.S_IFREG):
                            skipped.append(relative); continue
                        if label == "os":
                            uid, gid, mode = actual.st_uid, actual.st_gid, stat.S_IMODE(actual.st_mode)
                        else:
                            uid, gid = accounts["mobile"] if relative == "mobile" or relative.startswith("mobile/") else accounts["root"]
                            if relative == "containers/Bundle": uid, gid = accounts["bundle_owner"]
                            mode = stat.S_IMODE(actual.st_mode)
                        target = mounts["data"] / relative
                        assert target.exists() and stat.S_IFMT(target.lstat().st_mode) == kind, relative
                        entries[relative] = dict(relative=relative, uid=uid, gid=gid, mode=mode, type=kind, origin=label)
        finally:
            for device in reversed(devices): run("hdiutil", "detach", device)
    rows = sorted(entries.values(), key=lambda r: (r["type"] != stat.S_IFDIR, r["relative"].count("/"), r["relative"]))
    proof = dict(os_build="21H461", source_volume_uuid="04769D26-2CA0-4825-B443-E2E5F88300F2",
                 source_readonly=True, source_owners_on=True, source_accounts=accounts, source_bundle_account=bundle_account,
                 seed_encoded_sha256=seed_report["encoded_sha256"], entries=rows, skipped_nonregular_paths=sorted(set(skipped)),
                 creates_files=False, changes_file_contents=False, allowed_backend="verified volatile RAM Data only",
                 hardware_verified=False)
    header = encode(proof)
    REPORT.write_text(json.dumps(proof, indent=2) + "\n")
    HEADER.write_text(header)
    print(f"Prepared {len(rows)} numeric metadata entries; readonly source/seed unchanged")


if __name__ == "__main__": main()
