"""Decode the shared CPU, FT3683 and guarded GPU context-read checkpoint."""

import re

from inspect_ios26_lockscreen_percore_record import PREFIX, inspect_status
from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope

RESULT = re.compile(r"([01])/([0-9a-f]{8}),([01])/([0-9a-f]{8}),([01])/([0-2])/([0-3])/([0-9a-f]{16}),([01])/([0-9a-f]{8})")


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    body, marker, gpu = envelope["text"].rpartition("; gpu=")
    if not marker:
        raise ValueError("missing guarded GPU checkpoint")
    match = PREFIX.fullmatch(body)
    if not match:
        raise ValueError("missing CPU and FT3683 checkpoint")
    valid = int(match[2], 16)
    pairs = [tuple(int(value, 16) for value in pair.split("/")) for pair in match[3].split(",")]
    active = [cpu for cpu, pair in enumerate(pairs) if any(pair)]
    if any(not valid & (1 << cpu) for cpu in active):
        raise ValueError("CPU accounting delta without a valid sample pair")
    record = inspect_status(envelope, int(match[1]), match[4])
    record.update(valid_cpu_mask=valid, active_cpu_ids=active, user_system_tick_deltas=pairs,
                  all_eight_executed_work=valid == 255 and len(active) == 8)
    if gpu in ("alloc", "pending"):
        return dict(record, gpu_snapshot=gpu, context_reads_complete=False, endpoint_reservation_complete=False)
    result = RESULT.fullmatch(gpu)
    if not result:
        raise ValueError("invalid GPU checkpoint")
    maps = int(result[2], 16) if result[1] == "1" else None
    probe = int(result[4], 16) if result[3] == "1" else None
    returned = result[5] == "1"
    disposition = int(result[6]) if returned else None
    if returned and (maps != 0 or probe != 0):
        raise ValueError("endpoint reservation without successful mapping and probe")
    context = int(result[10], 16) if result[9] == "1" else None
    if context is not None and (not returned or disposition != 0):
        raise ValueError("context read without completed endpoint reservation")
    return dict(record, context_probe_raw=context, context_reads_complete=context == 0,
                gpu_snapshot="returned", guarded_mapping_raw=maps, guarded_probe_raw=probe,
                endpoint_reservation_disposition=disposition,
                endpoint_status_domain=int(result[7]) if returned else None,
                endpoint_raw_status=int(result[8], 16) if returned else None,
                endpoint_reservation_complete=returned and disposition == 0)
