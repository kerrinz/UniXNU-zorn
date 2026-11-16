"""Run a fixed GENI trial with the Mac receiver open before temporary boot."""

import argparse
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread

from inspect_ios26_geni_stages_capture import inspect_capture

HERE = Path(__file__).resolve().parent


def import_reader():
    spec = spec_from_file_location("geni_reader", HERE / "read-zorn-geni-uart.py")
    reader = module_from_spec(spec)
    spec.loader.exec_module(reader)
    return reader


def main():
    from zorn_ios26_geni_stages_trial import BOOT, TAG, TRIAL, validate

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=Path)
    args = parser.parse_args()
    bundle = TRIAL / "bundle.json"
    validate(bundle)
    trial = TRIAL / "trial"
    if (trial / "one-shot.claim.json").exists():
        parser.error("trial already consumed")
    raw_path = trial / "uart.raw"
    report_path = trial / "uart-capture.json"
    if report_path.exists() or raw_path.exists():
        parser.error("UART capture output already exists")
    reader = import_reader()
    ready, stop, ended = Event(), Event(), Event()
    errors = []

    def receive():
        try:
            reader.capture(args.port, raw_path, 600, ready_callback=ready.set,
                           stop_requested=stop.is_set)
        except (OSError, ValueError, reader.termios.error) as error:
            errors.append(str(error))
        finally:
            ended.set()
            ready.set()

    receiver = Thread(target=receive)
    receiver.start()
    try:
        if not ready.wait(5) or ended.is_set():
            raise RuntimeError(errors[0] if errors else "UART receiver did not open")
        result = subprocess.run(
            [sys.executable, str(HERE / "zorn_ios26_geni_stages_trial.py"),
             "--bundle", str(bundle), "--admission", str(TRIAL / "admission.json")],
            check=False,
        )
    finally:
        stop.set()
        receiver.join()

    run_path = trial / "run.json"
    run = json.loads(run_path.read_text()) if run_path.exists() else {}
    raw = raw_path.read_bytes()
    recovery = run.get("recovery_identity_after", {}).get("family")
    verified = None
    if result.returncode == 0 and recovery and run.get("uart_tx_result") == 0:
        try:
            verified = inspect_capture(raw, (trial / "before-log.bin").read_bytes(),
                                     (trial / "after-log.bin").read_bytes(), TAG)
        except (ValueError, OSError) as error:
            errors.append(str(error))
    report = {
        "boot_sha256": BOOT, "tag": TAG, "port": str(args.port),
        "serial_bytes": len(raw), "serial_sha256": hashlib.sha256(raw).hexdigest(),
        "recovery": recovery, "boot_runner_exit": result.returncode,
        "wire_matches_recovered_checkpoint": verified is not None,
        "verified_stages": verified["stages"] if verified else [], "capture_errors": errors,
    }
    with report_path.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))
    return 0 if verified and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
