#!/usr/bin/env python3
"""Public reserve cardinality contract;pure arithmetic,never construct an index."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';H=B/'NativeAdrenoHandleIndex.h'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=H.read_text();pin=sha(H);(O/'original.h').write_text(old)
old_body='''        if(!cells_)return false;
        while(keys*2>size_)if(!grow())return false;'''
new_body='''        if(!cells_ || keys>SIZE_MAX/2)return false;
        while(keys>size_/2)if(!grow())return false;'''
assert old.count(old_body)==1
new=old.replace(old_body,new_body,1);C=O/H.name;C.write_text(new)
(O/'handle-reserve-width.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+H.name,tofile='b/'+H.name)))
assert new.replace(new_body,old_body,1)==old
# Cardinalities only: no cell pointer, native index/allocator/provider, or live
# handle is represented. Test the exact loop comparison and new early bound.
prefix='#include <stddef.h>\n#include <stdint.h>\n#include <stdio.h>\n'
for name,expr in [('before','keys*2>size'),('candidate','keys>size/2')]:
 source=prefix+'static int decision(size_t keys,size_t size){\n'
 if name=='candidate':source+='if(keys>SIZE_MAX/2)return -1;\n'
 source+='return '+expr+'?1:0;\n}\n'
 source+=r'''int main(){int ok=1;unsigned bypass=0,reject=0,controls=0;
 size_t half=SIZE_MAX/2+1;
 for(size_t delta=0;delta<3;++delta){int d=decision(half+delta,64);
#ifdef EXPECT_FIXED
  ok&=d==-1;reject+=d==-1;
#else
  ok&=d==0;bypass+=d==0;
#endif
 }
 const size_t cases[][3]={{0,64,0},{31,64,0},{32,64,0},{33,64,1},{64,128,0},{65,128,1},{SIZE_MAX/2,SIZE_MAX-1,0}};
 for(const auto &c:cases){ok&=decision(c[0],c[1])==(int)c[2];++controls;}
 printf("PASS=%d impossible_key_counts_bypassing_growth=%u rejected=%u cardinality_controls=%u no-index-or-handles\n",ok,bypass,reject,controls);return ok?0:1;}
'''
 (O/(name+'-arithmetic.cpp')).write_text(source)
events=[];clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++'
def run(args,name,cwd=R):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=list(map(str,args)),directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout
outputs={}
for name in ['before','candidate']:
 args=[clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',O/(name+'-arithmetic.cpp'),'-o',O/(name+'-arithmetic')]
 if name=='candidate':args+=['-DEXPECT_FIXED=1']
 run(args,name+'-build');outputs[name]=run([O/(name+'-arithmetic')],name+'-run').decode()
assert 'bypassing_growth=3' in outputs['before'] and 'rejected=3' in outputs['candidate']
# Compile the ACTUAL changed inline method with actual kernel allocator
# declarations. This internal,unlinked compile fixture takes an unbound pointer;
# no object is instantiated and its allocation paths are never executed.
fixture=O/'compile-reserve.cpp';fixture.write_text('#include "NativeAdrenoHandleIndex.h"\nstatic_assert(sizeof(NativeAdrenoHandleIndex)==24);\n[[maybe_unused]] static __attribute__((used,noinline)) bool review_only_reserve(NativeAdrenoHandleIndex *unbound,size_t keys){return unbound->reserve(keys);}\n')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments'])
args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ'])
args[args.index(service)]=str(fixture);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-I'+str(O),'-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert version==17<<16 and sha(H)==pin
assert str(C) in (O/'candidate-inputs.d').read_text()
result=dict(scope='public reserve cardinality preflight contract;not current caller-triggered GPU bug',original_header_SHA=pin,candidate_header_SHA=sha(C),three_impossible_cardinalities_bypass_old_growth_and_now_refuse=True,seven_scalar_controls_preserved=True,host_outputs=outputs,ASan_UBSan_pass=True,current_UserClient_and_VM_cardinalities_below_wrap_region=True,old_VM_capacity_review_not_reexecuted=True,only_reserve_guard_comparison_changed=True,no_class_field_or_layout_change=True,actual_candidate_inline_method_iOS17_object_pass=True,object_SHA=sha(obj),internal_compile_fixture_never_instantiated_or_called=True,no_selected_component_or_runtime_caller=True,object_not_linked_or_executed=True,real_allocator_imports_are_compile_dependencies_not_execution=True,original_catalog_and_32patches_profiles_unchanged=True,no_native_index_allocator_provider_or_success_handle_model=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:3 public reserve cardinality overflow witnesses now reject;7 controls/sanitizers/new inline iOS17 object;no index/native execution')
