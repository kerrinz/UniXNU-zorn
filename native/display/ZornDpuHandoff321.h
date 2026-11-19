// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornDisplayTiming318.h"

namespace ZornDpuHandoff321 {

// Pineapple K80 recovery FDT: qcom,mdss_mdp@ae00000, CTL and SSPP catalogues.
inline constexpr uint64_t Mdp = 0x0ae00000;
inline constexpr uint32_t ReadExtent = 0x30000;
inline constexpr uint32_t CtlOffsets[] = {0x16000, 0x17000, 0x18000, 0x19000, 0x1a000, 0x1b000};
inline constexpr uint32_t PipeOffsets[] = {
    0x5000, 0x7000, 0x9000, 0xb000, 0x25000, 0x27000, 0x29000, 0x2b000, 0x2d000, 0x2f000
};
// MiCode sde_hw_ctl.c fetch_tbl: VIG0..3 then DMA0..5.
inline constexpr unsigned FetchBits[] = {16, 17, 18, 19, 0, 1, 2, 3, 4, 5};
inline constexpr unsigned CtlCount = sizeof(CtlOffsets) / sizeof(CtlOffsets[0]);
inline constexpr unsigned PipeCount = sizeof(PipeOffsets) / sizeof(PipeOffsets[0]);
inline constexpr unsigned CtlWords = 4;
inline constexpr unsigned PipeWords = 5;
inline constexpr uint32_t UnstableTopology = 9;
static_assert(PipeCount == sizeof(FetchBits) / sizeof(FetchBits[0]));

enum Field : unsigned {
    Status, UptimeMs, GopAddress, GopStride, GccAhb, CoreDomain, CoreConfig,
    AhbClock, MdpClock, VsyncClock, DisplayCtlMask, ActiveFetchMask,
    CtlStart, PipeStart = CtlStart + CtlCount * CtlWords,
    Words = PipeStart + PipeCount * PipeWords
};

// Only the display's active SSPPs are read. No source addresses are changed.
// Equal physical and register addresses in this snapshot are correlation
// evidence; the display's SMMU translation must be checked independently.
template <typename CheckClock, typename MdpRead>
void sampleChecked(CheckClock &check, MdpRead &mdp, uint32_t stamp, uint32_t gop, uint32_t stride,
                   uint32_t (&out)[Words])
{
    using namespace ZornDisplayTiming318;
    for (auto &word : out) word = 0;
    out[UptimeMs] = stamp;
    out[GopAddress] = gop;
    out[GopStride] = stride;
    uint32_t state[ZornDisplayTiming318::Words]{};
    auto result = check(state);
    for (unsigned i = GccAhb; i <= VsyncClock; ++i)
        out[i] = state[ZornDisplayTiming318::GccAhb + i - GccAhb];
    out[Status] = uint32_t(result);
    if (result != Result::Observed) return;

    constexpr uint32_t CtlRegs[CtlWords] = {0xf4, 0xfc, 0x14, 0x18};
    constexpr uint32_t PipeRegs[PipeWords] = {0x14, 0x00, 0x24, 0x30, 0x38};
    uint32_t ctl[CtlCount][CtlWords]{};
    uint32_t pipe[PipeCount][PipeWords]{};
    uint32_t activeCtls = 0;
    uint32_t fetch = 0;
    for (unsigned i = 0; i < CtlCount; ++i) {
        if (!mdp(CtlOffsets[i] + CtlRegs[0], ctl[i][0])) {
            out[Status] = uint32_t(Result::MissingMapping);
            return;
        }
        if (!(ctl[i][0] & (1u << 1))) continue; // Live FDT DSI0 = INTF 1.
        activeCtls |= 1u << i;
        for (unsigned reg = 1; reg < CtlWords; ++reg) {
            if (!mdp(CtlOffsets[i] + CtlRegs[reg], ctl[i][reg])) {
                out[Status] = uint32_t(Result::MissingMapping);
                return;
            }
        }
        fetch |= ctl[i][1];
    }
    for (unsigned i = 0; i < PipeCount; ++i) {
        if (!(fetch & (1u << FetchBits[i]))) continue;
        for (unsigned reg = 0; reg < PipeWords; ++reg) {
            if (!mdp(PipeOffsets[i] + PipeRegs[reg], pipe[i][reg])) {
                out[Status] = uint32_t(Result::MissingMapping);
                return;
            }
        }
    }
    if (check(state) != Result::Observed) {
        out[Status] = uint32_t(Result::UnstablePower);
        return;
    }
    for (unsigned i = 0; i < CtlCount; ++i) {
        if (!(activeCtls & (1u << i))) continue;
        uint32_t active = 0, pending = 0, readPipes = 0;
        if (!mdp(CtlOffsets[i] + CtlRegs[0], active) ||
            !mdp(CtlOffsets[i] + CtlRegs[1], readPipes) ||
            !mdp(CtlOffsets[i] + CtlRegs[3], pending) || active != ctl[i][0] ||
            readPipes != ctl[i][1] || pending || ctl[i][3]) {
            out[Status] = UnstableTopology;
            return;
        }
    }
    if (check(state) != Result::Observed) {
        out[Status] = uint32_t(Result::UnstablePower);
        return;
    }
    out[DisplayCtlMask] = activeCtls;
    out[ActiveFetchMask] = fetch;
    for (unsigned i = 0; i < CtlCount; ++i)
        for (unsigned reg = 0; reg < CtlWords; ++reg) out[CtlStart + i * CtlWords + reg] = ctl[i][reg];
    for (unsigned i = 0; i < PipeCount; ++i)
        for (unsigned reg = 0; reg < PipeWords; ++reg) out[PipeStart + i * PipeWords + reg] = pipe[i][reg];
}

template <typename ClockRead, typename MdpRead>
void sample(ClockRead &clock, MdpRead &mdp, uint32_t stamp, uint32_t gop, uint32_t stride,
            uint32_t (&out)[Words])
{
    auto check = [&](uint32_t (&state)[ZornDisplayTiming318::Words]) {
        return ZornDisplayTiming318::checkClockState(clock, state);
    };
    sampleChecked(check, mdp, stamp, gop, stride, out);
}

} // namespace ZornDpuHandoff321
