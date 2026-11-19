// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiDesktopPlan271.h"
namespace ZornUiDone272 {
using Outcome=ZornUiScene269::Outcome;
using Result=ZornUiScene269::Result;
enum : uint32_t { X=28671,Y=1260,IntervalMs=100,GapMs=15000,BudgetMs=85000 };
struct Scene {ZornUiDesktop271::Scene initial;Result done;};
// Actual271 upper-right ROI sample36,8 is inside the observed Done-style pill.
// One bounded tap after the unchanged swipe/hold. Its visual effect must still
// be observed;returned dispatch never acknowledges userland event delivery.
template<class Backend> Scene run(Backend &io){
    Scene scene;const uint64_t start=io.nowMs();
    const auto age=[&](){const auto now=io.nowMs();return now>=start?now-start:UINT64_MAX;};
    scene.initial=ZornUiDesktop271::run(io);
    if(scene.initial.swipe.outcome!=Outcome::Complete || scene.initial.press.outcome!=Outcome::Complete)return scene;
    const uint64_t after=age();
    for(;;){
        const uint64_t elapsed=age();
        if(elapsed>=BudgetMs){scene.done.outcome=Outcome::Deadline;return scene;}
        if(!io.ready())return scene;
        if(elapsed>=after && elapsed-after>=GapMs)break;
        const uint64_t remain=elapsed>=after?GapMs-(elapsed-after):0;
        if(!remain){scene.done.outcome=Outcome::Deadline;return scene;}
        io.sleepMs(uint32_t(remain<250?remain:250));
    }
    Result &r=scene.done;
    if(age()>=BudgetMs){r.outcome=Outcome::Deadline;return scene;}
    r.outcome=Outcome::Complete;const auto begin=io.nowMs();
    ZornContacts::Frame contact{};contact.count=1;contact.points[0].x=X;contact.points[0].y=Y;
    contact.points[0].strength=1;contact.points[0].id=ZornUiScene269::Identity;
    r.attempted=1;r.firstRaw=io.send(contact);r.returned=1;
    if(r.firstRaw)r.outcome=Outcome::Dispatch;
    else {const auto elapsed=age();
        if(elapsed>=BudgetMs)r.outcome=Outcome::Deadline;
        else {const auto left=BudgetMs-elapsed;io.sleepMs(uint32_t(left<IntervalMs?left:IntervalMs));}}
    // Exactly one lift even if contact construction/dispatch partly failed or
    // its callback consumed the source deadline. Hardware WDT bounds a block.
    ZornContacts::Frame lift{};r.liftAttempted=1;r.liftRaw=io.send(lift);
    if(r.liftRaw){if(!r.firstRaw)r.firstRaw=r.liftRaw;r.outcome=Outcome::Dispatch;}
    else if(r.outcome==Outcome::Complete && age()>=BudgetMs)r.outcome=Outcome::Deadline;
    const auto end=io.nowMs();const auto duration=end>=begin?end-begin:UINT64_MAX;
    r.elapsedMs=duration>UINT32_MAX?UINT32_MAX:uint32_t(duration);return scene;
}
}
