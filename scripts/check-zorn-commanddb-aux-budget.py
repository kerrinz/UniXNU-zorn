#!/usr/bin/env python3
"""Regression for repeated-AUX output amplification;old suites and targets are not run."""
from pathlib import Path
import argparse,importlib.util,importlib.machinery,json,hashlib,struct,subprocess,sys,tracemalloc
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False)
S=R/'UniXNU-zorn/scripts/decode-zorn-commanddb-file.py';spec=importlib.util.spec_from_file_location('decoder_after',S);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
B=R/'out/zorn/gpu-commanddb-aux-export-budget-20261103';loader=importlib.machinery.SourceFileLoader('decoder_preimage',str(B/'decoder-preimage.py.txt'));before=importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name,loader));loader.exec_module(before)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def fixture(count,last=None):
 b=bytearray(75000);b[:4]=b'\x78\x56\x34\x12';b[4:8]=m.MAGIC;struct.pack_into('<4H',b,8,9,0,0,count)
 for i in range(count):struct.pack_into('<2H',b,144+i*24+20,last if last is not None and i==count-1 else 65535,0)
 return bytes(b)
failures=[]
def reject(name,b,peak_limit=None):
 if peak_limit:tracemalloc.start()
 try:m.decode(b,len(b),sha(b))
 except ValueError as e:
  assert str(e)=='aggregate AUX export exceeds offline output budget'
  peak=tracemalloc.get_traced_memory()[1] if peak_limit else None
  if peak_limit:assert peak<peak_limit,peak
  failures.append(dict(case=name,error=str(e),peak_traced_bytes=peak))
 else:raise AssertionError(name)
 finally:
  if peak_limit:tracemalloc.stop()
reject('actual-before-accepted-amplified-file',(B/'amplified-input.bin').read_bytes(),1024*1024)
# 128*65535+128 is exactly8MiB;one extra byte must reject.
exact=fixture(129,128);(O/'exact-budget.bin').write_bytes(exact);d=m.decode(exact,len(exact),sha(exact));assert sum(e['aux_bytes'] for r in d['rows'] for e in r.get('entries',[]))==m.MAX_TOTAL_AUX_BYTES;assert not d['snapshot_qualified'];del d
reject('one-byte-over-budget',fixture(129,129),1024*1024)
# Two rows must share the same aggregate budget,not receive separate budgets.
b=bytearray(fixture(128));struct.pack_into('<4H',b,24,10,0,0,1);reject('aggregate-across-slave-rows',bytes(b),1024*1024)
valid=(R/'out/zorn/gpu-commanddb-input-acquisition-20261103/synthetic.bin').read_bytes();expected=before.decode(valid,len(valid),sha(valid));actual=m.decode(valid,len(valid),sha(valid));assert json.dumps(actual,sort_keys=True)==json.dumps(expected,sort_keys=True)
assert m.decode(bytearray(valid),len(valid),sha(valid))==expected
# Actual read-only CLI must emit only the failure JSON,not partial row data.
bad=fixture(129,129);(O/'over-budget.bin').write_bytes(bad);guard=R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
cmd=[sys.executable,'-B',str(guard),str(S),'--raw-reservation-file',str(O/'over-budget.bin'),'--expected-bytes',str(len(bad)),'--source-sha256',sha(bad)]
p=subprocess.run(cmd,capture_output=True);(O/'cli.stdout.raw').write_bytes(p.stdout);(O/'cli.stderr.raw').write_bytes(p.stderr);r=json.loads(p.stdout);assert p.returncode==2 and not r['decoded'] and 'rows' not in r and not r['snapshot_qualified']
result=dict(scope='new output amplification regression only;synthetic offline files',new_refusals=failures,exact_8MiB_AUX_boundary_pass=True,within_budget_output_identical_to_preimage=True,mutable_input_preserved_by_immutable_copy=True,guarded_CLI_exit2_without_partial_output=True,CLI_stdout_sha256=sha(p.stdout),CLI_stderr_sha256=sha(p.stderr),decoder_sha256=sha(S.read_bytes()),old_suites_rerun=False,driver_or_native_target_recompiled=False,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:actual amplification refused before materialization;exact8MiB/3refusals/default equivalence/guarded CLI;0old-suite/target/device')
