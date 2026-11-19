// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornScanoutHandoff345.h"
#include <IOKit/IOMemoryDescriptor.h>
#include <kern/task.h>
#include <mach/vm_param.h>
#include <machine/machine_routines.h>
#include <pexpert/device_tree.h>

extern unsigned long gPhysBase, gPhysSize;
extern "C" uint64_t kvtophys(vm_offset_t);

namespace ZornScanoutAlias345 {

inline void observe(uint32_t (&out)[Words])
{
    out[Status] = ZornScanoutPropertyMissing;
    DTEntry chosen;
    const void *data = nullptr;
    unsigned size = 0;
    if (SecureDTLookupEntry(nullptr, "/chosen", &chosen) != kSuccess ||
        SecureDTGetProperty(chosen, ZORN_SCANOUT_PROPERTY, &data, &size) != kSuccess) return;

    enum ZornScanoutFirmwareStatus witness = ZornScanoutNoWitness;
    out[Status] = ZornScanoutPropertyInvalid;
    if (!zorn_scanout_decode(data, size, &witness)) return;
    out[FirmwareStatus] = witness;
    out[Status] = ZornScanoutFirmwareDenied;
    if (witness != ZornScanoutReserved) return;

    out[Status] = ZornScanoutKernelGeometryMismatch;
    if (PAGE_SIZE != 16384 || !zorn_scanout_matches_window(gPhysBase, gPhysSize)) return;

    out[PageBytes] = PAGE_SIZE;
    out[PhysicalBase] = ZORN_SCANOUT_BACK;
    out[Extent] = ZORN_SCANOUT_BYTES;
    out[Status] = ZornScanoutDescriptorFailed;
    auto *descriptor = IOMemoryDescriptor::withPhysicalAddress(ZORN_SCANOUT_BACK, ZORN_SCANOUT_BYTES,
                                                                kIODirectionIn | kIOMemoryMapperNone);
    if (!descriptor) return;
    IOByteCount contiguous = 0;
    if (descriptor->getLength() != ZORN_SCANOUT_BYTES ||
        descriptor->getPhysicalSegment(0, &contiguous, kIOMemoryMapperNone) != ZORN_SCANOUT_BACK ||
        contiguous < ZORN_SCANOUT_BYTES) {
        descriptor->release();
        return;
    }
    out[Status] = ZornScanoutMappingFailed;
    auto *map = descriptor->createMappingInTask(kernel_task, 0,
        kIOMapAnywhere | kIOMapInhibitCache | kIOMapReadOnly, 0, ZORN_SCANOUT_BYTES);
    if (map) {
        out[Status] = ZornScanoutWrongAlias;
        const auto start = map->getVirtualAddress();
        if (start && !(start & (PAGE_SIZE - 1)) && map->getLength() == ZORN_SCANOUT_BYTES &&
            start <= UINTPTR_MAX - ZORN_SCANOUT_BYTES) {
            for (size_t off = 0; off < ZORN_SCANOUT_BYTES; off += PAGE_SIZE) {
                if (kvtophys(start + off) != ZORN_SCANOUT_BACK + off) break;
                ++out[VerifiedPages];
            }
            if (out[VerifiedPages] == ZORN_SCANOUT_BYTES / PAGE_SIZE &&
                kvtophys(start + ZORN_SCANOUT_BYTES - 1) == ZORN_SCANOUT_BACK + ZORN_SCANOUT_BYTES - 1)
                out[Status] = ZornScanoutAliasVerified;
        }
        // No byte of the target was read or written, and DPU never had the alias.
        map->release();
    }
    descriptor->release();
}
} // namespace ZornScanoutAlias345
