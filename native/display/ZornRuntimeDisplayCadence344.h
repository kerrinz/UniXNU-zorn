// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornRuntimeDisplayCadence343.h"

namespace ZornRuntimeDisplayCadence344 {

namespace Base = ZornRuntimeDisplayCadence343;
using namespace ZornRuntimeDisplayCadence343;

enum Extra : unsigned {
    LogicalGeometry = Base::Words, QualifiedCopies, RejectedCopies, RejectionMask,
    AutoRefreshConfig, CopyToDsiSamples, CopyToDsiMinUs, CopyToDsiMaxUs,
    CopyToDsiSumLo, CopyToDsiSumHi, Words,
};

enum Rejection : uint32_t {
    PanelAlias = 1u << 0,
    LogicalExtent = 1u << 1,
    CopyTimestamp = 1u << 2,
    GpuLedger = 1u << 3,
    CopyLedger = 1u << 4,
    SurfaceFence = 1u << 5,
};

inline uint32_t reject(const uint32_t (&ledger)[16], bool checkedPanelAlias,
                       uint32_t logicalWidth, uint32_t logicalHeight,
                       uint32_t queuedUs, uint32_t copiedUs)
{
    uint32_t reason = checkedPanelAlias ? 0u : uint32_t(PanelAlias);
    // These ledger values describe the logical composition, which show()
    // scales into the separately validated physical framebuffer.
    if (!logicalWidth || !logicalHeight || logicalWidth > 16384 || logicalHeight > 16384 ||
        ledger[13] != logicalWidth || ledger[14] != logicalHeight) reason |= LogicalExtent;
    if (!queuedUs || queuedUs > copiedUs) reason |= CopyTimestamp;
    if (ledger[0] != 2 || !ledger[1] || !ledger[2] || ledger[3] != 2 ||
        !ledger[4] || ledger[4] != ledger[5] || ledger[8] != 1 || ledger[10] != 1) reason |= GpuLedger;
    if (ledger[9] != 1 || ledger[12] <= ledger[11]) reason |= CopyLedger;
    if (!ledger[6] || !ledger[7] || ledger[15] < ledger[2] || ledger[15] > ledger[5])
        reason |= SurfaceFence;
    return reason;
}

class CopyToDsi {
public:
    void add(uint32_t copiedUs, uint64_t observedUs)
    {
        if (!copiedUs || observedUs < copiedUs || observedUs - copiedUs > UINT32_MAX) return;
        const auto elapsed = uint32_t(observedUs - copiedUs);
        if (!samples_ || elapsed < minimum_) minimum_ = elapsed;
        if (elapsed > maximum_) maximum_ = elapsed;
        sum_ += elapsed;
        ++samples_;
    }

    void record(uint32_t (&out)[Words]) const
    {
        out[CopyToDsiSamples] = samples_;
        out[CopyToDsiMinUs] = minimum_;
        out[CopyToDsiMaxUs] = maximum_;
        out[CopyToDsiSumLo] = uint32_t(sum_);
        out[CopyToDsiSumHi] = uint32_t(sum_ >> 32);
    }

private:
    uint64_t sum_ = 0;
    uint32_t samples_ = 0, minimum_ = 0, maximum_ = 0;
};

} // namespace ZornRuntimeDisplayCadence344
