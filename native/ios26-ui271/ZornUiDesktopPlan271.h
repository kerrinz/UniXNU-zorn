// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "ZornUiScenePlan269.h"
namespace ZornUiDesktop271 {
using Outcome=ZornUiScene269::Outcome;
using Result=ZornUiScene269::Result;
enum : uint32_t { X=28330,Y=3938,Reports=6,IntervalMs=400,SettleMs=30000,BudgetMs=70000 };
struct Scene {Result swipe,press;};
// Coordinates are the visually identified actual270 Settings gear sample35,25
// in its720x1600 upper-right ROI of1440x3200. Not a foreign board parameter.
// Returned void dispatch is not queue delivery,Settings-menu or FT3683 proof.
template<class Backend> Scene run(Backend &io){
    Scene s;const uint64_t start=io.nowMs();
    const auto age=[&](){const auto now=io.nowMs();return now>=start?now-start:UINT64_MAX;};
    s.swipe=ZornUiScene269::run(io);
    if(s.swipe.outcome!=Outcome::Complete)return s;
    const auto settled=age();
    while(age()-settled<SettleMs){
        const auto elapsed=age();
        if(elapsed>=BudgetMs){s.press.outcome=Outcome::Deadline;return s;}
        if(!io.ready())return s;
        const auto remain=SettleMs-(elapsed-settled);
        io.sleepMs(uint32_t(remain<250?remain:250));
    }
    s.press.outcome=Outcome::Complete;
    const uint64_t pressStart=io.nowMs();
    for(unsigned i=0;i<Reports;++i){
        if(age()>=BudgetMs){s.press.outcome=Outcome::Deadline;break;}
        if(!io.ready()){s.press.outcome=Outcome::NoClient;break;}
        ZornContacts::Frame frame{};frame.count=1;
        frame.points[0].x=X;frame.points[0].y=Y;
        frame.points[0].strength=1;frame.points[0].id=ZornUiScene269::Identity;
        ++s.press.attempted;const auto raw=io.send(frame);++s.press.returned;
        if(raw){s.press.firstRaw=raw;s.press.outcome=Outcome::Dispatch;break;}
        const auto elapsed=age();
        if(elapsed>=BudgetMs){s.press.outcome=Outcome::Deadline;break;}
        io.sleepMs(uint32_t(BudgetMs-elapsed<IntervalMs?BudgetMs-elapsed:IntervalMs));
    }
    if(s.press.attempted){
        ZornContacts::Frame lift{};s.press.liftAttempted=1;s.press.liftRaw=io.send(lift);
        if(s.press.liftRaw){if(!s.press.firstRaw)s.press.firstRaw=s.press.liftRaw;s.press.outcome=Outcome::Dispatch;}
    }
    const auto end=io.nowMs();const auto elapsed=end>=pressStart?end-pressStart:UINT64_MAX;
    s.press.elapsedMs=elapsed>UINT32_MAX?UINT32_MAX:uint32_t(elapsed);return s;
}
}
