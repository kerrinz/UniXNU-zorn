#!/usr/bin/env python3
"""285 admission producer/consumer on temporary fixtures; no real boot admission."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

import zorn_ios26_gpu_v285_system_trial as t


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    path = Path(__file__).with_name('prepare-ios26-perf285-trial.py')
    spec = importlib.util.spec_from_file_location('actual_admission_prepare285',path)
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    controller = t.CURRENT.read_bytes()
    real_trial = t.TRIAL
    draft = t.load(real_trial/'preparation.json')
    check_paths = [t.BASE/n for n in prepare.BOOT_CHECKS]
    checks = []
    digest = lambda value: hashlib.sha256((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='SYNTHETIC-admission285-') as temp:
        temp = Path(temp).resolve()
        bundle = dict(t.EXPECTED,pins=copy.deepcopy(draft['pins']),SYNTHETIC_ONLY=True)
        for role in ('root_install_receipt','root_install_admission','root_install_claim'):
            f=temp/(role+'.SYNTHETIC.json');f.write_text('{"SYNTHETIC_ONLY":true}\n')
            bundle['pins'][role]=dict(path=str(f),sha256=t.sha(f))
        bundle_path=temp/'bundle.json';bundle_path.write_text(json.dumps(bundle))
        with patch.object(t,'TRIAL',temp):
            owner,ready=prepare.ready_records(bundle,bundle_path,check_paths)
            assert ready['root']['sha256']==t.ROOT_SHA and ready['hardware_only_pending']
            assert ready['camera']['seconds']==340 and not ready['human_input_required']
            assert ready['storage']['Data_end']<=ready['storage']['root26_relative_LBA4096']*4096
            def admission_for(o,r):
                return dict(scope=t.SCOPE,nonce=t.TAG,bundle_sha256=t.sha(bundle_path),boot_sha256=t.BOOT,
                    allow_boot=True,owner_sha256=digest(o),ready_sha256=digest(r))
            admission=admission_for(owner,ready)
            t.validate_boot_records(bundle_path,owner,ready,admission,digest(owner),digest(ready))
            checks.append('actual ready producer and pure consumer bind full current tuple,storage,logs/camera,stop/Recovery conditions;hardware remains pending')
            cases=[('wrong boot',lambda o,r,a:a.update(boot_sha256='0'*64)),
                ('wrong scope',lambda o,r,a:o.update(scope='foreign')),
                ('repeated boot',lambda o,r,a:r.update(one_boot=False)),
                ('bad timeout',lambda o,r,a:r.update(timeout_seconds=1500)),
                ('WDT disabled',lambda o,r,a:r.update(watchdog_seconds=0)),
                ('hardware conditions removed',lambda o,r,a:r.update(hardware_only_pending=[])),
                ('missing required host check',lambda o,r,a:r['host_checks'].pop()),
                ('boolean allow_boot replaced',lambda o,r,a:a.update(allow_boot=1))]
            for name,change in cases:
                o,r,a=map(copy.deepcopy,(owner,ready,admission));change(o,r,a)
                # Rebind the changed record bytes: failures must be semantic,
                # not merely a stale outer checksum.
                a['owner_sha256'],a['ready_sha256']=digest(o),digest(r)
                try:t.validate_boot_records(bundle_path,o,r,a,digest(o),digest(r))
                except ValueError:checks.append(name+' refused')
                else:raise AssertionError(name)
            try:prepare.publish_admission(bundle,bundle_path,check_paths[:-1])
            except ValueError:
                assert not any((temp/(n+'.json')).exists() for n in ('owner','ready','admission'))
                checks.append('failed semantic validation publishes none of the three records')
            else:raise AssertionError('incomplete checks published')
            prepare.publish_admission(bundle,bundle_path,check_paths)
            t.validate_boot_admission(bundle_path,temp/'admission.json')
            assert not (temp/'trial/one-shot.claim.json').exists()
            try:prepare.publish_admission(bundle,bundle_path,check_paths)
            except ValueError:checks.append('exclusive publication/consumer roundtrip passes;duplicate refuses;no claim')
            else:raise AssertionError('duplicate admission')
        synthetic_current=temp/'current.SYNTHETIC.json'
        for key in ('active_run','active_admission','active_build','runner_session','stop_device_operations'):
            state=dict(gpu_discovery=dict(current_mode='unattended-phone-connected',active_admission=None))
            state[key]=True;synthetic_current.write_text(json.dumps(state))
            with patch.object(t,'CURRENT',synthetic_current),patch.object(t,'TRIAL',temp):
                try:t.require_idle_trial()
                except ValueError:pass
                else:raise AssertionError('busy/stopped '+key)
        checks.append('all five busy/stopped controller conditions refuse before claim')
    command=[] # All positive admissions above are isolated temporary fixtures.
    assert not any((real_trial/(n+'.json')).exists() for n in ('owner','ready','admission','bundle'))
    assert t.CURRENT.read_bytes()==controller
    checks.append('real production admission/bundle/controller remain untouched')
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    report=dict(passed=True,checks=checks,source=pin(t.__file__),prepare_source=pin(path),test_tool=pin(__file__),
        command=command,positive_records_synthetic_temporary_only=True,actual285_root_not_installed_by_host_test=True,
        real_owner_ready_admission_claim_created=False,phone_access=False,full_GPU_qualification=False)
    (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS285 admission producer/consumer '+str(len(checks))+' controls; no real admission/phone access')


if __name__=='__main__':main()
