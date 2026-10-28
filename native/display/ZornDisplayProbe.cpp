// SPDX-License-Identifier: BSD-2-Clause-Patent
// Board glue for the canonical GopFramebuffer CPU path. Original Apple
// dispatch and code stay unchanged. Based on the sheng lifecycle example.
#include "OriginalLegacyFramebufferABI.h"
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IODeviceMemory.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOUserClient.h>
#include <libkern/c++/OSSymbol.h>
#include <libkern/c++/OSData.h>
#include <kern/task.h>
#include <sys/proc.h>
#include <mach/kmod.h>
#include <pexpert/pexpert.h>

extern "C" {
extern kmod_info_t g_kernel_kmod_info;
kern_return_t OSKextLoadKextWithIdentifier(const char *);
void native_legacy_display_static_init(void) __asm__("__GLOBAL__sub_I_NativeLegacyDisplay.cpp");
IOService *native_legacy_display_allocate(void);
void zorn_say(const char *);
void zorn_keystore_state_probe(void);
void zorn_hid_services_probe(void);
int zorn_ufs_log_ready(void);
int zorn_ufs_display_summary(unsigned, unsigned, unsigned, int);
void zorn_ufs_user_output(unsigned, const char *, size_t);
volatile uint64_t zorn_display_stats[32];
}
static bool requested, initialized, scanoutClaimed;
static unsigned mode;
static IOService *activeDisplay;
static bool videoValid(PE_Video &v) {
    return !PE_current_console(&v) && v.v_baseAddr==0xfc400000 &&
        v.v_width==1440 && v.v_height==3200 && v.v_rowBytes==5760 &&
        v.v_depth==32 && !v.v_rotate && v.v_display==1;
}
static void number(const char *tag,uint64_t value) {
    char word[12];snprintf(word,sizeof(word),"%s%08X",tag,(unsigned)value);zorn_say(word);
}
#include "ZornPanelBrightness.h"
#include "ZornTouchProbe.h"
static void checkpoint(bool mayWait=true) {
    (void)zorn_ufs_display_summary((unsigned)zorn_display_stats[0],(unsigned)zorn_display_stats[1],
                                 (unsigned)zorn_display_stats[2],mayWait);
}
extern "C" __attribute__((noreturn)) void native_legacy_backend_guard(unsigned slot,void *,void *caller) {
    zorn_display_stats[0]=0x100+slot;zorn_display_stats[1]=(uint32_t)kIOReturnUnsupported;
    checkpoint(false);number("DSC",(uintptr_t)caller);
    panic("zorn display: unsupported original backend slot %u",slot);
}
extern "C" bool native_legacy_gop_mapping_observed(IOService *,IOMemoryMap *map,uint32_t w,uint32_t h) {
    PE_Video video={};
    bool valid=videoValid(video) && w==video.v_width && h==video.v_height && map &&
        map->getPhysicalAddress()==video.v_baseAddr && map->getVirtualAddress() &&
        map->getLength()==video.v_rowBytes*video.v_height;
    zorn_display_stats[4]=valid;number("DSM",valid);return valid;
}
extern "C" void native_legacy_registration_observed(IOService *display) {
    zorn_display_stats[5]=zorn_display_stats[5]+1;zorn_display_stats[6]=((display->getState() & kIOServiceRegisteredState)!=0);zorn_say("DSPREG");
}
extern "C" void native_legacy_swap_stage(unsigned stage) {zorn_display_stats[7]=stage;}
extern "C" void native_legacy_client_enter(task_t task,uint32_t type) {
    zorn_display_stats[8]=zorn_display_stats[8]+1;zorn_display_stats[9]=type;
    zorn_display_stats[10]=task?static_cast<uint32_t>(proc_pid((proc_t)get_bsdtask_info(task))):0;
}
extern "C" void native_legacy_client_observed(IOReturn status,IOUserClient *client) {
    zorn_display_stats[11]=static_cast<uint32_t>(status);zorn_display_stats[12]=(uintptr_t)client;
    if(zorn_display_stats[8]<=8) {number("DCP",zorn_display_stats[10]);number("DCE",static_cast<uint32_t>(status));}
}
extern "C" void native_legacy_pm_observed(unsigned stage,IOReturn status,unsigned long ordinal) {
    zorn_display_stats[13]=stage;zorn_display_stats[14]=static_cast<uint32_t>(status);zorn_display_stats[15]=ordinal;
}
extern "C" void native_legacy_surface_rejected(uint64_t w,uint64_t h,uint32_t format,uint32_t planes,uint64_t stride,uint64_t allocation,uint64_t bytes) {
    zorn_display_stats[16]=w;zorn_display_stats[17]=h;zorn_display_stats[18]=format;
    zorn_display_stats[19]=planes;zorn_display_stats[20]=stride;zorn_display_stats[21]=allocation;zorn_display_stats[22]=bytes;
}
extern "C" void native_legacy_swap_validation_observed(bool accepted,unsigned reason,const void *,const void *) {
    if(accepted)zorn_display_stats[23]=zorn_display_stats[23]+1;else zorn_display_stats[24]=zorn_display_stats[24]+1;
    if(zorn_display_stats[23]+zorn_display_stats[24]<=8) {number("DSA",accepted);number("DSR",reason);}
}
extern "C" void native_legacy_frame_observed(unsigned kind,uint64_t count,uint64_t,uint64_t,uint64_t,uint64_t) {
    zorn_display_stats[25]=kind;zorn_display_stats[26]=count;
}
extern "C" void native_legacy_frame_colors_observed(const uint32_t *colors,const uint64_t *,uint64_t other) {
    zorn_display_stats[27]=colors?colors[0]:0;zorn_display_stats[28]=other;
}
extern "C" bool native_legacy_prepare_scanout(void) {
    PE_Video video={};int logOnly=0;
    if(!videoValid(video) || !PE_parse_boot_argn("zorn_log_only",&logOnly,sizeof(logOnly)) || logOnly!=1)return false;
    if(!scanoutClaimed) {
        if(PE_initialize_console(nullptr,kPEDisableScreen))return false;
        scanoutClaimed=true;
    }
    return true;
}
extern "C" void native_legacy_transfer_observed(IOReturn status,const void *,uint64_t bytes) {
    zorn_display_stats[29]=zorn_display_stats[29]+1;zorn_display_stats[30]=static_cast<uint32_t>(status);zorn_display_stats[31]=bytes;
    if(zorn_display_stats[29]<=8) {number("DFR",zorn_display_stats[29]);number("DFE",static_cast<uint32_t>(status));number("DFB",bytes);}
}
extern "C" void native_legacy_copy_timing_observed(uint64_t ticks,uint64_t bytes) {
    static unsigned count;
    if(count++<4) {number("DFT",ticks);number("DCF",bytes);}
}
extern "C" bool native_legacy_gpu_offer(void *,IOMemoryDescriptor *,uint64_t,uint32_t,uint32_t) {
    // No GPU transport is registered on zorn. The canonical caller falls back
    // to its real CPU copy; this refusal never reports GPU completion.
    return false;
}
extern "C" void native_legacy_gpu_fallback_observed(int status) {number("DGF",static_cast<uint32_t>(status));}
extern "C" void native_legacy_retirement_observed(IOService *) {
    static unsigned count;if(count++<8)zorn_say("DFDONE");
}
extern "C" void native_legacy_vsync_observed(unsigned event,unsigned hz) {
    static unsigned count;if(count++<8) {number("DVE",event);number("DVH",hz);}
}
static const OSMetaClass *lookup(const char *text) {
    const OSSymbol *name=OSSymbol::withCString(text);
    const OSMetaClass *meta=name?OSMetaClass::getMetaClassWithName(name):nullptr;
    OSSafeReleaseNULL(name);return meta;
}
extern "C" void native_legacy_display_probe(void) {
    // Called before the board UFS logger. Defer construction until IOBSD and
    // the independent recovery watchdog are available.
    requested=true;
}
extern "C" void native_legacy_display_late_probe(void) {
    if(!zorn_ufs_log_ready())return;
    if(initialized || !PE_parse_boot_argn("zorn_display",&mode,sizeof(mode)) || !mode)return;
    initialized=true;
    zornTouchProbe();
    zornPanelBrightnessProbe();
    zorn_keystore_state_probe();
    zorn_hid_services_probe();
    zorn_display_stats[0]=1;zorn_display_stats[1]=(uint32_t)kIOReturnError;
    if(mode>2) {checkpoint();return;}
    number("DSQ",requested);
    kern_return_t loaded=OSKextLoadKextWithIdentifier("com.apple.iokit.IOMobileGraphicsFamily");
    number("DSL",static_cast<uint32_t>(loaded));
    if(loaded) {zorn_display_stats[1]=static_cast<uint32_t>(loaded);checkpoint();return;}
    const OSMetaClass *parent=lookup("IOMobileFramebufferLegacy");
    if(!parent || parent!=&IOMobileFramebufferLegacy::gMetaClass || parent->getClassSize()!=0x18a0) {checkpoint();return;}
    zorn_display_stats[2]=parent->getClassSize();
    void *handle=OSMetaClass::preModLoad(g_kernel_kmod_info.name);
    if(!handle) {checkpoint();return;}
    native_legacy_display_static_init();
    zorn_display_stats[1]=static_cast<uint32_t>(OSMetaClass::postModLoad(handle));
    if(zorn_display_stats[1]) {checkpoint();return;}
    PE_Video video={};zorn_display_stats[0]=2;
    if(!videoValid(video)) {zorn_display_stats[1]=(uint32_t)kIOReturnBadArgument;checkpoint();return;}
    IOService *display=native_legacy_display_allocate();
    if(!display) {zorn_display_stats[1]=(uint32_t)kIOReturnNoMemory;checkpoint();return;}
    if(!display->metaCast("IOMobileFramebufferLegacy") || !display->metaCast("IOMobileFramebuffer") || !display->metaCast("IOService")) {
        zorn_display_stats[1]=(uint32_t)kIOReturnBadArgument;display->release();checkpoint();return;
    }
    zorn_display_stats[0]=3;zorn_display_stats[3]=display->getMetaClass()->getClassSize();
    if(!display->init()) {zorn_display_stats[1]=(uint32_t)kIOReturnNotReady;display->release();checkpoint();return;}
    if(mode==1) {
        display->release();zorn_display_stats[0]=4;zorn_display_stats[1]=0;checkpoint();zorn_say("DSPINIT");return;
    }
    zorn_display_stats[0]=5;
    kern_return_t result=OSKextLoadKextWithIdentifier("com.apple.iokit.IOSurface");
    OSDictionary *matching=IOService::nameMatching("IOCoreSurfaceRoot");
    IOService *surface=!result && matching?IOService::waitForMatchingService(matching,5000000000ULL):nullptr;
    OSSafeReleaseNULL(matching);
    if(!surface) {display->release();zorn_display_stats[1]=result?static_cast<uint32_t>(result):static_cast<uint32_t>(kIOReturnNotFound);checkpoint();return;}
    surface->release();
    IOPlatformDevice *nub=new IOPlatformDevice;
    IOService *home=IOService::getResourceService();
    IODeviceMemory *memory=IODeviceMemory::withRange(video.v_baseAddr,video.v_rowBytes*video.v_height);
    OSArray *ranges=OSArray::withCapacity(1);
    IORegistryEntry *dt=IORegistryEntry::fromPath("/arm-io",gIODTPlane);
    bool nubAttached=false,nubStarted=false,dtAttached=false,attached=false,started=false;
    if(nub && memory && ranges && dt && home && nub->init()) {
        ranges->setObject(memory);nub->setDeviceMemory(ranges);nub->setName("ZornGOPFramebuffer");
        nubAttached=nub->attach(home);if(nubAttached)nubStarted=nub->start(home);
        const char type[]="display-subsystem";OSData *property=OSData::withBytes(type,sizeof(type));
        if(nubStarted && property && nub->setProperty("device_type",property)) {
            nub->setName("gop-display",gIODTPlane);dtAttached=nub->attachToParent(dt,gIODTPlane);
        }
        OSSafeReleaseNULL(property);
        SInt32 score=0;
        if(dtAttached && display->probe(nub,&score)==display)attached=display->attach(nub);
        zorn_display_stats[0]=6;
        if(attached)started=display->start(nub);
    }
    number("DSB",started);number("DSI",display->getState());
    bool published=false;
    if(started && zorn_display_stats[4]) {
        OSDictionary *match=IOService::registryEntryIDMatching(display->getRegistryEntryID());
        IOService *found=match?IOService::waitForMatchingService(match,5000000000ULL):nullptr;
        published=found==display && (display->getState() & kIOServiceRegisteredState)!=0;
        OSSafeReleaseNULL(found);OSSafeReleaseNULL(match);
        number("DSJ",display->getState());number("DSK",published);
    }
    if(published) {
        zorn_display_stats[6]=1;
        activeDisplay=display;zorn_display_stats[0]=10;zorn_display_stats[1]=0;
        OSSafeReleaseNULL(memory);OSSafeReleaseNULL(ranges);OSSafeReleaseNULL(dt);
        checkpoint();zorn_say("DSPOK");return;
    }
    if(started)display->stop(nub);
    if(attached)display->detach(nub);
    if(dtAttached)nub->detachFromParent(dt,gIODTPlane);
    if(nubStarted)nub->stop(home);
    if(nubAttached)nub->detach(home);
    OSSafeReleaseNULL(memory);OSSafeReleaseNULL(ranges);OSSafeReleaseNULL(dt);OSSafeReleaseNULL(nub);
    display->release();zorn_display_stats[1]=(uint32_t)kIOReturnNotReady;checkpoint();
}
