"""Receiver-first284 transport using the established268 CDC implementation.

run_capture takes the fixed284 trial module, whose validate function must bind
the complete local bundle. The maintained runner independently checks admission
and installed-root evidence before claim/device access. No standalone boot CLI.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import termios
from threading import Event, Thread
import time

from zorn_ios26_perf284_capture import finish_capture

# Preserve old receipts/source instead of editing268. Reuse its actual bounded
# serial reader, exclusive open and source-defined identity matching verbatim.
TRANSPORT_SOURCE = Path(__file__).with_name('read-zorn-gpu-census268-cdc.py')
_spec = importlib.util.spec_from_file_location('known284_retained_cdc268', TRANSPORT_SOURCE)
_transport = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_transport)
find_port, capture = _transport.find_port, _transport.capture
PRODUCT = _transport.PRODUCT


def run_capture(trial):
    bundle = trial.TRIAL / 'bundle.json'
    trial.validate(bundle)
    out = trial.TRIAL / 'trial'
    raw = out / 'cdc.raw'
    if any(path.exists() or path.is_symlink() for path in
           (raw, out / 'cdc-capture.json', out / 'one-shot.claim.json')):
        raise ValueError('284 CDC trial has existing evidence or a claim')
    stop, polling = Event(), Event()
    errors, ports = [], []

    def receive():
        deadline = time.monotonic() + 610
        identity = 'ZORN26' + trial.TAG[:12].upper()
        try:
            while not stop.is_set() and time.monotonic() < deadline:
                result = subprocess.run(
                    ['/usr/sbin/ioreg', '-r', '-n', PRODUCT, '-l', '-w0'],
                    text=True, timeout=3, capture_output=True, check=False)
                if result.returncode:
                    raise ValueError('284 CDC registry query failed')
                port = find_port(result.stdout, identity)
                polling.set()
                if port:
                    ports.append(port)
                    capture(port, raw, stop, deadline)
                    return
                stop.wait(0.25)
        except (OSError, subprocess.SubprocessError, ValueError, termios.error) as error:
            errors.append(str(error))
        finally:
            polling.set()

    receiver = Thread(target=receive)
    receiver.start()
    code = 1
    try:
        if not polling.wait(5) or errors:
            raise RuntimeError('284 CDC listener could not start')
        result = subprocess.run(
            [sys.executable, '-B', str(Path(__file__).with_name('run-zorn-debug.py')),
             '--ios26-perf284-trial', '--bundle', str(bundle),
             '--admission', str(trial.TRIAL / 'admission.json')], check=False)
        code = result.returncode
    except (OSError, subprocess.SubprocessError, RuntimeError) as error:
        errors.append(str(error))
    finally:
        stop.set()
        receiver.join()
    verdict = finish_capture(out, tag=trial.TAG, program_tag=trial.PROBE_TAG,
                             scope=trial.SCOPE, runner_exit=code,
                             transport_errors=errors, port=ports[0] if ports else None)
    print(json.dumps({key: verdict.get(key) for key in (
        'verified', 'frame_count', 'bytes', 'runner_exit', 'errors',
        'serial_shot265_with_recovery_observed',
        'manual_observation_completed278_with_recovery_observed')}))
    return 0 if verdict['verified'] else 1
