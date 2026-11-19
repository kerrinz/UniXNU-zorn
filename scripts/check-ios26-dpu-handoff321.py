#!/usr/bin/env python3
"""Test the built K80 DPU handoff sampler and exact CDC layout."""

import argparse
import json
from pathlib import Path
import struct
import subprocess
import zlib

from inspect_ios26_ft313 import LAYOUTS, TE_END, parse_packet


FIXTURE = r'''
#include "ZornManualWire313.h"
#include <cassert>
#include <cstdio>

using namespace ZornDpuHandoff321;
using ZornDisplayTiming318::Window;
using ZornDisplayTiming318::Result;

struct Display {
    uint32_t parent = 1, flush = 0;
    unsigned reads = 0, pipeReads = 0;
    bool change = false, losePower = false;

    void take(uint32_t (&words)[Words])
    {
        auto clock = [&](Window window, uint32_t offset, uint32_t &value) {
            if (window == Window::Gcc) value = losePower && reads ? 0x80000001 : parent;
            else {
                assert(window == Window::DisplayClock);
                switch (offset) {
                case 0x1000: value = 0x80000000; break;
                case 0x1004: value = 0x10000; break;
                case 0: value = 0; break;
                case 0x0c: case 0x24: case 0xa4: value = 1; break;
                default: assert(false);
                }
            }
            return true;
        };
        auto mdp = [&](uint32_t offset, uint32_t &value) {
            ++reads;
            if (offset >= CtlOffsets[0]) {
                const unsigned index = (offset - CtlOffsets[0]) / 0x1000;
                const unsigned reg = offset & 0xfff;
                assert(index < CtlCount);
                if (reg == 0xf4) value = index == 0 ? 2 : 4;
                else {
                    assert(index == 0);
                    switch (reg) {
                    case 0xfc: value = change && pipeReads ? 0 : 1u << 16; break;
                    case 0x14: value = 0x100; break;
                    case 0x18: value = flush; break;
                    default: assert(false);
                    }
                }
            } else {
                ++pipeReads;
                switch (offset - PipeOffsets[0]) {
                case 0x14: value = 0xfc400000; break;
                case 0x00: value = 0x0c8005a0; break;
                case 0x24: value = 5760; break;
                case 0x30: value = 0x40000; break;
                case 0x38: value = 0; break;
                default: assert(false);
                }
            }
            return true;
        };
        sample(clock, mdp, 100, 0xfc400000, 5760, words);
    }
};

int main(int argc, char **argv)
{
    assert(argc == 3);
    uint32_t snap[Words]{};
    Display display;
    display.parent = 0x80000003;
    display.take(snap);
    assert(snap[Status] == uint32_t(Result::ParentClockOff) && snap[GccAhb] == display.parent);
    assert(display.reads == 0 && !snap[ActiveFetchMask]);
    display = {}; display.change = true;
    display.take(snap);
    assert(snap[Status] == UnstableTopology && !snap[ActiveFetchMask] && !snap[PipeStart]);
    display = {}; display.flush = 1;
    display.take(snap);
    assert(snap[Status] == UnstableTopology && !snap[PipeStart]);
    display = {}; display.losePower = true;
    display.take(snap);
    assert(snap[Status] == uint32_t(Result::UnstablePower) && !snap[PipeStart]);
    display = {};
    display.take(snap);
    assert(snap[Status] == uint32_t(Result::Observed) && snap[DisplayCtlMask] == 1);
    assert(snap[ActiveFetchMask] == (1u << 16) && display.pipeReads == PipeWords && snap[PipeStart] == 0xfc400000);

    uint32_t values[ZornManualWire313::Words]{};
    FILE *file = fopen(argv[1], "rb");
    assert(file && fread(values, 4, ZornManualWire313::HandoffStart, file) == ZornManualWire313::HandoffStart
           && fgetc(file) == EOF && !fclose(file));
    memcpy(values + ZornManualWire313::HandoffStart, snap, sizeof(snap));
    const uint8_t tag[16] = {0x32, 1};
    char wire[ZornManualWire313::Bytes];
    assert(ZornManualWire313::packet(wire, sizeof(wire), values, tag) == sizeof(wire));
    file = fopen(argv[2], "wb");
    assert(file && fwrite(wire, 1, sizeof(wire), file) == sizeof(wire) && !fclose(file));
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--previous-fixture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    previous = args.previous_fixture.read_bytes()
    assert previous[:8] == LAYOUTS[320][0] and len(previous) == TE_END
    parse_packet(previous, previous[8:24], 320)
    inputs, fixture, executable, wire = (args.out / name for name in (
        'SYNTHETIC-existing-samples.bin', 'fixture.cpp', 'fixture', 'SYNTHETIC-ft321.bin'))
    inputs.write_bytes(previous[24:-8])
    fixture.write_text(FIXTURE)
    argv = ['/usr/bin/clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
            '-I', str(args.source), str(fixture), '-o', str(executable)]
    subprocess.run(argv, check=True, timeout=30)
    subprocess.run([executable, inputs, wire], check=True, timeout=10)
    data = wire.read_bytes()
    _, (_, _, panels) = parse_packet(data, data[8:24], 321)
    early = panels[0]['early_DPU_handoff']
    assert early['equal_numeric_GOP_addresses'] == ['0'] and early['status'] == 7
    for slot, invalid in ((0, 3), (1, 0xffffffff), (3, 0), (10, 0), (15, 1)):
        corrupted = bytearray(data)
        struct.pack_into('<I', corrupted, TE_END - 8 + 4 * slot, invalid)
        struct.pack_into('<I', corrupted, len(data) - 8, zlib.crc32(corrupted[:-8]))
        try:
            parse_packet(corrupted, data[8:24], 321)
        except ValueError:
            continue
        raise AssertionError(f'Invalid scanout field {slot} accepted')
    (args.out / 'result.json').write_text(json.dumps(dict(passed=True, synthetic=True, command=argv,
        handoff=early, rejected_handoff_mutations=5), indent=2) + '\n')
    print('PASS DPU clock admission, active-pipe selection, CDC, and five negative controls')


if __name__ == '__main__':
    main()
