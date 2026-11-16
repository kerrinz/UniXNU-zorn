// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7ScmOwner26.h"
#include "ZornGen7ScmNormalGate26.h"
#include "ZornGen7ScmConvention.h"
#include "ZornGen7ZapOwner26.h"
#include "direct-ring/GpuZapLoad.h"
#include <IOKit/IODeviceTreeSupport.h>
#include <IOKit/IOLib.h>
#include <libkern/c++/OSData.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7ScmOwner26,OSObject);
namespace {
ZornGen7ScmOwner26 *claimedOwner=nullptr; // One pinned owner in this candidate image.
using namespace ZornGen7ColdBoot;
OperationResult unavailable(){return {Disposition::Unavailable,StatusDomain::Unavailable,0,0};}
bool normal(){constexpr uint64_t aif=(1ULL<<6)|(1ULL<<7)|(1ULL<<8);
    return preemption_enabled() && !ml_at_interrupt_context() && !(__builtin_arm_rsr64("DAIF")&aif);}
}
static uint32_t nativeScmZapObservation[4];
extern "C" void zorn26_native_scm_zap_observation(uint32_t (&out)[4]){memcpy(out,nativeScmZapObservation,sizeof(out));}
class ZornGen7ScmOwner26::Session final : public ZornGen7ColdBoot::CxScmSession {
    ZornGen7ScmOwner26 &owner_;
public:
    explicit Session(ZornGen7ScmOwner26 &owner):owner_(owner){}
private:
    OperationResult checkHeldCxRegisterSession(const IORecursiveLock &gate,
        ZornGen7ScmRegisters::Convention convention,uint32_t request,uint32_t budget) const override
    {return owner_.checkHeld(gate,convention,request,budget);}
};
struct ZornGen7ScmOwner26::Storage {
    IORegistryEntry *root=nullptr,*scmNode=nullptr,*gpuNode=nullptr;
    IOService *gpu=nullptr;OSObject *authorityOwner=nullptr,*compatibleObject=nullptr;
    const ZornGen7ScmAuthority26 authority;
    bool metadataReady=false,claimed=false,attempted=false,active=false,quarantined=false;
    bool zapAttempted=false,zapActive=false;ZornGen7ZapOwner26 *zap=nullptr;
    ZornGen7ScmRegisters::CallResult zapCall{};
    IORecursiveLock *startup=nullptr;uint32_t request=0,budget=0;
    OperationResult grant=unavailable(),operation=unavailable();bool grantReturned=false;
    ZornGen7ScmConvention::Result probe{};
    Session session;CxScmRegisterOperation *cx=nullptr;void *cxBytes=nullptr;
    Storage(ZornGen7ScmOwner26 &owner,const ZornGen7ScmAuthority26 &a):authority(a),session(owner){}
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7ScmOwner26::create(IORegistryEntry &root,IOService &gpu,OSObject &codeOwner,
    const ZornGen7ScmAuthority26 &authority,ZornGen7ScmOwner26 *&out)
{
    if(out || !normal() || !authority.acquireExclusiveCxEpoch)return kIOReturnBadArgument;
    if(!ZornGen7ScmNormalSequence26::prepare())return kIOReturnNoMemory;
    auto *owner=new ZornGen7ScmOwner26;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()){owner->release();return kIOReturnNoMemory;}
    owner->retain();owner->pinned_=true;out=owner;root.retain();gpu.retain();codeOwner.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    owner->storage_=new(memory)Storage(*owner,authority);auto &s=*owner->storage_;
    s.root=&root;s.gpu=&gpu;s.authorityOwner=&codeOwner;
    owner->gate_=IORecursiveLockAlloc();if(!owner->gate_)return kIOReturnNoMemory;
    s.scmNode=IORegistryEntry::fromPath("firmware/qcom_scm",gIODTPlane,nullptr,nullptr,&root);
    s.gpuNode=IORegistryEntry::fromPath("arm-io/gpu",gIODTPlane,nullptr,nullptr,&root);
    if(!s.scmNode || s.gpuNode!=&gpu)return kIOReturnNotReady;
    s.compatibleObject=s.scmNode->copyProperty("compatible");
    auto *data=OSDynamicCast(OSData,s.compatibleObject);
    constexpr char compatible[]="qcom,scm-v1.1\0qcom,scm";
    if(!data || data->getLength()!=sizeof(compatible) || !data->getBytesNoCopy())return kIOReturnUnsupported;
    const auto *bytes=static_cast<const uint8_t *>(data->getBytesNoCopy());
    for(size_t i=0;i<sizeof(compatible);++i)if(bytes[i]!=uint8_t(compatible[i]))return kIOReturnUnsupported;
    s.metadataReady=true;
    // Publish only complete native CPU metadata/gate. The compare-exchange
    // arbitrates this implementation's owner; it is NOT foreign SCM exclusion.
    ZornGen7ScmOwner26 *expected=nullptr;
    if(!__atomic_compare_exchange_n(&claimedOwner,&expected,owner,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))
        return kIOReturnExclusiveAccess;
    s.claimed=true;return kIOReturnSuccess;
}
OperationResult ZornGen7ScmOwner26::checkHeld(const IORecursiveLock &startup,
    ZornGen7ScmRegisters::Convention convention,uint32_t request,uint32_t budget) const
{
    if(!storage_ || !gate_ || !normal() || !IORecursiveLockHaveLock(&startup) ||
       !IORecursiveLockHaveLock(gate_) || !ZornGen7ScmNormalSequence26::heldByCurrentThread())return unavailable();
    const auto &s=*storage_; // Mutable session cells are read only under their gate.
    if(__atomic_load_n(&claimedOwner,__ATOMIC_ACQUIRE)!=this || !s.claimed || !s.active || s.quarantined ||
       s.startup!=&startup ||
       !s.grantReturned || s.grant.disposition!=Disposition::Complete ||
       s.probe.assessment!=ZornGen7ScmConvention::Assessment::Resolved || convention!=s.probe.convention ||
       request!=s.request || budget!=s.budget)return unavailable();
    return s.grant; // The actual independent returned grant, not constant success.
}
OperationResult ZornGen7ScmOwner26::initializeCxRegisters(IORecursiveLock &startup,uint32_t request,uint32_t budget)
{
    if(!storage_ || !gate_ || !normal() || !request || !budget || &startup==gate_ ||
       !IORecursiveLockHaveLock(&startup) || IORecursiveLockHaveLock(gate_) ||
       ZornGen7ScmNormalSequence26::heldByCurrentThread())return unavailable();
    auto &s=*storage_;IORecursiveLockLock(gate_);
    ZornGen7ScmNormalSequence26 sequence;
    auto finish=[&](){s.active=false;sequence.release();IORecursiveLockUnlock(gate_);return s.operation;};
    if(!s.metadataReady || !s.claimed || s.attempted ||
       __atomic_load_n(&claimedOwner,__ATOMIC_ACQUIRE)!=this)return finish();
    s.attempted=true;s.quarantined=true;s.startup=&startup;s.request=request;s.budget=budget;
    // Local serialization cannot exclude other SMC code. Acquire the actual
    // independent whole-epoch grant before a convention probe or init entry.
    s.grant=s.authority.acquireExclusiveCxEpoch(s.authority.cookie,*s.gpu,*s.scmNode,request,budget);
    s.grantReturned=true;if(s.grant.disposition!=Disposition::Complete){s.operation=s.grant;return finish();}
    // Hold through the original probe/CX operation and every interrupted continuation.
    // This lock does not replace the independent returned whole-epoch grant.
    if(!sequence.acquire())return finish();
    s.probe=ZornGen7ScmConvention::Resolve(budget);
    if(s.probe.assessment!=ZornGen7ScmConvention::Assessment::Resolved) {
        // Only the current attempted probe may supply this phase's raw return.
        const auto &call=s.probe.calls[s.probe.frameAvailable[1]?1:0];
        if(call.last_return_available && call.last_return.raw_returned) {
            s.operation.domain=StatusDomain::Platform64;s.operation.raw_status_available=1;
            s.operation.raw_status=call.last_return.raw.x0;
            if(s.probe.assessment==ZornGen7ScmConvention::Assessment::FirmwareNonzero && s.operation.raw_status)
                s.operation.disposition=Disposition::Failed;
        }
        return finish();
    }
    s.cxBytes=IOMallocZero(sizeof(CxScmRegisterOperation));if(!s.cxBytes)return finish();
    s.cx=::new(s.cxBytes) CxScmRegisterOperation(s.probe.convention,request,budget);
    s.quarantined=false;s.active=true;s.operation=s.cx->run(s.session,startup);
    if(s.operation.disposition!=Disposition::Complete)s.quarantined=true;
    // Releasing this returned CPU mutex never releases the epoch/security
    // grant or any resource. On error the pinned owner stays quarantined;
    // no raw call, probe, retry, WAITQ, reset or cleanup can be replayed.
    return finish();
}
void ZornGen7ScmOwner26::free(){if(pinned_)return;OSObject::free();}

IOReturn ZornGen7ScmOwner26::authenticateZap(ZornGen7ZapOwner26 &zap)
{
    nativeScmZapObservation[0]=1;
    nativeScmZapObservation[1]=(storage_?1u:0u) | (gate_?2u:0u) | (normal()?4u:0u) |
        ((gate_ && IORecursiveLockHaveLock(gate_))?8u:0u) | (ZornGen7ScmNormalSequence26::heldByCurrentThread()?16u:0u) |
        (preemption_enabled()?64u:0u) | (ml_at_interrupt_context()?128u:0u);
    nativeScmZapObservation[2]=uint32_t(__builtin_arm_rsr64("DAIF"));
    if(!storage_ || !gate_ || !normal() || IORecursiveLockHaveLock(gate_) ||
       ZornGen7ScmNormalSequence26::heldByCurrentThread())return kIOReturnNotReady;
    auto &s=*storage_;
    // initializeCxRegisters publishes startup under this same session gate.
    // Inspect it only after locking; HaveLock observes ownership without
    // acquiring the startup gate or reversing the startup->session order.
    IORecursiveLockLock(gate_);
    nativeScmZapObservation[0]=2;
    if(s.startup && IORecursiveLockHaveLock(s.startup)){
        nativeScmZapObservation[1]|=32u;
        IORecursiveLockUnlock(gate_);return kIOReturnNotReady;
    }
    ZornGen7ScmNormalSequence26 sequence;
    auto finish=[&](IOReturn raw){s.zapActive=false;if(raw)s.quarantined=true;sequence.release();IORecursiveLockUnlock(gate_);return raw;};
    nativeScmZapObservation[0]=3;
    nativeScmZapObservation[2]|=s.budget<<16;
    nativeScmZapObservation[3]=(s.metadataReady?1u:0u) | (s.claimed?2u:0u) | (s.quarantined?4u:0u) |
        (s.zapAttempted?8u:0u) | (s.active?16u:0u) | (s.grantReturned?32u:0u) |
        (__atomic_load_n(&claimedOwner,__ATOMIC_ACQUIRE)==this?64u:0u) |
        (s.grant.disposition==Disposition::Complete?128u:0u) | (s.operation.disposition==Disposition::Complete?256u:0u) |
        (s.probe.assessment==ZornGen7ScmConvention::Assessment::Resolved?512u:0u) |
        (s.probe.convention==ZornGen7ScmRegisters::Convention::Arm64?1024u:0u) | (s.budget?2048u:0u);
    if(!s.metadataReady || !s.claimed || s.quarantined || s.zapAttempted || s.active || !s.grantReturned ||
       __atomic_load_n(&claimedOwner,__ATOMIC_ACQUIRE)!=this || s.grant.disposition!=Disposition::Complete ||
       s.operation.disposition!=Disposition::Complete || s.probe.assessment!=ZornGen7ScmConvention::Assessment::Resolved ||
       s.probe.convention!=ZornGen7ScmRegisters::Convention::Arm64 || !s.budget)return finish(kIOReturnNotReady);
    nativeScmZapObservation[0]=4;
    if(!sequence.acquire())return finish(kIOReturnNotReady);
    s.zapAttempted=true;s.zap=&zap;s.zapActive=true;
    // Qualification derived ONLY from this retained owner's actually returned
    // convention probe+CX operation,not a caller-supplied boolean/old epoch.
    ggs_state actual{};actual.convention_verified=s.probe.assessment==ZornGen7ScmConvention::Assessment::Resolved;
    actual.available=s.operation.disposition==Disposition::Complete;actual.init_succeeded=actual.available;
    nativeScmZapObservation[0]=5;
    const auto raw=zap.loadWithHeldScm(actual);nativeScmZapObservation[0]=6;return finish(raw);
}
int ZornGen7ScmOwner26::invokeHeldZapFrame(ggs_regs &frame)
{
    using namespace ZornGen7ScmRegisters;
    if(!storage_ || !gate_ || !normal() || !IORecursiveLockHaveLock(gate_) || !ZornGen7ScmNormalSequence26::heldByCurrentThread())return 1;auto &s=*storage_;
    if(!s.zapActive || !s.zap || s.quarantined || s.probe.convention!=Convention::Arm64 || !s.budget)return 1;
    bool expected=false;ggs_regs allowed{};
    for(unsigned i=0;i<HPP_QUERY_COUNT;++i){hpp_frame(i,&allowed);bool same=true;for(unsigned j=0;j<8;++j)if(frame.x[j]!=allowed.x[j])same=false;if(same)expected=true;}
    if(frame.x[0]==0x42000201u && frame.x[1]==0x82 && frame.x[2]==13 && frame.x[3] && !frame.x[4] && !frame.x[5] && !frame.x[6] && !frame.x[7])expected=true;
    if(frame.x[0]==0x42000202u && frame.x[1]==3 && frame.x[2]==13 && frame.x[3]==HZL_RESERVATION_BASE && frame.x[4]==HZL_LOAD_SPAN && !frame.x[5] && !frame.x[6] && !frame.x[7])expected=true;
    if(frame.x[0]==0x42000205u && frame.x[1]==1 && frame.x[2]==13 && !frame.x[3] && !frame.x[4] && !frame.x[5] && !frame.x[6] && !frame.x[7])expected=true;
    if(!expected)return 1;
    ZornGen7SmcccArgs input{};for(unsigned i=0;i<8;++i)input.x[i]=frame.x[i];
    s.zapCall=InvokeWithInterruptedContinuation(&input,s.budget);
    const auto &r=s.zapCall;
    // Only actually captured result registers are updated;unused x4/x5/x7
    // remain input registers,never claimed as captured outputs.
    if(r.last_return_available && r.last_return.raw_returned){const auto &v=r.last_return.raw;
        frame.x[0]=v.x0;frame.x[1]=v.x1;frame.x[2]=v.x2;frame.x[3]=v.x3;frame.x[6]=v.x6;}
    // Existing explicit INTERRUPTED protocol budget only. BUSY/WAITQ/error
    // becomes refusal BEFORE the reused GGS transport could replay it.
    if(r.progress!=Progress::RawReturned || !r.last_return_available || !r.last_return.raw_returned ||
       r.last_return.kind!=ReturnKind::A0Zero){s.quarantined=true;return 1;}
    return 0;
}
