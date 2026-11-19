// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "GpiSpiTransfer.h"

namespace GpiSpi {

// The SM8650 provider supplies coherent DMA mappings. Channel counts are
// taken from the SPI DMA specifiers, with an event expansion factor of one.
constexpr unsigned ChannelEntries = 64;
constexpr unsigned EventEntries = 128;

struct RingMemory {
    RingElement *cpu;
    uint64_t iova;
};

struct RingSet {
    RingMemory tx;
    RingMemory rx;
    RingMemory event;
};

enum class Queue { Tx, Rx, Event };
enum class Result { Refused, Pending, Completed, Retained };

// One caller serializes this object and owns the already started GPI channels,
// event ring, SPI engine and all DMA mappings. Port supplies coherent DMA
// barriers, checked doorbells, the event producer and live fault/idle reads.
// An ambiguous write or completion poisons the session and leaves ownership
// with the caller until hardware quiescence can be established independently.
class Rings {
    RingSet memory_{};
    uint64_t started_ = 0;
    uint64_t terminal_[2]{};
    uint32_t bytes_ = 0;
    uint32_t timeout_ = 0;
    unsigned txNext_ = 0;
    unsigned rxNext_ = 0;
    unsigned eventNext_ = 0;
    unsigned completed_ = 0;
    enum class State { Unbound, Ready, InFlight, Retained };
    State state_ = State::Unbound;

    static bool valid(const RingMemory &ring, unsigned entries)
    {
        const uintptr_t address = reinterpret_cast<uintptr_t>(ring.cpu);
        const unsigned span = entries * sizeof(RingElement);
        return address && !(address & (alignof(RingElement) - 1)) &&
               address <= UINTPTR_MAX - span && ring.iova && !(ring.iova & (span - 1)) &&
               ring.iova <= UINT64_MAX - span;
    }

    static bool disjoint(const RingMemory &a, unsigned na, const RingMemory &b, unsigned nb)
    {
        const uintptr_t va = reinterpret_cast<uintptr_t>(a.cpu);
        const uintptr_t vb = reinterpret_cast<uintptr_t>(b.cpu);
        const unsigned sa = na * sizeof(RingElement), sb = nb * sizeof(RingElement);
        return (va + sa <= vb || vb + sb <= va) &&
               (a.iova + sa <= b.iova || b.iova + sb <= a.iova);
    }

    static uint64_t address(const RingMemory &ring, unsigned at)
    {
        return ring.iova + at * sizeof(RingElement);
    }

    Result retain()
    {
        state_ = State::Retained;
        return Result::Retained;
    }

public:
    Rings() = default;
    Rings(const Rings &) = delete;
    Rings &operator=(const Rings &) = delete;

    // The event doorbell at bind time must already advertise entries-1.
    // The three fresh read pointers must be at their corresponding ring base.
    bool bindStarted(const RingSet &mem, uint32_t txRead, uint32_t rxRead, uint32_t eventProducer)
    {
        if (state_ != State::Unbound ||
            !valid(mem.tx, ChannelEntries) || !valid(mem.rx, ChannelEntries) ||
            !valid(mem.event, EventEntries) ||
            !disjoint(mem.tx, ChannelEntries, mem.rx, ChannelEntries) ||
            !disjoint(mem.tx, ChannelEntries, mem.event, EventEntries) ||
            !disjoint(mem.rx, ChannelEntries, mem.event, EventEntries) ||
            txRead != uint32_t(mem.tx.iova) || rxRead != uint32_t(mem.rx.iova) ||
            eventProducer != uint32_t(mem.event.iova)) return false;
        memory_ = mem;
        state_ = State::Ready;
        return true;
    }

    template<class Port>
    Result submit(Port &port, uint64_t txIova, uint64_t rxIova, uint32_t bytes,
                  uint32_t clockSource, uint32_t clockDivider, uint32_t timeoutMicros)
    {
        if (state_ == State::Retained) return Result::Retained;
        FullDuplexTransfer command{};
        if (state_ != State::Ready || !timeoutMicros || timeoutMicros > 250000 ||
            !prepareMode0(txIova, rxIova, bytes, clockSource, clockDivider, command)) {
            return Result::Refused;
        }
        uint32_t producer = 0;
        if (!port.healthy() || !port.eventProducer(producer) ||
            producer != uint32_t(address(memory_.event, eventNext_))) return retain();

        for (const auto &entry : command.tx) {
            memory_.tx.cpu[txNext_] = entry;
            terminal_[Tx] = address(memory_.tx, txNext_);
            txNext_ = (txNext_ + 1) & (ChannelEntries - 1);
        }
        memory_.rx.cpu[rxNext_] = command.rx;
        terminal_[Rx] = address(memory_.rx, rxNext_);
        rxNext_ = (rxNext_ + 1) & (ChannelEntries - 1);

        completed_ = 0;
        bytes_ = bytes;
        timeout_ = timeoutMicros;
        started_ = port.nowMicros();
        state_ = State::InFlight;
        port.publish();
        // Both descriptor chains are published before ringing either channel.
        // Match the vendor SPI submission order, TX followed by linked RX.
        if (!port.ring(Queue::Tx, uint32_t(address(memory_.tx, txNext_))) ||
            !port.ring(Queue::Rx, uint32_t(address(memory_.rx, rxNext_)))) return retain();
        return Result::Pending;
    }

    template<class Port>
    Result poll(Port &port)
    {
        if (state_ == State::Retained) return Result::Retained;
        if (state_ != State::InFlight) return Result::Refused;
        uint32_t producer = 0;
        if (port.nowMicros() - started_ >= timeout_ || !port.healthy() ||
            !port.eventProducer(producer)) return retain();

        const uint32_t offset = producer - uint32_t(memory_.event.iova);
        if (offset >= EventEntries * sizeof(RingElement) || offset % sizeof(RingElement)) return retain();
        const unsigned stop = offset / sizeof(RingElement);
        if (stop != eventNext_) {
            port.acquire();
            do {
                const auto &entry = static_cast<volatile RingElement *>(memory_.event.cpu)[eventNext_];
                const RingElement event{{entry.words[0], entry.words[1], entry.words[2], entry.words[3]}};
                const unsigned channel = event.words[3] >> 24;
                if (channel > Rx || (completed_ & (1u << channel)) ||
                    !completes(event, Channel(channel), terminal_[channel], bytes_)) return retain();
                completed_ |= 1u << channel;
                eventNext_ = (eventNext_ + 1) & (EventEntries - 1);
            } while (eventNext_ != stop);

            // Keep one advertised element between the producer and consumer.
            const unsigned recycled = (eventNext_ + EventEntries - 1) & (EventEntries - 1);
            port.publish();
            if (!port.ring(Queue::Event, uint32_t(address(memory_.event, recycled))) ||
                !port.ackEvents()) return retain();
        }
        if (completed_ != 3 || !port.serialIdle()) return Result::Pending;
        port.acquire();
        state_ = State::Ready;
        return Result::Completed;
    }

    // An orderly stop still needs the board owner to stop and deallocate the
    // hardware contexts. This query only says there is no outstanding transfer.
    bool readyForOrderlyStop() const { return state_ == State::Ready; }
};

} // namespace GpiSpi
