#!/usr/bin/env python3
"""Exercise the native ring timeline and actual serialized retirement sweep."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess


BOUNDARIES = r'''
#include "actual-ring.cpp"
#include <array>
#include <cassert>

struct ZornGen7DirectVm26Routes {
    void *cookie;
    IOReturn (*beginSubmission)(void *);
    void (*endSubmission)(void *);
};
struct VmFixture {
    bool gated=false, failAcquire=false;
    unsigned holds=1, importedAcquires=0, namespaceHolds=1, surfaceFence=0;
    ZornGen7DirectVm26Routes routes{
        this,
        [](void *p)->IOReturn {auto &vm=*static_cast<VmFixture *>(p);assert(!vm.gated);vm.gated=true;return 0;},
        [](void *p) {auto &vm=*static_cast<VmFixture *>(p);assert(vm.gated);vm.gated=false;}
    };
    ZornGen7DirectVm26Routes *streams_=&routes;
    IOReturn retireJobAfterCompletion(uint64_t handle) {
        assert(gated && handle==12 && holds);--holds;return 0;
    }
    IOReturn acquireImported() {assert(gated);++importedAcquires;return failAcquire?kIOReturnIOError:0;}
    IOReturn retireSubmissionResourcesAfterCompletion() {
        assert(gated && namespaceHolds);--namespaceHolds;return 0;
    }
    void noteSurfaceCompletion246(uint32_t value) {assert(gated && value);surfaceFence=value;}
};
struct ZornGen7DirectSubmit26 {
    struct Job {bool active=false;uint32_t fence=0;size_t count=0;uint64_t handles[2]{};} jobs_[2];
    struct {unsigned references_retired=0,completed=0;} stats_;
    struct {bool failed=false;uint32_t retiredFence=0;} ledger;
    decltype(ledger) *present_=&ledger;
    bool attached_=true,poisoned_=false;
    VmFixture *vm_;
    NativeAdrenoRing *ring_;
    IOReturn poison();
    IOReturn release(Job &);
    IOReturn retireCompleted();
};
'''


CASES = r'''
struct RingFixture {
    std::array<uint32_t,2048> packets{};
    alignas(64) uint32_t page[16]{};
    unsigned reads=0, writes=0, publishes=0, barriers=0, acquisitions=0;
    bool uncertainWrite=false;
    NativeAdrenoRing ring;
    RingFixture() {
        NativeAdrenoRingIo io{
            this,
            [](void *p,uint32_t,uint32_t) {auto &h=*static_cast<RingFixture *>(p);++h.writes;return int(h.uncertainWrite);},
            [](void *p,uint32_t,uint32_t *out) {++static_cast<RingFixture *>(p)->reads;*out=0;return 0;},
            [](void *p) {++static_cast<RingFixture *>(p)->barriers;return 0;}
        };
        NativeAdrenoRingCache cache{
            this,
            [](void *p,const volatile uint32_t *at,size_t bytes) {
                auto &h=*static_cast<RingFixture *>(p);
                assert(at==h.packets.data() && bytes==sizeof(h.packets));++h.publishes;return 0;
            },
            [](void *p,volatile uint32_t *at,size_t bytes) {
                auto &h=*static_cast<RingFixture *>(p);
                assert(at==h.page && bytes==sizeof(h.page));++h.acquisitions;return 0;
            }
        };
        assert(ring.attach(&io,&cache,packets.data(),sizeof(packets),0x2000,page,sizeof(page),0x8000)==0);
    }
    uint32_t submit(bool framed=true) {
        uint32_t fence=0;
        const uint32_t word=0;
        assert((framed?ring.submitFramed(&word,1,&fence):ring.submit(&word,1,&fence))==0);
        return fence;
    }
};

int main() {
    for(bool framed : {false,true}) {
        RingFixture f;
        f.ring.seqno_=f.ring.completed_=f.page[1]=UINT32_MAX-1;
        f.ring.requestContextReset();
        assert(f.submit(framed)==UINT32_MAX && f.ring.outstanding()==1);
        const auto packets=f.packets;
        const auto captures=native_adreno_ring_log_count;
        const auto r=f.reads,w=f.writes,p=f.publishes,b=f.barriers;
        const uint32_t word=0;
        uint32_t refused=123;
        assert(f.ring.submitFramed(&word,1,&refused)==kIOReturnNoResources && !refused);
        assert(f.reads==r && f.writes==w && f.publishes==p && f.barriers==b && captures==native_adreno_ring_log_count);
        assert(f.packets==packets && !f.ring.poisoned() && f.ring.lastSubmitted()==UINT32_MAX);
        f.page[1]=UINT32_MAX;
        assert(f.ring.wait(UINT32_MAX,nullptr,0,nullptr)==NativeAdrenoRingFenceComplete);
        assert(!f.ring.outstanding() && f.ring.detach()==0);
    }
    for(bool readOnly : {false,true}) {
        RingFixture f;
        f.submit();f.submit();
        f.page[1]=2;
        assert(f.ring.wait(2,nullptr,0,nullptr)==NativeAdrenoRingFenceComplete);
        f.page[1]=1;
        const auto result=readOnly?f.ring.observeFence(1,nullptr,0,nullptr):f.ring.wait(1,nullptr,0,nullptr);
        assert(result==NativeAdrenoRingFencePoisoned && f.ring.completedFence()==2 && f.ring.poisoned());
    }
    {RingFixture f;f.submit();f.page[1]=2;
     assert(f.ring.wait(1,nullptr,0,nullptr)==NativeAdrenoRingFencePoisoned && !f.ring.completedFence());}
    {RingFixture f;f.submit();f.page[1]=1;
     assert(f.ring.observeFence(1,nullptr,0,nullptr)==NativeAdrenoRingFenceComplete);
     assert(!f.ring.completedFence() && f.ring.outstanding()==1);}
    {RingFixture f;VmFixture vm;ZornGen7DirectSubmit26 d{};d.vm_=&vm;d.ring_=&f.ring;
     d.jobs_[0]={true,f.submit(),1,{12}};f.page[1]=0;
     assert(!d.retireCompleted() && f.ring.outstanding()==1 && vm.holds==1 && d.jobs_[0].active);
     f.page[1]=1;
     assert(!d.retireCompleted() && !d.jobs_[0].active && f.ring.completedFence()==1 && !f.ring.outstanding());
     assert(!vm.gated && !vm.holds && !vm.namespaceHolds && vm.importedAcquires==1 && vm.surfaceFence==1);
     assert(d.ledger.retiredFence==1 && f.ring.detach()==0);}
    {RingFixture f;VmFixture vm;ZornGen7DirectSubmit26 d{};d.vm_=&vm;d.ring_=&f.ring;
     vm.failAcquire=true;d.jobs_[0]={true,f.submit(),1,{12}};f.page[1]=1;
     assert(d.retireCompleted()==kIOReturnIOError && f.ring.completedFence()==1);
     assert(d.poisoned_ && d.ledger.failed && d.jobs_[0].active && vm.namespaceHolds==1 && !vm.surfaceFence);}
    {RingFixture f;VmFixture vm;ZornGen7DirectSubmit26 d{};d.vm_=&vm;d.ring_=&f.ring;
     d.jobs_[0]={true,f.submit(),1,{12}};f.page[1]=2;
     assert(d.retireCompleted()==kIOReturnIOError && !f.ring.completedFence());
     assert(f.ring.poisoned() && d.poisoned_ && d.jobs_[0].active && vm.holds==1 && vm.namespaceHolds==1);}
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--pm4-header', type=Path, required=True)
    parser.add_argument('--pm4-source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sanitizer', choices=('address,undefined', 'thread'), required=True)
    args = parser.parse_args()
    harness = Path(__file__).with_name('check-ios26-context-fence.py')
    spec = importlib.util.spec_from_file_location('method_extractor', harness)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ring = args.source / 'direct-ring/NativeAdrenoRing.cpp'
    ring_header = args.source / 'direct-ring/NativeAdrenoRing.h'
    submit = args.source / 'direct-runtime/ZornGen7DirectSubmit26.cpp'
    args.out.mkdir()
    # The copy exposes fields to start near the 32-bit limit without billions
    # of simulated submissions. Selected function bodies and layout are exact.
    (args.out / ring_header.name).write_text(ring_header.read_text().replace(
        'class NativeAdrenoRing final {', 'class NativeAdrenoRing final {\npublic:', 1))
    (args.out / 'actual-ring.cpp').write_bytes(ring.read_bytes())
    include = args.out / 'IOKit'
    include.mkdir()
    (include / 'IOTypes.h').write_text('using IOReturn=int;\n')
    (include / 'IOLib.h').write_text('''#include "IOTypes.h"
constexpr IOReturn kIOReturnSuccess=0,kIOReturnNotReady=1,kIOReturnBadArgument=2,
                   kIOReturnNoResources=3,kIOReturnIOError=4,kIOReturnBusy=5;
''')
    selected = submit.read_text()
    gate = module.extract(selected, 'struct DirectSubmitGateScope {') + ';'
    methods = '\n'.join(module.extract(selected, 'IOReturn ZornGen7DirectSubmit26::' + name + '(')
                        for name in ('poison', 'release', 'retireCompleted'))
    fixture = args.out / 'fixture.cpp'
    fixture.write_text(BOUNDARIES + gate + methods + CASES)
    pm4 = args.out / 'pm4.o'
    flags = ['-g', '-fsanitize=' + args.sanitizer, '-I' + str(args.pm4_header.parent)]
    commands = [
        ['xcrun', 'clang', '-std=c11', *flags, '-c', str(args.pm4_source), '-o', str(pm4)],
        ['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation',
         *flags, '-I' + str(args.out), str(fixture), str(pm4), '-o', str(args.out / 'fixture')],
        [str(args.out / 'fixture')],
    ]
    env = os.environ | dict(ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1',
                            TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    for command in commands:
        subprocess.run(command, env=env, timeout=120, check=True)
    sources = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in
               (ring, ring_header, submit, args.pm4_source, args.pm4_header, harness, Path(__file__))}
    result = dict(passed=True, cases=9, sanitizer=args.sanitizer, actual_ring_and_sweep=True,
                  sources=sources, commands=commands, phone_access=False, hardware_qualified=False)
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS native fence monotonicity, exhaustion before WPTR, and lazy completion')


if __name__ == '__main__':
    main()
