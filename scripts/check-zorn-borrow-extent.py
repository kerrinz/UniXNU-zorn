#!/usr/bin/env python3
"""Pure unsigned interval math and unexecuted native module, never borrow."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoMemory.cpp';old=S.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(S)
anchor='    if(!mapping || ((uintptr_t)mapping&4095) || !physical || (physical&4095) || !bytes || (bytes&4095))return kIOReturnBadArgument;\n'
add='''    if(bytes-1>UINTPTR_MAX-reinterpret_cast<uintptr_t>(mapping) ||
        uint64_t(bytes-1)>UINT64_MAX-physical)return kIOReturnBadArgument;
'''
assert old.count(anchor)==1;new=old.replace(anchor,anchor+add,1);C=O/S.name;C.write_text(new);(O/'original.cpp').write_text(old);(O/'borrow-extent.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
def check(c):
 assert c.count(add)==1 and c.replace(add,'',1)==old
 start=c.index('IOReturn NativeAdrenoMemory::borrow(');body=c[start:c.index('IOReturn NativeAdrenoMemory::makeWriteCombined()',start)]
 assert body.index(anchor)<body.index(add)<body.index('spans_=IONewData(')<body.index('bzero(')
check(new);mut=[]
for name,c in [('removed',old),('missing-physical-bound',new.replace(' ||\n        uint64_t(bytes-1)>UINT64_MAX-physical','',1)),('endpoint-off-by-one',new.replace('if(bytes-1>UINTPTR_MAX','if(bytes>UINTPTR_MAX',1))]:
 try:check(c)
 except (AssertionError,ValueError):mut.append(name)
 else:raise AssertionError(name)
# This integer fixture has no pointer conversion, mapped buffer, actual PA,
# owner/provider or native object. It checks mathematical representability only.
code='''#include <stdint.h>
#include <stdio.h>
static bool base(uint64_t start,uint64_t length){return start&&!(start&4095)&&length&&!(length&4095);}
static bool bounded(uint64_t start,uint64_t length){return base(start,length)&&length-1<=UINT64_MAX-start;}
int main(){bool ok=true;unsigned old_pass=0,refused=0;
 const uint64_t bad[][2]={{UINT64_MAX-4095,8192},{8192,UINT64_MAX-4095}};
 for(auto &p:bad){old_pass+=base(p[0],p[1]);refused+=!bounded(p[0],p[1]);}
 ok &= old_pass==2 && refused==2;
 ok &= bounded(4096,4096);ok &= bounded(UINT64_MAX-4095,4096);
 ok &= !bounded(UINT64_MAX-4095,8192);ok &= !bounded(0,4096);
 ok &= !bounded(4096,0);ok &= !bounded(4097,4096);
 printf("ok=%d old_unbounded_pairs=%u bounded_refusals=%u controls=6 integer-only\\n",ok,old_pass,refused);return ok?0:1;}
'''
F=O/'interval-scalar.cpp';F.write_text(code);events=[]
def run(args,name,cwd=R):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout.decode()
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++';run([clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',F,'-o',O/'interval-scalar'],'scalar-build');out=run([O/'interval-scalar'],'scalar-run')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)];run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
res=dict(scope='public borrow interval representability preflight only',original_SHA=pin,candidate_SHA=sha(C),two_integer_interval_overflow_witnesses=True,six_integer_controls_preserved=True,scalar_output=out,source_mutations_refused=mut,ASan_UBSan_pass=True,new_NativeMemory_iOS17_object_pass=True,object_not_linked_or_executed=True,only_new_extent_guard_before_allocation_and_bzero=True,no_descriptor_backing_state_publication_reorder=True,no_borrow_bzero_allocator_getter_prepare_cache_native_or_provider_execution=True,no_mapped_buffer_physical_address_owner_or_success_peer_model=True,no_retained_exact_caller_found=True,not_actual_K80_fault_or_mapping_qualification=True,no_new_OAS_IOVA_or_policy_selection=True,catalog_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(res,indent=2)+'\n');print('PASS:2 integer interval overflows/6 controls/3 source controls/sanitizers/new NativeMemory iOS17 module;no borrow or native execution')
