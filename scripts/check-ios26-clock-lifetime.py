#!/usr/bin/env python3
"""Host-only regression using the supplied actual source sections;no phone access.

The original ASan failure is preserved in the publication evidence;this test
re-extracts the current fixed code to exercise lifetime,release and timing paths.
OS uptime,waitRange and freeBo are host stubs;this is not hardware qualification.
"""
from pathlib import Path
import argparse,json,subprocess,os,hashlib,shutil
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]/'native/ios26')
parser.add_argument('--ring-header',type=Path,help='actual selected NativeAdrenoRing.h when outside the prepared source root')
parser.add_argument('--out',type=Path,required=True,help='new independent output directory')
args=parser.parse_args();S=args.source_root.resolve();O=args.out.resolve();O.mkdir(parents=True,exist_ok=False)
v=(S/'direct-runtime/ZornGen7DirectVm26.cpp').read_text();c=(S/'direct-runtime/ZornGen7DirectClient26.cpp').read_text();s=(S/'direct-runtime/ZornGen7DirectSubmit26.cpp').read_text()
def section(t,start,end):a=t.index(start);return t[a:t.index(end,a)]
ring=(args.ring_header or S/'direct-ring/NativeAdrenoRing.h').resolve()
clock=section(ring.read_text(),'struct NativeAdrenoRingClock {','\n};')+'\n};'
now=section(v,'extern "C" uint64_t zorn_direct_vm_now_us(void)','/* Board hook')
phase=section(v,'struct PhaseClock {','\n};')+'\n};'
diag=section(s,'static uint64_t submitDiagNow','struct DirectSubmitGateScope')
release=section(c,'IOReturn ZornGen7DirectClient26::releaseAll','NativeAdrenoMemory *ZornGen7DirectClient26::memoryForToken')
assert 'vm_clock' not in c and 'zorn_direct_vm_now_us' not in c
assert '(*zorn_direct_vm_now_us)' not in v+s and 'extern "C" uint64_t zorn_direct_vm_now_us(void);' in s
source=r'''
#include <stdint.h>
#include <stddef.h>
#include <atomic>
#include <thread>
#include <cassert>
static std::atomic<uint64_t> ticks{1};
static void clock_get_uptime(uint64_t *v){*v=ticks.fetch_add(1000);}
static void absolutetime_to_nanoseconds(uint64_t v,uint64_t *n){*n=v;}
volatile uint64_t zorn_direct_vm_phase_us[2][8];uint64_t zorn_direct_vm_phase_max_us[2][6];volatile uint64_t zorn_direct_submit_cost[12];
'''+clock+now+phase+diag+r'''
using IOReturn=int;
constexpr int kIOReturnSuccess=0,kIOReturnNotReady=1,kIOReturnBadArgument=2;
constexpr size_t NativeAdrenoAbiMaxQueues=4;
struct NativeAdrenoAbiBoFree{uint64_t handle;};
struct Waiter{int raw=0,calls=0;int waitRange(uint32_t,size_t,const NativeAdrenoRingClock *c,uint32_t){++calls;if(c->now_us)c->now_us(c->cookie);return raw;}};
class ZornGen7DirectClient26{public:
 struct Entry{bool used;uint32_t mapping_leases;uint64_t handle;};struct Queue{};
 bool open_=true,scoped_=true,used_=false;Waiter waiter,*submit_=&waiter;uint32_t queue_base_=0;
 Entry entries_[2]={{true,3,1},{true,1,2}};size_t entry_count_=2;Queue queues_[4];int freed=0,freeRaw=0,closed=0;
 int freeBo(const NativeAdrenoAbiBoFree*){PhaseClock p;p.lap(1,1);p.done(1,4096);++freed;return freeRaw;}
 int close(){++closed;return 0;}
 IOReturn releaseAll(const NativeAdrenoRingClock*,uint32_t);
};
'''+release+r'''
static uint64_t cookieNow(void *p){return ++*static_cast<uint64_t*>(p);}
__attribute__((noinline)) static void returnedCall(){uint64_t cookie=7;NativeAdrenoRingClock clock{&cookie,cookieNow,nullptr};assert(clock.now_us(clock.cookie)==8);PhaseClock p;p.lap(0,1);p.done(0,4096);}
static void releaseTests(){
 uint64_t cookie=0;NativeAdrenoRingClock c{&cookie,cookieNow,nullptr};
 ZornGen7DirectClient26 a;assert(a.releaseAll(&c,0)==0 && a.freed==2 && a.closed==1 && cookie==1);
 ZornGen7DirectClient26 b;b.waiter.raw=17;assert(b.releaseAll(&c,0)==17 && b.freed==0 && b.closed==0);
 ZornGen7DirectClient26 d;d.freeRaw=18;assert(d.releaseAll(&c,0)==18 && d.freed==1 && d.closed==0);
 ZornGen7DirectClient26 e;assert(e.releaseAll(nullptr,0)==kIOReturnBadArgument && e.freed==0);
 e.open_=false;assert(e.releaseAll(&c,0)==kIOReturnNotReady);
 ZornGen7DirectClient26 f;f.scoped_=false;assert(f.releaseAll(&c,0)==0 && f.waiter.calls==0);
}
int main(){
 for(int i=0;i<1000;++i){returnedCall();PhaseClock later;later.lap(1,1);later.done(1,1);releaseTests();}
 {SubmitDiagScope outer(0);{SubmitDiagScope inner(3);}PhaseClock p;p.lap(0,2);p.done(0,1);}
 assert(zorn_direct_submit_cost[0]==1 && zorn_direct_submit_cost[3]==1);
 std::thread threads[4];for(auto &t:threads)t=std::thread([]{uint64_t prior=0;for(int i=0;i<10000;++i){auto n=zorn_direct_vm_now_us();assert(n>prior);prior=n;}});for(auto &t:threads)t.join();
}
'''
f=O/'actual-source.cpp';f.write_text(source);args=['/usr/bin/clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(f),'-o',str(O/'fixed')];p=subprocess.run(args,capture_output=True);(O/'compile.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr
p=subprocess.run([str(O/'fixed')],capture_output=True,env={**os.environ,'ASAN_OPTIONS':'detect_stack_use_after_return=1:symbolize=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=0'});(O/'fixed.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(O/'result.json').write_text(json.dumps(dict(passed=True,original_reproducer_record="docs/evidence/k80-gpu-v244-clock-lifetime-2026-11-16.json",fixed_ASan_UBSan_exit=p.returncode,actual_source_sections=['OS uptime function','PhaseClock','SubmitDiagScope','releaseAll'],checks=['after caller return','nested diagnostics','real releaseAll success','null clock','not-open early return','wait failure preserves resources','free failure stops close','unused range skips wait','four concurrent clock readers'],sources=[dict(path=str(p),sha256=sha(p)) for p in [S/'direct-runtime'/n for n in ['ZornGen7DirectClient26.cpp','ZornGen7DirectVm26.cpp','ZornGen7DirectSubmit26.cpp']]],limits=['Host OS time,waitRange and freeBo are mocks;not hardware evidence','Concurrent test covers stateless clock only;does not qualify existing volatile diagnostic counters','No dispatch hook remains,so no mutable context needs restoration']),indent=2)+'\n');print('PASS actual clock/release source sections ASan/UBSan')
