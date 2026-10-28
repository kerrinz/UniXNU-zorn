"""Stop new local builds/phone trials at the owner's one-session deadline."""
from datetime import datetime
import json
from pathlib import Path


def minimum_gui_recovery_timeout(hold_seconds):
    # Successful exec activation may pet until 180s independently of GUI hold.
    # Include the 55s bite and bounded firmware/recovery enumeration headroom.
    return max(int(hold_seconds), 180) + 180


def check_deadline():
    root = Path(__file__).resolve().parents[2]
    directory = root / "out/zorn/unattended-20261028"
    policy = directory / "session.json"
    if not policy.exists():
        return
    data = json.loads(policy.read_text())
    if data.get("cancelled") is True:
        return
    if data.get("serial") != "92988a43":
        raise RuntimeError("unattended deadline identity mismatch")
    stop = datetime.fromisoformat(data["stop_new_trials_at"])
    if (directory / "STOP").exists() or datetime.now(stop.tzinfo) >= stop:
        raise RuntimeError("Owner's shutdown cutoff reached: leave K80 in recovery and pause; no new build or boot")
