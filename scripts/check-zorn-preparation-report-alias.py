#!/usr/bin/env python3
"""Isolated preparation-report exclusions;no prepare,bind,getter,callback or native object execution."""
from pathlib import Path
import argparse,hashlib,json,difflib,subprocess
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False)
B=R/'UniXNU-zorn/native/gpu-owned/runtime/visibility';N=R/'UniXNU/drivers/NativeAdreno';K=R/'UniXNU/kits/ArmSmmu4K'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
profile=json.loads((B/'source-profile.json').read_text());cpp=B/'ZornGpuTablePreparation.cpp';hdr=B/'ZornGpuTablePreparation.h'
for p in [cpp,hdr]:assert sha(p)==profile['source_files'][str(p.relative_to(R))]
original=cpp.read_text();original_header=hdr.read_text()
header=original_header.replace(' Report report_{};uint32_t busy_=0;',''' Report report_{};uint32_t busy_=0;
 // Exclusions only,not ownership or usable mappings. The caller already
 // retains memory/arena/state for the full lifetime. Do not retain ephemeral
 // Geometry or callback-output storage as if their lifetime were guaranteed.
 struct BorrowedRange {uintptr_t base;size_t bytes;};
 BorrowedRange borrowed_[4]{};uint32_t borrowed_count_=0;
 bool outputClear(const void*,size_t) const;''')
assert header!=original_header
helper='''bool ZornGpuTablePreparation::outputClear(const void *p,size_t n) const {
 if(borrowed_count_>4)return false;
 uintptr_t out=(uintptr_t)p;
 for(uint32_t i=0;i<borrowed_count_;++i){const auto &r=borrowed_[i];
  if(!r.base||!r.bytes||r.bytes-1>UINTPTR_MAX-r.base)return false;
  if(out>=r.base?out-r.base<r.bytes:r.base-out<n)return false;
 }
 return true;
}
'''
candidate=original.replace('bool ZornGpuTablePreparation::zeroState(',helper+'bool ZornGpuTablePreparation::zeroState(')
needle=' if(out->cookie||out->publish_table_page||!zeroState(state))'
assert candidate.count(needle)==1
candidate=candidate.replace(needle,''' // Record only caller-retained metadata after argument extent/alias checks.
 borrowed_[0]={(uintptr_t)memory,sizeof(*memory)};
 borrowed_[1]={(uintptr_t)arena,sizeof(*arena)};
 borrowed_[2]={(uintptr_t)state,sizeof(*state)};borrowed_count_=3;
'''+needle)
needle=' void *pool=memory->mapping();size_t poolbytes=memory->bytes();'
assert candidate.count(needle)==1
candidate=candidate.replace(needle,needle+'''
 if(pool&&poolbytes&&poolbytes-1<=UINTPTR_MAX-(uintptr_t)pool){
  borrowed_[3]={(uintptr_t)pool,poolbytes};borrowed_count_=4;
 }''')
candidate=candidate.replace(' if(!enter())return Busy;Report copy=report_;',' if(!enter())return Busy;\n if(!outputClear(out,sizeof(*out))){leave();return Invalid;}\n Report copy=report_;')
candidate=candidate.replace(' if(!enter())return Busy;int result=publisher_.snapshot(out);leave();return result;',' if(!enter())return Busy;\n if(!outputClear(out,sizeof(*out))){leave();return Invalid;}\n int result=publisher_.snapshot(out);leave();return result;')
assert candidate.count('if(!outputClear(out,sizeof(*out)))')==2
for name,s,h in [('original',original,original_header),('candidate',candidate,header)]:
 d=O/name;d.mkdir();(d/'ZornGpuTablePreparation.cpp').write_text(s);(d/'ZornGpuTablePreparation.real.h').write_text(h);(d/'ZornGpuTablePreparation.h').write_text(h.replace('private:\n','private:\n friend struct ReportRangeProbe; /* host metadata fixture only */\n'))
patch=''.join(difflib.unified_diff(original_header.splitlines(True),header.splitlines(True),fromfile='a/native/gpu-owned/runtime/visibility/ZornGpuTablePreparation.h',tofile='b/native/gpu-owned/runtime/visibility/ZornGpuTablePreparation.h'))+''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/native/gpu-owned/runtime/visibility/ZornGpuTablePreparation.cpp',tofile='b/native/gpu-owned/runtime/visibility/ZornGpuTablePreparation.cpp'))
(O/'preparation-report-exclusions.UNAPPLIED.patch').write_text(patch)
harness=r'''#include "ZornGpuTablePreparation.h"
#include <cstring>
#include <cstdio>
using P=ZornGpuTablePreparation;using V=ZornGpuTableVisibility;
struct ReportRangeProbe {
 static void ranges(P &p,unsigned char *base){
#if EXPECT_REPAIRED
  const size_t sizes[]={sizeof(NativeAdrenoMemory),sizeof(ArmSmmu4KLiveArena),sizeof(ArmSmmu4KLiveState),192};
  for(unsigned i=0;i<4;++i)p.borrowed_[i]={(uintptr_t)(base+256+i*512),sizes[i]};p.borrowed_count_=4;
#else
  (void)p;(void)base;
#endif
 }
 static bool unqualified(const P &p){return !p.report_.native_attempted&&!p.report_.native_status_available&&!p.report_.callback_exported&&!p.report_.runtime_complete;}
#if EXPECT_REPAIRED
 static void corrupt(P &p,unsigned mode){if(mode==0)p.borrowed_count_=5;else {p.borrowed_count_=1;p.borrowed_[0]={UINTPTR_MAX-7,16};}}
#endif
};
static int call(P &p,bool publisher,void *out){return publisher?p.snapshotPublisher(static_cast<V::Report*>(out)):p.snapshot(static_cast<P::Report*>(out));}
static size_t report_size(bool publisher){return publisher?sizeof(V::Report):sizeof(P::Report);}
static int check(bool publisher,unsigned range,unsigned kind){
 alignas(64) unsigned char storage[2560];unsigned char before[2560];memset(storage,0xa5,sizeof(storage));memcpy(before,storage,sizeof(storage));P p;ReportRangeProbe::ranges(p,storage);
 size_t sizes[]={sizeof(NativeAdrenoMemory),sizeof(ArmSmmu4KLiveArena),sizeof(ArmSmmu4KLiveState),192};size_t base=256+range*512,n=report_size(publisher),at=base;bool collision=true;
 if(kind==1)at=base+sizes[range]-8;
 if(kind==2)at=base-n+8;
 if(kind==3){at=base-n;collision=false;}
 if(kind==4){at=base+sizes[range];collision=false;}
 int status=call(p,publisher,storage+at);bool same=!memcmp(storage,before,sizeof(storage));P::Report safe{};int unlocked=p.snapshot(&safe);
 int expected=EXPECT_REPAIRED&&collision?P::Invalid:P::Ok;bool no_native=ReportRangeProbe::unqualified(p)&&!safe.runtime_complete;
 bool ok=status==expected&&unlocked==P::Ok&&no_native&&(collision?(EXPECT_REPAIRED?same:!same):true);
 if(!ok)printf("FAIL publisher=%u range=%u kind=%u status=%d same=%d\n",publisher,range,kind,status,same);
 return ok;
}
int main(){int ok=1;for(unsigned publisher=0;publisher<2;++publisher)for(unsigned r=0;r<4;++r)for(unsigned kind=0;kind<5;++kind)ok&=check(publisher,r,kind);
 P empty;P::Report a{};V::Report b{};ok&=empty.snapshot(&a)==P::Ok&&empty.snapshotPublisher(&b)==P::Ok&&ReportRangeProbe::unqualified(empty);
#if EXPECT_REPAIRED
 for(unsigned mode=0;mode<2;++mode){P invalid;ReportRangeProbe::corrupt(invalid,mode);memset(&a,0xa5,sizeof(a));P::Report before=a;ok&=invalid.snapshot(&a)==P::Invalid&&!memcmp(&a,&before,sizeof(a));}
#endif
 printf("PASS=%d class_bytes=%zu collision_cases=24 adjacent_cases=16 no-native-or-getter-execution\n",ok,sizeof(P));return ok?0:1;}
'''
(O/'harness.cpp').write_text(harness);events=[];outputs={};clang=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++')
def run(cmd):
 p=subprocess.run([str(x) for x in cmd],capture_output=True);i=len(events);(O/f'{i}.stdout.raw').write_bytes(p.stdout);(O/f'{i}.stderr.raw').write_bytes(p.stderr);events.append(dict(command=[str(x) for x in cmd],returncode=p.returncode));save(O/'events.json',events)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace') or p.stdout.decode(errors='replace'))
 return p.stdout.decode()
for name,selected in [('original',0),('candidate',1)]:
 flags=['-std=c++17','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',O/name,'-I',B,'-I',R/'out/zorn/gpu-native-visibility-publisher/host-include','-I',N,'-I',K]
 run([clang,*flags,'-DEXPECT_REPAIRED='+str(selected),O/name/'ZornGpuTablePreparation.cpp',B/'ZornGpuTableVisibility.cpp',O/'harness.cpp','-o',O/(name+'-check')]);outputs[name]=run([O/(name+'-check')])
for p in [cpp,hdr]:assert sha(p)==profile['source_files'][str(p.relative_to(R))]
result=dict(scope='pure reporting methods over injected exclusion metadata;no native objects,prepare,getters,bind or callback execution',collision_cases_before_write=24,collision_cases_after_reject_unchanged=24,adjacent_cases_preserved=16,unbound_snapshot_methods_preserved=True,malformed_exclusion_metadata_refuses_unchanged=True,rejection_releases_lock=True,ASan_UBSan_pass=True,candidate_cpp_sha256=sha(O/'candidate/ZornGpuTablePreparation.cpp'),candidate_header_sha256=sha(O/'candidate/ZornGpuTablePreparation.real.h'),patch_sha256=sha(O/'preparation-report-exclusions.UNAPPLIED.patch'),main_sources_unchanged=True,old_child_visibility_patch_not_composed=True,headers_and_source={str(p):sha(p) for p in [cpp,hdr,B/'ZornGpuTableVisibility.cpp',B/'ZornGpuTableVisibility.h']},host_outputs=outputs,native_or_device_execution=False,old_suite_reexecuted=False)
save(O/'result.json',result);print(outputs['original']+outputs['candidate']+'PASS:24 report collisions independently repaired;no native provider or runtime selection')
