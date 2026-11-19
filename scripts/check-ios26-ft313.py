#!/usr/bin/env python3
"""Validate physical-contact accounting and the actual FT313 packet encoder."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import zlib

from inspect_ios26_ft313 import LAYOUTS, PACKET_BYTES, inspect_progress, parse_packet, split_physical
from inspect_ios26_scroll309 import UI276_BYTES, UI_MAGIC
from inspect_ios26_ui_manual277 import split_manual


FIXTURE = r'''
#include "ZornFt3683Trace313.h"
#include "ZornManualWire313.h"
#include <atomic>
#include <cassert>
#include <cstdio>
#include <thread>
#if defined(ZORN_TEST_COST317)
#include "ZornPresentCost278.h"
#endif

using namespace ZornFt3683Trace313;

int main(int argc, char **argv) {
    assert(argc == 2);
    Trace trace;
    uint32_t seen[Count]{};
    assert(!trace.snapshot(seen));
    trace.poll(false, nullptr, false);
    trace.poll(true, nullptr, false);
    ZornContacts::Frame report{};
    report.count = 1;
    report.points[0] = {10, 5000, 75, 0};  // Edge down in slot zero.
    trace.poll(true, &report, true);
    report.points[0].x = 5000;
    report.count = 2;
    report.points[1] = {8000, 12000, 50, 19};
    trace.poll(true, &report, true);
    ZornContacts::Frame empty{};
    trace.poll(true, &empty, false);  // Failed report cannot retire either ID.
    assert(trace.snapshot(seen));
    assert(seen[Downs] == 2 && seen[Moves] == 1 && seen[Lifts] == 0);
    assert(seen[SeenIds] == ((1u << 19) | 1u) && seen[MaxActive] == 2);
    assert(seen[EdgeDowns] == 1 && seen[MultiContactSamples] == 1);
    trace.poll(true, &empty, true);
    assert(trace.snapshot(seen) && seen[Lifts] == 2);
    trace.poll(true, &report, true);
    trace.forceRelease();
    trace.poll(true, &empty, true);
    assert(trace.snapshot(seen) && seen[Lifts] == 2 && seen[ForcedRelease] == 1);

    std::atomic<bool> done{false};
    std::thread writer([&] {
        for (unsigned i = 0; i < 10000; ++i) trace.poll(true, &empty, true);
        done.store(true);
    });
    do {
        if (trace.snapshot(seen)) {
            assert(seen[Polls] == seen[ReadReturned] + 1);
            assert(seen[ReadReturned] == seen[Decoded] + 1);
            assert(seen[Decoded] == seen[Accepted] + 1);
        }
    } while (!done.load());
    writer.join();
    uint32_t v[ZornManualWire313::Words] = {6, 0, 63, 9, 10000, 90000, 170000};
    static_assert(ZornManualWire313::TouchWords == Count);
#if defined(ZORN_TEST_COST317)
    ZornPresentCost278 cost;
    struct { uint64_t toMicros(uint64_t us) const { return us; } } clock;
#endif
    for (unsigned n = 0; n < 9; ++n) {
        v[7 + 17*n] = 90000 + 10000*n;
        unsigned at = ZornManualWire313::PresentWords + n*(Count+1);
        v[at] = trace.snapshot(seen);
        assert(v[at]);
        for (unsigned i = 0; i < Count; ++i) v[at + 1 + i] = seen[i];
        for (unsigned i = 0; i < 500; ++i) trace.poll(true, &empty, true);
#if defined(ZORN_TEST_COST317)
        cost.attempt();
        cost.result(false, true, true);
        cost.frame = n + 300;
        cost.producer = n + 500;
        cost.measure(ZornPresentCost278::Show, 100, 200, clock);
        uint32_t timing[ZornManualWire313::CostWords]{};
        cost.pack(timing, 89000 + 10000*n);
        if (n != 4) {
            unsigned begin = ZornManualWire313::TouchEnd + n * (1 + ZornManualWire313::CostWords);
            v[begin] = 1;
            for (unsigned i = 0; i < ZornManualWire313::CostWords; ++i) v[begin + 1 + i] = timing[i];
        }
#endif
    }
    const uint8_t tag[16] = {0x31, 0x30};
    char packet[ZornManualWire313::Bytes]{};
    assert(!ZornManualWire313::packet(packet, sizeof(packet)-1, v, tag));
    assert(ZornManualWire313::packet(packet, sizeof(packet), v, tag) == sizeof(packet));
    FILE *file = fopen(argv[1], "wb");
    assert(file && fwrite(packet, 1, sizeof(packet), file) == sizeof(packet));
    assert(!fclose(file));
}
'''

WORKER_FIXTURE = r'''
#include "ZornManualWire313.h"
#define NSEC_PER_SEC 1000000000ULL
void clock_interval_to_deadline(unsigned n, uint64_t unit, uint64_t *out)
{
    assert(n == 5 && unit == NSEC_PER_SEC);
    *out = mach_absolute_time() + n * unit;
}
extern "C" void zorn26_ui_menu_progress274(uint32_t (&out)[16])
{
    // Advance across a millisecond before the first observation stamp.
    ++nowTick;
    out[0] = 7;
}
extern "C" bool zorn26_ft3683_trace313(uint32_t (&out)[ZornManualWire313::TouchWords])
{
    if (nowTick > 100100 && nowTick < 110100) return false;
    out[0] = uint32_t(nowTick);
    if (mode == 12) normalContext = false;
    return true;
}
#if defined(ZORN_TEST_COST317)
extern "C" int zorn26_present_cost_snapshot278(uint32_t (&out)[ZornManualWire313::CostWords])
{
    out[0] = 278;
    out[2] = uint32_t(nowTick) - 1;
    return !(nowTick > 120100 && nowTick < 130100);
}
#endif
'''

WORKER_MAIN = r'''
int main()
{
    for (unsigned testMode : {0u, 9u, 10u, 11u, 12u}) {
        mode = testMode;
        normalContext = boardValid = true;
        nowTick = starts = deallocs = 0;
        pending = nullptr;
        pendingContext = nullptr;
        scheduled269 = done269 = schedulingReturned269 = 0;
        captureDeadline270 = 0;
        for (auto &item : status269) item = 0;
        uint32_t out[ZornManualWire313::Words]{};
        assert(!zorn26_ui_menu_snapshot313(out));
        zorn26_ui_menu_schedule313(&platform);
        zorn26_ui_menu_schedule313(&platform);
        assert(starts == 1);
        if (pending) {
            assert(platform.refs == 2);
            try { pending(pendingContext, 0); } catch (Terminated &) {}
        }
        assert(platform.refs == 1 && zorn26_ui_menu_snapshot313(out));
        assert(!attachedService && !sends && !serviceFrees);
        if (mode == 0 || mode == 10) {
            assert(out[0] == 6 && out[3] == 9 && out[5] == 90001 && out[6] == 170009);
            for (unsigned n = 0; n < 9; ++n) {
                const unsigned at = ZornManualWire313::PresentWords + n * (ZornManualWire313::TouchWords + 1);
                assert(out[at] == (n != 2));
                assert(out[at + 1] == (n == 2 ? 0u : out[7 + 17*n]));
#if defined(ZORN_TEST_COST317)
                const unsigned cost = ZornManualWire313::TouchEnd + n * (ZornManualWire313::CostWords + 1);
                assert(out[cost] == (n != 4));
                assert(out[cost + 1] == (n == 4 ? 0u : 278u));
                assert(out[cost + 3] == (n == 4 ? 0u : out[7 + 17*n] - 1));
#endif
            }
        } else if (mode == 12) {
            assert(out[0] == 7 && out[3] == 1 && out[5] == 90001 && out[6] == 100001);
            assert(out[ZornManualWire313::PresentWords] == 1);
            assert(out[ZornManualWire313::PresentWords + 1] == 90001);
        } else {
            assert(out[0] == 7 && !out[3]);
        }
        nowTick += 4999;
        assert(!zorn26_ui_menu_capture_ready313());
        ++nowTick;
        assert(zorn26_ui_menu_capture_ready313());
    }
}
'''


def actual_observer(source):
    reference = Path(__file__).with_name('check-ios26-ui-service269.py')
    spec = importlib.util.spec_from_file_location('scene269_fixture', reference)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    body = (source / 'ZornUiSceneService269.cpp').read_text()
    assert all(token not in body for token in ('submitFrame(', 'registerService(', 'ZornUiTap275'))
    return base.PREFIX + WORKER_FIXTURE + body[body.index('namespace {'):] + WORKER_MAIN


def mixed_capture_fixture(build, physical, schema):
    source = build / 'root-trial/trial/cdc.raw'
    original = source.read_bytes()
    identity = json.loads((build / 'artifact-identity.json').read_text())
    tag = identity['run_id']
    replacement = bytearray(physical)
    replacement[8:24] = bytes.fromhex(tag)
    struct.pack_into('<I', replacement, len(replacement) - 8, zlib.crc32(replacement[:-8]))
    before, old_magic, after = original.partition(UI_MAGIC)
    assert old_magic and UI_MAGIC not in after
    fixture = before + replacement + after[UI276_BYTES - len(old_magic):]
    report, _ = inspect_progress(fixture, tag, identity['application_probe_run_id'], schema)
    assert report['wire_nonterminal_frames313'] == 38
    assert report['crop297']['complete'] and report['crop297']['packet_count'] == 7
    assert len(report['physical313']) == 9 and report['physical313'][1]['read_success_rate_hz'] == 50
    assert not report['physical_FT3683_functionally_qualified'] and not report['full_GPU_qualification']
    return dict(archived_CDC=str(source), archived_CDC_sha256=hashlib.sha256(original).hexdigest(),
                synthetic_replacement_stream_sha256=hashlib.sha256(fixture).hexdigest(),
                total_frames=38, crop_chunks=7, physical_fixture_samples=9)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--touch-board', type=Path, required=True)
    parser.add_argument('--touch-common', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sanitizer', choices=('address,undefined', 'thread'), required=True)
    parser.add_argument('--wire-schema', type=int, choices=(313, 317), default=313)
    parser.add_argument('--v312-build', type=Path,
                        help='replay the archived CDC with only its synthetic scene frame replaced by the test FT packet')
    args = parser.parse_args()
    schema = args.wire_schema
    args.out.mkdir()
    cpp = args.out / 'fixture.cpp'
    cpp.write_text(FIXTURE)
    app = args.out / 'fixture'
    wire = args.out / f'SYNTHETIC-ft{schema}.bin'
    compiler = ['xcrun', 'clang++', '-std=c++17', '-pthread', '-g', '-O1', '-fno-omit-frame-pointer',
                '-fsanitize=' + args.sanitizer,
                *['-I' + str(p) for p in (args.source, args.touch_board, args.touch_common)]]
    if schema == 317:
        compiler.append('-DZORN_TEST_COST317=1')
    command = [*compiler, str(cpp), '-o', str(app)]
    env = os.environ | dict(ASAN_OPTIONS='symbolize=0', UBSAN_OPTIONS='symbolize=0:halt_on_error=1',
                            TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    subprocess.run(command, env=env, check=True)
    subprocess.run([app, wire], env=env, check=True)
    observer = args.out / 'actual-observer.cpp'
    observer.write_text(actual_observer(args.source))
    observer_app = args.out / 'actual-observer'
    observer_command = [*compiler, str(observer), '-o', str(observer_app)]
    subprocess.run(observer_command, env=env, check=True)
    subprocess.run([observer_app], env=env, check=True)
    payload = wire.read_bytes()
    tag = '3130' + '00'*14
    before = b'fixture-before\r\n'
    after = b'fixture-after\r\n'
    rest, timeline, (samples, costs, panels), partial = split_physical(before + payload + after, tag, schema)
    assert len(payload) == LAYOUTS[schema][1] and not partial and rest == before + after
    assert not panels
    if schema == 317:
        assert len(costs) == 9 and costs[4] is None
        assert costs[0]['show_us'] == 100 and costs[8]['show_us'] == 900
        assert costs[0]['frame'] == 300 and costs[8]['copied_frames'] == 9
        invalid_cost = bytearray(payload)
        struct.pack_into('<I', invalid_cost, PACKET_BYTES - 8 + 68 + 8, 0)
        struct.pack_into('<I', invalid_cost, len(invalid_cost) - 8, zlib.crc32(invalid_cost[:-8]))
    else:
        assert not costs
    _, manual, _ = split_manual(timeline, tag)
    assert manual[0]['count'] == 9 and all(r['edge_downs'] == 1 for r in samples)
    assert samples[0]['accepted'] + 4000 == samples[8]['accepted']
    assert all(r['forced_releases'] == 1 and r['lifts'] == 2 for r in samples)
    bad_crc = bytearray(payload)
    bad_crc[48] ^= 8
    decreased = bytearray(payload)
    struct.pack_into('<I', decreased, 24 + 160*4 + (13*4 + 4), 1)
    struct.pack_into('<I', decreased, len(decreased)-8, zlib.crc32(decreased[:-8]))
    invalid = (bad_crc, decreased, invalid_cost) if schema == 317 else (bad_crc, decreased)
    for data in invalid:
        try:
            parse_packet(data, bytes.fromhex(tag), schema)
        except ValueError:
            continue
        raise AssertionError('Invalid counter envelope was accepted')
    for data, identity in ((payload+payload, tag), (payload, '00'*16), (timeline, tag)):
        try:
            split_physical(data, identity, schema)
        except ValueError:
            continue
        raise AssertionError('Duplicate, foreign, or legacy scene was accepted')
    assert split_physical(payload[:800], tag, schema)[-1] == 800
    files = ('ZornFt3683Trace313.h', 'ZornManualWire313.h', 'ZornUiSceneService269.cpp')
    hashes = {name: hashlib.sha256((args.source/name).read_bytes()).hexdigest() for name in files}
    result = dict(passed=True, commands=[command, observer_command], sources=hashes, synthetic=True,
                  phone_access=False, actual_observer_thread_checked=True, wire_magic=LAYOUTS[schema][0].decode(),
                  wire_bytes=len(payload), actual_dispatch_qualification=False)
    if args.v312_build:
        result['mixed_capture_fixture'] = mixed_capture_fixture(args.v312_build, payload, schema)
    (args.out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'PASS physical trace and observer timing for wire schema {schema}')


if __name__ == '__main__':
    main()
