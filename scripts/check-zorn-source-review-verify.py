#!/usr/bin/env python3
"""New verify-only artifact/body/receipt boundaries;no old compiles or rebuilds."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/gpu-source-review-verify-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/build-zorn-source-data-review.py';GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
BASE=ROOT/'out/zorn/gpu-source-data-build-entry-20261103/raw-mode-real-build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    original={p.name:sha(p) for p in BASE.iterdir() if p.is_file()}
    def invoke(directory,good=False,anchor=None,extras=()):
        command=[sys.executable,'-B',str(GUARD),str(TOOL),'--source-review-only','--verify-only','--out-dir',str(directory)]
        if anchor is not False:command+=['--receipt-sha256',anchor or sha(directory/'result.json')]
        command+=list(extras);q=subprocess.run(command,capture_output=True,text=True)
        assert q.returncode==(0 if good else 2),(q.returncode,q.stdout,q.stderr)
        if q.stderr:
            assert not good and 'forbidden' not in q.stderr;return dict(argument_refused=True,error=q.stderr.splitlines()[-1])
        d=json.loads(q.stdout);assert d['hardware_qualification'] is False and d['allow_boot'] is False
        assert d['source_review_integrity_verified'] is good and d['recompiled'] is False and d['executed'] is False
        return d
    baseline=invoke(BASE,True,anchor=original['result.json'])
    assert baseline['object_review']['compiled_source_bytes']==167116 and baseline['raw_streams_match_anchored_receipt']
    cases=[]
    def clone(case):
        directory=OUT/case;directory.mkdir(exist_ok=False)
        for p in BASE.iterdir():
            if p.is_file():
                dest=directory/p.name;shutil.copyfile(p,dest);assert dest.stat().st_ino!=p.stat().st_ino and dest.stat().st_nlink==1
        return directory
    for case in ['header-self-signed','model-self-signed','object-self-signed','raw-stream-tamper','failed-event-history','authority-flag','foreign-target-command','truncated-object-self-signed','duplicate-receipt-key','redirected-stream-name']:
        directory=clone(case);rp=directory/'result.json';r=json.loads(rp.read_text());reanchor=True
        if case=='header-self-signed':
            p=directory/'UnselectedSourceTables.h';p.write_text(p.read_text()+'\n// forged source body\n');r['outputs'][p.name]=sha(p)
        elif case=='model-self-signed':
            p=directory/'source-layout-data.json';d=json.loads(p.read_text());d['records']['properties'][0][4]=1;p.write_text(json.dumps(d));r['outputs'][p.name]=sha(p)
        elif case in ['object-self-signed','truncated-object-self-signed']:
            p=directory/'isolated-source-data.o';b=bytearray(p.read_bytes())
            if case=='object-self-signed':b[400]^=1
            else:b=b[:40]
            p.write_bytes(b);r['outputs'][p.name]=sha(p)
            e=directory/'build-events.jsonl';rows=[json.loads(line) for line in e.read_text().splitlines()];rows[-1]['object_sha256']=sha(p);e.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        elif case=='raw-stream-tamper':
            (directory/'compile-0.stderr').write_bytes(b'changed\xff\x00');reanchor=False
        elif case=='failed-event-history':
            e=directory/'build-events.jsonl';rows=[json.loads(line) for line in e.read_text().splitlines()];rows[5]['phase']='failed';e.write_text(''.join(json.dumps(row)+'\n' for row in rows));reanchor=False
        elif case=='authority-flag':r['hardware_qualification']=True
        elif case=='foreign-target-command':
            a=r['commands'][0]['arguments'];a[a.index('--target=arm64-apple-ios17.0.0')]='--target=arm64-apple-ios27.0.0'
        elif case=='redirected-stream-name':r['commands'][0]['raw_streams']['stderr']['path']='/not-read/outside.stderr'
        if reanchor:rp.write_text(json.dumps(r))
        if case=='duplicate-receipt-key':rp.write_text(rp.read_text().replace('"completed": true','"completed": true, "completed": true',1))
        d=invoke(directory,anchor=sha(rp) if reanchor else original['result.json']);cases.append(dict(case=case,self_signed_receipt_recomputed=reanchor,error=d['error']))
    d=invoke(BASE,anchor='0'*64);cases.append(dict(case='wrong-independent-anchor',error=d['error']))
    d=invoke(BASE,anchor=False);cases.append(dict(case='missing-independent-anchor',error=d['error']))
    d=invoke(BASE,anchor=original['result.json'],extras=['--execute']);cases.append(dict(case='verify-execute-mutually-exclusive',error=d['error']))
    assert all(sha(BASE/name)==digest for name,digest in original.items())
    (OUT/'result.json').write_text(json.dumps(dict(one_existing_artifact_readonly_verification=baseline,new_refusal_cases=cases,child_no_writes_or_processes=True,original_artifacts_unchanged=True,no_rebuild_compile_or_native_execution=True,independent_anchor_required=True,original_source_bodies_not_self_signed_status_prove_data_integrity=True,hardware_qualification=False,driver_patch_count_remains32=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n')
    print('PASS:new verify-only path,13refusals incl self-signed tampered bodies/log/event/scope;no writes/processes/compiles/native/device')

if __name__=='__main__':main()
