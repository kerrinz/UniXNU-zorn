#!/usr/bin/env python3
"""Timeline declared-byte preflight only; no ring, stamp or address execution."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct,re
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';S=B/'NativeAdrenoRing.cpp';H=B/'NativeAdrenoRing.h';old=S.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(S)
assert 'void setTimeline(bool on) {stamps_=on;}' in H.read_text()
assert old.count('fence_bytes<64')==2
start=old.index('IOReturn NativeAdrenoRing::submitWords(');anchor='    const uint32_t size_words=(uint32_t)(ring_bytes_/4),mask=size_words-1;';at=old.index(anchor,start)
guard='    if(framed && stamps_ && fence_bytes_<RingStampOffset+64*16)return kIOReturnBadArgument;\n'
new=old[:at]+guard+old[at:];C=O/'NativeAdrenoRing.cpp';C.write_text(new);(O/'original.cpp').write_text(old)
(O/'ring-timeline-extent.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/NativeAdrenoRing.cpp',tofile='b/NativeAdrenoRing.cpp')))
def sourcecheck(c):
 assert c.count(guard)==1 and c.replace(guard,'',1)==old
 body=c[c.index('IOReturn NativeAdrenoRing::submitWords('):]
 assert body.index(guard)<body.index('readRptr(&rptr)')<body.index('emitPrologue(')
sourcecheck(new);controls=[]
for name,c in [('removed',old),('off-by-one',new.replace('fence_bytes_<RingStampOffset+64*16','fence_bytes_<RingStampOffset+64*16-1',1)),('plain-only',new.replace('if(framed && stamps_','if(!framed && stamps_',1))]:
 try:sourcecheck(c)
 except (AssertionError,ValueError):controls.append(name)
 else:raise AssertionError(name)
offset=int(re.search(r'RingStampOffset = (\d+)',old).group(1));assert offset==512
# Numeric offsets only: end stamp stores two 32-bit words at slot+8.
# This is not an IOVA, mapped-memory or GPU stamp success model.
max_exclusive=offset+63*16+8+8;assert max_exclusive==offset+64*16
fixture='''#include <stddef.h>
#include <stdio.h>
static bool refused(bool framed,bool stamps,size_t bytes){return framed && stamps && bytes<1536;}
int main(){bool ok=true;const size_t short_counts[]={64,512,1535};
 for(size_t n:short_counts)ok &= refused(true,true,n);
 ok &= !refused(true,true,1536);ok &= !refused(true,true,4096);
 ok &= !refused(false,true,64);ok &= !refused(true,false,64);
 printf("ok=%d short_declared_counts=3 boundary_controls=4 scalar-only\\n",ok);return ok?0:1;}
'''
# Bind fixture expression to the source's extracted predicate and offset constant.
expr=guard.split('if(',1)[1].split(')return',1)[0].replace('stamps_','stamps').replace('fence_bytes_','bytes').replace('RingStampOffset',str(offset));fixture=fixture.replace('framed && stamps && bytes<1536',expr)
F=O/'extent-scalar.cpp';F.write_text(fixture);events=[]
def run(args,name,cwd=R):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout.decode()
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++';run([clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',F,'-o',O/'extent-scalar'],'scalar-build');output=run([O/'extent-scalar'],'scalar-run')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments']);args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)];run(args,'candidate-ios17',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,n=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=n
assert ver==17<<16 and sha(S)==pin
result=dict(scope='declared fence-buffer byte count before framed timeline packet emission',original_SHA=pin,candidate_SHA=sha(C),original_attach_accepts_fence_bytes_at_least_64=True,original_timeline_reader_has_extent_guard_but_writer_preflight_missing=True,original_public_setTimeline_does_not_check_extent=True,required_declared_bytes=max_exclusive,three_short_counts_previously_unchecked_now_refused=[64,512,1535],four_boundary_mode_controls_preserved=True,three_source_mutations_refused=controls,scalar_output=output,ASan_UBSan_pass=True,new_iOS17_Ring_object_pass=True,object_not_linked_or_executed=True,only_new_preflight_no_packet_log_or_layout_changes=True,no_ring_words_address_IOVA_stamp_callback_cache_or_native_success_model=True,actual_K80_short_fence_not_claimed=True,old_commit_patch_and_32patches_not_combined=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:timeline fence extent source witness/3 short counts/4 controls/3 mutations/sanitizers/new Ring iOS17 object;no native calls')
