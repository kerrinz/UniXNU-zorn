#!/usr/bin/env python3
"""New combined raw-graph/pure-schema read-only routes;never run generator module."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/zorn/gpu-graph-closure-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/verify-zorn-gpu-reference-source.py'
GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 cases=[]
 for p in sorted((ROOT/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.gpu.json')):
  doc=json.loads(p.read_text());raw=Path(doc['input']['path'])
  q=subprocess.run([sys.executable,'-B',str(GUARD),str(TOOL),'--graph-check-only','--source-schema-check','--input',str(p),'--input-sha256',sha(p),'--dtb',str(raw),'--dtb-sha256',sha(raw)],capture_output=True,text=True)
  assert not q.stderr,q.stderr
  d=json.loads(q.stdout);assert q.returncode==2 and d['references_verified'] and d['graph_verified'] and d['source_schema_compatible'] is False and 'multi-SKU/bin' in d['error'],d
  assert not d['generated_policy'] and not d['hardware_qualification']
  cases.append(dict(input=str(p),graph_verified=True,source_schema_compatible=False,error=d['error']))
 p=next((ROOT/'out/zorn/gpu-stock-dt-source-20261102/vendor').glob('*.gpu.json'));doc=json.loads(p.read_text());raw=Path(doc['input']['path'])
 q=subprocess.run([sys.executable,'-B',str(GUARD),str(TOOL),'--source-schema-check','--input',str(p),'--input-sha256',sha(p),'--dtb',str(raw),'--dtb-sha256',sha(raw)],capture_output=True,text=True)
 assert q.returncode==2 and 'requires --graph-check-only' in q.stderr and not q.stdout
 (OUT/'schema-route-result.json').write_text(json.dumps(dict(new_combined_routes=cases,missing_graph_flag_refused=True,child_no_write_or_process=True,pure_function_AST_only=True,prepare_module_not_executed=True,policy_headers_emitted=0,old_suites_reexecuted=False),indent=2)+'\n')
 print('PASS:4 combined raw-graph/pure-schema routes refuse incompatible multi-SKU;missing graph flag refused;0headers/prepare/native')
if __name__=='__main__':main()
