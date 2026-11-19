// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "../GpiSpiControl.h"

#include <cassert>
#include <initializer_list>

using GpiSpi::Control;
using GpiSpi::Queue;
using GpiSpi::Result;
using Command = Control::Command;
using namespace GpiSpi::ControlRegisters;

struct Port {
    enum Fault { None, Timeout, WrongIRQ, WrongState, AckSticky, PostedWrite, ClockLost, WrongBase } fault = None;
    uint64_t now = 0;
    unsigned state[3]{};
    uint32_t pending[2]{};
    unsigned writes = 0, resets = 0, clears = 0;
    bool retired = true, idle = true;
    uint32_t words[0x2200 / sizeof(uint32_t)]{};
    GpiSpi::RingElement tx[GpiSpi::ChannelEntries]{}, rx[GpiSpi::ChannelEntries]{}, event[GpiSpi::EventEntries]{};

    bool healthy() const { return fault != ClockLost || writes == 0; }
    bool serialIdle() const { return idle; }
    bool drained() const { return retired; }
    uint64_t nowMicros() const { return now; }
    void waitMicros(unsigned span) { now += span; }
    void publish() {}

    bool read(uint32_t address, uint32_t &word) const
    {
        switch (address) {
        case TxContext: word = words[address / 4] | (state[0] << 20); return true;
        case RxContext: word = words[address / 4] | (state[1] << 20); return true;
        case EventContext: word = words[address / 4] | (state[2] << 20); return true;
        case ChannelPending: word = pending[0]; return true;
        case EventPending: word = pending[1]; return true;
        }
        if (address < sizeof(words) && !(address % 4)) {
            word = words[address / 4];
            return true;
        }
        return false;
    }

    bool write(uint32_t address, uint32_t word)
    {
        if (address == ChannelClear || address == EventClear) {
            const unsigned group = address == EventClear;
            assert(pending[group] == word);
            ++clears;
            if (fault != AckSticky) pending[group] = 0;
            return true;
        }
        if (address != ChannelCommand && address != EventCommand) {
            assert(address < sizeof(words) && !(address % 4));
            const bool base = address == TxContext + BaseLow || address == RxContext + BaseLow ||
                              address == EventContext + BaseLow;
            words[address / 4] = word + (base && fault == WrongBase);
            if (base) words[(address + ReadLow - BaseLow) / 4] = word;
            return true;
        }
        ++writes;
        const unsigned group = address == EventCommand;
        const unsigned channel = word & 255;
        const unsigned command = word >> 24;
        assert(channel <= 1 && (!group || !channel));
        if (fault == Timeout) return true;
        const unsigned index = group ? 2 : channel;
        switch (command) {
        case 0: state[index] = 1; break;
        case 1: state[index] = 2; break;
        case 2: state[index] = 3; break;
        case 9: assert(state[index] == 3); state[index] = 1; ++resets; break;
        case 10: assert(state[index] == 1); break; // Vendor CNTXT_0 can stay stale.
        default: assert(false);
        }
        if (fault == WrongState) state[index] = 0xf;
        pending[fault == WrongIRQ ? 1 - group : group] = 1u << channel;
        return fault != PostedWrite;
    }
};

static void start(Control &control, Port &port, GpiSpi::Rings &rings, bool bind = true)
{
    assert(control.execute(port, Queue::Tx, Command::Allocate) == Result::Refused);
    assert(!port.writes);
    assert(control.execute(port, Queue::Event, Command::Allocate) == Result::Completed);
    for (auto queue : {Queue::Tx, Queue::Rx})
        assert(control.execute(port, queue, Command::Allocate) == Result::Completed);
    assert(control.execute(port, Queue::Tx, Command::Start) == Result::Refused);
    assert(control.configure(port, Queue::Event, {port.event, 0x101000}, 4) == Result::Completed);
    assert(port.words[EventDoorbell / 4] == 0x1017f0);
    assert(control.configure(port, Queue::Tx, {port.tx, 0x101000}, 4) == Result::Refused);
    assert(control.configure(port, Queue::Tx, {port.tx, 0x100000}, 4) == Result::Completed);
    assert(control.configure(port, Queue::Rx, {port.rx, 0x100400}, 4) == Result::Completed);
    assert(port.words[(TxContext + Scratch) / 4] == 0x10014);
    assert(port.words[(RxContext + Scratch) / 4] == 0x14);
    for (auto queue : {Queue::Tx, Queue::Rx})
        assert(control.execute(port, queue, Command::Start) == Result::Completed);
    if (bind) {
        assert(control.bind(port, rings) == Result::Completed);
        assert(rings.readyForOrderlyStop());
        assert(control.acceptsTransfers() && !control.canReleaseMemory());
        assert(control.bind(port, rings) == Result::Refused);
    }
}

int main()
{
    {
        Port port;
        Control control;
        GpiSpi::Rings rings;
        start(control, port, rings);
        assert(control.execute(port, Queue::Tx, Command::Stop) == Result::Completed);
        assert(!control.acceptsTransfers() && !control.canReleaseMemory());
        assert(control.execute(port, Queue::Tx, Command::ResetStopped) == Result::Refused);
        assert(!port.resets);
        assert(control.execute(port, Queue::Rx, Command::Stop) == Result::Completed);
        for (auto queue : {Queue::Tx, Queue::Rx})
            assert(control.execute(port, queue, Command::ResetStopped) == Result::Completed);
        assert(control.execute(port, Queue::Event, Command::Deallocate) == Result::Refused);
        for (auto queue : {Queue::Tx, Queue::Rx, Queue::Event})
            assert(control.execute(port, queue, Command::Deallocate) == Result::Completed);
        assert(port.writes == 12 && port.clears == 12 && port.resets == 2);
        assert(control.canReleaseMemory() && !control.acceptsTransfers());
        assert(control.execute(port, Queue::Event, Command::Allocate) == Result::Refused);
    }
    for (auto fault : {Port::Timeout, Port::WrongIRQ, Port::WrongState,
                       Port::AckSticky, Port::PostedWrite, Port::ClockLost}) {
        Port port{fault};
        Control control;
        assert(control.execute(port, Queue::Event, Command::Allocate) == Result::Retained);
        assert(port.writes == 1 && port.resets == 0);
        assert(control.execute(port, Queue::Event, Command::Allocate) == Result::Retained);
        assert(!control.canReleaseMemory() && !control.acceptsTransfers());
        assert(port.writes == 1);
        if (fault == Port::Timeout) assert(port.now == 250000);
    }
    for (const bool occupied : {false, true}) {
        Port port;
        Control control;
        if (occupied) port.state[2] = 1;
        else port.pending[0] = 1;
        assert(control.execute(port, Queue::Event, Command::Allocate) == Result::Refused);
        assert(!port.writes && !port.clears);
        assert(control.canReleaseMemory());
    }
    {
        Port port;
        Control control;
        GpiSpi::Rings rings;
        start(control, port, rings);
        port.retired = false;
        assert(control.execute(port, Queue::Tx, Command::Stop) == Result::Retained);
        assert(port.writes == 5 && !port.resets);
    }
    {
        Port port;
        Control control;
        assert(control.execute(port, Queue::Event, Command::Allocate) == Result::Completed);
        port.fault = Port::WrongBase;
        assert(control.configure(port, Queue::Event, {port.event, 0x101000}, 4) == Result::Retained);
        assert(!port.words[EventDoorbell / 4]);
        assert(control.execute(port, Queue::Tx, Command::Allocate) == Result::Retained);
    }
    {
        Port port;
        Control control;
        GpiSpi::Rings rings;
        start(control, port, rings, false);
        ++port.words[(EventContext + ReadLow) / 4];
        assert(control.bind(port, rings) == Result::Retained);
        assert(!rings.readyForOrderlyStop());
    }
}
