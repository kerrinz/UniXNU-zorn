#!/usr/bin/env python3
"""Exercise the v325 startup caller and the exact CDC wire with host-only transports."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import zlib

from inspect_ios26_ft313 import LAYOUTS, RESOURCES_END, display_lease, parse_packet, split_physical


FIXTURE = r'''
#include "ZornManualWire313.h"
#include <cassert>
#include <cstdio>

using namespace ZornDisplayLeaseProbe325;

int main(int argc, char **argv)
{
    assert(argc == 3);
    uint32_t values[ZornManualWire313::Words]{};
    auto *input = fopen(argv[1], "rb");
    assert(input && fread(values, 4, ZornManualWire313::LeaseStart, input) == ZornManualWire313::LeaseStart);
    assert(fgetc(input) == EOF && fclose(input) == 0);
    auto *file = fopen(argv[2], "wb");
    assert(file);
    const uint8_t tag[16] = {0x32, 5};
    for (unsigned test = 0; test <= 6; ++test) {
        unsigned reads = 0, calls = 0;
        bool held = false;
        auto read = [&](uint32_t &word) {
            if (++reads == (test == 1 ? 1u : test == 3 ? 2u : test == 5 ? 3u : 0u)) return false;
            word = 0x80000003;
            return true;
        };
        const auto setLease = [&](bool hold) -> uint32_t {
            ++calls;
            assert(hold != held);
            if ((hold && test == 2) || (!hold && test == 4)) return 0xe00002d8;
            held = hold;
            return 0;
        };
        auto steps = [&](bool hold) -> uint32_t {
            return hold ? (test == 2 ? 15 : 127) : (test == 4 ? 65 : 253);
        };
        uint32_t snapshot[Words]{};
        if (test) {
            const auto result = run(read, setLease, steps, 32050, 0xe00002ca, snapshot);
            assert(snapshot[Status] == test);
            assert(result == (test == Returned ? 0u : test == 2 || test == 4 ? 0xe00002d8u : 0xe00002cau));
            assert(calls == (test >= 4 ? 2u : test >= 2 ? 1u : 0u));
            assert(held == (test == HeldClockUnavailable || test == ReleaseFailed));
        }
        memcpy(values + ZornManualWire313::LeaseStart, snapshot, sizeof(snapshot));
        char wire[ZornManualWire313::Bytes];
        assert(ZornManualWire313::packet(wire, sizeof(wire), values, tag) == sizeof(wire));
        assert(fwrite(wire, 1, sizeof(wire), file) == sizeof(wire));
    }
    assert(fclose(file) == 0);
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
    parse_packet(previous, previous[8:24], 322)
    inputs = args.out / 'SYNTHETIC-v322-words.bin'
    inputs.write_bytes(previous[24:-8])
    fixture = args.out / 'fixture.cpp'
    fixture.write_text(FIXTURE)
    executable = args.out / 'fixture'
    output = args.out / 'SYNTHETIC-lease325-packets.bin'
    cc = ['/usr/bin/clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
          '-I', str(args.source), str(fixture), '-o', str(executable)]
    subprocess.run(cc, check=True, timeout=30)
    subprocess.run([executable, inputs, output], check=True, timeout=10)
    packets = output.read_bytes()
    _, size = LAYOUTS[325]
    assert len(packets) == 7 * size
    for index in range(7):
        packet = packets[index*size:(index+1)*size]
        _, (_, _, panels) = parse_packet(packet, packet[8:24], 325)
        lease = display_lease(packet)
        assert (lease is None if index == 0 else lease['status'] == index)
        assert panels and panels[0].get('display_register_resource_lease') == lease
    good = packets[-size:]
    for field, bad in ((0, 7), (2, 1), (3, 1), (7, 63), (8, 125)):
        corrupt = bytearray(good)
        struct.pack_into('<I', corrupt, RESOURCES_END - 8 + field*4, bad)
        struct.pack_into('<I', corrupt, size-8, zlib.crc32(corrupt[:-8]))
        try:
            parse_packet(corrupt, good[8:24], 325)
        except ValueError:
            continue
        raise AssertionError(f'Invalid lease field {field} accepted')
    assert split_physical(good[:-1], good[8:24].hex(), 325)[3] == size - 1
    try:
        split_physical(previous, good[8:24].hex(), 325)
    except ValueError:
        pass
    else:
        raise AssertionError('v322 wire accepted as v325')
    (args.out / 'result.json').write_text(json.dumps(dict(passed=True, synthetic=True, command=cc,
        bytes=size, checked_states=7, invalid_lease_fields=5, held_read_failure_preserves_lease=True,
        returned_lease=display_lease(good)), indent=2) + '\n')
    print('PASS v325 startup caller, schema 325 CDC, previous schema and failure/retention controls')


if __name__ == '__main__':
    main()
