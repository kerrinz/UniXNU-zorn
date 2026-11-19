#!/usr/bin/env python3
"""Test the compiled K80 TE sampler, packet and host decoder."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

from inspect_ios26_ft313 import LAYOUTS, PANEL_END, parse_packet


FIXTURE = r'''
#include "ZornManualWire313.h"
#include <cassert>
#include <cstdio>

using namespace ZornPanelTe320;

struct Pad {
    uint64_t now = 190000000;
    unsigned step = 0, ctlReads = 0, inputReads = 0;
    unsigned period = 8333;
    uint32_t ctl = 4;
    bool moved = false, stoppedTime = false, failInput = false;

    bool read(uint32_t offset, uint32_t &value)
    {
        assert(offset == 0 || offset == 4);
        if (offset == 0) {
            value = ctl;
            if (ctlReads++ && moved) value ^= 1;
            return true;
        }
        ++inputReads;
        value = period && (step % period) < 150;
        return !failInput;
    }

    void poll(bool displayed, uint32_t (&snap)[Words])
    {
        auto readPad = [&](uint32_t offset, uint32_t &value) { return read(offset, value); };
        auto clock = [&] { return now + step; };
        auto delay = [&](unsigned us) { if (!stoppedTime) step += us; };
        sample(readPad, clock, delay, displayed, snap);
    }
};

int main(int argc, char **argv)
{
    assert(argc == 3);
    uint32_t snap[Words]{};
    Pad pad;
    pad.poll(false, snap);
    assert(snap[Status] == uint32_t(Outcome::NoPresentation) && !pad.ctlReads);
    pad.ctl = (1 << 9) | 4;
    pad.poll(true, snap);
    assert(snap[Status] == uint32_t(Outcome::UnexpectedPad) && !pad.inputReads);
    pad = {}; pad.ctl = (1 << 11) | 4;
    pad.poll(true, snap);
    assert(snap[Status] == uint32_t(Outcome::UnexpectedPad) && !pad.inputReads);
    pad = {}; pad.failInput = true;
    pad.poll(true, snap);
    assert(snap[Status] == uint32_t(Outcome::ReadUnavailable) && pad.inputReads == 1);
    pad = {}; pad.moved = true;
    pad.poll(true, snap);
    assert(snap[Status] == uint32_t(Outcome::PadChanged) && pad.ctlReads == 2);
    pad = {}; pad.stoppedTime = true;
    pad.poll(true, snap);
    assert(snap[Status] == uint32_t(Outcome::Incomplete) && pad.inputReads == PollLimit);
    pad = {}; pad.period = 0;
    pad.poll(true, snap);
    assert(snap[Status] == uint32_t(Outcome::Observed) && !snap[FallingEdges]);
    pad = {};
    pad.poll(true, snap);
    assert(snap[Status] == uint32_t(Outcome::Observed) && pad.ctlReads == 2);
    assert(snap[ElapsedUs] == SampleUs && snap[MaxGapUs] == PollUs && snap[FallingEdges] == 20);

    uint32_t values[ZornManualWire313::Words]{};
    FILE *file = fopen(argv[1], "rb");
    assert(file && fread(values, 4, ZornManualWire313::TeStart, file) == ZornManualWire313::TeStart
           && fgetc(file) == EOF && !fclose(file));
    memcpy(values + ZornManualWire313::TeStart, snap, sizeof(snap));
    const uint8_t tag[16] = {0x32};
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
    assert previous[:8] == LAYOUTS[318][0] and len(previous) == PANEL_END
    parse_packet(previous, previous[8:24], 318)
    inputs, fixture, executable, wire = (args.out / name for name in (
        'SYNTHETIC-existing-samples.bin', 'fixture.cpp', 'fixture', 'SYNTHETIC-ft320.bin'))
    inputs.write_bytes(previous[24:-8])
    fixture.write_text(FIXTURE)
    argv = ['/usr/bin/clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
            '-I', str(args.source), str(fixture), '-o', str(executable)]
    subprocess.run(argv, check=True, timeout=30)
    subprocess.run([executable, inputs, wire], check=True, timeout=10)
    data = wire.read_bytes()
    _, (_, _, panels) = parse_packet(data, data[8:24], 320)
    observation = panels[-1]['external_TE']
    assert 119.9 < observation['steady_sample_hz'] < 120.2
    offset = PANEL_END - 8
    for slot, invalid in ((2, 0), (4, 150000), (5, 16002), (7, 33), (9, 1)):
        corrupted = bytearray(data)
        struct.pack_into('<I', corrupted, offset + 4 * slot, invalid)
        struct.pack_into('<I', corrupted, len(data) - 8, zlib.crc32(corrupted[:-8]))
        try:
            parse_packet(corrupted, data[8:24], 320)
        except ValueError:
            continue
        raise AssertionError(f'Invalid TE field {slot} accepted')
    (args.out / 'result.json').write_text(json.dumps(dict(passed=True, synthetic=True, command=argv,
        observation=observation, rejected_TE_mutations=5, sha256=hashlib.sha256(data).hexdigest()), indent=2) + '\n')
    print('PASS actual TE sampler and CDC encoding, legacy decoder, five negative controls')


if __name__ == '__main__':
    main()
