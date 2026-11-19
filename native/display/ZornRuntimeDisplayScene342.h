// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornRuntimeDisplayFrame341.h"

namespace ZornRuntimeDisplayScene342 {

enum State : uint32_t { NotRun, ReadinessDeadline, ServiceFailure, GestureFailed, GestureComplete };
enum Field : unsigned {
    Status, StartMs, EndMs, ContactAttempts, ContactReturns, FirstRaw, LiftRaw,
    GopUnavailable, OutdatedCopy, InvalidLedger, SameSignature, ClaimExpired,
    ReadinessChecks, LastSwap, GestureOutcome, Words,
};
inline constexpr unsigned ObservationMs = 85000;
inline constexpr unsigned GestureReadyMs = 6000;
inline constexpr unsigned GestureBudgetMs = 8000;
inline constexpr unsigned MinClaimWindowMs = 2000;

inline bool hasTime(uint64_t now, uint64_t deadline, uint64_t required)
{
    return now < deadline && deadline - now >= required;
}

inline Field classify(const uint32_t (&ledger)[16], uint32_t armed, uint32_t queued, uint32_t copied)
{
    if (!armed || queued < armed || copied < queued) return OutdatedCopy;
    return ZornRuntimeDisplayFrame341::eligible(ledger, armed, queued, copied) ? Words : InvalidLedger;
}

} // namespace ZornRuntimeDisplayScene342
