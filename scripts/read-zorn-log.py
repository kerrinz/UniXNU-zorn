#!/usr/bin/env python3
"""Read the zorn UniXNU checkpoint block from recovery over adb.

Only reads /dev/block/by-name/userdata on the K80 with serial 92988a43.
The 4 KiB block is 4 MiB beyond the end of the flashed SHNGROOT image.
"""

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import uuid
from pathlib import Path


SERIAL = "92988a43"
BLOCK_SIZE = 4096
LOG_BLOCK = 9382658048 // BLOCK_SIZE + 1024
FORMATS = {b"ZORNLOG1": (510, 8), b"ZORNLOG2": (340, 12), b"ZORNLOG3": (180, 12),
           b"ZORNLOG4": (172, 12), b"ZORNLOG5": (162, 12), b"ZORNLOG6": (140, 12), b"ZORNLOG7": (136, 12), b"ZORNLOG8": (134, 12), b"ZORNLOG9": (98, 12), b"ZORNLOGA": (96, 12), b"ZORNLOGB": (92, 12), b"ZORNLOGC": (64, 12), b"ZORNLOGD": (84, 12)}


def touch_raw(block):
    if len(block) != BLOCK_SIZE or block[:8] != b"ZORNLOGC":
        return None
    if block[784:792] not in (b"ZORNTCH1", b"ZORNTCH2"):
        raise ValueError("invalid touch raw metadata")
    kind = struct.unpack_from("<I", block, 800)[0]
    if kind != (1 if block[784:792] == b"ZORNTCH2" else 0):
        raise ValueError("invalid touch payload kind")
    size, expected = struct.unpack_from("<II", block, 792)
    if size != 3120 or expected > 65535:
        raise ValueError("invalid touch raw length/checksum")
    raw = block[960:960 + size]
    value = 0xffff
    for byte in raw:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0x8408 if value & 1 else 0)
    if value != expected:
        raise ValueError("touch raw checksum mismatch")
    if kind == 1 and raw[2944:2952] != b"ZORNCAL1":
        raise ValueError("invalid touch calibration pair")
    return raw


def from_recovery():
    adb = ["adb", "-s", SERIAL]
    serial = subprocess.run(adb + ["get-serialno"], capture_output=True, text=True, check=True)
    if serial.stdout.strip() != SERIAL:
        raise ValueError(f"unexpected adb serial: {serial.stdout.strip()!r}")
    dd = (f"dd if=/dev/block/by-name/userdata bs={BLOCK_SIZE} "
          f"skip={LOG_BLOCK} count=1 2>/dev/null")
    command = adb + ["exec-out", "sh", "-c", dd]
    result = subprocess.run(command, capture_output=True, check=True)
    if len(result.stdout) != BLOCK_SIZE:
        raise ValueError(f"read {len(result.stdout)} bytes, expected {BLOCK_SIZE}: {result.stderr!r}")
    return result.stdout


def _cpu_active_block(block):
    if block[:8] != b"ZORNLOGE":
        return None
    import importlib.util
    path = Path(__file__).with_name("zorn_cpu_active.py")
    spec = importlib.util.spec_from_file_location("zorn_cpu_active_bound", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.decode(block)


def decode(block):
    active = _cpu_active_block(block)
    if active is not None: block = active["original_block"]
    if len(block) != BLOCK_SIZE:
        raise ValueError(f"log block is {len(block)} bytes, expected {BLOCK_SIZE}")
    if block[:8] not in FORMATS:
        raise ValueError(f"bad log magic: {block[:8]!r}")
    capacity, width = FORMATS[block[:8]]
    count = int.from_bytes(block[8:12], "little")
    if count > capacity:
        raise ValueError(f"invalid checkpoint count: {count}")
    ring = block[:8] != b"ZORNLOG1"
    next_slot = int.from_bytes(block[12:16], "little") if ring else 0
    if next_slot >= capacity or (ring and count < capacity and next_slot != count):
        raise ValueError(f"invalid next slot: {next_slot}")
    start = next_slot if ring and count == capacity else 0
    words = []
    for index in range(count):
        slot = (start + index) % capacity
        offset = 16 + width * slot
        raw = block[offset:offset + width].split(b"\0", 1)[0]
        if not raw or any(byte < 32 or byte > 126 for byte in raw):
            raise ValueError(f"invalid checkpoint at {index}: {raw!r}")
        words.append(raw.decode("ascii"))
    return words


def touch_trace(raw):
    """Decode only the coherent v18 trace union, never as a saved thread stack."""
    words = struct.unpack("<108I", raw)
    sequence, magic, total, count, frames, bad, last_ms, gap, zero0, zero1, flags, zero2 = words[:12]
    if magic != 0x3152545a or flags not in (1, 2):
        raise ValueError("invalid touch trace header")
    if flags == 2:
        if any(value for index, value in enumerate(words) if index not in (1, 10)):
            raise ValueError("unavailable touch trace contains data")
        return {"status": "snapshot-unavailable", "records": []}
    if not sequence or sequence & 1 or count != min(total, 32) or bad > frames or gap > last_ms or zero0 or zero1 or zero2:
        raise ValueError("invalid touch trace counters")
    start = total % 32 if total >= 32 else 0
    points = []
    for index in range(count):
        slot = (start + index) % 32
        ms, xy, meta = words[12 + slot * 3:15 + slot * 3]
        x, y = xy & 0xffff, xy >> 16
        identity, phase, contacts, reason = meta & 255, (meta >> 8) & 255, (meta >> 16) & 255, meta >> 24
        if (x > 32767 or y > 32767 or identity >= 20 or phase not in (1, 2, 3) or contacts > 10 or
                reason > 2 or (phase != 3 and (reason or not contacts)) or ms > last_ms or
                (points and ms < points[-1]["ms"])):
            raise ValueError("invalid touch trace point")
        points.append({"sequence": total - count + index + 1, "ms": ms, "id": identity,
                       "phase": ("down", "move", "up")[phase - 1], "contacts": contacts,
                       "x": x, "y": y, "release_reason": ("normal", "invalid-frames", "worker-stop")[reason]})
    if total < 32 and any(words[12 + count * 3:]):
        raise ValueError("unused touch trace slots contain data")
    return {"status": "coherent", "total_records": total, "overwritten_records": total - count,
            "matrix_samples": frames, "bad_samples": bad, "last_ms": last_ms, "max_sample_gap_ms": gap,
            "coordinate_max": 32767, "records": points,
            "scope": "decoded sensor contacts before HID delivery; GUI receipt not implied"}


def gui_state(block):
    cpu_active = _cpu_active_block(block)
    if cpu_active is not None: block = cpu_active["original_block"]
    if len(block) != BLOCK_SIZE or block[:8] not in (b"ZORNLOG3", b"ZORNLOG4", b"ZORNLOG5", b"ZORNLOG6", b"ZORNLOG7", b"ZORNLOG8", b"ZORNLOG9", b"ZORNLOGA", b"ZORNLOGB", b"ZORNLOGD"):
        return None
    offset = {b"ZORNLOG3": 2176, b"ZORNLOG4": 2080, b"ZORNLOG5": 1960, b"ZORNLOG6": 1696, b"ZORNLOG7": 1648, b"ZORNLOG8": 1624, b"ZORNLOG9": 1192, b"ZORNLOGA": 1168, b"ZORNLOGB": 1120, b"ZORNLOGD": 1024}[block[:8]]
    magic, version, size, tick, stage, pid, sequence, ms = struct.unpack_from("<8s6IQ", block, offset)
    allowed = {b"ZORNLOG3": ((1, 1344), (2, 1920)), b"ZORNLOG4": ((3, 2016),),
               b"ZORNLOG5": ((4, 2136),), b"ZORNLOG6": ((5, 2400),), b"ZORNLOG7": ((6, 2448),), b"ZORNLOG8": ((7, 2472),), b"ZORNLOG9": ((8, 2904), (9, 2904), (10, 2904)), b"ZORNLOGA": ((11, 2928), (12, 2928), (13, 2928)), b"ZORNLOGB": ((14, 2976), (15, 2976)), b"ZORNLOGD": ((16, 3072), (17, 3072), (18, 3072), (19, 3072))}[block[:8]]
    maximum_tick = 60 if version >= 12 else 20 if version >= 6 else 12
    if magic != b"ZORNGUI1" or (version, size) not in allowed or tick > maximum_tick or stage > (14 if version >= 8 else 12):
        raise ValueError("invalid GUI snapshot header")
    free, active, inactive, wired = struct.unpack_from("<4I", block, offset + 40)
    ram = struct.unpack_from("<3Q", block, offset + 56)
    display = struct.unpack_from("<32Q", block, offset + 80)
    result = {"tick": tick, "stage": stage, "pid": pid, "sequence": sequence, "ms": ms,
              "pages": {"free": free, "active": active, "inactive": inactive, "wired": wired},
              "ram_data": {"reads": ram[0], "writes": ram[1], "errors": ram[2]},
              "display": list(display), "processes": [], "exits": []}
    if cpu_active is not None:
        result["cpu_active"] = {key: value for key, value in cpu_active.items() if key != "original_block"}
    if version == 19:
        import importlib.util
        spec = importlib.util.spec_from_file_location("zorn_display_progress", Path(__file__).with_name("zorn_display_progress.py"))
        decoder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(decoder)
        result["display"], result["display_progress"] = decoder.decode(display)
    if version >= 3:
        fields = ("dyld_flags", "owner_dyld_flags", "fixups_parsed", "fixups_applied",
                  "hold_seconds", "watchdog_mode", "owner_stage", "owner_mount_flags")
        result["configuration"] = dict(zip(fields, struct.unpack_from("<8Q", block, offset + 1920)))
        paths = ("/usr/lib/libobjc-trampolines.dylib", "/private/preboot/usr/lib/libobjc-trampolines.dylib",
                 "/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64",
                 "/private/preboot/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64")
        result["paths"] = [{"path": path, "errno": error, "vnode_type": kind}
                           for path, (error, kind) in zip(paths, struct.iter_unpack("<2I", block[offset + 1984:offset + 2016]))]
    if version >= 4:
        result["ipc_attempts"] = []
        names = ("launchd", "SpringBoard", "backboardd")
        for index, (seq, pid, message, receiver, bits) in enumerate(struct.iter_unpack("<IiiiI", block[offset + 2016:offset + 2136])):
            if seq:
                if pid <= 0:
                    raise ValueError("invalid GUI IPC sender")
                sender = "lsd" if version >= 13 and index // 2 == 0 and pid != 1 else names[index // 2]
                result["ipc_attempts"].append({"sequence": seq, "name": sender,
                    "pid": pid, "message": message, "receiver_pid": receiver, "bits": bits})
                if version >= 5:
                    pos = offset + 2136 + index * 16
                    result["ipc_attempts"][-1]["receiver_name"] = block[pos:pos + 16].split(b"\0", 1)[0].decode("utf-8", errors="replace")
    if version >= 5:
        result["iokit_queries"] = []
        for index in range(3):
            seq, pid, status, present, provider = struct.unpack_from("<IiiI40s", block, offset + 2232 + index * 56)
            if seq:
                if pid <= 0 or present > 1:
                    raise ValueError("invalid GUI IOKit query")
                sender = "lsd" if version >= 13 and index == 0 and pid != 1 else names[index]
                result["iokit_queries"].append({"sequence": seq, "name": sender, "pid": pid,
                    "status": status, "iterator_present": bool(present),
                    "provider_class": provider.split(b"\0", 1)[0].decode("utf-8", errors="replace")})
    if version >= 6:
        values = struct.unpack_from("<6Q", block, offset + 2400)
        result["keystore"] = dict(zip(("stage", "status", "opens", "calls", "refused"), values[:5]))
        result["keystore"].update(last_selector=values[5] >> 32, last_result=values[5] & 0xffffffff)
    if version >= 7:
        identity, metadata, length = struct.unpack_from("<3Q", block, offset + 2448)
        result["startup_policy"] = {"recorded": identity & 0xffffffff != 0xffffffff,
            "status": identity & 0xffffffff, "uid": identity >> 32,
            "gid": metadata & 0xffffffff, "mode": metadata >> 32, "bytes": length}
    for index in range(3):
        pos = offset + 336 + index * 272
        name, pid, sample_tick, slide, header, count, truncated = struct.unpack_from("<16s2I2Q2I", block, pos)
        if count > 4 or sample_tick > maximum_tick or truncated > 1:
            raise ValueError("invalid GUI process snapshot")
        if not pid:
            continue
        name = name.split(b"\0", 1)[0].decode("ascii")
        expected_name = (("launchd", "lsd") if version >= 11 else ("lsd",) if version >= 9 else ("launchd",), ("SpringBoard",), ("backboardd",))[index]
        if name not in expected_name:
            raise ValueError("unexpected GUI process snapshot")
        process = {"name": name, "pid": pid, "tick": sample_tick, "slide": slide,
                   "main_header": header, "thread_count": count, "truncated": bool(truncated), "threads": []}
        for n in range(count):
            pc, lr, sp, fp, wait, cont, state, reserved = struct.unpack_from("<6Q2I", block, pos + 48 + n * 56)
            if reserved and (version < 10 or reserved > 64):
                raise ValueError("unexpected GUI thread extension")
            process["threads"].append({"index": n, "pc": pc, "lr": lr, "sp": sp, "fp": fp,
                "wait": wait, "continuation": cont, "state": state, "frames": []})
            if version >= 10:
                process["threads"][-1]["original_index"] = reserved - 1 if reserved else n
        result["processes"].append(process)
    if version >= 8:
        result["user_stacks"] = []
        result["kernel_stacks"] = []
        if version in (18, 19):
            result["touch_trace"] = touch_trace(block[offset + 2472:offset + 2904])
        else:
            for index in range(3):
                stack_pid, stack_tick, count, error, *frames = struct.unpack_from("<4I16Q", block, offset + 2472 + index * 144)
                if count > 16 or stack_tick > maximum_tick:
                    raise ValueError("invalid GUI user stack")
                if not stack_pid:
                    if stack_tick or count or error or any(frames):
                        raise ValueError("unrecorded GUI stack contains data")
                    continue
                name = ("lsd" if version >= 9 else "launchd", "SpringBoard", "backboardd")[index]
                if version >= 11 and index == 0:
                    name = block[offset + 336:offset + 352].split(b"\0", 1)[0].decode("ascii")
                    if name not in ("lsd", "launchd"):
                        raise ValueError("user stack lacks its process identity")
                kernel_stack = bool(error & 0x80000000)
                if kernel_stack and version < 15:
                    raise ValueError("kernel stack flag in a legacy user-stack record")
                error &= 0x7fffffff
                result["kernel_stacks" if kernel_stack else "user_stacks"].append({
                    "name": name, "pid": stack_pid, "tick": stack_tick,
                    "count": count, "error": error, "frames": frames[:count]})
                for process in result["processes"]:
                    if process["pid"] == stack_pid and process["name"] == name and process["tick"] == stack_tick and process["threads"]:
                        process["threads"][0]["kernel_frames" if kernel_stack else "frames"] = frames[:count]
                        process["threads"][0]["kernel_stack_read_error" if kernel_stack else "stack_read_error"] = error
    if version >= 11:
        outcome, counts, owner = struct.unpack_from("<3Q", block, offset + 2904)
        stage, error = outcome >> 32, outcome & 0xffffffff
        checked, total = counts & 0xffffffff, counts >> 32
        if stage > 4 or checked > total or total > 512:
            raise ValueError("invalid Data permission metadata")
        # Stage 4 validates the existing retained marker, without replaying the
        # seed's metadata template. Never report its zero checked count as a
        # successful full-template walk, or accept contradictory success fields.
        if stage == 4 and (version < 15 or error or checked or not total or owner):
            raise ValueError("invalid retained Data permission metadata")
        result["data_permissions"] = {"recorded": stage != 0, "stage": stage, "error": error,
            "checked": checked, "total": total, "root_uid": owner & 0xffffffff, "root_gid": owner >> 32}
        if stage == 4:
            result["data_permissions"]["policy"] = "verified-existing-marker; no template replay"
    if version >= 14:
        outcome, block_bytes, blocks, available, uuid0, uuid1 = struct.unpack_from("<6Q", block, offset + 2928)
        error, supported = outcome & 0xffffffff, outcome >> 32
        if supported > 15 or (supported & 1 and (block_bytes == 0 or block_bytes > 1 << 20)):
            raise ValueError("invalid Data space metadata")
        if supported & 6 == 6 and available > blocks:
            raise ValueError("Data available blocks exceed total")
        result["data_space"] = {"recorded": error != 0xffffffff, "error": error, "supported": supported,
            "block_bytes": block_bytes, "blocks": blocks, "available_blocks": available,
            "uuid": str(uuid.UUID(bytes=struct.pack("<2Q", uuid0, uuid1))).upper() if supported & 8 else None}
        if error == 0 and supported & 7 == 7:
            result["data_space"].update(total_bytes=blocks * block_bytes, available_bytes=available * block_bytes)
    if version >= 16:
        values = list(struct.unpack_from("<12Q", block, offset + 2976))
        if version >= 17:
            edges = [value >> 32 for value in values[1:7]]
            if edges[0] > 1 or edges[5] > 3:
                raise ValueError("invalid touch event dispatch metadata")
            result["touch_edges"] = dict(zip(("installed", "dispatches", "digitizer_events",
                "edge_marks", "skipped_events", "install_error"), edges))
            for index in range(1, 7):
                values[index] &= 0xffffffff
        stage, error = values[0] & 0xffffffff, values[0] >> 32
        if stage not in (0, 1, 3, 4, 5, 6, 7, 21, 22, 23, 24) or values[4] > 10 or values[5] > 32767 or values[6] > 32767 or values[10] >> 32 > 1:
            raise ValueError("invalid touch runtime metadata")
        result["touch"] = dict(zip(("reads", "bad", "decoded", "contacts", "x", "y"), values[1:7]))
        result["touch"].update(stage=stage, error=error, peak=values[7] & 0xffffffff,
            noise=values[7] >> 32, irq=values[8], counter_ms=values[9],
            hid_stage=values[10] & 0xffffffff, event_driver=bool(values[10] >> 32),
            reports=values[11] >> 32, last_result=values[11] & 0xffffffff)
        # Aligned individual counters; this is not an atomic frame snapshot.
        result["touch"]["snapshot_policy"] = "independent aligned words; may span adjacent frames"
    for index in range(4):
        seq, pid, status, namespace, code, name = struct.unpack_from("<IiiIQ24s", block, offset + 1152 + index * 48)
        if seq:
            event = {"sequence": seq, "pid": pid, "status": status, "namespace": namespace,
                     "code": code, "name": name.split(b"\0", 1)[0].decode("ascii")}
            if version >= 2:
                pc, lr, far, slide, header, esr, cpsr, fixups, reason = struct.unpack_from("<5Q3I92s", block, offset + 1344 + index * 144)
                event["detail"] = {"pc": pc, "lr": lr, "far": far, "slide": slide, "main_header": header,
                                   "esr": esr, "cpsr": cpsr, "fixups": fixups,
                                   "reason": reason.split(b"\0", 1)[0].decode("utf-8", errors="replace"), "frames": []}
            result["exits"].append(event)
    return result


def image4_events(words):
    labels = {1: "worker enter", 2: "worker return", 3: "service wait",
              4: "service found", 5: "service absent", 6: "start enter",
              7: "start true", 8: "start false", 9: "gate try-close result",
              10: "gate wait", 11: "gate open", 12: "service matching",
              13: "SoftwareAES start enter", 14: "SoftwareAES start true",
              15: "SoftwareAES start false"}
    events = []
    for index, word in enumerate(words):
        if word not in ("I4EARLY", "I4EVENT"):
            continue
        fields = words[index + 1:index + 5]
        if len(fields) != 4 or any(len(field) != 11 or not field.startswith(prefix)
                                   for field, prefix in zip(fields, ("I4K", "I4P", "I4H", "I4L"))):
            continue
        kind, pc, high, low = [int(field[3:], 16) for field in fields]
        name = ""
        start = index + 5
        if words[start:start + 1] == ["I4NBEGIN"] and "I4NEND" in words[start + 1:]:
            end = words.index("I4NEND", start + 1)
            name = "".join(words[start + 1:end])
        events.append({"early": word == "I4EARLY", "kind": kind,
                       "event": labels.get(kind, f"kind {kind}"), "pc_low": pc,
                       "value": (high << 32) | low, "name": name})
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", type=Path, help="decode an existing 4096-byte local dump")
    parser.add_argument("--save", type=Path, help="save the raw block locally after adb read")
    parser.add_argument("--tail", type=int, default=80, help="print this many latest words (default: 80)")
    args = parser.parse_args()
    if args.tail < 1:
        parser.error("--tail must be positive")
    if args.block and args.save:
        parser.error("--save is only for adb reads")
    block = args.block.read_bytes() if args.block else from_recovery()
    if args.save:
        args.save.write_bytes(block)
    words = decode(block)
    raw_touch = touch_raw(block)
    if raw_touch is not None:
        print(f"Touch raw: {len(raw_touch)} bytes; SHA256 {hashlib.sha256(raw_touch).hexdigest()}")
        if args.save:
            raw_path = args.save.with_suffix(".touch.bin")
            raw_path.write_bytes(raw_touch)
            print(f"Saved complete touch frame: {raw_path}")
    gui = gui_state(block)
    if gui is not None:
        print("GUI snapshot: " + json.dumps(gui, separators=(",", ":")))
    print(f"{len(words)} checkpoints; showing last {min(len(words), args.tail)}")
    for index, word in enumerate(words[max(0, len(words) - args.tail):],
                                  start=max(0, len(words) - args.tail)):
        print(f"{index:03d} {word}")
    if "PANICBEGIN" in words:
        begin = len(words) - 1 - words[::-1].index("PANICBEGIN")
        if "PANICEND" in words[begin + 1:]:
            end = words.index("PANICEND", begin + 1)
            print("panic: " + "".join(words[begin + 1:end]))
    output = []
    partial = None
    for word in words:
        if word == "USRBEGIN":
            partial = []
        elif word == "USREND":
            if partial is not None:
                output.append("".join(partial))
            partial = None
        elif partial is not None:
            partial.append(word)
    if output:
        print("user output: " + "".join(output))
    mount_text = None
    for word in words:
        if word == "APBEGIN":
            mount_text = []
        elif word == "APEND":
            if mount_text is not None:
                print("mount printf: " + "".join(mount_text))
            mount_text = None
        elif mount_text is not None:
            mount_text.append(word)
    hash_name = None
    for word in words:
        if word == "HFBEGIN":
            hash_name = []
        elif word == "HFEND":
            if hash_name is not None:
                print("authenticated-file progress: " + "".join(hash_name))
            hash_name = None
        elif hash_name is not None:
            hash_name.append(word)
    names = []
    partial = None
    for word in words:
        if word == "SCTBEGIN":
            partial = []
        elif word == "SCTEND":
            if partial is not None:
                name = "".join(partial)
                if not names or names[-1] != name:
                    names.append(name)
            partial = None
        elif partial is not None:
            partial.append(word)
    if names:
        print("sysctl names: " + " | ".join(names))
    for event in image4_events(words):
        when = "before UFS" if event["early"] else "live"
        print(f"Image4 {when}: {event['event']}; pc_low={event['pc_low']:#010x}; "
              f"value={event['value']:#x}" + (f"; {event['name']}" if event["name"] else ""))


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        sys.exit(str(error))
