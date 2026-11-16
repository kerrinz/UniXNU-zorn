#!/usr/bin/env python3
"""Pure property-byte parser transaction repair;no native objects or mapping rights."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
O=ap.parse_args().out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
S=B/'NativeAdrenoBoard.cpp';H=B/'NativeAdrenoBoard.h';original=S.read_text()
(O/'original.cpp').write_text(original);(O/H.name).write_bytes(H.read_bytes())
old='''        stream_ids[index]=static_cast<uint16_t>(sid);
    }
    *count=total;'''
new='''    }
    /* Validate the entire property before exposing any stream ID. A late bad
     * phandle/specifier must not leave a valid-looking output prefix. */
    for(size_t index=0;index<total;++index) {
        const uint8_t *at=cells+index*per_entry;
        stream_ids[index]=static_cast<uint16_t>(be32(at+CellBytes));
    }
    *count=total;'''
assert original.count(old)==1
candidate=original.replace(old,new);C=O/'candidate.cpp';C.write_text(candidate)
assert original[original.index('IOReturn NativeAdrenoBoard::parseReg'):]==candidate[candidate.index('IOReturn NativeAdrenoBoard::parseReg'):]
(O/'board-iommus-transaction.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/NativeAdrenoBoard.cpp',tofile='b/NativeAdrenoBoard.cpp')))
inc=O/'host-include/IOKit';inc.mkdir(parents=True)
(inc/'IOTypes.h').write_text('/* Host scalar statuses only;no native objects or provider. */\n#include <stdint.h>\ntypedef int32_t IOReturn;\nenum {kIOReturnSuccess=0,kIOReturnBadArgument=-1,kIOReturnNoResources=-2};\n')
harness=r'''#include "NativeAdrenoBoard.h"
#include <stdio.h>
#include <string.h>
static unsigned char raw[40];
static void cell(unsigned index,uint32_t value){for(unsigned i=0;i<4;++i)raw[index*4+i]=(uint8_t)(value>>(24-i*8));}
int main(){int ok=1;unsigned refused=0,preserved=0,overwritten=0,valid=0;
 for(unsigned spec=1;spec<=4;++spec){
  for(unsigned bad=0;bad<2;++bad){
   memset(raw,0,sizeof(raw));cell(0,1);cell(1,0x1234);cell(1+spec,bad?2:0);cell(2+spec,bad?0x10000:0x4321);
   uint16_t out[4]={0xa5a5,0xa5a5,0xa5a5,0xa5a5},saved[4];memcpy(saved,out,sizeof(out));size_t count=99;
   IOReturn result=NativeAdrenoBoard::parseIommus(raw,2*(1+spec)*4,spec,out,4,&count);
   bool same=!memcmp(saved,out,sizeof(out));++refused;preserved+=same;overwritten+=!same;
   ok&=result==kIOReturnBadArgument&&count==0&&out[1]==0xa5a5;
#ifdef EXPECT_TRANSACTION
   ok&=same;
#else
   ok&=!same&&out[0]==0x1234;
#endif
  }
  memset(raw,0,sizeof(raw));cell(0,1);cell(1,0);cell(1+spec,2);cell(2+spec,0xffff);
  uint16_t out[3]={3,3,0xbeef};size_t count=99;
  IOReturn result=NativeAdrenoBoard::parseIommus(raw,2*(1+spec)*4,spec,out,2,&count);
  ok&=result==kIOReturnSuccess&&count==2&&out[0]==0&&out[1]==0xffff&&out[2]==0xbeef;++valid;
 }
 printf("PASS=%d late_refusals=%u unchanged=%u overwritten=%u valid_property_layouts=%u no-native-or-mapping\n",ok,refused,preserved,overwritten,valid);return ok?0:1;}
'''
(O/'harness.cpp').write_text(harness)
clang=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++');events=[]
def run(cmd,name,cwd=R):
 p=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,timeout=45);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,command=list(map(str,cmd)),cwd=str(cwd),returncode=p.returncode));(O/'events.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout.decode()
outputs={}
for name,source in [('before',O/'original.cpp'),('candidate',C)]:
 cmd=[clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-I'+str(O),'-I'+str(O/'host-include'),source,O/'harness.cpp','-o',O/name]
 if name=='candidate':cmd+=['-DEXPECT_TRANSACTION=1']
 run(cmd,name+'-build');outputs[name]=run([O/name],name+'-run')
assert 'overwritten=8' in outputs['before'] and 'unchanged=8' in outputs['candidate']
# Compile only this changed candidate against the actual frozen iOS17 recipe
# and real XNU headers,never the scalar host shim or a selected driver target.
recipe=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'
rec=json.JSONDecoder().raw_decode(recipe.read_text())[0];args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args
assert not any(x in args for x in ['-MF','-MJ'])
args[args.index(rec['file'])]=str(C);obj=O/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-I'+str(O),'-mgeneral-regs-only','-MD','-MF',str(O/'candidate-inputs.d'),'-MT',str(obj)]
run(args,'candidate-ios17-build',Path(rec['directory']))
raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;version=None
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 cmd,size=struct.unpack_from('<II',raw,at)
 if cmd==0x32:platform,version=struct.unpack_from('<II',raw,at+8);assert platform==2
 at+=size
assert version==17<<16
assert sha(S)==hashlib.sha256(original.encode()).hexdigest()
result=dict(scope='pure DT property-byte parseIommus output transaction only;unselected UNAPPLIED candidate',original_CPP_SHA=sha(S),original_header_SHA=sha(H),candidate_CPP_SHA=sha(C),before_after_host_outputs=outputs,eight_late_failures_before_overwrite_after_unchanged=True,four_property_layouts_preserved=True,count_zero_on_failure_convention_preserved=True,parseReg_unchanged=True,ASan_UBSan_pass=True,changed_candidate_iOS17_object_pass=True,target_object_SHA=sha(obj),target_minimum_OS='17.0',target_object_not_linked_or_executed=True,real_target_headers_no_host_shim=True,catalog_unchanged=True,old_driver_patches_unmerged=True,old_suites_or_targets_rerun=False,native_objects_or_providers_executed=False,stream_ids_are_synthetic_file_values_not_route_permissions=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:8 late partial-output failures repaired;4 pure layouts preserved;sanitizers and new iOS17 object;no native/device')
