#include "ZornProgressGate203.h"
#include "ZornClientTrace240.h"
// SPDX-License-Identifier: MIT
#include "ZornGen7AppIo26.h"
#include "ZornGen7HostRing26.h"
#include "ZornGen7TaskAdmission26.h"
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IOLib.h>
#include <kern/task.h>
#include <kern/task_ref.h>
#include <kern/sched_prim.h>
#include <os/cpp_util.h>
#include <string.h>
#include <sys/proc.h>
#include <sys/proc_private.h>
#include "ZornApplicationObservation26.h"
#include "ZornApplicationObservation26.inc"
OSDefineMetaClassAndStructors(ZornGen7AppIoService26,IOAcceleratorES)
OSDefineMetaClassAndStructors(ZornGen7AppIoClient26,IOUserClient)
// Only scalar atomics in resident kernel storage; no object access in snapshot.
static uint32_t zornClientEvents240;
extern "C" void zorn26_client_event240(unsigned event) {
    if(event<ZornClientTraceEvents240)
        __atomic_fetch_or(&zornClientEvents240,1u<<event,__ATOMIC_RELAXED);
}
// Called by the actual application-close entry, before any Close callouts.
// Preserve discovery milestones; the upper four bits describe this close.
extern "C" void zorn26_client_close_reset242(void) {
    __atomic_fetch_and(&zornClientEvents240,0xfffffu,__ATOMIC_RELAXED);
}
extern "C" uint32_t zorn26_client_snapshot240(void) {
    return __atomic_load_n(&zornClientEvents240,__ATOMIC_RELAXED);
}
static_assert(__is_same(decltype(((IOUserClient*)nullptr)->removeMappingForDescriptor(nullptr)),IOMemoryMap*));
IOReturn ZornGen7AppIoService26::createAndPublish(ZornGen7HostRing26 &owner,OSObject &authorityOwner,const ZornGen7AppAuthority26 &authority,IOService *&out)
{
    if(out || !authority.acquire || !authority.check || !authority.release)return kIOReturnBadArgument;auto *platform=IOService::getPlatform();if(!platform)return kIOReturnNotReady;
    // Same actual publisher thread; bounded diagnostics add no service/client authority.
    if(!zorn26_gpu_diagnostic_gate203(3))return kIOReturnTimeout;
    auto *p=new ZornGen7AppIoService26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->clients_=IOLockAlloc();if(!p->clients_){p->release();return kIOReturnNoMemory;}owner.retain();p->owner_=&owner;authorityOwner.retain();p->authorityOwner_=&authorityOwner;p->authority_=authority;
    // Retain every partial after attachment has been attempted.
    out=p;
    // These are the two actual keys consumed by Metal's existing discovery.
    // They select the independently built K80 plugin only;no user-client
    // grant,IGPU type1 success,Apple hardware model or capability is invented.
#if !defined(ZORN_GEN7_APP_PROBE186)
    if(!p->setProperty("MetalPluginName","NativeAdrenoMetal") ||
       !p->setProperty("MetalPluginClassName","NativeAdrenoMetalDevice"))return kIOReturnNoMemory;
#endif
    // The qualification build discovers this exact class directly. Its retained
    // old root Metal plugin must not automatically claim this exclusive client.
    // Normal Metal builds retain the existing discovery properties above.
    if(!zorn26_gpu_diagnostic_gate203(4))return kIOReturnTimeout;
    if(!p->attach(platform) || !p->start(platform))return kIOReturnNotReady;
    p->setName("ZornGen7DirectApplicationIo");
    if(!zorn26_gpu_diagnostic_gate203(5))return kIOReturnTimeout;
    zorn26_client_event240(0);
    p->registerService();
    zorn26_client_event240(1);
    if(!zorn26_gpu_diagnostic_gate203(6))return kIOReturnTimeout;
    return kIOReturnSuccess;
}
IOReturn ZornGen7AppIoService26::setProperties(OSObject *)
{return kIOReturnUnsupported;} // normal preexisting app-service mutation refusal
void ZornGen7AppIoService26::free(){if(clients_)IOLockFree(clients_);clients_=nullptr;if(authorityOwner_)authorityOwner_->release();authorityOwner_=nullptr;if(owner_)owner_->release();owner_=nullptr;IOService::free();}
IOReturn ZornGen7AppIoService26::newUserClient(task_t task,void *security,UInt32 type,OSDictionary *properties,IOUserClient **out)
{
    zorn26_client_event240(2);
    if(out)*out=nullptr;if(!out || !owner_)return kIOReturnBadArgument;
    // Distinct application endpoint;normal XNU entitlement/MACF/filter and
    // registerOwner admission completes before any GPU acquisition. Native
    // initialization is deferred to the first actual method on this client.
    if(!task || task==kernel_task || task!=current_task() || type!=0x4147)return kIOReturnNotPermitted;
    zorn26_client_event240(3);
    const auto serviceAdmission=ZornGen7AdmitTaskService26(*this,task,type);
    zorn26_client_event240(4);
    if(serviceAdmission)return serviceAdmission; // no GPU attempt and no consumed session
    if(!clients_)return kIOReturnNotReady;IOLockLock(clients_);
    if(reserved_){IOLockUnlock(clients_);return kIOReturnExclusiveAccess;}
    reserved_=true;IOLockUnlock(clients_);
    zorn26_client_event240(5);
    auto *p=new ZornGen7AppIoClient26;if(!p){returnClientSlot(nullptr);return kIOReturnNoMemory;}
    zorn26_client_event240(6);
    if(!p->initWithTask(task,security,type,properties)){p->release();returnClientSlot(nullptr);return kIOReturnNoMemory;}
    // Real client identity owns this reservation;ordinary metadata-only
    // rejection/free can return it. Failed native acquisition cannot.
    zorn26_client_event240(7);
    retain();p->service_=this;IOLockLock(clients_);client_=p;IOLockUnlock(clients_);
    task_reference(task);p->openingTask_=task;
    p->serial_=IOLockAlloc();p->views_=IONewZero(ZornGen7AppIoClient26::View,ZornGen7AppIoClient26::ViewCount);
    if(!p->serial_ || !p->views_){p->release();return kIOReturnNoMemory;}
    owner_->retain();p->owner_=owner_;authorityOwner_->retain();p->authorityOwner_=authorityOwner_;p->authority_=authority_;
    // No native acquisition yet:normal IOKit failure may free this object.
    zorn26_client_event240(8);
    if(!p->attach(this)){p->release();return kIOReturnNotReady;}
    zorn26_client_event240(9);
    if(!p->start(this)){p->detach(this);p->release();return kIOReturnNotReady;}
    zorn26_client_event240(10);
    const auto clientAdmission=ZornGen7AdmitTaskClient26(*p,p->openingTask_,type);
    zorn26_client_event240(11);
    if(clientAdmission){
        // No GPU session/table/BO has been created. This unpublished client
        // has only normal IOKit metadata/task/filter references to unwind.
        p->stop(this);p->detach(this);p->release();
        return clientAdmission;
    }
    zorn26_client_event240(12);
    p->live_=true;*out=p;
    if(auto process=static_cast<proc_t>(get_bsdtask_info(task)))
        appObservationBind(reinterpret_cast<uintptr_t>(p),proc_uniqueid(process),uint32_t(proc_pid(process)));
    zorn26_client_event240(13);
    return kIOReturnSuccess;
    // No actual GPU/native operation here. A mandatory real authority provider
    // is retained,not manufactured;this candidate is not yet published/bound.
}
void ZornGen7AppIoService26::returnClientSlot(ZornGen7AppIoClient26 *actual)
{
    if(!clients_)return;IOLockLock(clients_);
    if(reserved_ && client_==actual){client_=nullptr;reserved_=false;}
    IOLockUnlock(clients_);
    // Software slot only. Caller must have either attempted no native work,
    // or completed actual process/OOB/authority close successfully.
}
bool ZornGen7AppIoClient26::matchesOwnedSession(const ZornGen7HostRing26 &ring,const IOService *service,
    task_t task,bool closing) const
{
    return owner_==&ring && service_ && service_==service && getProvider()==service_ &&
        openingTask_==task && task && task!=kernel_task && live_ && attempted_ && pinned_ &&
        serial_ && views_ && !viewError_ && (closing?
        (closing_ && closingThread_==current_thread() && closingThread_!=THREAD_NULL):!closing_);
    // Called only by the retained actual Ring inside this serialized client's
    // method/close. Kernel task may close only this exact ongoing clientClose.
}
IOReturn ZornGen7AppIoClient26::ensureProcess()
{
    // Caller holds serial_;there is no acquire retry or failed partial cleanup.
    zorn26_client_event240(14);
    if(attempted_)return attemptRaw_;
    retain();pinned_=true;attempted_=true; // keep actual partials from the first authority call onward
    zorn26_client_event240(15);
    attemptRaw_=owner_->prepareApplicationExecution(*this,openingTask_,0x4147,*authorityOwner_,authority_,execution_);
    zorn26_client_event240(16);
    if(!attemptRaw_)appObservationEvent(reinterpret_cast<uintptr_t>(this),2,0,0);
    if(!attemptRaw_)attemptRaw_=owner_->acquireApplicationOob(*this,*execution_);
    if(!attemptRaw_)appObservationEvent(reinterpret_cast<uintptr_t>(this),4,0,0);
    if(!attemptRaw_)attemptRaw_=owner_->openApplicationProcess(*this,*execution_,process_);
    appObservationEvent(reinterpret_cast<uintptr_t>(this),attemptRaw_?0:8,0,uint32_t(attemptRaw_));
    return attemptRaw_;
}
IOReturn ZornGen7AppIoClient26::dropViews(uint32_t token)
{
    if(viewError_)return viewError_;if(token>ViewCount)return kIOReturnBadArgument;
    for(size_t i=0;i<ViewCount;++i){auto &v=views_[i];if(!v.descriptor || (token && token!=i+1))continue;
        while(auto *mapping=removeMappingForDescriptor(v.descriptor)){
            const auto raw=mapping->unmap();if(raw){v.quarantine=mapping;viewError_=raw;return raw;}mapping->release();
        }
        v.descriptor->release();v.descriptor=nullptr;
    }
    return kIOReturnSuccess;
}
IOReturn ZornGen7AppIoClient26::run(uint32_t method,const void *input,size_t inputBytes,void *output,size_t outputBytes)
{
    zorn26_client_event240(17);
    if(!serial_)return kIOReturnNotReady;IOLockLock(serial_);auto done=[&](IOReturn raw){appObservationEvent(reinterpret_cast<uintptr_t>(this),0,method,uint32_t(raw));IOLockUnlock(serial_);return raw;};
    if(!live_ || closing_ || viewError_ || !owner_ || !openingTask_)return done(kIOReturnNotReady);
    if(current_task()!=openingTask_)return done(kIOReturnNotPermitted);
    const auto prepared=ensureProcess();if(prepared)return done(prepared);
    if(method==NativeAdrenoMethodBoCpuUnmap && input && inputBytes==sizeof(NativeAdrenoAbiBoCpuUnmap)){
        NativeAdrenoAbiBoCpuUnmap request{};memcpy(&request,input,sizeof(request));uint32_t leases=0;
        auto raw=owner_->applicationIoLeases(*this,*execution_,*process_,request,leases);if(raw)return done(raw);
        if(leases<=1){raw=dropViews(request.token);if(raw)return done(raw);}
    }
    return done(owner_->dispatchApplicationProcess(*this,*execution_,*process_,method,input,inputBytes,output,outputBytes));
}
IOReturn ZornGen7AppIoClient26::action(OSObject *object,void *,IOExternalMethodArguments *args)
{
    zorn26_client_event240(18);
    auto *p=OSDynamicCast(ZornGen7AppIoClient26,object);if(!p || !args)return kIOReturnBadArgument;
    const auto raw=p->run(args->selector,args->structureInput,args->structureInputSize,args->structureOutput,args->structureOutputSize);
    zorn26_application_native_return225(reinterpret_cast<uintptr_t>(p),reinterpret_cast<uintptr_t>(args),args->selector,2,uint32_t(raw));
    return raw;
}
IOReturn ZornGen7AppIoClient26::externalMethod(uint32_t selector,IOExternalMethodArguments *args,IOExternalMethodDispatch *,OSObject *,void *)
{
    zorn26_client_event240(19);
    static const IOExternalMethodDispatch table[]={
        {action,0,0,0,sizeof(NativeAdrenoAbiParams)},
        {action,0,sizeof(NativeAdrenoAbiBoAlloc),0,sizeof(NativeAdrenoAbiBoAllocReply)},
        {action,0,sizeof(NativeAdrenoAbiBoMap),0,sizeof(NativeAdrenoAbiBoMapReply)},
        {action,0,sizeof(NativeAdrenoAbiBoFree),0,0},
        {action,0,sizeof(NativeAdrenoAbiSubmit),0,sizeof(NativeAdrenoAbiSubmitReply)},
        {action,0,sizeof(NativeAdrenoAbiWaitFence),0,0},
        {action,0,0,0,sizeof(NativeAdrenoAbiTimestamp)},
        {action,0,0,0,sizeof(NativeAdrenoAbiStatus)},
        {action,0,sizeof(NativeAdrenoAbiMetadata),0,0},
        {action,0,sizeof(NativeAdrenoAbiMetadata),0,sizeof(NativeAdrenoAbiMetadata)},
        {action,0,sizeof(NativeAdrenoAbiQueue),0,sizeof(NativeAdrenoAbiQueueReply)},
        {action,0,sizeof(NativeAdrenoAbiQueue),0,0},
        {action,0,sizeof(NativeAdrenoAbiBoCpuMap),0,sizeof(NativeAdrenoAbiBoCpuMapReply)},
        {action,0,sizeof(NativeAdrenoAbiBoCpuUnmap),0,0},
        {action,0,0,0,sizeof(NativeAdrenoAbiDeviceInfo)},
        {action,0,sizeof(NativeAdrenoAbiBoImport),0,sizeof(NativeAdrenoAbiBoAllocReply)},
        {action,0,sizeof(NativeAdrenoAbiSubmitBatch),0,sizeof(NativeAdrenoAbiSubmitReply)}};
    if(selector<1 || selector>sizeof(table)/sizeof(table[0]))return kIOReturnUnsupported;
    zorn26_application_native_return225(reinterpret_cast<uintptr_t>(this),reinterpret_cast<uintptr_t>(args),selector,1,0);
    const auto raw=IOUserClient::externalMethod(selector,args,const_cast<IOExternalMethodDispatch *>(&table[selector-1]),this,nullptr);
    zorn26_application_native_return225(reinterpret_cast<uintptr_t>(this),reinterpret_cast<uintptr_t>(args),selector,3,uint32_t(raw));
    return raw;
}
IOReturn ZornGen7AppIoClient26::clientMemoryForType(UInt32 token,IOOptionBits *options,IOMemoryDescriptor **out)
{
    if(out)*out=nullptr;if(!out || !options || !serial_ || !token || token>ViewCount)return kIOReturnBadArgument;
    IOLockLock(serial_);auto done=[&](IOReturn raw){IOLockUnlock(serial_);return raw;};
    if(!live_ || closing_ || viewError_ || !execution_ || !process_ || attemptRaw_)return done(kIOReturnNotReady);
    if(current_task()!=openingTask_)return done(kIOReturnNotPermitted);
    // Recheck a cached view too;quarantined or retired backing cannot grant a
    // new CPU lease. The descriptor identity is retained across XNU unmap.
    IOMemoryDescriptor *actual=nullptr;auto raw=owner_->copyApplicationIoView(*this,*execution_,*process_,token,actual);if(raw)return done(raw);
    auto &view=views_[token-1];if(view.descriptor)actual->release();else view.descriptor=actual;
    view.descriptor->retain();*out=view.descriptor;*options=kIOMapAnywhere|kIOMapWriteCombineCache;return done(kIOReturnSuccess);
}
IOReturn ZornGen7AppIoClient26::clientClose()
{
    if(!serial_)return kIOReturnNotReady;IOLockLock(serial_);
    if(!live_ || closing_ || viewError_){IOLockUnlock(serial_);return kIOReturnNotReady;}
    closing_=true;closingThread_=current_thread();
    // No acquisition attempted means normal metadata-only close. A failed
    // or partial attempt remains pinned;do not invent a rollback/release.
    auto raw=attempted_?attemptRaw_:kIOReturnSuccess;
    if(!raw)raw=dropViews(0);
    if(!raw)appObservationEvent(reinterpret_cast<uintptr_t>(this),16,0,0);
    if(!raw && attempted_)raw=owner_->closeApplicationProcess(*this,*execution_,process_);
    if(!raw && attempted_)appObservationEvent(reinterpret_cast<uintptr_t>(this),32,0,0);
    if(!raw && attempted_)raw=owner_->releaseApplicationOob(*this,*execution_);
    if(!raw && attempted_)appObservationEvent(reinterpret_cast<uintptr_t>(this),64,0,0);
    if(!raw && attempted_)raw=owner_->closeApplicationExecution(*this,execution_);
    appObservationEvent(reinterpret_cast<uintptr_t>(this),(!raw && attempted_)?128:0,0,uint32_t(raw),true);
    task_t task=TASK_NULL;if(!raw){live_=false;task=openingTask_;openingTask_=TASK_NULL;}
    IOLockUnlock(serial_);
    if(!raw){if(service_)service_->returnClientSlot(this);if(task)task_deallocate(task);terminate();if(pinned_){pinned_=false;release();}}return raw;
}
void ZornGen7AppIoClient26::free()
{
    // A live/failed object has an explicit pin and must not reach free(). Do
    // not silently release descriptors/backing still possibly visible to VM.
    if(views_ && (!live_ || !attempted_) && !viewError_){IODelete(views_,View,ViewCount);views_=nullptr;}
    if(service_ && !attempted_)service_->returnClientSlot(this);
    if(service_)service_->release();service_=nullptr;
    if(serial_)IOLockFree(serial_);serial_=nullptr;
    if(openingTask_){task_deallocate(openingTask_);openingTask_=TASK_NULL;}
    if(authorityOwner_)authorityOwner_->release();authorityOwner_=nullptr;
    if(owner_)owner_->release();owner_=nullptr;IOUserClient::free();
}
