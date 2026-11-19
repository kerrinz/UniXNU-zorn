#include "ZornScanoutPhase349.h"
#include <cassert>
#include <initializer_list>

int main()
{
    namespace P = ZornScanoutPhase349;
    constexpr auto micros = [](uint64_t time) { return time; };
    const ZornSwapPhases349 phase{1000, 7400, 13800, 20200, 26600, true};
    uint32_t row[P::RecordWords]{};
    P::pack(row, 9, phase, 33000, 39400, 12, 0, true, micros);
    assert(row[0] == 9 && row[1] == (100u | 100u << 16) && row[2] == row[1]);
    assert(row[3] == (100u | (12u | P::Valid | P::Gpu | P::Transferred) << 16));

    for (const auto drawStart : {uint64_t(1), uint64_t(33000)}) {
        for (auto &word : row) word = 0;
        P::pack(row, 10, phase, drawStart, 10000000, 8, 256, false, micros);
        assert(row[0] == 10 && !row[1] && !row[2]);
        assert(row[3] == ((8u | P::Gpu | 256u << P::GuardShift) << 16));
    }
}
