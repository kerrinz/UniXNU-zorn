"""Decode a recovered K80 USB CDC preflight record."""

import re

from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope

WORD = r"([0-9a-f]{8})"
RECORD = re.compile(
    rf"K80 CDC preflight: result=([0-9]+) power={WORD} clocks={WORD} core={WORD} hw={WORD}"
    rf" gctl={WORD} dctl={WORD} dsts={WORD} id={WORD}/{WORD}/{WORD} scr0={WORD}"
    rf" matches=([0-9]+) route={WORD} cb={WORD}/{WORD}/{WORD} tx=([0-9]+) cdc=([0-9]+)/([0-9]+)/([0-9]+)/([0-7])"
)
RESULTS = (
    "mapping failed", "power off", "clock off", "invalid core", "wrong role",
    "controller busy", "unrecognized SMMU", "missing stream", "ambiguous stream",
    "translated or faulting", "identity route",
)


def inspect_page(page, tag, before):
    envelope = inspect_envelope(page, tag, before)
    match = RECORD.fullmatch(envelope["text"])
    if not match:
        raise ValueError("missing K80 USB CDC preflight fields")
    result, matches = int(match[1]), int(match[13])
    if result >= len(RESULTS) or matches > 107:
        raise ValueError("out-of-range K80 USB CDC preflight fields")
    if ((result <= 7 and matches != 0) or (result == 8 and matches < 2)
            or (result >= 9 and matches != 1)):
        raise ValueError("K80 USB CDC result and stream count differ")
    names = ("power", "clocks", "core", "hardware", "gctl", "dctl", "dsts",
             "id0", "id1", "id2", "scr0", "route", "cbar", "sctlr", "cba2r")
    words = match.groups()[1:12] + match.groups()[13:17]
    tx, events, setups, completed, flags = map(int, match.groups()[17:])
    if tx > 10 or (tx == 7) != (result != 10) or setups > events or completed > 63:
        raise ValueError("USB CDC transmit disagrees with route qualification")
    return dict(envelope, result=RESULTS[result], stream_matches=matches, tx_status=tx,
                registers=dict(zip(names, map(lambda value: int(value, 16), words))),
                cdc_state=dict(events=events, setups=setups, completed=completed, flags=flags))
