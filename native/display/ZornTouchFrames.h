// SPDX-License-Identifier: BSD-2-Clause-Patent
// Explicit finite raw touch acquisition. No HID publication or firmware writes.
#pragma once
static void zornTouchFrames(const ZornTouch::Snapshot &snapshot,char *report,size_t capacity) {
    ZornTouchIdBus bus;unsigned error=bus.prepare(snapshot);
    uint8_t ids[3]={};ZornFt::ReadResult idResult={};
    const uint8_t commands[3]={0xa3,0x9f,0xa6};
    if(!error)for(unsigned i=0;i<3;++i) {
        unsigned rc=ZornFt::readIdentity(bus,commands[i],ids[i],idResult);
        if(rc){error=20+rc;break;}
    }
    if(!error && (ids[0]!=0x36 || ids[1]!=0x83))error=30;
    uint8_t first[84]={},latest[84]={};
    unsigned reads=0,good=0,bad=0,changes=0,irqLow=0,lastError=0;
    if(!error) {
        zorn_say("TWAIT");
        uint64_t start=0,now=0,hz=0;
        __asm__ volatile("mrs %0,cntfrq_el0\n\tisb\n\tmrs %1,cntpct_el0":"=r"(hz),"=r"(start));
        if(!hz || hz>1000000000)error=31;
        else for(unsigned i=0;i<200;++i) {
            __asm__ volatile("isb\n\tmrs %0,cntpct_el0":"=r"(now));
            if(now-start>=hz*20)break;
            if(!(bus.read(5,4)&1))++irqLow;
            ZornFt::FrameResult frame={};++reads;
            lastError=ZornFt::readFrame(bus,frame);
            if(lastError)++bad;
            else {
                if(!good)memcpy(first,frame.raw+7,sizeof(first));
                else if(memcmp(latest,frame.raw+7,sizeof(latest)))++changes;
                memcpy(latest,frame.raw+7,sizeof(latest));++good;
            }
            bus.delay(100000);
        }
    }
    bool restored=bus.restore();if(!restored && !error)error=15;
    int n=snprintf(report,capacity,"TOUCHFR e=%u id=%02x%02x fw=%02x n=%u ok=%u bad=%u chg=%u irq=%u last=%u rst=%u F=",
        error,ids[0],ids[1],ids[2],reads,good,bad,changes,irqLow,lastError,restored);
    for(auto value:first)if(n>0 && (size_t)n<capacity)n+=snprintf(report+n,capacity-n,"%02x",value);
    if(n>0 && (size_t)n<capacity)n+=snprintf(report+n,capacity-n," L=");
    for(auto value:latest)if(n>0 && (size_t)n<capacity)n+=snprintf(report+n,capacity-n,"%02x",value);
    if(n<=0 || (size_t)n>=capacity)panic("zorn touch frame report overflow");
}
