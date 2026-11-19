// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

extern "C" {
#include "GeniSpi.h"
}

namespace ZornFt3683GeniInventory26 {
constexpr uint32_t Engine = 0x00a90000;
constexpr uint32_t Wrapper = 0x00ac0000;
constexpr uint32_t Vote = 0x00152008;
constexpr uint32_t Votes = (1u << 20) | (1u << 21) | (1u << 26);
constexpr uint32_t Branches[] = {0x0012313c, 0x00123140, 0x001183bc};

enum State : uint32_t {
    None, ClockUnavailable, ReadUnavailable, Inconsistent, ProtocolMismatch,
    BusyOrDmaMode, FifoDisabled, UnsupportedFifo, FifoObserved
};
enum Field : unsigned {
    Status, ClockVote, WrapperVersion, Firmware, Interface, Sequencer,
    Geometry, DmaMode, TxFifo, RxFifo, ClockBranches, Words
};

inline bool allowed(uint32_t address)
{
    switch (address) {
    case Vote:
    case Branches[0]:
    case Branches[1]:
    case Branches[2]:
    case Wrapper + QUPV3_HW_VER_REG:
    case Engine + GENI_FW_REVISION_RO:
    case Engine + GENI_IF_DISABLE_RO:
    case Engine + SE_GENI_STATUS:
    case Engine + SE_HW_PARAM_0:
    case Engine + SE_GENI_DMA_MODE_EN:
    case Engine + SE_GENI_TX_FIFO_STATUS:
    case Engine + SE_GENI_RX_FIFO_STATUS:
        return true;
    }
    return false;
}

// The existing board owner serializes access before its GPIO preparation.
// The pinned firmware holds the rails and all three clocks. If the live
// clock readback differs, this probe does not read the engine or wrapper.
template<class Port>
void capture(Port &port, uint32_t (&data)[Words])
{
    for (auto &word : data) word = 0;
    data[Status] = ClockUnavailable;
    if (!port.read(Vote, data[ClockVote]) || data[ClockVote] == UINT32_MAX ||
        (data[ClockVote] & Votes) != Votes) return;
    for (unsigned i = 0; i < sizeof(Branches) / sizeof(Branches[0]); ++i) {
        uint32_t branch = 0;
        if (!port.read(Branches[i], branch) || branch == UINT32_MAX) return;
        data[ClockBranches] |= 1u << i;
        if (branch & (1u << 31)) {
            data[ClockBranches] |= 1u << (i + 8);
            return;
        }
    }

    struct Reader {
        Port &port;
        bool valid = true;
        uint32_t read(uint32_t address)
        {
            uint32_t value = 0;
            if (!valid || !port.read(address, value) || value == UINT32_MAX) {
                valid = false;
                return 0;
            }
            return value;
        }
    } reader{port};
    geni_spi engine{};
    engine.se.ctx = &reader;
    engine.se.rd = [](void *ctx, uint32_t reg) {
        return static_cast<Reader *>(ctx)->read(Engine + reg);
    };
    engine.wrapper.ctx = &reader;
    engine.wrapper.rd = [](void *ctx, uint32_t reg) {
        return static_cast<Reader *>(ctx)->read(Wrapper + reg);
    };

    data[Status] = ReadUnavailable;
    if (geni_spi_read_info(&engine) != 0 || !reader.valid) return;
    data[WrapperVersion] = engine.info.qup_hw_version;
    data[Firmware] = engine.info.fw_revision;
    data[Interface] = engine.info.if_disable;
    data[Sequencer] = engine.info.geni_status;
    data[Geometry] = engine.info.hw_param0;
    data[DmaMode] = reader.read(Engine + SE_GENI_DMA_MODE_EN);
    data[TxFifo] = reader.read(Engine + SE_GENI_TX_FIFO_STATUS);
    data[RxFifo] = reader.read(Engine + SE_GENI_RX_FIFO_STATUS);
    if (!reader.valid) return;

    const uint32_t after = reader.read(Engine + SE_GENI_STATUS);
    const uint32_t vote = reader.read(Vote);
    if (!reader.valid || after != data[Sequencer] || (vote & Votes) != Votes) {
        data[Status] = Inconsistent;
    } else if (engine.info.protocol != GENI_PROTO_SPI) {
        data[Status] = ProtocolMismatch;
    } else if ((after & 0x1001) || (data[DmaMode] & GENI_DMA_MODE_EN) ||
               (data[TxFifo] & 0xfffffff) || (data[RxFifo] & GENI_RX_WC_MASK)) {
        data[Status] = BusyOrDmaMode;
    } else if (engine.info.fifo_disabled) {
        data[Status] = FifoDisabled;
    } else if (!data[WrapperVersion] || engine.info.tx_fifo_depth < 4 || engine.info.fifo_width_bits != 32) {
        data[Status] = UnsupportedFifo;
    } else {
        data[Status] = FifoObserved;
    }
}
} // namespace ZornFt3683GeniInventory26
