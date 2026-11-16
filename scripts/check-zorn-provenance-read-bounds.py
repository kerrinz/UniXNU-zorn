#!/usr/bin/env python3
"""Unapplied bounded-reader repair with real file-read traces;no old suites,headers or native execution."""
from pathlib import Path
import argparse,hashlib,json,difflib,subprocess,sys,runpy
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False)
S=R/'UniXNU-zorn/scripts/verify-zorn-gpu-source-provenance.py';PIN='245b28b55bebd95861933216136fef4c2115c55cdd2dc11f6d96befd07491eb4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
assert sha(S)==PIN;original=S.read_text();(O/'original.py.txt').write_text(original)
helper='''MAX_SOURCE_JSON_BYTES=16*1024*1024
MAX_RAW_DTB_BYTES=16*1024*1024

def read_bounded(path,limit,label):
    # Limit the actual read,not a stat-before-read or post-hash check.
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError(label+' reader bound')
    return raw

'''
candidate=original.replace('def unique(pairs):',helper+'def unique(pairs):').replace('        src=a.input.read_bytes();raw=a.dtb.read_bytes()',"        src=read_bounded(a.input,MAX_SOURCE_JSON_BYTES,'source JSON')\n        raw=read_bounded(a.dtb,MAX_RAW_DTB_BYTES,'raw DTB')").replace("        if len(src)>16*1024*1024:raise ValueError('source JSON reader bound')\n",'')
assert candidate!=original
(O/'bounded-reader.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/scripts/verify-zorn-gpu-source-provenance.py',tofile='b/scripts/verify-zorn-gpu-source-provenance.py')))
# A real relocated source tree preserves ROOT semantics and exact dependency
# bytes.No fake __file__,pin substitution,import stub or bypass is required.
M=O/'mirror';T=M/'UniXNU-zorn/scripts';T.mkdir(parents=True);C=T/S.name;C.write_text(candidate)
copies={}
for rel in ['UniXNU/scripts/unixnu/__init__.py','UniXNU/scripts/unixnu/devicetree.py','UniXNU/scripts/unixnu/util.py','out/zorn/gpu-votes-source-identity-20261103/candidate.py']:
 p=R/rel;q=M/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());assert sha(p)==sha(q);copies[str(p)]=sha(p)
# The wrapper observes real read requests and returns the real file bytes.
wrapper=r'''from pathlib import Path
import runpy,sys,json
script=Path(sys.argv[1]);args=sys.argv[2:];watched={str(Path(args[args.index('--input')+1]).resolve()),str(Path(args[args.index('--dtb')+1]).resolve())};events=[];real_open=Path.open
class Observed:
 def __init__(self,stream,path):self.stream=stream;self.path=path
 def __enter__(self):return self
 def __exit__(self,*a):return self.stream.__exit__(*a)
 def read(self,n=-1):
  data=self.stream.read(n);events.append(dict(path=self.path,requested=n,returned=len(data)));return data
def opened(path,*a,**k):
 stream=real_open(path,*a,**k);resolved=str(path.resolve());return Observed(stream,resolved) if resolved in watched else stream
Path.open=opened;sys.argv=[str(script),*args];code=0
try:runpy.run_path(str(script),run_name='__main__')
except SystemExit as e:code=e.code
finally:Path.open=real_open;print(json.dumps(dict(real_read_trace=events)),file=sys.stderr)
raise SystemExit(code)
'''
(O/'trace-cli.py').write_text(wrapper)
# Sparse synthetic inputs keep disk use bounded without touching old artifacts.
limit=16*1024*1024
for name,size in [('oversized-json.bin',limit+8192),('oversized-dtb.bin',limit+65536),('exact-bound.bin',limit)]:
 with (O/name).open('wb') as f:f.truncate(size)
(O/'small.json').write_text('{"nodes":[]}');(O/'small.dtb').write_bytes(b'not-a-DTB')
guard=R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py';events=[]
def cli(script,source,dtb,name):
 cmd=[sys.executable,'-B',str(guard),str(O/'trace-cli.py'),str(script),'--input',str(source),'--input-sha256',sha(source),'--dtb',str(dtb),'--dtb-sha256',sha(dtb)]
 p=subprocess.run(cmd,capture_output=True);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,command=cmd,returncode=p.returncode));save(O/'events.json',events);assert p.returncode==2,p.stderr.decode(errors='replace')
 return json.loads(p.stdout),json.loads(p.stderr)['real_read_trace']
before_json,t0=cli(S,O/'oversized-json.bin',O/'small.dtb','before-json');after_json,t1=cli(C,O/'oversized-json.bin',O/'small.dtb','after-json');assert before_json['error']==after_json['error']=='source JSON reader bound';assert t0[0]['requested']==-1 and t0[0]['returned']==limit+8192 and len(t0)==2;assert len(t1)==1 and t1[0]['requested']==limit+1 and t1[0]['returned']==limit+1
before_dtb,t2=cli(S,O/'small.json',O/'oversized-dtb.bin','before-dtb');after_dtb,t3=cli(C,O/'small.json',O/'oversized-dtb.bin','after-dtb');assert t2[1]['requested']==-1 and t2[1]['returned']==limit+65536;assert t3[1]['requested']==limit+1 and t3[1]['returned']==limit+1 and after_dtb['error']=='raw DTB reader bound'
module=runpy.run_path(str(C));exact=module['read_bounded'](O/'exact-bound.bin',limit,'exact');assert len(exact)==limit;del exact
# Only two changed-path real input equivalences,not the old malformed suite.
manifest=json.loads((R/'out/zorn/gpu-power-source-compare-20261103/inputs.json').read_text());real=[]
for i,row in enumerate(manifest['sources'][:2]):
 before,oldtrace=cli(S,Path(row['graph_json']),Path(row['dtb']),'real-before-'+str(i));after,newtrace=cli(C,Path(row['graph_json']),Path(row['dtb']),'real-after-'+str(i));assert before==after and after['raw_source_verified'] and not after['accepted'];assert all(x['requested']==limit+1 for x in newtrace);real.append(dict(source_id=row['id'],output_identical=True,raw_source_verified=True,pure_schema_refusal_retained=True,source_reads=newtrace))
assert sha(S)==PIN
result=dict(scope='unapplied file-read work-bound repair;main pinned chain unchanged',before_json_read_trace=t0,after_json_read_trace=t1,before_raw_DTB_read_trace=t2,after_raw_DTB_read_trace=t3,oversized_JSON_does_not_open_DTB=True,exact_16MiB_helper_boundary_pass=True,two_real_changed_input_equivalences=real,guarded_CLI_no_write_process=True,original_provenance_SHA=PIN,original_provenance_unchanged=True,relocated_real_dependency_copies=copies,candidate_SHA=sha(C),patch_SHA=sha(O/'bounded-reader.UNAPPLIED.patch'),old_suites_or_driver_targets_rerun=False,hardware_qualification=False,device_operations=False)
save(O/'result.json',result);print('PASS:real before/after read(-1) vs read(limit+1),early JSON refusal,raw DTB cap,exact boundary,2real equivalences;original pins unchanged')
