// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornGeniConsole26.h"

namespace ZornGeniStages26 {
enum class Stage : unsigned { RootPrepare, RootRegistered, Pid1Worker, Snapshot, Count };

// Call from ordinary boot threads, with no subsystem lock held. The mapping
// belongs to the boot and is never replaced while a transfer might be active.
inline ZornGeniTx::Result emit(Stage stage, const char *line, size_t length,
                             ZornGeniTx::Snapshot *snapshot = nullptr)
{
    using ZornGeniConsole26::Registers;
    using ZornGeniTx::Result;
    if (unsigned(stage) >= unsigned(Stage::Count) || !line || !length || length > 512)
        return Result::Invalid;

    unsigned selected = 0;
    if (!PE_parse_boot_argn("zorn26_geni_stages", &selected, sizeof(selected)) || selected != 1 ||
        !preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled())
        return Result::Unavailable;

    static unsigned gate;
    if (__atomic_exchange_n(&gate, 1u, __ATOMIC_ACQUIRE)) return Result::Busy;
    struct Unlock {
        unsigned &gate;
        ~Unlock() { __atomic_store_n(&gate, 0u, __ATOMIC_RELEASE); }
    } unlock{gate};

    static unsigned attempted;
    static bool stopped;
    static Registers serialClock{}, wrapperClocks{}, pins{}, distributor{}, uart{};
    const unsigned bit = 1u << unsigned(stage);
    if (stopped || (attempted & bit)) return Result::Busy;
    if (!attempted) {
        serialClock.base = ml_io_map(0x11c000, 0x4000);
        wrapperClocks.base = ml_io_map(0x120000, 0x4000);
        pins.base = ml_io_map(0xf11c000, 0x4000);
        distributor.base = ml_io_map(0x17100000, 0x4000);
        uart.base = ml_io_map(0x89c000, 0x4000);
    }
    attempted |= bit;

    constexpr uint32_t clockOff = 1u << 31;
    constexpr unsigned uartInterrupt = 32 + 462;
    if (!serialClock.base || !wrapperClocks.base || !pins.base || !distributor.base || !uart.base ||
        (serialClock.read(0x288c) & clockOff) || (wrapperClocks.read(0x328c) & clockOff) ||
        (wrapperClocks.read(0x3290) & clockOff) || (pins.read(0x2000) >> 2 & 0xfu) != 1) {
        stopped = true;
        return Result::Unavailable;
    }
    if (distributor.read(0x100 + 4 * (uartInterrupt / 32)) & (1u << (uartInterrupt % 32))) {
        stopped = true;
        return Result::Busy;
    }
    const auto result = ZornGeniTx::send(uart, line, length, snapshot);
    stopped = result != Result::Complete;
    return result;
}
}
