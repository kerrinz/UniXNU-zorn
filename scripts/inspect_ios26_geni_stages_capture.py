"""Verify ordered K80 GENI stage records against the recovered snapshot."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from inspect_ios26_geni_state_record import inspect_page
from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope

STAGES = ("root-prepare", "root-registered", "pid1-worker")


def inspect_capture(raw, before, after, tag):
    if not re.fullmatch(r"[0-9a-f]{32}", tag):
        raise ValueError("expected a 32-digit lowercase artifact ID")
    identity = bytes.fromhex(tag)
    decoded = inspect_page(after, identity, before)
    if decoded["uart_tx_result"] != 0:
        raise ValueError("GENI controller did not complete the snapshot transfer")
    body = inspect_envelope(after, identity, before)["text"].rpartition("; uart=")[0]
    prefix = f"K80 iOS26 GENI {tag} ".encode("ascii")
    snapshot = f"K80 iOS26 GENI TX {tag}: ".encode("ascii")
    expected = [prefix + stage.encode("ascii") for stage in STAGES]
    expected.append(snapshot + body.encode("ascii"))
    # Preserve the CRLF boundary. A final unterminated tagged record must also
    # fail, including when it duplicates a complete record earlier in the file.
    *lines, tail = raw.split(b"\r\n")
    if tail.startswith((prefix, snapshot)):
        raise ValueError("unterminated GENI record for this artifact")
    actual = [line for line in lines if line.startswith((prefix, snapshot))]
    if actual != expected:
        raise ValueError("missing, repeated, reordered or changed GENI records")
    return {
        "artifact_id": tag,
        "stages": [*STAGES, "snapshot"],
        "wire_matches_recovered_checkpoint": True,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("raw", type=Path)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    try:
        report = inspect_capture(args.raw.read_bytes(), args.before.read_bytes(),
                                 args.after.read_bytes(), args.tag)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
