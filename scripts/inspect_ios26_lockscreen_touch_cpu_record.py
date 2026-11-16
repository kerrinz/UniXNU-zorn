"""Decode a CPU availability sample and FT3683 snapshot from a local page."""
import re
import struct
import zlib

MILESTONE = re.compile(
    r"K80 FT3683: schedule=(?P<schedule>[0-9a-f]{8}) f=(?P<flags>[0-9a-f]+) "
    r"res=(?P<resources>[0-9a-f]{8}) platformThread=(?P<platform_thread>[0-9a-f]{8}) "
    r"board=(?P<board_phase>[0-9]+)/(?P<board_create>[0-9a-f]{8}) "
    r"cap=(?P<capture_raw>[0-3])/(?P<capture_reads>[0-9]+) "
    r"prep=(?P<prep>[0-9a-f]+) id=(?P<identity_count>[0-3])/(?P<identity>[0-9a-f]{6}) "
    r"host=(?P<host_phase>[0-9]+) worker=(?P<worker_phase>[0-9]+)/(?P<worker_end>[0-9]+)/"
    r"(?P<worker_thread>[0-9a-f]{8}) baseline=(?P<accepted>[0-9]+)/(?P<attempts>[0-9]+) "
    r"frames=(?P<frames>[0-9]+) last=(?P<outcome>[0-9]+)/(?P<detail>[0-9a-f]{8}) "
    r"release=(?P<release>[0-9a-f]{8}); PID1 EL0"
)
FLAGS = (
    "resources_returned", "provider_opened", "platform_thread_returned",
    "platform_thread_handle", "board_create_returned", "capture_returned",
    "preparation_returned", "host_status_valid", "hid_started",
    "register_call_returned", "worker_thread_returned", "worker_entered",
    "producer_finished", "last_source_valid", "contact_release_returned",
)



def inspect_envelope(page, tag, before):
    if len(page) != 4096 or len(before) != 4096 or len(tag) != 16:
        raise ValueError("expected two 4 KiB pages and an exact artifact ID")
    if page == before or before.startswith(b"HJPAN026" + tag):
        raise ValueError("stale artifact record")
    magic, run_id, length, crc, text = struct.unpack("<8s16sII512s", page[:544])
    if magic != b"HJPAN026" or run_id != tag:
        raise ValueError("record identity differs")
    if not 0 < length < 512 or text[length] or any(page[544:]):
        raise ValueError("record envelope differs")
    raw = bytearray(page[:544])
    raw[28:32] = bytes(4)
    if zlib.crc32(raw) != crc:
        raise ValueError("record CRC differs")
    return dict(run_id=run_id.hex(), text=text[:length].decode("ascii"),
                freshness="before and after differ; tag absent before")

def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    match = re.fullmatch(r"cpu_online=([0-8]); (.*)", envelope["text"])
    if not match:
        raise ValueError("missing K80 CPU availability sample")
    online = int(match[1])
    text = match[2]
    result = {
        "status": "FT3683 archived snapshot",
        "run_id": envelope["run_id"], "freshness": envelope["freshness"],
        "pid1_el0_in_record": True, "cpu_online": online, "touch_input_delivery_proven": False,
        "device_execution_proven_by_local_decode": False,
    }
    if text == "K80 FT3683: schedule did not return by sample; PID1 EL0":
        return dict(result, schedule_returned=False)
    early = re.fullmatch(r"K80 FT3683: schedule=([0-9a-f]{8}) owner=0; PID1 EL0", text)
    if early:
        return dict(result, schedule_returned=True, schedule_raw=int(early[1], 16), owner_present=False)
    match = MILESTONE.fullmatch(text)
    if not match:
        raise ValueError("current record does not contain the FT3683 snapshot")

    def decimal(name):
        return int(match[name])

    def raw(name):
        return int(match[name], 16)

    flags = raw("flags")
    accepted, attempts, frames, outcome = (decimal(k) for k in ("accepted", "attempts", "frames", "outcome"))
    if (flags >> len(FLAGS) or accepted > min(attempts, 8) or attempts > 12
            or frames > 64 or outcome > 7):
        raise ValueError("FT3683 snapshot fields exceed the selected source bounds")
    observed = {flag: bool(flags & (1 << i)) for i, flag in enumerate(FLAGS)}
    capture_raw = decimal("capture_raw")
    capture_reads = decimal("capture_reads")
    if capture_reads > 32:
        raise ValueError("FT3683 capture read count exceeds the retained inventory")
    result.update(
        capture_raw=capture_raw if observed["capture_returned"] else None,
        capture_reads=capture_reads if observed["capture_returned"] else None,
        schedule_returned=True, schedule_raw=raw("schedule"), owner_present=True,
        observed=observed, board_phase=decimal("board_phase"),
        host_phase=decimal("host_phase") if observed["host_status_valid"] else None,
        resource_raw=raw("resources") if observed["resources_returned"] else None,
        platform_thread_raw=raw("platform_thread") if observed["platform_thread_returned"] else None,
        board_create_raw=raw("board_create") if observed["board_create_returned"] else None,
        preparation_raw=raw("prep") if observed["preparation_returned"] else None,
        returned_identity=list(bytes.fromhex(match["identity"])[:decimal("identity_count")]),
        baseline_accepted=accepted, baseline_attempts=attempts, frame_read_calls_returned=frames,
        worker_phase=decimal("worker_phase"), worker_end=decimal("worker_end"),
        worker_thread_raw=raw("worker_thread") if observed["worker_thread_returned"] else None,
        last_source_outcome=outcome if observed["last_source_valid"] else None,
        last_transport_raw=raw("detail") if observed["last_source_valid"] and outcome == 5 else None,
        last_submit_raw=raw("detail") if observed["last_source_valid"] and outcome == 7 else None,
        contact_release_raw=raw("release") if observed["contact_release_returned"] else None,
    )
    return result
