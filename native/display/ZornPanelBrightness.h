// SPDX-License-Identifier: BSD-2-Clause-Patent
// K80 O11 board mapping and logging. No panel/PHY reset or clock changes.
#include "ZornDsiBrightness.h"
extern "C" int zorn_ufs_brightness_finish(const char *,unsigned,int);
struct ZornBrightnessBus {
    volatile uint32_t *registers;
    uint64_t frequency;
    static uint64_t counter() {
        uint64_t value;
        __asm__ volatile("isb\n\tmrs %0, cntpct_el0":"=r"(value)::"memory");
        return value;
    }
    uint32_t read(unsigned offset) {
        uint32_t value=registers[offset/4];
        __asm__ volatile("dsb sy" ::: "memory");
        return value;
    }
    void write(unsigned offset,uint32_t value) {
        registers[offset/4]=value;
        __asm__ volatile("dsb sy" ::: "memory");
    }
    void delay(unsigned us) {
        // IODelay can assert_wait/thread_block before idle latency is known.
        // DSI's <=10ms individual waits use the invariant hardware counter.
        uint64_t start=counter(),ticks=(frequency*us+999999)/1000000;
        while(counter()-start<ticks) __asm__ volatile("yield" ::: "memory");
    }
};
static char zornBrightnessResult[200];
extern "C" void zorn_brightness_checkpoint() {
    if (zornBrightnessResult[0])
        zorn_ufs_user_output(0,zornBrightnessResult,strlen(zornBrightnessResult));
}
static void zornPanelBrightnessProbe()
{
    unsigned request = 0;
    if (!PE_parse_boot_argn("zorn_brightness", &request, sizeof(request)) || !request)
        return;
    PE_Video video = {};
    unsigned watchdog=0;
    PE_parse_boot_argn("zorn_wdt",&watchdog,sizeof(watchdog));
    if (request > 4 || watchdog!=1 || !videoValid(video)) {
        if (!zorn_ufs_brightness_finish("BL bad arguments/video/watchdog",request,0))
            panic("zorn brightness refused unsafe context");
        return;
    }
    IODeviceMemory *memory = IODeviceMemory::withRange(0x0ae94000, 0x1000);
    IOMemoryMap *map = memory ? memory->map(kIOMapInhibitCache) : nullptr;
    if (!map || !map->getVirtualAddress() || map->getPhysicalAddress() != 0x0ae94000 ||
        map->getLength() != 0x1000) {
        if (!zorn_ufs_brightness_finish("BL map failed",request,0))
            panic("zorn brightness map failure could not be recorded");
        OSSafeReleaseNULL(map);
        OSSafeReleaseNULL(memory);
        return;
    }
    static const unsigned offsets[] = {
        0x000, 0x004, 0x008, 0x00c, 0x03c, 0x048, 0x04c, 0x050,
        0x068, 0x084, 0x0a8, 0x0ac, 0x0b4, 0x0c0, 0x110, 0x11c,
        0x120, 0x15c, 0x1dc, 0x1f4, 0x2cc, 0x330
    };
    uint64_t frequency;
    __asm__ volatile("mrs %0, cntfrq_el0":"=r"(frequency));
    if (!frequency || frequency>1000000000) {
        if (!zorn_ufs_brightness_finish("BL invalid ARM counter frequency",request,0))
            panic("zorn brightness invalid counter");
        return;
    }
    ZornBrightnessBus bus{reinterpret_cast<volatile uint32_t *>(map->getVirtualAddress()),frequency};
    bool success=true;
    if (request==1) {
        char line[240];
        size_t used=snprintf(line,sizeof(line),"BLPROBE ctrl0=ae94000");
        for (unsigned offset:offsets) {
            if (used+16>=sizeof(line)) {
                zorn_ufs_user_output(0,line,used);
                used=snprintf(line,sizeof(line),"BLMORE");
            }
            used+=snprintf(line+used,sizeof(line)-used," %03x=%08x",offset,bus.read(offset));
        }
        zorn_ufs_user_output(0,line,used);
    } else {
        char gates[160];
        int n=snprintf(gates,sizeof(gates),
            "BLGATE tpg=%08x fifo=%08x ver=%08x secure=%08x split=%08x ",
            bus.read(0x15c),bus.read(0x1dc),bus.read(0x1f4),bus.read(0x2cc),bus.read(0x330));
        zorn_ufs_user_output(0,gates,n);
        ZornBrightness::Panel<ZornBrightnessBus> panel(bus);
        bool ok=panel.run(request==ZornBrightness::DimProbe?ZornBrightness::Dim:request);
        success=ok;
        snprintf(zornBrightnessResult,sizeof(zornBrightnessResult),
            "BL mode=%u ok=%u err=%u old=%u target=%u got=%u writes=%u reads=%u int=%08x ack=%08x tout=%08x cnt=%u raw=%08x ",
            request,ok,panel.error,panel.before,panel.target,panel.after,panel.writes,panel.readbacks,
            panel.interrupt,panel.ack,panel.timeouts,panel.count,panel.response);
    }
    OSSafeReleaseNULL(map);
    OSSafeReleaseNULL(memory);
    // Short qualification exits immediately; no early-boot sleeping hold.
    if (!zorn_ufs_brightness_finish(request==1?"BL register snapshot complete":zornBrightnessResult,request,success))
        panic("zorn brightness result could not be committed");
}
