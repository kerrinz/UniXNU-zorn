#!/usr/bin/env python3
"""Build/package a zorn diagnostic image; boot only after every step succeeds."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "UniXNU"
OUT = ROOT / "out/zorn"
MANIFEST = OUT / "boot.inputs.json"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boot", action="store_true", help="run the serial-pinned recovery loop after packaging")
    parser.add_argument("--ipsw", type=Path, help="local iPad7,1 / 21H461 IPSW; also accepts UNIXNU_IPSW")
    parser.add_argument("--incremental-patched-tree", action="store_true",
                        help="reuse the existing patched XNU tree; clean patch replay is not yet qualified")
    parser.add_argument("--fd", type=Path, default=ROOT.parent /
                        "Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd")
    args = parser.parse_args()
    args.fd = args.fd.expanduser().resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    record = {"status": "building", "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "serial": "92988a43", "incremental_patched_tree": args.incremental_patched_tree}

    def save():
        pending = MANIFEST.with_suffix(".json.tmp")
        pending.write_text(json.dumps(record, indent=2) + "\n")
        pending.replace(MANIFEST)

    def run(phase, command, cwd=ROOT, env=None):
        record.update(status="building", phase=phase)
        save()
        print(f"[{phase}]", flush=True)
        subprocess.run([str(value) for value in command], cwd=cwd, env=env, check=True)

    save()
    try:
        if not args.fd.is_file():
            raise RuntimeError(f"missing firmware: {args.fd}")
        env = dict(os.environ)
        local_ipsw = args.ipsw
        if local_ipsw is None and not env.get("UNIXNU_IPSW"):
            candidate = ROOT / "iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw"
            if candidate.is_file():
                local_ipsw = candidate
        if local_ipsw is not None:
            local_ipsw = local_ipsw.expanduser().resolve()
            if not local_ipsw.is_file():
                raise RuntimeError(f"missing local IPSW: {local_ipsw}")
            env["UNIXNU_IPSW"] = str(local_ipsw)
        env.pop("UNIXNU_PATCH_LIST", None)
        if args.incremental_patched_tree:
            if not (CORE / "out/zorn/tree/.cache/xnu-work/bsd/kern/bsd_init.c").is_file():
                raise RuntimeError("--incremental-patched-tree requires the existing patched XNU tree")
            env["UNIXNU_PATCH_LIST"] = "1"
        run("defconfig", [CORE / "unixnu", "defconfig", "zorn_defconfig", "-D", ROOT / "UniXNU-zorn"], CORE)
        run("kernel", [CORE / "unixnu", "build", "kernel"], CORE, env)
        trust = OUT / "original-trustcache/original-static-system.bundle"
        run("payload", [sys.executable, ROOT / "uefi-zorn/scripts/make-zorn-payload.py",
                        "--trust-cache", trust])
        image = OUT / "boot.img"
        run("boot-image", [sys.executable, ROOT / "uefi-zorn/scripts/package-zorn-boot.py",
                           "--fd", args.fd, "--ramdisk", OUT / "payload.img", "-o", image])
        inputs = [CORE / "out/zorn/kernel/kernel.macho", CORE / "out/zorn/.config",
                  ROOT / "UniXNU-zorn/board.toml", ROOT / "UniXNU-zorn/configs/zorn_defconfig",
                  ROOT / "uefi-zorn/payload/EFI/UniXNU/unixnu.toml", OUT / "kernel.macho.adt",
                  OUT / "root.img", trust, args.fd]
        record.update(status="ready", phase="packaged", image=str(image), sha256=digest(image),
                      inputs={str(path): digest(path) for path in inputs},
                      completed=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        save()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        record.update(status="failed", error=str(error))
        save()
        raise
    if args.boot:
        # This runner validates the ready manifest and image digest before USB actions.
        subprocess.run([sys.executable, Path(__file__).with_name("run-zorn-debug.py")], check=True)
    print(f"ready {image}: {record['sha256']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
