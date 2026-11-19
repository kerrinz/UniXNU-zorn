#include "ZornScanoutLive348.h"
#include <cassert>

namespace L = ZornScanoutLive348;
namespace D = L::Dpu;
namespace C = D::Cmd;
constexpr uint32_t front = ZORN_SCANOUT_FRONT, back = ZORN_SCANOUT_BACK;

struct Port {
    uint32_t source0 = front, source1 = front, flush = 0, frames = UINT32_MAX;
    uint32_t config = uint32_t(D::Mode::FourTe), line = 1, tear = 8, dsi = 4;
    uint32_t framePolls = 0, writes = 0;
    uint64_t now = 100000;
    bool withhold = false, wrongCounter = false, failSecondAddress = false;
    bool lease() const { return true; }
    bool readMdp(uint32_t off, uint32_t &word) {
        switch (off) {
        case 0: word = 0xa0000000; break;
        case C::CtlTop: word = 0x20000; break;
        case C::CtlIntfActive: word = 2; break;
        case C::CtlFetchActive: word = 0x30000; break;
        case C::CtlStart: word = 0; break;
        case C::CtlFlush: word = flush; break;
        case C::Vig0Source: word = source0; break;
        case C::Vig1Source: word = source1; break;
        case C::Vig0Stride: case C::Vig1Stride: word = ZORN_SCANOUT_STRIDE; break;
        default: return false;
        }
        return true;
    }
    bool readIntf(uint32_t off, uint32_t &word) {
        switch (off) {
        case C::AutoRefreshConfig: word = config; break;
        case C::AutoRefreshStatus: case C::UnderrunCount: word = 0; break;
        case C::InterfaceFrames: word = frames; break;
        case D::WriteLine: word = line; break;
        default: return false;
        }
        return true;
    }
    bool readTear(uint32_t off, uint32_t &word) {
        if (off != D::TearEnable && off != D::TearStatus) return false;
        word = off == D::TearStatus ? tear : 0;
        return true;
    }
    bool readDsi(uint32_t off, uint32_t &word) {
        switch (off) {
        case 0: word = 0x20080000; break;
        case 4: word = 0x1f5; break;
        case 0xa8: word = 0x1f1f; break;
        case C::DsiInterrupt: word = dsi; break;
        default: return false;
        }
        return true;
    }
    bool writeMdp(uint32_t off, uint32_t word) {
        ++writes;
        switch (off) {
        case C::Vig0Source: source0 = word; return true;
        case C::Vig1Source: if (failSecondAddress) return false; source1 = word; return true;
        case C::CtlFlush: flush = word; framePolls = 0; return true;
        default: return false;
        }
    }
    bool writeTear(uint32_t off, uint32_t word) {
        assert(off == D::TearClear && word == D::TearDoneMask);
        tear &= ~word;
        return true;
    }
    bool writeDsi(uint32_t off, uint32_t word) {
        assert(off == C::DsiInterrupt && word == C::DsiDone);
        dsi &= ~word;
        return true;
    }
    uint64_t nowUs() const { return now; }
    void delayMs(unsigned ms) {
        now += ms * 1000;
        ++framePolls;
        if (withhold) return;
        if (framePolls == 31) {
            flush = 0;
            tear |= D::TearDoneMask;
            line = 3011;
        } else if (framePolls == 33) {
            frames += wrongCounter ? 2 : 1;
            dsi |= C::DsiDone;
            line = 1;
        }
    }
};

int main()
{
    Port port;
    L::Ownership buffers;
    uint32_t report[D::Words]{};
    assert(L::present(port, buffers, 1, 501, back, 90000, 98000, report));
    assert(buffers.shown().to == back && buffers.shown().completed == 133000 && port.frames == 0);
    assert(buffers.writableAddress() == front && report[D::DsiUs] == 33001 && report[D::FrameDelta] == 1);
    assert(!L::present(port, buffers, 1, 501, front, 133000, 133000, report));
    assert(port.writes == 3 && buffers.shown().sequence == 1);
    assert(L::present(port, buffers, 2, 502, front, 125000, 133000, report));
    assert(buffers.originalRestored() && buffers.shown().completed == 166000 && port.writes == 6);
    assert(buffers.shown().completed - buffers.shown().queued == 41000);

    for (unsigned scenario = 0; scenario < 4; ++scenario) {
        port = {};
        buffers = {};
        if (scenario == 0) port.config = D::InheritedAutoConfig;
        port.withhold = scenario == 1;
        port.wrongCounter = scenario == 2;
        port.failSecondAddress = scenario == 3;
        assert(!L::present(port, buffers, 1, 501, back, 90000, 98000, report));
        assert(!buffers.shown().sequence);
        assert(buffers.uncertain() == (scenario != 0));
        assert(buffers.writableAddress() == (scenario == 0 ? back : 0));
        assert(port.writes == (scenario == 0 ? 0 : scenario == 3 ? 2 : 3));
        if (scenario == 1) assert(port.now == 200000 && report[D::Status] == D::Timeout);
        if (scenario == 2) assert(report[D::FrameDelta] == 2 && report[D::Retain] == 1);
        if (scenario == 3) {
            assert(port.source0 == back && port.source1 == front && report[D::Retain] == 1);
            assert(!L::present(port, buffers, 2, 502, back, 90000, 98000, report) && port.writes == 2);
        }
    }
}
