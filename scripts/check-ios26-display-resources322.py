#!/usr/bin/env python3
"""Validate shared CommandDB resolution and its CDC encoding."""

import argparse
import json
from pathlib import Path
import struct
import subprocess
import zlib

from inspect_ios26_ft313 import HANDOFF_END, LAYOUTS, parse_packet


FIXTURE = r'''
#include "ZornManualWire313.h"
#include "ZornDisplayResources322.h"
#include <cassert>
#include <cstdio>

using namespace ZornDisplayResources322;
using namespace ZornGen7Rpmh;
using Read = CommandDbReadStatus;

struct Reader : NativeCommandDbResourceReader {
    unsigned reads = 0;
    bool fail = false;
    Read copyActualStandalone(bool &) override { assert(false); return Read::Rejected; }
    Read copyActualAddress(const uint8_t (&)[8], CommandDbResource &) override
    { assert(false); return Read::Rejected; }
    Read copyActualAuxPrefix(const uint8_t (&id)[8], CommandDbResource &out, void *aux,
                             size_t capacity, size_t used) override
    {
        const unsigned i = reads++;
        assert(i < BcmCount && !memcmp(id, BcmIds[i], 8) && capacity == 8 && used == 8);
        const uint8_t actual[] = {0xe8, 3, 0, 0, 16, 0, 3, 0};
        memcpy(aux, actual, used);
        out = {0x11100 + 4 * i, uint16_t(fail && i == 0 ? 4 : 8), 1};
        return fail && i == 1 ? Read::Missing : Read::Available;
    }
    Read copyActualResource(const uint8_t (&id)[8], CommandDbResource &out, void *aux, size_t capacity) override
    {
        const unsigned i = reads++ - BcmCount;
        assert(i < ArcCount && !memcmp(id, ArcIds[i], 8) && capacity == 32);
        const uint8_t actual[] = {0, 0, 64, 0, 128, 0, 0, 0, 0, 0};
        const uint8_t invalid[] = {0, 0, 128, 0, 64, 0, 0, 0, 0, 0};
        memcpy(aux, fail && i == 2 ? invalid : actual, sizeof(actual));
        out = {0x21100 + 4 * i, uint16_t(sizeof(actual)), fail && i == 0 ? 2u : 1u};
        return Read::Available;
    }
};

int main(int argc, char **argv)
{
    assert(argc == 3);
    Reader reader;
    reader.fail = true;
    uint32_t data[Words]{};
    resolve(reader, data);
    assert(reader.reads == BcmCount + ArcCount);
    assert(data[0] == Invalid && data[1] == 0 && data[BcmWords] == Missing);
    assert(data[ArcStart] == Invalid && data[ArcStart + 2 * ArcWords] == Invalid);
    reader.reads = 0;
    reader.fail = false;
    resolve(reader, data);
    assert(reader.reads == BcmCount + ArcCount);
    assert(data[0] == Available && data[3] == 1000);
    assert(data[ArcStart] == Available && data[ArcStart + 3] == 3);

    uint32_t values[ZornManualWire313::Words]{};
    FILE *file = fopen(argv[1], "rb");
    assert(file && fread(values, 4, ZornManualWire313::ResourcesStart, file) == ZornManualWire313::ResourcesStart
           && fgetc(file) == EOF && !fclose(file));
    memcpy(values + ZornManualWire313::ResourcesStart, data, sizeof(data));
    const uint8_t tag[16] = {0x32, 2};
    char wire[ZornManualWire313::Bytes];
    assert(ZornManualWire313::packet(wire, sizeof(wire), values, tag) == sizeof(wire));
    file = fopen(argv[2], "wb");
    assert(file && fwrite(wire, 1, sizeof(wire), file) == sizeof(wire) && !fclose(file));
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reader-include', type=Path, required=True)
    parser.add_argument('--previous-fixture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    previous = args.previous_fixture.read_bytes()
    assert previous[:8] == LAYOUTS[321][0] and len(previous) == HANDOFF_END
    parse_packet(previous, previous[8:24], 321)
    input_data, fixture, executable, wire = (args.out / name for name in (
        'SYNTHETIC-existing-samples.bin', 'fixture.cpp', 'fixture', 'SYNTHETIC-ft322.bin'))
    input_data.write_bytes(previous[24:-8])
    fixture.write_text(FIXTURE)
    argv = ['/usr/bin/clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
            '-I', str(args.source), '-I', str(args.reader_include), str(fixture), '-o', str(executable)]
    subprocess.run(argv, check=True, timeout=30)
    subprocess.run([executable, input_data, wire], check=True, timeout=10)
    data = wire.read_bytes()
    _, (_, _, panels) = parse_packet(data, data[8:24], 322)
    resources = panels[0]['display_CommandDB']
    assert resources['all_resolved_distinct'] and resources['arc']['mmcx.lvl']['levels'] == [0, 64, 128]
    for slot, invalid in ((1, 1), (2, 7), (15, 1), (17, 33), (18, 17)):
        corrupted = bytearray(data)
        struct.pack_into('<I', corrupted, HANDOFF_END - 8 + 4 * slot, invalid)
        struct.pack_into('<I', corrupted, len(data) - 8, zlib.crc32(corrupted[:-8]))
        try:
            parse_packet(corrupted, data[8:24], 322)
        except ValueError:
            continue
        raise AssertionError(f'Invalid CommandDB field {slot} accepted')
    (args.out / 'result.json').write_text(json.dumps(dict(passed=True, synthetic=True, command=argv,
        resources=resources, rejected_mutations=5), indent=2) + '\n')
    print('PASS display CommandDB reuse, CDC layout, and malformed-resource controls')


if __name__ == '__main__':
    main()
