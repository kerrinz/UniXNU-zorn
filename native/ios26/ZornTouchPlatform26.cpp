// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornTouchPlatform26.h"
#include "ZornTouchTrialSnapshot26.h"
#include "../../../board/zorn/platform-base/display/ZornTouchPacing.h"
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <IOKit/IOLib.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSSharedPtr.h>
#include "ZornGen7NativeDtEntry26.h"
#include <IOKit/IOKitKeys.h>
#include <kern/thread.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <pexpert/pexpert.h>

OSDefineMetaClassAndStructors(ZornTouchPlatform26,IOService);
namespace {
uint32_t creatorAttempted26;
ZornTouchPlatform26 *platformTouch26;
uint32_t scheduleReturned26;
IOReturn scheduleRaw26;
bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}
bool nativeK80(IORegistryEntry &root)
{
    OSSharedPtr<OSObject> property(root.copyProperty("compatible"),OSNoRetain);
    auto *data=OSDynamicCast(OSData,property.get());
    if(!data || !data->getBytesNoCopy() || !data->getLength())return false;
    const auto *bytes=static_cast<const uint8_t *>(data->getBytesNoCopy());
    const size_t length=data->getLength();
    constexpr char required[]="xiaomi,zorn";
    bool found=false;
    for(size_t at=0;at<length;) {
        const size_t begin=at;
        while(at<length && bytes[at])++at;
        if(at==length || at==begin)return false;
        if(at-begin==sizeof(required)-1) {
            bool equal=true;
            for(size_t i=0;i<sizeof(required)-1;++i)
                if(bytes[begin+i]!=uint8_t(required[i]))equal=false;
            if(equal)found=true;
        }
        ++at;
    }
    return found; // Board selection only, not hardware access permission.
}
}

IOReturn ZornTouchPlatform26::createAndSchedule(IOService &platform,
    unsigned pacing,uint32_t limit,ZornTouchPlatform26 *&out)
{return createWithMode(platform,pacing,{false,limit},out);}
IOReturn ZornTouchPlatform26::createAndScheduleContinuous(IOService &platform,unsigned pacing,ZornTouchPlatform26 *&out)
{return createWithMode(platform,pacing,{true,0},out);}
IOReturn ZornTouchPlatform26::createWithMode(IOService &platform,unsigned pacing,
    ZornTouchRunPolicy26 policy,ZornTouchPlatform26 *&out)
{
    ZornTouchPacing::Settings settings;
    if(out || !normal() || !policy.valid() || !ZornTouchPacing::select(pacing,settings) ||
       !OSDynamicCast(IODTPlatformExpert,&platform))return kIOReturnBadArgument;
    OSSharedPtr<IORegistryEntry> root(IORegistryEntry::fromPath("/",gIODTPlane),OSNoRetain);
    if(!root || !nativeK80(*root))return kIOReturnUnsupported;
    uint32_t empty=0;
    if(!__atomic_compare_exchange_n(&creatorAttempted26,&empty,1u,false,
        __ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return kIOReturnExclusiveAccess;
    auto *owner=new ZornTouchPlatform26;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()){owner->release();return kIOReturnError;}
    owner->retain();owner->pinned_=true;out=owner;
    platform.retain();owner->platform_=&platform;
    owner->root_=root.detach();owner->pacing_=pacing;owner->runPolicy_=policy;
    owner->gate_=IOLockAlloc();if(!owner->gate_)return kIOReturnNoMemory;
    const auto resources=owner->prepareProvider();if(resources)return resources;
    if(!owner->attach(owner->touchProvider_) || !owner->IOService::start(owner->touchProvider_))return kIOReturnNotAttached;
    owner->setName("ZornFT3683Board");
    // No seizure, service publication or PM initialization. Hold this native
    // touch client open through every returned or uncertain bus operation.
    // The platform expert itself stays available to storage/GPU creators.
    const bool opened=owner->touchProvider_->open(owner,0,nullptr);
    IOLockLock(owner->gate_);owner->status_.providerOpenReturned=true;
    owner->status_.providerOpened=opened;IOLockUnlock(owner->gate_);
    if(!opened || !owner->touchProvider_->isOpen(owner))return kIOReturnExclusiveAccess;
    thread_t thread=THREAD_NULL;
    const auto raw=kernel_thread_start(worker,owner,&thread);
    IOLockLock(owner->gate_);owner->status_.threadRaw=raw;
    owner->status_.threadReturned=true;owner->status_.threadHandleReturned=thread!=THREAD_NULL;
    IOLockUnlock(owner->gate_);
    if(raw!=KERN_SUCCESS)return kIOReturnNoResources;
    if(thread==THREAD_NULL)return kIOReturnNotReady;
    thread_deallocate(thread);return kIOReturnSuccess;
}

IOReturn ZornTouchPlatform26::prepareProvider()
{
    auto *expert=OSDynamicCast(IODTPlatformExpert,platform_);
    if(!expert || !root_)return kIOReturnNotReady;
    touchNode_=IORegistryEntry::fromPath("arm-io/ft3683",gIODTPlane,nullptr,nullptr,root_);
    if(!touchNode_)return kIOReturnNotFound;
    OSSharedPtr<OSObject> compatible(touchNode_->copyProperty("compatible"),OSNoRetain);
    auto *binding=OSDynamicCast(OSData,compatible.get());
    constexpr char expected[]="unixnu,zorn-ft3683-gpio";
    if(!binding || binding->getLength()!=sizeof(expected) || !binding->getBytesNoCopy())return kIOReturnUnsupported;
    const auto *bound=static_cast<const uint8_t *>(binding->getBytesNoCopy());
    for(size_t i=0;i<sizeof(expected);++i)if(bound[i]!=uint8_t(expected[i]))return kIOReturnUnsupported;
    // The real platform may already have made the native nub. Reuse only
    // that exact base class under this expert: arbitrary subclasses can have
    // shared handleOpen policies. Never replace an attached driver or borrow
    // its claim; the independent open below still must actually succeed.
    IOPlatformDevice *provider=nullptr;
    if(ZornGen7NativeDtEntry26::canPromote(*touchNode_)) {
        provider=new IOPlatformDevice;if(!provider)return kIOReturnNoMemory;
        touchProvider_=provider;
        if(!provider->init(touchNode_,gIODTPlane))return kIOReturnError;
        if(!provider->attach(expert))return kIOReturnNotAttached;
    } else {
        provider=OSDynamicCast(IOPlatformDevice,touchNode_);
        if(!provider || provider->getMetaClass()!=IOPlatformDevice::metaClass ||
           provider->getProvider()!=expert)return kIOReturnExclusiveAccess;
        provider->retain();touchProvider_=provider;
    }
    const auto raw=provider->getResources();
    IOLockLock(gate_);status_.resourcesReturned=true;status_.resourcesRaw=raw;IOLockUnlock(gate_);
    if(raw)return raw;
    OSSharedPtr<OSObject> property(provider->copyProperty(gIODeviceMemoryKey),OSNoRetain);
    auto *array=OSDynamicCast(OSArray,property.get());
    if(!array || array->getCount()!=6)return kIOReturnBadArgument;
    static_assert(sizeof(ZornTouch::pins)/sizeof(ZornTouch::pins[0])==6);
    for(unsigned i=0;i<6;++i) {
        auto *resource=OSDynamicCast(IOMemoryDescriptor,array->getObject(i));
        if(!resource || resource->getLength()!=4096)return kIOReturnBadArgument;
        IOByteCount contiguous=0;
        const uint64_t physical=0xf100000ULL+uint64_t(ZornTouch::pins[i])*0x1000ULL;
        if(resource->getPhysicalSegment(0,&contiguous,kIOMemoryMapperNone)!=physical || contiguous<4096)
            return kIOReturnBadArgument;
        resource->retain();gpioResources_[i]=resource;
    }
    // Resource shape identifies this source projection. The actual native
    // provider open and the later live bus checks are separate operations.
    return kIOReturnSuccess;
}

void ZornTouchPlatform26::worker(void *context,wait_result_t)
{
    auto &owner=*static_cast<ZornTouchPlatform26 *>(context);
    IOLockLock(owner.gate_);const bool stopped=owner.stopRequested_;IOLockUnlock(owner.gate_);
    if(!stopped && owner.touchProvider_->isOpen(&owner) && nativeK80(*owner.root_)) {
        ZornTouchBoard26 *board=nullptr;
        const auto raw=ZornTouchBoard26::create(owner,owner,owner.gpioResources_,board);
        IOLockLock(owner.gate_);owner.board_=board;owner.status_.boardCreateRaw=raw;
        owner.status_.boardCreateReturned=true;const bool stopAfterCreate=owner.stopRequested_;
        IOLockUnlock(owner.gate_);
        if(board && stopAfterCreate)board->requestStop();
        if(!raw && board && !stopAfterCreate && owner.touchProvider_->isOpen(&owner)) {
            const auto actual=owner.runPolicy_.continuous ? board->startContinuous(owner.pacing_) : board->start(owner.pacing_,owner.runPolicy_.limit);
            IOLockLock(owner.gate_);owner.status_.board=actual;
            owner.status_.boardStartReturned=true;IOLockUnlock(owner.gate_);
        }
    }
    (void)thread_terminate(current_thread());panic("K80 FT3683 platform worker termination returned");
}

ZornTouchPlatform26::Status ZornTouchPlatform26::readStatus()
{
    if(!gate_ || !normal())return {};
    IOLockLock(gate_);auto status=status_;auto *board=board_;IOLockUnlock(gate_);
    if(board && status.boardCreateReturned && !status.boardCreateRaw)status.board=board->readStatus();
    return status;
}
void ZornTouchPlatform26::stop(IOService *provider)
{
    if(gate_ && normal()) {
        IOLockLock(gate_);stopRequested_=true;auto *board=board_;IOLockUnlock(gate_);
        if(board)board->requestStop();
    }
    // A stop request is not a sensor/worker drain. Keep the open client,
    // mappings and callback storage; do not restore pins or release resources.
    IOService::stop(provider);
}
void ZornTouchPlatform26::free(){if(pinned_)return;IOService::free();}

extern "C" void zorn26_touch_platform_start(IOService *platform)
{
    unsigned selected=0,record=0,pacing=0,continuous=0;uint32_t limit=0;
    if(!PE_parse_boot_argn("zorn26_touch",&selected,sizeof(selected)) || selected!=1 || !platform)return;
    if(PE_parse_boot_argn("zorn26_platform_record",&record,sizeof(record)) && record)return;
    // Finite validation remains the default and still requires nonzero limit.
    // Continuous acquisition is a separate explicit source/profile selection;
    // it never follows from an absent/zero legacy budget or guessed pacing.
    if(!PE_parse_boot_argn("zorn26_touch_pacing",&pacing,sizeof(pacing)) || pacing>1)return;
    if(PE_parse_boot_argn("zorn26_touch_continuous",&continuous,sizeof(continuous)) && continuous>1)return;
    const bool hasLimit=PE_parse_boot_argn("zorn26_touch_limit",&limit,sizeof(limit));
    unsigned recordTouch=0;
    const bool recordSelected=PE_parse_boot_argn("zorn26_touch_record",&recordTouch,sizeof(recordTouch)) && recordTouch==1;
    if(recordSelected){
        unsigned installed=0;
        const bool runPolicyValid = continuous == 1 ? (!hasLimit || limit == 0) : (hasLimit && limit != 0);
        if(!runPolicyValid || !PE_parse_boot_argn("zorn26_installed_root_trial",&installed,sizeof(installed)) || installed!=1)
            return;
    }
    IOReturn raw;
    if(continuous==1){
        if(hasLimit && limit)return; // conflicting policies,not a silent override
        raw=ZornTouchPlatform26::createAndScheduleContinuous(*platform,pacing,platformTouch26);
    } else {
        if(!hasLimit || !limit)return;
        raw=ZornTouchPlatform26::createAndSchedule(*platform,pacing,limit,platformTouch26);
    }
    if(recordSelected){
        scheduleRaw26=raw;
        __atomic_store_n(&scheduleReturned26,1u,__ATOMIC_RELEASE);
    }
}

int ZornTouchFormatTrialSnapshot26(char *output,size_t capacity)
{
    if(!normal() || !output || !capacity)return -1;
    if(!__atomic_load_n(&scheduleReturned26,__ATOMIC_ACQUIRE))
        return snprintf(output,capacity,"K80 FT3683: schedule did not return by sample; PID1 EL0");
    auto *owner=platformTouch26;
    if(!owner)return snprintf(output,capacity,"K80 FT3683: schedule=%08x owner=0; PID1 EL0",unsigned(scheduleRaw26));
    const auto p=owner->readStatus();
    const auto &b=p.board;
    const auto &h=b.host;
    const auto &w=h.worker;
    const unsigned flags=unsigned(p.resourcesReturned) | (unsigned(p.providerOpened)<<1) |
        (unsigned(p.threadReturned)<<2) | (unsigned(p.threadHandleReturned)<<3) |
        (unsigned(p.boardCreateReturned)<<4) | (unsigned(b.captureReturned)<<5) |
        (unsigned(b.preparationReturned)<<6) | (unsigned(b.hostStatusValid)<<7) |
        (unsigned(h.started)<<8) | (unsigned(h.registerCallReturned)<<9) |
        (unsigned(w.threadCreateReturned)<<10) | (unsigned(w.workerEntered)<<11) |
        (unsigned(w.producerFinished)<<12) | (unsigned(w.lastSourceValid)<<13) |
        (unsigned(w.contactReleaseReturned)<<14);
    const auto outcome=w.lastSource.outcome;
    unsigned last=0;
    if(w.lastSourceValid && outcome==ZornFt3683Source26::Outcome::DispatchReturned)
        last=unsigned(w.lastSource.detail.dispatchStatus);
    else if(w.lastSourceValid && outcome==ZornFt3683Source26::Outcome::TransportError)
        last=w.lastSource.detail.transportError;
    return snprintf(output,capacity,
        "K80 FT3683: schedule=%08x f=%x res=%08x platformThread=%08x board=%u/%08x cap=%u/%u prep=%x id=%u/%02x%02x%02x host=%u worker=%u/%u/%08x baseline=%u/%u frames=%u last=%u/%08x release=%08x; PID1 EL0",
        unsigned(scheduleRaw26),flags,unsigned(p.resourcesRaw),unsigned(p.threadRaw),unsigned(b.phase),
        unsigned(p.boardCreateRaw),b.capture.result,b.capture.reads,b.preparationRaw,b.identityReadsReturned,unsigned(b.identity[0]),
        unsigned(b.identity[1]),unsigned(b.identity[2]),unsigned(h.phase),unsigned(w.phase),unsigned(w.end),
        unsigned(w.threadCreateStatus),w.acceptedBaselines,w.baselineAttempts,w.framesRead,unsigned(outcome),last,
        unsigned(w.contactReleaseStatus));
}
