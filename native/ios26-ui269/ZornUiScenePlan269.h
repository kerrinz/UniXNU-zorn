// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stdint.h>
#include "ZornTouchTypes.h"

// A diagnostic display-coordinate gesture, never a physical FT3683 sample.
// Reuse the real iOS26 Frame -> IOHIDEvent path; do not encode HID fields here.
namespace ZornUiScene269 {
enum class Outcome : uint32_t { Complete=0, NoClient=1, Deadline=2, Dispatch=3 };
struct Result {
    Outcome outcome=Outcome::NoClient;
    uint32_t polls=0, attempted=0, returned=0, firstRaw=0;
    uint32_t liftAttempted=0, liftRaw=UINT32_MAX, elapsedMs=0;
};
enum : uint32_t { X=16384, StartY=32112, EndY=8192, Steps=16,
    IntervalMs=60, PollMs=250, ReadyMs=30000, BudgetMs=32000, Identity=1 };

// Backend calls are synchronous. ready() proves an open kernel HID subscriber,
// send()==0 only proves the real event-construction/void-dispatch calls returned.
// A source deadline stops new contacts/moves; one final empty frame is still
// attempted after ANY contact dispatch, including a partial failing dispatch.
// The independent hardware watchdog bounds a backend call that never returns.
template<class Backend> Result run(Backend &io) {
    Result r;
    const uint64_t start=io.nowMs();
    const auto age=[&]() -> uint64_t {const auto now=io.nowMs();return now>=start?now-start:UINT64_MAX;};
    bool ready=false;
    while(age()<ReadyMs) {
        ++r.polls;
        if(io.ready()){ready=true;break;}
        const uint64_t elapsed=age();
        if(elapsed>=ReadyMs)break;
        io.sleepMs(uint32_t(ReadyMs-elapsed<PollMs?ReadyMs-elapsed:PollMs));
    }
    if(ready) {
        r.outcome=Outcome::Complete;
        for(unsigned i=0;i<=Steps;++i) {
            if(age()>=BudgetMs){r.outcome=Outcome::Deadline;break;}
            if(!io.ready()){r.outcome=Outcome::NoClient;break;}
            ZornContacts::Frame frame{};frame.count=1;
            frame.points[0].x=X;
            frame.points[0].y=uint16_t(StartY-(uint64_t(StartY-EndY)*i)/Steps);
            frame.points[0].strength=1;frame.points[0].id=Identity;
            ++r.attempted;
            const uint32_t raw=io.send(frame);++r.returned;
            if(raw){r.firstRaw=raw;r.outcome=Outcome::Dispatch;break;}
            const uint64_t elapsed=age();
            if(elapsed>=BudgetMs){r.outcome=Outcome::Deadline;break;}
            io.sleepMs(uint32_t(BudgetMs-elapsed<IntervalMs?BudgetMs-elapsed:IntervalMs));
        }
    }
    if(r.attempted) {
        ZornContacts::Frame lift{};r.liftAttempted=1;
        r.liftRaw=io.send(lift);
        if(r.liftRaw) {
            if(!r.firstRaw)r.firstRaw=r.liftRaw;
            r.outcome=Outcome::Dispatch;
        }
    }
    const uint64_t elapsed=age();r.elapsedMs=elapsed>UINT32_MAX?UINT32_MAX:uint32_t(elapsed);
    return r;
}
}
