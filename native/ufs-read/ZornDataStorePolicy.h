// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
// K80-specific allocation, independently checked against both live GPT copies.
// Blocks are 4096 bytes. The existing OS/SystemOS image and log are below it.
#include <stdint.h>
static constexpr uint64_t kZornDataPartitionFirst = 3112704;
static constexpr uint64_t kZornDataPartitionLast = 64049146;
static constexpr uint64_t kZornDataRelativeFirst = 2621440; // 10 GiB
static constexpr uint64_t kZornDataPages = 131072;
static constexpr uint64_t kZornDataWindowBlocks = 131077; // header + 4 bitmap + 512 MiB
static constexpr uint64_t kZornDataFirst = kZornDataPartitionFirst + kZornDataRelativeFirst;
static inline bool zornDataGeometry(uint64_t first, uint64_t last, uint64_t imageBytes, uint64_t logLba)
{
    return first == kZornDataPartitionFirst && last == kZornDataPartitionLast &&
        imageBytes == 9382658048ULL && logLba == first + 2291712 &&
        kZornDataFirst > logLba && kZornDataRelativeFirst * 4096 >= imageBytes + 8 * 1024 * 1024 &&
        kZornDataFirst + kZornDataWindowBlocks <= last + 1;
}
static inline bool zornDataRange(uint64_t offset, uint32_t blocks)
{
    return blocks && blocks <= 32 && offset < kZornDataWindowBlocks &&
        blocks <= kZornDataWindowBlocks - offset;
}
static inline bool zornDataCommandAllowed(const uint8_t *u, unsigned n, unsigned direction,
    uint32_t bytes, unsigned mode, bool opened)
{
    if (!opened || mode != 2 || !u || n < 32 || u[0] != 1 || u[2] || u[3] ||
        u[8] || u[10] || u[11]) return false;
    for (unsigned i = 4; i < 12; ++i) if (u[i]) return false;
    const uint8_t *c = u + 16;
    for (unsigned i = 10; i < 16; ++i) if (c[i]) return false;
    uint32_t length = (uint32_t(u[12]) << 24) | (uint32_t(u[13]) << 16) | (uint32_t(u[14]) << 8) | u[15];
    if (length != bytes) return false;
    if (c[0] == 0x35) { // Real SYNCHRONIZE CACHE completion; no data payload.
        if (direction || bytes || u[1]) return false;
        for (unsigned i = 1; i < 10; ++i) if (c[i]) return false;
        return true;
    }
    if (direction != 1 || u[1] != 0x20 || c[0] != 0x2a || c[1] != 8 || c[6] || c[9]) return false;
    uint64_t lba = (uint32_t(c[2]) << 24) | (uint32_t(c[3]) << 16) | (uint32_t(c[4]) << 8) | c[5];
    uint32_t blocks = (uint32_t(c[7]) << 8) | c[8];
    return lba >= kZornDataFirst && zornDataRange(lba - kZornDataFirst, blocks) && bytes == blocks * 4096U;
}
