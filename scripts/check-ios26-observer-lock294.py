#!/usr/bin/env python3
"""Exercise the actual compact observer with host implementations of XNU locks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

LOCKS = """#pragma once
#include <mutex>
using lck_spin_t = std::mutex;
#define LCK_GRP_DECLARE(var, name) int var __attribute__((unused))
#define LCK_SPIN_DECLARE(var, group) lck_spin_t var
inline void lck_spin_lock(lck_spin_t *lock) { lock->lock(); }
inline bool lck_spin_try_lock(lck_spin_t *lock) { return lock->try_lock(); }
inline void lck_spin_unlock(lck_spin_t *lock) { lock->unlock(); }
"""

TEST = r"""
#include <atomic>
#include <cassert>
#include <cstring>
#include <thread>
#include <vector>
#include "ZornApplicationObservation26.h"
#include "ZornApplicationObservation26.inc"

int main() {
    constexpr uintptr_t client = 64;
    appObservationBind(client, 10, 10);

    std::atomic<bool> held{false}, attempted{false}, release{false}, finished{false};
    std::thread holder([&] {
        appObservationLock();
        held.store(true);
        while (!release.load()) std::this_thread::yield();
        appObservationUnlock();
    });
    while (!held.load()) std::this_thread::yield();
    std::thread contender([&] {
        attempted.store(true);
        appObservationEvent(client, 2, 3, 0);
        finished.store(true);
    });
    while (!attempted.load()) std::this_thread::yield();
    ZornApplicationObservation26 sample{};
    assert(!zorn26_application_snapshot(&sample));
    assert(!zorn26_application_observes_map222(client));
    assert(!finished.load());
    release.store(true);
    holder.join();
    contender.join();

    constexpr unsigned threads = 4;
    constexpr unsigned events = 2000;
    std::atomic<bool> done{false};
    std::thread reader([&] {
        unsigned calls = 0;
        while (!done.load()) {
            ZornApplicationObservation26 value{};
            if (zorn26_application_snapshot(&value)) {
                assert(value.calls >= calls && !value.dropped);
                calls = value.calls;
            }
            std::this_thread::yield();
        }
    });
    std::vector<std::thread> writers;
    for (unsigned n = 0; n < threads; ++n) {
        writers.emplace_back([=] {
            for (unsigned i = 0; i < events; ++i) {
                appObservationEvent(client, 2, 3, 0);
            }
        });
    }
    for (auto &writer : writers) writer.join();
    done.store(true);
    reader.join();
    assert(zorn26_application_snapshot(&sample));
    assert(sample.calls == 1 + threads * events && !sample.dropped);

    const char report[] = "ZORN193MTL run=PROGRAM phase=11 ";
    assert(zorn26_application_stderr_reserve(10, 10));
    zorn26_application_stderr_commit(10, report, unsigned(std::strlen(report)), 0);
    assert(zorn26_application_snapshot(&sample));
    assert(sample.lines == 0 && !sample.dropped);  // No newline: raw context only.
    assert(!zorn26_application_stderr_reserve(11, 11));  // Still a real rejection.
    for (unsigned i = 0; i < 129; ++i) {
        zorn26_application_prepare_event(client, 16, 0, 0);
    }
    appObservationEvent(client, 128, 0, 0, true);
    appObservationEvent(client, 128, 0, 0, true);
    assert(zorn26_application_snapshot(&sample));
    assert(sample.closeReturned && !sample.closeRaw && sample.dropped == 2);
    assert(sample.prepareEvents == 128 && sample.calls == 2 + threads * events);
}
"""


def pin(path):
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sanitizer', choices=['address,undefined', 'thread'], required=True)
    args = parser.parse_args()
    build = args.build.resolve()
    out = args.out.resolve()
    candidate = json.loads((build / 'candidate.json').read_text())
    source = Path(candidate['source'])
    stub = out / 'host-include/kern/locks.h'
    stub.parent.mkdir(parents=True)
    stub.write_text(LOCKS)
    test = out / 'observer-host.cpp'
    test.write_text(TEST.replace('PROGRAM', candidate['program_tag']))
    cmd = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-pthread',
           '-fsanitize=' + args.sanitizer, '-I' + str(stub.parents[1]),
           '-I' + str(source), str(test), '-o', str(out / 'observer-host')]
    for name, command in [('compile', cmd), ('run', [str(out / 'observer-host')])]:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (out / (name + '.stderr')).write_text(result.stderr)
        result.check_returncode()
    checks = [
        'Contending writer is retained and both diagnostic readers refuse immediately',
        '8000 concurrent native events retain their exact count during snapshots',
        'Foreign identity and preparation capacity still count as loss',
        'Close finalizes once and later events are ignored',
    ]
    result = dict(passed=True, test_tool=pin(Path(__file__).resolve()),
                  source=pin(source / 'ZornApplicationObservation26.inc'),
                  host_lock_model=pin(stub), check=checks, sanitizer=args.sanitizer,
                  hardware_qualified=False, phone_access=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'PASS294 compact observer under {args.sanitizer}: {len(checks)} checks')


if __name__ == '__main__':
    main()
