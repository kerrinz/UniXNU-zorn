#!/usr/bin/env python3
"""305 receiver/postprocessor on explicitly synthetic retained274+menu297 fixtures."""
import argparse, base64, copy, hashlib, json, struct, tempfile, zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import zorn_ios26_glass297_capture as post
import zorn_ios26_opp305_receiver as receiver
from zorn_ios26_glass297_capture import finish_capture
import zorn_ios26_gpu_v305_system_trial as t
from inspect_ios26_ui_menu274 import split_menu
from inspect_ios26_ui_roi270 import split_roi


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir()
    repo = Path(__file__).resolve().parents[1]
    legacy = json.loads((repo / 'docs/evidence/k80-gpu-v274-context-menu-observed-2026-11-17.json').read_text())
    legacy_raw = Path(legacy['raw_CDC']['path'])
    old_tag = legacy['boot_tag']
    old_probe = legacy['inactive_probe_program_tag']
    menu_free, _, _ = split_menu(legacy_raw.read_bytes(), old_tag)
    normal_old, _, _ = split_roi(menu_free, old_tag)
    normal = normal_old.replace(old_tag.encode(), t.TAG.encode()).replace(old_probe.encode(), t.PROBE_TAG.encode())

    old_bytes = legacy_raw.read_bytes()
    at = 0
    menu = None
    while at < len(old_bytes):
        if old_bytes.startswith(b'K80UI274', at):
            assert menu is None
            pkt = bytearray(old_bytes[at:at + 288])
            pkt[8:24] = bytes.fromhex(t.TAG)
            struct.pack_into('<I', pkt, 280, zlib.crc32(pkt[:280]))
            menu = bytes(pkt)
            at += 288
        elif old_bytes.startswith(b'K80SH270', at):
            at += 68 + struct.unpack_from('<I', old_bytes, at + 28)[0]
        else:
            at = old_bytes.index(b'\r\n', at) + 2
    assert menu is not None

    menu297_fixture = (t.BASE / 'glass-sampler-asan/SYNTHETIC-menu297-wire.bin').read_bytes()
    pixels = menu297_fixture.removeprefix(b'fixture-before\r\n').removesuffix(b'fixture-after\r\n')
    chunks = []
    while pixels:
        size = 68 + struct.unpack_from('<I', pixels, 28)[0]
        chunk = bytearray(pixels[:size])
        assert chunk.startswith(b'K80SH297')
        chunk[8:24] = bytes.fromhex(t.TAG)
        struct.pack_into('<I', chunk, 64, zlib.crc32(chunk[:64]))
        chunks.append(bytes(chunk))
        pixels = pixels[size:]
    assert len(chunks) == 7

    wire = normal + menu + b''.join(chunks)
    page = bytearray((legacy_raw.parent / 'after-log.bin').read_bytes())
    assert page[8:24] == bytes.fromhex(old_tag)
    page[8:24] = bytes.fromhex(t.TAG)
    page[28:32] = bytes(4)
    struct.pack_into('<I', page, 28, zlib.crc32(page[:544]))
    before_page = (legacy_raw.parent / 'before-log.bin').read_bytes()

    (a.out / 'SYNTHETIC-wire305.bin').write_bytes(wire)
    (a.out / 'SYNTHETIC-page305.bin').write_bytes(page)
    checks = []

    def capture(*, data=wire, code=0, fields=None, missing_run=False):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            if data is not None:
                (out / 'cdc.raw').write_bytes(data)
            (out / 'before-log.bin').write_bytes(before_page)
            (out / 'after-log.bin').write_bytes(page)
            run = dict(scope=t.SCOPE, boot_attempts=1, fastboot_returned_success=True,
                       recovery_identity_after=dict(family='TWRP'))
            run.update(fields or {})
            if not missing_run:
                (out / 'run.json').write_text(json.dumps(run))
            x = finish_capture(out, tag=t.TAG, program_tag=t.PROBE_TAG,
                               timing_session=t.TIMING_SESSION, scope=t.SCOPE, runner_exit=code)
            assert json.loads(json.dumps(x)) == json.loads((out / 'cdc-capture.json').read_text()) and not x['full_GPU_qualification']
            if missing_run:
                assert (out / 'ordinary297-stderr.bin').exists() and (out / 'screen297-menu.bgrx').exists()
            try:
                finish_capture(out, tag=t.TAG, program_tag=t.PROBE_TAG,
                               timing_session=t.TIMING_SESSION, scope=t.SCOPE, runner_exit=code)
            except FileExistsError:
                pass
            else:
                raise AssertionError('capture overwritten')
            return x

    x = capture()
    assert x['verified'] and x['menu_capture_with_recovery'] and x['synthetic_menu_dispatch_returned274']
    assert not x['scalar_timing287']['complete'] and not x['glass_blur_visually_qualified']
    checks.append('actual305 capture completes on explicitly synthetic274menu+menu297+native-page fixture;no hardware qualification')

    for name, kw in [
        ('old boot', dict(data=legacy_raw.read_bytes())),
        ('missing raw', dict(data=None)),
        ('truncated', dict(data=wire[:-17])),
        ('runner failure', dict(code=1)),
        ('missing run', dict(missing_run=True)),
        ('bool boot count', dict(fields=dict(boot_attempts=True))),
        ('wrong scope', dict(fields=dict(scope='foreign'))),
        ('two boots', dict(fields=dict(boot_attempts=2))),
        ('no successful boot', dict(fields=dict(fastboot_returned_success=False))),
        ('unknown recovery', dict(fields=dict(recovery_identity_after=dict(family='unknown')))),
    ]:
        x = capture(**kw)
        assert not x['verified'] and not x['menu_capture_with_recovery']
        checks.append(name + ' cannot qualify')

    original_inspect = post.inspect_progress
    base_res, base_img, base_rem = original_inspect(wire, t.TAG, t.PROBE_TAG)
    rpc_source = t.STAGE / 'k80-gpu-v290-async-submit-71e1465877624de2aaac70d24739bf6f/rpc-decoder-host/SYNTHETIC-two-reports.bin'
    rpc_fixture = rpc_source.read_bytes().replace(b'a' * 32, t.TIMING_SESSION.encode())
    for name, frag, want_complete, want_rpc in [
        ('actual-schema', rpc_fixture, True, True),
        ('loss', rpc_fixture.replace(b'NC meta 287 18 0 0 2000000000', b'NC meta 287 18 4 1 2000000000'), True, False),
        ('foreign session', rpc_fixture.replace(t.TIMING_SESSION.encode(), b'0' * 32), False, False),
    ]:
        v = copy.deepcopy(base_res)
        v['journal248'].update(stderr_base64=base64.b64encode(frag).decode(), sha256=hashlib.sha256(frag).hexdigest())
        with patch.object(post, 'inspect_progress', side_effect=lambda *a, _v=v: (copy.deepcopy(_v), base_img, base_rem)):
            x = capture()
        if name == 'foreign session':
            assert not x['verified'] and x['errors']
        else:
            assert x['verified'] and x['scalar_timing287']['complete'] == want_complete, x['errors']
            assert x['scalar_timing287']['native_RPC_complete'] == want_rpc
        checks.append('actual postprocessor timing ' + name + ':explicit synthetic journal;no GPU evidence')

    class HostThread:
        def __init__(self, target): self.target = target
        def start(self): self.target()
        def join(self): pass

    registry = '"idVendor" = 4617\n"idProduct" = 1\n"USB Serial Number" = "ZORN26' + t.TAG[:12].upper() + '"\n"IOCalloutDevice" = "/dev/cu.usbmodemHOST305"\n'
    assert receiver.find_port(registry, 'ZORN26' + t.TAG[:12].upper()) and receiver.find_port(registry, 'foreign') is None
    for case in ('success', 'runner failure', 'launch error', 'existing claim', 'bundle rejected'):
        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / 'root-trial'
            out = trial / 'trial'
            out.mkdir(parents=True)
            calls = []
            (out / 'before-log.bin').write_bytes(before_page)
            (out / 'after-log.bin').write_bytes(page)
            if case == 'existing claim':
                (out / 'one-shot.claim.json').write_text('HOST ONLY')
            def validate(path):
                calls.append('validate')
                assert path == trial / 'bundle.json'
                if case == 'bundle rejected':
                    raise ValueError('HOST bad bundle')
            def receive(port, path, stop, deadline):
                assert calls == ['validate', 'registry'] and port == '/dev/cu.usbmodemHOST305'
                calls.append('receive')
                path.write_bytes(wire)
            def run_sub(args, **kwargs):
                if args[0] == '/usr/sbin/ioreg':
                    assert calls == ['validate']
                    calls.append('registry')
                    return SimpleNamespace(returncode=0, stdout=registry)
                assert calls == ['validate', 'registry', 'receive'] and args[2] == str(Path(receiver.__file__).with_name('run-zorn-debug.py'))
                assert args[3:] == ['--ios26-opp305-trial', '--bundle', str(trial / 'bundle.json'), '--admission', str(trial / 'admission.json')]
                calls.append('runner')
                if case == 'launch error':
                    raise OSError('HOST launch failure')
                (out / 'run.json').write_text(json.dumps(dict(
                    scope=t.SCOPE, boot_attempts=1, fastboot_returned_success=True,
                    recovery_identity_after=dict(family='TWRP'),
                )))
                return SimpleNamespace(returncode=int(case == 'runner failure'))
            config = SimpleNamespace(TRIAL=trial, TAG=t.TAG, PROBE_TAG=t.PROBE_TAG,
                                     TIMING_SESSION=t.TIMING_SESSION, SCOPE=t.SCOPE, validate=validate)
            with patch.object(receiver, 'Thread', HostThread), patch.object(receiver, 'capture', receive), patch.object(receiver.subprocess, 'run', run_sub):
                if case in ('existing claim', 'bundle rejected'):
                    try:
                        receiver.run_capture(config)
                    except ValueError:
                        assert calls == ['validate']
                    else:
                        raise AssertionError(case)
                    assert not (out / 'cdc-capture.json').exists()
                else:
                    code = receiver.run_capture(config)
                    x = json.loads((out / 'cdc-capture.json').read_text())
                    assert (code == 0) == (case == 'success') and x['verified'] == (case == 'success')
            checks.append('actual receiver ' + case + ':validation then listener then fixed runner;exclusive output')

    pin = lambda p: dict(path=str(Path(p).resolve()), sha256=t.sha(p))
    (a.out / 'result.json').write_text(json.dumps(dict(
        passed=True, checks=checks, source=pin(receiver.__file__), receiver=pin(receiver.__file__),
        postprocessor=pin(Path(__file__).with_name('zorn_ios26_glass297_capture.py')),
        retained_serial_transport=pin(receiver.TRANSPORT_SOURCE), test_tool=pin(__file__),
        explicit_synthetic_fixtures=True, phone_access=False,
    ), indent=2) + '\n')
    print('PASS305 actual postprocessor/receiver controls; no phone')


if __name__ == '__main__':
    main()
