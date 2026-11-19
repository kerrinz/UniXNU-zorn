// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornDisplaySmmu336.h"

namespace ZornDisplaySmmuHost337 {

enum Status : uint32_t { NoThreadContext = 6, MissingLock, LockDeadline, TransportUnavailable,
                         MissingMapping, MappingBounds, MappingPhysical };
inline constexpr unsigned LockAttempts = 16;
inline constexpr uint32_t LockDeadlineMs = 100;

// Wait outside the UFS lock. The display lease stays held and its state is
// checked again before publication. There is one critical section and no
// new mapping or UFS command, even if the transport is busy at first.
template <typename TryLock, typename Unlock, typename Delay, typename Now, typename Sample>
void withTransport(TryLock tryLock, Unlock unlock, Delay delay, Now now, Sample sample,
                   uint32_t (&out)[ZornDisplaySmmu336::Words])
{
    using ZornDisplaySmmu336::State;
    const uint32_t started = now();
    for (unsigned attempt = 0; attempt < LockAttempts; ++attempt) {
        if (now() - started >= LockDeadlineMs) break;
        if (tryLock()) {
            sample(out);
            unlock();
            return;
        }
        if (attempt + 1 < LockAttempts) delay(2);
    }
    out[State] = LockDeadline;
}

} // namespace ZornDisplaySmmuHost337
