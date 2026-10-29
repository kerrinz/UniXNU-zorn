#!/usr/bin/env python3
"""Run the actual event adapter with host ABI stubs; no USB or kernel access."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "UniXNU-zorn/native/display"
OUT = ROOT / "out/zorn/touch/dispatch-host-check.json"
abi = r'''
#pragma once
#include <cstdint>
namespace ZornEventABI {
enum { DriverSlots = 220 };
inline uintptr_t original[220], userOriginal[220], events[37];
inline uintptr_t DriverMethods[220], UserDriverMethods[220];
inline const uintptr_t DriverVptr = reinterpret_cast<uintptr_t>(original);
inline const uintptr_t UserDriverVptr = reinterpret_cast<uintptr_t>(userOriginal);
inline const uintptr_t EventVptr = reinterpret_cast<uintptr_t>(events);
}
'''
program = r'''
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
using IOOptionBits = uint32_t;
struct OSArray;
struct OSObject {
    uintptr_t *vptr;
    uint64_t reserved[2] = {};
    OSArray *children = nullptr;
    uint32_t type = 11, index = 1, mask = 2, touch = 1;
    int32_t x = 32768, y = 65535;
};
static_assert(offsetof(OSObject, children) == 24);
struct OSArray : OSObject {
    bool arrayType = true;
    unsigned count = 0;
    OSObject *objects[33] = {};
    unsigned getCount() { return count; }
    OSObject *getObject(unsigned i) { assert(i < count); return objects[i]; }
};
#define OSDynamicCast(type, p) ((p)->arrayType ? (p) : nullptr)
struct Meta {
    unsigned size;
    unsigned getClassSize() { return size; }
};
struct IORegistryEntry {
    uintptr_t *vptr;
    Meta meta;
    unsigned retained = 0;
    Meta *getMetaClass() { return &meta; }
    void retain() { ++retained; }
};
using IOService = IORegistryEntry;
extern "C" { volatile uint32_t zorn_touch_edge_stats[8]; }
#include "ZornTouchEdgeDispatch.h"
static unsigned baseCalls, userCalls;
static IOService *lastDriver;
static OSObject *lastEvent;
static IOOptionBits lastOptions;
static void originalBase(IOService *d, OSObject *e, IOOptionBits o) {
    ++baseCalls; lastDriver = d; lastEvent = e; lastOptions = o;
}
static void originalUser(IOService *d, OSObject *e, IOOptionBits o) {
    ++userCalls; lastDriver = d; lastEvent = e; lastOptions = o;
}
static uint32_t type(void *e) { return static_cast<OSObject *>(e)->type; }
static int32_t integer(void *p, uint32_t field, IOOptionBits) {
    auto *e = static_cast<OSObject *>(p);
    switch (field) {
        case 0xb0005: return e->index;
        case 0xb0007: return e->mask;
        case 0xb0009: return e->touch;
    }
    assert(false); return 0;
}
static void setInteger(void *p, uint32_t field, int32_t value, IOOptionBits) {
    assert(field == 0xb0007); static_cast<OSObject *>(p)->mask = value;
}
static int32_t fixed(void *p, uint32_t field, IOOptionBits) {
    assert(field == 0xb0000 || field == 0xb0001);
    auto *e = static_cast<OSObject *>(p); return field == 0xb0000 ? e->x : e->y;
}
static void reset() {
    ZornTouchEdges::installedDriver = nullptr;
    ZornTouchEdges::originalDispatch = 0;
    ZornTouchEdges::tracker = {};
    for (auto &v : zorn_touch_edge_stats) v = 0;
    baseCalls = userCalls = 0; lastDriver = nullptr; lastEvent = nullptr;
    for (unsigned i = 0; i < 220; ++i) {
        ZornEventABI::original[i] = 0x1000 + i * 8;
        ZornEventABI::userOriginal[i] = 0x9000 + i * 8;
    }
    ZornEventABI::original[198] = reinterpret_cast<uintptr_t>(&originalBase);
    ZornEventABI::userOriginal[198] = reinterpret_cast<uintptr_t>(&originalUser);
    memcpy(ZornEventABI::DriverMethods, ZornEventABI::original, 220 * 8);
    memcpy(ZornEventABI::UserDriverMethods, ZornEventABI::userOriginal, 220 * 8);
    ZornEventABI::events[18] = reinterpret_cast<uintptr_t>(&type);
    ZornEventABI::events[23] = reinterpret_cast<uintptr_t>(&integer);
    ZornEventABI::events[24] = reinterpret_cast<uintptr_t>(&setInteger);
    ZornEventABI::events[25] = reinterpret_cast<uintptr_t>(&fixed);
}
static void send(IOService &d, OSObject &e, IOOptionBits options) {
    reinterpret_cast<void (*)(IOService *, OSObject *, IOOptionBits)>(d.vptr[198])(&d, &e, options);
}
int main() {
    for (unsigned kind : {1U, 2U}) {
        reset();
        uintptr_t *before = kind == 1 ? ZornEventABI::original : ZornEventABI::userOriginal;
        IOService d{before, {kind == 1 ? 0x108U : 0x110U}};
        ZornTouchEdges::install(&d);
        assert(zorn_touch_edge_stats[0] == 1 && zorn_touch_edge_stats[5] == 0);
        assert(zorn_touch_edge_stats[6] == kind && d.retained == 1);
        assert(d.vptr != before && d.vptr[198] != before[198]);
        for (unsigned i = 0; i < 220; ++i) if (i != 198) assert(d.vptr[i] == before[i]);
        assert(!memcmp(before, kind == 1 ? ZornEventABI::DriverMethods : ZornEventABI::UserDriverMethods, 220 * 8));
        OSObject child{ZornEventABI::events};
        OSArray children; children.count = 1; children.objects[0] = &child;
        OSObject root{ZornEventABI::events}; root.children = &children;
        send(d, root, 0x1234);
        assert((child.mask & 0x800) && (root.mask & 0x800));
        assert(zorn_touch_edge_stats[1] == 1 && zorn_touch_edge_stats[2] == 1 && zorn_touch_edge_stats[3] == 1);
        assert(baseCalls == (kind == 1) && userCalls == (kind == 2));
        assert(lastDriver == &d && lastEvent == &root && lastOptions == 0x1234);
        child.y = 32768; child.mask = 0; root.mask = 0; send(d, root, 3);
        assert(child.mask & 0x800); // origin persists while moving to center
        child.touch = 0; child.mask = 2; send(d, root, 4); assert(child.mask & 0x800);
        child.touch = 1; child.mask = 2; root.mask = 0; send(d, root, 5);
        assert(!(child.mask & 0x800) && !(root.mask & 0x800));
        children.count = 33; send(d, root, 6);
        assert(zorn_touch_edge_stats[4] == 1 && baseCalls + userCalls == 5);
        children.count = 1; child.vptr = nullptr; send(d, root, 7);
        assert(zorn_touch_edge_stats[4] == 2 && baseCalls + userCalls == 6);
        ZornTouchEdges::install(&d); assert(d.retained == 1);
    }
    for (unsigned error : {1U, 2U, 3U}) {
        reset(); uintptr_t unknown[220]; memcpy(unknown, ZornEventABI::original, sizeof(unknown));
        IOService d{error == 1 ? unknown : ZornEventABI::original, {error == 2 ? 0x110U : 0x108U}};
        if (error == 3) ZornEventABI::original[45] ^= 1;
        auto *before = d.vptr; ZornTouchEdges::install(&d);
        assert(zorn_touch_edge_stats[5] == error && !zorn_touch_edge_stats[0]);
        assert(d.vptr == before && !d.retained && !ZornTouchEdges::originalDispatch);
    }
}
'''
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    (temp / "OriginalHidEventABI.h").write_text(abi)
    (temp / "check.cpp").write_text("#include <initializer_list>\n" + program)
    subprocess.run(["xcrun", "clang++", "-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-I", str(temp), "-I", str(SOURCE),
                    str(temp / "check.cpp"), "-o", str(temp / "check")], check=True)
    subprocess.run([str(temp / "check")], check=True)
result = dict(passed=True, actual_adapter_source_sha256=hashlib.sha256(
    (SOURCE / "ZornTouchEdgeDispatch.h").read_bytes()).hexdigest(),
    exact_base_and_subclass_dispatch_preserved=True, original_tables_unchanged=True,
    unknown_vptr_size_and_method_mismatch_refused=True, event_lifetime_and_invalid_children=True,
    asan_ubsan=True, hardware_qualified=False)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
