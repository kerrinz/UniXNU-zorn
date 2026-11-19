// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stdint.h>

namespace ZornGopWriterEpoch343 {

struct Frame {
    uint32_t epoch = 0;
    uint32_t swap = 0;
    uint32_t producerFence = 0;
    uint32_t generation = 0;
    uint32_t signature = 0;
    uint32_t copiedUs = 0;

    bool qualified() const
    {
        return epoch && !(epoch & 1u) && swap && producerFence && generation && copiedUs;
    }
};

// Writes are serialized by the real GOP writer lock. The poller does not acquire
// it, so validation does not stall the compositor or alter the scanout cadence.
class Ownership {
public:
    // Call while holding the writer lock, before the first GOP store. Complete
    // only after the stores' device barrier and the matching GPU ledger.
    void begin()
    {
        __atomic_fetch_add(&epoch_, 1u, __ATOMIC_SEQ_CST);
    }

    void finish(const Frame &stamp)
    {
        __atomic_store_n(&swap_, stamp.swap, __ATOMIC_SEQ_CST);
        __atomic_store_n(&fence_, stamp.producerFence, __ATOMIC_SEQ_CST);
        __atomic_store_n(&generation_, stamp.generation, __ATOMIC_SEQ_CST);
        __atomic_store_n(&signature_, stamp.signature, __ATOMIC_SEQ_CST);
        __atomic_store_n(&copiedUs_, stamp.copiedUs, __ATOMIC_SEQ_CST);
        __atomic_fetch_add(&epoch_, 1u, __ATOMIC_SEQ_CST);
    }

    Frame poll() const
    {
        const auto epoch = __atomic_load_n(&epoch_, __ATOMIC_SEQ_CST);
        if (!epoch || (epoch & 1u)) return {};
        Frame snapshot{
            epoch,
            __atomic_load_n(&swap_, __ATOMIC_SEQ_CST),
            __atomic_load_n(&fence_, __ATOMIC_SEQ_CST),
            __atomic_load_n(&generation_, __ATOMIC_SEQ_CST),
            __atomic_load_n(&signature_, __ATOMIC_SEQ_CST),
            __atomic_load_n(&copiedUs_, __ATOMIC_SEQ_CST),
        };
        if (__atomic_load_n(&epoch_, __ATOMIC_SEQ_CST) != epoch) return {};
        return snapshot;
    }

private:
    uint32_t epoch_ = 0, swap_ = 0, fence_ = 0, generation_ = 0, signature_ = 0, copiedUs_ = 0;
};

} // namespace ZornGopWriterEpoch343
