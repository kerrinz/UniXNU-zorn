#!/usr/bin/env python3
"""Only new raw-DTB provenance checks;no source policy/header/device execution."""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-source-provenance-20261103';SOURCE=R/'UniXNU-zorn/scripts/verify-zorn-gpu-source-provenance.py'
def main():
 j=R/'out/zorn/gpu-stock-dt-source-20261102/vendor/fdt-01f95000.gpu.json';original=json.loads(j.read_text());dtb=Path(original['input']['path']);runs=[];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 def invoke(p,raw=dtb,rawsha=None,jsonsha=None):
  q=subprocess.run([sys.executable,'-B',str(R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'),str(SOURCE),'--input',str(p),'--input-sha256',jsonsha or sha(p),'--dtb',str(raw),'--dtb-sha256',rawsha or sha(raw)],capture_output=True,text=True)
  assert 'forbidden' not in q.stderr,q.stderr;d=json.loads(q.stdout);assert q.returncode==2 and not d['accepted'] and not d['generated_policy'] and not d['hardware_qualification'];return d
 for case in ['changed-byte','omitted-property','added-property','absent-path','status-forgery','declared-SHA-forgery','duplicate-node']:
  d=copy.deepcopy(original);n=d['nodes'][0]
  if case=='changed-byte':key=next(k for k,v in n['properties_hex'].items() if v);v=n['properties_hex'][key];n['properties_hex'][key]=('ff' if v[:2]!='ff' else '00')+v[2:]
  elif case=='omitted-property':del n['properties_hex'][next(iter(n['properties_hex']))]
  elif case=='added-property':n['properties_hex']['forged-source-property']='00000001'
  elif case=='absent-path':n['path']='/not-in-raw-source'
  elif case=='status-forgery':n['source_enabled']=not n['source_enabled']
  elif case=='declared-SHA-forgery':d['input']['sha256']='0'*64
  else:d['nodes'].append(copy.deepcopy(n))
  p=O/(case+'.json');p.write_text(json.dumps(d));result=invoke(p);assert not result['raw_source_verified'];runs.append(dict(case=case,result=result))
 for case,opts in [('wrong-DTB-SHA',dict(rawsha='0'*64)),('wrong-JSON-SHA',dict(jsonsha='0'*64))]:
  result=invoke(j,**opts);assert not result['raw_source_verified'];runs.append(dict(case=case,result=result))
 # An honest single-node subset may verify its own bytes;validation still sees
 # the entire raw tree and therefore cannot hide the K80 multi-SKU tables.
 d=copy.deepcopy(original);d['nodes']=d['nodes'][:1];p=O/'trimmed-source.json';p.write_text(json.dumps(d));result=invoke(p);assert result['raw_source_verified'] and not result['declared_node_set_complete'] and 'multi-SKU/bin' in result['error'];runs.append(dict(case='trimmed-source-cannot-hide-raw-SKU',result=result))
 # Pin malformed raw bytes too:matching hashes must not bypass structural parsing.
 raw=O/'truncated-source.dtb';raw.write_bytes(dtb.read_bytes()[:40]);d=copy.deepcopy(original);d['input']['sha256']=sha(raw);p=O/'truncated-source.json';p.write_text(json.dumps(d));result=invoke(p,raw=raw);assert not result['raw_source_verified'] and 'Invalid raw DTB' in result['error'];runs.append(dict(case='hash-matching-malformed-DTB',result=result))
 real=[]
 for p in sorted((R/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.gpu.json')):
  d=json.loads(p.read_text());result=invoke(p,raw=Path(d['input']['path']));assert result['raw_source_verified'] and 'multi-SKU/bin' in result['error'];real.append(result)
 (O/'result.json').write_text(json.dumps(dict(new_provenance_cases=runs,real_K80_raw_source_verifications=real,source_json_and_raw_DTB_SHA_distinct=True,whole_raw_tree_used_for_schema_not_JSON_subset=True,child_file_write_and_process_forbidden=True,policy_headers_emitted=0,prepare_audit_formatter_not_executed=True,old_suites_reexecuted=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n')
 print('PASS:11 new provenance cases +4raw K80 bindings;self-signed tampering/trimming/malformed DTB cannot qualify source;0headers/write/process/native')
if __name__=='__main__':main()
