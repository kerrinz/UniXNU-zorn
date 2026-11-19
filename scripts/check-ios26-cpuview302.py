#!/usr/bin/env python3
"""Build ZornCpuViewContextFree302 under ASan/UBSan and TSan; verify exact ABI method classification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

FIXTURE = r'''
#include "NativeAdrenoABI.h"
#include "ZornCpuViewContextFree302.h"
#include <cassert>
#include <thread>
#include <vector>

int main() {
    // 1. All 12 CPU-only / metadata / queue / global-timer methods are context-free
    const uint32_t contextFree[] = {
        NativeAdrenoMethodQuery,
        NativeAdrenoMethodBoAlloc,
        NativeAdrenoMethodBoImport,
        NativeAdrenoMethodGetDeviceInfo,
        NativeAdrenoMethodGetTimestamp,
        NativeAdrenoMethodBoCpuMap,
        NativeAdrenoMethodBoCpuUnmap,
        NativeAdrenoMethodCreateQueue,
        NativeAdrenoMethodCloseQueue,
        NativeAdrenoMethodSetMetadata,
        NativeAdrenoMethodGetMetadata,
        NativeAdrenoMethodGetStatus,
    };
    for (uint32_t m : contextFree) {
        assert(zorn26_native_context_free_method302(m));
    }

    // 2. All SMMU page-table and GPU command-ring / fence methods MUST select context
    const uint32_t contextRequired[] = {
        NativeAdrenoMethodBoMap,
        NativeAdrenoMethodBoFree,
        NativeAdrenoMethodSubmit,
        NativeAdrenoMethodSubmitBatch,
        NativeAdrenoMethodWaitFence,
    };
    for (uint32_t m : contextRequired) {
        assert(!zorn26_native_context_free_method302(m));
    }

    // 3. Invalid / out-of-range method selectors MUST return false
    const uint32_t invalid[] = {0u, 18u, 19u, 255u, 0xffffffffu};
    for (uint32_t m : invalid) {
        assert(!zorn26_native_context_free_method302(m));
    }

    // 4. Concurrent evaluation under TSan
    std::vector<std::thread> threads;
    for (int t = 0; t < 8; ++t) {
        threads.emplace_back([&]() {
            for (int iter = 0; iter < 500; ++iter) {
                for (uint32_t m : contextFree) assert(zorn26_native_context_free_method302(m));
                for (uint32_t m : contextRequired) assert(!zorn26_native_context_free_method302(m));
            }
        });
    }
    for (auto &th : threads) th.join();
    return 0;
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--include', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sanitizer', choices=('asan', 'tsan'), required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    src = args.out / 'fixture.cpp'
    src.write_text(FIXTURE)
    bin_path = args.out / 'fixture'
    san_flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if args.sanitizer == 'asan' else ['-fsanitize=thread']
    cmd = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-pthread', *san_flags,
           '-I' + str(args.source), '-I' + str(args.include), str(src), '-o', str(bin_path)]
    env = dict(os.environ, ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1', TSAN_OPTIONS='symbolize=0')
    subprocess.run(cmd, env=env, check=True)
    subprocess.run([str(bin_path)], env=env, check=True)
    header = args.source / 'ZornCpuViewContextFree302.h'
    report = dict(
        passed=True,
        sanitizer=args.sanitizer,
        phone_access=False,
        context_free_methods_verified=12,
        context_required_methods_preserved=5,
        invalid_selectors_rejected=True,
        source_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        command=cmd,
    )
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS CpuViewContextFree302 ({args.sanitizer}): 12 CPU-only methods context-free, 5 SMMU/GPU methods preserved')


if __name__ == '__main__':
    main()
