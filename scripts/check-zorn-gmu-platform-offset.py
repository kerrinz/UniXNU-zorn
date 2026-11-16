#!/usr/bin/env python3
"""Check only exported offset predicate arithmetic; never bind or invoke MMIO."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoGmuPlatform.cpp';H=B/'NativeAdrenoGmuPlatform.h'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=S.read_text();pin=sha(S);header=H.read_text()
assert 'Every access is 4-byte aligned and inside its window' in header
assert 'built.read32=read32;built.write32=write32' in old
before='(at&3) || at+4>bounds.bytes';after='(at&3) || at>bounds.bytes || bounds.bytes-at<4'
assert old.count(before)==2
new=old.replace(before,after);C=O/'NativeAdrenoGmuPlatform.cpp';C.write_text(new);(O/'original.cpp').write_text(old)
assert new.replace(after,before)==old
(O/'gmu-platform-offset.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/NativeAdrenoGmuPlatform.cpp',tofile='b/NativeAdrenoGmuPlatform.cpp')))
def check_source(candidate):
 assert candidate.count(after)==2 and before not in candidate
 assert candidate.replace(after,before)==old
controls=[]
for name,text in [('read-old-guard',new.replace(after,before,1)),('write-old-guard',new.rsplit(after,1)[0]+before+new.rsplit(after,1)[1]),('removed-upper-limit',new.replace('at>bounds.bytes || ','',1))]:
 try:check_source(text)
 except AssertionError:controls.append(name)
 else:raise AssertionError(name)
check_source(new)
events=[]
def run(args,name,cwd=R):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50)
 (O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr)
 events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n')
 assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout.decode()
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++'
outputs={}
for name,expr in [('before',before),('candidate',after)]:
 # Only the integer subexpression is extracted. No bounds.base, object,
 # window, callback, address, provider or MMIO operation is represented.
 code='#include <stdint.h>\n#include <stddef.h>\n#include <stdio.h>\nstatic bool refused(size_t at,size_t bytes){struct {size_t bytes;} bounds{bytes};return '+expr+';}\n'
 code+='''int main(){bool ok=true;unsigned bad_pass=0,bad_refused=0;
 for(size_t bytes:{size_t(4),size_t(64),size_t(UINT32_MAX-3)}){
  bool no=refused(SIZE_MAX-3,bytes);bad_pass+=!no;bad_refused+=no;
#ifdef FIXED
  ok &= no;
#else
  ok &= !no;
#endif
 }
 const size_t cases[][3]={{0,4,0},{4,8,0},{8,8,1},{5,64,1},{64,64,1},{0,0,1},{UINT32_MAX-7,UINT32_MAX-3,0},{UINT32_MAX-3,UINT32_MAX-3,1}};
 for(auto &c:cases)ok &= refused(c[0],c[1])==bool(c[2]);
 printf("ok=%d overflow_pass=%u overflow_refused=%u controls=8 scalar-only\\n",ok,bad_pass,bad_refused);return ok?0:1;}
'''
 # Avoid library initializer-list dependencies in the freestanding predicate fixture.
 code=code.replace('for(size_t bytes:{size_t(4),size_t(64),size_t(UINT32_MAX-3)})','const size_t extents[]={4,64,UINT32_MAX-3}; for(size_t bytes:extents)')
 src=O/(name+'-scalar.cpp');src.write_text(code)
 args=[clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',src,'-o',O/(name+'-scalar')]
 if name=='candidate':args+=['-DFIXED=1']
 run(args,name+'-build');outputs[name]=run([O/(name+'-scalar')],name+'-run')
assert 'overflow_pass=3' in outputs['before'] and 'overflow_refused=3' in outputs['candidate']
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
result=dict(scope='exported callback public offset contract, extracted integer subexpression only',original_SHA=pin,header_SHA=sha(H),candidate_SHA=sha(C),host_outputs=outputs,three_overflow_witnesses_refused_after=True,eight_controls_preserved=True,source_mutations_refused=controls,ASan_UBSan_pass=True,only_two_integer_guards_changed=True,public_size_t_offset_abi_preserved=True,layout_bind_publication_and_services_unchanged=True,new_iOS17_object_pass=True,object_SHA=sha(obj),no_target_link_or_execution=True,no_native_object_bind_callback_window_base_address_or_provider_model=True,actual_K80_or_generated_caller_trigger_not_claimed=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:3 scalar wrap witnesses/8 controls/3 source mutations;new iOS17 object;no MMIO or callbacks')
