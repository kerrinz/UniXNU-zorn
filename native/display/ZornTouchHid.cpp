// SPDX-License-Identifier: BSD-2-Clause-Patent
// Board-owned digitizer using the unmodified 21H461 IOHIDDevice parser.
// Report shape follows UniXNU NativeHidInput's ten-contact collection.
#include "OriginalHidDeviceABI.h"
#include "ZornTouchContacts.h"
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOCatalogue.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSDictionary.h>
#include <libkern/c++/OSUnserialize.h>
#include <libkern/c++/OSIterator.h>
#include <libkern/c++/OSString.h>
#include <libkern/c++/OSSymbol.h>
#include <mach/kmod.h>
#include <pexpert/pexpert.h>
extern kmod_info_t g_kernel_kmod_info;
extern "C" void zorn_touch_hid_static_init(void) __asm__("__GLOBAL__sub_I_ZornTouchHid.cpp");
extern "C" {volatile uint32_t zorn_touch_hid_stats[8];}
extern "C" {volatile uint32_t zorn_touch_edge_stats[8];}
#include "ZornTouchEdgeDispatch.h"
#include "ZornTouchKernelMatch.h"
extern "C" volatile uint64_t zorn_touch_runtime_stats[12];
static void hidStage(unsigned stage) {
    zorn_touch_hid_stats[0]=stage;
    zorn_touch_runtime_stats[10]=stage | (uint64_t(zorn_touch_hid_stats[1])<<32);
}
static bool registerKernelTouchParser() {
    unsigned enabled=0;
    if(!PE_parse_boot_argn("zorn_touch_kernel_parser",&enabled,sizeof(enabled)) || enabled!=1)return true;
    zorn_touch_hid_stats[5]=1;
    OSString *error=nullptr;
    OSObject *object=OSUnserializeXML(zornTouchKernelPersonality,&error);
    OSDictionary *personality=OSDynamicCast(OSDictionary,object);
    OSArray *drivers=OSArray::withCapacity(1);
    bool ok=personality && !error && drivers && drivers->setObject(personality) &&
        gIOCatalogue && gIOCatalogue->addDrivers(drivers,false);
    OSSafeReleaseNULL(drivers);OSSafeReleaseNULL(object);OSSafeReleaseNULL(error);
    zorn_touch_hid_stats[5]=ok?2:3;
    return ok;
}
#define ZORN_FINGER_DESC \
  0x09,0x22,0xa1,0x02,0x09,0x42,0x15,0,0x25,1,0x75,1,0x95,1,0x81,2,0x09,0x47,0x81,2,0x75,6,0x95,1,0x81,3, \
  0x09,0x51,0x75,8,0x95,1,0x15,0,0x26,0xff,0,0x81,2, \
  0x05,1,0x09,0x30,0x15,0,0x26,0xff,0x7f,0x75,16,0x95,1,0x81,2,0x09,0x31,0x81,2,0x05,0x0d,0xc0,
static const uint8_t descriptor[]={0x05,0x0d,0x09,4,0xa1,1,0x85,3,
 ZORN_FINGER_DESC ZORN_FINGER_DESC ZORN_FINGER_DESC ZORN_FINGER_DESC ZORN_FINGER_DESC
 ZORN_FINGER_DESC ZORN_FINGER_DESC ZORN_FINGER_DESC ZORN_FINGER_DESC ZORN_FINGER_DESC
 0x09,0x54,0x75,8,0x95,1,0x15,0,0x26,0xff,0,0x81,2,0xc0};
class ZornTouchHid : public IOHIDDevice {
    OSDeclareDefaultStructors(ZornTouchHid)
    IOWorkLoop *loop=nullptr;
    ZornContacts::Frame previous={};
    bool eventDriver=false;
    static IORegistryEntry *findDriver(IORegistryEntry *parent,unsigned depth) {
        if(!depth)return nullptr;OSIterator *it=parent->getChildIterator(gIOServicePlane);if(!it)return nullptr;
        IORegistryEntry *found=nullptr;while(OSObject *child=it->getNextObject()) {
            IORegistryEntry *entry=OSDynamicCast(IORegistryEntry,child);
            if(!entry)continue;
            if(entry->metaCast("IOHIDEventDriver")){entry->retain();found=entry;}
            else found=findDriver(entry,depth-1);
            if(found)break;
        }
        it->release();return found;
    }
    IOReturn write(const ZornContacts::Frame &current,const ZornContacts::Frame &up) {
        if(current.count+up.count>10)return kIOReturnBadArgument;
        uint8_t report[62]={3};unsigned index=0;
        for(unsigned group=0;group<2;++group) {
            const ZornContacts::Frame &frame=group?up:current;
            for(unsigned i=0;i<frame.count;++i,++index) {
                const auto &p=frame.points[i];uint8_t *f=report+1+index*6;
                f[0]=group?2:3;f[1]=p.id;f[2]=static_cast<uint8_t>(p.x);f[3]=static_cast<uint8_t>(p.x>>8);f[4]=static_cast<uint8_t>(p.y);f[5]=static_cast<uint8_t>(p.y>>8);
            }
        }
        report[61]=static_cast<uint8_t>(index);
        IOBufferMemoryDescriptor *memory=IOBufferMemoryDescriptor::withBytes(report,sizeof(report),kIODirectionNone);
        IOReturn rc=memory?IOHIDDevice::handleReport(memory,0,0):kIOReturnNoMemory;
        OSSafeReleaseNULL(memory);__atomic_fetch_add(&zorn_touch_hid_stats[2],1,__ATOMIC_RELAXED);zorn_touch_hid_stats[3]=static_cast<uint32_t>(rc);
        if(rc)__atomic_fetch_add(&zorn_touch_hid_stats[4],1,__ATOMIC_RELAXED);
        zorn_touch_runtime_stats[11]=(uint64_t(zorn_touch_hid_stats[2])<<32) | static_cast<uint32_t>(rc);
        return rc;
    }
    static IOReturn sendAction(OSObject *owner,void *data,void *,void *,void *) {
        auto *self=OSDynamicCast(ZornTouchHid,owner);auto *frame=static_cast<const ZornContacts::Frame *>(data);
        if(!self || !frame || frame->count>10)return kIOReturnBadArgument;
        if(!self->eventDriver) {
            IORegistryEntry *driver=findDriver(self,4);self->eventDriver=driver!=nullptr;
            unsigned edges=0;
            if(driver && PE_parse_boot_argn("zorn_touch_edges",&edges,sizeof(edges)) && edges==1)ZornTouchEdges::install(driver);
            OSSafeReleaseNULL(driver);
        }
        zorn_touch_hid_stats[1]=self->eventDriver;
        hidStage(zorn_touch_hid_stats[0]);
        if(!self->eventDriver)return kIOReturnNotReady;
        ZornContacts::Frame up={};
        for(unsigned i=0;i<self->previous.count;++i) {
            const auto &p=self->previous.points[i];bool found=false;
            for(unsigned j=0;j<frame->count;++j)if(frame->points[j].id==p.id)found=true;
            if(!found)up.points[up.count++]=p;
        }
        IOReturn rc=kIOReturnSuccess;
        if(frame->count+up.count>10) {
            ZornContacts::Frame empty={};rc=self->write(empty,self->previous);
            if(rc)return rc;self->previous={};up={};
        }
        if(frame->count || up.count)rc=self->write(*frame,up);
        if(!rc)self->previous=*frame;
        return rc;
    }
public:
    void observeService() {
        IORegistryEntry *entry=findDriver(this,4);
        IOService *service=entry?OSDynamicCast(IOService,entry):nullptr;
        if(service) {
            zorn_touch_hid_stats[6]=service->getState();
            IOService *interface=service->getProvider();
            IOService *resource=getProvider();
            zorn_touch_hid_stats[7]=(service->isOpen()?1u:0u) |
                (service->getProperty("HIDServiceSupport")==kOSBooleanTrue?2u:0u) |
                (interface && interface->getProperty("IOHIDDeviceOpenedByEventSystem")==kOSBooleanTrue?4u:0u) |
                (resource && resource->metaCast("IOHIDResource")?8u:0u);
        }
        OSSafeReleaseNULL(entry);
    }
    IOWorkLoop *getWorkLoop() const override{return loop;}
    OSString *newTransportString() const override{return OSString::withCString("SPI");}
    OSString *newProductString() const override{return OSString::withCString("Redmi K80 FT3683 Touchscreen");}
    IOReturn newReportDescriptor(IOMemoryDescriptor **out) const override {
        if(!out)return kIOReturnBadArgument;
        *out=IOBufferMemoryDescriptor::withBytes(descriptor,sizeof(descriptor),kIODirectionNone);
        return *out?kIOReturnSuccess:kIOReturnNoMemory;
    }
    bool start(IOService *provider) override {
        loop=IOWorkLoop::workLoop();if(!loop)return false;
        if(!setProperty("HIDDefaultBehavior",true) || !setProperty("Built-In",true) ||
           !setProperty("DisplayIntegrated",true) || !setProperty("DigitizerCollectionDispatch",true))return false;
        if(!registerKernelTouchParser())return false;
        return IOHIDDevice::start(provider);
    }
    void stop(IOService *provider) override{IOHIDDevice::stop(provider);}
    void free() override{OSSafeReleaseNULL(loop);IOHIDDevice::free();}
    IOReturn send(const ZornContacts::Frame &frame){return loop?loop->runAction(&ZornTouchHid::sendAction,this,const_cast<ZornContacts::Frame *>(&frame)):kIOReturnNotReady;}
};
OSDefineMetaClassAndStructors(ZornTouchHid,IOHIDDevice)
static ZornTouchHid *touchDevice;
extern "C" int zorn_touch_hid_publish(void) {
    if(touchDevice)return 1;
    hidStage(11);
    const OSSymbol *name=OSSymbol::withCString("IOHIDDevice");
    const OSMetaClass *meta=name?OSMetaClass::getMetaClassWithName(name):nullptr;OSSafeReleaseNULL(name);
    if(!meta || meta!=&IOHIDDevice::gMetaClass || meta->getClassSize()!=0xd0){hidStage(1);return 0;}
    hidStage(12);void *handle=OSMetaClass::preModLoad(g_kernel_kmod_info.name);if(!handle){hidStage(2);return 0;}
    hidStage(13);zorn_touch_hid_static_init();hidStage(14);kern_return_t rc=OSMetaClass::postModLoad(handle);
    if(rc){hidStage(3);zorn_touch_hid_stats[3]=static_cast<uint32_t>(rc);zorn_touch_runtime_stats[11]=static_cast<uint32_t>(rc);return 0;}
    hidStage(15);
    // Follow the upstream input probe's genuine HID resource provider, rather
    // than attaching the digitizer directly under generic IOResources.
    hidStage(20);
    OSDictionary *match=IOService::serviceMatching("IOHIDResource");
    IOService *provider=match?IOService::waitForMatchingService(match,5000000000ULL):nullptr;
    OSSafeReleaseNULL(match);
    auto *device=provider?new ZornTouchHid:nullptr;
    bool attached=false,started=false;
    if(device && provider){hidStage(16);if(device->init()){hidStage(17);attached=device->attach(provider);if(attached){hidStage(18);started=device->start(provider);}}}
    if(!started){if(attached)device->detach(provider);OSSafeReleaseNULL(device);OSSafeReleaseNULL(provider);hidStage(4);return 0;}
    device->setName("ZornFT3683Touch");hidStage(19);device->registerService();touchDevice=device;
    OSSafeReleaseNULL(provider);
    hidStage(5);return 1;
}
extern "C" int zorn_touch_hid_send(const ZornContacts::Frame *frame) {
    if(!touchDevice || !frame)return int(kIOReturnNotReady);
    return int(touchDevice->send(*frame));
}
extern "C" void zorn_touch_hid_observe(void) {
    if(touchDevice)touchDevice->observeService();
}
