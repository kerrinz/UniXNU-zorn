#!/usr/bin/env python3
"""Only new source-check CLI checks under no-write/no-subprocess child guards."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-votes-source-cli-20261103'
def main():
 candidate=O/'candidate.py';wrapper=O/'no-side-effects.py';runs=[]
 def run(path=None,expected=False,override=None,extra=None):
  args=[] if path is None else ['--source-check-only','--input',str(path),'--sha256',override or hashlib.sha256(path.read_bytes()).hexdigest()]
  p=subprocess.run([sys.executable,'-B',str(wrapper),str(candidate),*(extra if extra is not None else args)],capture_output=True,text=True)
  assert 'forbidden' not in p.stderr,p.stderr
  data=json.loads(p.stdout) if p.stdout.strip() else None
  if path is not None:
   assert data and data['accepted']==expected and not data['generated_policy'] and not data['hardware_qualification'],p.stderr
   assert p.returncode==(0 if expected else 2)
  else:assert p.returncode!=0 and 'policy emission disabled' in p.stderr
  runs.append(dict(input=str(path) if path else None,returncode=p.returncode,stdout=data,stderr=p.stderr))
 run();run(extra=['--unexpected'])
 for p in sorted((R/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.gpu.json')):run(p)
 cell=lambda v:v.to_bytes(4,'big').hex()
 rows=[]
 for kind,path,h in [('gpu','/soc/gpu@3d00000',1),('gmu','/soc/gmu@3d6a000',2)]:
  rows.extend([dict(path=path,properties_hex={'operating-points-v2':cell(h)}),dict(path=path+'/opp-table',properties_hex={'phandle':cell(h)}),dict(path=path+'/opp-table/opp0',properties_hex={'opp-hz':cell(0)+cell(1000),'opp-level':cell(1),'opp-peak-kBps':cell(1)})])
 p=O/'shape-fixture.json';p.write_text(json.dumps(dict(nodes=rows)));run(p,True);run(p,False,override='0'*64)
 for name,raw in [('duplicate-json-key','{"nodes":[],"nodes":[]}'),('duplicate-path',json.dumps(dict(nodes=rows+[rows[0]]))),('odd-hex',json.dumps(dict(nodes=[dict(path='/bad',properties_hex={'x':'a'})]))),('non-string-hex',json.dumps(dict(nodes=[dict(path='/bad',properties_hex={'x':4})]))),('malformed-root','[]')]:
  p=O/(name+'.json');p.write_text(raw);run(p)
 old=ast.parse((O/'original.py.txt').read_text());new=ast.parse(candidate.read_text())
 assert ast.dump(next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='prepare'))==ast.dump(next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='prepare'))
 review=O/'review';(review/'scripts').mkdir(parents=True,exist_ok=False);p=review/'scripts/prepare-sheng-gmu-votes.py';p.write_text((O/'original.py.txt').read_text());patch=O/'source-check-only-cli.UNAPPLIED.patch'
 for flags in [['--check'],[],['--reverse','--check'],['--reverse']]:
  subprocess.run(['git','apply',*flags,str(patch)],cwd=review,check=True)
  if flags==[]:assert p.read_bytes()==candidate.read_bytes()
 assert p.read_bytes()==(O/'original.py.txt').read_bytes()
 result=dict(runs=runs,no_file_write_or_subprocess_in_child=True,prepare_AST_unchanged_and_not_executed=True,default_emission_disabled_in_isolated_candidate=True,independent_apply_reverse_inverse=True,policy_headers_emitted=0,driver_patch_count_remains32=True,old_suites_reexecuted=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:13 CLI routes under no-write/no-process guard;4real K80 refusals;SHA/JSON/schema/default gate;prepare unchanged,independent inverse;0 headers')
if __name__=='__main__':main()
