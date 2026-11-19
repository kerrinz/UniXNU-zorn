#!/usr/bin/env python3
"""Build ZornPresenterScope298 under ASan/UBSan and TSan; verify issuer release before show()."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspect_ios26_gpu_surface246 import decode_surface

FIXTURE = r'''
#include "ZornPresenterScope298.h"
#include "ZornPresentCost278.h"
#include <atomic>
#include <cassert>
#include <cstdio>
#include <mutex>
#include <thread>
#include <vector>

namespace {
std::mutex gRegistry;
std::mutex gIssuer;
std::atomic<bool> gRegistryHeld{false};
std::atomic<bool> gIssuerHeld{false};
int gNextMode = 2; // 2=gpu, 1=cpu, 0=busy, -1=failed
uint64_t gIssuerOpsDuringShow = 0;

struct TestLease {
    int token_;
    explicit TestLease(uint32_t producer) : token_(gNextMode) {
        (void)producer;
        if (token_ > 0) {
            gRegistry.lock();
            gRegistryHeld.store(true, std::memory_order_release);
            if (token_ == 2) {
                gIssuer.lock();
                gIssuerHeld.store(true, std::memory_order_release);
            }
        }
    }
    ~TestLease() {
        if (token_ > 0) {
            if (token_ == 2) {
                gIssuerHeld.store(false, std::memory_order_release);
                gIssuer.unlock();
            }
            gRegistryHeld.store(false, std::memory_order_release);
            gRegistry.unlock();
        }
    }
    bool ready() const { return token_ > 0; }
    bool failed() const { return token_ < 0; }
    bool gpu() const { return token_ == 2; }
};

struct TestSurface {
    uint32_t sid;
    bool allowAcquire = true;
};

struct TestClock {
    uint64_t ticks = 1000;
    uint64_t now() { ticks += 100; return ticks; }
    uint64_t toMicros(uint64_t dt) { return dt; }
    uint32_t uptimeMs() { return uint32_t(ticks / 1000); }
};
} // namespace

int main() {
    TestClock clock;
    ZornPresentCost278 cost{};
    uint64_t observed = clock.now();
    std::atomic<uint64_t> presents{40};
    TestSurface s0{424, true};
    TestSurface *surfaces[4] = {&s0, nullptr, nullptr, nullptr};

    // 1. GPU frame: issuer+registry held for acquire/ledger/fence, dropped BEFORE show(),
    // allowing concurrent client/SwapEnd threads to acquire issuer+registry without blocking.
    gNextMode = 2;
    bool showRan = false;
    auto out = zorn26_present_frame298<4, TestLease>(
        391u, 910u, 1125u, 2436u, surfaces, observed, clock, cost,
        [&](TestSurface *s) {
            assert(gRegistryHeld.load(std::memory_order_acquire));
            assert(gIssuerHeld.load(std::memory_order_acquire));
            return s->allowAcquire;
        },
        [&](uint32_t *tail, uint32_t *retired) {
            assert(gRegistryHeld.load(std::memory_order_acquire));
            assert(gIssuerHeld.load(std::memory_order_acquire));
            *tail = 910u;
            *retired = 910u;
            return true;
        },
        [&](uint32_t sid) {
            assert(sid == 424u);
            assert(gIssuerHeld.load(std::memory_order_acquire));
            return 910u;
        },
        [&]() { return presents.load(std::memory_order_acquire); },
        [&]() {
            assert(!gIssuerHeld.load(std::memory_order_acquire));
            assert(!gRegistryHeld.load(std::memory_order_acquire));
            std::vector<std::thread> workers;
            for (int t = 0; t < 4; ++t) {
                workers.emplace_back([]() {
                    for (int i = 0; i < 64; ++i) {
                        std::lock_guard<std::mutex> reg(gRegistry);
                        std::lock_guard<std::mutex> iss(gIssuer);
                        ++gIssuerOpsDuringShow;
                    }
                });
            }
            for (auto &w : workers) w.join();
            presents.fetch_add(1, std::memory_order_release);
            showRan = true;
        });
    assert(showRan && out.completed && !out.terminal && out.copied && out.readable);
    assert(gIssuerOpsDuringShow == 256);
    assert(!gIssuerHeld.load() && !gRegistryHeld.load());

    // 2. Early-boot CPU frame (token==1): registry remains held across show().
    gNextMode = 1;
    bool cpuShowHeldRegistry = false;
    auto cpuOut = zorn26_present_frame298<4, TestLease>(
        2u, 0u, 1125u, 2436u, surfaces, observed, clock, cost,
        [&](TestSurface *) -> bool { assert(false); return false; },
        [&](uint32_t *, uint32_t *) -> bool { assert(false); return false; },
        [&](uint32_t) -> uint32_t { assert(false); return 0; },
        [&]() { return presents.load(std::memory_order_acquire); },
        [&]() {
            cpuShowHeldRegistry = gRegistryHeld.load(std::memory_order_acquire) &&
                                  !gIssuerHeld.load(std::memory_order_acquire);
            presents.fetch_add(1, std::memory_order_release);
        });
    assert(cpuShowHeldRegistry && cpuOut.completed && !cpuOut.terminal && cpuOut.copied);
    assert(cpuOut.record[3] == 1u && cpuOut.record[8] == 0u && cpuOut.record[10] == 0u);

    // 3. Busy frame (token==0): neither acquire nor show runs, non-terminal.
    gNextMode = 0;
    auto busyOut = zorn26_present_frame298<4, TestLease>(
        392u, 911u, 1125u, 2436u, surfaces, observed, clock, cost,
        [&](TestSurface *) -> bool { assert(false); return false; },
        [&](uint32_t *, uint32_t *) -> bool { assert(false); return false; },
        [&](uint32_t) -> uint32_t { assert(false); return 0; },
        [&]() { return presents.load(std::memory_order_acquire); },
        [&]() { assert(false); });
    assert(!busyOut.completed && !busyOut.terminal && !busyOut.readable);

    // 4. Terminal lease refusal (token==-1): terminal=true, no show.
    gNextMode = -1;
    auto failOut = zorn26_present_frame298<4, TestLease>(
        393u, 912u, 1125u, 2436u, surfaces, observed, clock, cost,
        [&](TestSurface *) -> bool { assert(false); return false; },
        [&](uint32_t *, uint32_t *) -> bool { assert(false); return false; },
        [&](uint32_t) -> uint32_t { assert(false); return 0; },
        [&]() { return presents.load(std::memory_order_acquire); },
        [&]() { assert(false); });
    assert(!failOut.completed && failOut.terminal && !failOut.readable);

    // 5. Cache acquire refusal on GPU frame: terminal=true, no show, locks released.
    gNextMode = 2;
    s0.allowAcquire = false;
    auto acqFail = zorn26_present_frame298<4, TestLease>(
        394u, 913u, 1125u, 2436u, surfaces, observed, clock, cost,
        [&](TestSurface *s) { return s->allowAcquire; },
        [&](uint32_t *, uint32_t *) -> bool { assert(false); return false; },
        [&](uint32_t) -> uint32_t { assert(false); return 0; },
        [&]() { return presents.load(std::memory_order_acquire); },
        [&]() { assert(false); });
    assert(!acqFail.completed && acqFail.terminal && !acqFail.readable);
    assert(!gIssuerHeld.load() && !gRegistryHeld.load());

    printf("1");
    for (unsigned i = 0; i < 16; ++i) printf("/%08x", out.record[i]);
    printf("\n");
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
    proc = subprocess.run([str(bin_path)], env=env, capture_output=True, check=True)
    wire_line = proc.stdout.strip()
    decoded = decode_surface(wire_line)
    assert decoded['available'] and decoded['lease'] == 2 and decoded['all_acquires_passed']
    assert decoded['completion_ledger_valid'] and decoded['pixel_copy_returned']
    assert decoded['producer_fence'] == decoded['completed'] == decoded['surface_gpu_access_fence'] == 910
    header = args.source / 'ZornPresenterScope298.h'
    report = dict(
        passed=True,
        sanitizer=args.sanitizer,
        phone_access=False,
        issuer_and_registry_released_before_gpu_show=True,
        concurrent_issuer_acquisitions_during_show=256,
        early_cpu_frame_registry_preserved=True,
        busy_and_terminal_and_acquire_refusal_verified=True,
        surface246_wire_decoded=decoded,
        source_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        command=cmd,
    )
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS PresenterScope298 ({args.sanitizer}): issuer/registry released before GPU show, 256 concurrent ops race-free, surface246 verified')


if __name__ == '__main__':
    main()
