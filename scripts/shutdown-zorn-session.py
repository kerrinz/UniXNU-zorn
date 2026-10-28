#!/usr/bin/env python3
"""One requested local deadline: drain K80 tests, power off K80, then this Mac.

No partition/slot changes; only 92988a43 is addressable. --serve is the timed
executor. --inspect is read-only. Config dates and a single-process lock make
this a one-session job, not a recurring shutdown service.
"""
import argparse
from datetime import datetime, timedelta
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SERIAL = "92988a43"
ZONE = ZoneInfo("Asia/Shanghai")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    if cfg.get("cancelled") is True:
        print("Owner cancelled this deadline; no actions")
        return
    assert cfg["serial"] == SERIAL and cfg["product"] == "zorn" and cfg["slot"] == "b"
    deadline = datetime.fromisoformat(cfg["shutdown_at"]).astimezone(ZONE)
    cutoff = datetime.fromisoformat(cfg["stop_new_trials_at"]).astimezone(ZONE)
    prepare = datetime.fromisoformat(cfg["prepare_at"]).astimezone(ZONE)
    assert cutoff < prepare < deadline and deadline - cutoff <= timedelta(hours=1)
    out = args.config.resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    status_path = out / "shutdown-status.json"
    journal = out / "shutdown-journal.jsonl"
    status = {"serial": SERIAL, "deadline": deadline.isoformat(), "pid": os.getpid()}

    def record(event, **fields):
        entry = {"time": datetime.now(ZONE).isoformat(), "event": event, **fields}
        with journal.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n"); f.flush(); os.fsync(f.fileno())
        status.update(entry)
        tmp = status_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        tmp.replace(status_path)

    def command(argv, timeout=12):
        try:
            result = subprocess.run(list(map(str, argv)), capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"

    adb = [cfg["adb"], "-s", SERIAL]
    fastboot = [cfg["fastboot"], "-s", SERIAL]

    def identity():
        code, state, _ = command(adb + ["get-state"])
        if code == 0:
            _, serial, _ = command(adb + ["get-serialno"])
            _, product, _ = command(adb + ["shell", "getprop", "ro.product.device"])
            if serial != SERIAL or product != "zorn":
                raise RuntimeError("ADB identity mismatch; no device action permitted")
            return state
        code, output, error = command(fastboot + ["getvar", "product"], timeout=3)
        if code == 0:
            if "product: zorn" not in output + error:
                raise RuntimeError("fastboot product mismatch")
            code, output, error = command(fastboot + ["getvar", "current-slot"], timeout=3)
            if code or "current-slot: b" not in output + error:
                raise RuntimeError("fastboot slot mismatch")
            return "fastboot"
        return "absent"

    def recover(seconds):
        end = time.monotonic() + seconds
        requested = False
        previous = None
        while time.monotonic() < end:
            state = identity()
            if state != previous:
                record("device-state", state=state); previous = state
            if state == "recovery":
                return True
            if not requested and state in ("fastboot", "device"):
                argv = fastboot + ["reboot", "recovery"] if state == "fastboot" else adb + ["reboot", "recovery"]
                code, output, error = command(argv, timeout=15)
                record("recovery-request", code=code, output=output, error=error)
                requested = True
            # XNU's independent watchdog returns it to recovery without ADB.
            time.sleep(2)
        return False

    if args.inspect:
        print(json.dumps({"configuration": cfg, "current_state": identity(), "no_power_action": True}, indent=2))
        return
    if not args.serve:
        parser.error("choose --inspect or --serve")
    lock = (out / "shutdown.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("An executor already owns this deadline")
    now = datetime.now(ZONE)
    if now.date() != deadline.date() or now > deadline + timedelta(minutes=5):
        raise SystemExit("Expired/different-day deadline; refusing a late shutdown")
    code, output, error = command(["/usr/bin/osascript", "-e",
        'tell application "System Events" to get count of processes'], timeout=20)
    status["mac_automation_preflight"] = {"code": code, "error": error}
    record("executor-ready", automation_code=code, automation_output=output, automation_error=error)
    # Keep the local timer eligible while unattended; no display/audio access.
    awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-t",
        str(max(1, int((deadline - now).total_seconds()) + 120))], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    status["caffeinate_pid"] = awake.pid
    prepared = False
    while datetime.now(ZONE) < deadline:
        if json.loads(args.config.read_text()).get("cancelled") is True:
            record("cancelled-by-owner")
            awake.terminate()
            return
        now = datetime.now(ZONE)
        if now >= cutoff and not (out / "STOP").exists():
            (out / "STOP").write_text("Requested 2026-10-28 05:00 shutdown; resume only after a new user instruction.\n")
            record("new-trials-stopped")
        if now >= prepare and not prepared:
            ready = recover(min(480, max(1, int((deadline - now).total_seconds()) - 30)))
            if ready:
                saved = command([sys.executable, ROOT / "UniXNU-zorn/scripts/read-zorn-log.py",
                    "--save", out / "last-checkpoints.bin", "--tail", "98"], timeout=30)
                (out / "last-checkpoints.txt").write_text(saved[1] + "\n" + saved[2])
                record("recovery-and-log-saved", read_code=saved[0])
            else:
                record("recovery-not-reached")
            prepared = True
        time.sleep(min(5, max(0.1, (deadline - datetime.now(ZONE)).total_seconds())))
    (out / "STOP").write_text("05:00 shutdown deadline reached; no further trials.\n")
    # Power requests are never sent before the configured deadline.
    if recover(35):
        code, output, error = command(adb + ["shell", "/system/bin/reboot", "-p"], timeout=12)
        record("phone-poweroff-requested", code=code, output=output, error=error)
        time.sleep(3)
        code, state, error = command(adb + ["get-state"], timeout=5)
        record("phone-post-poweroff-adb", reachable=code == 0, state=state, error=error)
    else:
        record("phone-unreachable-at-deadline", physical_poweroff_confirmed=False)
    record("mac-shutdown-requesting", method="System Events graceful shutdown")
    code, output, error = command(["/usr/bin/osascript", "-e",
        'tell application "System Events" to shut down'], timeout=25)
    record("mac-shutdown-command-returned", code=code, output=output, error=error)


if __name__ == "__main__":
    main()
