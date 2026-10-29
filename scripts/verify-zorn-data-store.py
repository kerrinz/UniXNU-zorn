#!/usr/bin/env python3
"""Verify the readonly trial/window; optionally provision only five header blocks.

The optional initialization is restricted to the exact backed-up reservation,
after a matched mode1 run and a full preimage check. No GPT/OS formatting.
"""
import argparse
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import threading
from zorn_data_profile import DIRECTORY,NAME

ROOT = Path(__file__).resolve().parents[2]
OUT = DIRECTORY


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


prepare = load("store_prepare", Path(__file__).with_name("prepare-zorn-data-store.py"))
symbols = load("store_messages", Path(__file__).with_name("symbolicate-zorn-gui.py"))


def window_hash(replacement=None, backup=False):
    if NAME=='8g' and not backup:
        if replacement is not None:raise ValueError('replacement only applies to local backup')
        return prepare.device_window_hash()[0]
    h = hashlib.sha256(); total = 0
    process = timer = None
    if backup:
        stream = gzip.open(OUT / "preimage.bin.gz", "rb")
    else:
        command = f"dd if=/dev/block/by-name/userdata bs=4096 skip={prepare.RELATIVE_FIRST} count={prepare.WINDOW_BLOCKS} 2>/dev/null"
        process = subprocess.Popen([prepare.ADB, "-s", prepare.SERIAL, "exec-out", "sh", "-c", command],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        timer = threading.Timer(180, process.kill); timer.start(); stream = process.stdout
    try:
        while True:
            b = stream.read(128 * 1024)
            if not b:
                break
            if replacement is not None and total < len(replacement):
                n = min(len(b), len(replacement) - total)
                b = replacement[total:total + n] + b[n:]
            total += len(b)
            if total > prepare.WINDOW_BLOCKS * 4096:
                raise ValueError("Oversized reservation stream")
            h.update(b)
        if total != prepare.WINDOW_BLOCKS * 4096 or (process and process.wait(timeout=5)):
            raise ValueError("Short/failed reservation stream")
    finally:
        if timer:
            timer.cancel()
        stream.close()
        if process and process.poll() is None:
            process.kill(); process.wait(timeout=5)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--initialize", action="store_true", help="write/readback only the explicitly backed-up overlay metadata")
    args = p.parse_args()
    plan_path = OUT / "plan.json"; plan = json.loads(plan_path.read_text())
    if plan.get("installed"):
        raise ValueError("Overlay already provisioned; refusing reinitialization")
    if not plan.get("backup_roundtrip_verified") or prepare.window(plan["userdata_first"], plan["userdata_last"]) != \
            (plan["absolute_first_lba"], plan["blocks"]):
        raise ValueError("Reservation plan mismatch")
    if plan.get('data_profile','512m')!=NAME or plan['logical_data_bytes']!=prepare.PAGES*4096:
        raise ValueError('selected Data profile differs from reservation')
    run = json.loads((args.run / "run.json").read_text()); build = json.loads((args.run / "build-inputs.json").read_text())
    archive = ROOT / "out/zorn/builds" / run["sha256"][:8]
    if run.get("status") != "recovered" or run.get("kernel_log_changed") is not True or \
            run.get("serial") != prepare.SERIAL or run.get("product") != "zorn" or run.get("slot") != "b" or \
            build.get("status") != "ready" or build.get("data_store_mode") != 1 or build.get('data_profile','512m')!=NAME or build != json.loads((archive / "inputs.json").read_text()):
        raise ValueError("Require exact recovered mode1 probe with changed log")
    if build['inputs'].get(str(plan_path))!=hashlib.sha256(plan_path.read_bytes()).hexdigest():
        raise ValueError('probe did not use this exact prepared plan')
    if hashlib.file_digest((archive / "boot.img").open("rb"), "sha256").hexdigest() != run["sha256"] or \
            hashlib.file_digest((archive / "kernel.macho").open("rb"), "sha256").hexdigest() != build["inputs"][str(ROOT / "UniXNU/out/zorn/kernel/kernel.macho")]:
        raise ValueError("Probe boot/kernel archive mismatch")
    matches = []
    for text in symbols.messages(args.run / "checkpoints.bin"):
        matches += re.findall(r"DSTORE mode=1 open=0 state=4 header=9 gpt=0/255 present=0 writes=0 loaded=0 errors=0", text)
    if not matches:
        raise ValueError("No real readonly probe record with validated GPT and refused foreign header")
    if prepare.adb("get-state") != "recovery" or prepare.adb("get-serialno") != prepare.SERIAL or \
            prepare.adb("shell", "getprop", "ro.product.device") != "zorn" or \
            prepare.adb("shell", "getprop", "ro.boot.slot_suffix") != "_b":
        raise ValueError("Require exact K80 recovery/slot")

    def boundaries():
        header = prepare.read_blocks("/dev/block/sda", 1, 1)
        import struct
        backup_lba = struct.unpack_from("<Q", header, 32)[0]
        if header != (OUT / "primary-header.bin").read_bytes():
            raise ValueError("Primary GPT changed")
        backup_header = prepare.read_blocks("/dev/block/sda", backup_lba, 1)
        entries_blocks = len((OUT / "primary-entries.bin").read_bytes()) // 4096
        current = {"primary-header.bin": header,
                   "primary-entries.bin": prepare.read_blocks("/dev/block/sda", 2, entries_blocks),
                   "backup-header.bin": backup_header,
                   "backup-entries.bin": prepare.read_blocks("/dev/block/sda", struct.unpack_from("<Q", backup_header, 72)[0], entries_blocks),
                   "root-manifest.bin": prepare.read_blocks("/dev/block/by-name/userdata", 0, 1),
                   "before-window.bin": prepare.read_blocks("/dev/block/by-name/userdata", prepare.RELATIVE_FIRST - 1, 1),
                   "after-window.bin": prepare.read_blocks("/dev/block/by-name/userdata", prepare.RELATIVE_FIRST + prepare.WINDOW_BLOCKS, 1)}
        if any(hashlib.sha256(v).hexdigest() != plan["evidence_sha256"][k] for k, v in current.items()):
            raise ValueError("GPT/root/fence readback changed")

    boundaries()
    if window_hash(backup=True) != plan["preimage_sha256"] or window_hash() != plan["preimage_sha256"]:
        raise ValueError("Current reserved window differs from its complete preimage; refusing initialization")
    proof = {"run": str(args.run), "boot_sha256": run["sha256"], "readonly_probe_record": matches[-1],
             "whole_window_unchanged": True, "preimage_sha256": plan["preimage_sha256"],
             "gpt_root_fences_unchanged": True, "phone_writes": False}
    (OUT / "readonly-verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    if not args.initialize:
        print(json.dumps(proof, indent=2)); return
    metadata = (OUT / "empty-overlay-metadata.bin").read_bytes()
    metadata_blocks=1+prepare.BITMAP_BLOCKS
    if len(metadata) != metadata_blocks * 4096 or hashlib.sha256(metadata).hexdigest() != plan["empty_metadata_sha256"]:
        raise ValueError("Prepared five-block metadata changed")
    expected = window_hash(replacement=metadata, backup=True)
    attempt = {"status": "prepared", "serial": prepare.SERIAL, "relative_first_lba": prepare.RELATIVE_FIRST,
               "data_profile":NAME,"blocks_to_write": metadata_blocks,
               "installer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "probe_boot_sha256":run['sha256'],"expected_full_window_sha256": expected, "preimage_sha256": plan["preimage_sha256"]}
    (OUT / "install-attempt.json").write_text(json.dumps(attempt, indent=2) + "\n")
    remote = "/tmp/unixnu-zorn-data-overlay-header.bin"
    prepare.adb("push", OUT / "empty-overlay-metadata.bin", remote)
    if prepare.adb("exec-out", "cat", remote, binary=True) != metadata:
        raise ValueError("Recovery tmpfs metadata copy mismatch; no store write attempted")
    # Exact bounded metadata write; old page contents remain outside the five blocks.
    prepare.adb("shell", f"dd if={remote} of=/dev/block/by-name/userdata bs=4096 seek={prepare.RELATIVE_FIRST} count={metadata_blocks} conv=notrunc")
    prepare.adb("shell", "sync")
    readback=b''.join(prepare.read_blocks('/dev/block/by-name/userdata',prepare.RELATIVE_FIRST+i,min(32,metadata_blocks-i)) for i in range(0,metadata_blocks,32))
    if readback != metadata or window_hash() != expected:
        raise ValueError("Metadata/full-window readback differs; stay in recovery and preserve preimage")
    boundaries()
    attempt.update(status="installed-readback-verified", gpt_root_fences_unchanged=True)
    (OUT / "install-attempt.json").write_text(json.dumps(attempt, indent=2) + "\n")
    plan.update(status="installed-metadata-readback-verified", phone_writes=True,
                installed=True, installed_metadata_blocks=metadata_blocks, readonly_probe_verified=True,
                initialized_full_window_sha256=expected, initialized_at=datetime.datetime.now().astimezone().isoformat())
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(attempt, indent=2))


if __name__ == "__main__":
    main()
