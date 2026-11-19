// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ArmSmmu4K.h"
#include "GpiSpiRings.h"

namespace ZornFt3683DmaMemory {

constexpr unsigned CpuPageBytes = 16384;
constexpr unsigned SmmuPageBytes = 4096;
constexpr uint64_t GpiWindow = 0x00100000;
constexpr uint64_t QupWindow = 0x40000000;
static_assert(GpiSpi::ChannelEntries * sizeof(GpiSpi::RingElement) * 2 <= SmmuPageBytes);
static_assert(GpiSpi::EventEntries * sizeof(GpiSpi::RingElement) <= SmmuPageBytes);

struct Page {
    uint8_t *cpu;
    uint64_t physical;
};

struct Mapping {
    GpiSpi::RingSet rings;
    uint8_t *txBuffer;
    uint8_t *rxBuffer;
    uint64_t txIova;
    uint64_t rxIova;
    ArmSmmu4KConfig gpi;
    ArmSmmu4KConfig qup;
    ArmSmmu4KRange gpiRanges[2];
    ArmSmmu4KRange qupRanges[2];
    ArmSmmu4KResult gpiTables;
    ArmSmmu4KResult qupTables;
};

inline bool valid(const Page &page)
{
    const uintptr_t address = reinterpret_cast<uintptr_t>(page.cpu);
    constexpr uint64_t mask = CpuPageBytes - 1;
    return address && !(address & mask) && address <= UINTPTR_MAX - CpuPageBytes &&
           page.physical && !(page.physical & mask) && page.physical <= UINT64_MAX - CpuPageBytes;
}

inline bool distinct(const Page &a, const Page &b)
{
    // After validation the spans have equal length and are page-aligned.
    return a.cpu != b.cpu && a.physical != b.physical;
}

// A caller leases three verified, disjoint contiguous 16 KiB CPU pages.
// One contains coherent transfer/event rings and wire buffers. Each of the
// other two contains one inactive 4 KiB-granule APPs SMMU page-table tree.
// Publish no pointers to hardware until both trees and the live stream
// ownership have been verified. Block the streams and stop their users
// before dismantling any of these leases.
inline ArmSmmu4KStatus build(const Page &data, const Page &gpiTables, const Page &qupTables,
                            unsigned outputBits, Mapping &out)
{
    out = {};
    if (!valid(data) || !valid(gpiTables) || !valid(qupTables) ||
        !distinct(data, gpiTables) || !distinct(data, qupTables) || !distinct(gpiTables, qupTables)) {
        return ArmSmmu4KArgument;
    }
    constexpr unsigned rxRingOffset = GpiSpi::ChannelEntries * sizeof(GpiSpi::RingElement);
    constexpr unsigned eventOffset = SmmuPageBytes, txOffset = 2 * SmmuPageBytes, rxOffset = 3 * SmmuPageBytes;
    constexpr unsigned read = ArmSmmu4KRead;
    constexpr unsigned readWrite = ArmSmmu4KRead | ArmSmmu4KWrite;
    constexpr unsigned writeback = 1, innerShareable = 3;
    Mapping mapping{};
    mapping.gpi = {32, outputBits, gpiTables.physical, 2};
    mapping.qup = {32, outputBits, qupTables.physical, 2};
    mapping.gpiRanges[0] = {GpiWindow, data.physical, SmmuPageBytes, read, writeback, innerShareable};
    mapping.gpiRanges[1] = {GpiWindow + SmmuPageBytes, data.physical + eventOffset,
                           SmmuPageBytes, readWrite, writeback, innerShareable};
    mapping.qupRanges[0] = {QupWindow, data.physical + txOffset, SmmuPageBytes, read, writeback, innerShareable};
    mapping.qupRanges[1] = {QupWindow + SmmuPageBytes, data.physical + rxOffset,
                           SmmuPageBytes, readWrite, writeback, innerShareable};
    constexpr unsigned tableCapacity = CpuPageBytes / SmmuPageBytes;
    auto status = ArmSmmu4KBuild(&mapping.gpi, mapping.gpiRanges, 2, reinterpret_cast<uint64_t *>(gpiTables.cpu),
                                tableCapacity, &mapping.gpiTables);
    if (status != ArmSmmu4KSuccess) return status;
    status = ArmSmmu4KBuild(&mapping.qup, mapping.qupRanges, 2, reinterpret_cast<uint64_t *>(qupTables.cpu),
                           tableCapacity, &mapping.qupTables);
    if (status != ArmSmmu4KSuccess) return status;
    mapping.rings = {{reinterpret_cast<GpiSpi::RingElement *>(data.cpu), GpiWindow},
                     {reinterpret_cast<GpiSpi::RingElement *>(data.cpu + rxRingOffset), GpiWindow + rxRingOffset},
                     {reinterpret_cast<GpiSpi::RingElement *>(data.cpu + eventOffset), GpiWindow + SmmuPageBytes}};
    mapping.txBuffer = data.cpu + txOffset;
    mapping.rxBuffer = data.cpu + rxOffset;
    mapping.txIova = QupWindow;
    mapping.rxIova = QupWindow + SmmuPageBytes;
    out = mapping;
    return ArmSmmu4KSuccess;
}

} // namespace ZornFt3683DmaMemory
