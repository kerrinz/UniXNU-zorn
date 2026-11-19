#include "ZornScanoutFlipOwnership348.h"
#include <cassert>

using ZornScanoutFlipOwnership348::Ownership;
constexpr uint32_t front = ZORN_SCANOUT_FRONT, back = ZORN_SCANOUT_BACK;

int main()
{
    Ownership pair;
    assert(pair.originalRestored() && pair.writableAddress() == back);
    assert(!pair.stage(1, 99, front, 100, 110));
    assert(pair.stage(1, 99, back, 100, 110));
    assert(!pair.writableAddress() && !pair.originalRestored());
    assert(!pair.program(2, 111) && !pair.program(1, 109));
    pair.rejectBeforeProgram(1);
    assert(pair.originalRestored() && pair.writableAddress() == back);
    assert(!pair.stage(1, 99, back, 100, 110));
    assert(pair.stage(2, UINT32_MAX, back, 120, 125));
    assert(pair.program(2, 126));
    pair.rejectBeforeProgram(2);
    assert(!pair.originalRestored() && !pair.writableAddress());
    assert(pair.complete(2, back, back, 1, true, 140));
    assert(pair.shown().sequence == 2 && pair.shown().swap == UINT32_MAX);
    assert(pair.shown().to == back && pair.shown().queued == 120 &&
           pair.shown().ready == 125 && pair.shown().programmed == 126 &&
           pair.shown().completed == 140);
    assert(!pair.originalRestored() && pair.writableAddress() == front);
    assert(!pair.complete(2, back, back, 1, true, 150));
    assert(pair.stage(3, 0, front, 130, 145) && pair.program(3, 146));
    assert(pair.complete(3, front, front, 1, true, 160));
    assert(pair.originalRestored() && pair.writableAddress() == back);

    for (unsigned fault = 0; fault < 7; ++fault) {
        Ownership held;
        assert(held.stage(1, 77, back, 100, 110));
        assert(held.program(1, 120));
        if (fault == 6) held.markUncertain();
        assert(!held.complete(fault == 0 ? 2 : 1, fault == 1 ? front : back,
                              fault == 2 ? front : back, fault == 3 ? 2 : 1,
                              fault != 4, fault == 5 ? 119 : 130));
        assert(held.uncertain() && !held.writableAddress() && !held.originalRestored());
        assert(!held.stage(2, 78, front, 130, 140) && !held.shown().sequence);
    }
}
