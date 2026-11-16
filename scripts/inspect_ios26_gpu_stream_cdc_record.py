"""Decode the K80 checkpoint with active SMMU global fault control."""

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
    gpu, separator, context_irq = gpu.partition(",g=")
    if not separator or not re.fullmatch(r"[0-9a-f]{1,14}", context_irq):
        raise ValueError("missing or invalid GMU context fault IRQ record")
    packed = int(context_irq, 16)
    stage, bank, context_intid = packed & 255, (packed >> 8) & 255, (packed >> 16) & 65535
    gic_readback = (packed >> 32) & 0xfff
    stream = packed >> 44
    stream_slot = (stream >> 3) & 31
    stream_writes = (stream >> 1) & 3
    stream_complete = bool(stream & 256)
    if (stream > 0x1ff or (stream and (stage != 4 or not stream & 1))
            or stream_writes > 2 or stream_slot > 24
            or (stream_writes and not stream_slot)
            or (stream_complete and stream_writes != 2)):
        raise ValueError("inconsistent GMU blocked stream record")
    if (gic_readback > 0xfff or (gic_readback and stage < 3)
            or (stage == 4 and not gic_readback & 0x800)
            or (gic_readback & 0x800 and stage != 4)
            or (gic_readback & 0x800 and gic_readback & 0x78f != 0x78f)
            or stage > 4 or (not stage and packed)
            or (stage == 1 and context_intid)
            or (context_intid and not 32 <= context_intid <= 1019)
            or (stage >= 3 and (not context_intid or not 2 <= bank < 22))):
        raise ValueError("inconsistent GMU context IRQ stage")
    gpu, separator, control = gpu.partition(",a=")
    control_fields = re.fullmatch(
        r"([0-9a-f]{1,3})/([0-9a-f]{1,8})/([0-9a-f]{1,8})/([0-9a-f]{1,8})/([0-9]{1,4})/([0-9a-f]{1,8})",
        control,
    )
    if not separator or not control_fields:
        raise ValueError("missing or invalid global fault control record")
    state, before_cr0, readback_cr0, gfsr = (int(value, 16) for value in control_fields.groups()[:4])
    sync_reads = int(control_fields[5])
    sync_status = int(control_fields[6], 16)
    if (state > 0x1ff or any(state & (1 << bit) and not state & (1 << (bit - 1))
                              for bit in range(1, 9))
            or (before_cr0 and not state & 2)
            or (state & 4 and before_cr0 & 1)
            or (gfsr and not state & 8)
            or (readback_cr0 and not state & 64)
            or (sync_reads and not state & 16)
            or (sync_status and not sync_reads)
            or sync_reads > 4096):
        raise ValueError("inconsistent global fault control state")
    complete = bool(state & 256)
    if complete and (not sync_reads or sync_status & 1 or gfsr or
                     readback_cr0 != (before_cr0 | 0x06)):
        raise ValueError("global fault control complete without matching hardware readback")
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
    if (state and flags != 15) or (flags == 15 and status == 0 and not complete):
        raise ValueError("global fault control state conflicts with IRQ registration")
    fault_control = dict(state=state, complete=complete, cr0_before=before_cr0 if state & 2 else None,
                         cr0_readback=readback_cr0 if state & 64 else None,
                         gfsr=gfsr if state & 8 else None, sync_reads=sync_reads,
                         sync_status=sync_status if sync_reads else None)
    if (bool(stage) != complete or (stage and (status == 0) != stream_complete)
            or (stage == 4 and not stream)):
        raise ValueError("GMU context IRQ state conflicts with global control")
    context_fault_irq = dict(stage=stage, bank=bank if stage else None, intid=context_intid or None,
                             status=(0 if stage == 4 else status) if stage else None, registered_masked=stage == 4,
                             gic_readback=gic_readback)
    blocked_stream = dict(attempted=bool(stream), slot=stream_slot - 1 if stream_slot else None,
                          writes=stream_writes, complete=stream_complete, status=status if stream else None)
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
    return dict(record, blocked_stream=blocked_stream, context_fault_irq=context_fault_irq, global_fault_control=fault_control, global_irq=dict(flags=flags, status=status if flags & 1 else None,
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
