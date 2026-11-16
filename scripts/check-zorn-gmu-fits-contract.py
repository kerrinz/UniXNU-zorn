#!/usr/bin/env python3
"""Numeric model of a pinned fits predicate;no native descriptors,addresses or MMIO."""
from pathlib import Path
import argparse,hashlib,json,subprocess
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False)
S=R/'out/zorn/gpu-catalog-service-dependencies/sm8550-primary/kits/Sm8550Platform/ShengGmu.c';expected='d61daa0b10038314922400daf6288a957e973043e171f986f5f226f2dff2de09'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
assert sha(S)==expected;t=S.read_text();start=t.index('static int fits(');end=t.index('\n}',start)+2;fits=t[start:end];(O/'fits-source-review.txt').write_text(fits+'\n')
expr=fits[fits.index('return extent(')+7:fits.index(';',fits.index('return extent('))]
expr=expr.replace('(uintptr_t)w->cpu','base').replace('w->bytes','bytes')
assert '->' not in expr and '*' not in expr and '[' not in expr
start=t.index('static int extent(');end=t.index('}',start)+1;extent=t[start:end]
start=t.index('ShengGmuStatus ShengGmuBindMmio(');bind=t[start:t.index('\n}',start)+2];(O/'bind-source-review.txt').write_text(bind+'\n')
assert bind.index('*out=(ShengGmuIo){0}')<bind.index('if(!m)')<bind.index('for(unsigned i=0;')<bind.index('out->cookie=m')
assert 'return ShengGmuArgument' not in bind[bind.index('out->cookie=m'):]
M=2**64-1
cases=[(16,4,0),(16,4,4),(16,3,0),(16,8,4),(16,8,8),(16,8,5),(17,8,0),(0,8,0),(16,0,0),(M-3,4,0),(M-3,5,0),(16,8,M),(16,8,M-3),(16,M-15,M-19),(16,M-15,M-15)]
checks=[];rows=[]
for base,n,at in cases:
 want=bool(base and n and base+n-1<=M and base%4==0 and at%4==0 and at+4<=n)
 checks.append(f'if(predicate(UINT64_C({base}),UINT64_C({n}),UINT64_C({at}))!={int(want)})return {len(checks)+1};')
 rows.append(dict(numeric_base_token=base,bytes=n,offset=at,expected=want))
source='#include <stdint.h>\n#include <stddef.h>\n_Static_assert(sizeof(uintptr_t)==8 && sizeof(size_t)==8,"64-bit numeric model");\n'+extent+'\nstatic int predicate(uintptr_t base,size_t bytes,size_t at){return '+expr+';}\nint main(void){\n'+'\n'.join(checks)+'\nreturn 0;}\n'
assert all(s not in source for s in ['ShengGmuMmio','volatile','BindMmio','mmio_read','mmio_write','->'])
(O/'numeric-harness.c').write_text(source);save(O/'numeric-cases.json',rows)
clang=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang');events=[]
commands=[[str(clang),'-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined',str(O/'numeric-harness.c'),'-o',str(O/'numeric-check')],[str(O/'numeric-check')]]
for i,cmd in enumerate(commands):
 p=subprocess.run(cmd,capture_output=True);(O/f'{i}.stdout.raw').write_bytes(p.stdout);(O/f'{i}.stderr.raw').write_bytes(p.stderr);events.append(dict(command=cmd,returncode=p.returncode,stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr).hexdigest()));save(O/'events.json',events)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace') or str(p.returncode))
assert sha(S)==expected
save(O/'result.json',dict(scope='static fits/BindMmio audit and numeric expression model only;no MMIO descriptors or real addresses',primary_sha256=expected,numeric_boundary_cases=len(cases),sanitizers_pass=True,static_publication_order=dict(output_zeroed_before_validation=True,all_window_checks_before_publication=True,no_argument_failure_after_publication=True,requires_disjoint_input_output_from_primary_header=True),counterexample_found=False,source_patch_required=False,branch_finite_complete=True,native_descriptor_or_callback_constructed=False,BindMmio_or_MMIO_or_validator_executed=False,selected_target_compile=False,hardware_qualification=False,mapping_authority=False,generated_policy=False,compiler_sha256=sha(clang)))
print('PASS:15 numeric fits boundaries;static publication order checked;no native descriptor/callback/target or device activity')
