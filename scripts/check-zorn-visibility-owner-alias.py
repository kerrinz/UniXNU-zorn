#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,hashlib,argparse
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description='Additional opaque metadata output-alias regression;no native peer');ap.add_argument('--capsule',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.capsule.resolve();T=a.out.resolve();T.mkdir(exist_ok=False)
harness=r'''#include "ZornGpuTableVisibility.h"
#include <cstring>
#include <cstdio>
struct SnapshotMetadataProbe {
 static void owner(ZornGpuTableVisibility &v,void *p){v.memory_=static_cast<NativeAdrenoMemory*>(p);}
 static bool unqualified(const ZornGpuTableVisibility &v){return !v.report_.bound&&!v.report_.native_attempts&&!v.report_.native_status_available&&!v.base_&&!v.bytes_;}
};
using V=ZornGpuTableVisibility;
static int check(const char *name,size_t offset,bool overlaps){
 alignas(64) unsigned char storage[512];unsigned char before[512];memset(storage,0xa5,sizeof(storage));memcpy(before,storage,sizeof(storage));
 V v;SnapshotMetadataProbe::owner(v,storage+128);auto *out=reinterpret_cast<V::Report*>(storage+offset);
 int status=v.snapshot(out);bool unchanged=!memcmp(storage,before,sizeof(storage));V::Report safe{};int again=v.snapshot(&safe);
 bool unqualified=SnapshotMetadataProbe::unqualified(v)&&!safe.runtime_complete&&!safe.bound;
 printf("%s status=%d unchanged=%d unqualified=%d unlocked=%d\n",name,status,unchanged,unqualified,again);
 return status==(EXPECT_REPAIRED&&overlaps?V::Invalid:V::Ok)&&unqualified&&again==V::Ok&&(overlaps?(EXPECT_REPAIRED?unchanged:!unchanged):true);
}
int main(){static_assert(sizeof(NativeAdrenoMemory)%8==0,"metadata extent test alignment");int ok=1;
 ok&=check("owner-start",128,true);ok&=check("owner-tail",128+sizeof(NativeAdrenoMemory)-8,true);
 ok&=check("cross-owner-start",128-sizeof(V::Report)+8,true);ok&=check("adjacent-before",128-sizeof(V::Report),false);ok&=check("adjacent-after",128+sizeof(NativeAdrenoMemory),false);
 puts(ok?"PASS:opaque metadata token only;no native object construction/dereference/getter/bind":"FAIL");return ok?0:1;}
'''
(T/'harness.cpp').write_text(harness);clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++';flags=['-std=c++17','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(O),'-I',str(R/'out/zorn/gpu-native-visibility-publisher/host-include'),'-I',str(R/'UniXNU/drivers/NativeAdreno'),'-I',str(R/'UniXNU/kits/ArmSmmu4K')];events=[];outputs={}
for name,source,select in [('before',O/'candidate-pool-only.cpp',0),('after',O/'candidate.cpp',1)]:
 commands=[[clang,*flags,'-DEXPECT_REPAIRED='+str(select),str(source),str(T/'harness.cpp'),'-o',str(T/(name+'-check'))],[str(T/(name+'-check'))]]
 for cmd in commands:
  p=subprocess.run(cmd,capture_output=True);i=len(events);(T/f'{i}.stdout.raw').write_bytes(p.stdout);(T/f'{i}.stderr.raw').write_bytes(p.stderr);events.append(dict(command=cmd,returncode=p.returncode));(T/'events.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace') or p.stdout.decode(errors='replace')
 outputs[name]=p.stdout.decode()
r=dict(scope='additional opaque owner-metadata alias branch,not a native object or successful backend',before_owner_collisions_accepted=3,after_owner_collisions_rejected=3,adjacent_outputs_preserved=2,rejection_unlocks=True,no_native_object_constructed_or_dereferenced=True,no_getters_or_bind_or_callbacks=True,prior_pool_case_suite_not_rerun=True,ASan_UBSan_pass=True,outputs=outputs,candidate_sha256=hashlib.sha256((O/'candidate.cpp').read_bytes()).hexdigest());(T/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(outputs['before']+outputs['after'])
