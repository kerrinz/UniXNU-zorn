#!/usr/bin/env python3
"""Prepare an independent310 archive offline; finalize reusing verified297 root."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import zorn_ios26_gpu_v310_system_trial as t

BOOT_CHECKS = (
    'scroll-io-host310/result.json', 'scroll-camera-host310/result.json',
    'scroll-entry-host310/result.json', 'scroll-archive-host310/result.json',
)


def ready_records(bundle, bundle_path, check_paths):
    pin = lambda p: dict(path=str(p), sha256=t.sha(p))
    binding = dict(scope=t.SCOPE, nonce=t.TAG, bundle_sha256=t.sha(bundle_path),
                   boot_sha256=t.BOOT, allow_boot=True)
    owner = dict(
        binding,
        authorization_source=(
            'Standing owner authorization: only92988a43/zorn/slotA; unattended ordinary-backboardd/scroll310; '
            'protect Android/17/Data. One temporary boot, zero retries, no physical assistance. '
            'Fixed SDK37/ADB5039; fresh Recovery and protections inside runner. '
            'No bootstrap, flash, restore or layout change. '
            'Failure to return verified Recovery stops device operations.'
        ),
    )
    proof = t.load(t.PACKAGE)
    pins = bundle['pins']
    ready = dict(
        binding, host_checks_passed=True, one_boot=True, timeout_seconds=600,
        watchdog_seconds=300, ordinary_timing_session=t.TIMING_SESSION,
        host_checks=[pin(p) for p in check_paths],
        kernel=pin(pins['kernel']['path']), FD=pin(pins['fd']['path']), ADT=pin(pins['ADT']['path']),
        loader=pin(pins['loader']['path']), manager=pin(pins['manager']['path']), menu=pin(pins['menu']['path']),
        root=proof['root'], actual_root_installation=pin(pins['root_install_receipt']['path']),
        actual_install_claim=pin(pins['root_install_claim']['path']),
        local_root_first_page_expectation=pin(pins['root_first_page']['path']),
        firmware_inputs=pin(t.BASE / 'firmware-input-closure310.json'), configuration=proof['boot_args'],
        CPU_page_bytes=16384, GPU_page_bytes=4096, disk_block_bytes=4096,
        storage=dict(
            partition='unixnu', GUID='b279731f-ccad-4ef5-a8b7-e7440cd08de3',
            absolute_LBAs4096=[47271680, 64048895], Android_userdata='sda34 ends at47271679;preserved',
            iPadOS17_root_bytes=9382658048, Data_start=17179869184, Data_end=25770070016,
            Data_read_only=True, root26_relative_LBA4096=6291712, root26_bytes=34359738368,
            root26_read_only=True, gap_after_Data=782336, reserve_after_root=8588886016,
            Recovery_and_boot_partitions_unchanged=True,
        ),
        active_path=(
            'Ordinary backboardd on installed297 root; nominal 578MHz, inherited GPU stack and FT3683 transport. '
            'Bounded virtual Settings scene, actual Hand coordinates/identity, settled framebuffer CDC crop.'
        ),
        expected=(
            'Actual Settings scroll creates new completed frames and visible row movement. '
            'Read seven CRC chunks and preserve the presentation ledger and verified Recovery return.'
        ),
        operator_plan=[
            'Start fixed CDC receiver and camera before one boot',
            'Run one bounded virtual swipe/menu/dismiss/app/scroll scene after live GPU gate',
            'Wait for automatic Recovery and verify all protected readbacks',
        ],
        synthetic_input_enabled=True, human_input_required=False,
        stop_conditions=[
            'Wrong identity/slot/Recovery/tool/GPT/Data/rootpage/BCB/inputs refuses boot',
            'Unknown GPU/DMA state retains resources; no reset/retry/fallback',
            '300s independent WDT; no verified Recovery within 600s stops device operations',
            'Incomplete/foreign/lost logs or uniform/black background cannot qualify blur',
        ],
        logs=dict(
            receiver_first=True, wire_limit=529408, nonterminal_frames=38, terminal_max_bytes=409600,
            SHOT_format=297, SHOT_chunks=7, UI_format=276, panic_raw_only=True,
            native_log_LBA4096=49563392, native_log_blocks=1,
        ),
        camera=dict(
            entry=pin(Path(__file__).with_name('capture-zorn-video310.py')),
            binary=pin(t.SOURCES['camera_binary']), device='USB  Camera', audio=False,
            seconds=320, host_timeout_seconds=380, container='fragmented-MP4 v310-window.*',
        ),
        hardware_only_pending=[
            'Fresh Recovery/92988a43/zorn/slotA/GPT/Data/fullBCB/rootpage inside runner',
            '310 firmware authentication, GMU/HFI, initial task/fence and CPU-visible result',
            'Ordinary backboardd with presenter-unlock298, same-frame menu/widget 104x48 pixels and fence ledger',
            'Two complete 287 scalar/RPC snapshots measuring presenter-unlock latency vs 297',
            'Actual front-app scroll, complete settled crop, visible Settings row movement; physical FT3683 pending',
        ],
    )
    return owner, ready


def publish_admission(bundle, bundle_path, check_paths):
    paths = [t.TRIAL / (name + '.json') for name in ('owner', 'ready', 'admission')]
    t.require(all(not p.exists() and not p.is_symlink() for p in paths), '310 boot admission records already exist')
    for p in check_paths:
        t.require(t.load(p).get('passed') is True, '310 admission host check failed')
    owner, ready = ready_records(bundle, bundle_path, check_paths)
    digest = lambda value: hashlib.sha256((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()).hexdigest()
    admission = dict(scope=t.SCOPE, nonce=t.TAG, bundle_sha256=t.sha(bundle_path), boot_sha256=t.BOOT,
                     allow_boot=True, owner_sha256=digest(owner), ready_sha256=digest(ready))
    t.validate_boot_records(bundle_path, owner, ready, admission, digest(owner), digest(ready))
    from zorn_ios26_logdirs_boot_trial import save
    save(paths[0], owner, True)
    save(paths[1], ready, True)
    save(paths[2], admission, True)
    t.validate_boot_admission(bundle_path, paths[2])


def archive(role, source):
    source = Path(source).resolve()
    target = t.TRIAL / 'archive' / role.replace('/', '_')
    t.require(not target.exists() and not target.is_symlink(), '310 archive exists: ' + role)
    digest = t.sha(source)
    subprocess.run(['/bin/cp', '-c', str(source), str(target)], check=True)
    t.require(not target.samefile(source) and t.sha(target) == digest and t.sha(source) == digest,
              '310 independent archive copy differs: ' + role)
    return dict(path=str(source), archive=str(target), sha256=digest)


def publish_bundle(path, bundle):
    t.require(path == t.TRIAL / 'bundle.json' and not path.exists() and not path.is_symlink(),
              '310 fresh canonical final bundle required')
    t.validate_bundle_contents(bundle)
    from zorn_ios26_logdirs_boot_trial import save
    save(path, bundle, True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--finalize', action='store_true')
    action.add_argument('--admit', action='store_true')
    args = parser.parse_args()
    proof = t.validate_package()
    preparation = t.TRIAL / 'preparation.json'
    if args.admit:
        bundle_path = t.TRIAL / 'bundle.json'
        bundle = t.validate(bundle_path)
        t.require_idle_trial()
        admission_test = t.load(t.BASE / 'scroll-admission-host310/result.json')
        t.require(admission_test['passed'] is True, '310 admission producer regression required')
        for key in ('source', 'prepare_source', 'test_tool'):
            t.pinned(admission_test[key])
        publish_admission(bundle, bundle_path, [t.BASE / n for n in BOOT_CHECKS] +
                          [t.BASE / 'scroll-admission-host310/result.json'])
        print('310 fresh local boot admission prepared; no claim/USB/boot')
        return
    if args.finalize:
        path = t.TRIAL / 'bundle.json'
        t.require(not path.exists() and not path.is_symlink(), '310 bundle already finalized')
        t.validate_installation()
        draft = t.load(preparation)
        t.require(draft['status'] == 'offline-awaiting-local310-finalization' and
                  draft['expected'] == t.EXPECTED, '310 exact preparation required')
        pins = draft['pins']
        for row in pins.values():
            t.pinned(row)
            t.require(t.sha(row['archive']) == row['sha256'], '310 archived preparation changed')
        for role, source in draft['pending_runtime_inputs'].items():
            t.require(Path(source) == t.SOURCES[role], '310 pending path differs')
            pins[role] = archive(role, source)
        bundle = dict(t.EXPECTED, pins=pins)
        publish_bundle(path, bundle)
        t.validate(path)
        print('310 local installed-root bundle finalized; no admission/claim/device access')
        return
    t.TRIAL.mkdir(exist_ok=False)
    (t.TRIAL / 'archive').mkdir()
    (t.TRIAL / 'trial').mkdir()
    sources = dict(t.SOURCES)
    pending = {k: sources.pop(k) for k in ('root_install_receipt', 'root_install_admission', 'root_install_claim')}
    sources.update(
        boot=proof['boot']['path'], FAT=proof['FAT']['path'], package=t.PACKAGE,
        kernel=proof['pins']['kernel']['archive'], ADT=proof['pins']['ADT']['archive'],
        fd=proof['pins']['FD']['archive'], record_identity=t.BASE / 'artifact-identity.json',
    )
    for row in proof['FAT_members']:
        role = {'BOOTAA64.EFI': 'manager', 'DarwinBoot26.efi': 'loader', 'kernel.macho': 'kernel',
                'kernel.macho.adt': 'ADT', 'unixnu.toml': 'menu'}[Path(row['FAT_path']).name]
        sources[role] = row['readback']
    parent = t.STAGE / 'k80-gpu-v277-system-trial-e13cccee337c43fc8020baea055232ae/root-trial/bundle.json'
    baseline = t.load(parent)['pins']
    for role, expected in t.PROTECTED_HASHES.items():
        t.require(baseline[role]['sha256'] == expected, '310 retained protection baseline differs')
        t.pinned(baseline[role])
        sources[role] = baseline[role]['path']
    for role in t.TOOLS:
        t.pinned(baseline[role])
        sources[role] = baseline[role]['path']
    first = t.TRIAL / 'root-first-page310.LOCAL-EXPECTED.bin'
    with Path(proof['root']['image']).open('rb') as stream:
        first.write_bytes(stream.read(4096))
    sources['root_first_page'] = first
    t.require(set(sources) | set(pending) == t.ARTIFACTS | t.PROTECTIONS | t.TOOLS | t.SOURCES.keys(),
              '310 preparation role coverage differs')
    pins = {role: archive(role, source) for role, source in sources.items()}
    from zorn_ios26_logdirs_boot_trial import save
    save(preparation, dict(
        status='offline-awaiting-local310-finalization',
        expected=t.EXPECTED, pins=pins,
        pending_runtime_inputs={k: str(p) for k, p in pending.items()},
        historical_protection_baseline=dict(path=str(parent), sha256=t.sha(parent)),
        root_first_page_scope='Local expectation only;not phone readback',
        root_installation_required=False, system_booted=False, phone_access=False,
        owner_ready_admission_claim_created=False,
    ), True)
    print('310 independent offline preparation archived; installed297 evidence awaiting local finalization; no device access')


if __name__ == '__main__':
    main()
