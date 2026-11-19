#!/usr/bin/env python3
"""Camera gating296 host regression; no camera is opened and no phone accessed."""
import argparse, copy, hashlib, importlib.util, json, tempfile
from pathlib import Path
from types import SimpleNamespace

import zorn_ios26_gpu_v296_system_trial as t


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name('capture-zorn-video296.py')
    spec = importlib.util.spec_from_file_location('actual_camera296', source)
    camera = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(camera)
    bundle = dict(scope=t.SCOPE, serial='92988a43', product='zorn', slot='a',
                  pins=dict(boot=dict(sha256=t.BOOT)))
    claim = dict(scope=t.SCOPE, boot_sha256=t.BOOT, status='consumed-no-repeat', before_first_USB=True)
    run = dict(scope=t.SCOPE, status='single-boot-attempt', boot_attempts=1)
    state = dict(active_run=str(t.TRIAL / 'trial'), stop_device_operations=False,
                 gpu_discovery=dict(current_mode='unattended-phone-connected'))
    args0 = [bundle, claim, run, state, 10.0]
    binding = camera.inspect_current(*args0)
    assert binding['scope'] == t.SCOPE and binding['boot_sha256'] == t.BOOT
    assert binding['actual_boot_version'] == 296 and not binding['physical_known_image_proven']
    checks = ['source268 camera backend reused with296 exact scope/boot and no physical qualification']
    cases = [
        ('foreign bundle scope', lambda a: a[0].update(scope='old')),
        ('foreign boot', lambda a: a[0]['pins']['boot'].update(sha256='0' * 64)),
        ('foreign serial', lambda a: a[0].update(serial='f85d4270')),
        ('wrong slot', lambda a: a[0].update(slot='b')),
        ('unconsumed claim', lambda a: a[1].update(status='unused')),
        ('claim before USB missing', lambda a: a[1].update(before_first_USB=False)),
        ('repeated boot', lambda a: a[2].update(boot_attempts=2)),
        ('boolean boot count', lambda a: a[2].update(boot_attempts=True)),
        ('foreign active run', lambda a: a[3].update(active_run='old')),
        ('stop set', lambda a: a[3].update(stop_device_operations=True)),
        ('offline mode', lambda a: a[3]['gpu_discovery'].update(current_mode='unattended-offline-no-phone')),
        ('stale fastboot file', lambda a: a.__setitem__(4, 121)),
        ('future fastboot file', lambda a: a.__setitem__(4, -1)),
    ]
    for name, change in cases:
        bad = copy.deepcopy(args0)
        change(bad)
        try:
            camera.inspect_current(*bad)
        except ValueError:
            checks.append(name + ' rejected before camera')
        else:
            raise AssertionError(name)
    with tempfile.TemporaryDirectory() as temp:
        def fake_ffmpeg(arguments, **kwargs):
            assert arguments[0] == str(t.SOURCES['camera_binary'])
            assert '-an' in arguments and '-n' in arguments
            assert arguments[arguments.index('-t') + 1] == '340'
            assert kwargs['timeout'] == 358
            Path(arguments[-1]).write_bytes(b'HOST-ONLY-FAKE-CAMERA-BYTES')
            return SimpleNamespace(returncode=0, stderr='HOST ONLY')
        report = camera.backend.capture_clip(binding, Path(temp), t.SOURCES['camera_binary'], run=fake_ffmpeg)
        assert report['returncode'] == 0 and report['boot_sha256'] == t.BOOT
        assert report['scope'] == t.SCOPE and not report['physical_known_image_proven']
        assert report == json.loads((Path(temp) / 'v268-window.json').read_text())
        try:
            camera.backend.capture_clip(binding, Path(temp), t.SOURCES['camera_binary'], run=fake_ffmpeg)
        except ValueError:
            checks.append('shared bounded camera backend writes296 scope and refuses duplicate output')
        else:
            raise AssertionError('camera overwrite')
    pin = lambda p: dict(path=str(Path(p).resolve()), sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    result = dict(
        passed=True, checks=checks, source=pin(source),
        retained_camera_backend=pin(camera.BACKEND_SOURCE), test_tool=pin(__file__),
        actual_ffmpeg_not_executed=True, fake_video_bytes_discarded=True,
        phone_access=False, camera_opened=False, hardware_qualified=False,
    )
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS296 camera gate/backend: ' + str(len(checks)) + ' controls; no camera/phone I/O')


if __name__ == '__main__':
    main()
