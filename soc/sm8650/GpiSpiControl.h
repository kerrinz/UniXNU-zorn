// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "GpiSpiRings.h"

namespace GpiSpi {

// Relative to the board's published GPII channel-context page. The board
// owner retains the MMIO window, clocks, GIC claim, streams and ring pages.
namespace ControlRegisters {
constexpr uint32_t TxContext = 0, RxContext = 0x80, EventContext = 0x1000;
constexpr uint32_t Length = 4, BaseLow = 8, BaseHigh = 12, ReadLow = 16;
constexpr uint32_t EventModeration = 0x20, MsiLow = 0x28, MsiHigh = 0x2c;
constexpr uint32_t EventUpdateLow = 0x30, EventUpdateHigh = 0x34, Qos = 0x5c, Scratch = 0x60;
constexpr uint32_t TxDoorbell = 0x2000, RxDoorbell = 0x2008, EventDoorbell = 0x2100;
constexpr uint32_t ChannelCommand = 0x3008, EventCommand = 0x3010;
constexpr uint32_t ChannelPending = 0x3090, EventPending = 0x3094;
constexpr uint32_t ChannelClear = 0x30a0, EventClear = 0x30a4;
constexpr uint32_t StateMask = 0xfu << 20;
}

class Control {
public:
    enum class Command : uint32_t { Allocate = 0, Start = 1, Stop = 2, ResetStopped = 9, Deallocate = 10 };

private:
    enum class State : uint32_t { Free = 0, Allocated = 1, Started = 2, Stopped = 3 };
    static constexpr unsigned Channels = 3, Event = 4;
    unsigned owned_ = 0, prepared_ = 0, started_ = 0, stopped_ = 0, reset_ = 0;
    unsigned engine_ = 0;
    RingMemory memory_[3]{};
    bool used_ = false;
    bool retained_ = false;
    bool released_ = false;
    bool bound_ = false;

    Result refuse()
    {
        if (!used_) return Result::Refused;
        retained_ = true;
        return Result::Retained;
    }

    static unsigned index(Queue queue)
    {
        return queue == Queue::Tx ? 0 : queue == Queue::Rx ? 1 : queue == Queue::Event ? 2 : 3;
    }

    static bool overlap(uint64_t a, uint64_t b, unsigned aBytes, unsigned bBytes)
    {
        return a < b + bBytes && b < a + aBytes;
    }

    bool transition(unsigned bit, Command command, State &from, State &to) const
    {
        switch (command) {
        case Command::Allocate:
            from = State::Free;
            to = State::Allocated;
            return !(owned_ & bit) && (bit == Event || (owned_ & Event));
        case Command::Start:
            from = State::Allocated;
            to = State::Started;
            return bit != Event && prepared_ == (Channels | Event) && !(started_ & bit) && !stopped_;
        case Command::Stop:
            from = State::Started;
            to = State::Stopped;
            return bit != Event && started_ == Channels && !(stopped_ & bit);
        case Command::ResetStopped:
            from = State::Stopped;
            to = State::Allocated;
            return bit != Event && stopped_ == Channels && !(reset_ & bit);
        case Command::Deallocate:
            from = State::Allocated;
            to = State::Free;
            return (owned_ & bit) && reset_ == Channels && (bit != Event || owned_ == Event);
        }
        return false;
    }

    void completed(unsigned bit, Command command)
    {
        switch (command) {
        case Command::Allocate: owned_ |= bit; break;
        case Command::Start: started_ |= bit; break;
        case Command::Stop: stopped_ |= bit; break;
        case Command::ResetStopped: reset_ |= bit; break;
        case Command::Deallocate:
            owned_ &= ~bit;
            released_ = !owned_;
            break;
        }
    }

public:
    Control() = default;
    Control(const Control &) = delete;
    Control &operator=(const Control &) = delete;

    // Command refusal by itself carries no memory-release authority.
    bool canReleaseMemory() const { return !used_ || released_; }
    bool acceptsTransfers() const { return bound_ && !retained_ && !stopped_ && !released_; }

    // Each context is allocated before its registers are programmed. Ring
    // addresses, cache publication and doorbell writes are on the same port.
    // The port checks the live lease on each MMIO write.
    template<class Port>
    Result configure(Port &port, Queue queue, const RingMemory &ring, unsigned engine)
    {
        using namespace ControlRegisters;
        if (retained_) return Result::Retained;
        const unsigned slot = index(queue);
        if (released_ || slot == 3 || engine > 7) return Result::Refused;
        const unsigned bit = 1u << slot;
        const bool event = bit == Event;
        if (!(owned_ & bit) || (prepared_ & bit) || started_ || (!event && !(prepared_ & Event)) ||
            (prepared_ && engine != engine_)) return Result::Refused;
        const unsigned length = (event ? EventEntries : ChannelEntries) * sizeof(RingElement);
        const auto cpu = reinterpret_cast<uintptr_t>(ring.cpu);
        if (!cpu || cpu % alignof(RingElement) || cpu > UINTPTR_MAX - length || !ring.iova ||
            ring.iova % length || ring.iova > UINT64_MAX - length) return Result::Refused;
        for (unsigned other = 0; other < 3; ++other) {
            if (!(prepared_ & (1u << other))) continue;
            const auto &saved = memory_[other];
            const unsigned bytes = (other == 2 ? EventEntries : ChannelEntries) * sizeof(RingElement);
            if (overlap(cpu, reinterpret_cast<uintptr_t>(saved.cpu), length, bytes) ||
                overlap(ring.iova, saved.iova, length, bytes)) return Result::Refused;
        }
        constexpr uint32_t contextBySlot[] = {TxContext, RxContext, EventContext};
        constexpr uint32_t bellBySlot[] = {TxDoorbell, RxDoorbell, EventDoorbell};
        const uint32_t ctx = contextBySlot[slot], bell = bellBySlot[slot];
        const uint32_t config = (sizeof(RingElement) << 24) | 2u |
                                (event ? 1u << 16 : queue == Queue::Tx ? 1u << 3 : 0u);
        const uint32_t high = uint32_t(ring.iova >> 32);
        uint32_t readback = 0;
        if (!port.healthy() || !port.serialIdle() || !port.read(ctx, readback) ||
            (readback & StateMask) != (1u << 20)) return refuse();
        const auto writeChecked = [&](uint32_t address, uint32_t value, uint32_t mask = UINT32_MAX) {
            return port.write(address, value) && port.read(address, readback) && (readback & mask) == value;
        };
        const uint32_t checkedConfig = config | (1u << 20);
        const uint32_t configMask = StateMask | (0xffu << 24) | (event ? 0x1000fu : 0x7c00fu);
        if (!port.write(ctx, config) || !port.read(ctx, readback) || (readback & configMask) != checkedConfig ||
            !writeChecked(ctx + Length, length, 0xffff) || !writeChecked(ctx + BaseLow, uint32_t(ring.iova)) ||
            !writeChecked(ctx + BaseHigh, high) || !port.write(bell + 4, high)) return refuse();
        if (event) {
            constexpr uint32_t zeros[] = {EventModeration, MsiLow, MsiHigh, EventUpdateLow, EventUpdateHigh};
            for (const auto offset : zeros)
                if (!writeChecked(ctx + offset, 0)) return refuse();
            port.publish();
            if (!port.write(bell, uint32_t(ring.iova + length - sizeof(RingElement)))) return refuse();
        } else {
            const uint32_t scratch = (queue == Queue::Tx ? 1u << 16 : 0) | (1u << 4) | engine;
            if (!writeChecked(ctx + Scratch, scratch) || !writeChecked(ctx + Scratch + 4, 0) ||
                !writeChecked(ctx + Scratch + 8, 0) || !writeChecked(ctx + Scratch + 12, 0) ||
                !writeChecked(ctx + Qos, 1)) return refuse();
        }
        port.publish();
        if (!port.healthy()) return refuse();
        memory_[slot] = ring;
        prepared_ |= bit;
        engine_ = engine;
        return Result::Completed;
    }

    template<class Port>
    Result bind(Port &port, Rings &rings)
    {
        using namespace ControlRegisters;
        if (retained_) return Result::Retained;
        if (released_ || bound_ || started_ != Channels || stopped_) return Result::Refused;
        uint32_t tx = 0, rx = 0, event = 0;
        if (!port.healthy() || !port.serialIdle() || !port.read(TxContext + ReadLow, tx) ||
            !port.read(RxContext + ReadLow, rx) || !port.read(EventContext + ReadLow, event) ||
            !rings.bindStarted({memory_[0], memory_[1], memory_[2]}, tx, rx, event)) return refuse();
        bound_ = true;
        return Result::Completed;
    }

    // The owner serializes commands and ring operations. The local GPII
    // control sources are enabled. During polling the owner masks CPU IRQ
    // delivery so an ISR cannot consume the completion. healthy() verifies
    // that exclusion and checks live clocks and GPII/stream fault status.
    // drained() verifies that the ring owner has retired every request and
    // closed admission before STOP and the remaining orderly commands.
    template<class Port>
    Result execute(Port &port, Queue queue, Command command)
    {
        using namespace ControlRegisters;
        if (retained_) return Result::Retained;
        if (released_ || (queue != Queue::Tx && queue != Queue::Rx && queue != Queue::Event)) return Result::Refused;

        const bool event = queue == Queue::Event;
        const uint32_t channel = queue == Queue::Rx ? 1 : 0;
        const uint32_t bit = 1u << channel;
        const unsigned ownership = event ? Event : bit;
        State from{}, to{};
        if (!transition(ownership, command, from, to)) return Result::Refused;
        const bool stopping = command == Command::Stop || command == Command::ResetStopped ||
                              command == Command::Deallocate;
        const uint32_t own = event ? EventPending : ChannelPending;
        const uint32_t other = event ? ChannelPending : EventPending;
        const uint32_t context = event ? EventContext : channel ? RxContext : TxContext;
        uint32_t pending = 0, foreign = 0, config = 0;
        if (!port.healthy() || !port.serialIdle() || (stopping && !port.drained()) || !port.read(own, pending) ||
            !port.read(other, foreign) || pending || foreign || !port.read(context, config) ||
            config == UINT32_MAX || State((config & StateMask) >> 20) != from) return refuse();

        // A failed write can still have reached the controller.
        used_ = true;
        const uint64_t began = port.nowMicros();
        if (!port.write(event ? EventCommand : ChannelCommand, (uint32_t(command) << 24) | channel))
            return refuse();
        for (unsigned poll = 0; poll <= 250; ++poll) {
            if (port.nowMicros() - began >= 250000 || !port.healthy() || !port.read(own, pending) ||
                !port.read(other, foreign) || foreign || (pending & ~bit)) return refuse();
            if (pending == bit) {
                if (!port.write(event ? EventClear : ChannelClear, bit) || !port.read(own, pending) || pending ||
                    !port.read(other, foreign) || foreign ||
                    !port.read(context, config) || config == UINT32_MAX || !port.healthy()) return refuse();
                const auto state = State((config & StateMask) >> 20);
                // MiCode documents that DE_ALLOC may leave CNTXT_0 unchanged.
                // Only a freshly observed matching completion can retire it.
                if (state != to && (command != Command::Deallocate || state != from)) return refuse();
                completed(ownership, command);
                return Result::Completed;
            }
            port.waitMicros(1000);
        }
        return refuse();
    }
};

} // namespace GpiSpi
