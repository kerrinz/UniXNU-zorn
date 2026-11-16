#!/usr/bin/env python3
"""Only new aggregate hashing-work boundaries and changed-input equivalence;no firmware execution."""
from pathlib import Path
import argparse,importlib.util,importlib.machinery,types,json,hashlib,struct,subprocess,sys
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False);B=R/'out/zorn/gpu-aop-payload-hash-budget-20261103';S=R/'UniXNU-zorn/scripts/inspect-zorn-aop-source-kind.py'
spec=importlib.util.spec_from_file_location('aop_after',S);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
loader=importlib.machinery.SourceFileLoader('aop_before',str(B/'inspector-preimage.py.txt'));before=importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name,loader));loader.exec_module(before)
real_hash=hashlib.sha256
calls=[0,0]
def counted(raw):calls[0]+=1;calls[1]+=len(raw);return real_hash(raw)
m.hashlib=types.SimpleNamespace(sha256=counted)
def fixture(count,last=None):
 b=bytearray(1024*1024);ident=b'\x7fELF\x01\x01\x01'+b'\0'*9;struct.pack_into('<16sHHIIIIIHHHHHH',b,0,ident,2,243,1,0,52,0,0,52,32,count,0,0,0)
 for i in range(count):struct.pack_into('<8I',b,52+i*32,0,0,0,0,last if last is not None and i==count-1 else len(b),0,0,0)
 return bytes(b)
refusals=[]
def reject(name,b,error='aggregate program payload hashing exceeds offline work budget'):
 calls[:]=[0,0]
 try:m.inspect(b)
 except ValueError as e:assert str(e)==error;assert calls==[0,0];refusals.append(dict(case=name,error=str(e),payload_hash_calls=0))
 else:raise AssertionError(name)
reject('before-accepted-amplified-input',(B/'repeated-payload.elf').read_bytes());reject('one-byte-over-work-budget',fixture(65,1))
b=bytearray(fixture(2));struct.pack_into('<I',b,52+32+16,len(b)+1);reject('late-program-extent-before-first-hash',b,'program file extent outside supplied source')
calls[:]=[0,0];exact=m.inspect(fixture(64));assert calls==[64,64*1024*1024] and len(exact['programs'])==64
source_rows=json.loads((R/'out/zorn/gpu-source-review-verify-20261103/next-local-inputs.json').read_text())
# Use the two actual source identities already retained in the first envelope stage.
actual=[]
for row in json.loads((R/'out/zorn/gpu-aop-source-kind-20261103/result.json').read_text())['two_real_static_source_envelopes']:
 p=Path(row['input']);raw=p.read_bytes();assert real_hash(raw).hexdigest()==row['sha256'];calls[:]=[0,0]
 got=m.inspect(raw);expected=before.inspect(raw);assert got==expected;actual.append(dict(input=str(p),source_sha256=row['sha256'],output_identical=True,payload_bytes_hashed=calls[1],no_source_authentication_or_DB_eligibility=not got['source_authentication_verified'] and not got['commanddb_snapshot_usable']))
# Guarded actual CLI:oversized work refuses without any output file or process.
b=fixture(65,1);(O/'over-budget.elf').write_bytes(b);guard=R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py';cmd=[sys.executable,'-B',str(guard),str(S),'--input',str(O/'over-budget.elf'),'--sha256',real_hash(b).hexdigest()];p=subprocess.run(cmd,capture_output=True);(O/'cli.stdout.raw').write_bytes(p.stdout);(O/'cli.stderr.raw').write_bytes(p.stderr);d=json.loads(p.stdout);assert p.returncode==2 and not d['container_bounds_verified'] and not d['commanddb_snapshot_usable']
result=dict(scope='new aggregate hashing-work repair;not firmware or target execution',new_refusals=refusals,exact_64MiB_payload_work_pass=True,two_changed_real_sources=actual,guarded_CLI_exit2=True,source_sha256=real_hash(S.read_bytes()).hexdigest(),old_malformed_suite_or_driver_targets_rerun=False,native_or_device_execution=False,hardware_qualification=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:3 prehash refusals/exact64MiB/2changed real-source equivalences/guarded CLI;no old suite or firmware execution')
