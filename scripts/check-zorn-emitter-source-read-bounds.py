#!/usr/bin/env python3
"""Test emitter collect's own source reads;never emit or compile headers."""
from pathlib import Path
import argparse, difflib, hashlib, json, subprocess, sys

R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
P=O.parent;T=P/'mirror/UniXNU-zorn/scripts'
S=R/'UniXNU-zorn/scripts/emit-zorn-unselected-source-data.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PIN='97596eec625720faf6eff1860f9af6aad7146cc0c56a99d3daf995202ec05b5a'
assert sha(S)==PIN
original=S.read_text();(O/'original.py.txt').write_text(original)
reader=T/'read-zorn-gpu-power-source.py'
candidate=original.replace('8e15bbef1f754f2808f5ffeeff76bdd0a707f5d8f77a136cec621f3d7929361b',sha(reader))
candidate=candidate.replace("    reader = runpy.run_path(str(READER))", "    reader = runpy.run_path(str(READER))\n    bounded = reader['input_reader']()")
candidate=candidate.replace('        blob = source.read_bytes(); digest = sha(blob)', "        blob = bounded['read_bounded'](source,bounded['MAX_RAW_DTB_BYTES'],'raw DTB'); digest = sha(blob)")
candidate=candidate.replace("            provenance, rows = reader['verified_graph'](root,digest,graph.read_bytes(),entry['graph_sha256'])", "            graph_bytes = bounded['read_bounded'](graph,bounded['MAX_SOURCE_JSON_BYTES'],'source JSON')\n            provenance, rows = reader['verified_graph'](root,digest,graph_bytes,entry['graph_sha256'])")
C=T/S.name;assert not C.exists();C.write_text(candidate)
(O/'emitter-source-reads.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/scripts/'+S.name,tofile='b/scripts/'+S.name)))
# The collector accepts four explicit entries as its low-level argument;these
# malformed test manifests are never passed off as approved CLI manifests.
wrapper='''from pathlib import Path
import runpy,sys,json,hashlib
script=Path(sys.argv[1]);manifest=json.loads(Path(sys.argv[2]).read_bytes());watched={str(Path(row[k]).resolve()) for row in manifest['sources'] for k in ['dtb','graph_json']};real_open=Path.open;trace=[]
class Observed:
 def __init__(self,stream,path):self.stream=stream;self.path=path
 def __enter__(self):return self
 def __exit__(self,*a):return self.stream.__exit__(*a)
 def read(self,n=-1):
  data=self.stream.read(n);trace.append(dict(path=self.path,requested=n,returned=len(data)));return data
def opened(path,*a,**k):
 stream=real_open(path,*a,**k);resolved=str(path.resolve());return Observed(stream,resolved) if resolved in watched else stream
Path.open=opened;out={};code=0
try:
 model=runpy.run_path(str(script))['collect'](manifest)
 out=dict(model_SHA=hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest(),counts={k:len(v) for k,v in model.items()})
except ValueError as e:out=dict(error=str(e));code=2
finally:Path.open=real_open
out['trace']=trace;print(json.dumps(out));raise SystemExit(code)
'''
(O/'trace-collect.py').write_text(wrapper)
manifest=R/'out/zorn/gpu-power-source-compare-20261103/inputs.json'
guard=R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py';events=[]
def run(script,m,name):
 cmd=[sys.executable,'-B',str(guard),str(O/'trace-collect.py'),str(script),str(m)]
 p=subprocess.run(cmd,capture_output=True);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr)
 events.append(dict(name=name,command=cmd,returncode=p.returncode));(O/'events.json').write_text(json.dumps(events,indent=2)+'\n')
 assert p.returncode in (0,2),p.stderr
 return p.returncode,json.loads(p.stdout)
code,before=run(S,manifest,'real-before');acode,after=run(C,manifest,'real-after')
assert code==acode==0 and before['model_SHA']==after['model_SHA'] and before['counts']==after['counts']
assert before['counts']['sources']==4 and before['counts']['tables']==16 and before['counts']['entries']==192
assert len(after['trace'])==8 and all(t['requested']==16*1024*1024+1 for t in after['trace'])
refusals=[]
for key,digest_key,filename,error in [('dtb','dtb_sha256','oversized-dtb.bin','raw DTB reader bound'),('graph_json','graph_sha256','oversized-graph.json','source JSON reader bound')]:
 m=json.loads(manifest.read_text());m['sources'][0][key]=str(P/filename);m['sources'][0][digest_key]=sha(P/filename)
 path=O/('bad-'+key+'.json');path.write_text(json.dumps(m))
 bcode,b=run(S,path,'before-'+key);acode,a=run(C,path,'after-'+key)
 assert bcode==acode==2 and a['error']==error
 position=0 if key=='dtb' else 1
 assert b['trace'][position]['requested']==-1 and a['trace'][position]['requested']==16*1024*1024+1
 assert 'model_SHA' not in a
 refusals.append(dict(input=key,before_trace=b['trace'],after_trace=a['trace'],no_partial_model=True))
saved=reader.read_bytes()
try:
 reader.write_bytes(saved+b'\n# isolated tamper\n')
 code,bad=run(C,manifest,'reader-pin-refusal');assert code==2 and bad['error']=='pinned source reader changed' and not bad['trace']
finally:reader.write_bytes(saved)
assert sha(S)==PIN
result=dict(original_unchanged=True,original_SHA=PIN,candidate_SHA=sha(C),candidate_reader_SHA=sha(reader),
            all_four_source_model_identical=True,model_SHA=after['model_SHA'],counts=after['counts'],
            eight_actual_source_reads_bounded=True,refusals=refusals,strict_reader_pin_before_inputs=True,
            no_header_render_emit_or_compile=True,no_approval_manifest_changed=True,
            guarded_no_write_process=True,hardware_qualification=False,native_execution=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: emitter own DTB/graph bounds,4-source model identical,strict candidate reader pin;no emit/compile')
