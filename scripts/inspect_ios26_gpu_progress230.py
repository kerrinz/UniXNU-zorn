"""Bounded source terminal enum over the existing CDC transport; no panic text."""

import re

from inspect_ios26_gpu_progress229 import inspect_progress as inspect_previous


def inspect_progress(data, run_id, probe_run_id):
    if len(data) > 119808:
        raise ValueError("CDC total including terminal exceeds source budget")
    normal = []
    reason = None
    partial = 0
    ended = False
    expected = b"K80 TERM " + run_id.encode("ascii") + b" r="
    for line in data.splitlines(keepends=True):
        if ended:
            raise ValueError("data follows the one terminal packet")
        if line.startswith(b"K80 TERM "):
            match = re.fullmatch(rb"K80 TERM ([0-9a-f]{32}) r=([123])\r\n", line)
            if match:
                if match[1] != run_id.encode("ascii"):
                    raise ValueError("terminal identity differs")
                reason = int(match[2])
            elif (not line.endswith(b"\n") and len(line) < 47 and
                  (expected.startswith(line) or
                   any((expected + digit + b"\r\n").startswith(line) for digit in (b"1", b"2", b"3")))):
                partial = len(line)
            else:
                raise ValueError("terminal enum syntax differs")
            ended = True
        else:
            normal.append(line)
    result = inspect_previous(b"".join(normal), run_id, probe_run_id)
    if ended and (not result["transport_frames_valid"] or result["partial_tail_bytes"] or result["frame_count"] >= 39):
        raise ValueError("terminal requires prior complete frames within the same39frame budget")
    result["terminal230"] = dict(
        reason=reason,
        source_path={1: "time-limit", 2: "panic-classified-terminal", 3: "halt-or-restart"}.get(reason),
        packet_complete=reason is not None,
        partial_bytes=partial,
        host_received_exact_packet=reason is not None,
        panic_path_source_observed=reason == 2,
        cause_known=False,
        DMA_completion_or_quiescence_proven=False,
        scope="Source enum only; no error text, addresses, registers or backtrace. Missing/refused/partial packet proves no ending cause. START retains all USB resources; host reception does not prove device-side completion handling.",
    )
    return result
