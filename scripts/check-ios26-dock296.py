#!/usr/bin/env python3
"""Build the actual Dock sampler and validate its CDC pixels and rejection paths."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import zlib

from inspect_ios26_dock296 import PIXEL_END, split_dock

SAMPLER = r'''
#include "ZornSerialDock296.h"
#include <cassert>
#include <cstdio>
#include <vector>

int main(int argc, char **argv) {
    assert(argc == 2);
    constexpr unsigned width = 208, height = 384, stride = width * 4;
    std::vector<uint32_t> screen(width * height);
    for (unsigned y = 0; y < height; ++y) {
        for (unsigned x = 0; x < width; ++x) screen[y * width + x] = 0xff000000u | y << 12 | x;
    }
    const unsigned geometry[16] = {2, 64, 7, 2, 7, 7, 1, 3, 1, 1, 1, 63, 64, width, height, 7};
    const uint8_t tag[16] = {0x29, 0x6a};
    ZornSerialDock296 shot;
    assert(!shot.ready() && shot.request() && !shot.request() && shot.pending());
    assert(!shot.capture(screen.data(), width, height - 1, stride, screen.size() * 4, geometry));
    assert(!shot.capture(screen.data(), width, height, stride, screen.size() * 4 - 1, geometry));
    assert(shot.capture(screen.data(), width, height, stride, screen.size() * 4, geometry));
    assert(shot.ready() && !shot.pending());
    assert(!shot.capture(screen.data(), width, height, stride, screen.size() * 4, geometry));
    FILE *wire = fopen(argv[1], "wb");
    assert(wire);
    fputs("fixture-before\r\n", wire);
    for (unsigned offset = 0; offset < shot.Bytes;) {
        char packet[3072]{};
        const unsigned count = shot.packet(packet, sizeof(packet), offset, tag);
        assert(count > shot.PacketHeader && count <= sizeof(packet));
        assert(fwrite(packet, 1, count, wire) == count);
        offset += count - shot.PacketHeader;
    }
    fputs("fixture-after\r\n", wire);
    assert(fclose(wire) == 0);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    source = args.out / 'fixture.cpp'
    source.write_text(SAMPLER)
    binary = args.out / 'fixture'
    wire = args.out / 'SYNTHETIC-dock-wire.bin'
    command = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
               '-fno-omit-frame-pointer', '-I' + str(args.source), str(source), '-o', str(binary)]
    env = os.environ | dict(ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1')
    subprocess.run(command, env=env, check=True)
    subprocess.run([binary, wire], env=env, check=True)
    tag = '296a' + '00' * 14
    data = wire.read_bytes()
    rest, image, dock = split_dock(data, tag)
    assert rest == b'fixture-before\r\nfixture-after\r\n'
    assert dock['complete'] and dock['packet_count'] == 7
    assert dock['source_roi'] == dict(x=0, y=288, width=208, height=96)
    assert dock['source_present_record'][1:8] == (64, 7, 2, 7, 7, 1, 3)
    pixels = struct.unpack('<4992I', image[16:PIXEL_END])
    assert pixels == tuple(0xff000000 | (288 + 2 * y) << 12 | (2 * x)
                           for y in range(48) for x in range(104))
    offset = len(b'fixture-before\r\n')
    bad_payload = bytearray(data)
    bad_payload[offset + 68] ^= 1
    bad_crop = bytearray(data)
    struct.pack_into('<I', bad_crop, offset + 52, 0)
    struct.pack_into('<I', bad_crop, offset + 64, zlib.crc32(bad_crop[offset:offset + 64]))
    for wrong_data, wrong_tag in [(data, '00' * 16), (bad_payload, tag), (bad_crop, tag)]:
        try:
            split_dock(wrong_data, wrong_tag)
        except ValueError:
            continue
        raise AssertionError('Accepted invalid Dock capture')
    _, _, partial = split_dock(data[:offset + 80], tag)
    assert partial['partial_packet_bytes'] == 80 and not partial['complete']
    header = args.source / 'ZornSerialDock296.h'
    report = dict(passed=True, phone_access=False, fixture_pixels=len(pixels),
                  boot_mismatch_rejected=True, payload_corruption_rejected=True,
                  wrong_roi_rejected=True, incomplete_chunk_reported=True,
                  source_sha256=hashlib.sha256(header.read_bytes()).hexdigest(), command=command)
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS Dock sampler, 4992 exact pixels, seven CRC chunks and rejection paths')


if __name__ == '__main__':
    main()
