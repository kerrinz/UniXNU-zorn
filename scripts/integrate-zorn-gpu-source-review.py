#!/usr/bin/env python3
"""Stage coherent source review only; never select or run a GPU component."""
from pathlib import Path
import argparse,json,hashlib,shutil,re,subprocess,datetime
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
P=json.loads((R/'out/zorn/gpu-offline-integration-scope-20261103/integration-scope-proposal.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N=O/'native';L=O/'linux-reference';N.mkdir();L.mkdir();sources={}
base=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740'
for p in base.iterdir():
 if p.is_file():shutil.copyfile(p,N/p.name);sources[str(N/p.name)]={'original':str(p),'sha256':sha(p)}
linux={
'adreno_gen7_hwsched_hfi.c':'out/zorn/gpu-discovery-20261030/layout/adreno_gen7_hwsched_hfi.c',
'adreno_gen7_hwsched.c':'out/zorn/gpu-discovery-20261030/layout/adreno_gen7_hwsched.c',
'adreno_gen7_gmu.c':'out/zorn/gpu-discovery-20261030/profile-reference/adreno_gen7_gmu.c',
'adreno_gen7_gmu.h':'out/zorn/gpu-discovery-20261030/profile-reference/adreno_gen7_gmu.h',
'adreno_hwsched.c':'out/zorn/gpu-gen7-preallocated-providers/adreno_hwsched.c',
'adreno_hwsched.h':'out/zorn/gpu-gen7-replay-error-retention/adreno_hwsched.h',
'kgsl.c':'out/zorn/gpu-gen7-preallocated-providers/kgsl.c'}
for name,rel in linux.items():
 p=R/rel;assert p.is_file();shutil.copyfile(p,L/name);sources[str(L/name)]={'original':str(p),'sha256':sha(p)}
(O/'baseline-inputs.json').write_text(json.dumps(sources,indent=2)+'\n');D=O/'normalized-patches';D.mkdir();events=[]
items=list(P['old32_independent_patch_inputs'].items())+list(P['two_recent_patch_inputs'].items())
for i,(path,pin) in enumerate(items,1):
 p=Path(path);assert sha(p)==pin;s=p.read_text();targets=[Path(x[6:]).name for x in s.splitlines() if x.startswith('+++ b/')];domain='native' if all(t.startswith('NativeAdreno') for t in targets) else 'linux-reference';assert targets and all((O/domain/t).is_file() for t in targets)
 lines=[]
 for line in s.splitlines(True):
  if line.startswith(('--- a/','+++ b/')):line=line[:6]+Path(line[6:].strip()).name+'\n'
  elif line.startswith('diff --git '):
   names=line.split();line='diff --git a/'+Path(names[2]).name+' b/'+Path(names[3]).name+'\n'
  lines.append(line)
 q=D/(str(i).zfill(2)+'-'+p.name);q.write_text(''.join(lines));check=subprocess.run(['git','apply','--check','--whitespace=nowarn',str(q)],cwd=O/domain,capture_output=True);(O/(str(i).zfill(2)+'-check.stdout.raw')).write_bytes(check.stdout);(O/(str(i).zfill(2)+'-check.stderr.raw')).write_bytes(check.stderr)
 event={'number':i,'patch':str(p),'patch_sha256':pin,'normalized_patch':str(q),'domain':domain,'targets':targets,'check_returncode':check.returncode,'status':'CONFLICT_REQUIRES_SEMANTIC_PORT'}
 if check.returncode==0:
  done=subprocess.run(['git','apply','--whitespace=nowarn',str(q)],cwd=O/domain,capture_output=True);assert done.returncode==0,done.stderr;event['status']='APPLIED_TO_ISOLATED_COPY'
 events.append(event);(O/'integration-events.json').write_text(json.dumps(events,indent=2)+'\n')
assert all(sha(Path(x['original']))==x['sha256'] for x in sources.values())
summary={'inputs':len(events),'applied':sum(e['status']=='APPLIED_TO_ISOLATED_COPY' for e in events),'conflicts':[{'number':e['number'],'targets':e['targets']} for e in events if e['check_returncode']],'only_isolated_copies_modified':True,'native_or_device_execution':False,'runtime_selection':False,'hardware_qualification':False};(O/'initial-integration-result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
