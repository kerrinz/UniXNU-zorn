/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuGmuHfiStatus.h"
#include <stddef.h>

int
ZGClassifyGmuHfiStatus(uint32_t raw, uint32_t supplied_software_mask,
                       ZGGmuHfiStatus *out)
{
    if (!out || (uintptr_t)out % _Alignof(ZGGmuHfiStatus) ||
        (uintptr_t)out > UINTPTR_MAX - (sizeof(*out) - 1))
        return ZGHFI_STATUS_INVALID;

    const uint32_t msgq = UINT32_C(1), dbgq = UINT32_C(4);
    const uint32_t cm3 = UINT32_C(0x8000);
    /* Exact oob_max=8 source: GENMASK(31-(8-1),0) keeps bit24.
     * Header HFI_IRQ_OOB_MASK=0xffff0000 is a different mask. */
    const uint32_t ignored = UINT32_C(0xfe000000);
    const uint32_t inline_msgq = (supplied_software_mask & msgq) ? 0 : raw & msgq;
    const uint32_t effective = raw & ~inline_msgq;
    ZGGmuHfiStatus value = {
        raw, supplied_software_mask, effective, inline_msgq,
        effective & (msgq | dbgq), effective & cm3,
        effective & ignored, (effective & ~ignored) & ~supplied_software_mask,
        raw & ~(msgq | dbgq | cm3)
    };
    *out = value;
    return ZGHFI_STATUS_OK;
}
