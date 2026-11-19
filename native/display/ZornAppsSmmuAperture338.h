// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornDisplaySmmuHost337.h"

namespace ZornAppsSmmuAperture338 {

inline constexpr uint64_t PhysicalBase = 0x15000000;
inline constexpr uint32_t ApertureBytes = 0xd0000;
inline constexpr uint32_t Unpublished = 13;

// The UFS initializer publishes once, before root registration starts I/O.
// Its caller must retain the real mapping before committing the virtual base.
// Publication never lends the mutable UFS command state to the display path.
class Publication {
    uintptr_t address_ = 0;
    uint32_t status_ = 0;

public:
    bool begin()
    {
        uint32_t expected = 0;
        return __atomic_compare_exchange_n(&status_, &expected, Unpublished, false,
                                          __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE);
    }

    void finish(uint32_t status, uintptr_t base = 0)
    {
        address_ = base;
        __atomic_store_n(&status_, status, __ATOMIC_RELEASE);
    }

    uint32_t snapshot(uintptr_t &base) const
    {
        const uint32_t status = __atomic_load_n(&status_, __ATOMIC_ACQUIRE);
        base = status == ZornDisplaySmmu336::Observed ? address_ : 0;
        return status ? status : Unpublished;
    }
};

} // namespace ZornAppsSmmuAperture338
