#!/usr/bin/env python3
"""Exercise the selected direct-ring IB rollback and BO-free error paths."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess


FIXTURE = r'''
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <initializer_list>

using IOReturn = int;
constexpr IOReturn kIOReturnSuccess=0, kIOReturnBadArgument=1, kIOReturnNotReady=2;
constexpr IOReturn kIOReturnBusy=3, kIOReturnIOError=4;
static uint32_t native_adreno_trace_stage, zorn_direct_import_live[3];
static unsigned lastImportState;
static void noteImportState(uint64_t handle, unsigned state) {
    assert(handle==1);
    lastImportState=state;
}

struct VmFixture {
    unsigned held[4]{0, 1, 1, 1};
    IOReturn retireRaw[4]{};
    unsigned retireCalls=0, unmapCalls=0;
    IOReturn retireJobAfterCompletion(uint64_t handle) {
        ++retireCalls;
        assert(handle && handle<4 && held[handle]);
        if(retireRaw[handle])return retireRaw[handle];
        --held[handle];
        return kIOReturnSuccess;
    }
    IOReturn unmap(uint64_t handle) {assert(handle==2);++unmapCalls;return kIOReturnSuccess;}
};

struct ZornGen7DirectSubmit26 {
    struct Job {uint32_t fence=0;size_t count=0;uint64_t handles[4]{};uint32_t queue=0;bool active=false;};
    struct {size_t references_retired=0;unsigned poisoned_jobs=0;} stats_;
    struct {bool failed=false;} present;
    decltype(present) *present_=&present;
    VmFixture *vm_;
    bool poisoned_=false;
    IOReturn sweepRaw=kIOReturnSuccess;
    unsigned sweeps=0;
    explicit ZornGen7DirectSubmit26(VmFixture &vm): vm_(&vm) {}
    IOReturn poison();
    IOReturn cancelUnpublishedIbHolds(Job &,const uint64_t *,size_t,uint32_t);
    IOReturn retireCompleted(){++sweeps;return poisoned_?kIOReturnNotReady:sweepRaw;}
};

struct NativeAdrenoAbiBoFree {uint64_t handle;};
struct ZornGen7DirectClient26 {
    struct Entry {
        uint64_t handle=1, mapped=2, iova=0x1000;
        bool imported=true, unreleasable=false, mapped_state=true;
        unsigned mapping_leases=0;
        struct {unsigned calls=0;IOReturn release(){++calls;return kIOReturnSuccess;}} memory;
    } entry;
    bool open_=true;
    VmFixture *vm_;
    ZornGen7DirectSubmit26 *submit_;
    Entry *find(uint64_t handle){return entry.handle==handle?&entry:nullptr;}
    void clear(Entry &value){assert(!value.mapped && !value.mapped_state);value.handle=0;}
    IOReturn freeBo(const NativeAdrenoAbiBoFree *);
};
'''


TESTS = r'''
int main()
{
    const uint64_t handles[]={1,2,3};
    for(unsigned count : {0u,1u,3u}) {
        VmFixture vm;
        ZornGen7DirectSubmit26 submit(vm);
        ZornGen7DirectSubmit26::Job job{};
        assert(!submit.cancelUnpublishedIbHolds(job,handles,count,9));
        assert(vm.retireCalls==count && submit.stats_.references_retired==count);
        assert(!job.active && !job.count && !job.fence && !submit.poisoned_);
        for(unsigned i=1;i<=3;++i)assert(vm.held[i]==unsigned(i>count));
    }
    for(unsigned mask : {1u,2u,4u,7u}) {
        VmFixture vm;
        for(unsigned i=1;i<=3;++i)if(mask&(1u<<(i-1)))vm.retireRaw[i]=IOReturn(i+10);
        ZornGen7DirectSubmit26 submit(vm);
        ZornGen7DirectSubmit26::Job job{};
        const auto raw=submit.cancelUnpublishedIbHolds(job,handles,3,9);
        assert(raw==((mask&4)?13:(mask&2)?12:11));
        assert(job.active && !job.fence && job.queue==9 && submit.poisoned_ && submit.present.failed);
        assert(vm.retireCalls==3 && job.count+submit.stats_.references_retired==3);
        assert(submit.stats_.poisoned_jobs==1);
        unsigned retained=0;
        for(unsigned i=3;i>0;--i) {
            const bool failed=mask&(1u<<(i-1));
            assert(vm.held[i]==unsigned(failed));
            if(failed)assert(job.handles[retained++]==i);
        }
        assert(retained==job.count);
    }
    for(IOReturn status : {kIOReturnIOError,kIOReturnBusy,kIOReturnNotReady,kIOReturnSuccess}) {
        VmFixture vm;
        ZornGen7DirectSubmit26 submit(vm);
        submit.sweepRaw=status;
        ZornGen7DirectClient26 client{{},true,&vm,&submit};
        const NativeAdrenoAbiBoFree request{1};
        zorn_direct_import_live[0]=1;
        lastImportState=0;
        assert(client.freeBo(&request)==status);
        assert(submit.sweeps==1);
        if(status) {
            assert(!vm.unmapCalls && !client.entry.memory.calls && client.entry.handle==1);
            assert(client.entry.mapped_state && client.entry.iova==0x1000 && lastImportState==3);
            assert(zorn_direct_import_live[0]==1 && zorn_direct_import_live[2]==uint32_t(status));
        } else {
            assert(vm.unmapCalls==1 && client.entry.memory.calls==1 && !client.entry.handle);
            assert(!zorn_direct_import_live[0] && lastImportState==2);
        }
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sanitizer', choices=('address,undefined', 'thread'), required=True)
    args = parser.parse_args()
    harness = Path(__file__).with_name('check-ios26-retirement-chain.py')
    spec = importlib.util.spec_from_file_location('retirement_chain', harness)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    submit_file = args.source / 'direct-runtime/ZornGen7DirectSubmit26.cpp'
    client_file = args.source / 'direct-runtime/ZornGen7DirectClient26.cpp'
    submit, client = submit_file.read_text(), client_file.read_text()
    actual = module.extract(submit, 'IOReturn ZornGen7DirectSubmit26::submit(')
    assert actual.count('cancelUnpublishedIbHolds(*job,handles,') == 4
    assert actual.index('if(ring_->poisoned())') < actual.rindex('cancelUnpublishedIbHolds(')
    sources = (
        (submit, 'IOReturn ZornGen7DirectSubmit26::poison('),
        (submit, 'IOReturn ZornGen7DirectSubmit26::cancelUnpublishedIbHolds('),
        (client, 'static void noteFreeRefused('),
        (client, 'IOReturn ZornGen7DirectClient26::freeBo('),
    )
    args.out.mkdir()
    cpp = args.out / 'fixture.cpp'
    cpp.write_text(FIXTURE + '\n'.join(module.extract(contents, symbol) for contents, symbol in sources) + TESTS)
    executable = args.out / 'fixture'
    command = ['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-g',
               '-fsanitize=' + args.sanitizer, str(cpp), '-o', str(executable)]
    env = os.environ | dict(ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1',
                            TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    subprocess.run(command, env=env, timeout=120, check=True)
    subprocess.run([executable], env=env, timeout=120, check=True)
    pins = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (submit_file, client_file, harness, Path(__file__))}
    result = dict(passed=True, compiled_actual_rollback_and_BoFree=True, checked_producer_callsites=4,
                  fixture_cases=11, actual_DMA_or_device_access=False, sanitizer=args.sanitizer,
                  command=command, sources=pins)
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS Direct Ring unpublished reference rollback and BoFree retention')


if __name__ == '__main__':
    main()
