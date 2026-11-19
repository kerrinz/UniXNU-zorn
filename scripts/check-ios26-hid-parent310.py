#!/usr/bin/env python3
"""Host ASan/UBSan + TSan test for ZornHidParentLead310.h and actual touch-frame310/ZornTouchFrameEvent26.cpp."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

MOCK_HID = r'''
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <atomic>
#include <vector>
#include <map>
#include <cassert>

using IOReturn = int32_t;
using IOFixed = int32_t;
using SInt32 = int32_t;
using UInt32 = uint32_t;
using UInt64 = uint64_t;
using IOOptionBits = uint32_t;

enum : IOReturn {
    kIOReturnSuccess = 0,
    kIOReturnNoMemory = -536870211,
    kIOReturnBadArgument = -536870206,
    kIOReturnBusy = -536870187,
};

enum {
    kIOHIDDigitizerTransducerTypeStylus = 0,
    kIOHIDDigitizerTransducerTypeFinger = 2,
    kIOHIDDigitizerTransducerTypeHand = 3,
};

enum : uint32_t {
    kIOHIDDigitizerEventRange = 0x00000001,
    kIOHIDDigitizerEventTouch = 0x00000002,
    kIOHIDDigitizerEventPosition = 0x00000004,
    kIOHIDDigitizerEventIdentity = 0x00000020,
    kIOHIDDigitizerEventFromEdgeTip = 0x00000800,
};

enum : uint32_t {
    kIOHIDEventFieldIsBuiltIn = 0x0004,
    kIOHIDEventFieldDigitizerX = 0xb0000,
    kIOHIDEventFieldDigitizerY = 0xb0001,
    kIOHIDEventFieldDigitizerIndex = 0xb0005,
    kIOHIDEventFieldDigitizerIdentity = 0xb0006,
    kIOHIDEventFieldDigitizerEventMask = 0xb0007,
    kIOHIDEventFieldDigitizerRange = 0xb0008,
    kIOHIDEventFieldDigitizerTouch = 0xb0009,
    kIOHIDEventFieldDigitizerCollection = 0xb000a,
    kIOHIDEventFieldDigitizerButtonMask = 0xb0004,
    kIOHIDEventFieldDigitizerChildEventMask = 0xb0018,
    kIOHIDEventFieldDigitizerIsDisplayIntegrated = 0xb0019,
};

inline std::atomic<int> gLiveHidObjects{0};

class OSObject {
    std::atomic<int> refs_{1};
protected:
    virtual ~OSObject() { gLiveHidObjects.fetch_sub(1, std::memory_order_relaxed); }
public:
    OSObject() { gLiveHidObjects.fetch_add(1, std::memory_order_relaxed); }
    void retain() { refs_.fetch_add(1, std::memory_order_relaxed); }
    void release() {
        if (refs_.fetch_sub(1, std::memory_order_acq_rel) == 1) delete this;
    }
};

class IOHIDEvent;
class OSArray : public OSObject {
    std::vector<OSObject *> items_;
protected:
    ~OSArray() override {
        for (auto *o : items_) if (o) o->release();
    }
public:
    void add(OSObject *o) {
        if (o) o->retain();
        items_.push_back(o);
    }
    unsigned getCount() const { return static_cast<unsigned>(items_.size()); }
    OSObject *getObject(unsigned i) const { return i < items_.size() ? items_[i] : nullptr; }
};

class IOHIDEvent : public OSObject {
    OSArray *children_ = nullptr;
protected:
    ~IOHIDEvent() override {
        if (children_) children_->release();
    }
public:
    uint64_t timestamp = 0;
    uint32_t transducerId = 0;
    int transducerType = 0;
    bool inRange = false;
    uint32_t buttonMaskInit = 0;
    std::map<uint32_t, SInt32> ints;
    std::map<uint32_t, IOFixed> fixeds;

    static IOHIDEvent *digitizerEvent(uint64_t ts, uint32_t tid, int type,
                                      bool range, uint32_t btn, IOFixed x, IOFixed y) {
        auto *e = new IOHIDEvent;
        e->timestamp = ts;
        e->transducerId = tid;
        e->transducerType = type;
        e->inRange = range;
        e->buttonMaskInit = btn;
        e->fixeds[kIOHIDEventFieldDigitizerX] = x;
        e->fixeds[kIOHIDEventFieldDigitizerY] = y;
        if (type == kIOHIDDigitizerTransducerTypeFinger)
            e->ints[kIOHIDEventFieldDigitizerIdentity] = 2;
        return e;
    }
    void setIntegerValue(uint32_t field, SInt32 val) { ints[field] = val; }
    void setFixedValue(uint32_t field, IOFixed val) { fixeds[field] = val; }
    void appendChild(IOHIDEvent *child) {
        if (!children_) children_ = new OSArray;
        children_->add(child);
    }
    OSArray *getChildren() const { return children_; }
};
'''

TEST_MAIN = r'''
#include "ZornTouchFrameEvent26.h"
#include "ZornHidParentLead310.h"
#include <thread>
#include <mutex>
#include <cstring>
#include <cstdio>

int main() {
    // 1. Settings list_scroll down at (16384, 24576) with slot id=1 (and physical FT3683 slot id=0)
    for (unsigned slotId : {0u, 1u, 9u, 19u}) {
        ZornContacts::Frame prev{}, cur{};
        cur.count = 1;
        cur.points[0] = {16384, 24576, 100, static_cast<uint8_t>(slotId)};
        ZornEdgePolicy::Tracker edges{};
        ZornTouchEventBatch26 batch;
        assert(ZornBuildTouchFrameEvents26(cur, prev, edges, 123456ULL, batch) == kIOReturnSuccess);
        assert(batch.count == 1 && batch.events[0] != nullptr);
        auto *parent = batch.events[0];
        const IOFixed ex = ZornHidParentLead310::normalized(16384);
        const IOFixed ey = ZornHidParentLead310::normalized(24576);
        assert(ex > 0x7fff && ey > 0xbfff);
        assert(parent->fixeds[kIOHIDEventFieldDigitizerX] == ex);
        assert(parent->fixeds[kIOHIDEventFieldDigitizerY] == ey);
        assert(parent->ints[kIOHIDEventFieldIsBuiltIn] == 1);
        assert(parent->ints[kIOHIDEventFieldDigitizerCollection] == 1);
        assert(parent->ints[kIOHIDEventFieldDigitizerIsDisplayIntegrated] == 1);
        assert(parent->ints[kIOHIDEventFieldDigitizerRange] == 1);
        assert(parent->ints[kIOHIDEventFieldDigitizerTouch] == 1);
        assert(parent->ints[kIOHIDEventFieldDigitizerChildEventMask] == parent->ints[kIOHIDEventFieldDigitizerEventMask]);
        assert(parent->ints[kIOHIDEventFieldDigitizerChildEventMask] != 0);

        auto *children = parent->getChildren();
        assert(children && children->getCount() == 1);
        auto *child = static_cast<IOHIDEvent *>(children->getObject(0));
        assert(child->transducerId == slotId + 2U);
        assert(child->ints[kIOHIDEventFieldDigitizerIndex] == static_cast<SInt32>(slotId));
        assert(child->ints[kIOHIDEventFieldDigitizerIdentity] == static_cast<SInt32>(slotId + 2U));
        assert(child->fixeds[kIOHIDEventFieldDigitizerX] == ex);
        assert(child->fixeds[kIOHIDEventFieldDigitizerY] == ey);

        // Move to (16384, 12288)
        ZornContacts::Frame moved = cur;
        moved.points[0].y = 12288;
        ZornTouchEventBatch26 moveBatch;
        assert(ZornBuildTouchFrameEvents26(moved, cur, batch.nextEdges, 123500ULL, moveBatch) == kIOReturnSuccess);
        assert(moveBatch.count == 1);
        assert(moveBatch.events[0]->fixeds[kIOHIDEventFieldDigitizerX] == ex);
        assert(moveBatch.events[0]->fixeds[kIOHIDEventFieldDigitizerY] == ZornHidParentLead310::normalized(12288));

        // Lift: active.count == 0, lifted.count == 1 -> parent MUST still carry lifted (x, y), NOT (0, 0)!
        ZornContacts::Frame empty{};
        ZornTouchEventBatch26 liftBatch;
        assert(ZornBuildTouchFrameEvents26(empty, moved, moveBatch.nextEdges, 123600ULL, liftBatch) == kIOReturnSuccess);
        assert(liftBatch.count == 1);
        auto *liftParent = liftBatch.events[0];
        assert(liftParent->fixeds[kIOHIDEventFieldDigitizerX] == ex);
        assert(liftParent->fixeds[kIOHIDEventFieldDigitizerY] == ZornHidParentLead310::normalized(12288));
        assert(liftParent->ints[kIOHIDEventFieldDigitizerTouch] == 0);
        assert(liftParent->ints[kIOHIDEventFieldDigitizerRange] == 0);
    }
    assert(gLiveHidObjects.load() == 0);

    // 2. 10-contact rollover (6 old lifted + 6 new active = 12 > 10 -> 2 collections, both with valid lead (x,y))
    {
        ZornContacts::Frame oldF{}, newF{};
        for (unsigned i = 0; i < 6; ++i) {
            oldF.points[oldF.count++] = {static_cast<uint16_t>(5000 + i * 100), 8000, 50, static_cast<uint8_t>(i)};
            newF.points[newF.count++] = {static_cast<uint16_t>(15000 + i * 100), 18000, 50, static_cast<uint8_t>(i + 6)};
        }
        ZornEdgePolicy::Tracker edges{};
        ZornTouchEventBatch26 over;
        assert(ZornBuildTouchFrameEvents26(newF, oldF, edges, 999ULL, over) == kIOReturnSuccess);
        assert(over.count == 2);
        assert(over.events[0]->fixeds[kIOHIDEventFieldDigitizerX] == ZornHidParentLead310::normalized(5000));
        assert(over.events[0]->fixeds[kIOHIDEventFieldDigitizerY] == ZornHidParentLead310::normalized(8000));
        assert(over.events[1]->fixeds[kIOHIDEventFieldDigitizerX] == ZornHidParentLead310::normalized(15000));
        assert(over.events[1]->fixeds[kIOHIDEventFieldDigitizerY] == ZornHidParentLead310::normalized(18000));
    }
    assert(gLiveHidObjects.load() == 0);

    // 3. Multi-threaded stress + settled framebuffer record pairing under mutex
    std::mutex fbLock;
    uint32_t lastShownRecord[16]{};
    uint32_t fbPixel = 0;
    std::vector<std::thread> threads;
    for (unsigned t = 0; t < 8; ++t) {
        threads.emplace_back([&, t]() {
            for (unsigned iter = 0; iter < 128; ++iter) {
                ZornContacts::Frame prev{}, cur{};
                cur.count = 1;
                cur.points[0] = {static_cast<uint16_t>(4096 + iter * 32), static_cast<uint16_t>(8192 + iter * 16), 80, static_cast<uint8_t>(t % 10)};
                ZornEdgePolicy::Tracker edges{};
                ZornTouchEventBatch26 b;
                assert(ZornBuildTouchFrameEvents26(cur, prev, edges, iter + 1, b) == kIOReturnSuccess);
                assert(b.events[0]->fixeds[kIOHIDEventFieldDigitizerX] != 0);
                if ((t & 1) == 0) {
                    std::lock_guard<std::mutex> g(fbLock);
                    fbPixel = 2000 + iter;
                    lastShownRecord[0] = 2;
                    lastShownRecord[1] = fbPixel;
                    lastShownRecord[9] = 1;
                } else {
                    std::lock_guard<std::mutex> g(fbLock);
                    if (lastShownRecord[0] == 2) {
                        assert(lastShownRecord[1] == fbPixel && lastShownRecord[9] == 1);
                    }
                }
            }
        });
    }
    for (auto &th : threads) th.join();
    assert(gLiveHidObjects.load() == 0);
    std::puts("PASS310 actual ZornTouchFrameEvent26 parent Hand DigitizerX/Y + ChildEventMask + IsBuiltIn + finger identity>=2 across single/move/lift/rollover/8-thread concurrency with zero leaks");
    return 0;
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--touch-os', type=Path, required=True)
    ap.add_argument('--touch-common', type=Path, required=True)
    ap.add_argument('--touch-board', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sanitizer', choices=['asan', 'tsan'], required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)

    inc = a.out / 'mock-inc'
    (inc / 'libkern/c++').mkdir(parents=True)
    (inc / 'IOHIDEvent.h').write_text(MOCK_HID)
    (inc / 'libkern/c++/OSArray.h').write_text('#pragma once\n#include "IOHIDEvent.h"\n')

    test_cpp = a.out / 'test_hid_parent310.cpp'
    test_cpp.write_text(TEST_MAIN)

    san = 'address,undefined' if a.sanitizer == 'asan' else 'thread'
    exe = a.out / 'test_hid_parent310'
    src_frame = a.source / 'touch-frame310/ZornTouchFrameEvent26.cpp'
    src_hdr = a.source / 'ZornHidParentLead310.h'
    args = [
        'xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-pthread', '-fno-omit-frame-pointer',
        '-fsanitize=' + san,
        '-I' + str(inc),
        '-I' + str(a.source / 'touch-frame310'),
        '-I' + str(a.source),
        '-I' + str(a.touch_os),
        '-I' + str(a.touch_common),
        '-I' + str(a.touch_board),
        str(src_frame),
        str(test_cpp),
        '-o', str(exe),
    ]
    env = os.environ | dict(
        ASAN_OPTIONS='symbolize=0:detect_leaks=0',
        UBSAN_OPTIONS='symbolize=0:halt_on_error=1',
        TSAN_OPTIONS='symbolize=0:halt_on_error=1',
    )
    rc = subprocess.run(args, capture_output=True, env=env, timeout=120)
    (a.out / 'compile.stderr').write_bytes(rc.stderr)
    assert rc.returncode == 0, rc.stderr.decode()
    rr = subprocess.run([str(exe)], capture_output=True, env=env, timeout=120)
    (a.out / 'run.stdout').write_bytes(rr.stdout)
    (a.out / 'run.stderr').write_bytes(rr.stderr)
    assert rr.returncode == 0, rr.stderr.decode()
    print(rr.stdout.decode().strip())

    pin = lambda p: dict(path=str(p.resolve()), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    res = dict(
        passed=True,
        sanitizer=a.sanitizer,
        sources=[pin(src_hdr), pin(src_frame), pin(a.touch_os / 'ZornTouchFrameEvent26.h'),
                 pin(a.source / 'touch-frame310/ZornTouchRollover26.h')],
        arguments=args,
        stdout=rr.stdout.decode().strip(),
        zero_live_hid_leaks=True,
        phone_access=False,
        hardware_qualified=False,
    )
    (a.out / 'result.json').write_text(json.dumps(res, indent=2) + '\n')


if __name__ == '__main__':
    main()
