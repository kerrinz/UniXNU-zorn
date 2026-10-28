#!/usr/bin/env python3
"""Resolve bounded GUI samples against the exact kernel and original cache.

Requires a recovered run with a changed log and matching build identity.
Only reads local inputs. Cache offsets come from the pinned Apple header.
"""
import argparse
import bisect
import hashlib
import importlib.util
import json
import mmap
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def messages(path):
    spec = importlib.util.spec_from_file_location("zorn_log", Path(__file__).with_name("read-zorn-log.py"))
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    words = reader.decode(path.read_bytes())
    current = None
    result = []
    for word in words:
        if word == "USRBEGIN":
            current = []
        elif word == "USREND":
            if current is not None:
                result.append("".join(current))
            current = None
        elif current is not None:
            current.append(word)
    return result


def kernel_symbols(path, addresses):
    best = {value: None for value in addresses if value}
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as b:
        if struct.unpack_from("<I", b)[0] != 0xfeedfacf:
            raise ValueError("Kernel is not a Mach-O 64 file")
        position = 32
        symtab = None
        for _ in range(struct.unpack_from("<I", b, 16)[0]):
            command, size = struct.unpack_from("<II", b, position)
            if size < 8 or position + size > len(b):
                raise ValueError("Invalid kernel load command")
            if command == 2:
                symtab = struct.unpack_from("<4I", b, position + 8)
            position += size
        if symtab is None:
            return {}
        offset, count, strings, string_size = symtab
        if offset + count * 16 > len(b) or strings + string_size > len(b):
            raise ValueError("Kernel symbol table exceeds file")
        for i in range(count):
            string, kind, section, _, value = struct.unpack_from("<IBBHQ", b, offset + i * 16)
            if kind & 0xe0 or kind & 0xe != 0xe or not section or string >= string_size:
                continue
            for address, previous in best.items():
                if value <= address and (previous is None or value > previous[0]):
                    best[address] = (value, string)
        result = {}
        for address, entry in best.items():
            if entry is None or address - entry[0] > 0x10000:
                continue
            pos = strings + entry[1]
            end = b.find(b"\0", pos, strings + string_size)
            if end >= 0:
                result[hex(address)] = {"nearest_symbol": b[pos:end].decode(errors="replace"),
                                        "offset": address - entry[0]}
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--symbols-dir", type=Path, default=ROOT / "out/zorn/gui-symbols")
    parser.add_argument("--export-supplement", type=Path,
                        help="readonly original cache exports with matching OS/volume/main-cache identity")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run = json.loads((args.run / "run.json").read_text())
    build = json.loads((args.run / "build-inputs.json").read_text())
    if run.get("status") != "recovered" or run.get("kernel_log_changed") is not True:
        raise ValueError("Require a recovered run with a changed kernel log")
    if run["sha256"] != build["sha256"] or build.get("status") != "ready":
        raise ValueError("Run/build identity mismatch")
    expected = [v for k, v in build["inputs"].items() if k.endswith("/kernel/kernel.macho")]
    if expected != [digest(args.kernel)]:
        raise ValueError("Kernel does not match this run")

    samples = {}
    exits = []
    snapshot = None
    spec = importlib.util.spec_from_file_location("zorn_gui_reader", Path(__file__).with_name("read-zorn-log.py"))
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    snapshot = reader.gui_state((args.run / "checkpoints.bin").read_bytes())
    for text in messages(args.run / "checkpoints.bin"):
        h = re.search(r"GUI (\w+)\[(\d+)\] slide=([0-9a-f]+) mh=([0-9a-f]+) threads=(\d+) truncated=(\d+)", text)
        if h:
            samples[h[1]] = {"name": h[1], "pid": int(h[2]), "slide": int(h[3], 16),
                            "main_header": int(h[4], 16), "thread_count": int(h[5]),
                            "truncated": bool(int(h[6])), "threads": []}
        t = re.search(r"GUI (\w+) t(\d+) pc=([0-9a-f]+) lr=([0-9a-f]+) sp=([0-9a-f]+) state=([0-9a-f]+) wait=([0-9a-f]+) cont=([0-9a-f]+) bt=([0-9a-f]+),([0-9a-f]+)", text)
        if t and t[1] in samples:
            samples[t[1]]["threads"].append({"index": int(t[2]), "pc": int(t[3], 16),
                "lr": int(t[4], 16), "sp": int(t[5], 16), "state": int(t[6], 16),
                "wait": int(t[7], 16), "continuation": int(t[8], 16),
                "frames": [int(t[9], 16), int(t[10], 16)]})
        if "GUI EXIT" in text:
            exits.append(text.strip())
    if snapshot is not None:
        samples = {p["name"]: p for p in snapshot["processes"]}
        exits = snapshot["exits"]

    proof = json.loads((args.symbols_dir / "inputs.json").read_text())
    for name, sha in proof["sha256"].items():
        if digest(args.symbols_dir / name) != sha:
            raise ValueError("Original cache/symbol input changed")
    supplement = None
    exported = {}
    if args.export_supplement:
        supplement = json.loads(args.export_supplement.read_text())
        if (supplement.get("os") != proof["os"] or
                supplement.get("source_volume_uuid") != proof["source_volume_uuid"] or
                supplement.get("main_cache_sha256") != proof["sha256"]["dyld_shared_cache_arm64"] or
                supplement.get("source_readonly") is not True or
                supplement.get("original_inputs_modified") is not False):
            raise ValueError("Export supplement does not match original cache identity")
        for name, entries in supplement["images"].items():
            exported[name] = sorted((int(row["address"], 16), row["name"]) for row in entries)
    offsets = proof["offsets"]
    main_cache = (args.symbols_dir / "dyld_shared_cache_arm64").read_bytes()
    region, region_size, max_slide = struct.unpack_from("<3Q", main_cache, offsets["sharedRegionStart"])
    image_offset, image_count = struct.unpack_from("<2Q", main_cache, offsets["imagesTextOffset"])
    images = []
    for i in range(image_count):
        _, va, size, name = struct.unpack_from("<16sQ2I", main_cache, image_offset + i * 32)
        end = main_cache.find(b"\0", name)
        if end < name:
            raise ValueError("Invalid original image path")
        images.append((va, va + size, main_cache[name:end].decode()))
    images.sort()
    starts = [image[0] for image in images]
    with (args.symbols_dir / "dyld_shared_cache_arm64.symbols").open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as symbols:
        if symbols[offsets["uuid"]:offsets["uuid"] + 16] != main_cache[offsets["symbolFileUUID"]:offsets["symbolFileUUID"] + 16]:
            raise ValueError("Original symbols UUID mismatch")
        base = struct.unpack_from("<Q", symbols, offsets["localSymbolsOffset"])[0]
        no, nc, so, ss, eo, ec = struct.unpack_from("<6I", symbols, base)
        if base + no + nc * 16 > len(symbols) or base + so + ss > len(symbols) or base + eo + ec * 16 > len(symbols):
            raise ValueError("Local symbol tables exceed file")
        entries = {}
        for i in range(ec):
            address, start, count = struct.unpack_from("<Q2I", symbols, base + eo + i * 16)
            if start + count > nc:
                raise ValueError("Invalid local symbol entry")
            entries[address] = (start, count)
        local_cache = {}
        contexts = [(sample, sample["threads"]) for sample in samples.values()]
        contexts += [(event["detail"], [event["detail"]]) for event in exits
                     if isinstance(event, dict) and "detail" in event]
        for context, threads in contexts:
            slide = context["slide"]
            if slide > max_slide or slide % 4096:
                raise ValueError("Observed cache slide exceeds original bounds")
            for thread in threads:
                thread["resolved"] = []
                for address in [thread["pc"], thread["lr"], *thread["frames"]]:
                    va = address - slide
                    if not region <= va < region + region_size:
                        continue
                    index = bisect.bisect_right(starts, va) - 1
                    if index < 0 or va >= images[index][1]:
                        continue
                    start, _, name = images[index]
                    row = {"address": hex(address), "unslid": hex(va), "image": name}
                    if start not in local_cache:
                        pairs = []
                        first, count = entries.get(start - region, (0, 0))
                        for i in range(first, first + count):
                            string, kind, section, _, value = struct.unpack_from("<IBBHQ", symbols, base + no + i * 16)
                            if not kind & 0xe0 and kind & 0xe == 0xe and section and start <= value < images[index][1] and string < ss:
                                pairs.append((value, string))
                        pairs.sort()
                        local_cache[start] = pairs
                    pairs = local_cache[start]
                    pos = bisect.bisect_right(pairs, (va, 0xffffffff)) - 1
                    if pos >= 0:
                        value, string = pairs[pos]
                        begin = base + so + string
                        end = symbols.find(b"\0", begin, base + so + ss)
                        if end >= begin:
                            row.update(nearest_local_symbol=symbols[begin:end].decode(errors="replace"), offset=va - value)
                    exported_pairs = exported.get(name, [])
                    export_index = bisect.bisect_right(exported_pairs, (va, chr(0x10ffff))) - 1
                    if export_index >= 0:
                        value, symbol = exported_pairs[export_index]
                        if start <= value < images[index][1] and ("offset" not in row or va - value <= row["offset"]):
                            row.pop("nearest_local_symbol", None)
                            row.update(nearest_export_symbol=symbol, offset=va - value)
                    thread["resolved"].append(row)

    continuations = {t["continuation"] for s in samples.values() for t in s["threads"]}
    kernel_frames = {frame for stack in (snapshot or {}).get("kernel_stacks", []) for frame in stack["frames"]}
    resolved_kernel = kernel_symbols(args.kernel, continuations | kernel_frames)
    for sample in samples.values():
        for thread in sample["threads"]:
            if "kernel_frames" in thread:
                thread["resolved_kernel"] = [{"address": hex(frame), **resolved_kernel.get(hex(frame), {})}
                                             for frame in thread["kernel_frames"]]
    result = {"run": args.run.name, "boot_sha256": run["sha256"], "kernel_sha256": expected[0],
              "samples": samples, "exits": exits, "snapshot": snapshot,
              "kernel_continuations": {hex(value): resolved_kernel[hex(value)] for value in continuations if hex(value) in resolved_kernel},
              "kernel_stack_symbols": {hex(value): resolved_kernel[hex(value)] for value in kernel_frames if hex(value) in resolved_kernel},
              "symbols_uuid_matches": True, "original_inputs_modified": False,
              "desktop_qualified": False}
    if supplement is not None:
        result["export_supplement"] = {"sha256": digest(args.export_supplement),
            "original_cache_identity_matches": True, "images": list(exported)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
