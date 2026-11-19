#!/usr/bin/env python3
"""Build ZornIokitDaemonQuiet301 under ASan/UBSan and TSan; verify once-only IOKit root busy decrement & user-resource publication."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

FIXTURE = r'''
#include "ZornIokitDaemonQuiet301.h"
#include <atomic>
#include <cassert>
#include <thread>
#include <vector>

int main() {
    // 1. Guard: !daemonAvailable -> no-op
    {
        ZornIokitQuietTracker301 tracker{};
        int decrements = 0, publishes = 0;
        uint32_t busy = 1;
        const auto snap = tracker.applyOnce(
            []() { return false; },
            []() { return false; },
            [&]() { return busy; },
            [&]() { ++decrements; --busy; },
            [&]() { ++publishes; });
        assert(snap.attempted && !snap.applied && snap.beforeBusy == 1 && snap.afterBusy == 1);
        assert(decrements == 0 && publishes == 0 && busy == 1);
    }

    // 2. Guard: userResource already published (e.g. real kernelmanagerd ran) -> no-op
    {
        ZornIokitQuietTracker301 tracker{};
        int decrements = 0, publishes = 0;
        uint32_t busy = 1;
        const auto snap = tracker.applyOnce(
            []() { return true; },
            []() { return true; },
            [&]() { return busy; },
            [&]() { ++decrements; --busy; },
            [&]() { ++publishes; });
        assert(snap.attempted && !snap.applied && snap.alreadyPublished && busy == 1);
        assert(decrements == 0 && publishes == 0);
    }

    // 3. Guard: busy == 0 underflow prevention -> no decrement
    {
        ZornIokitQuietTracker301 tracker{};
        int decrements = 0, publishes = 0;
        uint32_t busy = 0;
        const auto snap = tracker.applyOnce(
            []() { return true; },
            []() { return false; },
            [&]() { return busy; },
            [&]() { ++decrements; },
            [&]() { ++publishes; });
        assert(snap.attempted && !snap.applied && snap.beforeBusy == 0 && snap.afterBusy == 0);
        assert(decrements == 0 && publishes == 0);
    }

    // 4. Positive + 16-thread concurrent race: exactly 1 decrement (1 -> 0) and 1 publish!
    {
        ZornIokitQuietTracker301 tracker{};
        std::atomic<int> decrements{0}, publishes{0};
        std::atomic<uint32_t> busy{1};
        std::atomic<bool> published{false};
        std::atomic<bool> go{false};
        std::vector<std::thread> threads;
        for (int t = 0; t < 16; ++t) {
            threads.emplace_back([&]() {
                while (!go.load(std::memory_order_acquire)) std::this_thread::yield();
                for (int i = 0; i < 64; ++i) {
                    (void)tracker.applyOnce(
                        []() { return true; },
                        [&]() { return published.load(std::memory_order_acquire); },
                        [&]() { return busy.load(std::memory_order_acquire); },
                        [&]() {
                            decrements.fetch_add(1, std::memory_order_acq_rel);
                            busy.fetch_sub(1, std::memory_order_acq_rel);
                        },
                        [&]() {
                            publishes.fetch_add(1, std::memory_order_acq_rel);
                            published.store(true, std::memory_order_release);
                        });
                }
            });
        }
        go.store(true, std::memory_order_release);
        for (auto &th : threads) th.join();
        const auto snap = tracker.snapshot();
        assert(decrements.load() == 1 && publishes.load() == 1);
        assert(busy.load() == 0 && published.load());
        assert(snap.attempted && snap.applied && snap.beforeBusy == 1 && snap.afterBusy == 0);
    }
    return 0;
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sanitizer', choices=('asan', 'tsan'), required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    src = args.out / 'fixture.cpp'
    src.write_text(FIXTURE)
    bin_path = args.out / 'fixture'
    san_flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if args.sanitizer == 'asan' else ['-fsanitize=thread']
    cmd = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-pthread', *san_flags,
           '-I' + str(args.source), str(src), '-o', str(bin_path)]
    env = dict(os.environ, ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1', TSAN_OPTIONS='symbolize=0')
    subprocess.run(cmd, env=env, check=True)
    subprocess.run([str(bin_path)], env=env, check=True)
    header = args.source / 'ZornIokitDaemonQuiet301.h'
    report = dict(
        passed=True,
        sanitizer=args.sanitizer,
        phone_access=False,
        no_daemon_available_guard_verified=True,
        existing_daemon_published_guard_verified=True,
        zero_busy_underflow_guard_verified=True,
        concurrent_1024_calls_single_decrement_verified=True,
        source_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        command=cmd,
    )
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS IokitDaemonQuiet301 ({args.sanitizer}): guards and 16-thread once-only busy 1->0 verified')


if __name__ == '__main__':
    main()
