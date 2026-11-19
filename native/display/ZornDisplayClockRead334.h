// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornDisplayClockRead334 {

enum class Bank : uint8_t { Gcc, DispCc };
enum Field : unsigned {
    Status, GccAhbBefore, GccAxi, Domain, DomainConfig,
    Ahb, Mdp, Vsync, GccAhbAfter, Words
};
enum State : uint32_t {
    NotRun, GccUnavailable, InterfaceVoteAbsent, DispCcUnavailable,
    InterfaceVoteChanged, Sampled
};

// Relative to the two checked K80 GCC and DISP_CC resource windows.
// The GCC probe enables the interface clock at 0x27004 through bit 0.
// SDE_KMS uses a separate GCC AXI vote at 0x2700c.
inline constexpr uint32_t kGccAhb = 0x04;
inline constexpr uint32_t kGccAxi = 0x0c;
inline constexpr uint32_t kSoftwareEnable = 1u;

inline constexpr bool interfaceVoted(uint32_t word)
{
    return (word & kSoftwareEnable) != 0;
}

// Called only inside the actual MMCX, MX and SDE register-bus lease.
// The stock DISP_CC initialization uses this software interface vote.
// A controller snapshot never grants DPU/DSI or scanout access.
template <typename Read>
void sampleUnderLease(Read &read, uint32_t (&out)[Words])
{
    for (auto &value : out) value = 0;
    if (!read(Bank::Gcc, kGccAhb, out[GccAhbBefore]) ||
        !read(Bank::Gcc, kGccAxi, out[GccAxi])) {
        out[Status] = GccUnavailable;
        return;
    }
    if (!interfaceVoted(out[GccAhbBefore])) {
        out[Status] = InterfaceVoteAbsent;
        return;
    }

    constexpr Field fields[] = {Domain, DomainConfig, Ahb, Mdp, Vsync};
    constexpr uint32_t offsets[] = {0x1000, 0x1004, 0x00a4, 0x000c, 0x0024};
    for (unsigned i = 0; i < sizeof(fields) / sizeof(fields[0]); ++i) {
        if (!read(Bank::DispCc, offsets[i], out[fields[i]])) {
            out[Status] = DispCcUnavailable;
            return;
        }
    }
    if (!read(Bank::Gcc, kGccAhb, out[GccAhbAfter])) {
        out[Status] = GccUnavailable;
        return;
    }
    out[Status] = interfaceVoted(out[GccAhbAfter]) ? Sampled : InterfaceVoteChanged;
}

} // namespace ZornDisplayClockRead334
