#!/usr/bin/env python3
"""Read-only K80 Data-store reservation and exact preimage backup.

Does not write the phone, format a filesystem, or change GPT. A later installer
must revalidate this plan/preimage before installing any overlay metadata.
"""
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import threading
import zlib
import os
import argparse
from zorn_data_profile import DIRECTORY,SEED_REPORT,RELATIVE_FIRST,PAGES,BITMAP_BLOCKS,WINDOW_BLOCKS,NAME

ROOT = Path(__file__).resolve().parents[2]
ADB = "/Users/kerrinz/env/android_sdk/platform-tools/adb"
SERIAL = "92988a43"
OUT = DIRECTORY
BLOCK = 4096
PARTITION_BYTES = 249595670528
ROOT_BYTES = 9382658048
LOG_RELATIVE = 2291712


def adb(*args, binary=False):
    p = subprocess.run([ADB, "-s", SERIAL, *map(str, args)], capture_output=True,
                       timeout=20, check=True)
    return p.stdout if binary else p.stdout.decode().strip()


def read_blocks(device, first, blocks):
    if device not in ("/dev/block/sda", "/dev/block/by-name/userdata") or first < 0 or not 0 < blocks <= 32:
        raise ValueError("Invalid bounded read")
    b = adb("exec-out", "sh", "-c", f"dd if={device} bs=4096 skip={first} count={blocks} 2>/dev/null", binary=True)
    if len(b) != blocks * BLOCK:
        raise ValueError("Short device read")
    return b


def device_window_hash():
    result=subprocess.run([ADB,'-s',SERIAL,'exec-out','sh','-c',
        f'set -o pipefail\ndd if=/dev/block/by-name/userdata bs=4096 skip={RELATIVE_FIRST} count={WINDOW_BLOCKS} 2>/tmp/unixnu-zorn-blank-read-status | sha256sum\nzorn_blank_rc=$?\ncat /tmp/unixnu-zorn-blank-read-status\nexit "$zorn_blank_rc"'],capture_output=True,check=True,timeout=900)
    text=result.stdout.decode();actual=text.split()[0];records=text.split('\n',1)[1]
    if not re.fullmatch('[0-9a-f]{64}',actual) or not re.search(rf'\b{WINDOW_BLOCKS}\+0 records out\b',records):
        raise ValueError('whole window hash/read count failed: '+text)
    return actual,records


def gpt(header, entries, current):
    if len(header) != BLOCK or header[:8] != b"EFI PART":
        raise ValueError("GPT signature/size")
    if struct.unpack_from("<I", header, 8)[0] != 0x10000 or struct.unpack_from("<I", header, 12)[0] != 92:
        raise ValueError("GPT revision/header size")
    if struct.unpack_from("<Q", header, 24)[0] != current:
        raise ValueError("GPT self address")
    h = bytearray(header[:92]); expected = struct.unpack_from("<I", h, 16)[0]; h[16:20] = bytes(4)
    if zlib.crc32(h) != expected:
        raise ValueError("GPT header CRC")
    count, size = struct.unpack_from("<2I", header, 80)
    if not 1 <= count <= 256 or size != 128 or len(entries) < count * size:
        raise ValueError("GPT entries geometry")
    if zlib.crc32(entries[:count * size]) != struct.unpack_from("<I", header, 88)[0]:
        raise ValueError("GPT entry CRC")
    found = []
    for i in range(count):
        e = entries[i * size:(i + 1) * size]
        if e[56:128].decode("utf-16-le").rstrip("\0") == "userdata":
            first, last = struct.unpack_from("<2Q", e, 32)
            found.append((first, last))
    if len(found) != 1:
        raise ValueError("Require exactly one userdata entry")
    first, last = found[0]
    if first == 0 or last < first or (last - first + 1) * BLOCK != PARTITION_BYTES:
        raise ValueError("K80 userdata capacity differs")
    return {"userdata_first": first, "userdata_last": last,
            "disk_guid_raw": header[56:72].hex(), "header_crc32": expected,
            "entries_crc32": struct.unpack_from("<I", header, 88)[0]}


def window(first, last):
    if first < 1 or last < first or (last - first + 1) * BLOCK != PARTITION_BYTES:
        raise ValueError("Unexpected partition")
    absolute = first + RELATIVE_FIRST
    end = absolute + WINDOW_BLOCKS
    if RELATIVE_FIRST * BLOCK < ROOT_BYTES + 8 * 1024**2 or RELATIVE_FIRST <= LOG_RELATIVE:
        raise ValueError("Store overlaps root/log guard")
    if end > last + 1 or end - 1 > 0xffffffff:
        raise ValueError("Store exceeds partition or WRITE(10)")
    if NAME=='8g' and RELATIVE_FIRST <= 2621440+131077:
        raise ValueError('New store overlaps legacy Data')
    return absolute, WINDOW_BLOCKS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blank-only',action='store_true',help='on-device zero hash; no content export; require a completely zero window')
    args=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    plan_path = OUT / "plan.json"
    if plan_path.exists():
        raise SystemExit("Existing immutable reservation plan: inspect/reuse it; do not overwrite")
    if adb("get-state") != "recovery" or adb("get-serialno") != SERIAL or \
            adb("shell", "getprop", "ro.product.device") != "zorn" or \
            adb("shell", "getprop", "ro.boot.slot_suffix") != "_b":
        raise ValueError("Require exact K80 recovery and slot b")
    target = adb("shell", "readlink", "-f", "/dev/block/by-name/userdata")
    if not re.fullmatch(r"/dev/block/sda[0-9]+", target):
        raise ValueError("userdata is not on expected 4KiB LUN0")
    if int(adb("shell", "blockdev", "--getsize64", "/dev/block/by-name/userdata")) != PARTITION_BYTES:
        raise ValueError("Actual userdata size mismatch")
    header = read_blocks("/dev/block/sda", 1, 1)
    count, size = struct.unpack_from("<2I", header, 80)
    if not 1 <= count <= 256 or size != 128 or struct.unpack_from("<Q", header, 72)[0] != 2:
        raise ValueError("Primary GPT geometry")
    n = (count * size + BLOCK - 1) // BLOCK
    entries = read_blocks("/dev/block/sda", 2, n)
    geometry = gpt(header, entries, 1)
    backup_lba = struct.unpack_from("<Q", header, 32)[0]
    backup_header = read_blocks("/dev/block/sda", backup_lba, 1)
    be = struct.unpack_from("<Q", backup_header, 72)[0]
    if not 2 <= be < backup_lba or be + n > backup_lba:
        raise ValueError("Backup GPT table bounds")
    backup_entries = read_blocks("/dev/block/sda", be, n)
    bg = gpt(backup_header, backup_entries, backup_lba)
    if any(bg[k] != geometry[k] for k in ("userdata_first", "userdata_last", "disk_guid_raw", "entries_crc32")) or \
            entries[:count * size] != backup_entries[:count * size] or struct.unpack_from("<Q", backup_header, 32)[0] != 1:
        raise ValueError("Primary/backup GPT mismatch")
    absolute, blocks = window(geometry["userdata_first"], geometry["userdata_last"])
    root = read_blocks("/dev/block/by-name/userdata", 0, 1)
    with (ROOT / "UniXNU/out/zorn/userdata/userdata-root.img").open("rb") as f:
        expected_root = f.read(BLOCK)
    if root != expected_root or root[:8] != b"SHNGROOT" or struct.unpack_from("<Q", root, 16)[0] != ROOT_BYTES:
        raise ValueError("Installed system manifest differs")
    seed = json.loads(SEED_REPORT.read_text())
    if seed["bytes"] != PAGES * BLOCK or seed["volume_uuid"] != "C7D77FF3-6437-4C4A-8E05-E8E239AC1641":
        raise ValueError("Data seed size/UUID differs")
    artifacts = {"primary-header.bin": header, "primary-entries.bin": entries,
                 "backup-header.bin": backup_header, "backup-entries.bin": backup_entries,
                 "root-manifest.bin": root,
                 "before-window.bin": read_blocks("/dev/block/by-name/userdata", RELATIVE_FIRST - 1, 1),
                 "after-window.bin": read_blocks("/dev/block/by-name/userdata", RELATIVE_FIRST + blocks, 1)}
    for name, data in artifacts.items():
        path = OUT / name
        if path.exists() and path.read_bytes() != data:
            raise ValueError("Existing reservation evidence differs: " + name)
        path.write_bytes(data)
    backup = OUT / "preimage.bin.gz"
    temporary = OUT / "preimage.bin.gz.partial"
    if backup.exists() or temporary.exists():
        raise ValueError("Existing preimage must be inspected, not overwritten")
    command = f"dd if=/dev/block/by-name/userdata bs=4096 skip={RELATIVE_FIRST} count={blocks} 2>/dev/null"
    process=timer=None
    digest = hashlib.sha256(); total = 0
    zero=bytes(1024*1024)
    if args.blank_only:
        expected=hashlib.sha256()
        for at in range(0,blocks*BLOCK,len(zero)):expected.update(zero[:min(len(zero),blocks*BLOCK-at)])
        actual,records=device_window_hash()
        proof=dict(phone_writes=False,contents_exported=False,bytes=blocks*BLOCK,sha256=actual,
                   zero_sha256=expected.hexdigest(),all_zero=actual==expected.hexdigest(),dd_records=records)
        (OUT/'blank-check.json').write_text(json.dumps(proof,indent=2)+'\n')
        if not proof['all_zero']:raise ValueError('Window is not all-zero; no backup export or device write attempted')
    else:
        process = subprocess.Popen([ADB, "-s", SERIAL, "exec-out", "sh", "-c", command],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        timer = threading.Timer(900 if NAME=='8g' else 180, process.kill); timer.start()
    try:
        with gzip.open(temporary, "wb", compresslevel=1) as out:
            while True:
                data = (zero[:min(len(zero),blocks*BLOCK-total)] if total<blocks*BLOCK else b'') if args.blank_only else process.stdout.read(128*1024)
                if not data:
                    break
                total += len(data)
                if total > blocks * BLOCK:
                    raise ValueError("Preimage exceeds reservation")
                digest.update(data); out.write(data)
                if total%(128*1024**2)==0:print(f'preimage {total}/{blocks*BLOCK} bytes',flush=True)
        if (process and process.wait(timeout=5)) or total != blocks * BLOCK:
            raise ValueError("Incomplete preimage backup")
    finally:
        if timer:timer.cancel()
        if process and process.poll() is None:
            process.kill(); process.wait(timeout=5)
    check = hashlib.sha256(); check_bytes = 0
    with gzip.open(temporary, "rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            check.update(data); check_bytes += len(data)
    if check_bytes != total or check.digest() != digest.digest():
        raise ValueError("Compressed preimage roundtrip differs")
    temporary.rename(backup)
    metadata = bytearray((1 + BITMAP_BLOCKS) * BLOCK)
    metadata[:8] = b"SHNGDATA"
    struct.pack_into("<IIQ", metadata, 8, 1, 64, PAGES)
    metadata[24:56] = bytes.fromhex(seed["sha256"])
    struct.pack_into("<I", metadata, 56, 1)
    struct.pack_into("<I", metadata, 60, zlib.crc32(metadata[:60]))
    (OUT / "empty-overlay-metadata.bin").write_bytes(metadata)
    plan = {"status": "prepared-readonly-no-phone-writes", "serial": SERIAL, "product": "zorn", "slot": "b",
            "data_profile":NAME,
            "preimage_blank_proven":args.blank_only,
            **geometry, "relative_first_lba": RELATIVE_FIRST, "absolute_first_lba": absolute,
            "blocks": blocks, "bytes": total, "logical_data_bytes": PAGES * BLOCK,
            "pages": PAGES, "bitmap_blocks": BITMAP_BLOCKS,
            "seed_sha256": seed["sha256"], "volume_uuid": seed["volume_uuid"],
            "root_manifest_sha256": hashlib.sha256(root).hexdigest(),
            "backup": str(backup.relative_to(ROOT)), "preimage_sha256": digest.hexdigest(),
            "backup_roundtrip_verified": True, "backup_compressed_bytes": backup.stat().st_size,
            "evidence_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()},
            "empty_metadata_sha256": hashlib.sha256(metadata).hexdigest(),
            "phone_writes": False, "installed": False,
            "scope": "Only this exact dedicated userdata window may later back the Data overlay; OS/SystemOS/log/GPT unchanged"}
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
