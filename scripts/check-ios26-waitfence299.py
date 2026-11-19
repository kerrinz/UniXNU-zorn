#!/usr/bin/env python3
"""Build ZornWaitFenceScope299 under ASan/UBSan and TSan; verify unlocked IRQ wait & concurrency."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

FIXTURE = r'''
#include "ZornWaitFenceScope299.h"
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <thread>
#include <vector>

namespace {
std::mutex gClientSerial;
std::mutex gAppSerial;
std::mutex gIssuer;
std::mutex gWaitGate;
std::condition_variable gIrqCv;

std::atomic<uint32_t> gHwFence{100};
std::atomic<bool> gStopped{false};
uint32_t gLastSubmitted = 105;
uint32_t gCompletedCached = 100;
std::atomic<uint64_t> gConcurrentClientCalls{0};

uint64_t monoNs() {
    return uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
}
} // namespace

int main() {
    auto preflight = [](uint32_t target) -> ZornWaitPreflight299 {
        if (gStopped.load(std::memory_order_acquire)) return ZornWaitPreflight299::Passthrough;
        std::lock_guard<std::mutex> lk(gIssuer);
        if (!target || target > gLastSubmitted) return ZornWaitPreflight299::Passthrough;
        if (gCompletedCached >= target) return ZornWaitPreflight299::AlreadyComplete;
        return ZornWaitPreflight299::WaitIrq;
    };
    auto readHw = []() -> uint32_t { return gHwFence.load(std::memory_order_acquire); };
    auto isStopped = []() -> bool { return gStopped.load(std::memory_order_acquire); };
    auto sleepIrq = [](uint64_t stepNs, uint32_t target) {
        std::unique_lock<std::mutex> lk(gWaitGate);
        if (!gStopped.load(std::memory_order_acquire) && gHwFence.load(std::memory_order_acquire) < target) {
            gIrqCv.wait_for(lk, std::chrono::nanoseconds(stepNs));
        }
    };

    // 1. Passthrough cases: zero fence, out-of-range fence, zero timeout.
    assert(zorn26_await_fence_unlocked299(0, 5000000ULL, preflight, readHw, isStopped, monoNs,
        [&](uint64_t) { assert(false); }) == 5000000ULL);
    assert(zorn26_await_fence_unlocked299(999, 5000000ULL, preflight, readHw, isStopped, monoNs,
        [&](uint64_t) { assert(false); }) == 5000000ULL);
    assert(zorn26_await_fence_unlocked299(102, 0ULL, preflight, readHw, isStopped, monoNs,
        [&](uint64_t) { assert(false); }) == 0ULL);

    // 2. Already completed in preflight: returns 0 without sleeping.
    assert(zorn26_await_fence_unlocked299(100, 5000000ULL, preflight, readHw, isStopped, monoNs,
        [&](uint64_t) { assert(false); }) == 0ULL);

    // 3. In-flight fence: while waiter sleeps on gWaitGate, 4 concurrent threads acquire
    // gClientSerial -> gAppSerial -> gIssuer 256 times each without blocking on WaitFence,
    // and GPU IRQ thread signals fence 104 to wake the waiter promptly.
    std::atomic<bool> waiterEntered{false};
    std::thread gpuIrq([&]() {
        while (!waiterEntered.load(std::memory_order_acquire)) {
            std::this_thread::yield();
        }
        std::vector<std::thread> clients;
        for (int t = 0; t < 4; ++t) {
            clients.emplace_back([]() {
                for (int i = 0; i < 256; ++i) {
                    std::lock_guard<std::mutex> c(gClientSerial);
                    std::lock_guard<std::mutex> a(gAppSerial);
                    std::lock_guard<std::mutex> s(gIssuer);
                    gConcurrentClientCalls.fetch_add(1, std::memory_order_relaxed);
                }
            });
        }
        for (auto &w : clients) w.join();
        {
            std::lock_guard<std::mutex> lk(gWaitGate);
            gHwFence.store(104, std::memory_order_release);
        }
        gIrqCv.notify_all();
    });

    const uint64_t rem = zorn26_await_fence_unlocked299(
        104, 500000000ULL, preflight, readHw, isStopped, monoNs,
        [&](uint64_t stepNs) {
            waiterEntered.store(true, std::memory_order_release);
            sleepIrq(stepNs, 104);
        });
    gpuIrq.join();
    assert(rem == 0ULL);
    assert(gHwFence.load() == 104u);
    assert(gConcurrentClientCalls.load() == 1024ULL);

    // 4. Genuine timeout expiry when GPU has not reached fence 105 yet: returns 0 cleanly.
    const uint64_t t0 = monoNs();
    const uint64_t remTo = zorn26_await_fence_unlocked299(
        105, 500000ULL, preflight, readHw, isStopped, monoNs,
        [&](uint64_t stepNs) { sleepIrq(stepNs, 105); });
    const uint64_t dt = monoNs() - t0;
    assert(remTo == 0ULL && dt >= 400000ULL);

    // 5. Stopped ring aborts wait immediately.
    gStopped.store(true, std::memory_order_release);
    assert(zorn26_await_fence_unlocked299(105, 50000000ULL, preflight, readHw, isStopped, monoNs,
        [&](uint64_t) { assert(false); }) == 50000000ULL);

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
    cmd = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', *san_flags,
           '-I' + str(args.source), str(src), '-o', str(bin_path)]
    env = dict(os.environ, ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1', TSAN_OPTIONS='symbolize=0')
    subprocess.run(cmd, env=env, check=True)
    subprocess.run([str(bin_path)], env=env, check=True)
    header = args.source / 'ZornWaitFenceScope299.h'
    report = dict(
        passed=True,
        sanitizer=args.sanitizer,
        phone_access=False,
        unlocked_wait_verified=True,
        concurrent_client_serial_appSerial_issuer_calls=1024,
        passthrough_and_timeout_and_stop_verified=True,
        source_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        command=cmd,
    )
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS WaitFenceScope299 ({args.sanitizer}): 1024 concurrent serial+appSerial+issuer ops unblocked during IRQ wait')


if __name__ == '__main__':
    main()
