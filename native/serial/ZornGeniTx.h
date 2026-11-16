// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace ZornGeniTx {
enum class Result : unsigned { Complete, Unavailable, Busy, Invalid, Timeout, Fault };

struct Snapshot {
    uint32_t sequencer = 0, fifo = 0, irqEnable = 0, irqStatus = 0;
};

// K80 GENI debug UART register definitions from MiCode geni-se.h and
// qcom_geni_serial.c. The caller supplies an already clocked UART in FIFO mode.
template<class Io>
Result send(Io &io, const char *bytes, size_t length, Snapshot *snapshot = nullptr)
{
    constexpr unsigned status = 0x40, clock = 0x48, interface = 0x64, firmware = 0x68;
    constexpr unsigned mode = 0x258, format = 0x25c, packing0 = 0x260, packing1 = 0x264;
    constexpr unsigned wordLength = 0x268, stopBits = 0x26c, transferLength = 0x270;
    constexpr unsigned command = 0x600, irqStatus = 0x610, irqEnable = 0x614, irqClear = 0x618;
    constexpr unsigned parity = 0x2a4, fifo = 0x700, occupancy = 0x800, fifoShape = 0xe24;
    constexpr uint32_t active = 1u | (1u << 12), done = 1u;
    constexpr uint32_t faults = 0x3eu | (3u << 28);
    constexpr uint32_t fifoCount = (1u << 28) - 1;
    // Four LSB-first 8-bit vectors at positions 0, 8, 16 and 24.
    constexpr uint32_t pack0 = 14u | (270u << 10), pack1 = 526u | (783u << 10);
    if (!bytes || !length || length > 512) return Result::Invalid;
    if ((io.read(firmware) >> 8 & 0xffu) != 2 || !(io.read(clock) & 1u) ||
        (io.read(interface) & 1u) || (io.read(mode) & 1u) ||
        (io.read(format) & 3u) != 2 || (io.read(wordLength) & 0x3ffu) != 8 ||
        (io.read(stopBits) & 0xffffffu) || (io.read(parity) & 1u) ||
        (io.read(packing0) & 0xfffffu) != pack0 || (io.read(packing1) & 0xfffffu) != pack1)
        return Result::Unavailable;
    const Snapshot state{io.read(status), io.read(occupancy), io.read(irqEnable), io.read(irqStatus)};
    if (snapshot) *snapshot = state;
    // MiCode M_COMMON_GENI_M_IRQ_EN configures the protocol error flags.
    // The caller separately verifies the distributor IRQ is disabled.
    constexpr uint32_t commonIrqMask = 0x33c0007e;
    if ((state.sequencer & active) || (state.fifo & fifoCount) ||
        (state.irqEnable & ~commonIrqMask))
        return Result::Busy;
    const unsigned depth = io.read(fifoShape) >> 16 & 0x3fu;
    if (!depth) return Result::Unavailable;
    if (state.irqStatus & faults) return Result::Fault;

    io.write(irqClear, done);
    io.write(transferLength, uint32_t(length));
    io.write(command, 1u << 27);
    size_t sent = 0;
    // A single finite budget covers every FIFO wait and the final completion.
    for (unsigned tick = 0; tick < 10000; ++tick) {
        const uint32_t irq = io.read(irqStatus);
        if (irq & faults) return Result::Fault;
        if (irq & done) {
            if (sent != length) return Result::Fault;
            if (!(io.read(status) & 1u)) {
                io.write(irqClear, done);
                return Result::Complete;
            }
        } else if (sent < length && (io.read(occupancy) & fifoCount) < depth) {
            uint32_t packed = 0;
            for (unsigned shift = 0; shift < 32 && sent < length; shift += 8)
                packed |= uint32_t(uint8_t(bytes[sent++])) << shift;
            io.write(fifo, packed);
            continue;
        }
        io.delay();
    }
    return Result::Timeout;
}
}
