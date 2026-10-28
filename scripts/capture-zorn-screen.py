#!/usr/bin/env python3
"""Capture one authorized USB-camera frame, tied to the latest K80 trial.

No microphone, alternate camera, screenshot, or automatic UI classification.
The two-second settling interval avoids using an unexposed first frame.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "out/zorn/debug"
# Exact AVFoundation name: the USB device has two spaces here.
USB_CAMERA_NAME = "USB  Camera"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    if run.parent != RUNS.resolve():
        parser.error("require an existing local out/zorn/debug trial")
    latest = sorted(p for p in RUNS.iterdir() if p.is_dir() and (p / "run.json").is_file())[-1]
    if run != latest.resolve():
        parser.error("refuse a stale trial; select the latest run")
    trial = json.loads((run / "run.json").read_text())
    build = json.loads((run / "build-inputs.json").read_text())
    if (trial.get("serial") != "92988a43" or trial.get("product") != "zorn" or
            trial.get("slot") != "b" or trial.get("status") not in ("started", "recovered") or
            build.get("status") != "ready" or trial.get("sha256") != build.get("sha256")):
        parser.error("require a matching, identified K80 trial and ready build")
    now = datetime.now().astimezone()
    started = datetime.strptime(trial["started"], "%Y-%m-%dT%H:%M:%S%z")
    if not 0 <= (now - started).total_seconds() <= trial["recovery_timeout_seconds"] + 120:
        parser.error("trial attribution expired; do not capture an unrelated scene")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.error("ffmpeg with AVFoundation is required")
    stamp = now.strftime("%Y%m%d-%H%M%S")
    image = run / ("camera-" + stamp + ".jpg")
    report = {"run": run.name, "boot_sha256": trial["sha256"],
              "trial_status_before_capture": trial["status"],
              "device_name": USB_CAMERA_NAME, "audio": False, "settle_seconds": 2,
              "desktop_qualified": False, "interpretation_required": True}
    command = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-f", "avfoundation",
               "-pixel_format", "uyvy422", "-framerate", "30", "-i", USB_CAMERA_NAME + ":none",
               "-an", "-ss", "2", "-frames:v", "1", "-update", "1", str(image)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=18)
        report.update(returncode=result.returncode, stderr=result.stderr[-1600:])
    except subprocess.TimeoutExpired:
        report.update(returncode=124, error="capture exceeded 18 seconds")
    report["captured_at"] = datetime.now().astimezone().isoformat()
    if report["returncode"] == 0 and image.is_file():
        report.update(image=str(image.relative_to(ROOT)), bytes=image.stat().st_size,
                      image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    elif report["returncode"] == 0:
        report.update(returncode=1, error="ffmpeg returned without a frame")
    (run / ("camera-" + stamp + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report["returncode"]


if __name__ == "__main__":
    sys.exit(main())
