#!/usr/bin/env python3
"""Only extracted size arithmetic and an unselected object;never call allocate."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoGmuMemory.cpp';H=B/'NativeAdrenoGmuMemory.h'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S);(O/'original.cpp').write_text(old)
old_guard='''    if(sizes.icache>GmuUncachedBase-GmuIcacheIova ||
        sizes.dummy+sizes.log+sizes.hfi>GmuDebugIova-GmuUncachedBase ||
        sizes.debug>GmuApertureBytes-GmuDebugIova)return kIOReturnBadArgument;'''
new_guard='''    const uint64_t shared_bytes=GmuDebugIova-GmuUncachedBase;
    if(sizes.icache>GmuUncachedBase-GmuIcacheIova ||
        sizes.dummy>shared_bytes || sizes.log>shared_bytes-sizes.dummy ||
        sizes.hfi>shared_bytes-sizes.dummy-sizes.log ||
        sizes.debug>GmuApertureBytes-GmuDebugIova)return kIOReturnBadArgument;'''
assert old.count(old_guard)==1
new=old.replace(old_guard,new_guard,1);C=O/'NativeAdrenoGmuMemory.cpp';C.write_text(new)
assert new.replace(new_guard,old_guard,1)==old
(O/'gmu-size-sum.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/NativeAdrenoGmuMemory.cpp',tofile='b/NativeAdrenoGmuMemory.cpp')))
header=H.read_text();enum=re.search(r'enum : uint64_t \{.*?\n\};',header,re.S).group();pod=re.search(r'struct NativeAdrenoGmuSizes \{.*?\n\};',header,re.S).group()
prefix='''    const uint64_t requested[]={sizes.icache,sizes.dummy,sizes.debug,sizes.log,sizes.hfi};
    for(uint64_t value:requested)
        if(!value || (value&(0x1000-1)) || value>uint64_t(SIZE_MAX))
            return kIOReturnBadArgument;
'''
# The extracted block is the actual arithmetic predicate,not a native memory,
# successful allocator/provider or address model. The surrounding state/getter
# and ALL allocation/cleanup/mapping code are deliberately absent.
for name,guard in [('before',old_guard),('candidate',new_guard)]:
 code='#include <stdint.h>\n#include <stddef.h>\n#include <stdio.h>\n'+enum+'\n'+pod+'\nenum {kIOReturnBadArgument=-1};\n'
 code+='static int predicate(const NativeAdrenoGmuSizes &sizes){\n'+prefix+guard+'\nreturn 0;\n}\n'
 code+=r'''int main(){int ok=1;unsigned refused=0,passed_bad=0;
 const uint64_t huge=UINT64_MAX-4095,limit=GmuDebugIova-GmuUncachedBase;
 for(unsigned which=0;which<3;++which){NativeAdrenoGmuSizes s{4096,4096,4096,4096,4096};
  if(which==0)s.dummy=huge;else if(which==1)s.log=huge;else s.hfi=huge;
  int status=predicate(s);refused+=status!=0;passed_bad+=status==0;
#ifdef EXPECT_FIXED
  ok&=status==kIOReturnBadArgument;
#else
  ok&=status==0;
#endif
 }
 NativeAdrenoGmuSizes exact{4096,4096,4096,4096,limit-8192};
 ok&=predicate(exact)==0;exact.hfi+=4096;ok&=predicate(exact)==kIOReturnBadArgument;
 exact.hfi=limit-12288;ok&=predicate(exact)==0;
 printf("PASS=%d overflow_tuples_refused=%u overflow_tuples_accepted=%u exact_plus_page_and_below_preserved=3 no-native-call\n",ok,refused,passed_bad);return ok?0:1;}
'''
 (O/(name+'-arithmetic.cpp')).write_text(code)
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++';events=[]
def run(args,name,cwd=R):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=list(map(str,args)),directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout
outputs={}
for name in ['before','candidate']:
 args=[clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',O/(name+'-arithmetic.cpp'),'-o',O/(name+'-arithmetic')]
 if name=='candidate':args+=['-DEXPECT_FIXED=1']
 run(args,name+'-build');outputs[name]=run([O/(name+'-arithmetic')],name+'-run').decode()
assert 'overflow_tuples_accepted=3' in outputs['before'] and 'overflow_tuples_refused=3' in outputs['candidate']
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments'])
args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert version==17<<16 and sha(S)==pin
result=dict(scope='pure extracted size-preflight predicate only;allocate/objects never executed',original_SHA=pin,header_SHA=sha(H),candidate_SHA=sha(C),three_invalid_aligned_uint64_tuples_accepted_before_refused_after=True,three_inbudget_boundary_controls_preserved=True,host_outputs=outputs,ASan_UBSan_pass=True,default_callers_not_claimed_to_hit_overflow=True,public_size_input_range_contract_repaired=True,only_preallocation_size_guard_changed=True,new_candidate_iOS17_object_pass=True,object_SHA=sha(obj),object_not_linked_or_executed=True,no_native_object_getter_allocator_provider_or_address_model=True,existing_layout_constants_not_K80_policy=True,catalog_original_patches_and_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:3 actual size-predicate overflow witnesses rejected;3 boundary controls/sanitizers/new iOS17 module;no allocate or native call')
