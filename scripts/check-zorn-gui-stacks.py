#!/usr/bin/env python3
"""Check frame pointer boundaries, the actual C log layout and decoder controls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "UniXNU-zorn/native/ufs-read/ZornGuiLog.h"
spec = importlib.util.spec_from_file_location("zorn_reader", Path(__file__).with_name("read-zorn-log.py"))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
program = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ZornGuiLog.h"
int main(void) {
    assert(ZORN_GUI_LOG_OFFSET == 1120);
    assert(ZORN_GUI_LOG_OFFSET + sizeof(struct ZornGuiFooter) == 4096);
    assert(offsetof(struct ZornGuiFooter, stacks) == 2472);
    assert(zorn_gui_kernel_frame_valid(0x1000, 0x4000, 0x1000));
    assert(zorn_gui_kernel_frame_valid(0x1000, 0x4000, 0x4ff0));
    assert(!zorn_gui_kernel_frame_valid(0x1000, 0x4000, 0xff0));
    assert(!zorn_gui_kernel_frame_valid(0x1000, 0x4000, 0x5000));
    assert(!zorn_gui_kernel_frame_valid(0x1000, 0x4000, 0x1018));
    assert(!zorn_gui_kernel_frame_valid(0xfffffffffffffff0ULL, 32, 0));
    assert(!zorn_gui_kernel_frame_valid(0xfffffffffffffff0ULL, 32, 0xfffffffffffffff0ULL));
    assert(zorn_gui_stack_frame_valid(0x1000, 0x1010, 0x1000, 0x2000));
    assert(zorn_gui_stack_frame_valid(0x1000, 0x1ff0, 0x1000, 0x2000));
    assert(!zorn_gui_stack_frame_valid(0xff0, 0x1000, 0x1000, 0x2000));
    assert(!zorn_gui_stack_frame_valid(0x1000, 0xff0, 0x1000, 0x2000));
    assert(!zorn_gui_stack_frame_valid(0x1000, 0x1018, 0x1000, 0x2000));
    assert(!zorn_gui_stack_frame_valid(0x1000, 0x2000, 0x1000, 0x2000));
    assert(!zorn_gui_stack_frame_valid(0x1000, 0x101000, 0, 0x200000));
    assert(!zorn_gui_stack_frame_valid(0xfffffffffffffff0ULL, 0, 0, -1ULL));
    assert(!zorn_gui_stack_frame_valid(0, 0, 0, 15));
    unsigned char block[4096] = {0};
    memcpy(block, "ZORNLOGB", 8);
    struct ZornGuiFooter *p = (void *)(block + ZORN_GUI_LOG_OFFSET);
    memcpy(p->magic, "ZORNGUI1", 8);
    p->version = 14; p->bytes = sizeof(*p); p->tick = 20; p->stage = 14;
    p->dataPermissions[0] = 3ULL << 32;
    p->dataPermissions[1] = (232ULL << 32) | 232;
    p->dataSpace[0] = 15ULL << 32; p->dataSpace[1] = 4096;
    p->dataSpace[2] = 131072; p->dataSpace[3] = 65536;
    const unsigned char uuid[16] = {0xc7,0xd7,0x7f,0xf3,0x64,0x37,0x4c,0x4a,0x8e,0x05,0xe8,0xe2,0x39,0xac,0x16,0x41};
    memcpy(&p->dataSpace[4], uuid, 16);
    memcpy(p->processes[1].name, "SpringBoard", 12);
    p->processes[1].pid = 5; p->processes[1].tick = 20; p->processes[1].count = 1;
    p->processes[1].threads[0].fp = 0x1010;
    p->stacks[1].pid = 5; p->stacks[1].tick = 20; p->stacks[1].count = 2;
    p->stacks[1].frames[0] = 0x180001234ULL; p->stacks[1].frames[1] = 0x180005678ULL;
    p->stacks[1].error = 1;
    assert(fwrite(block, 1, sizeof(block), stdout) == sizeof(block));
}
'''
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    (temp / "check.c").write_text(program)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(HEADER.parent),
                    str(temp / "check.c"), "-o", str(temp / "check")], check=True)
    block = subprocess.check_output([str(temp / "check")])
data_state = reader.gui_state(block)["data_space"]
kernel_sample = bytearray(block)
struct.pack_into("<I", kernel_sample, 1120 + 8, 15)
struct.pack_into("<I", kernel_sample, 1120 + 2472 + 144 + 12, 0x80000001)
struct.pack_into("<2Q", kernel_sample, 1120 + 2472 + 144 + 16, 0xfffffff007001234, 0xfffffff007005678)
decoded_kernel = reader.gui_state(bytes(kernel_sample))
assert decoded_kernel["user_stacks"] == []
assert decoded_kernel["kernel_stacks"][0]["error"] == 1
assert decoded_kernel["processes"][0]["threads"][0]["frames"] == []
assert decoded_kernel["processes"][0]["threads"][0]["kernel_frames"] == [0xfffffff007001234, 0xfffffff007005678]
struct.pack_into("<I", kernel_sample, 1120 + 2472 + 144 + 4, 19)
assert "kernel_frames" not in reader.gui_state(bytes(kernel_sample))["processes"][0]["threads"][0]
struct.pack_into("<I", kernel_sample, 1120 + 8, 14)
try:
    reader.gui_state(bytes(kernel_sample))
except ValueError:
    pass
else:
    raise AssertionError("kernel frames accepted as legacy user frames")
assert data_state["error"] == 0 and data_state["supported"] == 15
assert data_state["total_bytes"] == 512 * 1024**2
assert data_state["available_bytes"] == 256 * 1024**2
assert data_state["uuid"] == "C7D77FF3-6437-4C4A-8E05-E8E239AC1641"
space_rejected = 0
for relative, value in ((2928, 16 << 32), (2936, 0), (2952, 131073)):
    bad = bytearray(block)
    struct.pack_into("<Q", bad, 1120 + relative, value)
    try:
        reader.gui_state(bytes(bad))
    except ValueError:
        space_rejected += 1
    else:
        raise AssertionError("invalid Data filesystem metadata accepted")
# Continue historical controls with the unchanged v11 prefix at its old offset.
previous = bytearray(4096)
previous[:8] = b"ZORNLOGA"
previous[1168:] = block[1120:1120 + 2928]
struct.pack_into("<2I", previous, 1168 + 8, 11, 2928)
current_block = bytes(previous)
state = reader.gui_state(current_block)
service_events = bytearray(current_block)
struct.pack_into("<I", service_events, 1168 + 8, 13)
struct.pack_into("<IiiiI", service_events, 1168 + 2016, 9, 70, 100, 1, 17)
struct.pack_into("<IiiI40s", service_events, 1168 + 2232, 7, 70, 0, 1, b"IONetworkController")
decoded_events = reader.gui_state(bytes(service_events))
assert decoded_events["ipc_attempts"][0]["name"] == "lsd"
assert decoded_events["iokit_queries"][0]["name"] == "lsd"
struct.pack_into("<i", service_events, 1168 + 2016 + 4, 1)
struct.pack_into("<i", service_events, 1168 + 2232 + 4, 1)
decoded_events = reader.gui_state(bytes(service_events))
assert decoded_events["ipc_attempts"][0]["name"] == "launchd"
assert decoded_events["iokit_queries"][0]["name"] == "launchd"
extended = bytearray(current_block)
struct.pack_into("<I", extended, 1168 + 8, 12)
struct.pack_into("<I", extended, 1168 + 16, 60)
assert reader.gui_state(bytes(extended))["tick"] == 60
struct.pack_into("<I", extended, 1168 + 16, 61)
try:
    reader.gui_state(bytes(extended))
except ValueError:
    pass
else:
    raise AssertionError("unbounded GUI observation accepted")
assert state["data_permissions"] == {"recorded": True, "stage": 3, "error": 0,
    "checked": 232, "total": 232, "root_uid": 0, "root_gid": 0}
for relative, value in ((2904, 4 << 32), (2912, (232 << 32) | 233)):
    bad = bytearray(current_block)
    struct.pack_into("<Q", bad, 1168 + relative, value)
    try:
        reader.gui_state(bytes(bad))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid Data permission result accepted")
# Preserve regression coverage of the previous LOG9/v8-v10 wire formats.
legacy = bytearray(4096)
legacy[:8] = b"ZORNLOG9"
legacy[1192:] = current_block[1168:1168 + 2904]
struct.pack_into("<2I", legacy, 1192 + 8, 8, 2904)
block = bytes(legacy)
state = reader.gui_state(block)
assert reader.decode(block) == []
assert state["processes"][0]["threads"][0]["frames"] == [0x180001234, 0x180005678]
assert state["user_stacks"][0]["error"] == 1
rejected = 0
for offset, value in ((1192 + 8, 7), (1192 + 12, 2903), (1192 + 2472 + 144 + 8, 17),
                      (1192 + 2472 + 144 + 4, 21)):
    bad = bytearray(block)
    struct.pack_into("<I", bad, offset, value)
    try:
        reader.gui_state(bytes(bad))
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("invalid stack metadata accepted")
# A previous sample must not be presented as the current thread's backtrace.
stale = bytearray(block)
struct.pack_into("<I", stale, 1192 + 2472 + 144 + 4, 19)
assert reader.gui_state(bytes(stale))["processes"][0]["threads"][0]["frames"] == []
# Version 9 explicitly replaces the launchd slot with LaunchServices.
service = bytearray(block)
struct.pack_into("<I", service, 1192 + 8, 9)
struct.pack_into("<16s2I2Q2I", service, 1192 + 336, b"lsd", 88, 20, 0, 0, 1, 0)
struct.pack_into("<4I16Q", service, 1192 + 2472, 88, 20, 1, 0, 0x180009abc, *([0] * 15))
parsed_service = reader.gui_state(bytes(service))
assert parsed_service["processes"][0]["name"] == "lsd"
assert parsed_service["processes"][0]["threads"][0]["frames"] == [0x180009abc]
assert parsed_service["user_stacks"][0]["name"] == "lsd"
# Footer v10 records the original thread ordinal for a selected lsd window.
worker = bytearray(service)
struct.pack_into("<I", worker, 1192 + 8, 10)
struct.pack_into("<I", worker, 1192 + 336 + 48 + 52, 4)
assert reader.gui_state(bytes(worker))["processes"][0]["threads"][0]["original_index"] == 3
for version, ordinal in ((9, 4), (10, 65)):
    bad = bytearray(worker)
    struct.pack_into("<I", bad, 1192 + 8, version)
    struct.pack_into("<I", bad, 1192 + 336 + 48 + 52, ordinal)
    try:
        reader.gui_state(bytes(bad))
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("invalid thread extension accepted")
historical = 0
for path in (ROOT / "out/zorn/debug").glob("*/checkpoints.bin"):
    raw = path.read_bytes()
    reader.decode(raw)
    reader.gui_state(raw)
    historical += 1
result = {"c_layout_and_pointer_bounds": "pass", "c_to_python_roundtrip": "pass",
          "invalid_metadata_rejected": rejected, "stale_stack_not_attached": True,
          "launchservices_slot_roundtrip": True,
          "selected_worker_ordinal_roundtrip": True,
          "launchservices_ipc_iokit_names_roundtrip": True,
          "long_observation_tick_bounds": True,
          "data_permissions_roundtrip_and_refusal": True,
          "data_filesystem_space_uuid_roundtrip": True,
          "kernel_stack_kind_stale_and_bounds_controls": True,
          "invalid_data_space_rejected": space_rejected,
          "historical_logs_decoded": historical, "header_sha256": hashlib.sha256(HEADER.read_bytes()).hexdigest(),
          "hardware_stack_reads_qualified": False}
out = ROOT / "out/zorn/gui-stack-checks.json"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
