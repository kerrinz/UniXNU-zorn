from pathlib import Path
import json,subprocess,hashlib,os
import argparse
p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--alias-header',required=True,type=Path);options262=p.parse_args();S=options262.source_root.resolve();O=options262.out.resolve();O.mkdir();t=(S/'direct-runtime/ZornGen7DirectVm26.cpp').read_text();a=t.index('IOReturn ZornGen7DirectVm26::preflight(');z=t.index('ZornGen7DirectVm26::Mapping *',a);actual=t[a:z];board=(S/'ZornGen7DarwinBoardOwner.cpp').read_text();import re
selected=re.findall(r'prepareHostDirectRuntime\(board,runtime,(\d+)\)',board);assert selected==['8192'];chosen=int(selected[0]);assert chosen<=262144
helpers=t[t.index('static bool overlap('):t.index('static void reverse(')];alias=options262.alias_header.resolve()
prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <vector>
#include <cstdio>
#include "ZornClientFailure261.h"
#include "ALIAS_HEADER"
using IOReturn=uint32_t;
constexpr IOReturn kIOReturnSuccess=0,kIOReturnBadArgument=0xe00002c2,kIOReturnBusy=0xe00002d5,kIOReturnNoResources=0xe00002be;
constexpr unsigned ZornSmmuSparse4KRead=1,ZornSmmuSparse4KPrivileged=8;
constexpr size_t ZornGen7DirectVm26MaxObjects=4096;
struct Span {uint64_t physical=0x80000000,offset=0,bytes=16384;};
struct NativeAdrenoMemory {bool valid=true,quarantine=false;size_t length=16384,count=1;Span span{};const Span*external=nullptr;bool backed()const{return valid;}bool quarantined()const{return quarantine;}size_t bytes()const{return length;}size_t spanCount()const{return count;}const Span *spans()const{return external?external:&span;}};
struct ZornSmmuSparse4KRange {uint64_t iova=0,physical=0,bytes=4096;unsigned permissions=1,writeback=0,shareability=2;};
struct ZornSmmuSparse4KLiveArena {uint64_t iova=0x100000000,bytes=uint64_t(1)<<36;struct {unsigned output_bits=40;}config;uint32_t *alias_scratch=nullptr;size_t alias_scratch_entries=0;};
struct Tables {bool overlaps(uint64_t,uint64_t)const{return false;}};
static uint64_t zorn_direct_vm_alias_paths[2];static unsigned notes,stage,reason,d0,d1,rawNote;
extern "C" void zorn_failure_note261(uint32_t s,uint32_t raw,uint32_t kind,uint32_t r,uint32_t a,uint32_t b){assert(kind==ZornFailureBackend261);++notes;stage=s;rawNote=raw;reason=r;d0=a;d1=b;}
class ZornGen7DirectVm26 {public:
 struct Region {ZornSmmuSparse4KLiveArena *arena=nullptr;Tables *tables=nullptr;};
 size_t objects_=0,capacity_=4096,lower_count_=0,upper_count_=0;Region regions_[2]{};ZornSmmuSparse4KRange *ranges_=nullptr;uint32_t *alias_scratch_=nullptr;
 size_t spanCount()const{return lower_count_+upper_count_;}
 IOReturn preflight(const NativeAdrenoMemory *,unsigned,uint64_t,unsigned,unsigned,unsigned)const;
};
'''.replace('ALIAS_HEADER',str(alias))
main=r'''
int main(){
 ZornGen7DirectVm26 vm;NativeAdrenoMemory memory;ZornSmmuSparse4KLiveArena arena;Tables tables;
 std::vector<ZornSmmuSparse4KRange> ranges(4096);
 for(unsigned i=0;i<ranges.size();++i){ranges[i].iova=arena.iova+i*4096; ranges[i].physical=0x40000000+uint64_t(i)*4096;}
 vm.regions_[0]={&arena,&tables};vm.ranges_=ranges.data();
 auto run=[&](){notes=0;return vm.preflight(&memory,0,arena.iova+0x2000000,1,0,2);};
 assert(run()==0&&notes==0);
 vm.objects_=4096;assert(run()==kIOReturnNoResources&&notes==1&&stage==170&&reason==24&&d0==4096&&d1==4096&&rawNote==kIOReturnNoResources);
 vm.objects_=0;vm.lower_count_=4096;assert(run()==kIOReturnNoResources&&notes==1&&reason==25&&d0==0&&d1==1);
 vm.lower_count_=4095;assert(run()==0&&notes==0); // exact remaining span accepted;capacity is not increased
 vm.lower_count_=4096;memory.count=UINT64_MAX;assert(run()==kIOReturnNoResources&&notes==1&&reason==25&&d1==UINT32_MAX);
 vm.lower_count_=0;memory.count=1;memory.valid=false;assert(run()==kIOReturnBadArgument&&notes==0);
 memory.valid=true;memory.quarantine=true;assert(run()==kIOReturnBadArgument&&notes==0);
 memory.quarantine=false;memory.length=0;assert(run()==kIOReturnBadArgument&&notes==0);
 memory.length=16384;memory.count=0;assert(run()==kIOReturnBadArgument&&notes==0);
 memory.count=1;memory.span.bytes=4096;memory.length=4096;assert(run()==0&&notes==0); // GPU4KiB size remains distinct from CPU16KiB span
 memory.span.bytes=16384;memory.length=16384;memory.span.offset=4096;assert(run()==kIOReturnBadArgument&&notes==0);
 memory.span.offset=0;vm.objects_=UINT64_MAX;assert(run()==kIOReturnNoResources&&d0==UINT32_MAX&&reason==24);
 assert(vm.capacity_==4096);
 // Reproduce the real262 request:3524live spans and847incoming spans.
 std::vector<Span> scene(847);for(unsigned i=0;i<scene.size();++i){scene[i].offset=uint64_t(i)*16384;scene[i].physical=0x80000000+uint64_t(i)*32768;scene[i].bytes=16384;}
 memory.external=scene.data();memory.count=scene.size();memory.length=scene.size()*16384;vm.objects_=3;vm.lower_count_=3524;vm.capacity_=4096;
 assert(run()==kIOReturnNoResources&&reason==25&&d0==572&&d1==847);
 vm.capacity_=SELECTED_CAPACITY;assert(run()==kIOReturnSuccess&&notes==0);
 vm.lower_count_=8192;assert(run()==kIOReturnNoResources&&d0==0&&d1==847); // the new cap is still enforced
 puts("PASS263 observed3524+847span scene rejected at4096 and accepted by the actual selected8192bound;new bound still enforced;prior VM controls:12 capacity/boundary/poisoned-input/saturation controls;CPU16KiB/GPU4KiB separate,no mapping guard or authority bypass");
}
'''
f=O/'actual-preflight.cpp';f.write_text(prefix+helpers+actual+main.replace('SELECTED_CAPACITY',str(chosen)));args=['/usr/bin/clang++','-std=c++17','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(S),str(f),'-o',str(O/'check')];r=subprocess.run(args,capture_output=True);(O/'compile.json').write_text(json.dumps(dict(arguments=args,exit=r.returncode,stderr=r.stderr.decode()),indent=2)+'\n');assert r.returncode==0,r.stderr.decode();r=subprocess.run([str(O/'check')],capture_output=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0'});assert r.returncode==0,r.stderr.decode();pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());(O/'result.json').write_text(json.dumps(dict(passed=True,source=pin(S/'direct-runtime/ZornGen7DirectVm26.cpp'),header=pin(S/'ZornClientFailure261.h'),actual_alias_index=pin(alias),tool=pin(Path(__file__)),actual_preflight_compiled=True,memory_and_region_boundaries_are_explicit_CPU_fixtures=True,old_capacity=4096,selected_capacity=chosen,observed_required_spans=4371,selected_board_source=pin(S/'ZornGen7DarwinBoardOwner.cpp'),hardware_qualified=False,phone_access=False,stdout=r.stdout.decode()),indent=2)+'\n');print(r.stdout.decode())
