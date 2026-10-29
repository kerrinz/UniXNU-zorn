// SPDX-License-Identifier: BSD-2-Clause-Patent
// Default-off CPU0 polling bring-up; no controller firmware or OS writes.
#pragma once
#ifndef ZORN_TOUCH_RUNTIME_ENABLED
#define ZORN_TOUCH_RUNTIME_ENABLED 0
#endif
#if ZORN_TOUCH_RUNTIME_ENABLED
#include "ZornTouchContacts.h"
#include "ZornTouchTrace.h"
#include "ZornTouchPacing.h"
extern "C" uint32_t zorn_touch_trace_words[ZornTouchTrace::Words];
#include <kern/thread.h>
// Same private declaration as pinned XNU kern/thread.h; not exposed to IOKit headers.
extern "C" void thread_terminate_self(void);
extern "C" kern_return_t kernel_thread_start_priority(thread_continue_t,void *,integer_t,thread_t *);
extern "C" int zorn_touch_hid_publish(void);
extern "C" int zorn_touch_hid_send(const ZornContacts::Frame *);
extern "C" void zorn_touch_hid_observe(void);
extern "C" volatile uint32_t zorn_touch_hid_stats[8];
extern "C" volatile uint32_t zorn_touch_edge_stats[8];
namespace ZornTouchRuntime {
struct Session {
    static void *operator new(size_t,void *memory){return memory;}
    ZornTouchIdBus bus;
    ZornContacts::Detector detector;
    ZornTouchTrace::Recorder trace;
    ZornTouchPacing::Settings pacing;
    bool traceEnabled=false;
    uint64_t traceEpoch=0;
    ZornFt::MatrixFrameResult packet;
    uint64_t frequency=0,deadline=0,lastLog=0;
    unsigned stage=0,error=0,reads=0,bad=0,decoded=0,contacts=0,irq=0;
    unsigned x=0,y=0,consecutive=0;
};
alignas(Session) static uint8_t sessionBytes[sizeof(Session)];
static Session *session;
static uint64_t counter(){uint64_t v;__asm__ volatile("isb\n\tmrs %0,cntpct_el0":"=r"(v));return v;}
static void snapshot() {
    auto &s=*session;
    zorn_touch_runtime_stats[0]=s.stage | (uint64_t(s.error)<<32);
    zorn_touch_runtime_stats[1]=s.reads;zorn_touch_runtime_stats[2]=s.bad;
    zorn_touch_runtime_stats[3]=s.decoded;zorn_touch_runtime_stats[4]=s.contacts;
    zorn_touch_runtime_stats[5]=s.x;zorn_touch_runtime_stats[6]=s.y;
    zorn_touch_runtime_stats[7]=s.detector.peak | (uint64_t(s.detector.noise)<<32);
    zorn_touch_runtime_stats[8]=s.irq;
    if(s.frequency)zorn_touch_runtime_stats[9]=counter()/(s.frequency/1000);
    // Words10/11 are written by HID, including while publication is blocked.
}
static void report() {
    zorn_touch_hid_observe();
    snapshot();char text[240];auto &s=*session;
    int n=snprintf(text,sizeof(text),"TCH st=%u e=%u n=%u bad=%u dec=%u cnt=%u x=%u y=%u peak=%u noise=%u irq=%u pri=81 poll=%u bytes=1504 yield=%u HID=%u/%u/%u/%08x ED=%u/%u/%u/%u KP=%u HE=%u RS=%x CL=%x",
        s.stage,s.error,s.reads,s.bad,s.decoded,s.contacts,s.x,s.y,s.detector.peak,s.detector.noise,s.irq,s.pacing.pollMs,s.pacing.cooperateBytes,
        zorn_touch_hid_stats[0],zorn_touch_hid_stats[1],zorn_touch_hid_stats[2],zorn_touch_hid_stats[3],
        zorn_touch_edge_stats[0],zorn_touch_edge_stats[5],zorn_touch_edge_stats[6],zorn_touch_edge_stats[7],
        zorn_touch_hid_stats[5],zorn_touch_hid_stats[4],zorn_touch_hid_stats[6],zorn_touch_hid_stats[7]);
    if(n>0 && (size_t)n<sizeof(text))zorn_ufs_user_output(0,text,static_cast<size_t>(n));
}
static uint32_t traceMs() {return uint32_t((counter()-session->traceEpoch)/(session->frequency/1000));}
static void worker(void *,wait_result_t) {
    auto &s=*session;s.stage=4;snapshot();
    while(counter()<s.deadline) {
        ++s.reads;if(!(s.bus.read(5,4)&1))++s.irq;snapshot();
        unsigned rc=ZornFt::readMatrixFrame(s.bus,s.packet);ZornContacts::Frame frame={};
        if(rc || !s.detector.decode(s.packet.raw+7,frame)) {
            ++s.bad;++s.consecutive;s.error=rc?40+rc:50;
            if(s.traceEnabled)s.trace.sample({},traceMs(),false);
            if(s.consecutive>=3){ZornContacts::Frame release={};(void)zorn_touch_hid_send(&release);s.detector.previous={};if(s.traceEnabled)s.trace.release(traceMs(),1);}
            if(s.consecutive>=10)break;
        } else {
            s.consecutive=0;s.error=0;++s.decoded;s.contacts=frame.count;
            if(s.traceEnabled)s.trace.sample(frame,traceMs());
            if(frame.count){s.x=frame.points[0].x;s.y=frame.points[0].y;}
            s.stage=7;snapshot();(void)zorn_touch_hid_send(&frame);s.stage=4;
        }
        if(s.traceEnabled)s.trace.publish(zorn_touch_trace_words);
        snapshot();uint64_t now=counter();if(now-s.lastLog>=s.frequency*10){s.lastLog=now;report();}
        IOSleep(s.pacing.pollMs); // Keep a bounded sleep even in the explicit faster profile.
    }
    ZornContacts::Frame release={};(void)zorn_touch_hid_send(&release);
    if(s.traceEnabled){s.trace.release(traceMs(),2);s.trace.publish(zorn_touch_trace_words);}
    if(!s.bus.restore() && !s.error)s.error=15;
    s.stage=5;report();thread_terminate_self();
}
static void start() {
    unsigned mode=0;if(!PE_parse_boot_argn("zorn_touch",&mode,sizeof(mode)) || mode!=6 || session)return;
    session=new(sessionBytes)Session;
    auto &s=*session;s.stage=1;snapshot();unsigned watchdog=0,hid=0;
    if(!PE_parse_boot_argn("zorn_wdt",&watchdog,sizeof(watchdog)) || watchdog!=1 || !PE_parse_boot_argn("zorn_hid_family",&hid,sizeof(hid)) || hid!=1){s.error=1;s.stage=6;report();return;}
    __asm__ volatile("mrs %0,cntfrq_el0":"=r"(s.frequency));
    if(s.frequency<1000 || s.frequency>1000000000){s.frequency=0;s.error=31;report();return;}
    ZornTouchReadBus reader;ZornTouch::Snapshot snapshot;ZornTouch::capture(reader,snapshot);
    s.stage=21;ZornTouchRuntime::snapshot();s.error=s.bus.prepare(snapshot);
    uint8_t ids[3]={};const uint8_t commands[3]={0xa3,0x9f,0xa6};ZornFt::ReadResult id={};
    s.stage=22;ZornTouchRuntime::snapshot();
    if(!s.error)for(unsigned i=0;i<3;++i){unsigned rc=ZornFt::readIdentity(s.bus,commands[i],ids[i],id);if(rc){s.error=20+rc;break;}}
    if(!s.error && (ids[0]!=0x36 || ids[1]!=0x83 || ids[2]!=0x35))s.error=30;
    s.stage=23;ZornTouchRuntime::snapshot();
    unsigned faster=0;PE_parse_boot_argn("zorn_touch_fast",&faster,sizeof(faster));
    unsigned traceMode=0,smpMode=0;
    if(faster==1 && (!PE_parse_boot_argn("zorn_touch_trace",&traceMode,sizeof(traceMode)) || traceMode!=1 ||
        !PE_parse_boot_argn("zorn_smp_continue",&smpMode,sizeof(smpMode)) || smpMode!=1) && !s.error)s.error=35;
    if(!ZornTouchPacing::select(faster,s.pacing) && !s.error)s.error=34;
    s.bus.cooperateEvery=s.pacing.cooperateBytes;
    if(!s.error)for(unsigned i=0;i<12 && s.detector.baselines<8;++i){if(!ZornFt::readMatrixFrame(s.bus,s.packet))s.detector.add(s.packet.raw+7);IOSleep(50);}
    if(!s.error && s.detector.baselines<4)s.error=33;
    s.stage=24;ZornTouchRuntime::snapshot();
    if(!s.error && !zorn_touch_hid_publish())s.error=60;
    if(s.error){s.bus.restore();s.stage=6;report();return;}
    unsigned hold=0;PE_parse_boot_argn("zorn_gui_hold",&hold,sizeof(hold));
    if(hold<180)hold=180;if(hold>1800)hold=1800;
    s.lastLog=counter();s.deadline=s.lastLog+s.frequency*(hold+120);s.stage=3;
    unsigned trace=0;PE_parse_boot_argn("zorn_touch_trace",&trace,sizeof(trace));
    s.traceEnabled=trace==1;s.traceEpoch=s.lastLog;
    if(s.traceEnabled)s.trace.publish(zorn_touch_trace_words);
    // Driver priority avoids starvation. Explicit1ms yields remain after
    // 8 (legacy) or32 bytes (faster), with100/20ms between frames respectively.
    thread_t thread=THREAD_NULL;kern_return_t rc=kernel_thread_start_priority(worker,nullptr,81,&thread); // pinned XNU BASEPRI_KERNEL
    if(rc){s.error=61;s.stage=6;s.bus.restore();report();return;}
    thread_deallocate(thread);report();
}
}

#else
namespace ZornTouchRuntime {static void start() {}}
#endif
