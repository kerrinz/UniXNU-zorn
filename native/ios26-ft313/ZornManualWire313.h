// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornUiSceneWire269.h"

namespace ZornManualWire313 {
constexpr unsigned Samples = 9;
constexpr unsigned PresentWords = 160;
constexpr unsigned TouchWords = 12;
constexpr unsigned Words = PresentWords + Samples * (1 + TouchWords);
constexpr unsigned Bytes = 32 + 4 * Words;

inline unsigned packet(char *out, unsigned cap, const uint32_t (&values)[Words],
                       const uint8_t (&tag)[16])
{
    if (!out || cap < Bytes) return 0;
    auto *p = reinterpret_cast<uint8_t *>(out);
    memcpy(p, "K80FT313", 8);
    memcpy(p + 8, tag, 16);
    for (unsigned i = 0; i < Words; ++i) zorn_panic_le236(p, 24 + 4 * i, values[i]);
    zorn_panic_le236(p, Bytes - 8, zorn_panic_crc236(p, Bytes - 8));
    zorn_panic_le236(p, Bytes - 4, 313);
    return Bytes;
}
}
