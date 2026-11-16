#!/usr/bin/env python3
"""Isolated snapshot output alias repair;no bind,publisher,native getters or successful backing peer."""
from pathlib import Path
import argparse,hashlib,json,difflib,subprocess
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False)
B=R/'UniXNU-zorn/native/gpu-owned/runtime/visibility';N=R/'UniXNU/drivers/NativeAdreno';K=R/'UniXNU/kits/ArmSmmu4K';source=B/'ZornGpuTableVisibility.cpp';header=B/'ZornGpuTableVisibility.h'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
original=source.read_text();profile=json.loads((B/'source-profile.json').read_text());assert sha(source)==profile['source_files']['UniXNU-zorn/native/gpu-owned/runtime/visibility/ZornGpuTableVisibility.cpp'];assert sha(header)==profile['source_files']['UniXNU-zorn/native/gpu-owned/runtime/visibility/ZornGpuTableVisibility.h']
needle=' if(!enter())return Busy;\n Report r=report_;'
replacement=''' if(!enter())return Busy;
 // A report destination must not overwrite a known writable table pool,
 // including cached pool metadata left by a rejected bind. No native getter.
 uintptr_t p=(uintptr_t)out;
 if(base_&&bytes_&&(p>=base_?p-base_<bytes_:base_-p<sizeof(*out))){leave();return Invalid;}
 Report r=report_;'''
assert original.count(needle)==1;pool_only=original.replace(needle,replacement)
(O/'candidate-pool-only.cpp').write_text(pool_only)
candidate=pool_only.replace(' uintptr_t p=(uintptr_t)out;',' uintptr_t p=(uintptr_t)out,owner=(uintptr_t)memory_;\n if(memory_&&(p>=owner?p-owner<sizeof(*memory_):owner-p<sizeof(*out))){leave();return Invalid;}')
(O/'original.cpp').write_text(original);(O/'candidate.cpp').write_text(candidate)
(O/'visibility-snapshot-pool.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/native/gpu-owned/runtime/visibility/ZornGpuTableVisibility.cpp',tofile='b/native/gpu-owned/runtime/visibility/ZornGpuTableVisibility.cpp')))
# Test-only friendship changes no fields or real header;only cached numeric
# metadata is injected.No NativeAdrenoMemory object or successful bind exists.
fixture=header.read_text().replace('private:\n','private:\n friend struct SnapshotMetadataProbe; /* isolated host harness only */\n');assert fixture!=header.read_text();(O/'ZornGpuTableVisibility.h').write_text(fixture)
harness=r'''#include "ZornGpuTableVisibility.h"
#include <cstring>
#include <cstdio>
struct SnapshotMetadataProbe {
 static void range(ZornGpuTableVisibility &v,unsigned char *base,size_t n){v.base_=(uintptr_t)base;v.bytes_=n;}
 static bool no_native_state(const ZornGpuTableVisibility &v){return !v.memory_&&!v.report_.bound&&!v.report_.native_attempts&&!v.report_.native_status_available;}
};
using V=ZornGpuTableVisibility;
static int run(const char *name,size_t out_at,bool collision){
 alignas(64) unsigned char storage[320];unsigned char before[320];memset(storage,0xa5,sizeof(storage));memcpy(before,storage,sizeof(storage));
 V v;SnapshotMetadataProbe::range(v,storage+128,64);
 auto *out=reinterpret_cast<V::Report*>(storage+out_at);
 int status=v.snapshot(out);bool pool_same=!memcmp(storage+128,before+128,64);
 bool all_same=!memcmp(storage,before,sizeof(storage));
 V::Report safe{};int unlocked=v.snapshot(&safe);
 bool empty=SnapshotMetadataProbe::no_native_state(v)&&!safe.runtime_complete&&!safe.bound;
 int expected=EXPECT_REPAIRED&&collision?V::Invalid:V::Ok;
 printf("%s status=%d pool_unchanged=%d all_unchanged=%d no_native=%d unlocked=%d\n",name,status,pool_same,all_same,empty,unlocked);
 return status==expected&&empty&&unlocked==V::Ok&&(collision?(EXPECT_REPAIRED?all_same:!pool_same):pool_same);
}
int main(){static_assert(sizeof(V::Report)%8==0,"report test alignment");int ok=1;
 ok&=run("pool-start",128,true);ok&=run("pool-tail",184,true);
 ok&=run("crosses-pool-start",128-sizeof(V::Report)+8,true);
 ok&=run("adjacent-before",128-sizeof(V::Report),false);ok&=run("adjacent-after",192,false);
 V unbound;V::Report report{};ok&=unbound.snapshot(&report)==V::Ok&&SnapshotMetadataProbe::no_native_state(unbound);
 puts(ok?"PASS:snapshot metadata only;no bind/callback/native object or getter":"FAIL");return ok?0:1;}
'''
(O/'harness.cpp').write_text(harness)
clang=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++');events=[]
def run(cmd):
 p=subprocess.run([str(x) for x in cmd],capture_output=True);i=len(events);(O/f'{i}.stdout.raw').write_bytes(p.stdout);(O/f'{i}.stderr.raw').write_bytes(p.stderr);events.append(dict(command=[str(x) for x in cmd],returncode=p.returncode,stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr).hexdigest()));save(O/'events.json',events)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace') or p.stdout.decode(errors='replace'))
 return p.stdout.decode()
flags=['-std=c++17','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',O,'-I',R/'out/zorn/gpu-native-visibility-publisher/host-include','-I',N,'-I',K]
outputs={}
for name,repair in [('original',0),('candidate',1)]:
 run([clang,*flags,'-DEXPECT_REPAIRED='+str(repair),O/(name+'.cpp'),O/'harness.cpp','-o',O/(name+'-check')]);outputs[name]=run([O/(name+'-check')])
assert sha(source)==profile['source_files']['UniXNU-zorn/native/gpu-owned/runtime/visibility/ZornGpuTableVisibility.cpp'];assert sha(header)==profile['source_files']['UniXNU-zorn/native/gpu-owned/runtime/visibility/ZornGpuTableVisibility.h']
result=dict(scope='host reproduction of cached metadata state only,not a real bind/backing/physical pool',overlap_cases_before_overwrote=3,overlap_cases_after_reject_without_write=3,adjacent_cases_preserved=2,unbound_snapshot_preserved=True,rejection_releases_lock=True,ASan_UBSan_pass=True,no_native_object_or_success_peer_constructed=True,no_bind_or_callback_or_getter_executed=True,source_files={str(p):sha(p) for p in [source,header,N/'NativeAdrenoMemory.h',K/'ArmSmmu4KLive.h']},native_sources_and_old_profile_unchanged=True,patch_state='independent UNAPPLIED;not selected/composed with32driverpatches',candidate_sha256=sha(O/'candidate.cpp'),patch_sha256=sha(O/'visibility-snapshot-pool.UNAPPLIED.patch'),compiler_sha256=sha(clang),host_outputs=outputs,old_suite_or_target_recompiled=False,device_operations=False)
save(O/'result.json',result);print(outputs['original']+outputs['candidate']+'PASS:3 actual snapshot writes reproduced/rejected;no native binding or provider peer')
