#include "ZornGopLiveSession348.h"
#include <cassert>
#include <vector>

int main()
{
    namespace Gop = ZornGopLiveSession348;
    const ZornScanoutFlipOwnership348::Ownership::Frame frame{
        2, 502, ZORN_SCANOUT_BACK, ZORN_SCANOUT_FRONT, 125000, 133000, 133000, 166000
    };
    uint32_t wire[Gop::T::Words]{};
    Gop::record(wire, frame);
    assert(wire[Gop::T::Completed] == 1 && wire[Gop::T::TimingLost] == 0);
    assert(wire[Gop::T::Frames] == 502 && wire[Gop::T::Frames + 1] == 125000);
    assert(wire[Gop::T::Frames + 2] == 166000 && wire[Gop::T::Frames + 3] == (8250u << 16));

    std::vector<uint64_t> visible(ZORN_SCANOUT_BYTES / sizeof(uint64_t), 0xdeadbeefcafedeadull);
    std::vector<uint64_t> target(visible.size());
    visible.front() = 123;
    visible.back() = 456;
    Gop::seed(reinterpret_cast<uint8_t *>(target.data()), reinterpret_cast<const uint8_t *>(visible.data()));
    assert(target == visible);
}
