// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornGeniTx.h"
#include <IOKit/IOLib.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <pexpert/pexpert.h>

extern "C" vm_offset_t ml_io_map(vm_offset_t physical, vm_size_t size);

namespace ZornGeniConsole26 {
struct Registers {
    vm_offset_t base;
    uint32_t read(unsigned offset) { return ml_io_read32(base + offset); }
    void write(unsigned offset, uint32_t value) { ml_io_write32(base + offset, value); }
    void delay() { IODelay(10); }
};

// Only attach to an idle, firmware-configured port. Clock votes, the pin
// mux, the baud divider and any existing console owner are left alone.
inline ZornGeniTx::Result emit(const char *data, size_t size, ZornGeniTx::Snapshot *snapshot = nullptr)
{
    using ZornGeniTx::Result;
    unsigned selected = 0;
    if (!PE_parse_boot_argn("zorn26_geni_tx", &selected, sizeof(selected)) || selected != 1 ||
        !preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled())
        return Result::Unavailable;

    static unsigned attempted;
    if (__atomic_exchange_n(&attempted, 1u, __ATOMIC_ACQ_REL)) return Result::Busy;
    constexpr uint32_t clockOff = 1u << 31;
    // GCC QUP wrap2 S7 and both wrapper AHB branches, from gcc-pineapple.c.
    Registers serialClock{ml_io_map(0x11c000, 0x4000)};
    Registers wrapperClocks{ml_io_map(0x120000, 0x4000)};
    if (!serialClock.base || !wrapperClocks.base ||
        (serialClock.read(0x288c) & clockOff) ||
        (wrapperClocks.read(0x328c) & clockOff) ||
        (wrapperClocks.read(0x3290) & clockOff))
        return Result::Unavailable;
    // GPIO30 is the UART TX mux. RX is deliberately untouched.
    Registers pins{ml_io_map(0xf11c000, 0x4000)};
    if (!pins.base || (pins.read(0x2000) >> 2 & 0xfu) != 1) return Result::Unavailable;
    constexpr unsigned uartInterrupt = 32 + 462; // DT SPI to GIC INTID.
    Registers distributor{ml_io_map(0x17100000, 0x4000)};
    if (!distributor.base ||
        (distributor.read(0x100 + 4 * (uartInterrupt / 32)) & (1u << (uartInterrupt % 32))))
        return Result::Busy;
    Registers uart{ml_io_map(0x89c000, 0x4000)};
    return uart.base ? ZornGeniTx::send(uart, data, size, snapshot) : Result::Unavailable;
}
}
