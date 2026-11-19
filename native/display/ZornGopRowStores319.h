// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornGopRowStores319 {

// The selected K80 GOP target is little-endian and 32-bit pixel aligned.
// Use one aligned write for each complete pair. The caller owns this row and
// publishes stores with the presenter's existing device store barrier.
template <typename Pixel>
void store(volatile uint32_t *destination, uint32_t count, Pixel pixel)
{
    static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__, "GOP pixel byte order");
    uint32_t index = 0;
    if (count && (reinterpret_cast<uintptr_t>(destination) & 4)) {
        destination[0] = pixel(0);
        ++index;
    }
    for (; count - index >= 2; index += 2) {
        const uint64_t low = pixel(index);
        const uint64_t high = pixel(index + 1);
        *reinterpret_cast<volatile uint64_t *>(destination + index) = low | (high << 32);
    }
    if (index < count) destination[index] = pixel(index);
}

} // namespace ZornGopRowStores319
