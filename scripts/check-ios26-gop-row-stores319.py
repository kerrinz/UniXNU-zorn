#!/usr/bin/env python3
"""Compare the exact old and new scaled framebuffer row paths on host memory."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


PREFIX = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <thread>
#include <vector>
#include "ZornGopRowStores319.h"
#define ZORN_IOS26 1

class IOMobileFramebuffer {
public:
    uint8_t *fBase = nullptr;
    uint32_t fRowBytes = 0, fPanelHeight = 0;
    const uint32_t *fColumn = nullptr;
    const uint16_t *fColumnWeight = nullptr;
    bool fDiff = false;
    uint64_t fDiffPixels = 0;
    uint32_t fDiffLeft = ~0u, fDiffTop = ~0u, fDiffRight = 0, fDiffBottom = 0;
    void drawRows(const struct RowJob *, int32_t, int32_t, uint32_t *);
};
'''


CASES = r'''
template <class F, class Job>
F run(uint8_t *image, const uint8_t *pixels, const uint32_t *col, const uint16_t *weight,
      unsigned rowBytes, int clipFirst, int clipEnd, bool filter, bool diff, bool parallel)
{
    F fb;
    fb.fBase = image;
    fb.fRowBytes = rowBytes;
    fb.fPanelHeight = 11;
    fb.fColumn = col;
    fb.fColumnWeight = weight;
    fb.fDiff = diff;
    Job job{};
    job.pixels = pixels; job.stride = 7 * 4; job.sx = 1; job.sy = 1; job.sw = 5; job.sh = 4;
    job.px0 = -2; job.px1 = 13; job.py0 = -1; job.py1 = 12;
    job.cx0 = clipFirst; job.cx1 = clipEnd; job.filter = filter;
    uint32_t a[7]{}, b[7]{};
    if (parallel) {
        std::thread first([&] { fb.drawRows(&job, -1, 6, a); });
        fb.drawRows(&job, 6, 12, b);
        first.join();
    } else {
        fb.drawRows(&job, -1, 12, a);
    }
    return fb;
}

int main()
{
    std::vector<uint32_t> source(7*6);
    for (unsigned i = 0; i < source.size(); ++i) source[i] = 0xa9312853u * i + 0x014881f9u;
    uint32_t col[13]{};
    uint16_t weight[13]{};
    for (unsigned pad : {0u, 1u, 4u}) for (unsigned addressPad : {0u, 1u}) {
        unsigned row = 13 + pad;
        for (int first : {0, 1, 2, 12}) for (int end : {13, 12, 11, 1}) {
            if (end <= first) continue;
            for (bool filter : {false, true}) for (bool diff : {false, true}) {
                for (int i = 0; i < 13; ++i) {
                    if (filter) {
                        const auto at = reference::sample_at(i + 2, 5, 15);
                        col[i] = uint32_t(at >> 8);
                        weight[i] = col[i] < 4 ? uint16_t(at & 255) : 0;
                    } else {
                        col[i] = 1 + uint32_t((i + 2) * 5 / 15);
                    }
                }
                std::vector<uint32_t> old(row * 11 + addressPad + 3, 0x2357419b);
                auto changed = old;
                const auto *pixels = reinterpret_cast<const uint8_t *>(source.data());
                auto a = run<reference::IOMobileFramebuffer, reference::RowJob>(reinterpret_cast<uint8_t *>(old.data()+addressPad),
                    pixels, col, weight, row*4, first, end, filter, diff, !diff);
                auto b = run<current::IOMobileFramebuffer, current::RowJob>(reinterpret_cast<uint8_t *>(changed.data()+addressPad),
                    pixels, col, weight, row*4, first, end, filter, diff, !diff);
                assert(old == changed);
                assert(a.fDiffPixels==b.fDiffPixels && a.fDiffLeft==b.fDiffLeft && a.fDiffRight==b.fDiffRight &&
                       a.fDiffTop==b.fDiffTop && a.fDiffBottom==b.fDiffBottom);
                for (unsigned y=0; y<11; ++y) {
                    for (unsigned x=0; x<row; ++x) {
                        if (x < unsigned(first) || x >= unsigned(end)) assert(changed[addressPad+y*row+x] == 0x2357419b);
                    }
                }
            }
        }
    }
    alignas(8) uint32_t single[] = {1, 2, 3};
    ZornGopRowStores319::store(single+1, 0, [](uint32_t) -> uint32_t { assert(false); return 0; });
    ZornGopRowStores319::store(single+1, 1, [](uint32_t at) { assert(at == 0); return 42u; });
    assert(single[0] == 1 && single[1] == 42 && single[2] == 3);
}
'''


def actual_rows(path):
    source = path.read_text()
    begin = source.index('static inline uint32_t\nblend(')
    helpers = source[begin:source.index('#if defined(ZORN_IOS26)\nstruct Zorn26PanelAxis', begin)]
    begin = source.index('struct RowJob {')
    rows = source[begin:source.index('/* A helper of the scaling', begin)]
    return helpers + rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--sanitizer', choices=('address,undefined', 'thread'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    old = args.parent / 'MiniIOMobileFramebuffer.cpp'
    new = args.source / 'MiniIOMobileFramebuffer.cpp'
    header = args.source / 'ZornGopRowStores319.h'
    source = args.out / 'fixture.cpp'
    source.write_text(PREFIX[:PREFIX.index('class IOMobileFramebuffer')]
        + ''.join('namespace ' + name + ' {\n' + PREFIX[PREFIX.index('class IOMobileFramebuffer'):]
                  + actual_rows(path) + '}\n' for name, path in (('reference', old), ('current', new))) + CASES)
    program = args.out / 'fixture'
    command = ['xcrun', 'clang++', '-std=c++17', '-O2', '-g', '-pthread', '-fno-omit-frame-pointer',
               '-fsanitize=' + args.sanitizer, '-I' + str(args.source), str(source), '-o', str(program)]
    subprocess.run(command, check=True)
    subprocess.run([program], check=True, env=os.environ | dict(UBSAN_OPTIONS='halt_on_error=1',
                                                               TSAN_OPTIONS='halt_on_error=1'))
    checks = ('byte-identical clipped bilinear and nearest rows', '32-bit edges and 64-bit aligned pairs',
              'odd/even padded pitch and concurrent row splits', 'unchanged differential diagnostics')
    sources = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (old, new, header)}
    (args.out/'result.json').write_text(json.dumps(dict(passed=True, checks=checks, sources=sources,
        command=command, synthetic_host_memory=True, phone_access=False), indent=2)+'\n')
    print('PASS319 exact baseline and paired GOP row stores')


if __name__ == '__main__':
    main()
