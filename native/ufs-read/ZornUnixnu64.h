// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stdint.h>
// Exact partition created and read back on 2026-11-01. This descriptor check
// grants no controller ownership; the original UFS/GPT/lock checks still apply.
static constexpr uint64_t kZornUnixnuFirst = 47271680;
static constexpr uint64_t kZornUnixnuLast = 64048895;
static inline uint64_t zornUnixnuLe64(const uint8_t *p)
{
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) value |= uint64_t(p[i]) << (i * 8);
    return value;
}
static inline const uint8_t *zornUnixnu64Entry(const uint8_t *entries,
    uint32_t count, uint32_t size)
{
    if (!entries || !count || count > 256 || size != 128) return nullptr;
    const uint8_t type[16] = {0xaf,0x3d,0xc6,0x0f,0x83,0x84,0x72,0x47,
        0x8e,0x79,0x3d,0x69,0xd8,0x47,0x7d,0xe4};
    const uint8_t guid[16] = {0x1f,0x73,0x79,0xb2,0xad,0xcc,0xf5,0x4e,
        0xa8,0xb7,0xe7,0x44,0x0c,0xd0,0x8d,0xe3};
    const char name[] = "unixnu";
    const uint8_t *found = nullptr;
    for (uint32_t index = 0; index < count; ++index) {
        const uint8_t *entry = entries + index * size;
        bool match = true;
        for (unsigned i = 0; i < sizeof(name); ++i)
            if (entry[56 + 2*i] != uint8_t(name[i]) || entry[57 + 2*i]) match = false;
        if (!match) continue;
        // Reject ambiguous names even if one has the expected identity.
        if (found) return nullptr;
        for (unsigned i = 0; i < 16; ++i)
            if (entry[i] != type[i] || entry[16+i] != guid[i]) return nullptr;
        if (zornUnixnuLe64(entry + 32) != kZornUnixnuFirst ||
            zornUnixnuLe64(entry + 40) != kZornUnixnuLast ||
            zornUnixnuLe64(entry + 48) != 0) return nullptr;
        found = entry;
    }
    return found;
}
