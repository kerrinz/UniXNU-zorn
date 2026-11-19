#!/usr/bin/env python3
"""287 local finalization and all248 readback groups, using explicit test fixtures.

Actual current root/boot/source inputs are used. Installation records and
readbacks are synthetic in temporary directories; no hardware grade is earned.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

import zorn_ios26_gpu_v287_system_trial as t
import zorn_ios26_metal_root_delta as installer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    prepare_source = Path(__file__).with_name('prepare-ios26-perf287-trial.py')
    spec = importlib.util.spec_from_file_location('actual_prepare287', prepare_source)
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    state_before = t.CURRENT.read_bytes()
    real_preparation = t.TRIAL / 'preparation.json'
    preparation_before = real_preparation.read_bytes()
    draft = json.loads(preparation_before)
    review = installer.validate_review(t.REVIEW, installer.INSTALLS[installer.RPC287_FLAG])
    plan = installer.reviewed_module(review, 'plan_source', 'known287_finalization_plan')
    _, parts, retained = plan.load_plan()
    checks = []
    with tempfile.TemporaryDirectory(prefix='SYNTHETIC-known287-') as temp:
        # macOS /var is a symlink; production bundles use canonical paths.
        temp = Path(temp).resolve()
        reads = temp / 'SYNTHETIC-readbacks'
        reads.mkdir()
        for block, old, new in parts:
            (reads/f'delta-{block:07}.before.bin').write_bytes(old)
            (reads/f'delta-{block:07}.after.bin').write_bytes(new)
        (reads/'prior-root-changed-pages.before.bin').write_bytes(b''.join(raw for _,raw in retained))
        for name, source in [('primary_GPT','primary_GPT'),('backup_GPT','backup_GPT'),
                             ('root_manifest','root_manifest'),('Data','Data_metadata'),
                             ('before','root_before'),('after','root_after')]:
            data = Path(draft['pins'][source]['path']).read_bytes()
            for phase in ('before','after'):
                (reads/(name+'.'+phase+'.bin')).write_bytes(data)
        misc = Path(review['pins']['previous_misc']['path']).read_bytes()
        for name, data in [('log',bytes(4096)),('misc',misc)]:
            for phase in ('before','after'):
                (reads/(name+'.'+phase+'.bin')).write_bytes(data)
        t.verify_install_readbacks(reads, parts, retained, misc)
        checks.append('all248 groups/11724 exact old+new pages and13741 retained pages checked with actual reviewed plan;fixture bytes synthetic')
        changes = [('first old page', reads/f'delta-{parts[0][0]:07}.before.bin'),
                   ('last new page', reads/f'delta-{parts[-1][0]:07}.after.bin'),
                   ('prior retained pages', reads/'prior-root-changed-pages.before.bin'),
                   ('protected Data', reads/'Data.after.bin'),
                   ('protected BCB tail', reads/'misc.after.bin')]
        for name, file in changes:
            saved = file.read_bytes()
            bad = bytearray(saved)
            bad[-1] ^= 1
            file.write_bytes(bad)
            try:
                t.verify_install_readbacks(reads, parts, retained, misc)
            except ValueError:
                checks.append(name+' corruption refused')
            else:
                raise AssertionError(name)
            finally:
                file.write_bytes(saved)
        extra = reads/'delta-9999999.after.bin'
        extra.write_bytes(bytes(4096))
        try:
            t.verify_install_readbacks(reads, parts, retained, misc)
        except ValueError:
            checks.append('extra unreviewed readback group refused')
        else:
            raise AssertionError('extra group')
        extra.unlink()
        missing = reads/f'delta-{parts[-1][0]:07}.after.bin'
        saved = missing.read_bytes()
        missing.unlink()
        try:
            t.verify_install_readbacks(reads, parts, retained, misc)
        except ValueError:
            checks.append('missing final group refused')
        else:
            raise AssertionError('missing group')
        missing.write_bytes(saved)

        # Exercise the real installation verifier against a fully labelled
        # synthetic envelope plus the actual plan bytes, not a success stub.
        adm = temp/'SYNTHETIC-admission'
        adm.mkdir()
        installed_sources = dict(t.SOURCES)
        installed_sources.update(root_install_receipt=reads/'result.SYNTHETIC.json',
            root_install_admission=adm/'admission.json', root_install_claim=reads/'claim.SYNTHETIC.json')
        required = dict(scope='K80-persistent-iOS26-rpc287-b6847f4e',review_sha256=t.REVIEW_SHA,
            serial='92988a43',product='zorn',slot='a',partition='unixnu',relative_first_lba=6291712,
            old_root_sha256=review['window']['old_root_sha256'],new_root_sha256=t.ROOT_SHA,
            blocks=8388608,changed_pages=11724,write_groups=248,timeout_seconds=600,retries=0,
            allow_install=True,allow_boot=False,full_phone_root_readback=False,layout_change=False,
            entry_sha256=t.sha(t.SOURCES['root_install_entry']),runner_sha256=t.sha(t.SOURCES['root_install_runner']))
        def write(path, data):
            path.write_text(json.dumps(dict(data,SYNTHETIC_ONLY=True)))
        admission = dict(required)
        for role,flag in [('owner','approved'),('ready','ready')]:
            path = adm/(role+'.json')
            write(path,dict(required,**{flag:True}))
            admission[role]=dict(path=str(path),sha256=t.sha(path))
        write(installed_sources['root_install_admission'],admission)
        claim = dict(scope=required['scope'],admission_sha256=t.sha(installed_sources['root_install_admission']),
                     consumed_before_first_USB=True,reusable=False)
        write(installed_sources['root_install_claim'],claim)
        receipt = dict(scope=required['scope'],installed=True,booted=False,protected_metadata_and_fences_unchanged=True,
            phase='root-delta-installed-written-blocks-readback-verified',pages_written=11724,expected_image_sha256=t.ROOT_SHA,
            readback=dict(scope='written4KiB-root-pages-only',blocks=11724,bytes=48021504,
                          sha256='6714a0cb1c85c82374d27675416119e0b3f51dfd8b5a7e642cbd3a24afc3e1c9'),
            last_verified_group=247,last_verified_block=parts[-1][0],
            recovery_identity_before=dict(family='TWRP'),recovery_identity_after=dict(family='TWRP'))
        write(installed_sources['root_install_receipt'],receipt)
        synthetic_current=temp/'current.SYNTHETIC.json'
        write(synthetic_current,dict(gpu_discovery=dict(current_phone_root_expected_sha256=t.ROOT_SHA)))
        with patch.object(t,'SOURCES',installed_sources),patch.object(t,'CURRENT',synthetic_current):
            t.validate_installation()
            checks.append('real installation verifier validates complete synthetic admission/owner/ready/claim/readbacks;no success stub')
            for name,file,bad in [
                ('reusable claim',installed_sources['root_install_claim'],dict(claim,reusable=True)),
                ('stale admission binding',installed_sources['root_install_claim'],dict(claim,admission_sha256='0'*64)),
                ('incomplete last group',installed_sources['root_install_receipt'],dict(receipt,last_verified_group=9)),
                ('wrong last block',installed_sources['root_install_receipt'],dict(receipt,last_verified_block=0)),
            ]:
                saved=file.read_bytes();write(file,bad)
                try:t.validate_installation()
                except ValueError:checks.append(name+' refused by real installation verifier')
                else:raise AssertionError(name)
                finally:file.write_bytes(saved)

        trial = temp/'SYNTHETIC-trial'
        trial.mkdir()
        (trial/'archive').mkdir()
        sources = {role:Path(row['path']) for role,row in draft['pins'].items()}
        fixed = dict(t.SOURCES)
        for name in ('root_install_receipt','root_install_admission','root_install_claim'):
            f = temp/(name+'.SYNTHETIC-ONLY.json')
            f.write_text(json.dumps(dict(SYNTHETIC_ONLY=True, hardware_qualified=False)))
            fixed[name] = f
        sources.update(fixed)
        pins = {}
        for role, source in sources.items():
            source = source.resolve()
            target = trial/'archive'/role.replace('/','_')
            subprocess.run(['/bin/cp','-c',str(source),str(target)],check=True)
            pins[role] = dict(path=str(source),archive=str(target),sha256=t.sha(source))
        bundle = dict(t.EXPECTED, pins=pins)
        with patch.object(t,'TRIAL',trial), patch.object(t,'SOURCES',fixed):
            assert t.validate_bundle_contents(bundle) == bundle
            checks.append('actual local bundle-content validator passes complete current kernel/boot/FAT/menu/ADT/tools/protection/archive closure;installation not inferred')
            final = trial/'bundle.json'
            bad = copy.deepcopy(bundle)
            bad['root_read_only'] = False
            try:
                prepare.publish_bundle(final,bad)
            except ValueError:
                assert not final.exists()
                checks.append('failed final content check leaves no canonical bundle')
            else:
                raise AssertionError('bad final bundle')
            target = Path(pins['kernel']['archive'])
            original = target.read_bytes()
            target.write_bytes(original+b'HOST-CORRUPTION')
            try:
                prepare.publish_bundle(final,bundle)
            except ValueError:
                assert not final.exists()
                checks.append('corrupt independent kernel archive leaves no canonical bundle')
            else:
                raise AssertionError('archive corruption')
            target.write_bytes(original)
            prepare.publish_bundle(final,bundle)
            assert json.loads(final.read_text()) == bundle and bundle['allow_boot'] is False
            try:
                prepare.publish_bundle(final,bundle)
            except ValueError:
                checks.append('local-only finalization writes after validation and refuses overwrite')
            else:
                raise AssertionError('bundle overwritten')
    assert t.CURRENT.read_bytes() == state_before
    assert real_preparation.read_bytes() == preparation_before
    assert not (t.TRIAL/'bundle.json').exists()
    assert not (t.TRIAL/'trial/one-shot.claim.json').exists()
    def pin(p):
        p = Path(p).resolve()
        return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    report = dict(passed=True,checks=checks,source=pin(t.__file__),prepare_source=pin(prepare_source),
                  test_tool=pin(__file__),review=pin(t.REVIEW),
                  actual_current_native_inputs_and_carrier_checked=True,
                  synthetic_installation_records_and_readbacks_in_temporary_directory_only=True,
                  installation_validation_not_bypassed_in_production=True,
                  real_preparation_and_controller_unchanged=True,phone_access=False,
                  real_bundle_or_admission_or_claim_created=False,full_GPU_qualification=False)
    (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS287 full local finalization/readback controls '+str(len(checks))+'; no phone access')


if __name__ == '__main__':
    main()
