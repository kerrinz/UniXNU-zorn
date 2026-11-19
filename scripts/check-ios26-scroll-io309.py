#!/usr/bin/env python3
"""309 receiver/postprocessor on explicitly synthetic retained274+menu297 fixtures."""
import argparse, base64, copy, hashlib, json, struct, tempfile, zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import zorn_ios26_scroll309_capture as post
import zorn_ios26_scroll309_receiver as receiver
from zorn_ios26_scroll309_capture import finish_capture
import zorn_ios26_gpu_v309_system_trial as t
from inspect_ios26_ui_menu274 import split_menu
from inspect_ios26_ui_roi270 import split_roi


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--skipped-wire', type=Path, help='actual v309 CDC with unselected actions')
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

    pkt = bytearray((t.BASE / 'capture-mixed-SYNTHETIC309/SYNTHETIC-source276-packet.bin').read_bytes())
    assert len(pkt) == 672 and pkt.startswith(b'K80UI276')
    pkt[8:24] = bytes.fromhex(t.TAG)
    struct.pack_into('<I', pkt, 664, zlib.crc32(pkt[:664]))
    menu = bytes(pkt)

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

    (a.out / 'SYNTHETIC-wire309.bin').write_bytes(wire)
    (a.out / 'SYNTHETIC-page309.bin').write_bytes(page)
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
                assert (out / 'ordinary309-stderr.bin').exists() and (out / 'screen309-settings-scroll.bgrx').exists()
            try:
                finish_capture(out, tag=t.TAG, program_tag=t.PROBE_TAG,
                               timing_session=t.TIMING_SESSION, scope=t.SCOPE, runner_exit=code)
            except FileExistsError:
                pass
            else:
                raise AssertionError('capture overwritten')
            return x

    x = capture()
    assert x['verified'] and x['scroll_capture_with_recovery'] and x['synthetic_settings_scroll_returned_with_recovery']
    assert not x['scalar_timing287']['complete'] and not x['glass_blur_visually_qualified']
    checks.append('actual309 capture completes on explicitly synthetic274menu+menu297+native-page fixture;no hardware qualification')

    if a.skipped_wire:
        from inspect_ios26_scroll309 import UI_MAGIC, UI276_BYTES, inspect_progress

        raw = a.skipped_wire.read_bytes()
        result, _, _ = inspect_progress(raw, t.TAG, t.PROBE_TAG)
        scene = result['synthetic_menu276']
        assert scene['press_outcome'] == 1 and scene['press_attempts'] == 0
        assert result['transport_frames_valid'] and result['menu297']['complete']
        assert not result['synthetic_settings_dispatch_returned276']
        at = raw.index(UI_MAGIC)
        for name, begin, offset in (('dismiss', 64, 5), ('app_tap', 96, 5), ('list_scroll', 128, 6)):
            assert scene[name]['selected'] == 0 and scene[name]['lift_raw'] == 0xffffffff
            packet = bytearray(raw[at:at + UI276_BYTES])
            struct.pack_into('<I', packet, 24 + 4 * (begin + offset), 0xe00002c0)
            struct.pack_into('<I', packet, 664, zlib.crc32(packet[:664]))
            try:
                inspect_progress(raw[:at] + packet + raw[at + UI276_BYTES:], t.TAG, t.PROBE_TAG)
            except ValueError as error:
                assert 'unselected' in str(error)
            else:
                raise AssertionError(f'Unselected action accepted a lift error: {name}')
        checks.append('actual skipped-scene wire accepted; three synthetic skipped-action lift errors refused')

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
        assert not x['verified'] and not x['scroll_capture_with_recovery']
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

    registry = '"idVendor" = 4617\n"idProduct" = 1\n"USB Serial Number" = "ZORN26' + t.TAG[:12].upper() + '"\n"IOCalloutDevice" = "/dev/cu.usbmodemHOST309"\n'
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
                assert calls == ['validate', 'registry'] and port == '/dev/cu.usbmodemHOST309'
                calls.append('receive')
                path.write_bytes(wire)
            def run_sub(args, **kwargs):
                if args[0] == '/usr/sbin/ioreg':
                    assert calls == ['validate']
                    calls.append('registry')
                    return SimpleNamespace(returncode=0, stdout=registry)
                assert calls == ['validate', 'registry', 'receive'] and args[2] == str(Path(receiver.__file__).with_name('run-zorn-debug.py'))
                assert args[3:] == ['--ios26-scroll309-trial', '--bundle', str(trial / 'bundle.json'), '--admission', str(trial / 'admission.json')]
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
        postprocessor=pin(Path(__file__).with_name('zorn_ios26_scroll309_capture.py')),
        retained_serial_transport=pin(receiver.TRANSPORT_SOURCE), test_tool=pin(__file__),
        explicit_synthetic_fixtures=True, phone_access=False,
    ), indent=2) + '\n')
    print('PASS309 actual postprocessor/receiver controls; no phone')


if __name__ == '__main__':
    main()
