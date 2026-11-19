// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornDisplaySmmu336 {

// Pineapple Apps SMMU qcom,handoff-smrs = <0x1c00 0x2> and the display's
// non-secure IOMMU specifier. This is the Apps SMMU retained by the UFS
// owner, separate from the GPU's privately managed SMMU.
inline constexpr uint32_t Sid[] = {0x1c00, 0x1c02};
inline constexpr uint32_t NoSlot = UINT32_MAX;
enum Status : uint32_t { NotRun, HostUnavailable, ReadFailed, Unsupported, Changed, Observed };
enum Mode : uint32_t { UnmatchedBypass = 1, UnmatchedFault, StreamBypass, StreamFault,
                       ContextBypass, Stage1Enabled, OtherContext };
enum Entry : unsigned { Route, Slot, Smr, S2cr, Cbar, Cba2r, Sctlr, Ttbr0Low, Ttbr0High, Tcr, EntryWords };
enum Field : unsigned { State, GlobalControl, Id0, Id1, Streams, Words = Streams + 2 * EntryWords };

template <typename Read>
Status scan(Read &read, uint32_t aperture, const uint32_t (&streams)[2], uint32_t (&out)[Words])
{
    if (!read(0, out[GlobalControl]) || !read(0x20, out[Id0]) || !read(0x24, out[Id1])) {
        return ReadFailed;
    }
    const uint32_t control = out[GlobalControl], id0 = out[Id0], id1 = out[Id1];
    const bool extended = control & (1u << 3);
    const unsigned count = id0 & 255u, banks = id1 & 255u;
    const unsigned pages = 1u << (((id1 >> 28) & 7u) + 1);
    const unsigned sidWidth = (id0 >> 9) & 15u;
    // Match the inherited K80 UFS owner's 4 KiB register frame layout and
    // retained aperture. Never visit a register bank outside that mapping.
    if ((control & 1u) || !(id0 & (1u << 27)) || !count || !banks ||
        (id1 & (1u << 31)) || pages < 2 || (pages + banks) * 4096u > aperture ||
        ((id1 >> 16) & 255u) > banks ||
        (!(id0 & (1u << 8)) && (extended || sidWidth < 13))) {
        return Unsupported;
    }
    for (unsigned n = 0; n < 2; ++n) out[Streams + n * EntryWords + Slot] = NoSlot;
    const uint32_t matchMask = extended ? 0xffffu : 0x7fffu;
    for (unsigned slot = 0; slot < count; ++slot) {
        uint32_t smr = 0, s2cr = 0;
        if (!read(0x800 + 4 * slot, smr) || !read(0xc00 + 4 * slot, s2cr)) return ReadFailed;
        if (!(extended ? s2cr & (1u << 10) : smr & (1u << 31))) continue;
        for (unsigned n = 0; n < 2; ++n) {
            if ((streams[n] ^ smr) & 0xffffu & ~((smr >> 16) & matchMask)) continue;
            auto *entry = out + Streams + n * EntryWords;
            if (entry[Slot] != NoSlot) return Unsupported;
            entry[Slot] = slot;
            entry[Smr] = smr;
            entry[S2cr] = s2cr;
        }
    }
    for (unsigned n = 0; n < 2; ++n) {
        auto *entry = out + Streams + n * EntryWords;
        if (entry[Slot] == NoSlot) {
            entry[Route] = control & (1u << 10) ? UnmatchedFault : UnmatchedBypass;
            continue;
        }
        const unsigned type = (entry[S2cr] >> 16) & 3u;
        if (type == 1 || type == 2) {
            entry[Route] = type == 1 ? StreamBypass : StreamFault;
            continue;
        }
        const unsigned bank = entry[S2cr] & 255u;
        if (type || bank >= banks) return Unsupported;
        const uint32_t offset = (pages + bank) * 4096u;
        if (!read(0x1000 + 4 * bank, entry[Cbar]) || !read(0x1800 + 4 * bank, entry[Cba2r]) ||
            !read(offset, entry[Sctlr]) || !read(offset + 0x20, entry[Ttbr0Low]) ||
            !read(offset + 0x24, entry[Ttbr0High]) || !read(offset + 0x30, entry[Tcr])) return ReadFailed;
        const unsigned context = (entry[Cbar] >> 16) & 3u;
        if (context == 1 && bank >= ((id1 >> 16) & 255u) && (id0 & (1u << 30))) {
            entry[Route] = entry[Sctlr] & 1u ? Stage1Enabled : ContextBypass;
        } else {
            entry[Route] = OtherContext;
        }
    }
    return Observed;
}

// Publish only a stable complete pair. This observes translation controls;
// it does not walk a page table or assert an IOVA resolves to the GOP PA.
template <typename Read>
void sample(Read &read, uint32_t aperture, const uint32_t (&streams)[2], uint32_t (&out)[Words])
{
    for (auto &word : out) word = 0;
    uint32_t first[Words]{}, second[Words]{};
    Status status = scan(read, aperture, streams, first);
    if (status == Observed) status = scan(read, aperture, streams, second);
    if (status == Observed) {
        for (unsigned i = 1; i < Words; ++i) {
            if (first[i] != second[i]) {
                status = Changed;
                break;
            }
        }
    }
    out[State] = status;
    if (status == Observed)
        for (unsigned i = 1; i < Words; ++i) out[i] = second[i];
}

template <typename Read>
void sample(Read &read, uint32_t aperture, uint32_t (&out)[Words])
{
    sample(read, aperture, Sid, out);
}

} // namespace ZornDisplaySmmu336
