// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornDisplayTiming318 {

enum class Window : uint8_t { Gcc, DisplayClock, Interface };

struct Range {
    uint64_t address;
    uint32_t bytes;
};

inline constexpr Range Windows[] = {
    {0x00127004, 4},       // GCC_DISP_AHB_CLK, gcc-pineapple.c
    {0x0af08000, 0x1008},  // MDSS branches, BCR and GDSCR/CFG_GDSCR
    {0x0ae36000, 0x300},   // DSI0's mdp_intf_base in the zorn live FDT
};

enum Field : unsigned {
    Status, UptimeMs, GccAhb, CoreDomain, CoreDomainConfig, AhbClock,
    MdpClock, VsyncClock, InterfaceStatus, TearEnable, TearReadCount,
    TearWriteLine, InterfaceFrameCount, MdpFrameCount, VideoLine, Words
};

enum class Result : uint32_t {
    NotObserved, NoPresentation, MissingMapping, ParentClockOff, DomainInactive,
    DisplayClockOff, UnstablePower, Observed, StoppedAfterFault
};

inline bool clockRunning(uint32_t branch)
{
    return (branch & 0x80000001) == 1;
}

// Check that the already running firmware display is accessible. This probe
// never votes for a clock or power domain. A hardware-controlled domain can
// lose its clocks between reads, so it is outside the probe's scope.
template <typename Read>
Result checkClockState(Read &read, uint32_t (&out)[Words])
{
    if (!read(Window::Gcc, 0, out[GccAhb])) return Result::MissingMapping;
    if (!clockRunning(out[GccAhb])) return Result::ParentClockOff;

    if (!read(Window::DisplayClock, 0x1000, out[CoreDomain]) ||
        !read(Window::DisplayClock, 0x1004, out[CoreDomainConfig])) {
        return Result::MissingMapping;
    }
    constexpr uint32_t powerOn = 1u << 31;
    constexpr uint32_t controlOrCollapse = 7u;
    constexpr uint32_t transition = (1u << 16) | (1u << 15);
    if ((out[CoreDomain] & (powerOn | controlOrCollapse)) != powerOn ||
        (out[CoreDomainConfig] & transition) != (1u << 16)) {
        return Result::DomainInactive;
    }

    uint32_t reset = 0;
    if (!read(Window::DisplayClock, 0, reset) ||
        !read(Window::DisplayClock, 0xa4, out[AhbClock]) ||
        !read(Window::DisplayClock, 0x0c, out[MdpClock]) ||
        !read(Window::DisplayClock, 0x24, out[VsyncClock])) {
        return Result::MissingMapping;
    }
    if ((reset & 1) || !clockRunning(out[AhbClock]) || !clockRunning(out[MdpClock]) ||
        !clockRunning(out[VsyncClock])) {
        return Result::DisplayClockOff;
    }
    return Result::Observed;
}

// Fixed register reads follow MiCode sde_hw_intf_get_vsync_info and the
// bounded observer in HoujiDisplayTiming.h. Retain the raw counters separately
// so a stopped command-mode engine is distinguishable from a running panel.
template <typename Read>
void sample(Read &read, bool presented, uint32_t stamp, uint32_t (&out)[Words], bool &stopped)
{
    for (auto &word : out) word = 0;
    out[UptimeMs] = stamp;
    if (stopped) {
        out[Status] = uint32_t(Result::StoppedAfterFault);
        return;
    }
    auto status = presented ? checkClockState(read, out) : Result::NoPresentation;
    if (status == Result::Observed) {
        constexpr uint32_t offsets[] = {0x26c, 0x284, 0x298, 0x2b0, 0xac, 0xa4, 0xb0};
        static_assert(sizeof(offsets) / sizeof(offsets[0]) == Words - InterfaceStatus);
        uint32_t counts[Words - InterfaceStatus]{};
        for (unsigned i = 0; i < Words - InterfaceStatus; ++i) {
            if (!read(Window::Interface, offsets[i], counts[i])) {
                status = Result::MissingMapping;
                break;
            }
        }
        if (status == Result::Observed) {
            uint32_t after[Words]{};
            if (checkClockState(read, after) == Result::Observed) {
                for (unsigned i = 0; i < Words - InterfaceStatus; ++i) out[InterfaceStatus + i] = counts[i];
            } else {
                status = Result::UnstablePower;
            }
        }
    }
    out[Status] = uint32_t(status);
    stopped = status == Result::MissingMapping || status == Result::UnstablePower;
}

} // namespace ZornDisplayTiming318
