#!/usr/bin/env python3
"""Isolate two pinned GMU integer helpers;never compile or execute the GMU validator."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False)
S=R/'out/zorn/gpu-catalog-service-dependencies/sm8550-primary/kits/Sm8550Platform/ShengGmu.c'
expected='d61daa0b10038314922400daf6288a957e973043e171f986f5f226f2dff2de09'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
assert sha(S)==expected
text=S.read_text();helpers=[]
for name,signature in [('extent','uintptr_t at,size_t bytes'),('overlap','uintptr_t a,size_t na,uintptr_t b,size_t nb')]:
 pattern='static int '+name+'('+signature+')\n'
 start=text.index(pattern);end=text.index('}',start)+1;function=text[start:end];assert function.count('{')==1
 assert not any(word in function for word in ['->','read32','write32','sha256','volatile'])
 helpers.append(function)
# This retained function body is evidence only;it never enters generated C.
start=text.index('static ShengGmuStatus validate(');level=0;begin=text.index('{',start)
for end in range(begin,len(text)):
 if text[end]=='{':level+=1
 if text[end]=='}':
  level-=1
  if not level:break
validate=text[start:end+1];assert 'd->services.sha256(' in validate
(O/'validate-source-review.txt').write_text(validate+'\n')
M=2**64-1
extent_cases=[(0,1),(1,0),(1,1),(M,1),(M,2),(M-15,16),(M-15,17),(1,M),(2,M),(16,16),(16,M-15),(16,M-14)]
overlap_cases=[(16,16,32,16),(16,16,31,16),(16,16,16,16),(16,16,15,1),(16,16,15,2),(M-15,16,M,1),(1,1,M,1),(1,M,1,1),(1,M,M,1),(1,16,2,2)]
checks=[];rows=[]
for at,size in extent_cases:
 expected_result=int(at!=0 and size!=0 and at+size-1<=M);checks.append(f'ok &= extent(UINT64_C({at}),UINT64_C({size}))=={expected_result};');rows.append(dict(function='extent',inputs=[at,size],expected=bool(expected_result)))
for at,size,bt,bs in overlap_cases:
 assert at and bt and size and bs and at+size-1<=M and bt+bs-1<=M
 expected_result=int(max(at,bt)<=min(at+size-1,bt+bs-1))
 for x,n,y,m in [(at,size,bt,bs),(bt,bs,at,size)]:checks.append(f'ok &= overlap(UINT64_C({x}),UINT64_C({n}),UINT64_C({y}),UINT64_C({m}))=={expected_result};')
 rows.append(dict(function='overlap-both-orders',inputs=[at,size,bt,bs],expected=bool(expected_result)))
# Empty ranges are outside these callers' proven nonzero-extent precondition.
# Characterize a counterexample without labeling it reachable or applying a fix.
empty=(16,0,15,2);checks.append('ok &= overlap(16,0,15,2)==1;')
header='#include <stddef.h>\n#include <stdint.h>\n_Static_assert(sizeof(uintptr_t)==8 && sizeof(size_t)==8,"64-bit host arithmetic required");\n'
source=header+'\n'.join(helpers)+'\nint main(void){int ok=1;\n'+'\n'.join(checks)+'\nreturn ok?0:1;}\n'
assert 'validate(' not in source and 'sha256(' not in source and '->' not in source
(O/'range-harness.c').write_text(source);save(O/'arithmetic-cases.json',rows)
clang=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang');commands=[ [str(clang),'-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined',str(O/'range-harness.c'),'-o',str(O/'range-check')],[str(O/'range-check')] ];events=[]
for i,cmd in enumerate(commands):
 r=subprocess.run(cmd,capture_output=True);(O/f'{i}.stdout.raw').write_bytes(r.stdout);(O/f'{i}.stderr.raw').write_bytes(r.stderr);events.append(dict(command=cmd,returncode=r.returncode,stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()));save(O/'events.json',events)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
assert sha(S)==expected
save(O/'result.json',dict(scope='isolated exact two integer helpers only;no validator/runtime or target compilation',primary_sha256=expected,helpers_sha256=hashlib.sha256('\n'.join(helpers).encode()).hexdigest(),extent_boundary_cases=12,overlap_boundary_pairs=10,both_order_assertions=20,empty_range_counterexample=dict(inputs=empty,observed=True,reachable_through_validate=False,reason='validate requires all5 memory extents and firmware extent nonzero before overlap;no patch warranted for out-of-domain use'),static_validator_review=dict(executes_sha256_callback=True,validator_compiled_or_executed=False,generated_policy_header_used=False,owner_or_coherency_proven=False),sanitizers_pass=True,primary_source_unchanged=True,compiler_sha256=sha(clang),no_source_patch_required=True,selected_startup_compiled=False,hardware_qualification=False,native_or_device_execution=False,generated_policy=False))
print('PASS:12 extent boundaries/10 overlap pairs both orders;empty-range domain characterized;no validator/callback/target execution')
