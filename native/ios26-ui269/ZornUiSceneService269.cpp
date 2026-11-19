// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornTouchEventService26.h"
#include "ZornUiScenePlan269.h"
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <IOKit/IOLib.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSData.h>
#include <kern/clock.h>
#include <kern/thread.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
extern "C" bool zorn26_ui_scene_gpu_ready269();

// A separate normal HID service. No FT3683 provider open, GPIO, bus, IRQ,
// physical frame state, touchscreen identity or sampled contact is borrowed.
class ZornUiSceneService269 final : public ZornTouchEventService26 {
    OSDeclareDefaultStructors(ZornUiSceneService269);
public:
    bool hasSubscriber() {
        if(!_clientLock || !_clients || !acceptingFrames())return false;
        // The selected lifetime-fixed base keeps closed tombstones in _clients.
        // Its actual predicate skips them; array length is not an open client.
        IOLockLock(_clientLock);const bool present=handleIsOpenLocked(nullptr);
        IOLockUnlock(_clientLock);return present;
    }
protected:
    OSString *getTransport() override {return OSString::withCString("Virtual");}
    OSString *getProduct() override {return OSString::withCString("K80 GPU UI scene (synthetic)");}
};
OSDefineMetaClassAndStructors(ZornUiSceneService269,ZornTouchEventService26);

namespace {
uint32_t scheduled269=0,done269=0,schedulingReturned269=0;
uint32_t status269[16]{};
void store(unsigned i,uint32_t value){__atomic_store_n(status269+i,value,__ATOMIC_RELAXED);}
void addFlags(uint32_t flags){__atomic_fetch_or(status269+2,flags,__ATOMIC_RELAXED);}
void finish(uint32_t phase){store(0,phase);__atomic_store_n(&done269,1u,__ATOMIC_RELEASE);}
bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}
bool nativeK80(IOService *platform) {
    if(!OSDynamicCast(IODTPlatformExpert,platform))return false;
    auto *root=IORegistryEntry::fromPath("/",gIODTPlane);if(!root)return false;
    auto *property=root->copyProperty("compatible");root->release();
    auto *data=OSDynamicCast(OSData,property);bool found=false,valid=data&&data->getBytesNoCopy()&&data->getLength();
    if(valid) {
        const auto *p=static_cast<const uint8_t *>(data->getBytesNoCopy());
        const size_t length=data->getLength();constexpr char expected[]="xiaomi,zorn";
        for(size_t at=0;at<length;) {
            const size_t begin=at;while(at<length && p[at])++at;
            if(at==length || at==begin){valid=false;break;}
            if(at-begin==sizeof(expected)-1 && !memcmp(p+begin,expected,sizeof(expected)-1))found=true;
            ++at;
        }
    }
    OSSafeReleaseNULL(property);return valid&&found;
}
struct Backend {
    ZornUiSceneService269 &service;
    uint64_t nowMs() {uint64_t ns=0;absolutetime_to_nanoseconds(mach_absolute_time(),&ns);return ns/1000000;}
    bool ready(){return service.hasSubscriber();}
    uint32_t send(const ZornContacts::Frame &frame){return uint32_t(service.submitFrame(frame));}
    void sleepMs(uint32_t ms){IOSleep(ms);}
};
void worker(void *context,wait_result_t) {
    auto *platform=static_cast<IOService *>(context);
    // Fixed prospective candidate:one scene after real PID1 EL0,well before
    // the independent300s WDT. No boot-argument extension of the1022byte line.
    IOSleep(120000);
    if(!__atomic_load_n(&schedulingReturned269,__ATOMIC_ACQUIRE)) {
        store(7,uint32_t(kIOReturnNotReady));finish(7);
    } else if(!normal() || !nativeK80(platform)) {
        store(7,uint32_t(kIOReturnUnsupported));finish(7);
    } else if(!zorn26_ui_scene_gpu_ready269()) {
        // No new input or service registration after an incomplete/failed GPU
        // probe. This predicate grants no DMA-stop or resource-release authority.
        store(7,uint32_t(kIOReturnNotReady));finish(7);
    } else {
        addFlags(512);
        store(0,2);
        auto *service=new ZornUiSceneService269;
        bool initialized=false,attached=false,started=false;
        if(service)initialized=service->init();
        if(initialized){addFlags(4);attached=service->attach(platform);}
        if(attached){addFlags(8);started=service->start(platform);}
        if(started) {
            addFlags(16);service->registerService();addFlags(32);store(0,3);
            Backend io{*service};const auto r=ZornUiScene269::run(io);
            store(3,r.polls);store(4,uint32_t(service->hasSubscriber()));
            store(5,r.attempted);store(6,r.returned);store(7,r.firstRaw);
            store(8,r.liftRaw);store(9,r.elapsedMs);
            store(10,ZornUiScene269::X);store(11,ZornUiScene269::StartY);
            store(12,ZornUiScene269::EndY);store(13,ZornUiScene269::Steps);
            store(14,ZornUiScene269::Identity);store(15,uint32_t(r.outcome));
            if(r.attempted)addFlags(64);
            if(r.liftAttempted && !r.liftRaw)addFlags(128);
            // Drop only the producer's creation reference. The live registered
            // service remains held by its service-plane attachment/subscribers;
            // normal IOKit termination owns stop/detach/free. No force-close of
            // user clients, guessed callback drain or physical driver teardown.
            service->release();service=nullptr;addFlags(256);
            finish(r.outcome==ZornUiScene269::Outcome::Complete?6u:7u);
        } else {
            store(7,uint32_t(kIOReturnNotReady));
            // Not published,no worker/client callback can borrow this object.
            if(attached)service->detach(platform);
            OSSafeReleaseNULL(service);finish(7);
        }
    }
    platform->release();
    (void)thread_terminate(current_thread());panic("K80 synthetic UI worker termination returned");
}
}
extern "C" bool zorn26_ui_scene_done269() {return __atomic_load_n(&done269,__ATOMIC_ACQUIRE)!=0;}
extern "C" bool zorn26_ui_scene_snapshot269(uint32_t (&out)[16]) {
    if(!zorn26_ui_scene_done269())return false;
    for(unsigned i=0;i<16;++i)out[i]=__atomic_load_n(status269+i,__ATOMIC_RELAXED);
    return true;
}
extern "C" void zorn26_ui_scene_schedule269(IOService *platform) {
    if(!normal() || !nativeK80(platform))return;
    uint32_t zero=0;
    if(!__atomic_compare_exchange_n(&scheduled269,&zero,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
    store(0,1);addFlags(1);platform->retain();thread_t thread=THREAD_NULL;
    const auto raw=kernel_thread_start(worker,platform,&thread);
    store(1,uint32_t(raw));
    if(raw==KERN_SUCCESS && thread!=THREAD_NULL){thread_deallocate(thread);addFlags(2);}
    else if(raw!=KERN_SUCCESS){platform->release();store(7,uint32_t(raw));finish(7);}
    // Success without a handle does not authorize release/retry;the real worker
    // may still use the retained platform. A missing final packet is incomplete.
    __atomic_store_n(&schedulingReturned269,1u,__ATOMIC_RELEASE);
}
