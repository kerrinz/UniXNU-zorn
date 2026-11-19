// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiScenePlan269.h"
namespace ZornUiTap275 {
using Outcome=ZornUiScene269::Outcome;
using Result=ZornUiScene269::Result;
struct Config {uint16_t x,y;uint32_t gapMs,holdMs,budgetMs;};
// Parameterized from the existing Done272 wait/contact/lift path. The caller
// selects an observed target;this helper grants no GPU or resource authority.
// Any attempted contact is followed by one lift,including a failed callback.
template<class Backend> Result run(Backend &io,const Config &c){
    Result r;
    if(c.x>32767 || c.y>32767 || !c.holdMs || c.gapMs>=c.budgetMs ||
       c.holdMs>=c.budgetMs-c.gapMs)return r;
    const auto start=io.nowMs();
    const auto age=[&](){const auto now=io.nowMs();return now>=start?now-start:UINT64_MAX;};
    for(;;){
        const auto elapsed=age();
        if(elapsed>=c.budgetMs){r.outcome=Outcome::Deadline;return r;}
        if(!io.ready())return r;
        if(elapsed>=c.gapMs)break;
        const auto remain=c.gapMs-elapsed;
        io.sleepMs(uint32_t(remain<250?remain:250));
    }
    // A real readiness callback may consume time:recheck before touching down.
    if(age()>=c.budgetMs){r.outcome=Outcome::Deadline;return r;}
    r.outcome=Outcome::Complete;const auto begin=io.nowMs();
    ZornContacts::Frame contact{};contact.count=1;contact.points[0].x=c.x;contact.points[0].y=c.y;
    contact.points[0].strength=1;contact.points[0].id=ZornUiScene269::Identity;
    r.attempted=1;r.firstRaw=io.send(contact);r.returned=1;
    if(r.firstRaw)r.outcome=Outcome::Dispatch;
    else {const auto elapsed=age();
        if(elapsed>=c.budgetMs)r.outcome=Outcome::Deadline;
        else {const auto left=c.budgetMs-elapsed;io.sleepMs(uint32_t(left<c.holdMs?left:c.holdMs));}}
    ZornContacts::Frame lift{};r.liftAttempted=1;r.liftRaw=io.send(lift);
    if(r.liftRaw){if(!r.firstRaw)r.firstRaw=r.liftRaw;r.outcome=Outcome::Dispatch;}
    else if(r.outcome==Outcome::Complete && age()>=c.budgetMs)r.outcome=Outcome::Deadline;
    const auto end=io.nowMs();const auto duration=end>=begin?end-begin:UINT64_MAX;
    r.elapsedMs=duration>UINT32_MAX?UINT32_MAX:uint32_t(duration);return r;
}
}
