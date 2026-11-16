"""Own-source device-creation boundaries; no inference from missing markers."""

import re

from inspect_ios26_gpu_progress226 import inspect_progress as inspect_previous


def device_boundaries(frames, probe_run_id):
    seen = []
    foreign = invalid = False
    for frame in frames:
        text = (frame.get("application") or {}).get("raw_stderr", "")
        for match in re.finditer(r"ZORN229DEV run=([0-9a-f]{32}) stage=([0-9]+)\n", text):
            if match[1] != probe_run_id:
                foreign = True
                continue
            stage = int(match[2])
            if stage not in (1, 2, 3):
                invalid = True
            elif stage not in seen:
                seen.append(stage)
    ordered = seen in ([], [1], [1, 2], [1, 2, 3])
    valid = ordered and not foreign and not invalid
    return dict(
        stages=seen, ordered_prefix=ordered, foreign_identity=foreign,
        invalid_stage=invalid, unambiguous=valid,
        phase2_report_returned_to_probe_observed=valid and 1 in seen,
        before_standard_MTL_call_observed=valid and 2 in seen,
        standard_MTL_call_returned_observed=valid and 3 in seen,
        scope="Source229 markers only; stage1 follows report2 with optional10s wait removed; stage2 precedes MTL,stage3 permits nil;absence proves no failure cause,panic or PAC defect.",
    )


def inspect_progress(data, run_id, probe_run_id):
    result = inspect_previous(data, run_id, probe_run_id)
    result["device_creation229"] = device_boundaries(result["frames"], probe_run_id)
    return result
