/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_SCANOUT_HANDOFF_345_H
#define ZORN_SCANOUT_HANDOFF_345_H

#include <stddef.h>
#include <stdint.h>

#define ZORN_SCANOUT_PROPERTY "zorn,scanout-reservation"
#define ZORN_SCANOUT_MAGIC UINT32_C(0x3146535a) /* ZSF1 */
#define ZORN_SCANOUT_FRONT UINT64_C(0xfc400000)
#define ZORN_SCANOUT_BACK  UINT64_C(0xfd800000)
#define ZORN_SCANOUT_END   UINT64_C(0xfef00000)
#define ZORN_SCANOUT_WIDTH 1440
#define ZORN_SCANOUT_HEIGHT 3200
#define ZORN_SCANOUT_STRIDE (ZORN_SCANOUT_WIDTH * 4)
#define ZORN_SCANOUT_BYTES (ZORN_SCANOUT_STRIDE * ZORN_SCANOUT_HEIGHT)
#define ZORN_SCANOUT_WORDS 8

enum ZornScanoutFirmwareStatus {
    ZornScanoutNoWitness,
    ZornScanoutWrongGop,
    ZornScanoutXnuOverlap,
    ZornScanoutGcdUnavailable,
    ZornScanoutGcdConflict,
    ZornScanoutEfiMapInvalid,
    ZornScanoutEfiMapConflict,
    ZornScanoutEfiMapUncovered,
    ZornScanoutReserved,
};

enum ZornScanoutKernelStatus {
    ZornScanoutNotChecked,
    ZornScanoutPropertyMissing,
    ZornScanoutPropertyInvalid,
    ZornScanoutFirmwareDenied,
    ZornScanoutKernelGeometryMismatch,
    ZornScanoutDescriptorFailed,
    ZornScanoutMappingFailed,
    ZornScanoutWrongAlias,
    ZornScanoutAliasVerified,
};

static inline int zorn_scanout_span(uint64_t base, uint64_t length)
{
    return length && length <= UINT64_MAX - base;
}

static inline int zorn_scanout_matches_window(uint64_t base, uint64_t length)
{
    const uint64_t end = ZORN_SCANOUT_BACK + ZORN_SCANOUT_BYTES;
    return zorn_scanout_span(base, length) &&
        (base >= end || base + length <= ZORN_SCANOUT_FRONT);
}

static inline uint32_t zorn_scanout_load(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8) |
        ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);
}

static inline void zorn_scanout_write(uint8_t *data, unsigned word, uint32_t value)
{
    for (unsigned i = 0; i != 4; ++i)
        data[word * 4 + i] = (uint8_t)(value >> (i * 8));
}

static inline void zorn_scanout_record(uint8_t *data, enum ZornScanoutFirmwareStatus status)
{
    zorn_scanout_write(data, 0, ZORN_SCANOUT_MAGIC);
    zorn_scanout_write(data, 1, (uint32_t)status);
    const int reserved = status == ZornScanoutReserved;
    zorn_scanout_write(data, 2, reserved ? ZORN_SCANOUT_FRONT : 0);
    zorn_scanout_write(data, 3, reserved ? ZORN_SCANOUT_BACK : 0);
    zorn_scanout_write(data, 4, reserved ? ZORN_SCANOUT_BYTES : 0);
    zorn_scanout_write(data, 5, reserved ? ZORN_SCANOUT_STRIDE : 0);
    zorn_scanout_write(data, 6, reserved ? ZORN_SCANOUT_WIDTH : 0);
    zorn_scanout_write(data, 7, reserved ? ZORN_SCANOUT_HEIGHT : 0);
}

static inline int zorn_scanout_decode(const void *property, size_t size,
                                      enum ZornScanoutFirmwareStatus *status)
{
    if (!property || size != ZORN_SCANOUT_WORDS * 4) return 0;
    const uint8_t *data = (const uint8_t *)property;
    const uint32_t raw = zorn_scanout_load(data + 4);
    if (zorn_scanout_load(data) != ZORN_SCANOUT_MAGIC || !raw || raw > ZornScanoutReserved)
        return 0;
    uint8_t expected[ZORN_SCANOUT_WORDS * 4];
    zorn_scanout_record(expected, (enum ZornScanoutFirmwareStatus)raw);
    for (unsigned i = 0; i != sizeof(expected); ++i) {
        if (data[i] != expected[i]) return 0;
    }
    *status = (enum ZornScanoutFirmwareStatus)raw;
    return 1;
}

#ifdef __cplusplus
namespace ZornScanoutAlias345 {
enum Field : unsigned { Status, FirmwareStatus, PageBytes, VerifiedPages, PhysicalBase, Extent, Words };
}
#endif

#endif
