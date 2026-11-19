// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornRuntimeDisplayFrame341 {

enum State : uint32_t {
    NotRun, NoBaseline, PublicationClosed, NoChangedFrame, FrameClaimed, RouteLost,
};
enum Field : unsigned {
    Status, ArmedUs, Swap, ProducerFence, RetiredFence, Surface, SurfaceFence,
    CopyGeneration, QueuedUs, CopiedUs, ClaimedUs, BaselineSignature, ClaimedSignature,
    Attempts, Words,
};
inline constexpr unsigned WaitMs = 50000;
inline constexpr unsigned MaxAttempts = 2500;

// The exact run has a 300 s watchdog. Reject stamps that cannot fit the
// per-boot CDC clock rather than allowing truncation or inferred ordering.
inline uint32_t wireUs(uint64_t uptimeUs)
{
    return uptimeUs <= UINT32_MAX ? uint32_t(uptimeUs) : 0;
}

inline bool eligible(const uint32_t (&ledger)[16], uint32_t armed, uint32_t queued, uint32_t copied)
{
    return armed && armed <= queued && queued <= copied &&
        ledger[0] == 2 && ledger[1] && ledger[2] && ledger[3] == 2 &&
        ledger[4] && ledger[4] == ledger[5] && ledger[6] && ledger[7] &&
        ledger[8] == 1 && ledger[9] == 1 && ledger[10] == 1 && ledger[12] > ledger[11] &&
        ledger[13] == 1440 && ledger[14] == 3200 &&
        ledger[2] <= ledger[15] && ledger[15] <= ledger[5];
}

// This identifies a changed grid of visible pixels in the validated GOP
// alias. It is a content cross-check for the selected swap, not a panel CRC.
inline uint32_t signature(const volatile uint8_t *gop, uint32_t stride)
{
    uint32_t value = 2166136261u;
    for (unsigned y = 200; y < 3200; y += 400) {
        const auto *row = reinterpret_cast<const volatile uint32_t *>(gop + y * stride);
        for (unsigned x = 90; x < 1440; x += 180) {
            value ^= row[x] & 0x00ffffffu;
            value *= 16777619u;
        }
    }
    return value;
}

inline bool claim(const uint32_t (&ledger)[16], uint32_t queued, uint32_t copied, uint32_t now,
                  uint32_t changedSignature, uint32_t (&out)[Words])
{
    if (!eligible(ledger, out[ArmedUs], queued, copied) ||
        now < copied || now - out[ArmedUs] >= WaitMs * 1000u ||
        changedSignature == out[BaselineSignature]) return false;
    out[Status] = FrameClaimed;
    out[Swap] = ledger[1];
    out[ProducerFence] = ledger[2];
    out[RetiredFence] = ledger[5];
    out[Surface] = ledger[7];
    out[SurfaceFence] = ledger[15];
    out[CopyGeneration] = ledger[12];
    out[QueuedUs] = queued;
    out[CopiedUs] = copied;
    out[ClaimedUs] = now;
    out[ClaimedSignature] = changedSignature;
    return true;
}

} // namespace ZornRuntimeDisplayFrame341
