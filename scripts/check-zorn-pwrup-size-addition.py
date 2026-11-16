#!/usr/bin/env python3
"""Pure required-size addition only; no pack, register list or native work."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct,re
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoPwrup.cpp';old=S.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(S)
a='size_t(counts.ifpc+counts.preemption)*PairBytes';b='(size_t(counts.ifpc)+size_t(counts.preemption))*PairBytes';assert old.count(a)==1;new=old.replace(a,b,1);C=O/S.name;C.write_text(new);(O/'original.cpp').write_text(old);(O/'pwrup-size-addition.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)));assert new.replace(b,a,1)==old
header=(B/'NativeAdrenoPwrup.h').read_text();pod=re.search(r'struct NativeAdrenoPwrupCounts \{.*?\n\};',header,re.S).group(0);constants=re.search(r'enum : size_t \{.*?\};',old).group(0);body=re.search(r'size_t NativeAdrenoPwrupList::requiredBytes\(.*?\n\}',old,re.S).group(0).replace('NativeAdrenoPwrupList::requiredBytes','required')
events=[]
def run(args,name,cwd=R):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout.decode()
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++';outputs={}
for name in ['before','candidate']:
 func=body if name=='before' else body.replace(a,b)
 code='#include <stdint.h>\n#include <stddef.h>\n#include <stdio.h>\n'+constants+'\n'+pod+'\n'+func+'''
int main(){bool ok=true;unsigned mismatch=0;
 const NativeAdrenoPwrupCounts bad[]={{UINT32_MAX,1,0},{1,UINT32_MAX,0},{UINT32_MAX,UINT32_MAX,UINT32_MAX}};
 for(auto &c:bad){const uint64_t expected=16+(uint64_t(c.ifpc)+uint64_t(c.preemption))*8+uint64_t(c.dynamic)*12;bool same=required(c)==expected;mismatch+=!same;
#ifdef FIXED
 ok &= same;
#else
 ok &= !same;
#endif
 }
 const NativeAdrenoPwrupCounts legal[]={{0,0,0},{255,255,65535},{0,16,0}};
 for(auto &c:legal){uint64_t expected=16+(uint64_t(c.ifpc)+c.preemption)*8+uint64_t(c.dynamic)*12;ok &= required(c)==expected;}
 printf("ok=%d wide_sum_mismatches=%u legal_controls=3 size-only-no-policy\\n",ok,mismatch);return ok?0:1;}
'''
 f=O/(name+'-counts.cpp');f.write_text(code);args=[clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',f,'-o',O/(name+'-counts')]
 if name=='candidate':args+=['-DFIXED=1']
 run(args,name+'-build');outputs[name]=run([O/(name+'-counts')],name+'-run')
assert 'wide_sum_mismatches=3' in outputs['before'] and 'wide_sum_mismatches=0' in outputs['candidate']
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)];run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
res=dict(scope='public requiredBytes integer addition before widening',original_SHA=pin,candidate_SHA=sha(C),three_wide_count_tuples_wrong_before_correct_after=True,three_legal_count_controls_unchanged=True,host_outputs=outputs,ASan_UBSan_pass=True,only_operands_widened_before_sum=True,new_changed_Pwrup_iOS17_object_pass=True,object_not_linked_or_executed=True,pack_rejects_these_large_counts_before_requiredBytes_call=True,no_pack_overrun_or_actual_K80_trigger_claimed=True,no_pack_buildA740_register_list_policy_allocator_native_or_provider_execution=True,no_rate_vote_variant_or_component_selection=True,previous_alignment_candidate_not_combined=True,catalog_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(res,indent=2)+'\n');print('PASS:3 public size-sum witnesses/3 legal controls/sanitizers/new changed module;pack remains unexecuted and rejects large counts')
