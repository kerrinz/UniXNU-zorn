// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include "ZornDisplayClockRead334.h"
#include "ZornDpuHandoff321.h"

namespace ZornDisplayHeldTiming335 {

enum class Result : uint32_t {
    NotRun, ClockStateUnavailable, FabricClockInactive, DomainInactive,
    DisplayBranchInactive, ResetActive, InterfaceUnavailable,
    ClockChangedDuringRead, WindowExpired, Observed,
};

enum Field : unsigned {
    FirstStatus, SecondStatus, FirstMs, SecondMs,
    FirstIntfFrames, FirstMdpFrames, FirstTearCount, FirstLineCount,
    SecondIntfFrames, SecondMdpFrames, SecondTearCount, SecondLineCount,
    RouteStatus, GopAddress, GopStride, ActiveCtl, ActiveFetch, CtlStart,
    PipeStart = CtlStart + ZornDpuHandoff321::CtlCount * ZornDpuHandoff321::CtlWords,
    Used = PipeStart + ZornDpuHandoff321::PipeCount * 2,
    Words = ZornDpuHandoff321::Words,
};
static_assert(Used <= Words);

inline constexpr uint32_t kWindowMs = 120;
inline constexpr uint32_t kMaxWindowMs = 750;

inline Result classify(const uint32_t (&snapshot)[ZornDisplayClockRead334::Words])
{
    using namespace ZornDisplayClockRead334;
    using ZornDisplayTiming318::clockRunning;
    if (snapshot[Status] != Sampled || !interfaceVoted(snapshot[GccAhbBefore]) ||
        !interfaceVoted(snapshot[GccAhbAfter])) return Result::ClockStateUnavailable;
    if (!clockRunning(snapshot[GccAxi])) return Result::FabricClockInactive;
    constexpr uint32_t powerOn = 1u << 31;
    constexpr uint32_t controlOrCollapse = 7u;
    constexpr uint32_t completedPowerEvents = (1u << 16) | (1u << 15);
    if ((snapshot[Domain] & (powerOn | controlOrCollapse)) != powerOn ||
        (snapshot[DomainConfig] & completedPowerEvents) != (1u << 16)) {
        return Result::DomainInactive;
    }
    if (!clockRunning(snapshot[Ahb]) || !clockRunning(snapshot[Mdp]) ||
        !clockRunning(snapshot[Vsync])) return Result::DisplayBranchInactive;
    return Result::Observed;
}

template <typename ReadClock>
Result checkedClock(ReadClock &clock, uint32_t (&state)[ZornDisplayClockRead334::Words])
{
    using namespace ZornDisplayClockRead334;
    sampleUnderLease(clock, state);
    const auto status = classify(state);
    if (status != Result::Observed) return status;
    uint32_t reset = 0;
    if (!clock(Bank::DispCc, 0, reset)) return Result::ClockStateUnavailable;
    return (reset & 1) ? Result::ResetActive : Result::Observed;
}

struct Counters {
    uint32_t intfFrames;
    uint32_t mdpFrames;
    uint32_t tearCount;
    uint32_t lineCount;
};

template <typename ReadClock, typename ReadInterface>
Result sample(ReadClock &clock, ReadInterface &interface, Counters &result)
{
    using namespace ZornDisplayClockRead334;
    result = {};
    uint32_t state[ZornDisplayClockRead334::Words]{};
    const auto readiness = checkedClock(clock, state);
    if (readiness != Result::Observed) return readiness;

    Counters counters{};
    if (!interface(0xac, counters.intfFrames) ||
        !interface(0xa4, counters.mdpFrames) ||
        !interface(0x298, counters.tearCount) ||
        !interface(0xb0, counters.lineCount)) return Result::InterfaceUnavailable;

    if (checkedClock(clock, state) != Result::Observed) return Result::ClockChangedDuringRead;
    result = counters;
    return Result::Observed;
}

// Run only from the actual board owner after successful lease acquisition.
// Read two counter sets and then resolve the active K80 CTL and fetch routes.
template <typename ReadClock, typename ReadInterface, typename ReadMdp, typename Now, typename Delay>
void observe(ReadClock &clock, ReadInterface &interface, ReadMdp &mdp,
             Now now, Delay delay, uint32_t gop, uint32_t stride, uint32_t (&out)[Words])
{
    using DpuResult = ZornDisplayTiming318::Result;
    for (auto &value : out) value = 0;
    Counters first{}, second{};
    const uint32_t firstStart = now();
    const auto firstResult = sample(clock, interface, first);
    out[FirstStatus] = uint32_t(firstResult);
    if (firstResult != Result::Observed) return;

    const uint32_t start = now();
    out[FirstMs] = start;
    out[FirstIntfFrames] = first.intfFrames;
    out[FirstMdpFrames] = first.mdpFrames;
    out[FirstTearCount] = first.tearCount;
    out[FirstLineCount] = first.lineCount;

    delay(kWindowMs);
    const uint32_t secondStart = now();
    if (secondStart - firstStart > kMaxWindowMs) {
        out[SecondStatus] = uint32_t(Result::WindowExpired);
        return;
    }
    const auto secondResult = sample(clock, interface, second);
    out[SecondStatus] = uint32_t(secondResult);
    if (secondResult != Result::Observed) return;

    const uint32_t finish = now();
    if (finish < start || finish - start < kWindowMs || finish - start > kMaxWindowMs) {
        out[SecondStatus] = uint32_t(Result::WindowExpired);
        return;
    }
    out[SecondMs] = finish;
    out[SecondIntfFrames] = second.intfFrames;
    out[SecondMdpFrames] = second.mdpFrames;
    out[SecondTearCount] = second.tearCount;
    out[SecondLineCount] = second.lineCount;

    auto checkRouteClock = [&](uint32_t (&state)[ZornDisplayTiming318::Words]) {
        using namespace ZornDisplayClockRead334;
        uint32_t raw[ZornDisplayClockRead334::Words]{};
        if (checkedClock(clock, raw) != Result::Observed) return DpuResult::UnstablePower;
        state[ZornDisplayTiming318::GccAhb] = raw[GccAhbAfter];
        state[ZornDisplayTiming318::CoreDomain] = raw[Domain];
        state[ZornDisplayTiming318::CoreDomainConfig] = raw[DomainConfig];
        state[ZornDisplayTiming318::AhbClock] = raw[Ahb];
        state[ZornDisplayTiming318::MdpClock] = raw[Mdp];
        state[ZornDisplayTiming318::VsyncClock] = raw[Vsync];
        return DpuResult::Observed;
    };
    namespace Handoff = ZornDpuHandoff321;
    uint32_t route[Handoff::Words]{};
    Handoff::sampleChecked(checkRouteClock, mdp, finish, gop, stride, route);
    out[RouteStatus] = route[Handoff::Status];
    out[GopAddress] = gop;
    out[GopStride] = stride;
    if (route[Handoff::Status] != uint32_t(DpuResult::Observed)) return;
    out[ActiveCtl] = route[Handoff::DisplayCtlMask];
    out[ActiveFetch] = route[Handoff::ActiveFetchMask];
    for (unsigned i = 0; i < Handoff::CtlCount * Handoff::CtlWords; ++i) {
        out[CtlStart + i] = route[Handoff::CtlStart + i];
    }
    for (unsigned i = 0; i < Handoff::PipeCount; ++i) {
        const unsigned at = Handoff::PipeStart + i * Handoff::PipeWords;
        out[PipeStart + 2 * i] = route[at];
        out[PipeStart + 2 * i + 1] = route[at + 2];
    }
}

} // namespace ZornDisplayHeldTiming335
