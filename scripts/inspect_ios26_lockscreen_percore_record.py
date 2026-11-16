"""Decode paired per-core XNU accounting samples plus FT3683 status."""

import re

from inspect_ios26_lockscreen_touch_cpu_record import FLAGS, MILESTONE, inspect_envelope

PAIR = r"[0-9a-f]{8}/[0-9a-f]{8}"
PREFIX = re.compile(
    rf"cpu_online=([0-8]); cpumask=([0-9a-f]{{2}}); ticks=({PAIR}(?:,{PAIR}){{7}}); mode=continuous; (.*)"
)


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    match = PREFIX.fullmatch(envelope["text"])
    if not match:
        raise ValueError("expected eight CPU accounting pairs and continuous FT3683 status")
    online = int(match[1])
    valid = int(match[2], 16)
    pairs = [tuple(int(value, 16) for value in pair.split("/")) for pair in match[3].split(",")]
    for cpu, (user, system) in enumerate(pairs):
        if not valid & (1 << cpu) and (user or system):
            raise ValueError("accounting delta without a valid processor pair")
    active = [cpu for cpu, (user, system) in enumerate(pairs) if user or system]
    result = inspect_status(envelope, online, match[4])
    return dict(result, valid_cpu_mask=valid, active_cpu_ids=active,
                user_system_tick_deltas=pairs, all_eight_executed_work=valid == 255 and len(active) == 8)


def inspect_status(envelope, online, body):
    result = {
        "run_id": envelope["run_id"],
        "freshness": envelope["freshness"],
        "cpu_online": online,
        "touch_input_delivery_proven": False,
    }
    if body == "K80 FT3683: schedule did not return by sample; PID1 EL0":
        return dict(result, schedule_returned=False, continuous_polling_observed=False)
    early = re.fullmatch(r"K80 FT3683: schedule=([0-9a-f]{8}) owner=0; PID1 EL0", body)
    if early:
        return dict(result, schedule_returned=True, schedule_raw=int(early[1], 16),
                    owner_present=False, continuous_polling_observed=False)
    match = MILESTONE.fullmatch(body)
    if not match:
        raise ValueError("missing FT3683 status")

    flags = int(match["flags"], 16)
    frames, accepted, attempts, outcome, phase, end = (
        int(match[name]) for name in ("frames", "accepted", "attempts", "outcome", "worker_phase", "worker_end")
    )
    capture_reads = int(match["capture_reads"])
    if (flags >> len(FLAGS) or accepted > min(attempts, 8) or attempts > 12
            or frames > 0xffffffff or outcome > 7 or capture_reads > 32 or phase > 5 or end == 2):
        raise ValueError("FT3683 status is inconsistent with continuous acquisition")
    observed = {flag: bool(flags & (1 << index)) for index, flag in enumerate(FLAGS)}
    polling = (phase == 4 and end == 0 and not observed["producer_finished"]
               and observed["hid_started"] and observed["worker_entered"] and frames > 64)
    return dict(
        result, schedule_returned=True, schedule_raw=int(match["schedule"], 16), owner_present=True,
        observed=observed, continuous_polling_observed=polling,
        worker_phase=phase, worker_end=end, frame_read_calls_returned=frames,
        baseline_accepted=accepted, baseline_attempts=attempts,
        returned_identity=list(bytes.fromhex(match["identity"])[:int(match["identity_count"])]),
        last_source_outcome=outcome if observed["last_source_valid"] else None,
        last_submit_raw=int(match["detail"], 16) if observed["last_source_valid"] and outcome == 7 else None,
    )
