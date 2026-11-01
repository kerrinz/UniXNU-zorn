#!/usr/bin/env python3
"""Exercise local admission refusals with every process/USB call trapped."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

source = Path(__file__).with_name('zorn_unixnu64_run.py')
spec = importlib.util.spec_from_file_location('unixnu64_admission', source)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def trap(*args, **kwargs):
    raise AssertionError('admission reached a process/USB call')


base = dict(serial='92988a43',slot='a',storage_profile='unixnu64',timeout=600,
            allow_boot=True,GPU_enabled=False,fresh_Data=False,
            run_directory='test-run',inputs={},archive={})
refused = 0
with tempfile.TemporaryDirectory(prefix='unixnu64-admission-') as folder:
    root = Path(folder).resolve()
    runner.ROOT = root
    current = root/'out/zorn/unattended-active/current.json'
    current.parent.mkdir(parents=True)
    current.write_text('{}')
    ready = root/'ready.json'
    image = root/'out/zorn/dual-system-reinstall-20261101/image/boot.img'
    base['image'] = str(image)

    def check(data, expected):
        global refused
        ready.write_text(json.dumps(data))
        with patch.object(sys,'argv',['runner','--unixnu64-install-trial',str(ready)]), \
             patch.object(runner,'command',trap), patch('subprocess.run',trap), \
             patch('subprocess.Popen',trap), patch('subprocess.check_output',trap):
            try:
                runner.main()
            except RuntimeError as error:
                assert expected in str(error), str(error)
                refused += 1
            else:
                raise AssertionError('invalid admission was accepted')

    for key,value in [('serial','f85d4270'),('slot','b'),('storage_profile','userdata'),
                      ('timeout',900),('allow_boot',False),('GPU_enabled',True)]:
        check(dict(base,**{key:value}),'new-installation admission differs')
    check(base,'incomplete archive/source closure')
    check(dict(base,image=str(root/'other/boot.img')),'must belong to this storage workspace')
    for directory in ('../outside','/tmp/outside',''):
        check(dict(base,run_directory=directory),'incomplete archive/source closure')
    ready.with_suffix('.claim.json').write_text('{"status":"consumed-no-repeat"}')
    check({},'already consumed; no USB action')

print(json.dumps(dict(refusals=refused,process_calls=0,USB_calls=0,
                     scope='local refusal controls; no runtime ownership or recovery proof')))
