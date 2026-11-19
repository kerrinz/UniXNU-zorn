// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornDpuCommandTransfer339 {

// Recovery FDT and MiCode display 3f527f3e: sde_hw_ctl.c, sde_hwio.h,
// sde_hw_intf.c, dsi_ctrl_reg.h and dsi_ctrl_hw_cmn.c.
enum : uint32_t {
    Interrupt2Enable = 0x1008, Interrupt2Status = 0x100c, Interrupt2Clear = 0x102c,
    CtlTop = 0x16014, CtlFlush = 0x16018, CtlStart = 0x1601c,
    CtlIntfActive = 0x160f4, CtlFetchActive = 0x160fc,
    Vig0Source = 0x5014, Vig1Source = 0x7014, Vig0Stride = 0x5024, Vig1Stride = 0x7024,
    AutoRefreshConfig = 0x2b4, AutoRefreshStatus = 0x2c0, UnderrunCount = 0x268, InterfaceFrames = 0xac,
    DsiInterrupt = 0x110, DsiDone = 1u << 8, DsiDoneEnabled = 1u << 9, DsiError = 1u << 24,
    DsiEnableMask = 0xa222aa02, CtlDone = 1, VigFlush = 3,
};
enum Result : uint32_t {
    NotRun, RouteUnavailable, GopBusy, LeaseUnavailable, ReadUnavailable,
    ExistingActivity, WrongTopology, AutoRefreshActive, ArmFailed,
    ProgramUncertain, ObservationLost, Timeout, TransferObserved,
};
enum Field : unsigned {
    Status, Sequence, Retain, StartMs, LatchUs, CtlUs, DsiUs, Polls, FrameDelta,
    InitialAutoConfig, InitialAutoStatus, InitialCtlEnable, InitialCtlStatus,
    InitialDsi, LastDsi, DpuVersion, DsiVersion, PixelClock, ByteClock, ByteIntfClock,
    EscapeClock, InitialCtlStart, InitialCtlFlush, DsiControl, DsiClockControl, Words,
};

inline constexpr uint32_t DeadlineUs = 50000;

// The caller holds the checked display lease and the framebuffer writer
// lock. Same-address programming leaves the inherited DMA route intact. Clear
// only the two owned completion bits, and keep resources on ambiguous return.
template <typename Port>
void run(Port &port, uint32_t address, uint32_t stride, uint32_t (&out)[Words])
{
    out[Status] = LeaseUnavailable;
    if (!port.lease()) return;
    uint32_t ctl = 0, active = 0, fetch = 0, addr0 = 0, addr1 = 0, stride0 = 0, stride1 = 0;
    uint32_t underruns = 0, frames = 0;
    out[Status] = ReadUnavailable;
    if (!port.readMdp(0, out[DpuVersion]) || !port.readMdp(CtlTop, ctl) ||
        !port.readMdp(CtlIntfActive, active) || !port.readMdp(CtlFetchActive, fetch) ||
        !port.readMdp(CtlFlush, out[InitialCtlFlush]) || !port.readMdp(CtlStart, out[InitialCtlStart]) ||
        !port.readMdp(Vig0Source, addr0) || !port.readMdp(Vig1Source, addr1) ||
        !port.readMdp(Vig0Stride, stride0) || !port.readMdp(Vig1Stride, stride1) ||
        !port.readMdp(Interrupt2Enable, out[InitialCtlEnable]) || !port.readMdp(Interrupt2Status, out[InitialCtlStatus]) ||
        !port.readIntf(AutoRefreshConfig, out[InitialAutoConfig]) || !port.readIntf(AutoRefreshStatus, out[InitialAutoStatus]) ||
        !port.readIntf(UnderrunCount, underruns) || !port.readIntf(InterfaceFrames, frames) ||
        !port.readDsi(0, out[DsiVersion]) || !port.readDsi(4, out[DsiControl]) ||
        !port.readDsi(0xa8, out[DsiClockControl]) || !port.readDsi(DsiInterrupt, out[InitialDsi])) return;
    if (out[DpuVersion] >> 16 != 0xa000 || !(ctl & (1u << 17)) || active != 2 || fetch != 0x30000 ||
        address != 0xfc400000 || stride != 5760 || addr0 != address || addr1 != address ||
        (stride0 & 0xffff) != stride || (stride1 & 0xffff) != stride || out[DsiVersion] != 0x20080000 ||
        out[DsiControl] != 0x1f5 || (out[DsiClockControl] & 0x1f1f) != 0x1f1f) {
        out[Status] = WrongTopology;
        return;
    }
    if (out[InitialCtlStart] || out[InitialCtlFlush] || (out[InitialCtlEnable] & CtlDone) ||
        (out[InitialDsi] & (DsiDoneEnabled | DsiError))) {
        out[Status] = ExistingActivity;
        return;
    }
    if ((out[InitialAutoConfig] >> 31) || out[InitialAutoStatus]) {
        out[Status] = AutoRefreshActive;
        return;
    }

    out[Status] = ArmFailed;
    uint32_t ctlStatus = 0, start = 0, flush = 0, currentFrames = 0;
    const auto dsiEnables = out[InitialDsi] & DsiEnableMask;
    if (!port.lease() ||
        ((out[InitialCtlStatus] & CtlDone) && !port.writeMdp(Interrupt2Clear, CtlDone)) ||
        ((out[InitialDsi] & DsiDone) && !port.writeDsi(DsiInterrupt, dsiEnables | DsiDone)) ||
        !port.readMdp(Interrupt2Status, ctlStatus) || (ctlStatus & CtlDone) ||
        !port.readMdp(CtlStart, start) || start || !port.readMdp(CtlFlush, flush) || flush ||
        !port.readIntf(InterfaceFrames, currentFrames) || currentFrames != frames ||
        !port.readDsi(DsiInterrupt, out[LastDsi]) || (out[LastDsi] & (DsiDone | DsiError)) ||
        (out[LastDsi] & DsiEnableMask) != dsiEnables || !port.lease()) return;

    out[Status] = ProgramUncertain;
    out[Sequence] = out[Retain] = 1;
    const uint64_t startUs = port.nowUs();
    out[StartMs] = uint32_t(startUs / 1000);
    if (!port.writeMdp(Vig0Source, addr0) || !port.writeMdp(Vig1Source, addr1) ||
        !port.writeMdp(CtlFlush, VigFlush) || !port.writeMdp(CtlStart, 1)) return;

    out[Status] = Timeout;
    while (out[Polls] < 50 && port.nowUs() - startUs < DeadlineUs) {
        ++out[Polls];
        uint32_t currentUnderruns = 0;
        if (!port.lease() || !port.readMdp(CtlFlush, flush) || !port.readMdp(Interrupt2Status, ctlStatus) ||
            !port.readIntf(UnderrunCount, currentUnderruns) || currentUnderruns != underruns ||
            !port.readDsi(DsiInterrupt, out[LastDsi]) || (out[LastDsi] & DsiError) ||
            (out[LastDsi] & DsiEnableMask) != dsiEnables) {
            out[Status] = ObservationLost;
            return;
        }
        const uint64_t elapsed = port.nowUs() - startUs;
        if (elapsed >= DeadlineUs) return;
        // One-based elapsed encoding reserves zero for an unobserved event.
        if (!flush && !out[LatchUs]) out[LatchUs] = uint32_t(elapsed + 1);
        if ((ctlStatus & CtlDone) && !out[CtlUs]) out[CtlUs] = uint32_t(elapsed + 1);
        if ((out[LastDsi] & DsiDone) && !out[DsiUs]) out[DsiUs] = uint32_t(elapsed + 1);
        if (!flush && (ctlStatus & CtlDone) && (out[LastDsi] & DsiDone)) {
            uint32_t config = 0, autoStatus = 0;
            out[Status] = ObservationLost;
            if (!port.readMdp(CtlStart, start) || start || !port.readIntf(AutoRefreshConfig, config) ||
                (config >> 31) || !port.readIntf(AutoRefreshStatus, autoStatus) || autoStatus ||
                !port.readIntf(InterfaceFrames, currentFrames) || !port.lease() ||
                !port.writeMdp(Interrupt2Clear, CtlDone) || !port.writeDsi(DsiInterrupt, dsiEnables | DsiDone)) return;
            out[FrameDelta] = currentFrames - frames;
            out[Retain] = 0;
            out[Status] = TransferObserved;
            return;
        }
        port.delayMs(1);
    }
}

} // namespace ZornDpuCommandTransfer339
