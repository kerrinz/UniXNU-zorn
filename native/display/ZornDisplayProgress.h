// SPDX-License-Identifier: BSD-2-Clause-Patent
// Opt-in measurement helpers only. No I/O, queue, clock or driver calls.
#ifndef ZORN_DISPLAY_PROGRESS_H
#define ZORN_DISPLAY_PROGRESS_H
#include <stdint.h>

namespace ZornDisplayProgress {
enum : unsigned { Retired = 0, Armed, Sent, Idle, Late, Started, Properties, Events };
static constexpr unsigned Words = 16;
static constexpr unsigned SnapshotMs = 14, Unknown = 15;
// Low halves are original unsigned values. Refuse the overlay if ANY original
// high half is nonzero, including an unexpectedly large transfer byte count.
static constexpr unsigned Slots[Words] = {0,1,2,3,4,6,7,9,10,11,13,14,25,27,30,31};

struct alignas(64) State {
    uint64_t count[Events] = {};
    uint64_t publishedMs[Events] = {};
    uint64_t unknown = 0;
};
static_assert(Events == 7 && Words == Events * 2 + 2, "display progress layout");
static_assert(__atomic_always_lock_free(sizeof(uint64_t), nullptr), "64-bit lock-free counters required");

// ms is the caller's monotonic uptime in milliseconds. Individual words use
// relaxed atomics; counts and times are NOT an atomic pair. A delayed writer
// can publish an older time, so it is a last-published value, not an exact
// chronological maximum. Counter changes establish observed callback progress.
static inline void observe(State &state, unsigned event, uint64_t ms) {
    if (event >= Events) {
        __atomic_fetch_add(&state.unknown, uint64_t(1), __ATOMIC_RELAXED);
        return;
    }
    __atomic_fetch_add(&state.count[event], uint64_t(1), __ATOMIC_RELAXED);
    __atomic_store_n(&state.publishedMs[event], ms, __ATOMIC_RELAXED);
}
// Existing backend event numbers are 0 armed,1 sent,2 idle,3 late,4 started,
// 5 refresh properties. "Sent" observes the sender callback, not receipt.
static inline void vsync(State &state, unsigned backendEvent, uint64_t ms) {
    observe(state, backendEvent <= 5 ? backendEvent + Armed : Events, ms);
}
static inline void snapshot(const State &state, uint64_t nowMs, uint64_t out[Words]) {
    for (unsigned i = 0; i < Events; ++i) {
        out[i*2] = __atomic_load_n(&state.count[i], __ATOMIC_RELAXED);
        out[i*2+1] = __atomic_load_n(&state.publishedMs[i], __ATOMIC_RELAXED);
    }
    out[SnapshotMs] = nowMs;
    out[Unknown] = __atomic_load_n(&state.unknown, __ATOMIC_RELAXED);
}
// Transactional local encoding: all preconditions are checked before the
// caller's snapshot is touched. Never truncate an original or a new value.
static inline bool encode(uint64_t display[32], const uint64_t values[Words]) {
    for (unsigned i = 0; i < Words; ++i)
        if ((display[Slots[i]] >> 32) || (values[i] >> 32)) return false;
    for (unsigned i = 0; i < Words; ++i)
        display[Slots[i]] |= values[i] << 32;
    return true;
}
}
extern "C" void zorn_display_progress_configure(unsigned enabled);
extern "C" int zorn_display_progress_overlay(uint64_t display[32]);
#endif
