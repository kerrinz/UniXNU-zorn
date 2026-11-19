#include "ZornGopWriterReservation350.h"
#include <cassert>
#include <thread>

int main()
{
    ZornGopWriterReservation350::Reservation request;
    assert(!request.writerShouldYield(1));
    assert(!request.begin(99, 100));
    assert(!request.begin(100, 100));
    assert(request.begin(250, 100));
    std::thread boundary([&] {
        assert(request.writerShouldYield(101));
        assert(!request.begin(400, 100));
        assert(!request.finish(245));
        assert(request.writerShouldYield(249));
        assert(!request.writerShouldYield(250));
        assert(!request.writerShouldYield(260));
    });
    boundary.join();
    assert(request.finish(250));
    assert(!request.finish(250));
    assert(request.begin(500, 260));
    assert(!request.finish(250));
    assert(request.writerShouldYield(267));
    assert(request.finish(500));
    assert(!request.writerShouldYield(270));
}
