// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornDisplayResourceWire322.h"
#include "ZornGen7CommandDbResourceReader.h"

namespace ZornDisplayResources322 {

// K80's qcom,sde-reg-bus path and Pineapple DISPCC supplies. MMCX's
// pm_v8_s1_level also has a consumer of CX as its parent supply.
inline constexpr uint8_t BcmIds[][8] = {{'S','H','1'}, {'C','N','0'}, {'C','N','1'}};
inline constexpr uint8_t ArcIds[][8] = {
    {'c','x','.','l','v','l'}, {'m','m','c','x','.','l','v','l'}, {'m','x','.','l','v','l'}
};
static_assert(BcmCount == sizeof(BcmIds) / sizeof(BcmIds[0]));
static_assert(ArcCount == sizeof(ArcIds) / sizeof(ArcIds[0]));

inline bool hasUniqueAddress(const ZornGen7Rpmh::CommandDbResource &resource)
{
    return resource.matchingEntries == 1 && resource.address && !(resource.address & 3);
}

inline uint32_t littleEndianWord(const uint8_t *bytes)
{
    return uint32_t(bytes[0]) | uint32_t(bytes[1]) << 8 | uint32_t(bytes[2]) << 16 |
           uint32_t(bytes[3]) << 24;
}

inline void bcm(ZornGen7Rpmh::NativeCommandDbResourceReader &reader, const uint8_t (&id)[8], uint32_t *out)
{
    ZornGen7Rpmh::CommandDbResource info{};
    uint8_t aux[8]{};
    const auto result = reader.copyActualAuxPrefix(id, info, aux, sizeof(aux), sizeof(aux));
    if (result != ZornGen7Rpmh::CommandDbReadStatus::Available) {
        out[0] = result == ZornGen7Rpmh::CommandDbReadStatus::Missing ? Missing : Invalid;
        return;
    }
    if (!hasUniqueAddress(info) || info.auxBytes < sizeof(aux)) {
        out[0] = Invalid;
        return;
    }
    out[0] = Available;
    out[1] = info.address;
    out[2] = info.auxBytes;
    out[3] = littleEndianWord(aux);
    out[4] = littleEndianWord(aux + 4); // Raw width, VCD, reserved.
}

inline void arc(ZornGen7Rpmh::NativeCommandDbResourceReader &reader, const uint8_t (&id)[8], uint32_t *out)
{
    ZornGen7Rpmh::CommandDbResource info{};
    uint8_t aux[2 * MaxArcLevels]{};
    const auto result = reader.copyActualResource(id, info, aux, sizeof(aux));
    if (result != ZornGen7Rpmh::CommandDbReadStatus::Available) {
        out[0] = result == ZornGen7Rpmh::CommandDbReadStatus::Missing ? Missing : Invalid;
        return;
    }
    if (!hasUniqueAddress(info) || !info.auxBytes || info.auxBytes > sizeof(aux) || (info.auxBytes & 1)) {
        out[0] = Invalid;
        return;
    }
    unsigned count = info.auxBytes / 2;
    uint16_t levels[MaxArcLevels]{};
    // Match rpmh_regulator_load_arc_level_mapping: after index zero,
    // a zero level denotes padding. The rest is not a voltage vote.
    for (unsigned i = 0; i < count; ++i) {
        const auto level = uint16_t(aux[2 * i] | uint16_t(aux[2 * i + 1]) << 8);
        if (i && !level) {
            count = i;
            break;
        }
        if (i && level < levels[i - 1]) {
            out[0] = Invalid;
            return;
        }
        levels[i] = level;
    }
    out[0] = Available;
    out[1] = info.address;
    out[2] = info.auxBytes;
    out[3] = count;
    for (unsigned i = 0; i < MaxArcLevels / 2; ++i)
        out[4 + i] = levels[2 * i] | uint32_t(levels[2 * i + 1]) << 16;
}

inline void resolve(ZornGen7Rpmh::NativeCommandDbResourceReader &reader, uint32_t (&out)[Words])
{
    for (auto &word : out) word = 0;
    for (unsigned i = 0; i < BcmCount; ++i) bcm(reader, BcmIds[i], out + BcmWords * i);
    for (unsigned i = 0; i < ArcCount; ++i) arc(reader, ArcIds[i], out + ArcStart + ArcWords * i);
}

} // namespace ZornDisplayResources322
