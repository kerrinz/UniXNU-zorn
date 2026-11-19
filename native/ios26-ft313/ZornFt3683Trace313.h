// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornTouchEdges.h"
#include "ZornTouchTypes.h"

namespace ZornFt3683Trace313 {

enum Field : unsigned {
    Polls, ReadReturned, Decoded, Accepted, ForcedRelease, Downs, Moves, Lifts,
    SeenIds, MaxActive, EdgeDowns, MultiContactSamples, Count
};

// The platform admits one physical worker. Only that worker calls the two
// recording methods. Sampling is nonblocking and observes a complete copy.
class Trace {
public:
    void poll(bool readReturned, const ZornContacts::Frame *decoded, bool accepted)
    {
        ++counters_[Polls];
        counters_[ReadReturned] += readReturned;
        counters_[Decoded] += decoded != nullptr;
        if (decoded && accepted) {
            ++counters_[Accepted];
            recordFrame(*decoded);
        }
        publish();
    }

    void forceRelease()
    {
        // This is a cleanup dispatch, distinct from a sensor-observed lift.
        ++counters_[ForcedRelease];
        previous_ = {};
        publish();
    }

    bool snapshot(uint32_t (&out)[Count]) const
    {
        const auto sequence = __atomic_load_n(&sequence_, __ATOMIC_SEQ_CST);
        if (!sequence || (sequence & 1u)) return false;
        uint32_t copy[Count]{};
        for (unsigned i = 0; i < Count; ++i)
            copy[i] = __atomic_load_n(published_ + i, __ATOMIC_SEQ_CST);
        if (__atomic_load_n(&sequence_, __ATOMIC_SEQ_CST) != sequence) return false;
        for (unsigned i = 0; i < Count; ++i) out[i] = copy[i];
        return true;
    }

private:
    static const ZornContacts::Contact *find(const ZornContacts::Frame &frame, unsigned id)
    {
        for (unsigned i = 0; i < frame.count; ++i)
            if (frame.points[i].id == id) return &frame.points[i];
        return nullptr;
    }

    void recordFrame(const ZornContacts::Frame &frame)
    {
        // The real HID service already validated the complete accepted report.
        counters_[MultiContactSamples] += frame.count > 1;
        if (frame.count > counters_[MaxActive]) counters_[MaxActive] = frame.count;
        for (unsigned i = 0; i < frame.count; ++i) {
            const auto &point = frame.points[i];
            counters_[SeenIds] |= uint32_t(1) << point.id;
            const auto *old = find(previous_, point.id);
            if (old) {
                counters_[Moves] += old->x != point.x || old->y != point.y;
            } else {
                ++counters_[Downs];
                const auto x = uint32_t(point.x) * 65536u / 32767u;
                const auto y = uint32_t(point.y) * 65536u / 32767u;
                counters_[EdgeDowns] += x < ZornEdgePolicy::EdgeX || x > 65536u - ZornEdgePolicy::EdgeX ||
                    y < ZornEdgePolicy::EdgeY || y > 65536u - ZornEdgePolicy::EdgeY;
            }
        }
        for (unsigned i = 0; i < previous_.count; ++i)
            counters_[Lifts] += !find(frame, previous_.points[i].id);
        previous_ = frame;
    }

    void publish()
    {
        __atomic_add_fetch(&sequence_, 1u, __ATOMIC_SEQ_CST);
        for (unsigned i = 0; i < Count; ++i)
            __atomic_store_n(published_ + i, counters_[i], __ATOMIC_SEQ_CST);
        __atomic_add_fetch(&sequence_, 1u, __ATOMIC_SEQ_CST);
    }

    ZornContacts::Frame previous_{};
    uint32_t counters_[Count]{};
    uint32_t sequence_ = 0;
    uint32_t published_[Count]{};
};

}
