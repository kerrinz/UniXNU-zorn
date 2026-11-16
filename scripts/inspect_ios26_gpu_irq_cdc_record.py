"""Decode the shared CPU, FT3683 and guarded GPU CX timer checkpoint."""

import re

from inspect_ios26_lockscreen_percore_record import PREFIX, inspect_status
from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope

RESULT = re.compile(r"([01])/([0-9a-f]{1,8}),([01])/([0-9a-f]{1,8}),([01])/([0-2])/([0-3])/([0-9a-f]{1,16}),([01])/([0-9a-f]{1,8}),([01])/([0-9a-f]{1,8})/([01])/([0-9a-f]{1,8}),([01])/([0-9a-f]{1,8}),([01])/([0-9a-f]{1,8})/([0-9]+)/([0-9a-f]+)")


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    body, marker, gpu = envelope["text"].rpartition("; gpu=")
    if not marker:
        raise ValueError("missing guarded GPU checkpoint")
    head, tail = body.split("; ", 3)[:3], body.split("; ", 3)[-1]
    if tail.startswith("schedule="):
        tail = "K80 FT3683: " + tail
    match = PREFIX.fullmatch("; ".join([*head, "mode=continuous", tail]))
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
        return dict(record, gpu_snapshot=gpu, gmu_clock_complete=False, context_reads_complete=False, endpoint_reservation_complete=False)
    gpu, separator, fw = gpu.partition(",f=")
    firmware = None
    if separator:
        values = re.fullmatch(r"([0-9]+)/([0-9a-f]{1,8})/([0-9a-f]{1,8})/([01])", fw)
        if not values:
            raise ValueError("invalid CPU firmware preparation record")
        page, graph, code, zero = values.groups()
        firmware = dict(cpu_page_bytes=int(page), graph_status=int(graph, 16),
                        prepare_code=int(code, 16), zero_prepared=zero == "1")
    gpu, separator, tables = gpu.partition(",t=")
    stages = None
    if separator:
        fields = re.fullmatch(r"(0|1|3|7|15|31)(?:/([0-9a-f]{1,8}))/([0-9a-f]{1,8})/([0-9a-f]{1,8})/([0-9a-f]{1,8})/([0-9a-f]{1,8})", tables)
        if not fields:
            raise ValueError("invalid inactive GMU context record")
        mask = int(fields[1])
        statuses = [int(value, 16) for value in fields.groups()[1:]]
        if any(value and not (mask & (1 << i)) for i, value in enumerate(statuses)):
            raise ValueError("status for an uncalled inactive context stage")
        if any(statuses[i - 1] for i in range(1, 5) if mask & (1 << i)):
            raise ValueError("inactive context stages out of order")
        stages = dict(zip(("root_pages", "sparse_arenas", "gmu_image", "firmware_seed", "firmware_holds"),
                          (value if mask & (1 << i) else None for i, value in enumerate(statuses))))
    gpu, separator, irq = gpu.partition(",i=")
    if not separator or not (fields := re.fullmatch(r"([0-9a-f])/([0-9a-f]{1,8})/([0-9]{1,4})", irq)):
        raise ValueError("missing or invalid global IRQ record")
    flags, status = (int(value, 16) for value in fields.groups()[:2])
    intid = int(fields[3])
    if ((not flags & 1 and (flags or status or intid))
            or (flags & 4 and not flags & 2)
            or (flags & 8 and (flags != 15 or not 32 <= intid <= 1019))
            or (not flags & 8 and intid)
            or (flags & 1 and (not stages or stages["firmware_holds"] != 0))
            or (flags & 1 and status == 0 and flags != 15)):
        raise ValueError("inconsistent global IRQ state")
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
    clock = int(result[12], 16) if result[11] == "1" else None
    if clock is not None and context != 0:
        raise ValueError("GMU clocks without a completed context read")
    source = int(result[14], 16) if clock is not None and result[13] == "1" else None
    if clock == 0 and source != 0:
        raise ValueError("GMU clock success without the source return")
    ahb = int(result[16], 16) if result[15] == "1" else None
    timer = int(result[18], 16) if result[17] == "1" else None
    if (ahb is not None and clock != 0) or (timer is not None and ahb != 0):
        raise ValueError("CX timer record violates startup ordering")
    if stages and stages["root_pages"] is not None and timer != 0:
        raise ValueError("inactive context preparation before successful CX timer")
    return dict(record, global_irq=dict(flags=flags, status=status if flags & 1 else None,
                                        registered_masked=bool(flags & 8), intid=intid or None), inactive_context=stages, firmware_preparation=firmware, gmu_ahb_raw=ahb, cx_timer_raw=timer,
                cx_timer_samples=int(result[19]) if timer is not None else None,
                cx_timer_assessment=int(result[20], 16) if timer is not None else None,
                cx_timer_complete=timer == 0, context_probe_raw=context, context_reads_complete=context == 0,
                gmu_clock_raw=clock, gmu_clock_source_raw=source, gmu_clock_complete=clock == 0,
                gpu_snapshot="returned", guarded_mapping_raw=maps, guarded_probe_raw=probe,
                endpoint_reservation_disposition=disposition,
                endpoint_status_domain=int(result[7]) if returned else None,
                endpoint_raw_status=int(result[8], 16) if returned else None,
                endpoint_reservation_complete=returned and disposition == 0)
