#!/usr/bin/env python3
"""Fragmented-MP4 host USB-camera clip for the exact claimed298 boot; no audio/phone IO."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

import zorn_ios26_gpu_v298_system_trial as t

BACKEND_SOURCE = Path(__file__).with_name('capture-zorn-video268.py')
_spec = importlib.util.spec_from_file_location('pres298_retained_camera268', BACKEND_SOURCE)
backend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backend)

CAMERA = backend.CAMERA
SECONDS = 320
TIMEOUT_SECONDS = SECONDS + 60


def inspect_current(bundle, claim, run, state, age):
    if type(run.get('boot_attempts')) is not int:
        raise ValueError('298 camera requires one actual integer boot count')
    binding = backend.inspect_binding(bundle, claim, run, scope=t.SCOPE, boot_sha=t.BOOT, age=age)
    if (state.get('active_run') != str(t.TRIAL / 'trial') or
            state.get('stop_device_operations') or
            state.get('gpu_discovery', {}).get('current_mode') != 'unattended-phone-connected'):
        raise ValueError('298 camera current mode/run differs')
    return dict(binding, seconds=SECONDS, host_timeout_seconds=TIMEOUT_SECONDS,
                camera_backend='fragmented298', actual_boot_version=298)


def capture_clip(report, out, ffmpeg, run=subprocess.run):
    out = Path(out)
    out.mkdir(exist_ok=True)
    video = out / 'v298-window.mp4'
    record = out / 'v298-window.json'
    if video.exists() or record.exists():
        raise ValueError('single fresh298 camera clip required')
    report = dict(
        report, started=datetime.now(timezone.utc).isoformat(),
        ffmpeg_path=str(ffmpeg),
        ffmpeg_sha256=hashlib.sha256(Path(ffmpeg).read_bytes()).hexdigest(),
    )
    args = [
        str(ffmpeg), '-nostdin', '-hide_banner', '-loglevel', 'warning', '-n',
        '-f', 'avfoundation', '-pixel_format', 'uyvy422', '-framerate', '30', '-i', CAMERA + ':none',
        '-an', '-t', str(SECONDS), '-vf', 'scale=640:-2', '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', '18', '-pix_fmt', 'yuv420p', '-g', '30',
        '-movflags', '+frag_keyframe+empty_moov+default_base_moof', str(video),
    ]
    report['arguments'] = args
    try:
        p = run(args, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
        report.update(returncode=p.returncode, stderr=p.stderr[-1600:])
    except subprocess.TimeoutExpired:
        report.update(returncode=124, error=f'{TIMEOUT_SECONDS}s host capture bound;child terminated by subprocess')
    if video.is_file():
        report.update(video=str(video), bytes=video.stat().st_size,
                      sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    if report.get('returncode') == 0 and not report.get('bytes'):
        report.update(returncode=1, error='no video bytes returned')
    record.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    bundle = t.validate(t.TRIAL / 'bundle.json')
    deadline = time.monotonic() + 90
    while True:
        try:
            claim = t.load(t.TRIAL / 'trial/one-shot.claim.json')
            run = t.load(t.TRIAL / 'trial/run.json')
            fastboot = t.TRIAL / 'trial/fastboot.txt'
            if fastboot.is_file():
                binding = inspect_current(bundle, claim, run, t.load(t.CURRENT),
                                          time.time() - fastboot.stat().st_mtime)
                break
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError('no fresh298 claimed boot within90s;camera not opened')
        time.sleep(0.25)
    report = capture_clip(binding, t.TRIAL / 'camera', t.SOURCES['camera_binary'])
    print(json.dumps(report))
    return report['returncode']


if __name__ == '__main__':
    raise SystemExit(main())
