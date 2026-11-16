// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7ZapOwner26.h"
#include "ZornGen7HostRing26.h"
#include "ZornGen7ScmOwner26.h"
#include "ZornGen7InactiveOwner26.h"
#include "direct-ring/GpuZapLoad.h"
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <IOKit/IOLib.h>
#include <libkern/c++/OSData.h>
#include <kern/clock.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7ZapOwner26,OSObject)
namespace {
bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}
uint64_t little(const uint8_t *p,unsigned n){uint64_t v=0;for(unsigned i=0;i<n;++i)v|=uint64_t(p[i])<<(i*8);return v;}
}
extern "C" IOReturn zorn26_zap_seal_cpu_window(IOMemoryDescriptor *);
extern "C" void zorn26_zap_cpu_window_observation(uint64_t (&)[3]);
extern "C" void zorn26_native_scm_zap_observation(uint32_t (&)[4]);
static uint32_t nativeZapContext[12];
extern "C" void zorn26_native_zap_context(uint32_t (&out)[12]){memcpy(out,nativeZapContext,sizeof(out));}
static uint32_t nativeZapObservation[14];
void Zorn26RecordZapResult(IOReturn raw){nativeZapObservation[0]=uint32_t(raw);}
extern "C" void zorn26_native_zap_observation(uint32_t (&out)[14]){memcpy(out,nativeZapObservation,sizeof(out));}
struct ZornGen7ZapOwner26::Storage {
    IORecursiveLock &startup;IORegistryEntry &root;IOService &gpu;ZornGen7InactiveOwner26 &parent;
    ZornGen7HostRing26 &ring;ZornGen7ScmOwner26 &scm;OSObject &owner;const ZornGen7ZapAuthority26 authority;
    NativeAdrenoMemory metadata;NativeAdrenoCpuState cpu{};
    IORegistryEntry *gpuNode=nullptr,*scmNode=nullptr;OSObject *reservationProperty=nullptr,*noMapProperty=nullptr;
    IOMemoryDescriptor *reservation=nullptr;IOMemoryMap *map=nullptr;IOLock *waitGate=nullptr;
    uint64_t parentBase=0;size_t parentBytes=0,reservationOffset=0;volatile uint8_t *image=nullptr;
    bool attempted=false,grantReturned=false,cpuAccessEnded=false,authenticated=false;
    IOReturn grantRaw=kIOReturnNotReady,publishRaw=kIOReturnNotReady;int windowRaw=0;
    hpp_result capabilities{};hzl_result load{};hzl_config config{};
    Storage(IORecursiveLock &g,IORegistryEntry &r,IOService &v,ZornGen7InactiveOwner26 &p,
        ZornGen7HostRing26 &h,ZornGen7ScmOwner26 &s,OSObject &o,const ZornGen7ZapAuthority26 &a):
        startup(g),root(r),gpu(v),parent(p),ring(h),scm(s),owner(o),authority(a){}
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7ZapOwner26::create(IORecursiveLock &g,IORegistryEntry &r,IOService &gpu,ZornGen7InactiveOwner26 &p,
    ZornGen7HostRing26 &ring,ZornGen7ScmOwner26 &scm,OSObject &o,const ZornGen7ZapAuthority26 &a,ZornGen7ZapOwner26 *&out)
{
    if(out || !normal() || !IORecursiveLockHaveLock(&g) || !a.acquireExclusiveZapWindow || !a.checkHeldZapWindow)return kIOReturnNotReady;
    auto *z=new ZornGen7ZapOwner26;if(!z)return kIOReturnNoMemory;
    if(!z->init()){z->release();return kIOReturnNoMemory;}z->retain();z->pinned_=true;out=z;
    r.retain();gpu.retain();p.retain();ring.retain();scm.retain();o.retain();
    void *bytes=IOMallocZero(sizeof(Storage));if(!bytes)return kIOReturnNoMemory;
    z->storage_=new(bytes)Storage(g,r,gpu,p,ring,scm,o,a);z->storage_->waitGate=IOLockAlloc();
    if(!z->storage_->waitGate)return kIOReturnNoMemory;
    // Native allocations/mapping,SCM and waits never hold the startup gate.
    IORecursiveLockUnlock(&g);const auto raw=z->prepare();
    auto &s=*z->storage_;uint64_t cpu[3]{};zorn26_zap_cpu_window_observation(cpu);
    nativeZapObservation[0]=uint32_t(raw);nativeZapObservation[2]=uint32_t(s.grantRaw);nativeZapObservation[3]=uint32_t(s.windowRaw);
    nativeZapObservation[4]=s.load.code;nativeZapObservation[5]=s.load.phase;
    nativeZapObservation[6]=uint32_t(s.load.call[2].response.x[0]);nativeZapObservation[7]=uint32_t(s.load.call[2].response.x[1]);
    nativeZapObservation[8]=uint32_t(cpu[0]);nativeZapObservation[9]=uint32_t(cpu[0]>>32);
    nativeZapObservation[10]=uint32_t(cpu[1]);nativeZapObservation[11]=uint32_t(cpu[1]>>32);nativeZapObservation[12]=uint32_t(cpu[2]);
    nativeZapObservation[13]=(s.authenticated?1u:0u) | (s.cpuAccessEnded?2u:0u) | (s.map?4u:0u) |
        (s.load.call[2].attempted?8u:0u) | (s.load.call[2].valid?16u:0u) | (s.load.call[2].response_present?32u:0u);
    uint32_t scmContext[4]{};zorn26_native_scm_zap_observation(scmContext);
    for(unsigned i=0;i<4;++i)nativeZapContext[i]=scmContext[i];
    nativeZapContext[4]=(s.capabilities.code&255u) | (s.capabilities.phase<<8) |
        (s.capabilities.started?1u<<16:0u) | (s.capabilities.completed?1u<<17:0u) | (s.capabilities.guard_failed?1u<<18:0u);
    nativeZapContext[5]=s.capabilities.attempted_mask | (s.capabilities.valid_mask<<8) | (s.capabilities.available_mask<<16);
    nativeZapContext[6]=s.capabilities.supported;
    if(s.capabilities.phase && s.capabilities.phase<=HPP_QUERY_COUNT){
        const auto &q=s.capabilities.query[s.capabilities.phase-1];
        nativeZapContext[7]=(q.valid?1u:0u) | (q.attempted?2u:0u) | (q.response_present?4u:0u) |
            ((q.transport_code&255u)<<8) | (uint32_t(q.response_transport)<<16);
        nativeZapContext[8]=uint32_t(q.response.x[0]);nativeZapContext[9]=uint32_t(q.response.x[0]>>32);
        nativeZapContext[10]=uint32_t(q.response.x[1]);nativeZapContext[11]=uint32_t(q.response.x[1]>>32);
    }
    if(!raw)nativeZapObservation[1]=8;
    IORecursiveLockLock(&g);return raw;
}
IOReturn ZornGen7ZapOwner26::prepare()
{
    auto &s=*storage_;if(s.attempted || !normal() || IORecursiveLockHaveLock(&s.startup))return kIOReturnNotReady;s.attempted=true;nativeZapObservation[1]=1;
    s.gpuNode=IORegistryEntry::fromPath("arm-io/gpu",gIODTPlane,nullptr,nullptr,&s.root);
    s.scmNode=IORegistryEntry::fromPath("firmware/qcom_scm",gIODTPlane,nullptr,nullptr,&s.root);
    if(s.gpuNode!=&s.gpu || !s.scmNode)return kIOReturnNotReady;
    s.reservationProperty=s.gpu.copyProperty("zorn,zap-reservation");s.noMapProperty=s.gpu.copyProperty("zorn,zap-no-map");
    auto *reg=OSDynamicCast(OSData,s.reservationProperty),*no=OSDynamicCast(OSData,s.noMapProperty);
    if(!reg || reg->getLength()!=16 || !reg->getBytesNoCopy() || !no || no->getLength()!=4 || !no->getBytesNoCopy())return kIOReturnNotReady;
    const auto *bytes=static_cast<const uint8_t *>(reg->getBytesNoCopy());
    if(little(bytes,8)!=HZL_RESERVATION_BASE || little(bytes+8,8)!=HZL_RESERVATION_BYTES ||
       little(static_cast<const uint8_t *>(no->getBytesNoCopy()),4)!=1)return kIOReturnUnsupported;
    nativeZapObservation[1]=2;
    auto raw=NativeAdrenoQueryCpuPages(&s.cpu);if(raw)return raw;
    if(s.cpu.kernel_page_bytes!=4096 && s.cpu.kernel_page_bytes!=16384)return kIOReturnUnsupported;
    s.parentBase=HZL_RESERVATION_BASE&~(s.cpu.kernel_page_bytes-1u);
    const uint64_t end=(HZL_RESERVATION_BASE+HZL_RESERVATION_BYTES+s.cpu.kernel_page_bytes-1u)&~(s.cpu.kernel_page_bytes-1u);
    s.parentBytes=size_t(end-s.parentBase);s.reservationOffset=size_t(HZL_RESERVATION_BASE-s.parentBase);
    // Software-only <=36bit allocation ceiling follows the actual Native BO
    // backend budget;no SMMU/SCM hardware width or address is fabricated.
    const size_t budget=NativeAdrenoMemory::backingBudget(4096);if(!budget || budget!=s.cpu.kernel_page_bytes)return kIOReturnUnsupported;
    nativeZapObservation[1]=3;
    raw=s.metadata.allocate(4096,36,true,budget);if(raw)return raw;
    if(!s.metadata.descriptor() || !s.metadata.mapping() || s.metadata.spanCount()!=1 || s.metadata.ownedSpanCount()!=1 ||
       s.metadata.ownedBytes()!=budget || s.metadata.spans()[0].bytes!=4096 || s.metadata.spans()[0].offset ||
       s.metadata.ownedSpans()[0].offset || s.metadata.ownedSpans()[0].bytes!=budget ||
       s.metadata.spans()[0].physical!=s.metadata.ownedSpans()[0].physical ||
       hzl_overlap(s.metadata.ownedSpans()[0].physical,budget,s.parentBase,s.parentBytes))return kIOReturnNotReady;
    raw=s.metadata.makeWriteCombined();if(raw)return raw;
    s.reservation=IOMemoryDescriptor::withPhysicalAddress(s.parentBase,s.parentBytes,kIODirectionInOut|kIOMemoryMapperNone);
    if(!s.reservation)return kIOReturnNoMemory;
    IOByteCount contiguous=0;if(s.reservation->getLength()!=s.parentBytes ||
       s.reservation->getPhysicalSegment(0,&contiguous,kIOMemoryMapperNone)!=s.parentBase || contiguous<s.parentBytes)return kIOReturnNotReady;
    nativeZapObservation[1]=4;
    s.grantRaw=s.authority.acquireExclusiveZapWindow(s.authority.cookie,s.root,s.gpu,*s.scmNode,*s.reservation,
        *s.metadata.descriptor(),s.parentBase,s.parentBytes);s.grantReturned=true;if(s.grantRaw)return s.grantRaw;
    if(!forwardAllowed(HZL_PHASE_QUALIFY))return kIOReturnNotReady;
    nativeZapObservation[1]=5;
    s.map=s.reservation->createMappingInTask(kernel_task,0,kIOMapAnywhere|kIOMapInhibitCache,0,s.parentBytes);
    if(!s.map || s.map->getLength()!=s.parentBytes || s.map->getPhysicalAddress()!=s.parentBase ||
       !s.map->getVirtualAddress() || s.parentBytes-1>UINTPTR_MAX-s.map->getVirtualAddress())return kIOReturnNotReady;
    s.image=reinterpret_cast<volatile uint8_t *>(s.map->getVirtualAddress()+s.reservationOffset);
    nativeZapObservation[1]=6;
    s.config={s.metadata.mapping(),s.metadata.spans()[0].physical,4096,HZL_RESERVATION_BASE,HZL_RESERVATION_BYTES};
    if(!hzl_config_valid(&s.config) || !s.ring.claimInitialIdleForZap())return kIOReturnNotReady;
    nativeZapObservation[1]=7;
    return s.scm.authenticateZap(*this);
}
bool ZornGen7ZapOwner26::forwardAllowed(unsigned phase)
{
    if(!storage_ || !normal())return false;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.startup) || !s.grantReturned || s.grantRaw || !s.ring.zapWindowHealthy())return false;
    // No image read,VA query,remap or CPU cache access in this guard.
    s.windowRaw=s.authority.checkHeldZapWindow(s.authority.cookie,s.gpu,phase);return !s.windowRaw;
}
int ZornGen7ZapOwner26::queryGuard(void *p){return static_cast<ZornGen7ZapOwner26 *>(p)->forwardAllowed(HZL_PHASE_QUALIFY)?1:0;}
int ZornGen7ZapOwner26::loadGuard(void *p,unsigned phase){return static_cast<ZornGen7ZapOwner26 *>(p)->forwardAllowed(phase)?1:0;}
int ZornGen7ZapOwner26::call(void *p,ggs_regs *frame)
{
    auto &o=*static_cast<ZornGen7ZapOwner26 *>(p);if(!frame || !o.forwardAllowed(o.storage_->load.started?o.storage_->load.phase:HZL_PHASE_QUALIFY))return 1;
    return o.storage_->scm.invokeHeldZapFrame(*frame);
}
int ZornGen7ZapOwner26::delay(void *p,unsigned ms)
{
    auto &o=*static_cast<ZornGen7ZapOwner26 *>(p);if(ms!=GGS_BUSY_DELAY_MS || !o.forwardAllowed(o.storage_->load.started?o.storage_->load.phase:HZL_PHASE_QUALIFY))return 1;
    // The strict native adapter reports BUSY/WAITQ as transport refusal,so the
    // reused loader cannot replay those calls. Real delay exists for source
    // callback completeness;it never supplies success or a firmware result.
    auto &s=*o.storage_;uint64_t deadline=0;clock_interval_to_deadline(ms,NSEC_PER_MSEC,&deadline);
    IOLockLock(s.waitGate);(void)IOLockSleepDeadline(s.waitGate,&s.load,deadline,THREAD_UNINT);IOLockUnlock(s.waitGate);
    return o.forwardAllowed(s.load.started?s.load.phase:HZL_PHASE_QUALIFY)?0:1;
}
int ZornGen7ZapOwner26::publishMetadata(void *p,void *cpu,uint64_t physical,unsigned bytes)
{
    auto &o=*static_cast<ZornGen7ZapOwner26 *>(p);auto &s=*o.storage_;
    if(!o.forwardAllowed(HZL_PHASE_PUBLISH) || cpu!=s.metadata.mapping() || physical!=s.metadata.spans()[0].physical || bytes!=HZL_METADATA_BYTES)return 1;
    auto raw=s.metadata.holdForDevice();if(raw)return 1;
    s.publishRaw=s.metadata.publishForDevice(0,4096,false);__asm__ volatile("dsb sy" ::: "memory");return s.publishRaw?1:0;
}
int ZornGen7ZapOwner26::copySegment(void *p,uint64_t to,const uint8_t *from,unsigned bytes)
{
    auto &o=*static_cast<ZornGen7ZapOwner26 *>(p);auto &s=*o.storage_;
    if(!o.forwardAllowed(HZL_PHASE_COPY) || s.cpuAccessEnded || !s.image || to!=HZL_RESERVATION_BASE ||
       from!=mHoujiZapSegment || bytes!=HZL_SEGMENT_BYTES)return 1;
    for(unsigned i=0;i<bytes;++i)s.image[i]=from[i];__asm__ volatile("dsb sy" ::: "memory");
    bool same=true;for(unsigned i=0;i<bytes;++i)if(s.image[i]!=from[i])same=false;
    // NC stores+DSB are published only within the actual independent ALL-CPU
    // alias exclusion grant. Keep descriptor/map retained,but irreversibly end
    // THIS adapter's CPU image access BEFORE AUTH;no post-AUTH read/cleanup.
    s.image=nullptr;s.cpuAccessEnded=true;
    const auto sealed=zorn26_zap_seal_cpu_window(s.reservation);return same && !sealed?0:1;
}
IOReturn ZornGen7ZapOwner26::loadWithHeldScm(const ggs_state &qualified)
{
    auto &s=*storage_;if(!forwardAllowed(HZL_PHASE_QUALIFY))return kIOReturnNotReady;
    hpp_io queries{this,queryGuard,call,delay};
    if(hpp_run(&queries,&qualified,&s.capabilities) || !hzl_capabilities(&qualified,&s.capabilities))return kIOReturnNotReady;
    hzl_io load{this,loadGuard,publishMetadata,copySegment,call,delay};
    const auto code=hzl_run(&load,&s.config,&qualified,&s.capabilities,&s.load);
    if(code || !s.load.authenticated || !s.load.auth_attempted || !s.cpuAccessEnded || !s.load.call[2].valid ||
       !s.load.call[2].response_present || s.load.call[2].response.x[0] || s.load.call[2].response.x[1])return kIOReturnNotReady;
    s.authenticated=true;return kIOReturnSuccess;
    // Authentication only:CP_SET_SECURE_MODE,writebacks,NativeRing/fence/OOB
    // release are NOT supplied by successful PAS or a returned CPU grant.
}
void ZornGen7ZapOwner26::free(){if(pinned_)return;OSObject::free();}

bool ZornGen7ZapOwner26::authenticatedForRing(const ZornGen7HostRing26 &ring) const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;
    return &s.ring==&ring && s.grantReturned && !s.grantRaw && s.authenticated && s.cpuAccessEnded && !s.image &&
        s.load.phase==HZL_PHASE_DONE && s.load.code==HZL_OK && s.load.authenticated && s.load.auth_attempted &&
        s.load.call[2].attempted && s.load.call[2].valid && s.load.call[2].response_present &&
        !s.load.call[2].response_transport && !s.load.call[2].response.x[0] && !s.load.call[2].response.x[1];
    // No reserved image read or mapping is used to answer this private check.
}
