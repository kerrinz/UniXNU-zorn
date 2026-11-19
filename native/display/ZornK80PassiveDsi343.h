// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornDpuAutoRefreshTransfer340.h"
#include "ZornGopWriterEpoch343.h"
#include "ZornPassiveFrameOwnership.h"

namespace ZornK80PassiveDsi343 {

namespace Auto = ZornDpuAutoRefreshTransfer340;
namespace Cmd = Auto::Cmd;
namespace Stamp = ZornGopWriterEpoch343;
namespace Ownership = ZornPassiveFrameOwnership;

enum class State { ConfigUnavailable, CannotArm, Interrupted, Complete };
struct Report {
    State state = State::ConfigUnavailable;
    uint32_t interfaceAdvances = 0, freshDsi = 0, unbound = 0, changed = 0, repeated = 0, first = 0;
    uint32_t pollingGaps = 0;
    uint64_t elapsedUs = 0;
    bool retain = false;
};

// The board owner has already verified CTL0/VIG0/VIG1, the live Apps SMMU
// route, and the DSI0 controller. This observer never starts a transfer.
template<class Port, class Source, class Note>
Report observe(Port &port, const Source &source, uint64_t intervalUs, Note note)
{
    constexpr uint64_t pollLimit = 3500;
    Report out;
    uint32_t tearEn = 0, dsi = 0, config = 0, underruns = 0;
    if (!intervalUs || intervalUs > 8000000 || !port.lease() ||
        !port.readIntf(Cmd::AutoRefreshConfig, config) || config != Auto::InheritedAutoConfig ||
        !port.readIntf(Cmd::UnderrunCount, underruns) ||
        !port.readTear(Auto::TearEnable, tearEn) || (tearEn & Auto::TearDoneMask) ||
        !port.readDsi(Cmd::DsiInterrupt, dsi) || (dsi & (Cmd::DsiError | Cmd::DsiDoneEnabled))) return out;
    const uint32_t dsiMask = dsi & Cmd::DsiEnableMask;
    auto epoch = [&](const Stamp::Frame &row) {
        return Ownership::Epoch{row.epoch, row.signature, row.qualified()};
    };
    uint32_t foundTear = 0, foundDsi = 0;
    auto sample = [&](Ownership::Poll &poll) {
        poll = {};
        poll.beginUs = port.nowUs();
        poll.before = epoch(source.poll());
        uint32_t latestEn = 0, latestUnderruns = 0;
        if (!port.lease() || !port.readTear(Auto::TearEnable, latestEn) || latestEn != tearEn ||
            !port.readIntf(Cmd::AutoRefreshConfig, config) || config != Auto::InheritedAutoConfig ||
            !port.readIntf(Cmd::UnderrunCount, latestUnderruns) || latestUnderruns != underruns ||
            !port.readTear(Auto::TearStatus, foundTear) ||
            !port.readIntf(Auto::WriteLine, poll.writeLine) ||
            !port.readDsi(Cmd::DsiInterrupt, foundDsi) || (foundDsi & Cmd::DsiError) ||
            (foundDsi & Cmd::DsiEnableMask) != dsiMask ||
            !port.readIntf(Cmd::InterfaceFrames, poll.interfaceFrames)) return false;
        poll.kickoff = foundTear & Auto::AutoKickoff;
        poll.writePointer = foundTear & Auto::WritePointerIrq;
        poll.done = foundDsi & Cmd::DsiDone;
        poll.after = epoch(source.poll());
        poll.endUs = port.nowUs();
        return true;
    };
    auto acknowledge = [&] {
        const uint32_t tear = foundTear & Auto::TearDoneMask;
        return (!tear || port.writeTear(Auto::TearClear, tear)) &&
            (!(foundDsi & Cmd::DsiDone) || port.writeDsi(Cmd::DsiInterrupt, dsiMask | Cmd::DsiDone));
    };
    out.state = State::CannotArm;
    Ownership::Poll quiet;
    uint32_t busy = 0;
    if (!sample(quiet) || !port.readIntf(Cmd::AutoRefreshStatus, busy) || busy) return out;
    if (!acknowledge() || !sample(quiet) || quiet.kickoff || quiet.writePointer || quiet.done) {
        out.retain = true;
        return out;
    }
    Ownership::Pending pending(pollLimit);
    pending.begin(quiet);
    const uint64_t start = quiet.endUs;
    const uint32_t firstCount = quiet.interfaceFrames;
    out.state = State::Interrupted;
    bool invalid = false, started = false;
    uint64_t prev = start;
    for (unsigned polls = 0; polls < 8100; ++polls) {
        port.delayMs(1);
        Ownership::Poll present;
        if (!sample(present) || present.beginUs < prev || present.endUs < present.beginUs) {
            out.retain = started;
            return out;
        }
        out.elapsedUs = present.endUs - start;
        started |= present.kickoff || present.writePointer;
        const uint32_t advances = present.interfaceFrames - firstCount;
        if (advances > 2048u) {
            out.retain = started;
            return out;
        }
        out.interfaceAdvances = advances;
        if (present.endUs - prev > pollLimit) ++out.pollingGaps;
        prev = present.endUs;
        const auto status = invalid ? Ownership::Result::InvalidBoundary : pending.observe(present);
        invalid |= status == Ownership::Result::InvalidBoundary;
        if (present.done) {
            ++out.freshDsi;
            switch (status) {
                case Ownership::Result::CompleteFirst: ++out.first; break;
                case Ownership::Result::CompleteRepeated: ++out.repeated; break;
                case Ownership::Result::CompleteChanged: ++out.changed; break;
                default: ++out.unbound; break;
            }
            note(present, status);
            if (!acknowledge() || !sample(quiet) || quiet.kickoff || quiet.writePointer || quiet.done) {
                out.retain = true;
                return out;
            }
            pending.begin(quiet);
            started = invalid = false;
            prev = quiet.endUs;
        }
        if (out.elapsedUs >= intervalUs && !started) {
            out.state = State::Complete;
            return out;
        }
        if (out.elapsedUs >= intervalUs + 50000) {
            out.retain = true;
            return out;
        }
    }
    out.retain = started;
    return out;
}

} // namespace ZornK80PassiveDsi343
