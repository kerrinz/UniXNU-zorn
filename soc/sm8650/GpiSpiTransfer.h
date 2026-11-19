// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace GpiSpi {

struct alignas(16) RingElement {
    uint32_t words[4];
};
static_assert(sizeof(RingElement) == 16, "GPI rings contain four-word elements");

struct FullDuplexTransfer {
    RingElement tx[3];
    RingElement rx;
};

enum Channel : uint8_t { Tx = 0, Rx = 1 };

// The addresses refer to the mapped payload, and are distinct from the
// transfer ring addresses. The caller retains both mappings through completion.
inline bool prepareMode0(uint64_t txIova, uint64_t rxIova, uint32_t bytes,
                         uint32_t clockSource, uint32_t clockDivider,
                         FullDuplexTransfer &transfer)
{
    transfer = {};
    if (!txIova || !rxIova || !bytes || bytes > 0x00ffffff ||
        txIova > UINT64_MAX - bytes || rxIova > UINT64_MAX - bytes ||
        (txIova < rxIova + bytes && rxIova < txIova + bytes) ||
        clockSource > 7 || !clockDivider || clockDivider > 0x0fff) {
        return false;
    }

    constexpr uint32_t spiConfig = 0x22u << 16;
    constexpr uint32_t spiGo = 0x20u << 16;
    constexpr uint32_t dmaBuffer = 0x10u << 16;
    constexpr uint32_t linkRx = 1u << 11;
    constexpr uint32_t endOfTransfer = 1u << 9;
    constexpr uint32_t chain = 1;
    constexpr uint32_t packTxRx = 3u << 24;
    constexpr uint32_t wordSize8 = 8 - 4;
    constexpr uint32_t fullDuplex = 3;
    transfer.tx[0] = {{packTxRx | wordSize8, 0, (clockSource << 16) | clockDivider,
                       spiConfig | chain}};
    transfer.tx[1] = {{fullDuplex, 0, bytes, spiGo | linkRx | chain}};
    transfer.tx[2] = {{uint32_t(txIova), uint32_t(txIova >> 32), bytes, dmaBuffer | endOfTransfer}};
    transfer.rx = {{uint32_t(rxIova), uint32_t(rxIova >> 32), bytes, dmaBuffer}};
    return true;
}

// Count only a transfer-complete event identifying this terminal TRE. The
// caller must acquire each event once from the owned hardware ring and match
// it to the current outstanding submission before reusing TRE addresses.
inline bool completes(const RingElement &event, Channel channel,
                      uint64_t terminalTreIova, uint32_t bytes)
{
    constexpr uint8_t transferComplete = 0x22;
    constexpr uint8_t success = 1;
    constexpr uint8_t endOfTransfer = 2;
    constexpr uint16_t unexpectedError = 16;
    const uint64_t pointer = (uint64_t(event.words[1]) << 32) | event.words[0];
    const auto code = uint8_t(event.words[2] >> 24);
    return bytes && bytes <= 0x00ffffff && terminalTreIova && !(terminalTreIova & 15) &&
           pointer == terminalTreIova &&
           (event.words[2] & 0x00ffffff) == bytes &&
           (code == success || code == endOfTransfer) &&
           uint16_t(event.words[3]) != unexpectedError &&
           uint8_t(event.words[3] >> 16) == transferComplete &&
           uint8_t(event.words[3] >> 24) == channel;
}

} // namespace GpiSpi
