// SPDX-License-Identifier: BSD-2-Clause-Patent
// Explicit short read-only touch/display handoff test, followed by recovery.
#pragma once
#include "ZornTouchHandoff.h"
#include "ZornTouchIdentify.h"
#include "ZornTouchFrames.h"
extern "C" int zorn_ufs_touch_probe_finish(const char *);
extern "C" int zorn_ufs_touch_raw_finish(const char *,const uint8_t *,unsigned);
struct ZornTouchReadBus {
    bool read(uint32_t physical,uint32_t &value) {
        if(!ZornTouch::allowed(physical))return false;
        const uint32_t page=physical&~0xfffu;
        IODeviceMemory *memory=IODeviceMemory::withRange(page,4096);
        IOMemoryMap *map=memory?memory->map():nullptr;
        bool ok=map && map->getPhysicalAddress()==page && map->getLength()==4096;
        if(ok) {
            value=*reinterpret_cast<volatile uint32_t *>(map->getVirtualAddress()+(physical-page));
            __asm__ volatile("dsb sy" ::: "memory");
        }
        OSSafeReleaseNULL(map);OSSafeReleaseNULL(memory);return ok;
    }
};
static void zornTouchProbe(void) {
    unsigned mode=0,watchdog=0;
    if(!PE_parse_boot_argn("zorn_touch",&mode,sizeof(mode)) || !mode)return;
    if(mode==6)return; // long-lived driver is started after the display publishes
    if((mode<1 || mode>5) || !PE_parse_boot_argn("zorn_wdt",&watchdog,sizeof(watchdog)) || watchdog!=1)
        panic("zorn touch probe requires exact mode/watchdog");
    PE_Video v={};if(!videoValid(v))panic("zorn touch probe display identity differs");
    ZornTouchReadBus bus;ZornTouch::Snapshot s;ZornTouch::capture(bus,s);
    char report[512];
    if(mode>=2) {
        if(mode>=3)zornTouchFrames(s,report,sizeof(report),mode>=4,mode==5);
        else zornTouchIdentify(s,report,sizeof(report));
        if(mode>=4) {
            if(!zorn_ufs_touch_raw_finish(report,zornTouchCapturedRaw,zornTouchCapturedBytes))panic("zorn full touch log unavailable");
            panic("zorn full touch recovery returned");
        }
        if(!zorn_ufs_touch_probe_finish(report))panic("zorn touch ID log unavailable");
        panic("zorn touch ID recovery returned");
    }
    int n=snprintf(report,sizeof(report),"TOUCHRO rc=%u reads=%u clk=%08x/%08x/%08x/%08x ",s.result,s.reads,s.clock[0],s.clock[1],s.clock[2],s.clock[3]);
    for(unsigned i=0;i<6 && n>0 && (size_t)n<sizeof(report);++i)
        n+=snprintf(report+n,sizeof(report)-n,"g%u=%x/%x ",ZornTouch::pins[i],s.config[i],s.io[i]);
    if(n>0 && (size_t)n<sizeof(report))n+=snprintf(report+n,sizeof(report)-n,
        "SE=%x/%x/%x/%x/%x/%x/%x DSI=%x/%x/%x/%x/%x/%x/%x/%x/%x ",
        s.se[0],s.se[1],s.se[2],s.se[3],s.se[4],s.se[5],s.se[6],
        s.dsi[0],s.dsi[1],s.dsi[2],s.dsi[3],s.dsi[4],s.dsi[5],s.dsi[6],s.dsi[7],s.dsi[8]);
    if(n<=0 || (size_t)n>=sizeof(report))panic("zorn touch probe report overflow");
    if(!zorn_ufs_touch_probe_finish(report))panic("zorn touch probe log unavailable");
    panic("zorn touch probe recovery returned");
}
