// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornDpuCommandTransfer339.h"

namespace ZornDpuAutoRefreshTransfer340 {

namespace Cmd = ZornDpuCommandTransfer339;

// pineapple-sde-common.dtsi and the archived K80 FDT select INTF1 for DSI0.
// MiCode sde_hw_interrupts.c defines the tear bank and its W1C event bits.
enum : uint32_t {
    TearIrqBase = 0x36800, TearEnable = 0, TearStatus = 4, TearClear = 8, TearBytes = 12,
    AutoKickoff = 1, WritePointerIrq = 2, TearDoneMask = AutoKickoff | WritePointerIrq,
    WriteLine = 0x2b0, InheritedAutoConfig = 0x8000003c, PendingFlush = 1, WriteAdvanced = 2,
};
enum Result : uint32_t {
    NotRun, RouteUnavailable, GopBusy, LeaseUnavailable, ReadUnavailable,
    ExistingActivity, WrongTopology, AutoConfigChanged, ArmFailed,
    ProgramUncertain, ObservationLost, Timeout, TransferObserved,
};
enum Field : unsigned {
    Status, Sequence, Retain, StartMs, LatchUs, KickoffUs, DsiUs, Polls, FrameDelta,
    InitialAutoConfig, InitialAutoStatus, InitialTearEnable, InitialTear, InitialDsi,
    LastDsi, LastTear, InitialWriteLine, LastWriteLine, MaxGapUs, InitialInterfaceFrame,
    PixelClock, ByteClock, ByteIntfClock, EscapeClock, Evidence, Words,
};
inline constexpr uint32_t DeadlineUs = 1350000;
inline constexpr uint32_t MaxPolls = 1350;
inline constexpr uint32_t ObservationGapUs = 50000;

// Track one same-buffer flush while leaving autorefresh, the panel commands,
// the interrupt enables, and the scanout address unchanged. The caller holds
// the existing display lease and the GOP writer lock.
template <typename Port>
void run(Port &port, uint32_t address, uint32_t stride, uint32_t (&out)[Words])
{
    out[Status] = LeaseUnavailable;
    if (!port.lease()) return;
    uint32_t ctl = 0, active = 0, fetch = 0, addr0 = 0, addr1 = 0, stride0 = 0, stride1 = 0;
    uint32_t underruns = 0, start = 0, flush = 0, dpuVersion = 0, dsiVersion = 0, dsiControl = 0, laneStatus = 0;
    out[Status] = ReadUnavailable;
    if (!port.readMdp(0, dpuVersion) || !port.readMdp(Cmd::CtlTop, ctl) ||
        !port.readMdp(Cmd::CtlIntfActive, active) || !port.readMdp(Cmd::CtlFetchActive, fetch) ||
        !port.readMdp(Cmd::CtlFlush, flush) || !port.readMdp(Cmd::CtlStart, start) ||
        !port.readMdp(Cmd::Vig0Source, addr0) || !port.readMdp(Cmd::Vig1Source, addr1) ||
        !port.readMdp(Cmd::Vig0Stride, stride0) || !port.readMdp(Cmd::Vig1Stride, stride1) ||
        !port.readIntf(Cmd::AutoRefreshConfig, out[InitialAutoConfig]) ||
        !port.readIntf(Cmd::AutoRefreshStatus, out[InitialAutoStatus]) ||
        !port.readIntf(Cmd::UnderrunCount, underruns) || !port.readIntf(Cmd::InterfaceFrames, out[InitialInterfaceFrame]) ||
        !port.readTear(TearEnable, out[InitialTearEnable]) || !port.readTear(TearStatus, out[InitialTear]) ||
        !port.readDsi(0, dsiVersion) || !port.readDsi(4, dsiControl) ||
        !port.readDsi(0xa8, laneStatus) || !port.readDsi(Cmd::DsiInterrupt, out[InitialDsi])) return;
    if (dpuVersion != 0xa0000000 || !(ctl & (1u << 17)) || active != 2 || fetch != 0x30000 ||
        address != 0xfc400000 || stride != 5760 || addr0 != address || addr1 != address ||
        (stride0 & 0xffff) != stride || (stride1 & 0xffff) != stride || dsiVersion != 0x20080000 ||
        dsiControl != 0x1f5 || (laneStatus & 0x1f1f) != 0x1f1f) {
        out[Status] = WrongTopology;
        return;
    }
    if (out[InitialAutoConfig] != InheritedAutoConfig) {
        out[Status] = AutoConfigChanged;
        return;
    }
    if (start || flush || out[InitialAutoStatus] || (out[InitialTearEnable] & TearDoneMask) ||
        (out[InitialDsi] & (Cmd::DsiDoneEnabled | Cmd::DsiError))) {
        out[Status] = ExistingActivity;
        return;
    }

    const uint32_t initialDsiEnables = out[InitialDsi] & Cmd::DsiEnableMask;
    auto sample = [&] {
        uint32_t enables = 0, config = 0, currentUnderruns = 0;
        return port.lease() &&
            port.readMdp(Cmd::CtlFlush, flush) && port.readMdp(Cmd::CtlStart, start) && !start &&
            port.readIntf(Cmd::AutoRefreshConfig, config) && config == InheritedAutoConfig &&
            port.readIntf(Cmd::UnderrunCount, currentUnderruns) && currentUnderruns == underruns &&
            port.readTear(TearEnable, enables) && enables == out[InitialTearEnable] &&
            port.readTear(TearStatus, out[LastTear]) &&
            port.readIntf(WriteLine, out[LastWriteLine]) &&
            port.readDsi(Cmd::DsiInterrupt, out[LastDsi]) && !(out[LastDsi] & Cmd::DsiError) &&
            (out[LastDsi] & Cmd::DsiEnableMask) == initialDsiEnables;
    };
    auto clean = [&] {
        uint32_t busy = 0;
        return !(out[LastTear] & TearDoneMask) && !(out[LastDsi] & Cmd::DsiDone) &&
            port.readIntf(Cmd::AutoRefreshStatus, busy) && !busy;
    };
    auto acknowledge = [&] {
        const uint32_t tear = out[LastTear] & TearDoneMask;
        return (!tear || port.writeTear(TearClear, tear)) &&
            (!(out[LastDsi] & Cmd::DsiDone) ||
             port.writeDsi(Cmd::DsiInterrupt, initialDsiEnables | Cmd::DsiDone));
    };

    out[Status] = ArmFailed;
    out[LastTear] = out[InitialTear];
    out[LastDsi] = out[InitialDsi];
    if (!port.lease() || !acknowledge() || !sample() || flush || !clean()) return;
    out[InitialWriteLine] = out[LastWriteLine];

    out[Status] = ProgramUncertain;
    out[Sequence] = out[Retain] = 1;
    const uint64_t began = port.nowUs();
    out[StartMs] = uint32_t(began / 1000);
    if (!port.writeMdp(Cmd::CtlFlush, Cmd::VigFlush) || !sample() || flush != Cmd::VigFlush || !clean() ||
        out[LastWriteLine] != out[InitialWriteLine]) return;
    out[Evidence] = PendingFlush;

    out[Status] = Timeout;
    uint64_t previous = began;
    while (out[Polls] < MaxPolls && port.nowUs() - began < DeadlineUs) {
        ++out[Polls];
        if (!sample() || (flush & ~Cmd::VigFlush)) {
            out[Status] = ObservationLost;
            return;
        }
        const uint64_t now = port.nowUs();
        const uint64_t elapsed = now - began;
        if (elapsed >= DeadlineUs) return;
        const uint64_t gap = now - previous;
        previous = now;
        if (gap > out[MaxGapUs]) out[MaxGapUs] = uint32_t(gap);
        if (gap > ObservationGapUs) {
            out[Status] = ObservationLost;
            return;
        }
        const uint32_t observedAt = uint32_t(elapsed + 1);
        if (!flush && !out[LatchUs]) out[LatchUs] = observedAt;
        if (out[LastWriteLine] && out[LastWriteLine] != out[InitialWriteLine] &&
            (out[LastTear] & AutoKickoff)) out[Evidence] |= WriteAdvanced;
        if ((out[LastTear] & TearDoneMask) == TearDoneMask && (out[Evidence] & WriteAdvanced) &&
            !out[KickoffUs]) out[KickoffUs] = observedAt;
        if (out[LastDsi] & Cmd::DsiDone) {
            out[Status] = ObservationLost;
            if (flush || !out[LatchUs] || !out[KickoffUs]) return;
            out[DsiUs] = observedAt;
            uint32_t autoStatus = 0, currentFrames = 0;
            if (!port.readIntf(Cmd::AutoRefreshStatus, autoStatus) || autoStatus ||
                !port.readIntf(Cmd::InterfaceFrames, currentFrames) || !port.lease() || !acknowledge()) return;
            out[FrameDelta] = currentFrames - out[InitialInterfaceFrame];
            out[Retain] = 0;
            out[Status] = TransferObserved;
            return;
        }
        port.delayMs(1);
    }
}

} // namespace ZornDpuAutoRefreshTransfer340
