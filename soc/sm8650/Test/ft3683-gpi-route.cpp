// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "../../../native/display/ZornDisplaySmmu336.h"
#include "../../../native/display/ZornFt3683GpiRoute.h"
#include <cassert>

namespace Route = ZornFt3683GpiRoute;
namespace Smmu = ZornDisplaySmmu336;

struct GpiPort {
    uint32_t addressToChange = 0;
    uint32_t value = 0;
    unsigned visits = 0;
    bool available = true;
    bool read(uint32_t address, uint32_t &result)
    {
        assert(visits < 3 && address == Route::ContextRegisters[visits]);
        ++visits;
        result = address == addressToChange ? value : 0;
        return available;
    }
};

static void staticContexts()
{
    static_assert(Route::TxConfig == 0xa10000 && Route::RxConfig == 0xa10080 &&
                  Route::EventConfig == 0xa11000);
    GpiPort unreadable{0, 0, 0, false};
    assert(!Route::staticGpiiUnallocated(unreadable) && unreadable.visits == 1);
    for (const uint32_t address : Route::ContextRegisters) {
        for (unsigned state = 1; state < 16; ++state) {
            GpiPort busy{address, state << 20};
            assert(!Route::staticGpiiUnallocated(busy));
        }
        GpiPort invalid{address, UINT32_MAX};
        assert(!Route::staticGpiiUnallocated(invalid));
    }
    GpiPort unallocatedWithType{Route::EventConfig, 0x10010002};
    assert(Route::staticGpiiUnallocated(unallocatedWithType) &&
           unallocatedWithType.visits == 3);
}

struct SmmuRegisters {
    uint32_t smr[4] = {0x800000b6, 0x800000a3, 0x80021c00, 0};
    uint32_t s2cr[4] = {0x10000, 0, 1, 0};
    uint32_t control = 0;
    unsigned scans = 0;
    bool change = false;
    bool unreadable = false;

    bool operator()(uint32_t offset, uint32_t &value)
    {
        value = 0;
        if (offset == 0) { ++scans; value = control; }
        else if (offset == 0x20) value = (1u << 30) | (1u << 27) | (13u << 9) | 4;
        else if (offset == 0x24) value = 2;
        else if (offset >= 0x800 && offset < 0x810) value = smr[(offset - 0x800) / 4];
        else if (offset >= 0xc00 && offset < 0xc10) value = s2cr[(offset - 0xc00) / 4];
        else if (offset == 0x1000 || offset == 0x1004) value = 1u << 16;
        else if (offset == 0x2000) value = 1;
        else if (offset == 0x2020) value = scans == 2 && change ? 0x9000 : 0x8000;
        else if (offset == 0x2024 && unreadable) return false;
        return true;
    }
};

static void streamRoutes()
{
    constexpr unsigned Gpi = Smmu::Streams;
    constexpr unsigned Qup = Gpi + Smmu::EntryWords;
    // ID1 supplies 2 pages before the two context banks.
    constexpr uint32_t aperture = 0xd0000;
    uint32_t summary[Smmu::Words]{};
    SmmuRegisters read;
    Smmu::sample(read, aperture, Route::StreamIds, summary);
    assert(read.scans == 2 && summary[Smmu::State] == Smmu::Observed);
    assert(summary[Gpi + Smmu::Route] == Smmu::StreamBypass && summary[Gpi + Smmu::Slot] == 0);
    assert(summary[Qup + Smmu::Route] == Smmu::Stage1Enabled && summary[Qup + Smmu::Slot] == 1);
    assert(summary[Qup + Smmu::Ttbr0Low] == 0x8000);

    Smmu::sample(read, aperture, summary);
    assert(summary[Smmu::State] == Smmu::Observed &&
           summary[Gpi + Smmu::Slot] == 2 && summary[Qup + Smmu::Slot] == 2 &&
           summary[Gpi + Smmu::Route] == Smmu::ContextBypass);

    read = {};
    read.change = true;
    Smmu::sample(read, aperture, Route::StreamIds, summary);
    assert(summary[Smmu::State] == Smmu::Changed && summary[Qup + Smmu::Ttbr0Low] == 0);
    read = {};
    read.unreadable = true;
    Smmu::sample(read, aperture, Route::StreamIds, summary);
    assert(summary[Smmu::State] == Smmu::ReadFailed && summary[Qup + Smmu::Route] == 0);
    read = {};
    read.smr[3] = 0x800000b6;
    Smmu::sample(read, aperture, Route::StreamIds, summary);
    assert(summary[Smmu::State] == Smmu::Unsupported);
    read = {};
    read.smr[0] = 0;
    read.control = 1u << 10;
    Smmu::sample(read, aperture, Route::StreamIds, summary);
    assert(summary[Smmu::State] == Smmu::Observed && summary[Gpi + Smmu::Route] == Smmu::UnmatchedFault);
}

int main()
{
    staticContexts();
    streamRoutes();
}
