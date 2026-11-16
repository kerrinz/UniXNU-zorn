#!/usr/bin/env python3
"""Bound caller-supplied preflight controls in an independent source candidate."""
from pathlib import Path
import argparse,difflib,hashlib,json,shutil,subprocess,sys

R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
S=R/'UniXNU-zorn/scripts/build-zorn-source-data-review.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
original=S.read_text();original_SHA=sha(S);(O/'original.py.txt').write_text(original)
helper='''MAX_REVIEW_CONTROL_BYTES=1024*1024

def read_review_control(path):
    # Host input work budget only;the exact SHA remains independently required.
    with path.open('rb') as stream:raw=stream.read(MAX_REVIEW_CONTROL_BYTES+1)
    if len(raw)>MAX_REVIEW_CONTROL_BYTES:
        raise ValueError('source review control reader bound')
    return raw


'''
candidate=original.replace('def preflight(',helper+'def preflight(',1)
candidate=candidate.replace('    dependencies={}\n','    dependencies={}\n    approval_raw=None\n',1)
candidate=candidate.replace('        raw=path.read_bytes()\n',"        raw=read_review_control(path) if key=='approval' else path.read_bytes()\n",1)
candidate=candidate.replace('        dependencies[str(path)]=digest\n','        dependencies[str(path)]=digest\n        if key==\'approval\':approval_raw=raw\n',1)
candidate=candidate.replace('    raw=manifest.read_bytes()\n','    raw=read_review_control(manifest)\n',1)
candidate=candidate.replace("    receipt=json.loads((approval or PINNED['approval'][0]).read_text(),object_pairs_hook=emitter['unique'])", "    receipt=json.loads(approval_raw,object_pairs_hook=emitter['unique'])")
assert candidate!=original
(O/'preflight-controls.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/scripts/'+S.name,tofile='b/scripts/'+S.name)))
M=O/'mirror';prior=R/'out/zorn/gpu-review-artifact-read-bounds-20261103/mirror'
for root in ['UniXNU-zorn/scripts','UniXNU/scripts/unixnu','out/zorn/gpu-source-layout-review','out/zorn/gpu-power-source-compare-20261103','out/zorn/gpu-votes-source-identity-20261103']:
 for p in (prior/root).rglob('*'):
  if p.is_file() and p.name!=S.name:
   q=M/p.relative_to(prior);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);assert sha(p)==sha(q)
C=M/'UniXNU-zorn/scripts'/S.name;C.write_text(candidate)
manifest=R/'out/zorn/gpu-power-source-compare-20261103/inputs.json'
approval=R/'out/zorn/gpu-source-layout-review/owner-scope-approval.json'
limit=1024*1024
for name,size in [('over-control.bin',limit+8192),('exact-control.bin',limit),('plus-one-control.bin',limit+1)]:
 with (O/name).open('wb') as f:f.truncate(size)
wrapper='''from pathlib import Path
import runpy,sys,json
script=Path(sys.argv[1]);args=sys.argv[2:];watched={str(Path(args[args.index(k)+1]).resolve()) for k in ['--approval','--inputs'] if k in args};real_open=Path.open;trace=[]
class Observed:
 def __init__(self,stream,path):self.stream=stream;self.path=path
 def __enter__(self):return self
 def __exit__(self,*a):return self.stream.__exit__(*a)
 def read(self,n=-1):
  raw=self.stream.read(n);trace.append(dict(path=self.path,requested=n,returned=len(raw)));return raw
def opened(path,*a,**k):
 stream=real_open(path,*a,**k);p=str(path.resolve());return Observed(stream,p) if p in watched else stream
Path.open=opened;sys.argv=[str(script),*args];code=0
try:runpy.run_path(str(script),run_name='__main__')
except SystemExit as e:code=e.code
finally:Path.open=real_open;print(json.dumps(trace),file=sys.stderr)
raise SystemExit(code)
'''
(O/'trace-preflight.py').write_text(wrapper)
guard=R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py';events=[]
out=M/'out/zorn/never-created-output'
def cli(tool,m,a,name):
 cmd=[sys.executable,'-B',str(guard),str(O/'trace-preflight.py'),str(tool),'--source-review-only','--inputs',str(m),'--approval',str(a),'--out-dir',str(out)]
 p=subprocess.run(cmd,capture_output=True);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr)
 events.append(dict(name=name,command=cmd,returncode=p.returncode));save(O/'events.json',events)
 assert p.returncode in (0,2),p.stderr
 assert not out.exists()
 return p.returncode,json.loads(p.stdout),json.loads(p.stderr)
bad=[]
for flag in ['approval','manifest']:
 m=O/'over-control.bin' if flag=='manifest' else manifest
 a=O/'over-control.bin' if flag=='approval' else approval
 bc,b,bt=cli(S,m,a,'before-'+flag);ac,z,at=cli(C,m,a,'after-'+flag)
 assert bc==ac==2 and z['error']=='source review control reader bound'
 path=str((O/'over-control.bin').resolve());before=[x for x in bt if x['path']==path];after=[x for x in at if x['path']==path]
 assert before[0]['requested']==-1 and before[0]['returned']==limit+8192
 assert after[0]['requested']==limit+1 and after[0]['returned']==limit+1
 if flag=='approval':assert not any(x['path']==str(manifest) for x in at)
 bad.append(dict(control=flag,original_error=b['error'],before=before,after=after))
boundaries=[]
for key in ['approval','manifest']:
 for name,over in [('exact-control.bin',False),('plus-one-control.bin',True)]:
  m=O/name if key=='manifest' else manifest;a=O/name if key=='approval' else approval
  code,result,trace=cli(C,m,a,key+'-'+name)
  assert code==2 and (result['error']=='source review control reader bound')==over
  if not over:assert ('identity mismatch' if key=='approval' else 'only the approved four-source manifest') in result['error']
  boundaries.append(dict(control=key,size=(O/name).stat().st_size,reader_bound=over,SHA_gate_retained=not over))
bc,b,bt=cli(S,manifest,approval,'valid-original-plan');ac,z,at=cli(C,manifest,approval,'valid-candidate-plan')
assert bc==ac==0 and b['planned'] and z['planned'] and not b['executed'] and not z['executed']
assert b['output_content_SHA']==z['output_content_SHA'] and b['commands']==z['commands']
# Copied dependencies have identical bytes;only their independent mirror paths differ.
normalize=lambda inputs:{(p.replace(str(M),str(R),1) if p.startswith(str(M)+'/') else p):v for p,v in inputs.items()}
assert normalize(z['inputs'])==b['inputs']
approval_reads=[t for t in at if t['path']==str(approval)]
assert len(approval_reads)==1 and approval_reads[0]['requested']==limit+1
assert sha(S)==original_SHA and not out.exists()
result=dict(scope='independent UNAPPLIED preflight control reads;default plan only',original_SHA=original_SHA,candidate_SHA=sha(C),original_unchanged=True,
 two_actual_before_after_refusals=bad,four_exact_plus_one_boundaries=boundaries,strict_SHA_gates_retained=True,
 valid_plan_output_content_SHA_and_compile_commands_identical=True,dependency_bytes_identical_only_mirror_paths_differ=True,
 approval_parsed_from_same_SHA_checked_bytes=True,approval_read_once=True,control_budget_bytes=limit,
 guarded_no_write_process=True,no_output_directory_created=True,no_header_emit_compile_or_old_suite=True,
 hardware_qualification=False,native_execution=False,device_operations=False)
save(O/'result.json',result)
print('PASS:2 actual control whole-file reads bounded,4 inclusive-bound/SHA gates,plan equivalence;approval parsed from checked bytes;no output/process')
