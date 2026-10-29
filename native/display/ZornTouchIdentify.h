// SPDX-License-Identifier: BSD-2-Clause-Patent
// Bounded physical SPI ID test; no HID, controller configuration or firmware upload.
#pragma once
#include "ZornFt3683Wire.h"
struct ZornTouchIdBus {
    IODeviceMemory *memory[6]={};IOMemoryMap *maps[6]={};
    uintptr_t pins[6]={};uint32_t cfg[6]={},io[6]={};bool changed=false;
    uint32_t gpi[8]={};unsigned failure=0;
    unsigned cooperateEvery=0;
    __attribute__((noinline)) void afterByte(unsigned bytes) {
        if(cooperateEvery && bytes%cooperateEvery==0)IOSleep(1);
    }
    uint32_t read(unsigned i,unsigned offset) {
        uint32_t value=*reinterpret_cast<volatile uint32_t *>(pins[i]+offset);
        __asm__ volatile("dmb oshld" ::: "memory");return value;
    }
    void write(unsigned i,unsigned offset,uint32_t value) {
        if(i>=6 || (offset!=0 && offset!=4) || !pins[i])panic("zorn touch GPIO boundary");
        *reinterpret_cast<volatile uint32_t *>(pins[i]+offset)=value;
        __asm__ volatile("dsb osh" ::: "memory");
    }
    void set(unsigned i,unsigned value) {
        if(i!=1 && i!=2 && i!=3 && i!=4)panic("zorn touch output boundary");
        write(i,4,(read(i,4)&~2u)|(value?2u:0));
    }
    unsigned sample(){return read(0,4)&1;}
    void delay(unsigned us){
        // Sub-millisecond bit timing must not block the CPU0 thread for every
        // GPIO edge. Long reset/sample waits retain the scheduler's delay.
        if(us>1000){IODelay(us);return;}
        uint64_t start=0,now=0,hz=0;
        __asm__ volatile("mrs %0,cntfrq_el0\n\tisb\n\tmrs %1,cntpct_el0":"=r"(hz),"=r"(start));
        if(!hz || hz>1000000000)panic("zorn touch counter frequency");
        uint64_t ticks=(hz*us+999999)/1000000;
        do {__asm__ volatile("isb\n\tmrs %0,cntpct_el0":"=r"(now));}while(now-start<ticks);
    }
    bool transfer(const uint8_t *tx,uint8_t *rx,unsigned n){return ZornFt::transfer(*this,tx,rx,n);}
    // Only AP dynamic GPI instances2/3 from the live FDT are inspected. Never
    // reset an engine or steal an active DMA channel. No GPI writes exist.
    bool idleGpi() {
        unsigned at=0;
        for(unsigned instance=2;instance<=3;++instance) {
            uint32_t pa=0xa00000+0x10000+0x4000*instance;
            IODeviceMemory *m=IODeviceMemory::withRange(pa,4096);
            IOMemoryMap *map=m?m->map():nullptr;
            bool ok=map && map->getPhysicalAddress()==pa && map->getLength()==4096;
            if(ok)for(unsigned channel=0;channel<2;++channel) {
                uintptr_t base=map->getVirtualAddress()+channel*0x80;
                uint32_t config=*reinterpret_cast<volatile uint32_t *>(base);
                uint32_t scratch=*reinterpret_cast<volatile uint32_t *>(base+0x60);
                __asm__ volatile("dmb oshld" ::: "memory");
                gpi[at++]=config;gpi[at++]=scratch;
                if(!ZornFt::gpiIdle(config,scratch))ok=false;
            }
            OSSafeReleaseNULL(map);OSSafeReleaseNULL(m);if(!ok)return false;
        }
        return true;
    }
    unsigned prepare(const ZornTouch::Snapshot &s) {
        if(s.result || ((s.se[0]>>8)&255)!=1 || (s.se[2]&0x1001) ||
           (s.se[4]&0xfffffff) || (s.se[5]&0x1ffffff) || (s.se[6]&3))return failure=10;
        if(!idleGpi())return failure=11;
        for(unsigned i=0;i<6;++i) {
            uint32_t pa=0xf100000+ZornTouch::pins[i]*0x1000;
            memory[i]=IODeviceMemory::withRange(pa,4096);maps[i]=memory[i]?memory[i]->map():nullptr;
            if(!maps[i] || maps[i]->getPhysicalAddress()!=pa || maps[i]->getLength()!=4096)return failure=12;
            pins[i]=maps[i]->getVirtualAddress();cfg[i]=read(i,0);io[i]=read(i,4);
            if(cfg[i]!=s.config[i] || !ZornFt::pinOwned(cfg[i]))return failure=13;
        }
        changed=true;
        // Set output latches before directions: mode0 clock, inactive CS, reset low.
        set(1,1);set(2,0);set(3,1);set(4,0);
        for(unsigned i=0;i<6;++i) {
            uint32_t desired=ZornFt::gpioConfig(i,cfg[i]);
            write(i,0,desired);if(read(i,0)!=desired)return failure=14;
        }
        delay(10000);set(4,1);delay(200000);
        return 0;
    }
    bool restore() {
        bool ok=true;
        if(changed) {
            set(3,1);set(2,0);
            for(unsigned i=0;i<6;++i) {
                if(i!=0 && i!=5){write(i,4,io[i]);if((read(i,4)&2)!=(io[i]&2))ok=false;}
                write(i,0,cfg[i]);if(read(i,0)!=cfg[i])ok=false;
            }
            changed=false;
        }
        for(unsigned i=0;i<6;++i){OSSafeReleaseNULL(maps[i]);OSSafeReleaseNULL(memory[i]);pins[i]=0;}
        return ok;
    }
};
static void zornTouchIdentify(const ZornTouch::Snapshot &s,char *report,size_t length) {
    ZornTouchIdBus bus;
    unsigned error=bus.prepare(s),count=0;uint8_t values[3]={};
    const uint8_t commands[3]={0xa3,0x9f,0xa6};ZornFt::ReadResult results[3]={};
    if(!error)for(unsigned i=0;i<3;++i) {
        unsigned status=ZornFt::readIdentity(bus,commands[i],values[i],results[i]);
        ++count;if(status){error=20+status;break;}
    }
    unsigned irq=bus.changed?(bus.read(5,4)&1):2;
    bool restored=bus.restore();if(!restored && !error)error=15;
    bool identified=!error && values[0]==0x36 && values[1]==0x83;
    int n=snprintf(report,length,"TOUCHID err=%u id=%02x%02x fw=%02x match=%u count=%u restored=%u irq=%u GPI=",error,values[0],values[1],values[2],identified,count,restored,irq);
    for(unsigned i=0;i<8 && n>0 && (size_t)n<length;++i)n+=snprintf(report+n,length-n,"%x/",bus.gpi[i]);
    for(unsigned i=0;i<count && n>0 && (size_t)n<length;++i) {
        n+=snprintf(report+n,length-n," R%02x:%u:%u:",commands[i],results[i].error,results[i].attempts);
        for(auto v:results[i].raw)if(n>0 && (size_t)n<length)n+=snprintf(report+n,length-n,"%02x",v);
    }
    if(n<=0 || (size_t)n>=length)panic("zorn touch ID report overflow");
}
