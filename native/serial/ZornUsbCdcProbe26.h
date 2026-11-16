// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornUsbCdcProbe26 {
enum class Result : unsigned { MapFailed, PowerOff, ClockOff, InvalidCore, WrongRole,
                               ControllerBusy, UnknownSmmu, MissingStream, AmbiguousStream,
                               TranslatedOrFaulting, IdentityRoute };

struct Snapshot {
    uint32_t power = 0, clocks = 0, core = 0, hardware = 0, gctl = 0, dctl = 0, dsts = 0;
    uint32_t id0 = 0, id1 = 0, id2 = 0, scr0 = 0, matches = 0, route = 0;
    uint32_t cbar = 0, sctlr = 0, cba2r = 0;
};

// Addresses and SID are from K80's pineapple USB and apps SMMU nodes.
// The inherited-route check follows houji_usb_debug.c's read-only preflight.
template<class Io>
Result inspect(Io &io, Snapshot &out)
{
    const auto gcc = io.map(0x139000, 0x4000);
    if (!gcc) return Result::MapFailed;
    out.power = io.read(gcc, 0x04);
    if (!(out.power & (1u << 31))) return Result::PowerOff;
    out.clocks = io.read(gcc, 0x18) | io.read(gcc, 0x88) | io.read(gcc, 0x8c);
    if (out.clocks & (1u << 31)) return Result::ClockOff;

    const auto dwc = io.map(0x0a600000, 0x10000);
    if (!dwc) return Result::MapFailed;
    out.core = io.read(dwc, 0xc120);
    out.hardware = io.read(dwc, 0xc140);
    const auto width = out.hardware >> 24;
    if (((out.core >> 16) != 0x5533 && (out.core >> 16) != 0x3331) || width < 36 || width > 64)
        return Result::InvalidCore;
    out.gctl = io.read(dwc, 0xc110);
    out.dctl = io.read(dwc, 0xc704);
    out.dsts = io.read(dwc, 0xc70c);
    if ((out.gctl >> 12 & 3u) != 2) return Result::WrongRole;
    if ((out.dctl & (3u << 30)) || !(out.dsts & (1u << 22))) return Result::ControllerBusy;

    const auto smmu = io.map(0x15000000, 0x100000);
    if (!smmu) return Result::MapFailed;
    out.id0 = io.read(smmu, 0x20);
    out.id1 = io.read(smmu, 0x24);
    out.id2 = io.read(smmu, 0x28);
    out.scr0 = io.read(smmu, 0);
    // The reference uses legacy SMR valid bits and a 4 KiB context stride.
    // Record unfamiliar layouts without reading their route or context registers.
    if (out.id0 != 0x4c017e6b || out.id1 != 0x60000047 || out.id2 != 0x5111 ||
        (out.scr0 & ((1u << 3) | 1u))) return Result::UnknownSmmu;
    for (unsigned i = 0; i < (out.id0 & 0xff); ++i) {
        const uint32_t smr = io.read(smmu, 0x800 + 4 * i);
        if ((smr >> 31) && !((smr ^ 0x40u) & ~(smr >> 16 & 0x7fffu) & 0xffffu)) {
            ++out.matches;
            out.route = io.read(smmu, 0xc00 + 4 * i);
        }
    }
    if (!out.matches) return Result::MissingStream;
    if (out.matches != 1) return Result::AmbiguousStream;
    const unsigned type = out.route >> 16 & 3u;
    if (type == 1) return Result::IdentityRoute;
    const unsigned bank = out.route & 0xff;
    if (type != 0 || bank >= (out.id1 & 0xff)) return Result::TranslatedOrFaulting;
    out.cbar = io.read(smmu, 0x1000 + 4 * bank);
    out.cba2r = io.read(smmu, 0x1800 + 4 * bank);
    out.sctlr = io.read(smmu, 0x80000 + 0x1000 * bank);
    if ((out.cbar >> 16 & 3u) == 1 && (out.cba2r & 1u) && !(out.sctlr & 1u))
        return Result::IdentityRoute;
    return Result::TranslatedOrFaulting;
}
}
