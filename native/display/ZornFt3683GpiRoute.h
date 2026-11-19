// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornFt3683GpiRoute {

// Pineapple QUP1 SE4 selects static GPII 0 through the fifth DMA specifier.
// The vendor GPI offset is relative to gpi-top minus its 0x10000 EE offset.
constexpr uint32_t GpiTop = 0x00a00000;
constexpr uint32_t ChannelPage = GpiTop + 0x10000;
constexpr uint32_t EventPage = ChannelPage + 0x1000;
constexpr uint32_t TxConfig = ChannelPage;
constexpr uint32_t RxConfig = ChannelPage + 0x80;
constexpr uint32_t EventConfig = EventPage;
constexpr uint32_t ContextRegisters[] = {TxConfig, RxConfig, EventConfig};
constexpr uint32_t StreamIds[] = {0xb6, 0xa3};

template<class Port>
bool staticGpiiUnallocated(Port &port)
{
    // A stopped or allocated channel still belongs to its previous owner.
    // Both channels and the event context must be free before touching GPIO.
    for (const auto address : ContextRegisters) {
        uint32_t value = 0;
        if (!port.read(address, value) || value == UINT32_MAX || (value & (0xfu << 20))) return false;
    }
    return true;
}

} // namespace ZornFt3683GpiRoute
