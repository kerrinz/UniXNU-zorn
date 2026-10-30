"""Helpers for a proposed v19 high-half display overlay; no USB operations.

Call only after validating a v19 GUI header. v18 and older keep their original
display values untouched.
"""

SLOTS = (0, 1, 2, 3, 4, 6, 7, 9, 10, 11, 13, 14, 25, 27, 30, 31)
EVENTS = ("retired", "armed", "sent", "idle", "late", "started", "properties")


def decode(display):
    if len(display) != 32 or any(type(value) is not int or not 0 <= value < 1 << 64
                                 for value in display):
        raise ValueError("invalid display progress words")
    original = list(display)
    values = [original[index] >> 32 for index in SLOTS]
    for index in SLOTS:
        original[index] &= 0xffffffff
    now_ms = values[14]
    events = {}
    for index, name in enumerate(EVENTS):
        count, published_ms = values[index * 2:index * 2 + 2]
        # Zero count/nonzero time can be a concurrent snapshot, so preserve
        # it as uncertain, instead of inventing a coherent event or an error.
        overlaps = published_ms > now_ms or (count == 0 and published_ms != 0)
        events[name] = {"count": count, "last_published_uptime_ms": published_ms,
                        "sample_overlapped": overlaps,
                        "age_ms": now_ms - published_ms if count and not overlaps else None}
    return original, {"sample_uptime_ms": now_ms, "unknown_events": values[15],
                      "events": events, "receipt_confirmed": False,
                      "snapshot_policy": "independent relaxed atomic words; times may be stale or overlap adjacent callbacks"}
