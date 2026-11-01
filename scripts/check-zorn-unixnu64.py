#!/usr/bin/env python3
"""Check the actual partition selector and write boundaries without device I/O."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--gpt', required=True, type=Path)
args = p.parse_args()
source = Path(__file__).resolve().parents[1] / 'native/ufs-read'
test = r'''
#define ZORN_UNIXNU64 1
#define ZORN_DATA_8G 1
#include "ZornDataStorePolicy.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    assert(argc == 2);
    unsigned char disk[24576] = {};
    FILE *file = fopen(argv[1], "rb"); assert(file);
    assert(fread(disk, 1, sizeof(disk), file) == sizeof(disk)); fclose(file);
    unsigned char *entries = disk + 8192;
    const unsigned char *entry = zornUnixnu64Entry(entries, 128, 128);
    assert(entry == entries + 34*128);
    assert(zornDataGeometry(47271680, 64048895, 9382658048ULL, 49563392));
    assert(!zornDataGeometry(3112704, 47271679, 9382658048ULL, 5404416));
    assert(kZornDataFirst == 51465984 && kZornDataWindowBlocks == 2097217);
    assert(zornDataRange(0, 1) && zornDataRange(2097216, 1));
    assert(!zornDataRange(2097217, 1) && !zornDataRange(2097216, 2));
    assert(!zornDataRange(0, 0) && !zornDataRange(0, 33));
    unsigned char saved[128]; memcpy(saved, entry, 128);
    for (unsigned i=0; i<56; ++i) {
        entries[34*128+i] ^= 1;
        assert(!zornUnixnu64Entry(entries, 128, 128));
        entries[34*128+i] ^= 1;
    }
    memcpy(entries+35*128, saved, 128);
    assert(!zornUnixnu64Entry(entries, 128, 128)); // duplicate name
    memset(entries+35*128, 0, 128);
    memset(entries+34*128, 0, 128);
    assert(!zornUnixnu64Entry(entries, 128, 128)); // userdata never fallback
    memcpy(entries+34*128, saved, 128);
    assert(!zornUnixnu64Entry(entries, 0, 128));
    assert(!zornUnixnu64Entry(entries, 257, 128));
    assert(!zornUnixnu64Entry(entries, 128, 129));
    assert(!zornUnixnu64Entry(nullptr, 128, 128));
    unsigned char u[32] = {}; u[0]=1; u[1]=0x20; u[14]=0x10;
    u[16]=0x2a; u[17]=8; u[24]=1;
    auto command = [&](uint64_t lba) {
        for (unsigned i=0;i<4;++i) u[18+i]=lba>>(24-8*i);
        return zornDataCommandAllowed(u,32,1,4096,2,true);
    };
    assert(command(kZornDataFirst) && command(kZornDataFirst+2097216));
    assert(!command(kZornDataFirst-1) && !command(kZornDataFirst+2097217));
    assert(!command(3112704) && !command(47271679)); // actual Android partition
    assert(!command(49563392)); // log uses its separate one-block guard
    puts("PASS actual GPT selector, 56 identity corruptions, duplicate/missing, Data and CDB fences");
}
'''
with tempfile.TemporaryDirectory(prefix='zorn-unixnu64-') as tmp:
    src = Path(tmp)/'test.cpp'; exe = Path(tmp)/'test'
    src.write_text(test)
    subprocess.run(['xcrun','clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined',
                    '-Wall','-Wextra','-Werror','-I',str(source),str(src),'-o',str(exe)],check=True)
    subprocess.run([str(exe),str(args.gpt.resolve())],check=True)
