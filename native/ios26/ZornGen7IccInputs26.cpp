// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7IccInputs26.h"
#include "ZornGen7NativeDtEntry26.h"
#include "ZornGen7IccSource26.inc"
#include "ZornGen7NativeClockRoot.h"
#include "ZornGen7IccVoter26.h"
#include "ZornGen7IccQosSource26.inc"
#include <kern/task.h>
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <IOKit/IOKitKeys.h>
#include <IOKit/IOMemoryDescriptor.h>
#include <IOKit/IOLib.h>
#include <string.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSIterator.h>
#include <libkern/c++/OSSharedPtr.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7IccInputs26,OSObject)
namespace {
uint32_t qosObservation;
}
extern "C" uint32_t zorn26_native_qos_observation()
{
    return __atomic_load_n(&qosObservation,__ATOMIC_ACQUIRE);
}
namespace {
using namespace ZornGen7IccSource26;
bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}
uint32_t be32(const void *p){const auto *b=static_cast<const uint8_t *>(p);return uint32_t(b[0])<<24|uint32_t(b[1])<<16|uint32_t(b[2])<<8|b[3];}
}
struct ZornGen7IccInputs26::Storage {
    IOService *platform=nullptr,*gpu=nullptr;IORegistryEntry *root=nullptr,*gpuPeer=nullptr;
    OSObject *treeOwner=nullptr;IORegistryEntry *inputs[sizeof(nodes)/sizeof(*nodes)]{};
    OSObject *properties[property_capacity]{};size_t propertyCount=0;
    IOService *providers[2]{};IOPlatformDevice *nubs[2]{};
    IOMemoryDescriptor *gemDescriptor=nullptr;
    IOReturn resourcesRaw[2]{kIOReturnNotReady,kIOReturnNotReady};
    bool resourcesReturned[2]{},providerConstructed[2]{};
    uint32_t ddrType=0,ddr[16]{},ddrCount=0,bootstrapPeak=0;
    bool attempted=false,sourceReady=false,clockAttempted=false,clockBound=false;
    bool voterAttempted=false;ZornGen7IccVoter26 *voter=nullptr;
    uint32_t clockIndex=0;const char *clockNames[1]{};size_t clockNameExtents[1]{};
    char clockPath[1024]{};
    ZornGen7Clock::NativeClockFirmwareSpecifier clockSpec{};
    ZornGen7Clock::NativeClockFirmwareNode clockNode{};
    ZornGen7Clock::NativeClockFirmwareConsumer clockConsumer{};
    ZornGen7Clock::ClockConsumerListResult clockResult{};
    const ZornGen7Clock::ActualCcfBulkFields *clockFields=nullptr;
    ZornGen7Clock::NativeClockRoot *clockRoot=nullptr;IORecursiveLock *startupGate=nullptr;
    ZornGen7Icc::NativeIccClock *ubwcClock=nullptr;
    OSObject *qosAuthorityOwner=nullptr;ZornGen7OperationGuard26 qosGuard{};ZornGen7IccQosAuthority26 qosAuthority{};
    bool qosAttempted=false,qosReady=false,qosWindowReturned=false,qosMapGuardReturned=false;
    bool nativeQosMode=false,nativeQosOpened=false;unsigned qosNativeProbe=0;IOService *nativeQosClient=nullptr,*nativeQosParent=nullptr;
    int qosWindowRaw=0,qosMapGuardRaw=0;IOMemoryMap *qosMap=nullptr;uintptr_t qosVirtual=0;
    IOService *tbuProvider=nullptr,*tbuController=nullptr;bool tbuAttempted=false,tbuHeld=false,tbuReleaseAttempted=false;
    bool qosAccessBusy=false,qosGuardReturned=false,qosPrimitiveReturned=false,qosObserverReturned=false;
    int qosGuardRaw=0,qosObserverRaw=0;
    ZornGen7Clock::NativeCcfBulk *qosBulk=nullptr;
    ZornGen7Clock::CcfBulkResult qosEnableResult{};ZornGen7Clock::CcfBulkReleaseResult qosReleaseResult{};
    template<class Key> OSObject *copy(IORegistryEntry &node,Key key){
        if(propertyCount==property_capacity)return nullptr;
        OSObject *p=node.copyProperty(key);if(p)properties[propertyCount++]=p;return p;
    }
    bool scalar(IORegistryEntry &node,const char *key,uint32_t &value){
        auto *data=OSDynamicCast(OSData,copy(node,key));
        if(!data || data->getLength()!=4 || !data->getBytesNoCopy())return false;
        value=be32(data->getBytesNoCopy());return true;
    }
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7IccInputs26::create(IOService &platform,IORegistryEntry &root,
    IOService &gpu,OSObject &owner,uint32_t actualDdr,ZornGen7IccInputs26 *&out)
{
    if(out || !normal() || actualDdr!=ddr_type)return kIOReturnNotReady;
    auto *object=new ZornGen7IccInputs26;if(!object)return kIOReturnNoMemory;
    if(!object->init()){object->release();return kIOReturnNoMemory;}
    object->retain();object->pinned_=true;out=object;
    platform.retain();root.retain();gpu.retain();owner.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    object->storage_=new(memory)Storage;auto &s=*object->storage_;
    s.platform=&platform;s.root=&root;s.gpu=&gpu;s.treeOwner=&owner;s.ddrType=actualDdr;
    return object->resolve()?kIOReturnSuccess:kIOReturnNotReady;
}
bool ZornGen7IccInputs26::resolve()
{
    if(!storage_ || !normal())return false;auto &s=*storage_;
    if(s.attempted)return false;s.attempted=true;
    s.gpuPeer=IORegistryEntry::fromPath("arm-io/gpu",gIODTPlane,nullptr,nullptr,s.root);
    if(s.gpuPeer!=s.gpu)return false;
    // Inspect actual native input nodes and every archived property/child count.
    // The digest establishes which source projection was built, not a lease.
    for(size_t i=0;i<sizeof(nodes)/sizeof(*nodes);++i) {
        const auto &expected=nodes[i];auto *node=IORegistryEntry::fromPath(expected.path,gIODTPlane,nullptr,nullptr,s.root);
        s.inputs[i]=node;if(!node)return false;
        for(size_t p=0;p<expected.count;++p) {
            const auto &property=expected.properties[p];auto *data=OSDynamicCast(OSData,s.copy(*node,property.key));
            if(!data || data->getLength()!=property.count || (property.count && !data->getBytesNoCopy()))return false;
            const auto *bytes=static_cast<const uint8_t *>(data->getBytesNoCopy());
            for(size_t k=0;k<property.count;++k)if(bytes[k]!=property.bytes[k])return false;
        }
        OSSharedPtr<OSIterator> iterator(node->getChildIterator(gIODTPlane),OSNoRetain);
        size_t count=0;if(iterator)while(iterator->getNextObject()){if(++count>expected.children)return false;}
        if(count!=expected.children)return false;
    }
    auto *source=s.inputs[2]; // Source projection, not an ICC hardware provider.
    // Actual source DDR8 overrides are absent; generic fallback is exact here.
    if(s.copy(*source,"qcom,bus-table-ddr8"))return false;
    auto *table=OSDynamicCast(OSData,s.copy(*source,"qcom,bus-table-ddr"));
    if(!table || !table->getBytesNoCopy() || !table->getLength() || table->getLength()%4 || table->getLength()>sizeof(s.ddr))return false;
    s.ddrCount=table->getLength()/4;
    for(uint32_t i=0;i<s.ddrCount;++i)s.ddr[i]=be32(static_cast<const uint8_t *>(table->getBytesNoCopy())+i*4u);
    bool first=true;
    for(const auto &candidate:initial) {
        IORegistryEntry *bin=nullptr,*row=nullptr;
        for(size_t i=0;i<sizeof(nodes)/sizeof(*nodes);++i){
            if(!strcmp(nodes[i].path,candidate.bin))bin=s.inputs[i];
            if(!strcmp(nodes[i].path,candidate.row))row=s.inputs[i];
        }
        if(!bin || !row)return false;uint32_t selected=0,index=0,frequency=0,bus=0;
        if(!s.scalar(*bin,"qcom,initial-pwrlevel",selected) || selected!=candidate.index ||
           !s.scalar(*row,"reg",index) || index!=selected ||
           !s.scalar(*row,"qcom,gpu-freq",frequency) || !frequency)return false;
        if(s.copy(*row,"qcom,bus-min-ddr8") || s.copy(*row,"qcom,bus-freq-ddr8"))return false;
        if(!s.scalar(*row,"qcom,bus-min",bus) || bus>=s.ddrCount)return false;
        if(first){s.bootstrapPeak=s.ddr[bus];first=false;}
        else if(s.bootstrapPeak!=s.ddr[bus])return false;
    }
    if(first || s.bootstrapPeak!=source_bootstrap_peak)return false;
    auto *expert=OSDynamicCast(IODTPlatformExpert,s.platform);if(!expert)return false;
    for(unsigned i=0;i<2;++i) {
        auto *node=s.inputs[i];auto *provider=OSDynamicCast(IOService,node);
        if(ZornGen7NativeDtEntry26::canPromote(*node))provider=nullptr;
        if(provider) {
            if(!provider->getProvider())return false;provider->retain();s.providers[i]=provider;
            // A non-raw provider must already own its actual resources; never
            // overwrite another live provider or fabricate a descriptor array.
        }else{
            if(!ZornGen7NativeDtEntry26::canPromote(*node))return false;
            auto *nub=new IOPlatformDevice;s.nubs[i]=nub;if(!nub)return false;
            if(!nub->init(node,gIODTPlane) || !nub->attach(expert))return false;
            s.providers[i]=nub;s.providerConstructed[i]=true;
            if(i==0){s.resourcesRaw[i]=nub->getResources();s.resourcesReturned[i]=true;if(s.resourcesRaw[i]!=kIOReturnSuccess)return false;}
        }
        if(i==1){if(s.copy(*s.providers[i],"reg"))return false;continue;} // Exact source no MMIO declaration.
        auto *array=OSDynamicCast(OSArray,s.copy(*s.providers[i],gIODeviceMemoryKey));
        if(!array || array->getCount()!=1)return false;
        auto *descriptor=OSDynamicCast(IOMemoryDescriptor,array->getObject(0));if(!descriptor)return false;
        IOByteCount contiguous=0;
        if(descriptor->getLength()!=gem_bytes || descriptor->getPhysicalSegment(0,&contiguous,kIOMemoryMapperNone)!=gem_physical ||
           contiguous<gem_bytes)return false;
        descriptor->retain();s.gemDescriptor=descriptor;
    }
    s.sourceReady=true;return true;
    // This CPU construction establishes resource identity and bin-invariant
    // source scalar only. Later explicit methods perform source clock/BCM/QoS
    // and bandwidth work using real guards;resolve itself does not issue IO.
    // Private HLOS path is not full OEM provider or physical fabric ownership.
}
IOReturn ZornGen7IccInputs26::bindClock(ZornGen7Clock::NativeClockRoot &clocks,
    const ZornGen7Clock::NativeClockFirmwareNode &gcc,IORecursiveLock *startup)
{
    using namespace ZornGen7Clock;
    if(!sourceReady() || !normal() || !startup || !IORecursiveLockHaveLock(startup))return kIOReturnNotReady;
    auto &s=*storage_;if(s.clockAttempted)return kIOReturnNotReady;s.clockAttempted=true;
    // The board supplies its SAME already registered GCC node, not a node made
    // from Linux phandle0x2c. Native phandles belong to a different namespace.
    constexpr char gccPath[]="/gcc@100000";
    if(!gcc.lifetime || gcc.clock_cells!=1 || !gcc.full_name || gcc.full_name_extent!=sizeof(gccPath))return kIOReturnNotReady;
    for(size_t i=0;i<sizeof(gccPath);++i)if(gcc.full_name[i]!=gccPath[i])return kIOReturnNotReady;
    auto *raw=OSDynamicCast(OSData,s.copy(*s.providers[0],"k80,source-clocks"));
    auto *names=OSDynamicCast(OSData,s.copy(*s.providers[0],"k80,source-clock-names"));
    constexpr char alias[]="gcc_ddrss_ubwcp_clk";
    if(!raw || raw->getLength()!=8 || !raw->getBytesNoCopy() || !names || names->getLength()!=sizeof(alias) || !names->getBytesNoCopy())return kIOReturnBadArgument;
    const auto *cells=static_cast<const uint8_t *>(raw->getBytesNoCopy());
    if(be32(cells)!=0x2cu || be32(cells+4)!=13)return kIOReturnUnsupported;
    const auto *text=static_cast<const char *>(names->getBytesNoCopy());
    for(size_t i=0;i<sizeof(alias);++i)if(text[i]!=alias[i])return kIOReturnBadArgument;
    OSSharedPtr<IORegistryEntry> parent(s.providers[0]->copyParentEntry(gIODTPlane),OSNoRetain);
    if(parent.get()!=s.root || !gcc.parent || !gcc.parent->lifetime || gcc.parent->parent ||
       !gcc.parent->full_name || strcmp(gcc.parent->full_name,"/") || s.copy(*s.providers[0],"clock-ranges"))return kIOReturnNotReady;
    int pathBytes=sizeof(s.clockPath);
    if(!s.providers[0]->getPath(s.clockPath,&pathBytes,gIODTPlane))return kIOReturnNotReady;
    size_t extent=0;while(extent<sizeof(s.clockPath) && s.clockPath[extent])++extent;
    if(!extent || extent==sizeof(s.clockPath))return kIOReturnBadArgument;
    gcc.lifetime->retain();s.clockIndex=be32(cells+4);s.clockNames[0]=text;s.clockNameExtents[0]=sizeof(alias);
    s.clockSpec={&gcc,&s.clockIndex,1};
    s.clockNode={gcc.parent,ClockPropertyState::Present,ClockPropertyState::Absent,&s.clockSpec,1,
        s.clockNames,s.clockNameExtents,1,0,this,s.clockPath,extent+1u};
    s.clockConsumer={ClockPropertyState::Present,&s.clockNode,s.clockPath,extent+1u,this};
    s.clockResult=clocks.buildIccList(s.clockConsumer,startup,*this);
    if(s.clockResult.assessment!=ClockConsumerListAssessment::ListPublished ||
       !s.clockResult.source_return_available || s.clockResult.source_return!=1 || s.clockResult.entries_returned!=1)return kIOReturnNotReady;
    s.clockFields=clocks.iccBulkFields();
    if(!s.clockFields || !s.clockFields->num_clocks || *s.clockFields->num_clocks!=1 || !s.clockFields->slots || s.clockFields->slots_capacity!=1)return kIOReturnNotReady;
    s.clockRoot=&clocks;s.startupGate=startup;s.clockBound=true;return kIOReturnSuccess;
    // Actual bulk slot is retained for future source QoS dependency ordering.
    // No clock operation is called here; SH1 BCM proxy work must precede it.
}
bool ZornGen7IccInputs26::clockReady() const
{return sourceReady() && storage_->clockBound && storage_->clockFields;}
bool ZornGen7IccInputs26::sourceReady() const
{return storage_ && storage_->sourceReady && storage_->providers[0] && storage_->providers[1] && storage_->gemDescriptor;}
void ZornGen7IccInputs26::free(){if(pinned_)return;OSObject::free();}

IOReturn ZornGen7IccInputs26::bindVoter(ZornGen7RscRuntime26 &rsc,ZornGen7Rpmh::NativeCommandCache &cache,
    ZornGen7Rpmh::NativeReservation &reservation,const ZornGen7Rpmh::ActualXoCommandDbSnapshot &snapshot,OSObject &owner)
{return bindVoterInput(rsc,cache,reservation,&snapshot,nullptr,owner);}
IOReturn ZornGen7IccInputs26::bindVoterFromResources(ZornGen7RscRuntime26 &rsc,
    ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation,
    ZornGen7Rpmh::NativeCommandDbResourceReader &reader,OSObject &owner)
{return bindVoterInput(rsc,cache,reservation,nullptr,&reader,owner);}
IOReturn ZornGen7IccInputs26::bindVoterInput(ZornGen7RscRuntime26 &rsc,
    ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation,
    const ZornGen7Rpmh::ActualXoCommandDbSnapshot *snapshot,ZornGen7Rpmh::NativeCommandDbResourceReader *reader,OSObject &owner)
{
    if(!normal() || !clockReady() || storage_->voterAttempted || bool(snapshot)==bool(reader))return kIOReturnNotReady;
    auto &s=*storage_;s.voterAttempted=true;
    if(!s.clockRoot || !s.startupGate || !IORecursiveLockHaveLock(s.startupGate))return kIOReturnNotReady;
    s.ubwcClock=s.clockRoot->buildIccNodeClock(s.clockConsumer,s.startupGate,*this);
    if(!s.ubwcClock)return kIOReturnNotReady;
    return reader ? ZornGen7IccVoter26::createResources(*s.root,*s.treeOwner,rsc,cache,reservation,*reader,owner,*s.ubwcClock,*this,s.voter) :
        ZornGen7IccVoter26::create(*s.root,*s.treeOwner,rsc,cache,reservation,*snapshot,owner,*s.ubwcClock,*this,s.voter);
}
bool ZornGen7IccInputs26::voterReady() const
{return clockReady() && storage_->voter && storage_->voter->sourceReady();}

IOReturn ZornGen7IccInputs26::initializeInitialVotes()
{
    if(!normal() || !voterReady() || !storage_->startupGate ||
       !IORecursiveLockHaveLock(storage_->startupGate))return kIOReturnNotReady;
    return storage_->voter->initializeInitialVotes(storage_->startupGate);
}

// Same native descriptor/map primitives as RegisterMaps26,with the GEM
// resource retained by THIS actual ICC input owner. No physical descriptor is
// synthesized and no wider GPU/GMU mapping is reused.
IOReturn ZornGen7IccInputs26::configureQos(OSObject &owner,const ZornGen7OperationGuard26 &guard,
    const ZornGen7IccQosAuthority26 &authority)
{return configureQosImpl(owner,&guard,authority);}
IOReturn ZornGen7IccInputs26::configureNativeQos(OSObject &owner,const ZornGen7IccQosAuthority26 &authority)
{return configureQosImpl(owner,nullptr,authority);}
IOReturn ZornGen7IccInputs26::prepareNativeQos(OSObject &owner,bool program)
{return configureQosImpl(owner,nullptr,{},program?2:1);}
bool ZornGen7IccInputs26::nativeQosProviderHeld() const
{
    return storage_ && storage_->nativeQosMode && storage_->nativeQosOpened && storage_->nativeQosClient &&
        storage_->nativeQosParent && storage_->providers[0] && !storage_->providers[0]->isInactive() &&
        !storage_->nativeQosParent->isInactive() && !storage_->nativeQosClient->isInactive() &&
        storage_->providers[0]->getProvider()==storage_->nativeQosParent &&
        storage_->nativeQosClient->getProvider()==storage_->nativeQosParent && storage_->providers[0]->isOpen(storage_->nativeQosClient);
}
bool ZornGen7IccInputs26::claimNativeQosProvider()
{
    if(!normal() || !storage_ || !storage_->startupGate || !IORecursiveLockHaveLock(storage_->startupGate) ||
       !ml_get_interrupts_enabled())return false;auto &s=*storage_;
    auto *provider=s.providers[0];if(!provider || provider->isInactive() || s.nativeQosClient)return false;
    const auto *meta=provider->getMetaClass();if(meta!=IOPlatformDevice::metaClass && meta!=IOService::metaClass)return false;
    OSSharedPtr<IORegistryEntry> parent(provider->copyParentEntry(gIOServicePlane),OSNoRetain);
    auto *actual=OSDynamicCast(IOService,parent.get());if(!actual || actual->isInactive())return false;
    actual->retain();s.nativeQosParent=actual;s.nativeQosClient=new IOService;
    if(!s.nativeQosClient || !s.nativeQosClient->init() || !s.nativeQosClient->attach(actual))return false;
    s.nativeQosOpened=provider->open(s.nativeQosClient,0,nullptr);return nativeQosProviderHeld();
    // Actual OS single-client arbitration,not physical fabric/security access.
    // Independent full QoS window callback below remains mandatory.
}
IOReturn ZornGen7IccInputs26::configureQosImpl(OSObject &owner,const ZornGen7OperationGuard26 *guard,
    const ZornGen7IccQosAuthority26 &authority,unsigned nativeProbe)
{
    using namespace ZornGen7Clock;
    if(!normal() || !voterReady() || !storage_->startupGate || !IORecursiveLockHaveLock(storage_->startupGate) ||
       (guard && (!guard->admitMap || !guard->admitAccess || !guard->observeAccess)) ||
       (nativeProbe ? guard!=nullptr : !authority.acquireExclusiveProgrammingWindow))return kIOReturnNotReady;
    auto &s=*storage_;if(s.qosAttempted)return kIOReturnNotReady;s.qosAttempted=true;
    owner.retain();s.qosAuthorityOwner=&owner;if(guard)s.qosGuard=*guard;s.qosAuthority=authority;
    s.nativeQosMode=guard==nullptr;s.qosNativeProbe=nativeProbe;
    // As in the K80 ICC probe, own the provider before any registration.
    // Only a raw DT node promoted by this owner can enter native programming.
    OSSharedPtr<IORegistryEntry> liveGem;
    if(nativeProbe==2)liveGem=OSSharedPtr<IORegistryEntry>(IORegistryEntry::fromPath(
        "gem-noc",gIODTPlane,nullptr,nullptr,s.root),OSNoRetain);
    if(nativeProbe==2 && (!s.providerConstructed[0] || s.providers[0]!=s.nubs[0] ||
       s.nubs[0]->getProvider()!=s.platform || s.nubs[0]->getState()!=0 ||
       s.nubs[0]->getChildCount(gIOServicePlane)!=0 ||
       liveGem.get()!=s.nubs[0]))return kIOReturnExclusiveAccess;
    if(s.nativeQosMode && !claimNativeQosProvider())return kIOReturnExclusiveAccess;
    if(!nativeProbe){
        s.qosWindowRaw=s.qosAuthority.acquireExclusiveProgrammingWindow(s.qosAuthority.cookie,*s.providers[0],*s.gemDescriptor);
        s.qosWindowReturned=true;if(s.qosWindowRaw)return kIOReturnNotReady;
    }
    IOByteCount contiguous=0;
    if(s.gemDescriptor->getLength()!=gem_bytes ||
       s.gemDescriptor->getPhysicalSegment(0,&contiguous,kIOMemoryMapperNone)!=gem_physical || contiguous<gem_bytes)
        return kIOReturnNotReady;
    if(!s.nativeQosMode){
        s.qosMapGuardRaw=s.qosGuard.admitMap(s.qosGuard.cookie,*s.gemDescriptor,gem_physical,gem_bytes);
        s.qosMapGuardReturned=true;if(s.qosMapGuardRaw)return kIOReturnNotReady;
    }else if(!nativeQosProviderHeld())return kIOReturnNotOpen;
    s.qosMap=s.gemDescriptor->createMappingInTask(kernel_task,0,kIOMapAnywhere|kIOMapInhibitCache,0,gem_bytes);
    if(!s.qosMap)return kIOReturnNotReady; // Returned ownership retained even on later rejection.
    const auto at=s.qosMap->getVirtualAddress();
    if(s.qosMap->getLength()!=gem_bytes || s.qosMap->getPhysicalAddress()!=gem_physical || !at ||
       (at&3u) || at>UINTPTR_MAX-(gem_bytes-1u))return kIOReturnNotReady;
    s.qosVirtual=at;
    void *memory=IOMallocZero(sizeof(NativeCcfBulk));if(!memory)return kIOReturnNoMemory;
    s.qosBulk=::new(memory)NativeCcfBulk(*s.clockFields); // Pin before any live proxy/clock work.
    if(s.voter->acquireQosProxy(s.startupGate)!=kIOReturnSuccess)return kIOReturnNotReady;
    s.qosEnableResult=s.qosBulk->prepareEnableActual();
    if(!s.qosEnableResult.source_return_available || s.qosEnableResult.source_return ||
       s.qosEnableResult.prepare_entries_returned!=1 || s.qosEnableResult.enable_entries_returned!=1 ||
       !s.voter->sourceReady())return kIOReturnNotReady;
    unsigned index=0;uint32_t matched=0,observed=0;
    for(const auto &port:ZornGen7IccQosSource26::ports) {
        if(nativeProbe!=1 && (!qosUpdateBits(port.offset,1u<<24,port.disable<<24) ||
           !qosUpdateBits(port.offset,7u<<4,port.priority<<4) ||
           !qosUpdateBits(port.offset,1u<<3,port.urgent<<3)))return kIOReturnNotReady;
        if(nativeProbe){
            uint32_t value=0;
            if(!qosAccess(port.offset,false,value))return kIOReturnNotReady;
            constexpr uint32_t mask=(1u<<24)|(7u<<4)|(1u<<3);
            const uint32_t expected=(port.disable<<24)|(port.priority<<4)|(port.urgent<<3);
            observed|=1u<<index;
            if((value&mask)==expected)matched|=1u<<index;
            __atomic_store_n(&qosObservation,(observed<<16)|matched,__ATOMIC_RELEASE);
            ++index;
        }
    }
    if(nativeProbe==2 && matched!=observed)return kIOReturnIOError;
    // Normal successful source path only. No release/recommit on failed RMW,
    // failed enable or unavailable observation. This is not fault recovery.
    s.qosReleaseResult=s.qosBulk->disableUnprepareActual();
    if(s.qosReleaseResult.assessment!=CcfBulkReleaseAssessment::SourceVoidReturned ||
       s.qosReleaseResult.disable_entries_returned!=1 || s.qosReleaseResult.unprepare_entries_returned!=1 ||
       !s.voter->sourceReady())return kIOReturnNotReady;
    if(s.voter->recommitNormalQos(s.startupGate)!=kIOReturnSuccess)return kIOReturnNotReady;
    if(nativeProbe==1 && matched!=observed)return kIOReturnUnsupported;
    if(nativeProbe){
        s.qosVirtual=0;
        s.qosMap->release();
        s.qosMap=nullptr;
        s.providers[0]->close(s.nativeQosClient);
        s.nativeQosOpened=false;
        s.nativeQosClient->detach(s.nativeQosParent);
        s.nativeQosClient->release();
        s.nativeQosClient=nullptr;
        s.nativeQosParent->release();
        s.nativeQosParent=nullptr;
    }
    s.qosReady=true;return kIOReturnSuccess;
}
bool ZornGen7IccInputs26::qosAccess(uint32_t offset,bool write,uint32_t &value)
{
    if(!normal() || !storage_ || !storage_->startupGate || !IORecursiveLockHaveLock(storage_->startupGate))return false;
    auto &s=*storage_;
    if(s.qosAccessBusy || !s.qosAttempted || s.qosReady || !s.qosVirtual || !s.qosMap || !s.qosAuthorityOwner ||
       !s.voter || !s.voter->sourceReady() || (offset&3u) || offset>gem_bytes-4u)return false;
    bool sourceWord=false;for(const auto &port:ZornGen7IccQosSource26::ports)if(port.offset==offset)sourceWord=true;
    if(!sourceWord)return false;
    const uint32_t address=uint32_t(gem_physical+offset);s.qosAccessBusy=true;
    s.qosGuardReturned=false;s.qosPrimitiveReturned=false;s.qosObserverReturned=false;
    if(s.nativeQosMode){
        if(!nativeQosProviderHeld() ||
           (s.qosNativeProbe==1 && write) ||
           (s.qosNativeProbe==2 && (s.nubs[0]->getChildCount(gIOServicePlane)!=0 ||
             (s.nubs[0]->getState() & kIOServiceRegisteredState))) ||
           (!s.qosNativeProbe && (!s.qosWindowReturned || s.qosWindowRaw)) ||
           !ml_get_interrupts_enabled() ||
           !s.qosEnableResult.source_return_available || s.qosEnableResult.source_return ||
           s.qosEnableResult.prepare_entries_returned!=1 || s.qosEnableResult.enable_entries_returned!=1){s.qosAccessBusy=false;return false;}
    }else{
        s.qosGuardRaw=s.qosGuard.admitAccess(s.qosGuard.cookie,*s.gemDescriptor,address,4,write,write?value:0u);
        s.qosGuardReturned=true;if(s.qosGuardRaw){s.qosAccessBusy=false;return false;}
    }
    __asm__ volatile("dsb sy" ::: "memory");
    auto *reg=reinterpret_cast<volatile uint32_t *>(s.qosVirtual+offset);
    uint32_t actual=value;if(write)*reg=actual;else actual=*reg;
    __asm__ volatile("dsb sy" ::: "memory");s.qosPrimitiveReturned=true;
    if(!s.nativeQosMode){
        s.qosObserverRaw=s.qosGuard.observeAccess(s.qosGuard.cookie,*s.gemDescriptor,address,4,write,actual);
        s.qosObserverReturned=true;
    }
    s.qosAccessBusy=false;
    if((s.nativeQosMode?!nativeQosProviderHeld():s.qosObserverRaw!=0) || !s.voter->sourceReady())return false;
    if(!write)value=actual;return true; // Actual MMIO returned;no synthetic guard/observer success for native route.
}
bool ZornGen7IccInputs26::qosUpdateBits(uint32_t offset,uint32_t mask,uint32_t value)
{
    uint32_t original=0;if(!qosAccess(offset,false,original))return false;
    const uint32_t next=(original&~mask)|(value&mask);
    if(next==original)return true; // Source regmap_update_bits no-change branch performs no write.
    uint32_t actual=next;return qosAccess(offset,true,actual);
}

IOReturn ZornGen7IccInputs26::acquireTbuPower(IOService &qtb,IOService &controller)
{
    if(!normal() || !voterReady() || !storage_->startupGate || !IORecursiveLockHaveLock(storage_->startupGate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.qosReady || s.tbuAttempted || qtb.getProvider()!=&controller || qtb.isInactive() || controller.isInactive())return kIOReturnNotReady;
    OSSharedPtr<IORegistryEntry> parent(qtb.copyParentEntry(gIODTPlane),OSNoRetain);
    OSSharedPtr<OSObject> route(qtb.copyProperty("k80,source-icc-route"),OSNoRetain);
    auto *data=OSDynamicCast(OSData,route.get());
    if(parent.get()!=&controller || !data || data->getLength()!=8 || !data->getBytesNoCopy())return kIOReturnBadArgument;
    const auto *p=static_cast<const uint8_t *>(data->getBytesNoCopy());
    if(be32(p)!=0u || be32(p+4)!=512u)return kIOReturnUnsupported;
    // Exact source child has no own regulator/clock/resume metadata;its
    // genuine parent SMMU PM reference is checked independently by fence owner.
    const char *const absent[]={"clock-names","qcom,regulator-names","qcom,active-only"};
    for(const auto *key:absent){OSSharedPtr<OSObject> property(qtb.copyProperty(key),OSNoRetain);if(property)return kIOReturnUnsupported;}
    s.tbuAttempted=true;qtb.retain();controller.retain();s.tbuProvider=&qtb;s.tbuController=&controller;
    const auto raw=s.voter->setTbuPowerBandwidth(s.startupGate,true);
    if(raw!=kIOReturnSuccess)return raw;
    s.tbuHeld=true;return kIOReturnSuccess; // Real source vote return,not a hardware/security lease.
}
bool ZornGen7IccInputs26::tbuPowerHeldFor(IOService &qtb) const
{
    return storage_ && storage_->startupGate && IORecursiveLockHaveLock(storage_->startupGate) &&
        storage_->tbuHeld && !storage_->tbuReleaseAttempted && storage_->tbuProvider==&qtb &&
        storage_->tbuController && qtb.getProvider()==storage_->tbuController &&
        !qtb.isInactive() && !storage_->tbuController->isInactive() && storage_->voter && storage_->voter->sourceReady();
}
IOReturn ZornGen7IccInputs26::releaseTbuPower(IOService &qtb)
{
    if(!normal() || !tbuPowerHeldFor(qtb))return kIOReturnNotReady;auto &s=*storage_;
    s.tbuReleaseAttempted=true;const auto raw=s.voter->setTbuPowerBandwidth(s.startupGate,false);
    if(raw!=kIOReturnSuccess)return raw;s.tbuHeld=false;return kIOReturnSuccess;
}
IOReturn ZornGen7IccInputs26::applyBootstrapBandwidth()
{
    if(!normal() || !voterReady() || !storage_->startupGate || !IORecursiveLockHaveLock(storage_->startupGate) ||
       !storage_->qosReady || !storage_->bootstrapPeak)return kIOReturnNotReady;
    return storage_->voter->applyBootstrapBandwidth(storage_->startupGate,storage_->bootstrapPeak);
}

IOReturn ZornGen7IccInputs26::finishHostBootstrap()
{
    if(!normal() || !voterReady() || !storage_->startupGate || !IORecursiveLockHaveLock(storage_->startupGate) || !storage_->qosReady)return kIOReturnNotReady;
    return storage_->voter->finishHostBootstrap(storage_->startupGate);
}
IOReturn ZornGen7IccInputs26::applyHostAverageMbps(uint32_t average)
{
    if(!normal() || !voterReady() || !storage_->startupGate || !IORecursiveLockHaveLock(storage_->startupGate) || !storage_->qosReady)return kIOReturnNotReady;
    return storage_->voter->applyHostAverageMbps(storage_->startupGate,average);
}
