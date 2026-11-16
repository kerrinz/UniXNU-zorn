#!/usr/bin/env python3
"""New verify-only artifact read budgets;no old suite,compile or native execution."""
from pathlib import Path
import argparse,difflib,hashlib,json,shutil,subprocess,sys

R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
S=R/'UniXNU-zorn/scripts/build-zorn-source-data-review.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
original=S.read_text();original_SHA=sha(S);(O/'original.py.txt').write_text(original)
candidate=original.replace('    def read(name):\n', '    def read(name,limit):\n',1)
candidate=candidate.replace('        return path.read_bytes()\n', "        with path.open('rb') as stream:body=stream.read(limit+1)\n        if len(body)>limit:raise ValueError('review artifact reader bound: '+name)\n        return body\n",1)
candidate=candidate.replace("    raw=read('result.json')\n    if len(raw)>16*1024*1024:raise ValueError('review result reader bound')", "    # Explicit offline work budgets,not target memory geometry or authority.\n    object_limit=16*1024*1024\n    event_limit=1024*1024\n    raw=read('result.json',16*1024*1024)")
candidate=candidate.replace("        if read(name)!=text.encode():", "        if read(name,len(text.encode()))!=text.encode():")
candidate=candidate.replace("        if sha(read(name))!=digest:", "        limit=len(content[name].encode()) if name in content else object_limit\n        if sha(read(name,limit))!=digest:")
candidate=candidate.replace("    object_bytes=read('isolated-source-data.o')", "    object_bytes=read('isolated-source-data.o',object_limit)")
candidate=candidate.replace("            body=read(name);bodies[key]=body", "            limit=record.get('bytes')\n            maximum=(16 if key=='log' else 8)*1024*1024\n            if type(limit) is not int or not 0<=limit<=maximum:\n                raise ValueError('raw stream byte budget: '+name)\n            body=read(name,limit);bodies[key]=body")
candidate=candidate.replace("read('build-events.jsonl').splitlines()", "read('build-events.jsonl',event_limit).splitlines()")
assert candidate!=original and 'read(name)' not in candidate[candidate.index('def verify_review'):candidate.index('def execute_build')]
(O/'review-artifact-bounds.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/scripts/'+S.name,tofile='b/scripts/'+S.name)))
M=O/'mirror';T=M/'UniXNU-zorn/scripts';T.mkdir(parents=True);C=T/S.name;C.write_text(candidate)
dependencies=['UniXNU-zorn/scripts/emit-zorn-unselected-source-data.py','UniXNU-zorn/scripts/check-zorn-source-data-object.py',
 'UniXNU-zorn/scripts/read-zorn-gpu-power-source.py','UniXNU-zorn/scripts/verify-zorn-gpu-reference-source.py',
 'UniXNU-zorn/scripts/verify-zorn-gpu-source-provenance.py','UniXNU-zorn/scripts/inspect-zorn-gpu-overlay-inputs.py',
 'UniXNU/scripts/unixnu/__init__.py','UniXNU/scripts/unixnu/devicetree.py','UniXNU/scripts/unixnu/util.py',
 'out/zorn/gpu-source-layout-review/owner-scope-approval.json','out/zorn/gpu-source-layout-review/source-layout-object.cpp',
 'out/zorn/gpu-power-source-compare-20261103/inputs.json','out/zorn/gpu-votes-source-identity-20261103/candidate.py']
for rel in dependencies:
 p=R/rel;q=M/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);assert sha(p)==sha(q)
BASE=R/'out/zorn/gpu-source-data-build-entry-20261103/raw-mode-real-build'
baseline_SHA={p.name:sha(p) for p in BASE.iterdir() if p.is_file()}
cases=M/'out/zorn/read-bound-cases';cases.mkdir()
def clone(name):
 d=cases/name;d.mkdir()
 for p in BASE.iterdir():
  if p.is_file():
   q=d/p.name;shutil.copyfile(p,q);assert q.stat().st_ino!=p.stat().st_ino and q.stat().st_nlink==1
 return d
wrapper='''from pathlib import Path
import sys,runpy,json
script=Path(sys.argv[1]);args=sys.argv[2:];out=Path(args[args.index('--out-dir')+1]).resolve();real_open=Path.open;events=[]
class Observed:
 def __init__(self,stream,path):self.stream=stream;self.path=path
 def __enter__(self):return self
 def __exit__(self,*a):return self.stream.__exit__(*a)
 def read(self,n=-1):
  body=self.stream.read(n);events.append(dict(name=Path(self.path).name,requested=n,returned=len(body)));return body
def opened(path,*a,**k):
 stream=real_open(path,*a,**k);p=path.resolve();return Observed(stream,str(p)) if p.parent==out else stream
Path.open=opened;sys.argv=[str(script),*args];code=0
try:runpy.run_path(str(script),run_name='__main__')
except SystemExit as e:code=e.code
finally:Path.open=real_open;print(json.dumps(events),file=sys.stderr)
raise SystemExit(code)
'''
(O/'trace-verify.py').write_text(wrapper)
guard=R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py';events=[]
def invoke(tool,d,name):
 cmd=[sys.executable,'-B',str(guard),str(O/'trace-verify.py'),str(tool),'--source-review-only','--verify-only','--out-dir',str(d),'--receipt-sha256',sha(d/'result.json')]
 p=subprocess.run(cmd,capture_output=True);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr)
 events.append(dict(name=name,command=cmd,returncode=p.returncode));save(O/'events.json',events)
 assert p.returncode in (0,2),p.stderr
 return p.returncode,json.loads(p.stdout),json.loads(p.stderr)
good=clone('unchanged-copy');code,expected,_=invoke(S,good,'baseline-original');acode,actual,trace=invoke(C,good,'baseline-candidate')
assert code==acode==0 and actual==expected and actual['recompiled'] is False and actual['executed'] is False
assert all(t['requested']>=1 for t in trace)
refusals=[]
for name,file,size in [('receipt','result.json',16*1024*1024+4096),
                       ('source-body','UnselectedSourceTables.h',(BASE/'UnselectedSourceTables.h').stat().st_size+4096),
                       ('object','isolated-source-data.o',16*1024*1024+4096),
                       ('raw-stream','compile-0.stderr',16*1024*1024+4096),
                       ('events','build-events.jsonl',1024*1024+4096)]:
 d=clone(name)
 with (d/file).open('wb') as f:f.truncate(size)
 bc,b,bt=invoke(S,d,'before-'+name);ac,a,at=invoke(C,d,'after-'+name)
 assert bc==ac==2 and a['error']=='review artifact reader bound: '+file
 old_reads=[x for x in bt if x['name']==file];new_reads=[x for x in at if x['name']==file]
 assert old_reads and old_reads[0]['requested']==-1 and old_reads[0]['returned']==size
 assert new_reads and new_reads[0]['requested']<size and new_reads[0]['returned']==new_reads[0]['requested']
 assert not a['source_review_integrity_verified'] and not a['recompiled'] and not a['executed']
 refusals.append(dict(case=name,original_error=b['error'],candidate_error=a['error'],before=old_reads,after=new_reads))
# Independent receipt anchors are test inputs,not claims of successful compilation.
# Anchored absurd stream lengths must be refused before opening the stream body.
metadata=[]
for label,value in [('negative',-1),('bool',True),('too-large',8*1024*1024+1)]:
 d=clone('stream-'+label);rp=d/'result.json';r=json.loads(rp.read_text());r['commands'][0]['raw_streams']['stderr']['bytes']=value;save(rp,r)
 code,out,trace=invoke(C,d,'stream-'+label)
 assert code==2 and out['error']=='raw stream byte budget: compile-0.stderr'
 assert not any(t['name']=='compile-0.stderr' for t in trace)
 metadata.append(label)
# The limit is inclusive,not a stat-based cap: a valid anchored receipt padded
# exactly to the result budget still verifies without recompiling anything.
d=clone('exact-result');rp=d/'result.json';raw=rp.read_bytes();rp.write_bytes(raw+b' '*(16*1024*1024-len(raw)))
code,out,trace=invoke(C,d,'exact-result');assert code==0 and out==expected
assert next(x for x in trace if x['name']=='result.json')['returned']==16*1024*1024
# Preserve raw non-UTF8 and NUL bytes without introducing text decoding.
d=clone('raw-byte-preservation');rp=d/'result.json';r=json.loads(rp.read_text())
for suffix,body in [('stdout',b'\xff\x00'),('stderr',b'\x80\r\n'),('log',b'\xff\x00\x80\r\n')]:
 p=d/('compile-0.'+suffix);p.write_bytes(body);record=r['commands'][0]['raw_streams'][suffix];record.update(bytes=len(body),sha256=sha(p))
save(rp,r);code,out,trace=invoke(C,d,'raw-byte-preservation');assert code==0 and out==expected
assert sha(S)==original_SHA and all(sha(BASE/name)==digest for name,digest in baseline_SHA.items())
result=dict(scope='independent UNAPPLIED verify-only local artifact read budgets',original_SHA=original_SHA,candidate_SHA=sha(C),
 original_builder_unchanged=True,old_artifacts_unchanged=True,one_changed_path_readonly_equivalence=True,
 five_actual_before_after_refusals=refusals,three_invalid_stream_metadata_refused_before_read=metadata,
 exact_16MiB_receipt_boundary_pass=True,raw_nonUTF8_NUL_preserved=True,
 budgets=dict(receipt=16*1024*1024,object=16*1024*1024,events=1024*1024,stdout_stderr=8*1024*1024,combined_log=16*1024*1024,source_bodies='exact reconstructed byte lengths',streams='anchored nonnegative byte count,within explicit cap'),
 guarded_no_write_process=True,no_compile_or_old_suite=True,hardware_qualification=False,native_execution=False,device_operations=False)
save(O/'result.json',result)
print('PASS:5 actual whole-file artifact reads now bounded;3 metadata gates,exact receipt,raw byte preservation;no compile/process/write in verifier')
