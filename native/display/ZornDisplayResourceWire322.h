// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornDisplayResources322 {

inline constexpr unsigned BcmCount = 3;
inline constexpr unsigned ArcCount = 3;
inline constexpr unsigned BcmWords = 5;
inline constexpr unsigned ArcWords = 12;
inline constexpr unsigned MaxArcLevels = 16;
inline constexpr unsigned ArcStart = BcmCount * BcmWords;
inline constexpr unsigned Words = ArcStart + ArcCount * ArcWords;

enum Resolution : uint32_t { Missing = 1, Available, Invalid };

} // namespace ZornDisplayResources322
