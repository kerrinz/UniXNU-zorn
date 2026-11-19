// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornPanelTe320 {

// Live zorn FDT: primary DSI TE at TLMM GPIO86. Pineapple pinctrl:
// TLMM + 0x100000 + 0x1000 * 86, mux selector 1 = mdp_vsync.
inline constexpr uint64_t Address = 0x0f156000;
inline constexpr unsigned RegisterBytes = 8;
inline constexpr unsigned SampleUs = 160000;
inline constexpr unsigned PollUs = 10;
inline constexpr unsigned PollLimit = SampleUs / PollUs + 1;
inline constexpr unsigned EdgeLimit = 32;

enum Index : unsigned {
    Status, StartUptimeMs, InitialCtl, FinalCtl, ElapsedUs, Polls, MaxGapUs,
    FallingEdges, FirstEdgeUs, Words = FirstEdgeUs + EdgeLimit
};

enum class Outcome : uint32_t {
    NotRun, NoPresentation, ReadUnavailable, UnexpectedPad, PadChanged,
    Incomplete, Observed
};

inline bool isTearingInput(uint32_t ctl)
{
    constexpr unsigned muxMask = 0xf << 2;
    constexpr unsigned mdpVsync = 1 << 2;
    constexpr unsigned outputEnable = 1 << 9;
    constexpr unsigned egpioPresent = 1 << 11;
    constexpr unsigned localEnable = 1 << 12;
    return (ctl & (muxMask | outputEnable)) == mdpVsync &&
           (!(ctl & egpioPresent) || (ctl & localEnable));
}

// The caller owns a preemptible worker and read-only mapping. Hold the
// existing mux stable and record the raw falling edges seen by the vendor
// TE interrupt. A missed short pulse is possible between reads.
template <typename Read, typename Time, typename Delay>
void sample(Read &read, Time &nowUs, Delay &delay, bool presented, uint32_t (&out)[Words])
{
    for (auto &word : out) word = 0;
    out[Status] = uint32_t(Outcome::NoPresentation);
    if (!presented) return;

    out[Status] = uint32_t(Outcome::ReadUnavailable);
    if (!read(0, out[InitialCtl])) return;
    if (!isTearingInput(out[InitialCtl])) {
        out[Status] = uint32_t(Outcome::UnexpectedPad);
        return;
    }

    const uint64_t start = nowUs();
    out[StartUptimeMs] = uint32_t(start / 1000);
    uint32_t last = 0;
    uint32_t prev = 0;
    unsigned polls = 0;
    unsigned edges = 0;
    auto outcome = Outcome::Incomplete;
    for (; polls < PollLimit; ++polls) {
        uint32_t io = 0;
        if (!read(4, io)) {
            outcome = Outcome::ReadUnavailable;
            break;
        }
        const uint64_t when = nowUs();
        if (when < start || when - start < last || when - start > UINT32_MAX) break;
        const uint32_t elapsed = uint32_t(when - start);
        const uint32_t gap = elapsed - last;
        if (gap > out[MaxGapUs]) out[MaxGapUs] = gap;
        last = elapsed;
        if (polls && (prev & 1) && !(io & 1)) {
            if (edges == EdgeLimit) break;
            out[FirstEdgeUs + edges++] = elapsed;
        }
        prev = io;
        if (elapsed >= SampleUs) {
            ++polls;
            outcome = Outcome::Observed;
            break;
        }
        delay(PollUs);
    }

    out[ElapsedUs] = last;
    out[Polls] = polls;
    out[FallingEdges] = edges;
    if (!read(0, out[FinalCtl])) {
        outcome = Outcome::ReadUnavailable;
    } else if (out[FinalCtl] != out[InitialCtl]) {
        outcome = Outcome::PadChanged;
    }
    out[Status] = uint32_t(outcome);
}

} // namespace ZornPanelTe320
