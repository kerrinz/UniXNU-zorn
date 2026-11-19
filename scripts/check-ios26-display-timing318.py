#!/usr/bin/env python3
"""Exercise the actual display sampler and wire encoder on host registers."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import zlib

from inspect_ios26_ft313 import COST_END, PANEL_BYTES, LAYOUTS, parse_packet


FIXTURE = r'''
#include "ZornManualWire313.h"
#include <cassert>
#include <cstdio>

using namespace ZornDisplayTiming318;

struct Display {
    uint32_t parent = 1, domain = 0x80000000, config = 0x10000, reset = 0;
    uint32_t ahb = 1, mdp = 1, vsync = 1;
    unsigned readCalls = 0, coreReads = 0, interfaceReads = 0;
    unsigned frame = 65500;
    bool losePower = false, readFailure = false;

    bool operator()(Window window, uint32_t offset, uint32_t &value)
    {
        ++readCalls;
        assert(!(offset & 3) && offset + 4 <= Windows[unsigned(window)].bytes);
        if (window == Window::Gcc) {
            assert(!offset);
            value = parent;
            return true;
        }
        if (window == Window::DisplayClock) {
            ++coreReads;
            switch (offset) {
            case 0: value = reset; break;
            case 0x0c: value = mdp; break;
            case 0x24: value = vsync; break;
            case 0xa4: value = ahb; break;
            case 0x1000: value = losePower && interfaceReads ? 0 : domain; break;
            case 0x1004: value = config; break;
            default: assert(false);
            }
            return true;
        }
        ++interfaceReads;
        if (readFailure && offset == 0x2b0) return false;
        switch (offset) {
        case 0x26c: case 0x284: value = 1; break;
        case 0x298: value = (frame & 0xffff) << 16 | 77; break;
        case 0x2b0: case 0xb0: value = 13; break;
        case 0xac: case 0xa4: value = frame; break;
        default: assert(false);
        }
        return true;
    }
};

void check(Display display, bool presented, Result expected, unsigned core, unsigned intf)
{
    uint32_t snap[Words];
    bool stopped = false;
    sample(display, presented, 17, snap, stopped);
    assert(snap[Status] == uint32_t(expected) && snap[UptimeMs] == 17);
    assert(display.coreReads == core && display.interfaceReads == intf);
    if (!presented) assert(display.readCalls == 0);
    if (expected != Result::Observed) {
        for (unsigned field = InterfaceStatus; field < Words; ++field) assert(!snap[field]);
    } else {
        assert(snap[InterfaceFrameCount] == display.frame && (snap[TearReadCount] & 0xffff) == 77);
    }
    if (expected == Result::MissingMapping || expected == Result::UnstablePower) {
        const auto reads = display.readCalls;
        sample(display, true, 18, snap, stopped);
        assert(stopped && snap[Status] == uint32_t(Result::StoppedAfterFault) && display.readCalls == reads);
    }
}

int main(int argc, char **argv)
{
    assert(argc == 3);
    check({}, false, Result::NoPresentation, 0, 0);
    Display display;
    check(display, true, Result::Observed, 12, 7);
    display.parent = 0x80000001;
    check(display, true, Result::ParentClockOff, 0, 0);
    display = {}; display.domain |= 2;
    check(display, true, Result::DomainInactive, 2, 0);
    display = {}; display.config |= 0x8000;
    check(display, true, Result::DomainInactive, 2, 0);
    display = {}; display.mdp = 0;
    check(display, true, Result::DisplayClockOff, 6, 0);
    display = {}; display.reset = 1;
    check(display, true, Result::DisplayClockOff, 6, 0);
    display = {}; display.losePower = true;
    check(display, true, Result::UnstablePower, 8, 7);
    display = {}; display.readFailure = true;
    check(display, true, Result::MissingMapping, 6, 4);

    static_assert(ZornManualWire313::TimingWords == Words);
    uint32_t samples[ZornManualWire313::Words]{};
    FILE *file = fopen(argv[1], "rb");
    assert(file && fread(samples, sizeof(uint32_t), ZornManualWire313::TimingStart, file)
                   == ZornManualWire313::TimingStart && fgetc(file) == EOF && !fclose(file));
    bool stopped = false;
    for (unsigned i = 0; i < ZornManualWire313::Samples; ++i) {
        display = {};
        display.frame += i * 600;
        if (i == 4) display.parent = 0;
        uint32_t snapshot[Words]{};
        sample(display, true, samples[7 + 17*i] + 4, snapshot, stopped);
        for (unsigned field = 0; field < Words; ++field)
            samples[ZornManualWire313::TimingStart + i * Words + field] = snapshot[field];
    }
    const uint8_t tag[16] = {0x31, 0x30};
    char wire[ZornManualWire313::Bytes];
    assert(ZornManualWire313::packet(wire, sizeof(wire), samples, tag) == sizeof(wire));
    file = fopen(argv[2], "wb");
    assert(file && fwrite(wire, 1, sizeof(wire), file) == sizeof(wire) && !fclose(file));
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--previous-fixture', type=Path, required=True)
    parser.add_argument('--sanitizer', choices=('address,undefined', 'thread'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    old = args.previous_fixture.read_bytes()
    assert old[:8] == LAYOUTS[317][0] and len(old) == COST_END
    inputs, fixture, program, wire = [args.out / name for name in
        ('SYNTHETIC-existing-samples.bin', 'fixture.cpp', 'fixture', 'SYNTHETIC-ft318.bin')]
    inputs.write_bytes(old[24:-8])
    fixture.write_text(FIXTURE)
    command = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-fno-omit-frame-pointer',
               '-fsanitize=' + args.sanitizer, '-I' + str(args.source), str(fixture), '-o', str(program)]
    subprocess.run(command, check=True)
    subprocess.run([program, inputs, wire], check=True, env=os.environ | dict(
        UBSAN_OPTIONS='halt_on_error=1', TSAN_OPTIONS='halt_on_error=1'))
    data = wire.read_bytes()
    _, (touch, cost, panel) = parse_packet(data, bytes.fromhex('3130' + '00' * 14), 318)
    assert len(touch) == len(cost) == len(panel) == 9
    assert panel[0]['tear_read_count'] >> 16 == 65500 and panel[1]['tear_read_count'] >> 16 == 564
    assert panel[4]['status'] == 3 and not panel[4]['tear_read_count']
    for index, field, value in ((0, 6, 0), (4, 10, 1), (2, 1, 1), (4, 0, 2)):
        invalid = bytearray(data)
        struct.pack_into('<I', invalid, COST_END - 8 + index * PANEL_BYTES + field * 4, value)
        struct.pack_into('<I', invalid, len(invalid) - 8, zlib.crc32(invalid[:-8]))
        try:
            parse_packet(invalid, data[8:24], 318)
        except ValueError:
            continue
        raise AssertionError('Invalid panel record accepted')
    (args.out / 'result.json').write_text(json.dumps(dict(passed=True, command=command,
        header_sha256=hashlib.sha256((args.source/'ZornDisplayTiming318.h').read_bytes()).hexdigest(),
        packet_bytes=len(data), case_count=13, synthetic_host_registers=True, phone_access=False), indent=2) + '\n')
    print('PASS318 actual sampler and encoder with synthetic clock and panel states')


if __name__ == '__main__':
    main()
