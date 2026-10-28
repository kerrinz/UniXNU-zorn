#!/usr/bin/env python3
"""Losslessly gzip older generated kernels to recover local build space.

Keeps recent and investigation baselines as raw files. Every gzip is fully
decompressed and checked against the archived kernel SHA before removing its
raw duplicate. Boot images, logs, source, IPSWs and phone backups are untouched.
Restore a historical raw path with gzip -dk PATH/kernel.macho.gz.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/zorn"
PROTECTED = {"0959f393", "47d67736", "50081fc9", "650308ad", "cf7c7a70", "38dd08b2", "ffd39fb4", "af82587b",
             "f8533418", "78c070a8", "d22986fe", "eb55ebe5"}  # lock screen, Data and brightness evidence


def digest(stream):
    sha = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        sha.update(block)
        size += len(block)
    return sha.hexdigest(), size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reserve-gib", type=float, default=4)
    parser.add_argument("--include-plans", action="store_true", help="also losslessly compress older generated kernel-plan.json files")
    parser.add_argument("--keep-recent", type=int, default=14, help="retain 4..14 newest raw archives in addition to investigation baselines")
    args = parser.parse_args()
    if not 1 <= args.reserve_gib <= 8:
        parser.error("reserve must be 1..8 GiB")
    if not 4 <= args.keep_recent <= 14:
        parser.error("keep-recent must be 4..14")
    paths = sorted((OUT / "builds").glob("*/kernel.macho"), key=lambda p: p.stat().st_mtime)
    retained = {p.parent.name for p in paths[-args.keep_recent:]} | PROTECTED
    if args.include_plans:
        plans = sorted((OUT / "builds").glob("*/kernel-plan.json"), key=lambda p: p.stat().st_mtime)
        retained |= {p.parent.name for p in plans[-args.keep_recent:]}
        paths += plans
    reserve = int(args.reserve_gib * 1024**3)
    freed = count = 0
    for path in paths:
        if shutil.disk_usage(OUT).free >= reserve:
            break
        if path.parent.name in retained:
            continue
        target = path.with_name(path.name + ".gz")
        temporary = target.with_suffix(".gz.partial")
        if target.exists() or temporary.exists():
            continue
        build = json.loads((path.parent / "inputs.json").read_text())
        input_suffix = "/kernel/kernel.json" if path.name == "kernel-plan.json" else "/kernel/kernel.macho"
        expected = [value for key, value in build["inputs"].items() if key.endswith(input_suffix)]
        if build.get("status") != "ready" or len(expected) != 1:
            continue
        with path.open("rb") as stream:
            sha, size = digest(stream)
        if sha != expected[0]:
            raise RuntimeError("Refuse mismatched archive " + str(path))
        allocated = path.stat().st_blocks * 512
        try:
            with path.open("rb") as source, gzip.open(temporary, "wb", compresslevel=6) as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
            with gzip.open(temporary, "rb") as stream:
                if digest(stream) != (sha, size):
                    raise RuntimeError("gzip roundtrip differs: " + str(path))
            os.replace(temporary, target)
            report = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "archive": path.parent.name,
                      "artifact": path.name,
                      "sha256": sha, "logical_bytes": size, "gzip": str(target.relative_to(ROOT)),
                      "gzip_bytes": target.stat().st_size, "full_roundtrip_verified": True,
                      "restore": "gzip -dk " + str(target.relative_to(ROOT))}
            with (OUT / "archive-compression.jsonl").open("a") as journal:
                journal.write(json.dumps(report) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
            path.unlink()
            freed += allocated - target.stat().st_blocks * 512
            count += 1
            if count % 8 == 0:
                print(json.dumps({"compressed": count, "freed_bytes": freed,
                                  "free_bytes": shutil.disk_usage(OUT).free}), flush=True)
        finally:
            if temporary.exists():
                temporary.unlink()
    print(json.dumps({"compressed": count, "freed_bytes": freed,
                      "free_bytes": shutil.disk_usage(OUT).free, "reserve_reached": shutil.disk_usage(OUT).free >= reserve}), flush=True)


if __name__ == "__main__":
    main()
