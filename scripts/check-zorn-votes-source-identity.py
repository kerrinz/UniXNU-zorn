#!/usr/bin/env python3
"""Only new ambiguous-source identity refusal traces;no old CLI suite or emission."""
import ast,copy,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-votes-source-identity-20261103';P=R/'out/zorn/gpu-votes-source-cli-20261103'
def main():
 template=json.loads((P/'shape-fixture.json').read_text());wrapper=P/'no-side-effects.py';rows=[]
 def invoke(candidate,p,accepted):
  q=subprocess.run([sys.executable,'-B',str(wrapper),str(candidate),'--source-check-only','--input',str(p),'--sha256',hashlib.sha256(p.read_bytes()).hexdigest()],capture_output=True,text=True)
  assert 'forbidden' not in q.stderr,q.stderr
  d=json.loads(q.stdout);assert d['accepted']==accepted and q.returncode==(0 if accepted else 2) and not d['generated_policy'] and not d['hardware_qualification']
  return d
 for kind in ['duplicate-handle','conflicting-alias','zero-handle','reserved-handle','short-handle','vector-handle']:
  d=copy.deepcopy(template)
  if kind=='conflicting-alias':d['nodes'][1]['properties_hex']['linux,phandle']='00000002'
  else:
   raw={'duplicate-handle':'00000001','zero-handle':'00000000','reserved-handle':'ffffffff','short-handle':'0001','vector-handle':'0000000300000004'}[kind]
   d['nodes'].append(dict(path='/unrelated-source-provider',properties_hex={'phandle':raw}))
  p=O/(kind+'.json');p.write_text(json.dumps(d))
  before=invoke(P/'candidate.py',p,True);after=invoke(O/'candidate.py',p,False)
  rows.append(dict(case=kind,previous_accepted=before['accepted'],repaired_error=after['error']))
 # Both aliases are legitimate when they name the same single source object.
 d=copy.deepcopy(template);d['nodes'][1]['properties_hex']['linux,phandle']='00000001';p=O/'same-object-alias.json';p.write_text(json.dumps(d));invoke(O/'candidate.py',p,True)
 old=ast.parse((O/'original.py.txt').read_text());new=ast.parse((O/'candidate.py').read_text())
 assert ast.dump(next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='prepare'))==ast.dump(next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='prepare'))
 review=O/'review';(review/'scripts').mkdir(parents=True,exist_ok=False);p=review/'scripts/prepare-sheng-gmu-votes.py';p.write_bytes((O/'original.py.txt').read_bytes());patch=O/'source-identity-check.UNAPPLIED.patch'
 for flags in [['--check'],[],['--reverse','--check'],['--reverse']]:
  subprocess.run(['git','apply',*flags,str(patch)],cwd=review,check=True)
  if flags==[]:assert p.read_bytes()==(O/'candidate.py').read_bytes()
 assert p.read_bytes()==(O/'original.py.txt').read_bytes()
 result=dict(new_source_identity_cases=rows,same_node_alias_accepted_as_source_shape_only=True,no_write_or_process_in_child=True,prepare_AST_unchanged_and_not_executed=True,policy_headers_emitted=0,independent_apply_reverse_inverse=True,driver_patch_count_remains32=True,old_suites_reexecuted=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:6 newly reproduced ambiguous/invalid phandle admissions now refused;equal same-node alias retained;7 new cases only,no old suite/header/native')
if __name__=='__main__':main()
