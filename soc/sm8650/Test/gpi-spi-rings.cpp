// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "../GpiSpiRings.h"
#include <cassert>
#include <vector>

using namespace GpiSpi;

struct Port {
    static constexpr uint64_t TxBase = 0x100100000;
    static constexpr uint64_t RxBase = 0x100104000;
    static constexpr uint64_t EventBase = 0x100108000;
    RingElement tx[ChannelEntries]{};
    RingElement rx[ChannelEntries]{};
    RingElement event[EventEntries]{};
    struct Doorbell { Queue queue; uint32_t value; };
    std::vector<Doorbell> doorbells;
    unsigned producer = 0;
    unsigned published = 0;
    unsigned acquired = 0;
    unsigned acks = 0;
    uint64_t now = 0;
    bool idle = true;
    bool good = true;
    bool failRxDoorbell = false;
    bool failAck = false;
    uint32_t overrideProducer = 0;

    RingSet rings() { return {{tx, TxBase}, {rx, RxBase}, {event, EventBase}}; }
    bool healthy() const { return good; }
    bool serialIdle() const { return idle; }
    uint64_t nowMicros() const { return now; }
    void publish() { ++published; }
    void acquire() { ++acquired; }
    bool eventProducer(uint32_t &out) const
    {
        out = overrideProducer ? overrideProducer : uint32_t(EventBase) + producer * sizeof(RingElement);
        return true;
    }
    bool ring(Queue queue, uint32_t value)
    {
        assert(published);
        doorbells.push_back({queue, value});
        return !failRxDoorbell || queue != Queue::Rx;
    }
    bool ackEvents() { ++acks; return !failAck; }

    void complete(Channel channel, uint64_t tre, uint32_t length = 1513, uint8_t code = 2)
    {
        event[producer] = {{uint32_t(tre), uint32_t(tre >> 32), (uint32_t(code) << 24) | length,
                            (uint32_t(channel) << 24) | (0x22u << 16)}};
        producer = (producer + 1) % EventEntries;
    }
};

static bool bind(Rings &rings, Port &port)
{
    return rings.bindStarted(port.rings(), uint32_t(Port::TxBase), uint32_t(Port::RxBase),
                             uint32_t(Port::EventBase));
}

static Result submit(Rings &rings, Port &port)
{
    return rings.submit(port, 0x40000000, 0x40004000, 1513, 0, 2, 10000);
}

static void geometryAndWrap()
{
    Port port;
    Rings rings;
    auto overlap = port.rings();
    overlap.rx.iova = overlap.tx.iova;
    assert(!rings.bindStarted(overlap, 0, 0, 0));
    overlap = port.rings();
    overlap.rx.cpu = overlap.tx.cpu;
    assert(!rings.bindStarted(overlap, 0, 0, 0));
    assert(!rings.bindStarted(port.rings(), 0, uint32_t(Port::RxBase), uint32_t(Port::EventBase)));
    assert(bind(rings, port));
    assert(!bind(rings, port));
    assert(rings.readyForOrderlyStop());
    assert(rings.submit(port, 1, 2, 1513, 0, 2, 10000) == Result::Refused);
    assert(port.doorbells.empty());
    for (unsigned i = 0; i < 135; ++i) {
        const unsigned txStart = (3 * i) % ChannelEntries;
        const unsigned txTerminal = (txStart + 2) % ChannelEntries;
        const unsigned rxTerminal = i % ChannelEntries;
        const auto prior = port.doorbells.size();
        assert(submit(rings, port) == Result::Pending);
        assert(submit(rings, port) == Result::Refused);
        assert(!rings.readyForOrderlyStop());
        assert(port.doorbells.size() == prior + 2);
        assert(port.doorbells[prior].queue == Queue::Tx);
        assert(port.doorbells[prior].value == uint32_t(Port::TxBase) +
               ((txTerminal + 1) % ChannelEntries) * sizeof(RingElement));
        assert(port.doorbells[prior + 1].queue == Queue::Rx);
        assert(port.doorbells[prior + 1].value == uint32_t(Port::RxBase) +
               ((rxTerminal + 1) % ChannelEntries) * sizeof(RingElement));
        assert(port.tx[txStart].words[0] == 0x03000004);
        assert(port.tx[txTerminal].words[2] == 1513);
        assert(port.rx[rxTerminal].words[0] == 0x40004000);
        port.complete(Rx, Port::RxBase + rxTerminal * sizeof(RingElement), 1513, 1);
        assert(rings.poll(port) == Result::Pending);
        port.complete(Tx, Port::TxBase + txTerminal * sizeof(RingElement));
        port.idle = false;
        assert(rings.poll(port) == Result::Pending);
        port.idle = true;
        assert(rings.poll(port) == Result::Completed);
        const auto &eventDb = port.doorbells.back();
        assert(eventDb.queue == Queue::Event);
        assert(eventDb.value == uint32_t(Port::EventBase) +
               ((port.producer + EventEntries - 1) % EventEntries) * sizeof(RingElement));
        assert(rings.readyForOrderlyStop());
        assert(rings.poll(port) == Result::Refused);
    }
    assert(port.acks == 270 && port.published == 405 && port.acquired == 405);
}

static void failureRetention()
{
    for (unsigned fault = 0; fault != 8; ++fault) {
        Port port;
        Rings rings;
        assert(bind(rings, port));
        port.failRxDoorbell = fault == 0;
        if (fault == 0) {
            assert(submit(rings, port) == Result::Retained);
        } else {
            assert(submit(rings, port) == Result::Pending);
            switch (fault) {
            case 1: port.now = 10000; break;
            case 2: port.overrideProducer = uint32_t(Port::EventBase) + 1; break;
            case 3: port.complete(Tx, Port::TxBase); break;
            case 4: port.complete(Rx, Port::RxBase, 1512); break;
            case 5:
                port.complete(Rx, Port::RxBase);
                port.complete(Rx, Port::RxBase);
                break;
            case 6: port.good = false; break;
            case 7:
                port.complete(Rx, Port::RxBase);
                port.failAck = true;
                break;
            }
            assert(rings.poll(port) == Result::Retained);
        }
        const auto writes = port.doorbells.size();
        const auto acks = port.acks;
        assert(rings.poll(port) == Result::Retained);
        assert(submit(rings, port) == Result::Retained);
        assert(!bind(rings, port));
        assert(!rings.readyForOrderlyStop());
        assert(port.doorbells.size() == writes && port.acks == acks);
    }
}

int main()
{
    geometryAndWrap();
    failureRetention();
}
