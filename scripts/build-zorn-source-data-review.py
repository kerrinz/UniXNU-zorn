#!/usr/bin/env python3
"""Build only approved unselected source-data review artifacts;default is plan-only."""
import argparse
import hashlib
import json
import runpy
import struct
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PINNED={
 'emitter':(ROOT/'UniXNU-zorn/scripts/emit-zorn-unselected-source-data.py','97596eec625720faf6eff1860f9af6aad7146cc0c56a99d3daf995202ec05b5a'),
 'object_check':(ROOT/'UniXNU-zorn/scripts/check-zorn-source-data-object.py','f7a0e1a1f9830354cc708cd0eb6e345657ad503bca680300bb636f76ab548cfc'),
 'approval':(ROOT/'out/zorn/gpu-source-layout-review/owner-scope-approval.json','4eacf9778c333a97f02af638c145c83f638d2eb51b5b35595116c333eb82a7c9'),
 'object_template':(ROOT/'out/zorn/gpu-source-layout-review/source-layout-object.cpp','f70f19c77a719531c34b22007d04464e35d0e701af371651d5957272c99c4d7b'),
 'clang':(Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'),'1590ac950a3d627817d09ade5cb60b2115f17a72182a3141e010b4bcc482a0c9'),
}
MANIFEST=ROOT/'out/zorn/gpu-power-source-compare-20261103/inputs.json'
MANIFEST_SHA='a8b6cb3aa94ca8214e0ba20e9b6ba886de6707f3ddfba60f5a1244912f914e88'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def preflight(out_dir,manifest=MANIFEST,approval=None,verifying=False):
    """Validate fixed source scope fully before creating output or spawning clang."""
    root=ROOT/'out/zorn';out=out_dir.resolve()
    if not out.is_relative_to(root.resolve()) or out==root.resolve():raise ValueError('output must be an isolated project out/zorn subdirectory')
    if out_dir.is_symlink():raise ValueError('review directory cannot be a symlink')
    if verifying:
        if not out.is_dir():raise ValueError('existing source-review directory required')
    elif out_dir.exists():raise ValueError('output already exists;never overwrite a prior review')
    if not out.parent.is_dir():raise ValueError('output parent must already exist')
    for parent in [out.parent,*out.parents]:
        if parent==root:break
        if not verifying and (parent/'archive.json').exists():raise ValueError('output cannot modify a sealed capsule')
    dependencies={}
    for key,(path,digest) in PINNED.items():
        # Archived data verification neither executes nor needs a live compiler.
        if verifying and key=='clang':continue
        if key=='approval' and approval is not None:path=approval
        raw=path.read_bytes()
        if sha(raw)!=digest:raise ValueError('pinned '+key+' identity mismatch')
        dependencies[str(path)]=digest
    raw=manifest.read_bytes()
    if sha(raw)!=MANIFEST_SHA:raise ValueError('only the approved four-source manifest is allowed')
    emitter=runpy.run_path(str(PINNED['emitter'][0]))
    receipt=json.loads((approval or PINNED['approval'][0]).read_text(),object_pairs_hook=emitter['unique'])
    if receipt.get('owner_reply')!='允许' or receipt.get('manifest_sha256')!=MANIFEST_SHA or receipt.get('new_device_activation_authorized') is not False:
        raise ValueError('narrow source-layout approval required;no device authority')
    doc=json.loads(raw,object_pairs_hook=emitter['unique']);model=emitter['collect'](doc)
    dependencies[str(manifest)]=MANIFEST_SHA
    for source in doc['sources']:
        dependencies[source['dtb']]=source['dtb_sha256'];dependencies[source['graph_json']]=source['graph_sha256']
    content={
        'UnselectedSourceTables.h':emitter['render'](model),
        'source-layout-check.cpp':emitter['CHECK_CPP'],
        'source-layout-object.cpp':PINNED['object_template'][0].read_text(),
        'source-layout-data.json':json.dumps(dict(records=model,manifest_sha256=MANIFEST_SHA,generated_policy=False,any_source_selected=False,hardware_qualification=False),indent=2)+'\n',
    }
    # The frozen template is a source-only compile fixture for this exact model.
    expected_counts={'sources':4,'nodes':340,'properties':2298,'optional_fields':1392,'tables':16,'entries':192,'gmu_tables':4,'gmu_pairs':8,'text_bytes':71952,'property_bytes':16724}
    if {k:len(v) for k,v in model.items()}!=expected_counts:raise ValueError('approved model no longer matches isolated object template')
    common=[str(PINNED['clang'][0]),'-std=c++17','-ffreestanding','-fno-exceptions','-fno-rtti','-nostdinc','-nostdinc++','--target=arm64-apple-ios17.0.0','-Wall','-Wextra','-Werror','-pedantic']
    commands=[common+['-fsyntax-only',str(out/'source-layout-check.cpp')],common+['-O2','-c',str(out/'source-layout-object.cpp'),'-o',str(out/'isolated-source-data.o')]]
    plan=dict(mode='source-review-only',default_execution=False,out_dir=str(out),inputs=dependencies,
              output_content_SHA={name:sha(value.encode()) for name,value in content.items()},commands=commands,
              generated_policy=False,any_source_selected=False,hardware_qualification=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    return plan,content,model


def expected_bytes(model):
    keys=['sources','nodes','properties','optional_fields','tables','entries','gmu_tables','gmu_pairs']
    data=b''.join(struct.pack('<'+'I'*len(row),*row) for key in keys for row in model[key])+bytes(model['text_bytes'])+bytes(model['property_bytes'])
    return data+bytes(-len(data)%4)


def verify_review(plan,content,model,receipt_sha256):
    """Read local artifact bodies against raw source,never trust a success flag alone."""
    out=Path(plan['out_dir'])
    def read(name):
        path=out/name
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink!=1:
            raise ValueError('regular independent local artifact required: '+name)
        return path.read_bytes()
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate review JSON key')
            result[key]=value
        return result
    raw=read('result.json')
    if len(raw)>16*1024*1024:raise ValueError('review result reader bound')
    if sha(raw)!=receipt_sha256:raise ValueError('independent review receipt SHA mismatch')
    result=json.loads(raw,object_pairs_hook=unique)
    if not isinstance(result,dict) or result.get('completed') is not True:
        raise ValueError('review is not recorded complete')
    for key in ['generated_policy','any_source_selected','hardware_qualification','native_execution','allow_boot','readback_qualified']:
        if result.get(key) is not False:raise ValueError('review scope flag differs: '+key)
    if type(result.get('WriteAuthorized')) is not int or result['WriteAuthorized']!=0:
        raise ValueError('review cannot carry write authority')
    expected_names={*content,'isolated-source-data.o'}
    if not isinstance(result.get('outputs'),dict) or set(result['outputs'])!=expected_names:
        raise ValueError('exact source-only output set required')
    for name,text in content.items():
        if read(name)!=text.encode():raise ValueError('artifact differs from original-source reconstruction: '+name)
    for name,digest in result['outputs'].items():
        if sha(read(name))!=digest:raise ValueError('artifact receipt SHA mismatch: '+name)
    checker=runpy.run_path(str(PINNED['object_check'][0]))['inspect']
    object_bytes=read('isolated-source-data.o')
    review=checker(object_bytes,expected_bytes(model))
    def same_command(actual,expected):
        if not isinstance(actual,list) or len(actual)!=len(expected):return False
        for a,b in zip(actual,expected):
            if not isinstance(a,str):return False
            # Archive copies may move. Only filenames at the known output slots
            # relocate;all compiler flags and the executable remain exact.
            if b.startswith(str(out)+'/'):
                if not Path(a).is_absolute() or Path(a).name!=Path(b).name:return False
            elif a!=b:return False
        return True
    commands=result.get('commands')
    if not isinstance(commands,list) or len(commands)!=2:raise ValueError('two compile records required')
    for index,command in enumerate(commands):
        if not isinstance(command,dict) or type(command.get('returncode')) is not int or command['returncode']!=0:
            raise ValueError('compile record is incomplete/failed')
        if command.get('timeout') or command.get('spawn_error') or not same_command(command.get('arguments'),plan['commands'][index]):
            raise ValueError('compile command or failure state differs')
        streams=command.get('raw_streams')
        if not isinstance(streams,dict) or set(streams)!={'stdout','stderr','log'}:
            raise ValueError('raw stream records required')
        bodies={}
        for key,record in streams.items():
            name='compile-'+str(index)+'.'+key
            if not isinstance(record,dict) or not isinstance(record.get('path'),str) or Path(record['path']).name!=name:
                raise ValueError('raw stream filename mismatch')
            # Never follow caller-supplied absolute paths from the receipt.
            body=read(name);bodies[key]=body
            if type(record.get('bytes')) is not int or len(body)!=record['bytes'] or sha(body)!=record.get('sha256'):
                raise ValueError('raw stream content mismatch: '+name)
        if bodies['log']!=bodies['stdout']+bodies['stderr']:
            raise ValueError('combined log differs from raw streams')
    events=[json.loads(line,object_pairs_hook=unique) for line in read('build-events.jsonl').splitlines()]
    phases=['created','source-data-written','compile-start','compile-return','compile-start','compile-return','complete']
    if any(not isinstance(event,dict) for event in events) or [event.get('phase') for event in events]!=phases:
        raise ValueError('build event sequence is incomplete or failed')
    for index,start in enumerate([2,4]):
        event=events[start];returned=events[start+1]
        if event.get('index')!=index or not same_command(event.get('command'),plan['commands'][index]) or returned.get('index')!=index or type(returned.get('returncode')) is not int or returned['returncode']!=0:
            raise ValueError('build events differ from compile records')
    if events[-1].get('object_sha256')!=sha(object_bytes):raise ValueError('final event object identity mismatch')
    return dict(source_review_integrity_verified=True,recompiled=False,executed=False,
                original_source_reconstructed=True,raw_streams_match_anchored_receipt=True,object_review=review,
                scope='source artifact integrity only;not trusted compiler execution or GPU hardware qualification',
                generated_policy=False,hardware_qualification=False,native_execution=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)


def execute_build(plan,content,model,runner=None):
    """Preserve partial files and raw failure logs;never report a partial build complete."""
    out=Path(plan['out_dir']);out.mkdir(exist_ok=False)
    events=out/'build-events.jsonl'
    with events.open('x') as f:f.write(json.dumps(dict(phase='created',source_review_only=True))+'\n')
    def event(**data):
        with events.open('a') as f:f.write(json.dumps(data)+'\n')
    result=dict(completed=False,scope='isolated unselected source-data review only',commands=[],
                generated_policy=False,any_source_selected=False,hardware_qualification=False,native_execution=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    try:
        for path,digest in plan['inputs'].items():
            if sha(Path(path).read_bytes())!=digest:raise ValueError('input changed after preflight: '+path)
        for name,text in content.items():
            with (out/name).open('x') as f:f.write(text)
        event(phase='source-data-written')
        for index,command in enumerate(plan['commands']):
            for name,digest in plan['output_content_SHA'].items():
                if sha((out/name).read_bytes())!=digest:raise ValueError('generated input changed before compile: '+name)
            event(phase='compile-start',index=index,command=command)
            log=out/('compile-'+str(index)+'.log')
            def save_raw(stdout,stderr):
                stdout,stderr=stdout or b'',stderr or b''
                if not isinstance(stdout,bytes) or not isinstance(stderr,bytes):raise TypeError('expected raw compiler byte streams')
                streams={}
                for suffix,raw in [('stdout',stdout),('stderr',stderr),('log',stdout+stderr)]:
                    path=out/('compile-'+str(index)+'.'+suffix)
                    with path.open('xb') as f:f.write(raw)
                    streams[suffix]=dict(path=str(path),sha256=sha(raw),bytes=len(raw))
                return streams
            try:
                q=(runner or subprocess.run)(command,capture_output=True,text=False,timeout=30)
            except subprocess.TimeoutExpired as exc:
                streams=save_raw(exc.stdout,exc.stderr)
                result['commands'].append(dict(arguments=command,returncode=None,timeout=True,log=str(log),raw_streams=streams))
                event(phase='compile-timeout',index=index)
                raise
            except OSError as exc:
                with log.open('x') as f:f.write(str(exc)+'\n')
                result['commands'].append(dict(arguments=command,returncode=None,spawn_error=str(exc),log=str(log)))
                event(phase='compile-spawn-failed',index=index,error=str(exc))
                raise
            streams=save_raw(q.stdout,q.stderr)
            result['commands'].append(dict(arguments=command,returncode=q.returncode,log=str(log),raw_streams=streams))
            event(phase='compile-return',index=index,returncode=q.returncode)
            if q.returncode:raise ValueError('source-only compiler returned '+str(q.returncode))
        checker=runpy.run_path(str(PINNED['object_check'][0]))['inspect']
        result['object_review']=checker((out/'isolated-source-data.o').read_bytes(),expected_bytes(model))
        for name,digest in plan['output_content_SHA'].items():
            if sha((out/name).read_bytes())!=digest:raise ValueError('generated input changed during compile: '+name)
        result.update(completed=True,outputs={name:sha((out/name).read_bytes()) for name in [*content,'isolated-source-data.o']})
        event(phase='complete',object_sha256=result['outputs']['isolated-source-data.o'])
    except (ValueError,TypeError,OSError,subprocess.SubprocessError) as exc:
        result['error']=str(exc)
        try:event(phase='failed',error=str(exc))
        except OSError as log_error:result['event_record_error']=str(log_error)
        result['partial_outputs_preserved']=[p.name for p in out.iterdir() if p.is_file()]
    try:
        with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    except OSError as exc:
        result.update(completed=False,result_record_error=str(exc))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-review-only',action='store_true',required=True)
    action=p.add_mutually_exclusive_group()
    action.add_argument('--execute',action='store_true',help='explicitly emit/compile data-only review artifacts;default prints plan only')
    action.add_argument('--verify-only',action='store_true',help='read existing artifact bodies against original source;no writes/processes/rebuild')
    p.add_argument('--out-dir',type=Path,required=True);p.add_argument('--inputs',type=Path,default=MANIFEST)
    p.add_argument('--approval',type=Path);p.add_argument('--os',choices=['17'],default='17');p.add_argument('--target',choices=['ios'],default='ios')
    p.add_argument('--receipt-sha256',help='independently retained result.json SHA;required only for --verify-only')
    a=p.parse_args()
    if a.verify_only and not a.receipt_sha256:p.error('--verify-only requires independently retained --receipt-sha256')
    if a.receipt_sha256 and not a.verify_only:p.error('--receipt-sha256 requires --verify-only')
    try:
        plan,content,model=preflight(a.out_dir,a.inputs,a.approval,verifying=a.verify_only)
        if a.verify_only:
            print(json.dumps(verify_review(plan,content,model,a.receipt_sha256),indent=2));return 0
        if not a.execute:print(json.dumps(dict(planned=True,executed=False,**plan),indent=2));return 0
        result=execute_build(plan,content,model)
    except (ValueError,TypeError,OSError,struct.error) as exc:
        failure=dict(completed=False,error=str(exc),generated_policy=False,hardware_qualification=False,allow_boot=False,WriteAuthorized=0)
        if a.verify_only:failure.update(source_review_integrity_verified=False,recompiled=False,executed=False)
        print(json.dumps(failure));return 2
    print(json.dumps(result,indent=2));return 0 if result['completed'] else 2


if __name__=='__main__':raise SystemExit(main())
