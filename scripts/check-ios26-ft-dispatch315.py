#!/usr/bin/env python3
"""Run the selected FT3683 worker on explicit read, dispatch and cleanup fixtures."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess


BOUNDARIES = r'''
#include <cassert>
#include <cstdint>
#include <initializer_list>
#include <vector>
#include "ZornTouchRunPolicy26.h"

using IOReturn=int;
using kern_return_t=int;
constexpr int KERN_FAILURE=-1;
constexpr int kIOReturnSuccess=0, kIOReturnNotReady=2, dispatchFailure=3, cleanupFailure=4;

struct IOLock {bool held=false;};
static IOLock lock;
static void IOLockLock(IOLock *value) {assert(!value->held);value->held=true;}
static void IOLockUnlock(IOLock *value) {assert(value->held);value->held=false;}
struct ZornTouchIdBus {};
struct ZornTouchEventService26 {
    bool accepting=true;
    bool acceptingFrames() const {return accepting;}
};
struct ZornFt3683Source26 {
    enum class Outcome { None, NotCalibrated, BusNotPrepared, TransportError, DecodeRejected, DispatchReturned };
    struct Result {Outcome outcome; struct {IOReturn dispatchStatus;} detail;};
    std::vector<Result> frames;
    std::vector<IOReturn> releaseResults;
    std::vector<unsigned> releasedAt;
    unsigned next=0, closeAfter=0;
    Result readAndSubmit(ZornTouchIdBus &, ZornTouchEventService26 &service) {
        assert(!lock.held && service.accepting && next<frames.size());
        const Result result=frames[next++];
        if(next==closeAfter)service.accepting=false;
        return result;
    }
    IOReturn releaseAndReset(ZornTouchEventService26 &service) {
        assert(!lock.held && service.accepting && releasedAt.size()<releaseResults.size());
        const auto result=releaseResults[releasedAt.size()];
        releasedAt.push_back(next);
        return result;
    }
};
'''


DECLARATIONS = r'''
    IOLock *lock_=&lock;
    ZornTouchIdBus bus;
    ZornTouchIdBus *bus_=&bus;
    ZornTouchEventService26 service;
    ZornTouchEventService26 *service_=&service;
    ZornFt3683Source26 source_;
    Status status_;
    unsigned pollMs_=20;
    ZornTouchRunPolicy26 runPolicy_{true,0};
    void run();
    void requestStop();
    Status readStatus();
    bool stopRequested();
    void publishSource(const ZornFt3683Source26::Result &);
    void releaseContacts();
    void finish(End);
};
static ZornFt3683Worker26 *active;
static unsigned slept, stopAfterSleep;
void IOSleep(unsigned duration) {
    assert(duration==20 && !lock.held);
    if(++slept==stopAfterSleep)active->requestStop();
}
'''


CASES = r'''
using Outcome=ZornFt3683Source26::Outcome;
using End=ZornFt3683Worker26::End;
using Result=ZornFt3683Source26::Result;
constexpr Result rejected{Outcome::DispatchReturned,{dispatchFailure}};
constexpr Result accepted{Outcome::DispatchReturned,{kIOReturnSuccess}};
constexpr Result spi{Outcome::TransportError,{0}};
constexpr Result decode{Outcome::DecodeRejected,{0}};

struct Fixture : ZornFt3683Worker26 {
    Fixture() {assert(!lock.held);active=this;slept=stopAfterSleep=0;}
    void check(End end, unsigned reads, unsigned bad, unsigned waits,
               std::initializer_list<unsigned> releases, IOReturn releaseRaw=kIOReturnSuccess) {
        run();
        auto result=readStatus();
        assert(!lock.held && result.workerEntered && result.producerFinished);
        assert(result.phase==Phase::Finished && result.end==end);
        assert(result.consecutiveBad==bad && result.framesRead==reads && source_.next==reads && slept==waits);
        assert(source_.releasedAt==std::vector<unsigned>(releases));
        if(releases.size())assert(result.contactReleaseReturned && result.contactReleaseStatus==releaseRaw);
        else assert(!result.contactReleaseReturned);
    }
};

int main()
{
    {Fixture f;f.source_.frames.assign(10,rejected);f.source_.releaseResults={0};
     f.check(End::ConsecutiveBadLimit,10,10,9,{3});
     assert(f.readStatus().lastSource.detail.dispatchStatus==dispatchFailure);}
    {Fixture f;f.source_.frames={spi,decode,rejected,spi,decode,rejected,spi,decode,rejected,spi};
     f.source_.releaseResults={cleanupFailure,0};
     f.check(End::ConsecutiveBadLimit,10,10,9,{3,10});}
    {Fixture f;f.source_.frames.assign(20,rejected);f.source_.frames[9]=accepted;f.source_.releaseResults={0,0};
     f.check(End::ConsecutiveBadLimit,20,10,19,{3,13});}
    {Fixture f;f.source_.frames={accepted,rejected};f.source_.closeAfter=2;
     f.check(End::ServiceStopped,2,0,1,{});}
    {Fixture f;f.source_.frames={accepted,rejected};f.source_.releaseResults={0};stopAfterSleep=2;
     f.check(End::Requested,2,1,2,{2});}
    {Fixture f;f.source_.frames={accepted,accepted};f.runPolicy_={false,2};f.source_.releaseResults={0};
     f.check(End::FrameLimit,2,0,2,{2});}
    {Fixture f;f.source_.frames.assign(4,rejected);f.runPolicy_={false,4};f.source_.releaseResults={0};
     f.check(End::FrameLimit,4,4,4,{3});}
    {Fixture f;f.source_.frames={{Outcome::BusNotPrepared,{0}}};f.source_.releaseResults={0};
     f.check(End::BusUnavailable,1,0,0,{1});}
    {Fixture f;f.source_.frames={{Outcome::NotCalibrated,{0}}};f.source_.releaseResults={0};
     f.check(End::SourceContract,1,0,0,{1});}
    {Fixture f;f.source_.frames.assign(10,rejected);f.source_.releaseResults={cleanupFailure,cleanupFailure};
     f.check(End::ConsecutiveBadLimit,10,10,9,{3,10},cleanupFailure);}
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='exact iOS26 worker source directory')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sanitizer', choices=('address,undefined', 'thread'), required=True)
    args = parser.parse_args()
    harness = Path(__file__).with_name('check-ios26-retirement-chain.py')
    spec = importlib.util.spec_from_file_location('actual_methods', harness)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    worker = args.source / 'ZornFt3683Worker26.cpp'
    header = args.source / 'ZornFt3683Worker26.h'
    policy = args.source / 'ZornTouchRunPolicy26.h'
    interface = header.read_text()
    status = interface[interface.index('enum class Phase'):interface.index('    static IOReturn create(')]
    methods = worker.read_text()
    selected = '\n'.join(module.extract(methods, name + '(') for name in (
        'void ZornFt3683Worker26::requestStop', 'ZornFt3683Worker26::Status ZornFt3683Worker26::readStatus',
        'bool ZornFt3683Worker26::stopRequested', 'void ZornFt3683Worker26::publishSource',
        'void ZornFt3683Worker26::releaseContacts', 'void ZornFt3683Worker26::finish',
        'void ZornFt3683Worker26::run'))
    args.out.mkdir()
    source = args.out / 'fixture.cpp'
    source.write_text(BOUNDARIES + '\nstruct ZornFt3683Worker26 {\n' + status + DECLARATIONS + selected + CASES)
    executable = args.out / 'fixture'
    command = ['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-g',
               '-fsanitize=' + args.sanitizer, '-I' + str(args.source), str(source), '-o', str(executable)]
    env = os.environ | dict(ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1',
                            TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    subprocess.run(command, env=env, timeout=120, check=True)
    subprocess.run([executable], env=env, timeout=120, check=True)
    pins = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (worker, header, policy, harness, Path(__file__))}
    record = dict(passed=True, cases=10, sanitizer=args.sanitizer, actual_worker_methods=True, sources=pins,
                  command=command, actual_spi_or_HID_delivery_qualified=False, phone_access=False)
    (args.out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS actual FT3683 worker recovery limits, release ordering, intermittent and normal paths')


if __name__ == '__main__':
    main()
