#!/usr/bin/env python3
"""Isolated four-byte stores only, never build/pack a power-up policy list."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoPwrup.cpp';old=S.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(S)
a='    uint32_t *cursor=reinterpret_cast<uint32_t *>(out+HeaderBytes);'
b='''    uint8_t *cursor=out+HeaderBytes;
    const auto word=[&](uint32_t value) {
        memcpy(cursor,&value,sizeof(value));cursor+=sizeof(value);
    };'''
assert old.count(a)==1
new=old.replace(a,b,1)
for expr in ['ifpc_regs[i]','ifpc_values[i]','preemption_regs[i]','preemption_values[i]','dynamic_triplets[i*3]','dynamic_triplets[i*3+1]','dynamic_triplets[i*3+2]']:
 assert new.count('*cursor++='+expr+';')==1;new=new.replace('*cursor++='+expr+';','word('+expr+');',1)
C=O/S.name;C.write_text(new);(O/'original.cpp').write_text(old)
inv=new.replace(b,a,1)
for expr in ['ifpc_regs[i]','ifpc_values[i]','preemption_regs[i]','preemption_values[i]','dynamic_triplets[i*3]','dynamic_triplets[i*3+1]','dynamic_triplets[i*3+2]']:inv=inv.replace('word('+expr+');','*cursor++='+expr+';',1)
assert inv==old
(O/'pwrup-byte-store.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+S.name,tofile='b/'+S.name)))
controls=[]
for name,c in [('typed-store-restored',new.replace('memcpy(cursor,&value,sizeof(value));','*reinterpret_cast<uint32_t *>(cursor)=value;',1)),('short-copy',new.replace('memcpy(cursor,&value,sizeof(value));','memcpy(cursor,&value,3);',1)),('short-step',new.replace('cursor+=sizeof(value);','cursor+=3;',1))]:
 if b not in c:controls.append(name)
 else:raise AssertionError(name)
events=[]
def run(args,name,cwd=R,good=True):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n')
 if good:assert p.returncode==0,p.stderr.decode(errors='replace')
 else:assert p.returncode!=0 and b'misaligned address' in p.stderr
 return p.stdout.decode()
# Fixture is only the removed store operation/new byte-copy helper. It has
# no register arrays, list header, counts, GPU address, policy or pack() body.
pre='#include <stdint.h>\n#include <string.h>\n#include <stdio.h>\n'
before=pre+'int main(){alignas(4) uint8_t raw[12]{};uint32_t *cursor=reinterpret_cast<uint32_t *>(raw+1);*cursor++=0x01020304u;return raw[1]==4?0:1;}\n'
after=pre+'''int main(){bool ok=true;for(unsigned offset=0;offset<4;++offset){alignas(4) uint8_t raw[16]{};uint8_t *cursor=raw+offset;
 const auto word=[&](uint32_t value){memcpy(cursor,&value,sizeof(value));cursor+=sizeof(value);};
 const uint32_t pattern=0x01020304u;word(pattern);word(0);
 ok &= !memcmp(raw+offset,&pattern,4);for(unsigned i=4;i<8;++i)ok &= raw[offset+i]==0;
 ok &= cursor==raw+offset+8;
 for(unsigned i=0;i<offset;++i)ok &= raw[i]==0;
 for(unsigned i=offset+8;i<16;++i)ok &= raw[i]==0;}
 printf("ok=%d byte_alignments=4 canaries_and_native_byte_order_preserved no-policy-list\\n",ok);return ok?0:1;}
'''
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++'
for name,code in [('before',before),('candidate',after)]:
 f=O/(name+'-store.cpp');f.write_text(code);run([clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',f,'-o',O/(name+'-store')],name+'-build');run([O/(name+'-store')],name+'-run',good=name!='before')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)];run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
res=dict(scope='unaligned uint8_t output store contract; isolated 4-byte store only',original_SHA=pin,candidate_SHA=sha(C),before_isolated_store_UBSan_misaligned_failure_preserved=True,after_four_byte_alignments_canaries_native_order_pass=True,source_mutations_refused=controls,new_Pwrup_iOS17_object_pass=True,object_not_linked_or_executed=True,all_list_counts_limits_order_layout_and_callbacks_unchanged=True,no_buildA740_pack_policy_list_register_read_callback_native_or_provider_execution=True,no_generated_or_selected_power_rate_vote_bin_variant_policy=True,no_actual_K80_unaligned_buffer_claimed=True,firmware_alias_review='only retained Service caller has local rules,member firmware view,and external embedded image;no concrete alias found,no alias patch or validate/SHA execution',catalog_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(res,indent=2)+'\n');print('PASS:isolated original unaligned store UBSan failure;4 candidate byte alignments/3 source controls/new iOS17 module;no pack or policy execution')
