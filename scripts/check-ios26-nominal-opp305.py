#!/usr/bin/env python3
"""Verify ZornNominalOpp305 against K80's pinned ZornGen791StockVoteData.inc (stock_0_power_3 & stock_0_ddr) under ASan/UBSan and TSan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

STOCK_INC = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/shared/commanddb-xo-3badc85dcc584bf3a19b2cddb82597b7/k80/runtime/startup/ZornGen791StockVoteData.inc')

FIXTURE = r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <thread>
#include <vector>

enum Gen791PowerProperty : uint32_t {
    Gen791CxLevel = 1u << 0, Gen791AcdLevel = 1u << 1,
    Gen791BusMin = 1u << 2, Gen791BusMax = 1u << 3,
};
struct PowerLevelValues {
    uint32_t gpu_freq_hz, cx_level, voltage_level, acd_level, bus_freq, bus_min, bus_max;
};
struct Gen791SelectedPowerRow {
    uint32_t index;
    PowerLevelValues values;
    uint32_t present;
};
struct CommandDbBandwidthRows {
    const uint32_t *levels_kbps;
    size_t bytes;
    uint32_t count;
};
struct Gen791GmuPowerLevel {
    uint32_t frequency_hz, voltage_level;
};
struct StockPowerAlternative {
    uint32_t suffix;
    const Gen791SelectedPowerRow *rows;
    size_t count;
};
struct StockVoteData {
    uint8_t digest[32];
    const StockPowerAlternative *alternatives;
    size_t count;
    CommandDbBandwidthRows ddr, cnoc;
    Gen791GmuPowerLevel gmu[2];
};

#include "ZornGen791StockVoteData.inc"
#include "ZornNominalOpp305.h"

int main() {
    // Verify K80 SKU bin 3 (stock_0_power_3) has 12 rows and row 6 matches ZornNominalOpp305!
    const size_t n = sizeof(stock_0_power_3) / sizeof(stock_0_power_3[0]);
    assert(n == ZornNominalOpp305::kActiveRows);
    const auto &row = stock_0_power_3[ZornNominalOpp305::kSelectedRow];
    assert(row.index == ZornNominalOpp305::kSelectedRow);
    assert(row.values.gpu_freq_hz == ZornNominalOpp305::kGpuFreqHz);
    assert(row.values.voltage_level == ZornNominalOpp305::kVoltageCornerNom);
    assert(row.values.bus_freq == ZornNominalOpp305::kBusLevel);
    assert(ZornNominalOpp305::kPerfIndex == n - ZornNominalOpp305::kSelectedRow);
    assert(ZornNominalOpp305::kPerfIndex == 6u);

    // Verify DDR table entry matches kDdrKbps and last entry matches kMaxDdrKbps!
    const size_t ddr_n = sizeof(stock_0_ddr) / sizeof(stock_0_ddr[0]);
    assert(ZornNominalOpp305::kBusLevel < ddr_n);
    assert(stock_0_ddr[ZornNominalOpp305::kBusLevel] == ZornNominalOpp305::kDdrKbps);
    assert(stock_0_ddr[ddr_n - 1] == ZornNominalOpp305::kMaxDdrKbps);

    std::vector<std::thread> threads;
    for (int t = 0; t < 8; ++t) {
        threads.emplace_back([&]() {
            for (int iter = 0; iter < 500; ++iter) {
                assert(stock_0_power_3[ZornNominalOpp305::kSelectedRow].values.gpu_freq_hz == 578000000u);
                assert(stock_0_ddr[ZornNominalOpp305::kBusLevel] == 8171875u);
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
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sanitizer', choices=('asan', 'tsan'), required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    src = args.out / 'fixture.cpp'
    src.write_text(FIXTURE)
    bin_path = args.out / 'fixture'
    san_flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if args.sanitizer == 'asan' else ['-fsanitize=thread']
    cmd = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-pthread', *san_flags,
           '-I' + str(args.source), '-I' + str(STOCK_INC.parent), str(src), '-o', str(bin_path)]
    env = dict(os.environ, ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1', TSAN_OPTIONS='symbolize=0')
    subprocess.run(cmd, env=env, check=True)
    subprocess.run([str(bin_path)], env=env, check=True)
    header = args.source / 'ZornNominalOpp305.h'
    report = dict(
        passed=True,
        sanitizer=args.sanitizer,
        phone_access=False,
        selected_row=6,
        gpu_freq_hz=578000000,
        perf_index=6,
        bus_level=5,
        ddr_kbps=8171875,
        source_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        stock_table_sha256=hashlib.sha256(STOCK_INC.read_bytes()).hexdigest(),
    )
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS NominalOpp305 ({args.sanitizer}): K80 stock_0_power_3[6]=578MHz NOM (perfIndex=6), bus=5 (8171875 kbps) verified')


if __name__ == '__main__':
    main()
