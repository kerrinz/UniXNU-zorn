"""Decode the delayed FT3683 sample from a continuous CPU lockscreen trial."""

import re

from inspect_ios26_lockscreen_touch_cpu_record import FLAGS, MILESTONE, inspect_envelope


def inspect_page(page, expected_run_id, before):
    envelope = inspect_envelope(page, expected_run_id, before)
    prefix = re.fullmatch(r"cpu_online=([0-8]); mode=continuous; (.*)", envelope["text"])
    if not prefix:
        raise ValueError("expected a continuous FT3683 CPU checkpoint")
    result = {
        "run_id": envelope["run_id"],
        "freshness": envelope["freshness"],
        "cpu_online": int(prefix[1]),
        "touch_input_delivery_proven": False,
    }
    body = prefix[2]
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
