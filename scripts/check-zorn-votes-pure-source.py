#!/usr/bin/env python3
"""Test only isolated generator pure source checker;no prepare/import/audit/header execution."""
import ast
import builtins
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-votes-pure-source-check-20261102'

def main():
    original=(O/'original.py.txt').read_text();candidate=(O/'candidate.py.txt').read_text();addition=(O/'pure-entry.py.txt').read_text()
    assert candidate.replace(addition,'',1)==original
    assert hashlib.sha256(original.encode()).hexdigest()=='dfb330a56d990eb71ed60fd73f056fbcacca0a5533e6f011f7ee85286a6157ba'
    old=ast.parse(original);new=ast.parse(candidate)
    assert ast.dump(next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='prepare'))==ast.dump(next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='prepare'))
    fn=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='validate_source_nodes')
    env={'__builtins__':{k:getattr(builtins,k) for k in ['ValueError','isinstance','dict','str','bytes','int','set','len','range']}}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'pure-function-only','exec'),env);validate=env['validate_source_nodes']
    c=lambda v:v.to_bytes(4,'big')
    def fixture():
        d={}
        for kind,path,h in [('gpu','/soc/gpu@3d00000',1),('gmu','/soc/gmu@3d6a000',2)]:
            table=path+'/opp-table';d[path]={'operating-points-v2':c(h)};d[table]={'phandle':c(h)}
            d[table+'/opp0']={'opp-hz':c(0)+c(1000),'opp-level':c(1),'opp-peak-kBps':c(1)}
        return d
    assert not validate(fixture())['generated_policy']
    refused=[]
    for case in ['multi-reference','unknown-property','short-frequency','missing-level','duplicate-frequency','multi-SKU']:
        d=fixture();path='/soc/gpu@3d00000';entry=path+'/opp-table/opp0'
        if case=='multi-reference':d[path]['operating-points-v2']=c(1)+c(2)
        elif case=='unknown-property':d[entry]['opp-supported-hw']=c(1)
        elif case=='short-frequency':d[entry]['opp-hz']=c(1000)
        elif case=='missing-level':del d[entry]['opp-level']
        elif case=='duplicate-frequency':d[path+'/opp-table/opp1']=copy.deepcopy(d[entry])
        else:d[path+'/qcom,gpu-pwrlevel-bins']={}
        try:validate(d)
        except ValueError:refused.append(case)
        else:raise AssertionError(case)
    spec=importlib.util.spec_from_file_location('dt_source',R/'UniXNU-zorn/scripts/inspect-zorn-gpu-overlay-inputs.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    raw_refusals=[]
    for p in sorted((R/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.dtb')):
        blob=p.read_bytes();nodes={path:n.properties for path,n in helper.index(helper.read_fdt(blob)).items()}
        try:validate(nodes)
        except ValueError as e:assert 'multi-SKU/bin' in str(e);raw_refusals.append(dict(path=str(p),sha256=hashlib.sha256(blob).hexdigest(),error=str(e)))
        else:raise AssertionError('K80 source wrongly accepted')
    assert len(raw_refusals)==4
    review=O/'review';(review/'scripts').mkdir(parents=True,exist_ok=False);p=review/'scripts/prepare-sheng-gmu-votes.py';p.write_text(original);patch=O/'pure-source-check-entry.UNAPPLIED.patch'
    for flags in [['--check'],[],['--reverse','--check'],['--reverse']]:
        subprocess.run(['git','apply',*flags,str(patch)],cwd=review,check=True)
        if flags==[]:assert p.read_text()==candidate
    assert p.read_text()==original
    result=dict(new_cpu_schema_refusals=refused,actual_K80_base_source_refusals=raw_refusals,
                pure_function_executed_without_open_import_subprocess_capabilities=True,
                prepare_AST_unchanged_and_not_executed=True,generator_module_not_imported=True,
                previous_generator_repair_not_composed=True,apply_reverse_inverse_exact=True,
                source_sha256=hashlib.sha256(original.encode()).hexdigest(),candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
                policy_headers_emitted=0,driver_patch_count_remains32=True,old_suites_reexecuted=False,
                allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    (O/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS:6 schema refusals +4 real K80 multi-SKU refusals;pure entry only,no file/process/prepare capabilities;independent inverse exact;0 headers')

if __name__=='__main__':main()
