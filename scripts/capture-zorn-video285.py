#!/usr/bin/env python3
"""Use the retained268 camera backend only for a fresh, exact claimed285 boot.

The common backend retains its v268-window filenames; scope/boot metadata and
this enclosing285 archive identify the actual trial. No phone commands here.
"""
import importlib.util
import json
from pathlib import Path
import time

import zorn_ios26_gpu_v285_system_trial as t

BACKEND_SOURCE = Path(__file__).with_name('capture-zorn-video268.py')
_spec = importlib.util.spec_from_file_location('known285_retained_camera268', BACKEND_SOURCE)
backend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backend)


def inspect_current(bundle, claim, run, state, age):
    if type(run.get('boot_attempts')) is not int:
        raise ValueError('285 camera requires one actual integer boot count')
    binding = backend.inspect_binding(bundle, claim, run, scope=t.SCOPE, boot_sha=t.BOOT, age=age)
    if (state.get('active_run') != str(t.TRIAL/'trial') or
            state.get('stop_device_operations') or
            state.get('gpu_discovery', {}).get('current_mode') != 'unattended-phone-connected'):
        raise ValueError('285 camera current mode/run differs')
    return dict(binding, camera_backend='retained268', actual_boot_version=285,
                original_common_filenames_retained=True)


def main():
    bundle = t.validate(t.TRIAL/'bundle.json')
    deadline = time.monotonic()+90
    while True:
        try:
            claim = t.load(t.TRIAL/'trial/one-shot.claim.json')
            run = t.load(t.TRIAL/'trial/run.json')
            fastboot = t.TRIAL/'trial/fastboot.txt'
            if fastboot.is_file():
                binding = inspect_current(bundle, claim, run, t.load(t.CURRENT),
                                          time.time()-fastboot.stat().st_mtime)
                break
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError('no fresh285 claimed boot within90s;camera not opened')
        time.sleep(0.25)
    report = backend.capture_clip(binding, t.TRIAL/'camera', t.SOURCES['camera_binary'])
    print(json.dumps(report))
    return report['returncode']


if __name__ == '__main__':
    raise SystemExit(main())
