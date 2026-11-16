static unsigned zornRuntimeObservation[24];
extern "C" void Zorn26RecordRuntimeResult(unsigned raw){zornRuntimeObservation[0]=raw;}
extern "C" void zorn26_native_runtime_observation(unsigned (&out)[24]){for(unsigned i=0;i<24;i++)out[i]=zornRuntimeObservation[i];}
// SPDX-License-Identifier: GPL-2.0-only
#include "ZornGen7SmmuDomain26.h"
#include "ZornGen7ProcessTables26.h"
#include "ZornGen7HostRing26.h"
#include "ZornGen7DirectRuntimeAuthority26.h"
#include "direct-runtime/ZornGen7DirectSubmit26.h"
#include "ZornGen7NativeDtEntry26.h"
#include "ZornGen7SmmuFwspecSource26.inc"
#include "ZornGen7SmmuCapabilitySource26.inc"
#include "ZornGen7SmmuDmaSource26.inc"
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7AtomicSmmuIo26.h"
#include "ZornGen7SmmuTablePages26.h"
#include "ZornGen7HostGpuTables26.h"
#include "ZornGen7GpuMmuAuthority26.h"
#include "ZornGen7IccInputs26.h"
#include "ZornGen7SmmuProgramIo26.h"
#include "ZornGen7SmmuFaultIrq26.h"
#include "ZornGen7SmmuColdController26.h"
#include "ZornGen7SmmuStream26.h"
#include "ZornGen7BootBuffers26.h"
#include "ZornGen7HwschedBuffers26.h"
#include "ZornGen7HwschedHfi26.h"
#include "ZornGen7GmuIrq26.h"
#include "ZornGen7GmuLoadAuthority26.h"
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IOKitKeys.h>
#include <libkern/c++/OSArray.h>
#include <kern/cpu_data.h>
#include <pexpert/pexpert.h>
extern unsigned long gPhysBase,gPhysSize;
extern "C" vm_offset_t ml_io_map(vm_offset_t, vm_size_t);
#include "HoujiFullHostNativeMemory.h"
#include "vendor/Ace5Gmu/giulia_gpu_memory.h"
#include <IOKit/IODeviceTreeSupport.h>
#include <IOKit/IOLib.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSSharedPtr.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7SmmuDomain26,OSObject)

static uint64_t zornGmuContextIrqSnapshot;
static unsigned zornGmuStreamActivationSnapshot;
static uint32_t zornHostMmuPreflightSnapshot;
static uint32_t zornHostStreamSnapshot;
static uint32_t zornHostStreamTrace[2];
void Zorn26TraceHostStream(unsigned bank,unsigned stage,int raw)
{
    if(bank<2)__atomic_store_n(&zornHostStreamTrace[bank],(stage<<24)|(uint32_t(raw)&0x00ffffffu),__ATOMIC_RELEASE);
}
extern "C" uint32_t zorn26_host_stream_trace(unsigned bank)
{
    return bank<2?__atomic_load_n(&zornHostStreamTrace[bank],__ATOMIC_ACQUIRE):0;
}

extern "C" uint32_t zorn26_host_stream_observation()
{
    return __atomic_load_n(&zornHostStreamSnapshot,__ATOMIC_ACQUIRE);
}
static uint32_t zornHostActlrSnapshot[2];

IOReturn ZornGen7SelectActlr(IOService &,uint32_t,bool &,uint32_t &);

void Zorn26ObserveHostActlr(unsigned bank,uint32_t progress,uint32_t readback)
{
    if(bank<2)
        __atomic_store_n(&zornHostActlrSnapshot[bank],(progress<<28)|(readback&0x0fffffffu),__ATOMIC_RELEASE);
}

extern "C" uint32_t zorn26_host_actlr_observation(unsigned bank)
{
    return bank<2?__atomic_load_n(&zornHostActlrSnapshot[bank],__ATOMIC_ACQUIRE):0;
}

void Zorn26RecordHostMmuFence(uint32_t steps,IOReturn raw)
{
    __atomic_store_n(&zornHostMmuPreflightSnapshot,(steps<<24)|(uint32_t(raw)&0x00ffffffu),__ATOMIC_RELEASE);
}

extern "C" uint32_t zorn26_host_mmu_preflight_observation()
{
    return __atomic_load_n(&zornHostMmuPreflightSnapshot,__ATOMIC_ACQUIRE);
}
using ZornGmuDeferredSmr = unsigned (*)(ZornGen7SmmuDomain26 &);
static ZornGen7SmmuDomain26 *zornGmuDeferredOwner;
static ZornGmuDeferredSmr zornGmuDeferredSmr;
using ZornGmuTcmVerified = unsigned (*)(OSObject &, ZornGen7SmmuDomain26 &, const uint32_t (&)[5]);
static OSObject *zornGmuTcmBoard;
static ZornGen7SmmuDomain26 *zornGmuTcmDomain;
static ZornGmuTcmVerified zornGmuTcmVerified;
using ZornHostMmuFence = IOReturn (*)(ZornGen7SmmuDomain26 &,OSObject &,ZornGen7IccInputs26 &,unsigned,uint32_t &);
using ZornHostFenceHandoff = unsigned (*)(OSObject &,ZornGen7SmmuDomain26 &,ZornHostMmuFence);
static ZornHostFenceHandoff zornHostFenceHandoff;
static OSObject *zornHostZeroOwner;
static NativeAdrenoMemory *zornHostZero;

void Zorn26BindPreparedGpuZero(OSObject &owner,NativeAdrenoMemory &zero)
{
    // The CPU-side table preparation is single-shot on the startup thread.
    if(zornHostZeroOwner)return;
    owner.retain();
    zornHostZeroOwner=&owner;
    zornHostZero=&zero;
}


// Only the actual board owner registers this under the shared startup gate.
// The deferred owner release/acquire publication orders these fields.
void Zorn26RegisterGmuTcmHandoff(ZornGen7SmmuDomain26 &domain, OSObject &board,
    ZornGmuTcmVerified verified,ZornHostFenceHandoff fence)
{
    board.retain();
    zornGmuTcmDomain = &domain;
    zornGmuTcmBoard = &board;
    zornGmuTcmVerified = verified;
    zornHostFenceHandoff = fence;
}
extern "C" unsigned zorn26_gmu_validate_smr_after_checkpoint()
{
    auto *owner=__atomic_exchange_n(&zornGmuDeferredOwner,nullptr,__ATOMIC_ACQ_REL);
    if (!owner) return 0;
    const unsigned result=zornGmuDeferredSmr(*owner);
    owner->release();
    return result;
}

extern "C" unsigned zorn26_gmu_stream_activation_snapshot()
{
    return __atomic_load_n(&zornGmuStreamActivationSnapshot,__ATOMIC_ACQUIRE);
}
extern "C" uint64_t zorn26_gmu_context_irq_snapshot()
{
    return __atomic_load_n(&zornGmuContextIrqSnapshot, __ATOMIC_ACQUIRE);
}
namespace {
using namespace ZornGen7ColdBoot;
constexpr OperationResult unavailable{Disposition::Unavailable,StatusDomain::Unavailable,0,0};
OperationResult rawResult(int32_t raw)
{return {raw?Disposition::Failed:Disposition::Complete,StatusDomain::Platform32,1,uint32_t(raw)};}
bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}
uint32_t little(const uint8_t *p)
{return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
IOReturn validateGpuQtbRange(IOService &provider,uint32_t packed0,uint32_t packed1)
{
    OSSharedPtr<OSObject> range(provider.copyProperty("qcom,stream-id-range"),OSNoRetain),
        ports(provider.copyProperty("qcom,num-qtb-ports"),OSNoRetain);
    auto *r=OSDynamicCast(OSData,range.get());auto *n=OSDynamicCast(OSData,ports.get());
    if(!r || r->getLength()!=8 || !r->getBytesNoCopy() || !n || n->getLength()!=4 || !n->getBytesNoCopy())
        return kIOReturnBadArgument;
    const auto *rp=static_cast<const uint8_t *>(r->getBytesNoCopy());
    const auto *np=static_cast<const uint8_t *>(n->getBytesNoCopy());
    const uint32_t first=little(rp),count=little(rp+4),portCount=little(np);
    if(first!=0 || count!=0x400u || portCount!=2u)return kIOReturnUnsupported;
    const uint32_t ids[]={packed0,packed1};
    for(uint32_t packed:ids) {
        const uint32_t sid=packed&0xffffu,mask=packed>>16;
        if(mask || sid<first || sid-first>=count)return kIOReturnUnsupported;
    }
    return kIOReturnSuccess;
}
bool matches(IORegistryEntry &entry,const ZornGen7SmmuFwspecSource26::Node &expected)
{
    for(size_t i=0;i<expected.count;++i) {
        const auto &p=expected.properties[i];OSSharedPtr<OSObject> object(entry.copyProperty(p.key),OSNoRetain);
        auto *data=OSDynamicCast(OSData,object.get());
        if(!data || data->getLength()!=p.count || (p.count && !data->getBytesNoCopy()))return false;
        const auto *bytes=static_cast<const uint8_t *>(data->getBytesNoCopy());
        for(size_t k=0;k<p.count;++k)if(bytes[k]!=p.bytes[k])return false;
    }
    return true;
}
IOReturn consumerBypassAttributes(IORegistryEntry &root,IORegistryEntry &consumer,uint32_t &out)
{
    using namespace ZornGen7SmmuDmaSource26;
    OSSharedPtr<IORegistryEntry> node(&consumer,OSRetain);
    // Startup owns frozen native topology. A bounded, unexpected ancestry or
    // unsupported dma-mem redirect rejects instead of guessing a DMA parent.
    for(unsigned depth=0;node && depth<32;++depth) {
        OSSharedPtr<OSObject> coherent(node->copyProperty("dma-coherent"),OSNoRetain);
        if(coherent){out=coherent_attributes;return kIOReturnSuccess;}
        OSSharedPtr<OSObject> noncoherent(node->copyProperty("dma-noncoherent"),OSNoRetain);
        if(noncoherent){out=noncoherent_attributes;return kIOReturnSuccess;}
        OSSharedPtr<OSObject> names(node->copyProperty("interconnect-names"),OSNoRetain);
        if(names) {
            auto *data=OSDynamicCast(OSData,names.get());
            if(!data || (data->getLength() && !data->getBytesNoCopy()))return kIOReturnBadArgument;
            const auto *bytes=static_cast<const uint8_t *>(data->getBytesNoCopy());
            for(size_t at=0;at<data->getLength();) {
                size_t end=at;while(end<data->getLength() && bytes[end])++end;
                if(end==data->getLength())return kIOReturnBadArgument;
                if(end-at==7 && bytes[at]=='d' && bytes[at+1]=='m' && bytes[at+2]=='a' &&
                   bytes[at+3]=='-' && bytes[at+4]=='m' && bytes[at+5]=='e' && bytes[at+6]=='m')
                    return kIOReturnUnsupported;
                at=end+1;
            }
        }
        if(node.get()==&root) {
            out=profile_default_coherent?coherent_attributes:noncoherent_attributes;
            return kIOReturnSuccess;
        }
        node=OSSharedPtr<IORegistryEntry>(node->copyParentEntry(gIODTPlane),OSNoRetain);
    }
    return kIOReturnBadArgument;
}
}
namespace {
bool exactGmuImage(const ZornSmmuSparse4KContextImage &got,const ZornSmmuSparse4KContextImage &want)
{
    return got.cbar==want.cbar && got.cba2r==want.cba2r && got.tcr==want.tcr && got.tcr2==want.tcr2 &&
        got.mair0==want.mair0 && got.mair1==want.mair1 && got.sctlr==want.sctlr && !got.reserved_zero &&
        got.ttbr0==want.ttbr0 && got.ttbr1==want.ttbr1;
}
// K80 v113 observed only these one-direction changes on the native,
// unswitched GMU context. Compare every other field exactly.
bool nativeGmuImage(const ZornSmmuSparse4KContextImage &got,
    const ZornSmmuSparse4KContextImage &want, bool qualifiedNative)
{
    if (!qualifiedNative) return exactGmuImage(got,want);
    auto normalized=got;
    normalized.tcr2 &= ~(got.tcr2 & ~want.tcr2 & UINT32_C(0x60));
    normalized.sctlr |= want.sctlr & ~got.sctlr & UINT32_C(0x1000);
    return exactGmuImage(normalized,want);
}
}
struct ZornGen7SmmuDomain26::Storage {
    IOService &controller;ZornGen7SmmuRuntimePm26 &pm;const ArmSmmu4KIo io;
    IORecursiveLock &gate;const ZornGen7SmmuBankAuthority26 authority;
    const ZornGen7Smmu::ControllerPower::Reference *power=nullptr;
    ZornGen7QtbFence26 *native_qtb_owner=nullptr;IOPlatformDevice *native_qtb_provider=nullptr;
    ZornGen7QtbFenceResult26 native_qtb_result{};bool native_qtb_attempted=false;
    ZornGen7QtbFence26 *host_gpu_qtb_owner=nullptr;IOPlatformDevice *host_gpu_qtb_provider=nullptr;
    ZornGen7QtbFenceResult26 host_gpu_qtb_result{};bool host_gpu_qtb_attempted=false,host_gpu_qtb_released=false;
    bool native_controller_mode=false;
    bool nativeControllerClaimHeld() const {
        // Runtime PM retains the exact controller, original exclusive client,
        // parent, powered reference and startup gate. A second client cannot
        // open the same base IOService while that claim is held.
        return native_controller_mode && pm.nativeHeldFor(controller, gate);
    }
    uint32_t identification_reads=0;
    uint32_t id0=0,id1=0,id2=0,banks=0,s2banks=0;bool reserved[256]{};
    unsigned register_shift=0,s1_input_bits=0,s1_output_bits=0,physical_output_bits=0;
    uint32_t streamid_mask=0,mapping_groups=0;
    size_t register_stride=0,register_pages=0,context_base=0;
    bool three_level=false,coherent_walk=false,stream_matching=false;
    bool ready=false,stopped=false,busy=false;OperationResult last=unavailable;
    volatile uint32_t irq_faulted=0;
    bool failed() const {return stopped || __atomic_load_n(&irq_faulted,__ATOMIC_ACQUIRE)!=0;}
    bool global_fault_attempted=false,global_fault_ready=false;
    bool controller_start_attempted=false,cold_grant_returned=false;int cold_grant_raw=0;
    OSObject *cold_authority_owner=nullptr;ZornGen7SmmuColdAuthority26 cold_authority{};
    ZornGen7SmmuCold26::Geometry cold_geometry{};ZornGen7SmmuCold26::Result cold_result{};
    IOReturn cold_raw=kIOReturnNotReady;bool cold_returned=false;
    ZornGen7SmmuFaultIrq26 *global_fault_owner=nullptr;
    ZornGen7SmmuFaultIrq26 *native_global_masked_irq=nullptr;
    bool native_global_irq_attempted=false;ArmSmmu4KIo native_global_fault_io{};
    bool global_grant_returned=false;int global_grant_raw=0;
    uint32_t global_cr0_before=0,global_cr0_expected=0,global_cr0_readback=0;
    bool global_sync_write_returned=false,global_sync_read_returned=false,global_cr0_write_returned=false;
    int global_sync_write_raw=0,global_sync_read_raw=0,global_cr0_write_raw=0;
    unsigned global_sync_reads=0;uint32_t global_sync_status=0;
    bool gmu_fault_irq_attempted=false,gmu_fault_irq_ready=false;
    bool stream_slots[256]{};bool gmu_stream_attempted=false,gmu_stream_ready=false;
    bool gmu_activation_attempted=false,gmu_activation_ready=false;
    ZornSmmuSparse4KStatus activation_before_status=ZornSmmuSparse4KArgument;
    ZornSmmuSparse4KStatus activation_after_status=ZornSmmuSparse4KArgument;
    ZornSmmuSparse4KProgramResult activation_before{},activation_after{};
    bool gmu_program_attempted=false,gmu_program_ready=false;
    ZornSmmuSparse4KStatus gmu_program_status=ZornSmmuSparse4KArgument;
    ZornSmmuSparse4KProgramResult gmu_program{};
    struct Endpoint {
        IORegistryEntry *node=nullptr,*original=nullptr;IOService *consumer=nullptr;
        OSObject *property=nullptr;uint32_t packed=0;Reservation reservation{};
        ZornGen7AtomicSmmuIo26 *atomic_owner=nullptr;ArmSmmu4KIo atomic_io{};
        ZornGen7SmmuProgramIo26 program_route{};
        ZornGen7SmmuFaultIrq26 *fault_owner=nullptr;
        ZornGen7SmmuStream26 *stream_owner=nullptr;
        ZornGen7SmmuTablePages26 *tables=nullptr;ZornGen7SmmuTablePages26::PageHandle root{};
        ZornSmmuSparse4KLiveArena arena{};ZornSmmuSparse4KLiveState state{};
        ZornSmmuSparse4KLiveVisibility visibility{};ZornSmmuSparse4KLiveResult audit{};
        ZornSmmuSparse4KStatus sparse_status=ZornSmmuSparse4KArgument;
        ZornSmmuSparse4KContextConfig context{};ZornSmmuSparse4KContextImage image{};
        ZornSmmuSparse4KStatus image_status=ZornSmmuSparse4KArgument;
        uint32_t requested_actlr=0;bool requested_actlr_present=false,image_ready=false;
    } endpoints[3]{};
    bool host_gpu_tables_attempted=false,host_gpu_tables_ready=false;ZornGen7HostGpuTables26 *host_gpu_tables=nullptr;
    bool host_gpu_mmu_attempted=false,host_gpu_mmu_ready=false;unsigned host_gpu_mmu_poll_budget=0;
    bool runtime_attempted=false,runtime_active=false,runtime_ready=false,runtime_grant_returned=false,
        runtime_mapping_halted=false,runtime_attach_quiesced=false,runtime_attach_metadata_only=false;
    ZornGen7HostRing26 *runtime_boot=nullptr;
    bool host_runtime_mutation=false;thread_t runtime_transaction_thread=THREAD_NULL;
    bool host_process_transition=false,host_process_write_root=false,host_process_invalidate=false;
    uint64_t host_process_ttbr0=0;uint16_t host_process_asid=0;
    ZornGen7ProcessTables26 *runtime_process=nullptr;uint16_t runtime_process_asid=0;
    ZornGen7ProcessTables26 *process_submission_owner=nullptr;
    thread_t process_submission_thread=THREAD_NULL;unsigned process_submission_depth=0;
    int runtime_grant_raw=0;IOReturn runtime_route_raw=kIOReturnNotReady;
    OSObject *runtime_owner=nullptr;ZornGen7DirectRuntimeAuthority26 runtime_authority{};ZornGen7DirectVm26Routes runtime_routes{};
    bool native_host_runtime_ready=false,host_post_cp_access=false,host_runtime_observation=false;
    bool post_cp_context_attempted=false,post_cp_context_ready=false,post_cp_restore_needed=false,post_cp_grant_returned=false;
    int post_cp_grant_raw=0;uint32_t post_cp_expected_tcr=0,post_cp_observed_tcr=0;
    OSObject *host_gpu_mmu_owner=nullptr;ZornGen7GpuMmuAuthority26 host_gpu_mmu_authority{};
    bool host_gpu_mmu_grant_returned=false;int host_gpu_mmu_grant_raw=0;
    uint16_t host_banks[2]{},host_asids[2]{};uint32_t host_bypass[2]{},prr_before[2]{},prr_after[2]{};
    uint32_t prr_expected[2]{},host_actlr_before[2]{},host_actlr_after[2]{};
    IOReturn zero_publish_raw=kIOReturnNotReady,zero_hold_raw=kIOReturnNotReady;
    bool zero_publish_returned=false,zero_hold_returned=false;
    NativeAdrenoMemory *host_zero=nullptr;uint64_t host_zero_physical=0;
    int prr_read_raw[2]{},prr_write_raw[2]{},prr_barrier_raw=0;
    int host_actlr_read_raw[2]{},host_actlr_write_raw[2]{},host_actlr_barrier_raw[2]{};
    IORegistryEntry *endpoint_container=nullptr,*original_container=nullptr,*secure_node=nullptr,*native_root=nullptr;
    IOService *endpoint_parent=nullptr;bool endpoints_attempted=false,endpoints_ready=false;
    bool context_views_attempted=false,context_views_ready=false,context_probe_verified=false;
    IOMemoryDescriptor *context_probe_descriptor=nullptr;
    uint32_t context_probe_addresses[3]{};
    bool context_probe_active=false;
    bool gmu_context_fault_readable=false;
    unsigned gmu_context_intid=0;
    thread_t gmu_stream_thread=THREAD_NULL;
    uint32_t gmu_stream_base=0;
    unsigned gmu_stream_slot=256;
    unsigned gmu_stream_writes=0;
    bool gmu_bank_programming=false;
    bool gmu_stream_activating=false;
    bool gmu_smr_validating=false;
    bool gmu_cold_readback=false;
    bool host_context_images_ready=false;
    bool host_mmu_probe_readback=false;
    IOReturn prepareHostContextImages()
    {
        if(host_context_images_ready)return kIOReturnSuccess;
        for(unsigned i=0;i<2;++i){
            const auto &e=endpoints[i];
            if(!e.consumer || !e.reservation.acquired || !e.atomic_owner ||
               !e.program_route.io_.cookie || e.stream_owner || e.fault_owner ||
               e.reservation.context_bytes<8)return kIOReturnNotReady;
            host_banks[i]=e.reservation.bank;
            host_asids[i]=e.reservation.asid;
            const auto raw=consumerBypassAttributes(*native_root,*e.consumer,host_bypass[i]);
            if(raw)return raw;
        }
        const auto raw=host_gpu_tables->prepareContexts(id0,id2,host_asids,coherent_walk,host_bypass,banks);
        host_context_images_ready=raw==kIOReturnSuccess;
        return raw;
    }
    thread_t host_blocked_thread=THREAD_NULL;
    unsigned host_blocked_endpoint=2,host_blocked_slot=256,host_blocked_writes=0;
    bool host_fault_readable[2]{};
    bool host_stream_activation=false;
    unsigned host_owned_slots[2]{256,256};
    thread_t host_context_thread=THREAD_NULL;
    unsigned host_program_bank=2;
    bool host_prr_window=false;

    bool beginNativeHostPostCpWindow(uint32_t *failedPredicate=nullptr)
    {
        if(failedPredicate)*failedPredicate=0;
        if(!native_controller_mode)return true;
        // Preserve native short-circuit order. Only the actual Prepare caller
        // requests this local result; other window users invoke no observer.
        auto reject=[&](uint32_t predicate){if(failedPredicate)*failedPredicate=predicate;return false;};
        if(!IORecursiveLockHaveLock(&gate))return reject(53);
        if(!native_host_runtime_ready)return reject(54);
        if(!nativeControllerClaimHeld())return reject(55);
        if(failed())return reject(56);
        if(host_post_cp_access)return reject(57);
        if(__atomic_load_n(&host_context_thread,__ATOMIC_ACQUIRE))return reject(58);
        if(__atomic_load_n(&host_blocked_thread,__ATOMIC_ACQUIRE))return reject(59);
        host_post_cp_access=true;host_program_bank=2;host_blocked_endpoint=2;
        __atomic_store_n(&host_context_thread,current_thread(),__ATOMIC_RELEASE);
        __atomic_store_n(&host_blocked_thread,current_thread(),__ATOMIC_RELEASE);return true;
    }
    void selectNativeHostPostCpBank(unsigned bank)
    {if(native_controller_mode){host_program_bank=bank;host_blocked_endpoint=bank;}}
    void endNativeHostPostCpWindow()
    {
        if(!native_controller_mode || !host_post_cp_access)return;
        __atomic_store_n(&host_context_thread,THREAD_NULL,__ATOMIC_RELEASE);
        __atomic_store_n(&host_blocked_thread,THREAD_NULL,__ATOMIC_RELEASE);
        host_program_bank=2;host_blocked_endpoint=2;host_post_cp_access=false;
    }
    bool hostContextAccess(uint32_t physical,unsigned width,bool write,uint64_t value) const
    {
        const auto thread=__atomic_load_n(&host_context_thread,__ATOMIC_ACQUIRE);
        if(!thread || thread!=current_thread() || physical<gmu_stream_base ||
           __atomic_load_n(&irq_faulted,__ATOMIC_ACQUIRE))return false;
        const uint32_t offset=physical-gmu_stream_base;
        if(host_prr_window && width==4 && (offset==0x6008 || offset==0x600c))
            return !write || value==prr_expected[(offset-0x6008)/4];
        if(host_program_bank>=2)return false;
        const auto &e=endpoints[host_program_bank];
        const unsigned bank=e.reservation.bank;
        if(width==4){
            if(!write && (offset==0x20 || offset==0x24 || offset==0x28))return true;
            if(offset==register_stride+bank*4u || offset==register_stride+0x800u+bank*4u)
                return !host_post_cp_access || !write; // The held table programmer supplies its encoded image.
        }
        const unsigned cb=e.reservation.context_offset;
        if(offset<cb)return false;
        const unsigned reg=offset-cb;
        if(host_post_cp_access){
            if(host_process_transition){
                // The retained owner was checked when this same-thread window opened.
                // MMIO admission may run with interrupts masked; do not call PM/IOService here.
                if(!IORecursiveLockHaveLock(&gate) || !native_controller_mode || !native_host_runtime_ready || failed())return false;
                if(width==8)return (!write && (reg==0x20 || reg==0x28)) ||
                    (write && !host_runtime_observation && host_program_bank==0 &&
                     host_process_write_root && reg==0x20 && value==host_process_ttbr0);
                if(width!=4)return false;
                if(!write)return reg==0 || reg==4 || reg==0x10 || reg==0x30 ||
                    reg==0x38 || reg==0x3c || reg==0x58 || reg==0x7f4;
                return !host_runtime_observation && host_program_bank==0 && host_process_invalidate &&
                    ((reg==0x610 && value==host_process_asid) || (reg==0x7f0 && value==UINT32_MAX));
            }
            if(width==8)return !write && (reg==0x20 || reg==0x28);
            if(width!=4)return false;
            if(!write)return reg==0 || reg==4 || reg==0x10 || reg==0x30 || reg==0x38 || reg==0x3c || reg==0x58 || reg==0x7f4;
            if(host_runtime_observation)return false; // Runtime observation does not grant register writes.
            if(host_runtime_mutation){
                // The real task issuer and observed idle ring own this USER
                // transaction. No context reprogramming or blanket TLBIALL.
                return runtime_mapping_halted && runtime_transaction_thread==current_thread() && host_program_bank==0 &&
                    ((reg==0x610 && value==(runtime_process?runtime_process_asid:e.reservation.asid)) ||
                     (reg==0x7f0 && value==UINT32_MAX));
            }
            if(host_program_bank!=0 || !post_cp_restore_needed || !post_cp_grant_returned || post_cp_grant_raw)return false;
            return (reg==0x30 && value==post_cp_expected_tcr) ||
                (reg==0x610 && value==e.reservation.asid) || (reg==0x618 && value==0) ||
                (reg==0x7f0 && value==UINT32_MAX);
        }
        if(width==8)return reg==0x20 || reg==0x28;
        if(width!=4)return false;
        switch(reg){
            case 0: return true;
            case 4: return !write || (e.requested_actlr_present && value==e.requested_actlr) ||
                value==(host_actlr_before[host_program_bank]|(1u<<5));
            case 0x10: case 0x30: case 0x38: case 0x3c: return true;
            case 0x58: return !write || value==UINT32_MAX;
            case 0x610: return write && value==e.reservation.asid;
            case 0x618: return write && value==0;
            case 0x7f0: return write && value==UINT32_MAX;
            case 0x7f4: return !write;
            default: return false;
        }
    }

    IOReturn prepareHostPrrZero(NativeAdrenoMemory &zero)
    {
        const size_t cpu=zero.cpuPageBytes();
        if((cpu!=4096 && cpu!=16384) || !zero.backed() || zero.quarantined() || zero.imported() ||
           zero.readOnly() || !zero.writeCombined() || zero.deviceReferences() ||
           zero.bytes()!=4096 || zero.ownedBytes()!=cpu || !zero.mapping() ||
           !zero.descriptor() || zero.descriptor()->getLength()!=cpu || zero.spanCount()!=1 ||
           zero.ownedSpanCount()!=1 || zero.spans()[0].offset || zero.ownedSpans()[0].offset ||
           zero.spans()[0].bytes!=4096 || zero.ownedSpans()[0].bytes!=cpu ||
           zero.spans()[0].physical!=zero.ownedSpans()[0].physical)return kIOReturnNotReady;
        const auto physical=zero.spans()[0].physical;
        const uint64_t limit=UINT64_C(1)<<physical_output_bits;
        if(!physical || (physical&(cpu-1u)) || physical>=limit || cpu>limit-physical)
            return kIOReturnBadArgument;
        const auto *bytes=static_cast<const volatile uint8_t *>(zero.mapping());
        for(size_t i=0;i<cpu;++i)if(bytes[i])return kIOReturnNotReady;
        host_zero=&zero;
        host_zero_physical=physical;
        return kIOReturnSuccess;
    }

    IOReturn publishHostPrrZero()
    {
        zero_publish_raw=host_zero->publishForDevice(0,4096,true);
        zero_publish_returned=true;
        if(zero_publish_raw)return zero_publish_raw;
        zero_hold_raw=host_zero->holdForDevice();
        zero_hold_returned=true;
        if(zero_hold_raw)return zero_hold_raw;
        return host_zero->deviceReferences()==1?kIOReturnSuccess:kIOReturnNotReady;
    }

    bool hostBlockedAccess(uint32_t physical,unsigned width,bool write,uint64_t value) const
    {
        if(width!=4 || physical<gmu_stream_base || __atomic_load_n(&irq_faulted,__ATOMIC_ACQUIRE))
            return false;
        const auto thread=__atomic_load_n(&host_blocked_thread,__ATOMIC_ACQUIRE);
        if(!thread || thread!=current_thread() || host_blocked_endpoint>=2)return false;
        const auto &e=endpoints[host_blocked_endpoint];
        const unsigned offset=physical-gmu_stream_base;
        if(!write)
            return offset==0 || offset==0x20 ||
                (offset>=0x800u && offset<0x800u+mapping_groups*4u) ||
                (offset>=0xc00u && offset<0xc00u+mapping_groups*4u);
        if(host_stream_activation){
            // The thread window is established with the live owner checked
            // under the domain gate before AtomicSmmuIo masks local IRQs.
            if(!host_gpu_qtb_result.held)return false;
            const unsigned slot=host_owned_slots[host_blocked_endpoint];
            if(slot>=mapping_groups || !stream_slots[slot])return false;
            return (offset==0xc00u+slot*4u && value==(0x300u|e.reservation.bank)) ||
                (offset==0x800u+slot*4u && value==(e.packed|(1u<<31)));
        }
        if(host_blocked_slot>=mapping_groups)return false;
        const unsigned lane=host_blocked_slot*4u;
        return (host_blocked_writes==0 && offset==0xc00u+lane &&
            value==(0x20300u|e.reservation.bank)) ||
            (host_blocked_writes==1 && offset==0x800u+lane && value==e.packed);
    }

    static int acquireNativeBlockedHostStream(void *cookie,IOService &controller,IOService &consumer,
        unsigned bank,uint32_t requested,uint32_t effective,unsigned slot,bool extended,
        const uint32_t *smr,uint32_t,bool existing)
    {
        auto &s=*static_cast<Storage *>(cookie);
        if(!IORecursiveLockHaveLock(&s.gate) || !s.nativeControllerClaimHeld() || s.failed() ||
           !s.host_gpu_qtb_result.held || s.host_blocked_endpoint>=2 ||
           __atomic_load_n(&s.host_blocked_thread,__ATOMIC_ACQUIRE)!=current_thread())return 1;
        const auto &e=s.endpoints[s.host_blocked_endpoint];
        if(&controller!=&s.controller || &consumer!=e.consumer || bank!=e.reservation.bank ||
           requested!=e.packed || effective!=requested || requested!=s.host_blocked_endpoint ||
           extended || existing || !smr || (*smr&(1u<<31)) || slot>=s.mapping_groups ||
           !s.stream_slots[slot] || s.host_blocked_slot!=256)return 1;
        s.host_blocked_slot=slot;
        s.host_owned_slots[s.host_blocked_endpoint]=slot;
        return 0;
    }

    IOReturn haltHostQtb(OSObject &owner,ZornGen7IccInputs26 &tbuPower,unsigned budget)
    {
        auto &s=*this;
        if(s.host_gpu_qtb_attempted || s.host_gpu_qtb_owner || !s.native_controller_mode ||
           !s.nativeControllerClaimHeld() || !s.pm.nativeHeldFor(s.controller,s.gate))return (kIOReturnNotReady);
        s.host_gpu_qtb_attempted=true;
        IOPlatformDevice *qtb=nullptr;
        IOReturn raw;
        if(s.native_qtb_owner){
            if(!s.native_qtb_result.resume_complete || !s.native_qtb_result.power_release_returned ||
               s.native_qtb_result.power_release_raw!=kIOReturnSuccess || s.native_qtb_result.held || !s.native_qtb_provider)
                return (kIOReturnNotReady);
            qtb=s.native_qtb_provider;s.host_gpu_qtb_provider=qtb;s.host_gpu_qtb_owner=s.native_qtb_owner;
            const auto qtbRange=validateGpuQtbRange(*qtb,s.endpoints[0].packed,s.endpoints[1].packed);
            if(qtbRange)return (qtbRange);
            raw=s.host_gpu_qtb_owner->rearmAfterQuiescedSmmuOperation(owner,tbuPower,budget,s.host_gpu_qtb_result);
        }else{
            OSSharedPtr<IORegistryEntry> qtbNode(IORegistryEntry::fromPath("gpu-qtb",gIODTPlane,nullptr,nullptr,&s.controller),OSNoRetain);
            if(!qtbNode)return (kIOReturnNotFound);
            if(ZornGen7NativeDtEntry26::canPromote(*qtbNode)){
                qtb=new IOPlatformDevice;s.host_gpu_qtb_provider=qtb;
                if(!qtb || !qtb->init(qtbNode.get(),gIODTPlane) || !qtb->attach(&s.controller))return (kIOReturnNotAttached);
            }else{
                qtb=OSDynamicCast(IOPlatformDevice,qtbNode.get());
                if(!qtb || qtb->getMetaClass()!=IOPlatformDevice::metaClass || qtb->getProvider()!=&s.controller)return (kIOReturnExclusiveAccess);
                qtb->retain();s.host_gpu_qtb_provider=qtb;
            }
            if(qtb->isInactive())return (kIOReturnNotReady);
            // IOPlatformDevice::getResources expects an IOPlatformExpert
            // provider. This QTB's provider is the retained SMMU device.
            if(!qtb->getDeviceMemory() && !IODTResolveAddressing(qtb,"reg",nullptr))
                return kIOReturnNotFound;
            OSSharedPtr<OSObject> qtbMemory(qtb->copyProperty(gIODeviceMemoryKey),OSNoRetain);
            auto *qtbArray=OSDynamicCast(OSArray,qtbMemory.get());IOMemoryDescriptor *qtbDescriptor=nullptr;
            if(qtbArray)for(unsigned i=0;i<qtbArray->getCount();++i){
                auto *entry=OSDynamicCast(IOMemoryDescriptor,qtbArray->getObject(i));IOByteCount contiguous=0;
                if(entry && entry->getLength()==0x1000u && entry->getPhysicalSegment(0,&contiguous,kIOMemoryMapperNone)==0x3de8000u && contiguous>=0x1000u){
                    if(qtbDescriptor)return (kIOReturnBadArgument);qtbDescriptor=entry;
                }
            }
            if(!qtbDescriptor)return (kIOReturnNotFound);
            const auto qtbRange=validateGpuQtbRange(*qtb,s.endpoints[0].packed,s.endpoints[1].packed);
            if(qtbRange)return (qtbRange);
            raw=ZornGen7QtbFence26::createAndHalt(s.controller,*qtb,*qtbDescriptor,s.pm,tbuPower,s.gate,owner,
                budget,s.host_gpu_qtb_owner,s.host_gpu_qtb_result);
        }
        if(raw!=kIOReturnSuccess || !s.host_gpu_qtb_owner || !s.host_gpu_qtb_result.held || s.failed())
            return (raw==kIOReturnSuccess?kIOReturnNotReady:raw);
        return kIOReturnSuccess;
    }
    IOReturn resumeHostQtb()
    {
        if(!host_gpu_qtb_owner || !host_gpu_qtb_result.held || !host_gpu_qtb_provider)
            return kIOReturnNotReady;
        auto raw=host_gpu_qtb_owner->resumeAfterQuiescedSmmuOperation(host_gpu_qtb_result);
        if(raw || failed())return raw?raw:kIOReturnNotReady;
        uint32_t parentId=0;
        if(io.read32(io.cookie,0x20,&parentId) || parentId!=id0 || failed())return kIOReturnNotReady;
        raw=host_gpu_qtb_owner->lowerPowerAfterWriteSync(host_gpu_qtb_result);
        if(raw || failed() || !host_gpu_qtb_result.resume_complete || host_gpu_qtb_result.held)
            return raw?raw:kIOReturnNotReady;
        return kIOReturnSuccess;
    }
    unsigned observeHostMmuPreflight()
    {
        uint32_t steps=0;
        const auto raw=[&]() -> IOReturn {
            if(!IORecursiveLockHaveLock(&gate) || !nativeControllerClaimHeld() ||
               !pm.nativeHeldFor(controller,gate) || !native_root || !host_gpu_tables_ready ||
               !host_gpu_tables || !context_probe_verified || !gmu_activation_ready || failed() ||
               gmu_cold_readback || __atomic_load_n(&gmu_stream_thread,__ATOMIC_ACQUIRE))
                return kIOReturnNotReady;
            const auto prepared=prepareHostContextImages();
            if(prepared)return prepared;
            steps|=1;
            host_mmu_probe_readback=true;
            __atomic_store_n(&gmu_stream_thread,current_thread(),__ATOMIC_RELEASE);
            const auto observed=[&]() -> IOReturn {
                for(unsigned i=0;i<2;++i){
                    const auto &io=endpoints[i].atomic_io;
                    uint32_t sctlr=0,prr=0;
                    if(io.read32(io.cookie,0,&sctlr))return kIOReturnIOError;
                    if(sctlr&1u)return kIOReturnBusy;
                    steps|=2u<<i;
                    if(global_atomic_io.read32(global_atomic_io.cookie,0x6008+4u*i,&prr))
                        return kIOReturnIOError;
                    steps|=8u<<i;
                }
                return failed() ? kIOReturnNotReady : kIOReturnSuccess;
            }();
            __atomic_store_n(&gmu_stream_thread,THREAD_NULL,__ATOMIC_RELEASE);
            host_mmu_probe_readback=false;
            return observed;
        }();
        __atomic_store_n(&zornHostMmuPreflightSnapshot,(steps<<24)|(uint32_t(raw)&0x00ffffffu),__ATOMIC_RELEASE);
        return raw==kIOReturnSuccess?56:55;
    }
    unsigned gmu_activation_writes=0;
    bool nativeGmuBankAccess(uint32_t offset, unsigned width, bool write, uint64_t value) const
    {
        const auto &e=endpoints[2];
        const auto &image=e.image;
        const unsigned cb=e.reservation.context_offset;
        const unsigned bankOffset=e.reservation.bank*4u;
        if (width==4) {
            if (!write && (offset==0x24 || offset==0x28)) return true;
            if (offset==register_stride+bankOffset) return !write || value==image.cbar;
            if (offset==register_stride+0x800u+bankOffset) return !write || value==image.cba2r;
        }
        if (offset<cb) return false;
        const unsigned reg=offset-cb;
        if (width==8)
            return (reg==0x20 && (!write || value==image.ttbr0)) ||
                (reg==0x28 && (!write || value==image.ttbr1));
        if (width!=4) return false;
        switch (reg) {
            case 0: return !write || value==0 || value==image.sctlr;
            case 4: return !write || (e.requested_actlr_present && value==e.requested_actlr);
            case 0x10: return !write || value==image.tcr2;
            case 0x30: return !write || value==image.tcr;
            case 0x38: return !write || value==image.mair0;
            case 0x3c: return !write || value==image.mair1;
            case 0x58: return !write || value==UINT32_MAX;
            case 0x610: return write && value==e.reservation.asid;
            case 0x618: return write && value==0;
            case 0x7f0: return write && value==UINT32_MAX;
            case 0x7f4: return !write;
            default: return false;
        }
    }
    static int acquireNativeBlockedGmuStream(void *cookie, IOService &controller,
        IOService &consumer, unsigned bank, uint32_t requested, uint32_t effective,
        unsigned slot, bool extended, const uint32_t *smr, uint32_t, bool existing)
    {
        auto &s=*static_cast<Storage *>(cookie);
        const auto &endpoint=s.endpoints[2];
        if (!IORecursiveLockHaveLock(&s.gate) || !s.nativeControllerClaimHeld() || s.failed() ||
            __atomic_load_n(&s.gmu_stream_thread,__ATOMIC_ACQUIRE)!=current_thread() || &controller!=&s.controller ||
            &consumer!=endpoint.consumer || bank!=endpoint.reservation.bank ||
            requested!=endpoint.packed || requested!=5 || effective!=requested ||
            extended || existing || !smr || (*smr&(1u<<31)) ||
            slot>=s.mapping_groups || !s.stream_slots[slot] || s.gmu_stream_slot!=256)
            return 1;
        // Only the invalid slot is leased here. The atomic I/O gate does
        // not admit a valid SMR or translation S2CR in this startup phase.
        s.gmu_stream_slot=slot;
        return 0;
    }

    int blockedStreamAccess(uint32_t physical, unsigned width, bool write, uint64_t value) const
    {
        const auto thread=__atomic_load_n(&gmu_stream_thread,__ATOMIC_ACQUIRE);
        if (!thread || thread!=current_thread() ||
            physical<gmu_stream_base || __atomic_load_n(&irq_faulted,__ATOMIC_ACQUIRE))
            return 1;
        const unsigned offset=physical-gmu_stream_base;
        if (host_mmu_probe_readback)
            return width==4 && !write && (offset==0x6008 || offset==0x600c ||
                physical==context_probe_addresses[0] || physical==context_probe_addresses[1]) ? 0 : 1;
        if ((gmu_bank_programming || ((gmu_stream_activating || gmu_smr_validating || gmu_cold_readback) && !write)) &&
            nativeGmuBankAccess(offset,width,write,value)) return 0;
        if (width!=4 || (gmu_bank_programming && write)) return 1;
        if (!write)
            return (offset==0 || offset==0x20 ||
                (offset>=0x800 && offset<0x800+mapping_groups*4) ||
                (offset>=0xc00 && offset<0xc00+mapping_groups*4)) ? 0 : 1;
        if (gmu_cold_readback || gmu_stream_slot>=mapping_groups) return 1;
        const unsigned slotOffset=gmu_stream_slot*4;
        if (gmu_smr_validating)
            return gmu_activation_writes==1 && offset==0x800+slotOffset &&
                value==0x80000005u ? 0 : 1;
        if (gmu_stream_activating) {
            if (gmu_activation_writes==0 && offset==0xc00+slotOffset &&
                value==(0x300u|endpoints[2].reservation.bank)) return 0;
            return 1;
        }
        if (gmu_stream_writes==0 && offset==0xc00+slotOffset &&
            value==(0x20300u|endpoints[2].reservation.bank)) return 0;
        if (gmu_stream_writes==1 && offset==0x800+slotOffset && value==5) return 0;
        return 1;
    }
    static int authorizeNativeGmuContextSpi(void *cookie, IOService &controller,
        IOService &consumer, unsigned bank, unsigned irqSource, uint32_t intid)
    {
        auto &s = *static_cast<Storage *>(cookie);
        const auto &endpoint = s.endpoints[2];
        if (!IORecursiveLockHaveLock(&s.gate) || !s.nativeControllerClaimHeld() || s.failed() ||
            &controller != &s.controller || &consumer != endpoint.consumer ||
            endpoint.packed != 5 || bank != endpoint.reservation.bank || irqSource != bank + 1 ||
            intid != s.gmu_context_intid)
            return 1;

        // Pineapple GICD, same non-secure distributor as the kernel GIC driver.
        // Preserve an enabled, pending or active SPI before invoking the
        // existing registration path, which checks its own handler ledger.
        const auto distributor = ml_io_map(0x17100000, 0x4000);
        if (!distributor) return 1;
        const unsigned word = (intid / 32) * 4;
        const uint32_t bit = UINT32_C(1) << (intid % 32);
        const uint32_t occupied = ml_io_read32(distributor + 0x100 + word) |
            ml_io_read32(distributor + 0x200 + word) | ml_io_read32(distributor + 0x300 + word);
        return (occupied & bit) ? 1 : 0;
    }
    static int admitContextProbe(void *cookie, IOMemoryDescriptor &descriptor,
                                 uint32_t physical, unsigned width, bool write, uint64_t value) {
        const auto &s = *static_cast<const Storage *>(cookie);
        if (&descriptor != s.context_probe_descriptor) return 1;
        if (!s.blockedStreamAccess(physical,width,write,value) ||
            s.hostBlockedAccess(physical,width,write,value) || s.hostContextAccess(physical,width,write,value)) return 0;
        if (width != 4 || write) return 1;
        for(unsigned i=0;i<2;++i)
            if(__atomic_load_n(&s.host_fault_readable[i],__ATOMIC_ACQUIRE) &&
               physical==s.context_probe_addresses[i]+0x58u)return 0;
        if (__atomic_load_n(&s.gmu_context_fault_readable, __ATOMIC_ACQUIRE) &&
            physical == s.context_probe_addresses[2] + 0x58u) return 0;
        if (!__atomic_load_n(&s.context_probe_active, __ATOMIC_ACQUIRE)) return 1;
        for (const auto address : s.context_probe_addresses)
            if (physical == address) return 0;
        return 1;
    }
    static int observeContextProbe(void *cookie, IOMemoryDescriptor &descriptor,
                                   uint32_t physical, unsigned width, bool write, uint64_t value) {
        auto &s=*static_cast<Storage *>(cookie);
        const int raw=admitContextProbe(cookie,descriptor,physical,width,write,value);
        if (!raw && write) {
            if(s.hostContextAccess(physical,width,write,value))return 0;
            if(s.hostBlockedAccess(physical,width,write,value))++s.host_blocked_writes;
            else if (s.gmu_stream_activating || s.gmu_smr_validating) ++s.gmu_activation_writes;
            else if (!s.gmu_bank_programming) ++s.gmu_stream_writes;
        }
        return raw;
    }

    ZornGen7RegisterMaps26 *register_maps=nullptr;
    bool gmu_load_attempted=false,gmu_load_ready=false,gmu_load_grant_returned=false;
    int gmu_load_grant_raw=0,gmu_load_last_raw=0;bool gmu_load_last_returned=false;
    size_t tcm_words_written=0,itcm_shadow_words=0;
    uint32_t versions[5]{};unsigned version_words_returned=0;
    bool gmu_versions_attempted=false,gmu_versions_ready=false;
    // adreno_gpu_core_gen7_9_1 has no explicit gmu_fw_version initializer:
    // static C aggregate source initializes it to0. It is not a capability,
    // a supplied firmware result or a claim of compatibility after CM3 starts.
    uint32_t minimum_core_version=0;uint32_t *itcm_shadow=nullptr;
    ZornGen7AtomicSmmuIo26 *global_atomic_owner=nullptr;ArmSmmu4KIo global_atomic_io{};
    bool root_pages_attempted=false,root_pages_ready=false;
    bool sparse_attempted=false,sparse_ready=false;
    bool gmu_image_attempted=false,gmu_image_ready=false;
    bool firmware_seed_attempted=false,firmware_seed_ready=false;
    bool firmware_holds_attempted=false,firmware_holds_ready=false;
    bool firmware_publish_returned[5]{},firmware_hold_returned[5]{};
    IOReturn firmware_publish_raw[5]{},firmware_hold_raw[5]{};
    unsigned firmware_held_mask=0;
    const HoujiFullHostNativeMemory *firmware_memory=nullptr;OSObject *firmware_owner=nullptr;
    const uint8_t *firmware_bytes=nullptr;size_t firmware_size=0;
    gg_fw_block firmware_blocks[GG_FW_MAX_BLOCKS]{};
    gg_reservation firmware_reservations[GG_FW_MAX_BLOCKS]{};
    ZornSmmuSparse4KRange firmware_ranges[5]{},initial_ranges[12]{};size_t initial_range_count=0;
    ZornGen7BootBuffers26 *boot_buffers=nullptr;ZornGen7HwschedBuffers26 *hwsched_buffers=nullptr;bool boot_buffers_ready=false;
    bool gmu_config_attempted=false,gmu_config_ready=false;
    size_t firmware_block_count=0,firmware_reservation_count=0;
    ZornSmmuSparse4KLiveResult firmware_seed{};
    Storage(IOService &d,ZornGen7SmmuRuntimePm26 &p,const ArmSmmu4KIo &i,
        IORecursiveLock &g,const ZornGen7SmmuBankAuthority26 &a):controller(d),pm(p),io(i),gate(g),authority(a){}
    static void *operator new(size_t,void *p) noexcept{return p;}
};
IOReturn ZornGen7SmmuDomain26::createAndProbe(IOService &controller,ZornGen7SmmuRuntimePm26 &pm,
    const ArmSmmu4KIo &io,IORecursiveLock &gate,OSObject &controllerOwner,OSObject &authorityOwner,
    const ZornGen7SmmuBankAuthority26 &authority,ZornGen7SmmuDomain26 *&out)
{
    if(!authority.acquireActualBank)return kIOReturnBadArgument;
    return createAndProbeImpl(controller,pm,io,gate,controllerOwner,authorityOwner,&authority,out);
}
IOReturn ZornGen7SmmuDomain26::createNativeAndProbe(IOService &controller,ZornGen7SmmuRuntimePm26 &pm,
    const ArmSmmu4KIo &io,IORecursiveLock &gate,OSObject &controllerOwner,OSObject &codeOwner,ZornGen7SmmuDomain26 *&out)
{
    // Genuine native powered readonly IO;no bank authority is manufactured.
    if(!pm.nativeHeldFor(controller,gate) || io.read64 || io.write32 || io.write64 || io.barrier)return kIOReturnNotReady;
    return createAndProbeImpl(controller,pm,io,gate,controllerOwner,codeOwner,nullptr,out);
}
void ZornGen7SmmuDomain26::copyProbeResult(ZornGen7NativeSmmuProbeResult26 &out) const
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return;
    const auto &s=*storage_;out.identificationReads=s.identification_reads;
    if(s.identification_reads>0)out.id0=s.id0;if(s.identification_reads>1)out.id1=s.id1;if(s.identification_reads>2)out.id2=s.id2;
    out.capabilitiesReady=s.ready && !s.failed();
    if(out.capabilitiesReady){out.banks=s.banks;out.s2banks=s.s2banks;out.inputBits=s.s1_input_bits;
        out.outputBits=s.s1_output_bits;out.physicalBits=s.physical_output_bits;out.registerShift=s.register_shift;}
}
IOReturn ZornGen7SmmuDomain26::createAndProbeImpl(IOService &controller,ZornGen7SmmuRuntimePm26 &pm,
    const ArmSmmu4KIo &io,IORecursiveLock &gate,OSObject &controllerOwner,OSObject &authorityOwner,
    const ZornGen7SmmuBankAuthority26 *authority,ZornGen7SmmuDomain26 *&out)
{
    if(out || !normal() || !IORecursiveLockHaveLock(&gate) ||
       !io.cookie || !io.read32 || io.register_bytes<0x2c)return kIOReturnBadArgument;
    if(!matches(controller,ZornGen7SmmuFwspecSource26::nodes[0]))return kIOReturnBadArgument;
    for(const auto *key:ZornGen7SmmuFwspecSource26::controller_absent) {
        OSSharedPtr<OSObject> property(controller.copyProperty(key),OSNoRetain);
        if(property)return kIOReturnUnsupported;
    }
    auto *owner=new ZornGen7SmmuDomain26;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()){owner->release();return kIOReturnNoMemory;}
    owner->retain();owner->pinned_=true;out=owner;
    controller.retain();pm.retain();controllerOwner.retain();authorityOwner.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    owner->storage_=new(memory) Storage(controller,pm,io,gate,authority?*authority:ZornGen7SmmuBankAuthority26{});auto &s=*owner->storage_;
    s.native_controller_mode=authority==nullptr;
    if(s.native_controller_mode && !s.nativeControllerClaimHeld()){
        s.stopped=true;return kIOReturnNotOpen;
    }

    const auto acquired=pm.resumeAndGet();s.last=acquired.operation;
    if(acquired.operation.disposition!=Disposition::Complete || !acquired.active_controller) {
        s.stopped=true;return kIOReturnNotReady;
    }
    s.power=acquired.active_controller; // Held until real attach or retained failure.
    for(unsigned i=0;i<3;++i) {
        uint32_t *value=i==0?&s.id0:(i==1?&s.id1:&s.id2);
        const int raw=io.read32(io.cookie,0x20+4u*i,value);
        if(raw){s.last=rawResult(raw);s.stopped=true;return kIOReturnIOError;}
        ++s.identification_reads;
    }
    s.banks=s.id1&255u;s.s2banks=(s.id1>>16)&255u;
    OSSharedPtr<OSObject> property(controller.copyProperty("qcom,num-context-banks-override"),OSNoRetain);
    if(property) {
        auto *data=OSDynamicCast(OSData,property.get());
        if(!data || data->getLength()!=4 || !data->getBytesNoCopy()){s.stopped=true;return kIOReturnBadArgument;}
        const auto *p=static_cast<const uint8_t *>(data->getBytesNoCopy());
        const uint32_t count=uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);
        if(count<s.banks)s.banks=count; // Exact source min of observed count/override.
    }
    if(!s.banks || s.s2banks>s.banks){s.stopped=true;return kIOReturnUnsupported;}
    // Source controller format support; no fallback to an unrelated granule
    // or use of CPU page size as a GPU/SMMU page-size decision.
    if(!(s.id0&(1u<<30)) || !(s.id2&(1u<<12))){s.stopped=true;return kIOReturnUnsupported;}
    s.register_shift=(s.id1&(1u<<31))?16u:12u;
    s.register_stride=size_t(1)<<s.register_shift;
    s.register_pages=size_t(1)<<(((s.id1>>28)&7u)+1u);
    s.context_base=s.register_pages*s.register_stride;
    // The exact K80 DT has neither ignore-numpagendxb nor count overrides.
    // A mapped size mismatch cannot be repaired by inventing register geometry.
    OSSharedPtr<OSObject> threeLevel(controller.copyProperty("qcom,use-3-lvl-tables"),OSNoRetain);
    OSSharedPtr<OSObject> coherent(controller.copyProperty("dma-coherent"),OSNoRetain);
    s.three_level=bool(threeLevel);s.coherent_walk=bool(coherent);
    using ZornGen7SmmuCapabilitySource26::sourceIdSizeToBits;
    s.s1_input_bits=unsigned(sourceIdSizeToBits((s.id2>>8)&15u));
    if(s.three_level && s.s1_input_bits>39u)s.s1_input_bits=39u;
    // Linux S1 oas comes from IPA/ID2.IAS, not the separate PA/ID2.OAS.
    s.s1_output_bits=unsigned(sourceIdSizeToBits(s.id2&15u));
    s.physical_output_bits=unsigned(sourceIdSizeToBits((s.id2>>4)&15u));
    s.streamid_mask=(s.id0&(1u<<8))?0xffffu:((1u<<((s.id0>>9)&15u))-1u);
    s.stream_matching=bool(s.id0&(1u<<27));
    s.mapping_groups=s.stream_matching?(s.id0&255u):s.streamid_mask+1u;
    if(!s.mapping_groups){s.stopped=true;return kIOReturnUnsupported;}
    if(s.native_controller_mode && !s.nativeControllerClaimHeld()){s.stopped=true;return kIOReturnNotOpen;}
    s.ready=true;return kIOReturnSuccess;
}
OperationResult ZornGen7SmmuDomain26::reserveActual(IOService &consumer,const uint32_t *ids,size_t count,
    OSObject &fwspecOwner,Reservation &out)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return unavailable;
    auto &s=*storage_;
    const bool native=s.native_controller_mode;
    if((!native && !s.authority.acquireActualBank) ||
       (native && !s.nativeControllerClaimHeld()) || !s.ready || s.failed() || s.busy || !s.power || out.consumer || out.acquired ||
       (count && (!ids || count>SIZE_MAX/sizeof(*ids) ||
        (reinterpret_cast<uintptr_t>(ids)&3u) ||
        (count*sizeof(*ids)-1u)>UINTPTR_MAX-reinterpret_cast<uintptr_t>(ids))))return unavailable;
    if(native) {
        // Native allocation is deliberately limited to the three immutable
        // endpoints parsed by reserveNativeEndpoints. A provider open and a
        // free context image reserve only this controller-local bank; stream,
        // DMA, security, IRQ and global-control authority remain independent.
        bool exactEndpoint=false;
        for(auto &endpoint:s.endpoints)if(endpoint.consumer==&consumer && ids==&endpoint.packed &&
            &fwspecOwner==this && count==1 && endpoint.packed==ids[0] && endpoint.reservation.consumer==nullptr &&
            !endpoint.reservation.acquired)exactEndpoint=true;
        if(!exactEndpoint || (ids[0]>>16) || !s.stream_matching || s.streamid_mask>0xffffu ||
           s.banks!=22 || s.s2banks!=0 || s.mapping_groups!=24 || s.context_views_ready ||
           s.global_fault_attempted || s.controller_start_attempted || s.gmu_program_attempted ||
           s.host_gpu_mmu_attempted || s.register_shift!=12 ||
           s.register_stride!=0x1000u || s.register_pages!=32 || s.context_base!=0x20000u ||
           !s.io.read32 || s.io.read64 || s.io.write32 || s.io.write64 || s.io.barrier ||
           s.io.register_bytes<0x36000u)return unavailable;
    }
    bool gpu=false;for(size_t i=0;i<count;++i)if((ids[i]&0xffffu)<=1u)gpu=true;
    const uint32_t start=gpu?0u:2u,end=gpu?2u:s.banks;
    if(end>s.banks){s.stopped=true;return unavailable;}
    uint32_t bank=start;while(bank<end && s.reserved[bank])++bank;
    if(bank>=end){s.stopped=true;s.last=rawResult(-28);return s.last;} // __arm_smmu_alloc_bitmap source ENOSPC.
    const size_t offset=s.context_base+size_t(bank)*s.register_stride;
    if(bank<s.s2banks || offset>s.io.register_bytes ||
       s.register_stride>s.io.register_bytes-offset ||
       s.register_stride+0x804u+size_t(bank)*4u>s.io.register_bytes) {
        s.stopped=true;return unavailable;
    }
    for(size_t i=0;i<count;++i)if((ids[i]&0xffffu)&~s.streamid_mask) {
        s.stopped=true;return unavailable;
    }
    if(native) {
        // K80's selected native image uses ordinary SMMUv2 SMR validity and
        // exactly 24 stream groups. Read global quiescence, the full matching
        // table, then candidate contexts. Unknown or changing state poisons
        // the domain; no bank, stream, fault or translation register is written.
        s.busy=true;
        auto read=[&](size_t at,uint32_t &value) {
            if(!s.nativeControllerClaimHeld())return false;
            const int raw=s.io.read32(s.io.cookie,at,&value);
            return raw==0 && s.nativeControllerClaimHeld() && !s.failed();
        };
        auto failNative=[&](int32_t raw) {
            s.busy=false;s.stopped=true;s.last=rawResult(raw);return s.last;
        };
        uint32_t cr0=0,gfsr=0,tlbi=0;
        if(!read(0x00u,cr0) || !read(0x48u,gfsr) || !read(0x74u,tlbi))return failNative(-5);
        // CLIENTPD, EXIDS, pending faults, or an active global invalidate make
        // bank ownership ambiguous. Do not infer availability from SCTLR alone.
        if((cr0&((1u<<0)|(1u<<3))) || gfsr || (tlbi&1u))return failNative(-16);
        uint32_t smr[24]{},s2cr[24]{};
        const uint32_t requested=ids[0]&0xffffu;
        for(unsigned group=0;group<24;++group) {
            if(!read(0x800u+size_t(group)*4u,smr[group]) ||
               !read(0xc00u+size_t(group)*4u,s2cr[group]))return failNative(-5);
            if(smr[group]&(1u<<31)) {
                const uint32_t existingId=smr[group]&0xffffu;
                const uint32_t existingMask=(smr[group]>>16)&0x7fffu;
                if(!((existingId^requested)&~existingMask&0xffffu))return failNative(-16);
            }
        }
        bool found=false;
        while(bank<end) {
            const size_t cbar=0x1000u+size_t(bank)*4u;
            const size_t cba2r=0x1800u+size_t(bank)*4u;
            const size_t context=s.context_base+size_t(bank)*s.register_stride;
            uint32_t cbarValue=0,cba2rValue=0,sctlr=0;
            if(!read(cbar,cbarValue) || !read(cba2r,cba2rValue) || !read(context,sctlr))
                return failNative(-5);
            bool routed=false;
            for(unsigned group=0;group<24;++group)
                if(((s2cr[group]>>16)&3u)==0u && (s2cr[group]&0xffu)==bank)routed=true;
            if(!cbarValue && !cba2rValue && !(sctlr&1u) && !routed) {found=true;break;}
            do {++bank;} while(bank<end && s.reserved[bank]);
        }
        if(!found)return failNative(-28);
        if(!s.nativeControllerClaimHeld())return failNative(-5);
    }
    s.reserved[bank]=true;s.busy=true;
    consumer.retain();fwspecOwner.retain();
    // S1 ASID is the actual allocated cbndx in this exact source. Reservation
    // does not enable a bank. Native mode uses the retained single-owner
    // controller claim plus live empty-register check; external mode requires
    // its separate actual handoff callback exactly as before.
    const int raw=native?0:s.authority.acquireActualBank(s.authority.cookie,s.controller,consumer,
        uint16_t(bank),uint16_t(bank),ids,count);
    s.busy=false;s.last=rawResult(raw);
    if(raw){s.stopped=true;return s.last;}
    out.bank=uint16_t(bank);out.asid=uint16_t(bank);out.consumer=&consumer;out.acquired=true;
    out.context_offset=offset;out.context_bytes=s.register_stride;
    return s.last;
}
OperationResult ZornGen7SmmuDomain26::reserveNativeEndpoints(IOService &platform,
    IORegistryEntry &root,IOService &gmu,OSObject &treeOwner)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return unavailable;
    auto &s=*storage_;
    if(!s.ready || s.failed() || s.busy || !s.power || s.endpoints_attempted)return unavailable;
    s.endpoints_attempted=true;platform.retain();root.retain();gmu.retain();treeOwner.retain();s.native_root=&root;
    auto refuse=[&](){s.stopped=true;return unavailable;};
    using namespace ZornGen7SmmuFwspecSource26;
    OSSharedPtr<IORegistryEntry> controller(IORegistryEntry::fromPath(nodes[0].path+1,
        gIODTPlane,nullptr,nullptr,&root),OSNoRetain);
    if(controller.get()!=&s.controller || !matches(s.controller,nodes[0]))return refuse();
    OSSharedPtr<OSObject> id(s.controller.copyProperty("phandle"),OSNoRetain);
    auto *identifier=OSDynamicCast(OSData,id.get());
    if(!identifier || identifier->getLength()!=4 || !identifier->getBytesNoCopy())return refuse();
    const uint32_t phandle=little(static_cast<const uint8_t *>(identifier->getBytesNoCopy()));
    s.endpoint_container=IORegistryEntry::fromPath(nodes[1].path+1,gIODTPlane,nullptr,nullptr,&root);
    if(!s.endpoint_container || !matches(*s.endpoint_container,nodes[1]))return refuse();
    s.original_container=s.endpoint_container;
    auto *parent=OSDynamicCast(IOService,s.endpoint_container);
    if(ZornGen7NativeDtEntry26::canPromote(*s.endpoint_container)) {
        if(!parent){parent=new IOService;s.endpoint_parent=parent;if(!parent || !parent->init(s.endpoint_container,gIODTPlane))return refuse();}
        s.endpoint_parent=parent;
        s.endpoint_container=parent; // init(from,plane) transfers actual tree links.
        if(!parent->attach(&platform))return refuse();
    } else {
        if(!parent || parent->getProvider()!=&platform)return refuse();
        parent->retain();s.endpoint_parent=parent;
    }
    // Secure is retained as its distinct source endpoint, never silently
    // converted into an ordinary domain or passed to the bank allocator.
    s.secure_node=IORegistryEntry::fromPath(nodes[4].path+1,gIODTPlane,nullptr,nullptr,&root);
    if(!s.secure_node || !matches(*s.secure_node,nodes[4]))return refuse();
    OSSharedPtr<IORegistryEntry> secureParent(s.secure_node->copyParentEntry(gIODTPlane),OSNoRetain);
    if(secureParent.get()!=s.endpoint_container)return refuse();
    for(size_t i=0;i<3;++i) {
        auto &e=s.endpoints[i];const auto &expected=nodes[ordinary_indices[i]];
        e.node=IORegistryEntry::fromPath(expected.path+1,gIODTPlane,nullptr,nullptr,&root);
        e.original=e.node;
        if(!e.node || !matches(*e.node,expected))return refuse();
        if(i<2) {
            OSSharedPtr<IORegistryEntry> parentEntry(e.node->copyParentEntry(gIODTPlane),OSNoRetain);
            if(parentEntry.get()!=s.endpoint_container)return refuse();
            e.consumer=OSDynamicCast(IOService,e.node);
            if(ZornGen7NativeDtEntry26::canPromote(*e.node)) {
                if(!e.consumer){e.consumer=new IOService;if(!e.consumer || !e.consumer->init(e.node,gIODTPlane))return refuse();}
                e.node=e.consumer;
                if(!e.consumer->attach(s.endpoint_parent))return refuse();
            } else if(!e.consumer || e.consumer->getProvider()!=s.endpoint_parent)return refuse();
        } else {
            if(e.node!=&gmu)return refuse();e.consumer=&gmu;
        }
        e.consumer->retain();e.property=e.node->copyProperty("iommus");
        auto *data=OSDynamicCast(OSData,e.property);
        if(!data || data->getLength()!=12 || !data->getBytesNoCopy())return refuse();
        const auto *p=static_cast<const uint8_t *>(data->getBytesNoCopy());
        const uint32_t sid=little(p+4),mask=little(p+8);
        if(little(p)!=phandle || !phandle || sid>0xffffu || mask>0xffffu)return refuse();
        // Exact arm_smmu_of_xlate ID/MASK fields, from actual native cells.
        // Metadata and real CPU services establish no bank or DMA authority.
        e.packed=sid|(mask<<16);
    }
    for(auto &e:s.endpoints) {
        const auto result=reserveActual(*e.consumer,&e.packed,1,*this,e.reservation);
        if(result.disposition!=Disposition::Complete)return result;
    }
    s.endpoints_ready=true;return s.last;
}
IOReturn ZornGen7SmmuDomain26::bindContextViews(ZornGen7RegisterMaps26 &maps,
    IOMemoryDescriptor &descriptor,OSObject &guardOwner,const ZornGen7AtomicSmmuGuard26 &guard)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.ready || s.failed() || s.busy || !s.power || !s.endpoints_ready ||
       s.context_views_attempted)return kIOReturnNotReady;
    const bool probe = !guard.cookie && !guard.admitAtomicAccess && !guard.observeAtomicAccess;
    ZornGen7AtomicSmmuGuard26 access = guard;
    if (probe) {
        if (!s.nativeControllerClaimHeld()) return kIOReturnNotOpen;
        IOByteCount contiguous = 0;
        const auto physical = descriptor.getPhysicalSegment(0, &contiguous, kIOMemoryMapperNone);
        if (!physical || physical > UINT32_MAX || s.io.register_bytes > contiguous ||
            s.io.register_bytes - 1 > UINT32_MAX - physical) return kIOReturnBadArgument;
        s.context_probe_descriptor = &descriptor;
        for (unsigned i = 0; i < 3; ++i) {
            const auto &reservation = s.endpoints[i].reservation;
            if (!reservation.acquired || reservation.context_offset > s.io.register_bytes - 4)
                return kIOReturnNotReady;
            s.context_probe_addresses[i] = uint32_t(physical + reservation.context_offset);
        }
        access = {&s, Storage::admitContextProbe, Storage::observeContextProbe};
    } else if (!access.admitAtomicAccess || !access.observeAtomicAccess) {
        return kIOReturnBadArgument;
    }
    s.context_views_attempted=true;maps.retain();s.register_maps=&maps;descriptor.retain();guardOwner.retain();
    const auto globalRaw=maps.bindAtomicSmmuSubview(s.controller,descriptor,0,s.io.register_bytes,
        guardOwner,access,s.global_atomic_owner,s.global_atomic_io);
    if(globalRaw!=kIOReturnSuccess){s.stopped=true;return globalRaw;}
    for(auto &e:s.endpoints) {
        if(!e.reservation.acquired || !e.reservation.consumer){s.stopped=true;return kIOReturnNotReady;}
        const auto raw=maps.bindAtomicSmmuSubview(s.controller,descriptor,e.reservation.context_offset,
            e.reservation.context_bytes,guardOwner,access,e.atomic_owner,e.atomic_io);
        if(raw!=kIOReturnSuccess){s.stopped=true;return raw;}
        if(!e.program_route.bind(s.global_atomic_io,e.atomic_io,s.register_stride,
            e.reservation.context_offset,e.reservation.bank,s.id0,s.id1,s.id2,s.irq_faulted)) {
            s.stopped=true;return kIOReturnBadArgument;
        }
    }
    // These are real retained views. No bank registers have been programmed,
    // no stream has been attached, and no TLB domain is yet published.
    if (probe) {
        // The startup gate and retained PM hold cover these three synchronous reads.
        // Callback scope ends before this worker can publish its result.
        __atomic_store_n(&s.context_probe_active, true, __ATOMIC_RELEASE);
        IOReturn result = kIOReturnSuccess;
        for (auto &endpoint : s.endpoints) {
            uint32_t sctlr = 0;
            if (endpoint.atomic_io.read32(endpoint.atomic_io.cookie, 0, &sctlr)) {
                result = kIOReturnIOError;
                break;
            }
            if (sctlr & 1u) {
                result = kIOReturnBusy;
                break;
            }
        }
        __atomic_store_n(&s.context_probe_active, false, __ATOMIC_RELEASE);
        if (result != kIOReturnSuccess || !s.nativeControllerClaimHeld()) {
            s.stopped = true;
            return result == kIOReturnSuccess ? kIOReturnNotOpen : result;
        }
        s.context_probe_verified = true;
        // The read-only guard stays closed to runtime programming.
        return kIOReturnSuccess;
    }
    s.context_views_ready=true;return kIOReturnSuccess;
}
IOReturn ZornGen7SmmuDomain26::prepareRootPages()
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.ready || s.failed() || s.busy || !s.power || !s.endpoints_ready ||
       (!s.context_views_ready && !s.context_probe_verified) || s.root_pages_attempted)return kIOReturnNotReady;
    s.root_pages_attempted=true;
    // S1 descriptor output remains the source IPA capability. The backing
    // allocator must additionally fit the actual table walk's physical limit.
    const unsigned backingBits=s.s1_output_bits<s.physical_output_bits?s.s1_output_bits:s.physical_output_bits;
    for(auto &e:s.endpoints) {
        if(!e.reservation.acquired || !e.atomic_owner){s.stopped=true;return kIOReturnNotReady;}
        IOReturn raw=ZornGen7SmmuTablePages26::create(s.gate,*this,backingBits,e.tables);
        if(raw!=kIOReturnSuccess){s.stopped=true;return raw;}
        raw=e.tables->allocate4K(e.root);
        if(raw!=kIOReturnSuccess){s.stopped=true;return raw;}
    }
    // Actual empty roots only. No context image, table walk, stream route,
    // completion, IRQ ownership or GPU address is inferred from allocation.
    s.root_pages_ready=true;return kIOReturnSuccess;
}
IOReturn ZornGen7SmmuDomain26::prepareSparseArenas()
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.ready || s.failed() || s.busy || !s.power || !s.root_pages_ready || s.sparse_attempted)return kIOReturnNotReady;
    s.sparse_attempted=true;
    const uint64_t span=UINT64_C(1)<<s.s1_input_bits;
    if(span/4096>SIZE_MAX){s.stopped=true;return kIOReturnUnsupported;}
    for(auto &e:s.endpoints) {
        if(!e.tables || !e.root.physical || !e.root.mapping){s.stopped=true;return kIOReturnNotReady;}
        const auto *provider=e.tables->provider();e.visibility=e.tables->visibility();
        if(!provider || !e.visibility.publish_table_page){s.stopped=true;return kIOReturnNotReady;}
        // Actual qcom_adreno_smmu_init_context enables TTBR1 for GPU SID0/1
        // on the qualified K80 AArch64 S1 controller. GMU remains TTBR0.
        // arm_smmu_init_domain_context publishes the matching full aperture.
        const unsigned upper=(e.packed&0xffffu)<=1u?1u:0u;
        const uint64_t base=upper?UINT64_MAX-span+1u:0u;
        e.arena={{s.s1_input_bits,s.s1_output_bits,e.root.physical,size_t(span/4096)},
            base,span,upper,provider,nullptr,0};
        e.sparse_status=ZornSmmuSparse4KLivePrepare(&e.arena,&e.state);
        if(e.sparse_status==ZornSmmuSparse4KSuccess)
            e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,nullptr,0,&e.audit);
        if(e.sparse_status!=ZornSmmuSparse4KSuccess){e.state.poisoned=1;s.stopped=true;return kIOReturnIOError;}
    }
    // Empty actual sparse graphs only. No mappings, descriptors for resources,
    // context programming, stream routes or completion are manufactured.
    s.sparse_ready=true;return kIOReturnSuccess;
}
IOReturn ZornGen7SmmuDomain26::prepareGmuContextImage()
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.ready || s.failed() || s.busy || !s.power || !s.sparse_ready || s.gmu_image_attempted)return kIOReturnNotReady;
    s.gmu_image_attempted=true;auto &e=s.endpoints[2];
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(!e.consumer || !e.reservation.acquired || !e.tables || !e.state.prepared || e.state.poisoned ||
       e.arena.upper_region || e.state.tables.upper_region || !e.audit.complete ||
       e.state.tables.root_physical!=e.root.physical)return refuse(kIOReturnNotReady);
    OSSharedPtr<OSObject> group(e.consumer->copyProperty("qcom,iommu-group"),OSNoRetain);
    if(group || !matches(*e.consumer,ZornGen7SmmuFwspecSource26::nodes[5]))return refuse(kIOReturnUnsupported);
    // Pinned SM8650 gen7_gmu_iommu_init explicitly sets NO_STALL and documents
    // HUPCF0. These are the initial GMU image only, not GPU pagefault-policy
    // selection, fault handling/IRQ ownership or a promise to recover/abort DMA.
    if(!s.native_root)return refuse(kIOReturnNotReady);
    uint32_t bypassAttributes=0;
    const auto bypassRaw=consumerBypassAttributes(*s.native_root,*e.consumer,bypassAttributes);
    if(bypassRaw!=kIOReturnSuccess)return refuse(bypassRaw);
    e.context={&e.arena.config,nullptr,&e.state.tables,nullptr,s.id0,s.id2,
        e.reservation.asid,s.coherent_walk?1u:0u,0,0,0,bypassAttributes};
    e.image_status=ZornSmmuSparse4KEncodeContext(&e.context,&e.image);
    if(e.image_status!=ZornSmmuSparse4KSuccess)return refuse(kIOReturnUnsupported);
    // Source ACTLR grouping uses smr_is_subset(actual,setting). At this point
    // only the immutable REQUESTED packed stream record exists; retain its
    // candidate separately. Actual allocated/handoff SMR must be checked before
    // any ACTLR write. A matching DT tuple is never a stream/security lease.
    const auto actlrRaw=ZornGen7SelectActlr(s.controller,e.packed,e.requested_actlr_present,e.requested_actlr);
    if(actlrRaw)return refuse(actlrRaw);
    e.image_ready=true;s.gmu_image_ready=true;return kIOReturnSuccess;
}
IOReturn ZornGen7SmmuDomain26::seedGmuFirmware(const HoujiFullHostNativeMemory &memory,
    OSObject &owner,const uint8_t *firmware,size_t bytes)
{return seedGmuFirmwareInternal(memory,owner,firmware,bytes,false);}
IOReturn ZornGen7SmmuDomain26::seedGmuHwschedFirmware(const HoujiFullHostNativeMemory &memory,
    OSObject &owner,const uint8_t *firmware,size_t bytes)
{return seedGmuFirmwareInternal(memory,owner,firmware,bytes,true);}
IOReturn ZornGen7SmmuDomain26::seedGmuFirmwareInternal(const HoujiFullHostNativeMemory &memory,
    OSObject &owner,const uint8_t *firmware,size_t bytes,bool hwsched)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_image_ready ||
       s.firmware_seed_attempted)return kIOReturnNotReady;
    s.firmware_seed_attempted=true;owner.retain();s.firmware_owner=&owner;
    s.firmware_memory=&memory;s.firmware_bytes=firmware;s.firmware_size=bytes;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(!memory.prepared() || memory.count()!=HoujiFullHostNativeMemory::Slots ||
       !firmware || bytes!=FHG_GMU_BYTES || !e.image_ready || !e.tables ||
       e.state.context_offset || e.state.detached || e.state.generation ||
       e.state.poisoned || !e.state.prepared || e.state.tables.leaf_pages)
        return refuse(kIOReturnNotReady);
    // The same retained parser that populated the original five native slots.
    // VMA extents match pinned gen7_gmu_vma; only firmware metadata supplies
    // IOVAs. No FhgGraph/FhgRange diagnostic snapshot or fixed HFI/scratch VA
    // is replayed. TCM remains device memory and is deliberately not mapped.
    if(gg_fw_plan(firmware,bytes,s.firmware_blocks,GG_FW_MAX_BLOCKS,&s.firmware_block_count)!=GG_FW_OK ||
       gg_memory_plan(s.firmware_blocks,s.firmware_block_count,s.firmware_reservations,
           GG_FW_MAX_BLOCKS,&s.firmware_reservation_count)!=GG_FW_OK ||
       s.firmware_reservation_count!=5)return refuse(kIOReturnBadArgument);
    for(unsigned i=0;i<5;++i) {
        const auto &reservation=s.firmware_reservations[i];
        const auto &entry=memory.entry(i);const auto &bo=memory.bo(i);
        const auto &request=entry.request;const auto &backing=entry.backing;
        if(!entry.attempted || !entry.allocated || !entry.validated || !entry.published || entry.status ||
           request.slot!=i || request.kind!=FHG_FW || request.normal_nc || entry.nc ||
           request.logical_bytes!=reservation.bytes || uint64_t(request.gpu4k_pages)*4096!=reservation.bytes ||
           !bo.backed() || bo.quarantined() || bo.imported() || bo.readOnly() || bo.deviceReferences() ||
           bo.writeCombined() || !bo.mapping() || !bo.descriptor() || bo.spanCount()!=1 || bo.ownedSpanCount()!=1 ||
           bo.mapping()!=backing.cpu || bo.bytes()!=request.logical_bytes || bo.ownedBytes()!=request.owned_bytes ||
           bo.cpuPageBytes()!=request.cpu_page_bytes || bo.descriptor()->getLength()!=request.owned_bytes ||
           backing.physical!=bo.spans()[0].physical || bo.spans()[0].offset ||
           bo.spans()[0].bytes!=reservation.bytes || backing.owned_physical!=bo.ownedSpans()[0].physical ||
           bo.ownedSpans()[0].offset || bo.ownedSpans()[0].bytes!=request.owned_bytes ||
           backing.physical!=backing.owned_physical || backing.owned_bytes!=request.owned_bytes ||
           request.owned_bytes!=NativeAdrenoMemory::backingBudget(request.logical_bytes))
            return refuse(kIOReturnBadArgument);
        // Recheck genuine copied firmware data and its zero tail under this
        // owner's exclusive inactive borrow, rather than trusting a summary.
        const auto *cpu=static_cast<const volatile uint8_t *>(backing.cpu);
        for(uint64_t at=0;at<request.owned_bytes;++at) {
            uint8_t want=0;const uint64_t va=uint64_t(reservation.iova)+at;
            if(at<reservation.bytes)for(size_t k=0;k<s.firmware_block_count;++k) {
                const auto &block=s.firmware_blocks[k];
                if(block.size && va>=block.address && va-block.address<block.size) {
                    want=firmware[block.payload_offset+size_t(va-block.address)];break;
                }
            }
            if(cpu[at]!=want)return refuse(kIOReturnBadArgument);
        }
        // gen7_reserve_gmu_kernel_block: READ|WRITE|PRIV, with no CACHE or
        // NOEXEC. Actual QCOM_ARM_64_LPAE_S1 uses MAIR NC index0 and SH_OS.
        s.firmware_ranges[i]={reservation.iova,backing.physical,reservation.bytes,
            ZornSmmuSparse4KRead|ZornSmmuSparse4KWrite|ZornSmmuSparse4KPrivileged|ZornSmmuSparse4KExecute,0,2};
    }
    // All source-selected cold resources are seeded together while this
    // context is still never installed. No live-map/quiescence contract is weakened.
    const unsigned backingBits=s.s1_output_bits<s.physical_output_bits?s.s1_output_bits:s.physical_output_bits;
    for(unsigned i=0;i<5;++i)s.initial_ranges[i]=s.firmware_ranges[i];
    if(hwsched) {
        const auto raw=ZornGen7HwschedBuffers26::createAndPrepare(s.gate,*this,backingBits,
            s.firmware_reservations,s.firmware_reservation_count,s.firmware_blocks,s.firmware_block_count,s.hwsched_buffers);
        if(raw!=kIOReturnSuccess || !s.hwsched_buffers)return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
        ZornSmmuSparse4KRange bootRanges[7]{};
        if(!s.hwsched_buffers->copyPreparedRanges(bootRanges))return refuse(kIOReturnNotReady);
        for(unsigned i=0;i<7;++i)s.initial_ranges[5+i]=bootRanges[i];
        s.initial_range_count=12;
    }else{
        const auto raw=ZornGen7BootBuffers26::createAndPrepare(s.gate,*this,backingBits,
            s.firmware_reservations,s.firmware_reservation_count,s.boot_buffers);
        if(raw!=kIOReturnSuccess || !s.boot_buffers)return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
        ZornSmmuSparse4KRange bootRanges[2]{};
        if(!s.boot_buffers->copyPreparedRanges(bootRanges))return refuse(kIOReturnNotReady);
        for(unsigned i=0;i<2;++i)s.initial_ranges[5+i]=bootRanges[i];
        s.initial_range_count=7;
    }
    for(size_t i=1;i<s.initial_range_count;++i) {
        const auto value=s.initial_ranges[i];size_t j=i;
        while(j && s.initial_ranges[j-1].iova>value.iova){s.initial_ranges[j]=s.initial_ranges[j-1];--j;}
        s.initial_ranges[j]=value;
    }
    s.boot_buffers_ready=true;
    e.sparse_status=ZornSmmuSparse4KLiveSeedInactive(&e.arena,&e.state,&e.visibility,
        s.initial_ranges,s.initial_range_count,&s.firmware_seed);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !s.firmware_seed.complete)
        return refuse(kIOReturnIOError);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    // Still inactive. Native device holds, fault/stream/security ownership and
    // actual context programming must precede any future DMA or firmware start.
    s.firmware_seed_ready=true;return kIOReturnSuccess;
}
IOReturn ZornGen7SmmuDomain26::holdGmuFirmware(HoujiFullHostNativeMemory &memory,OSObject &owner)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.firmware_seed_ready ||
       s.firmware_holds_attempted)return kIOReturnNotReady;
    s.firmware_holds_attempted=true;
    auto refuse=[&](IOReturn raw){s.stopped=true;s.last=rawResult(raw);return raw;};
    if(!s.boot_buffers_ready || !s.boot_buffers || s.firmware_memory!=&memory || s.firmware_owner!=&owner || !memory.prepared() ||
       memory.count()!=HoujiFullHostNativeMemory::Slots || !e.image_ready ||
       e.state.poisoned || e.state.context_offset || e.state.detached || e.state.generation!=1)
        return refuse(kIOReturnNotReady);
    for(unsigned i=0;i<5;++i) {
        const auto &entry=memory.entry(i);const auto &bo=memory.bo(i);const auto &range=s.firmware_ranges[i];
        if(!entry.published || entry.status || !bo.backed() || bo.quarantined() || bo.imported() ||
           bo.readOnly() || bo.writeCombined() || bo.deviceReferences() || !bo.mapping() ||
           bo.mapping()!=entry.backing.cpu || bo.bytes()!=range.bytes || bo.ownedSpanCount()!=1 ||
           bo.spanCount()!=1 || bo.spans()[0].physical!=range.physical || bo.spans()[0].offset ||
           bo.spans()[0].bytes!=range.bytes || bo.ownedBytes()!=entry.request.owned_bytes ||
           bo.ownedSpans()[0].physical!=entry.backing.owned_physical ||
           bo.ownedSpans()[0].bytes!=entry.request.owned_bytes)
            return refuse(kIOReturnNotReady);
    }
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    for(unsigned i=0;i<5;++i) {
        // The original inventory exposes only a const observer. Here the
        // actual allocating parent passes its NONCONST memory object under
        // its exclusive borrow; this is the very same owned native member,
        // not a fabricated pointer, copied object or inferred device lease.
        auto &bo=const_cast<NativeAdrenoMemory &>(memory.bo(i));
        s.firmware_publish_raw[i]=bo.publishForDevice(0,bo.bytes(),true);
        s.firmware_publish_returned[i]=true;
        if(s.firmware_publish_raw[i]!=kIOReturnSuccess)return refuse(s.firmware_publish_raw[i]);
        s.firmware_hold_raw[i]=bo.holdForDevice();s.firmware_hold_returned[i]=true;
        if(bo.deviceReferences())s.firmware_held_mask|=1u<<i;
        if(s.firmware_hold_raw[i]!=kIOReturnSuccess)return refuse(s.firmware_hold_raw[i]);
        if(bo.deviceReferences()!=1)return refuse(kIOReturnNotReady);
    }
    if(s.firmware_held_mask!=31u)return refuse(kIOReturnNotReady);
    // Native reference accounting protects backing lifetime only. It does not
    // authorize streams, security, context activation, GMU start or release.
    // No partial holds are retired on failure; normal eventual retirement
    // requires genuine completion/quiescence and remains a separate step.
    s.firmware_holds_ready=true;return kIOReturnSuccess;
}
void ZornGen7SmmuDomain26::free(){if(pinned_)return;OSObject::free();}

IOReturn ZornGen7SmmuDomain26::installGmuFaultIrq(OSObject &owner,
    const ZornGen7SmmuFaultIrqAuthority26 &authority)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.global_fault_ready ||
       !s.global_fault_owner || !s.global_fault_owner->ready() || !s.firmware_holds_ready ||
       !s.context_views_ready || !s.gmu_image_ready || s.gmu_fault_irq_attempted)return kIOReturnNotReady;
    s.gmu_fault_irq_attempted=true;
    if(!e.reservation.acquired || !e.consumer || !e.atomic_owner || !e.program_route.io_.cookie) {
        s.stopped=true;return kIOReturnNotReady;
    }
    const auto raw=ZornGen7SmmuFaultIrq26::createAndArm(s.controller,*e.consumer,ZornGen7SmmuFaultIrq26::Scope::Context,
        e.reservation.bank,s.banks,e.atomic_io,*e.atomic_owner,owner,authority,*this,
        stopForContextFault,this,e.fault_owner);
    if(raw!=kIOReturnSuccess || s.failed() || !e.fault_owner || !e.fault_owner->ready()) {
        s.stopped=true;return raw==kIOReturnSuccess?kIOReturnNotReady:raw;
    }
    s.gmu_fault_irq_ready=true;return kIOReturnSuccess;
}
void ZornGen7SmmuDomain26::stopForContextFault(void *context)
{
    auto *owner=static_cast<ZornGen7SmmuDomain26 *>(context);
    if(owner && owner->storage_)__atomic_store_n(&owner->storage_->irq_faulted,1u,__ATOMIC_RELEASE);
}
bool ZornGen7SmmuDomain26::faulted() const
{return storage_ && __atomic_load_n(&storage_->irq_faulted,__ATOMIC_ACQUIRE)!=0;}

IOReturn ZornGen7SmmuDomain26::prepareGmuStreamSlot(OSObject &owner,
    const ZornGen7SmmuStreamAuthority26 &authority)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_fault_irq_ready ||
       !s.firmware_holds_ready || !s.global_atomic_owner || !e.fault_owner ||
       !e.fault_owner->ready() || s.gmu_stream_attempted)return kIOReturnNotReady;
    s.gmu_stream_attempted=true;
    // Genuine fwspec values from the other two retained native endpoints,
    // not invented stream IDs or claims of ownership over their transactions.
    const uint32_t others[]={s.endpoints[0].packed,s.endpoints[1].packed};
    const auto raw=ZornGen7SmmuStream26::prepareBlocked(s.controller,*e.consumer,
        e.reservation.bank,s.id0,e.packed,others,2,s.stream_slots,s.global_atomic_io,
        *s.global_atomic_owner,owner,authority,*this,s.irq_faulted,e.stream_owner);
    if(raw!=kIOReturnSuccess || s.failed() || !e.stream_owner || !e.stream_owner->ready()) {
        s.stopped=true;return raw==kIOReturnSuccess?kIOReturnNotReady:raw;
    }
    s.gmu_stream_ready=true;return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::programGmuContext(unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    if(!budget || budget>1048576)return kIOReturnBadArgument;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_stream_ready ||
       !s.firmware_holds_ready || !s.boot_buffers_ready || !s.gmu_fault_irq_ready || !e.stream_owner ||
       !e.stream_owner->ready() || !e.fault_owner || !e.fault_owner->ready() ||
       !e.image_ready || e.state.poisoned || s.gmu_program_attempted)return kIOReturnNotReady;
    s.gmu_program_attempted=true;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    auto raw=e.stream_owner->applyActlrToDisabledBank(e.atomic_io,e.program_route.io_,
        e.reservation.context_offset,e.reservation.asid,budget);
    if(raw!=kIOReturnSuccess || s.failed())return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    s.gmu_program_status=ZornSmmuSparse4KProgramDisabledContext(&e.program_route.io_,
        e.reservation.bank,&e.context,budget,&s.gmu_program);
    if(s.gmu_program_status!=ZornSmmuSparse4KSuccess || s.failed() ||
       !s.gmu_program.enabled || !s.gmu_program.readback_valid ||
       s.gmu_program.context_offset!=e.reservation.context_offset)return refuse(kIOReturnIOError);
    // Do not silently qualify K80 using another board's readback waivers.
    // Any actual difference is retained for the precise hardware trial; no
    // automatic disable, adjustment or repeated programming follows.
    const auto &got=s.gmu_program.readback;const auto &want=e.image;
    if(!nativeGmuImage(got,want,s.native_controller_mode && e.packed==5 &&
        e.reservation.bank==2 && !e.context.ttbr0_switched && !e.context.upper))return refuse(kIOReturnNotReady);
    raw=e.stream_owner->verifyBlocked();if(raw!=kIOReturnSuccess || s.failed())
        return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    e.state.context_offset=s.gmu_program.context_offset;
    s.gmu_program_ready=true;return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::prepareNativeGlobalMaskedIrq(ZornGen7RegisterMaps26 &maps,
    OSObject &owner,ZornGen7NativeSmmuIrqResult26 &out)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if((s.native_controller_mode && !s.nativeControllerClaimHeld()) ||
       !s.ready || s.failed() || s.busy || !s.power || s.native_global_irq_attempted ||
       s.global_fault_owner || s.controller_start_attempted)return kIOReturnNotReady;
    s.native_global_irq_attempted=true;maps.retain();owner.retain();
    if(!maps.bindNativeGlobalSmmuFaultIo(s.controller,s.gate,s.native_global_fault_io)){
        s.stopped=true;return kIOReturnNotReady;}
    out.io_bound=true;
    const auto cfg=maps.probeNativeSmmuConfiguration(s.controller,s.gate,out);
    if(cfg!=kIOReturnSuccess || s.failed()){s.stopped=true;return cfg==kIOReturnSuccess?kIOReturnNotReady:cfg;}
    const auto raw=ZornGen7SmmuFaultIrq26::createNativeGlobalMasked(s.controller,s.banks,
        s.native_global_fault_io,maps,*this,stopForContextFault,this,s.native_global_masked_irq,out);
    if(raw!=kIOReturnSuccess || !out.registered_masked){s.stopped=true;return raw==kIOReturnSuccess?kIOReturnNotReady:raw;}
    return kIOReturnSuccess; // Masked actual handler only;no global fault-control or bank/stream grant.
}

IOReturn ZornGen7SmmuDomain26::prepareNativeQtbFence(OSObject &owner,ZornGen7IccInputs26 &power,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;auto &s=*storage_;
    if(!s.native_controller_mode || !s.nativeControllerClaimHeld() || !s.ready || s.failed() ||
       !s.power || s.native_qtb_attempted || s.native_qtb_provider)return kIOReturnNotReady;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    OSSharedPtr<IORegistryEntry> node(IORegistryEntry::fromPath("gpu-qtb",gIODTPlane,nullptr,nullptr,&s.controller),OSNoRetain);
    if(!node)return refuse(kIOReturnNotFound);
    IOPlatformDevice *provider=nullptr;
    if(ZornGen7NativeDtEntry26::canPromote(*node)){
        provider=new IOPlatformDevice;s.native_qtb_provider=provider;
        if(!provider)return refuse(kIOReturnNoMemory);
        if(!provider->init(node.get(),gIODTPlane) || !provider->attach(&s.controller))return refuse(kIOReturnNotAttached);
    }else{
        provider=OSDynamicCast(IOPlatformDevice,node.get());
        if(!provider || provider->getMetaClass()!=IOPlatformDevice::metaClass || provider->getProvider()!=&s.controller)return refuse(kIOReturnExclusiveAccess);
        provider->retain();s.native_qtb_provider=provider;
    }
    const auto resources=provider->getResources();if(resources!=kIOReturnSuccess)return refuse(resources);
    OSSharedPtr<OSObject> memory(provider->copyProperty(gIODeviceMemoryKey),OSNoRetain);
    auto *array=OSDynamicCast(OSArray,memory.get());IOMemoryDescriptor *actual=nullptr;
    if(array)for(unsigned i=0;i<array->getCount();++i){
        auto *entry=OSDynamicCast(IOMemoryDescriptor,array->getObject(i));IOByteCount contiguous=0;
        if(entry && entry->getLength()==0x1000u && entry->getPhysicalSegment(0,&contiguous,kIOMemoryMapperNone)==0x3de8000u && contiguous>=0x1000u){
            if(actual)return refuse(kIOReturnBadArgument);actual=entry;
        }
    }
    if(!actual)return refuse(kIOReturnNotFound);
    const auto range=validateGpuQtbRange(*provider,0,0);if(range)return refuse(range);
    return haltNativeQtb(*provider,*actual,power,owner,budget,s.native_qtb_result);
}
IOReturn ZornGen7SmmuDomain26::haltNativeQtb(IOService &provider,IOMemoryDescriptor &descriptor,ZornGen7IccInputs26 &power,OSObject &owner,
    unsigned budget,ZornGen7QtbFenceResult26 &out)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;auto &s=*storage_;
    if(!s.native_controller_mode || !s.nativeControllerClaimHeld() || !s.ready || s.failed() || !s.power ||
       s.native_qtb_attempted || s.controller_start_attempted || s.global_fault_ready)return kIOReturnNotReady;
    s.native_qtb_attempted=true;
    const auto raw=ZornGen7QtbFence26::createAndHalt(s.controller,provider,descriptor,s.pm,power,s.gate,owner,budget,s.native_qtb_owner,out);
    if(raw!=kIOReturnSuccess || !out.held || s.failed()){s.stopped=true;return raw==kIOReturnSuccess?kIOReturnNotReady:raw;}
    return kIOReturnSuccess; // Actual QTB fence only,not a cold/security/bank ownership grant.
}
IOReturn ZornGen7SmmuDomain26::resumeNativeQtbAfterColdInit()
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;auto &s=*storage_;
    if(!s.native_controller_mode || !s.nativeControllerClaimHeld() || s.failed() || !s.power || !s.native_qtb_owner ||
       !s.cold_returned || s.cold_raw!=kIOReturnSuccess || !s.cold_result.complete || !s.global_fault_ready ||
       !s.global_fault_owner || !s.global_fault_owner->ready())return kIOReturnNotReady;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    const auto resume=s.native_qtb_owner->resumeAfterQuiescedSmmuOperation(s.native_qtb_result);
    if(resume!=kIOReturnSuccess || s.failed())return refuse(resume==kIOReturnSuccess?kIOReturnNotReady:resume);
    // Source power_off's distinct arm_smmu_arch_write_sync reads real parent ID0.
    // Do not lower TBU bandwidth until the parent write-sync has actually returned.
    uint32_t id=0;if(s.io.read32(s.io.cookie,0x20,&id) || id!=s.id0 || s.failed())return refuse(kIOReturnNotReady);
    const auto lower=s.native_qtb_owner->lowerPowerAfterWriteSync(s.native_qtb_result);
    if(lower!=kIOReturnSuccess)return refuse(lower);return kIOReturnSuccess;
}
IOReturn ZornGen7SmmuDomain26::prepareNativeActiveGlobalFaults(ZornGen7RegisterMaps26 &maps,
    ZornGen7NativeSmmuControlResult26 &out,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || !budget || budget>1048576)return kIOReturnBadArgument;
    auto &s=*storage_;
    if(!s.native_controller_mode || !s.nativeControllerClaimHeld() || !s.ready || s.failed() || !s.power ||
       !s.native_global_masked_irq || s.global_fault_owner || s.global_fault_attempted || s.controller_start_attempted || out.attempted)return kIOReturnNotReady;
    s.global_fault_attempted=true;out.attempted=true;maps.retain();
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    ArmSmmu4KIo io{};if(!maps.bindNativeSmmuControlIo(s.controller,s.gate,io))return refuse(kIOReturnNotReady);
    auto read=[&](size_t at,uint32_t &v){out.last_io_raw=io.read32(io.cookie,at,&v);return out.last_io_raw==0 && !s.failed();};
    auto write=[&](size_t at,uint32_t v){out.last_io_raw=io.write32(io.cookie,at,v);return out.last_io_raw==0 && !s.failed();};
    auto barrier=[&](){out.last_io_raw=io.barrier(io.cookie);return out.last_io_raw==0 && !s.failed();};
    if(!read(0,out.cr0_before))return refuse(kIOReturnIOError);out.cr0_before_returned=true;
    // Active-controller path only. Disabled/global cold initialization remains
    // separate;this cannot activate foreign streams by clearing CLIENTPD.
    if(out.cr0_before&1u)return refuse(kIOReturnNotReady);out.active_controller=true;
    if(!read(0x48,out.gfsr))return refuse(kIOReturnIOError);out.gfsr_returned=true;
    if(out.gfsr)return refuse(kIOReturnNotReady); // No stale-fault clear/retry.
    uint32_t current=0;if(!read(0,current) || current!=out.cr0_before)return refuse(kIOReturnNotReady);
    if(!write(0x70,UINT32_MAX))return refuse(kIOReturnIOError);out.sync_write_returned=true;
    if(!barrier())return refuse(kIOReturnIOError);
    bool synchronized=false;for(unsigned i=0;i<budget;++i){
        if(!read(0x74,out.sync_status))return refuse(kIOReturnIOError);++out.sync_reads;
        if(!(out.sync_status&1u)){synchronized=true;break;}
    }
    if(!synchronized)return refuse(kIOReturnTimeout);
    if(!read(0x48,out.gfsr) || out.gfsr || !s.nativeControllerClaimHeld())return refuse(kIOReturnNotReady);
    // K80's active-controller path owns GFRE/GFIE only. Keep configuration
    // fault bits 4 and 5 as observed and require an exact CR0 readback.
    if(!write(0,out.cr0_before|UINT32_C(0x06)))return refuse(kIOReturnIOError);out.cr0_write_returned=true;
    if(!barrier() || !read(0,out.cr0_readback))return refuse(kIOReturnIOError);out.cr0_readback_returned=true;
    if(out.cr0_readback!=(out.cr0_before|UINT32_C(0x06)) || !read(0x48,out.gfsr) || out.gfsr)return refuse(kIOReturnNotReady);
    out.arm_raw=s.native_global_masked_irq->armNativeGlobalAfterControl();out.arm_returned=true;
    if(out.arm_raw!=kIOReturnSuccess || s.native_global_masked_irq->verifyNoFault()!=kIOReturnSuccess || s.failed())return refuse(out.arm_raw==kIOReturnSuccess?kIOReturnNotReady:out.arm_raw);
    s.global_fault_owner=s.native_global_masked_irq;s.global_cr0_before=out.cr0_before;
    s.global_cr0_expected=out.cr0_before|UINT32_C(0x06);s.global_cr0_readback=out.cr0_readback;
    s.global_fault_ready=true;
    out.complete=true;
    unsigned selected=0;
    if (!PE_parse_boot_argn("zorn26_gmu_context_irq", &selected, sizeof(selected)) || selected != 1)
        return kIOReturnSuccess;

    auto &endpoint=s.endpoints[2];
    const auto &reservation=endpoint.reservation;
    const unsigned bank=reservation.bank;
    unsigned intid=0;
    unsigned stage=1;
    const auto contextRaw=[&]() -> IOReturn {
        if (!s.context_probe_verified || !s.firmware_holds_ready || !s.gmu_image_ready ||
            !s.nativeControllerClaimHeld() || !endpoint.consumer ||
            reservation.consumer!=endpoint.consumer || !reservation.acquired ||
            endpoint.packed!=5 || bank<2 || bank>=s.banks || !s.reserved[bank] ||
            !endpoint.atomic_owner || !endpoint.atomic_io.read32)
            return kIOReturnNotReady;
        const auto readProbe=[&](size_t offset, uint32_t &value) {
            return !s.io.read32(s.io.cookie,offset,&value) && !s.failed();
        };
        uint32_t cbar=0,cba2r=0,sctlr=0;
        if (!readProbe(0x1000u+bank*4u,cbar) || !readProbe(0x1800u+bank*4u,cba2r) ||
            !readProbe(reservation.context_offset,sctlr) || cbar || cba2r || (sctlr&1u))
            return kIOReturnBusy;
        for (unsigned slot=0;slot<s.mapping_groups;++slot) {
            uint32_t smr=0,s2cr=0;
            if (!readProbe(0x800u+slot*4u,smr) || !readProbe(0xc00u+slot*4u,s2cr))
                return kIOReturnIOError;
            if (((s2cr>>16)&3u)==0u && (s2cr&0xffu)==bank)
                return kIOReturnBusy;
            if ((smr&(1u<<31)) && !((smr^endpoint.packed)&~((smr>>16)&0x7fffu)&0xffffu))
                return kIOReturnBusy;
        }
        stage=2;
        OSSharedPtr<OSObject> globals(s.controller.copyProperty("#global-interrupts"),OSNoRetain);
        OSSharedPtr<OSObject> interrupts(s.controller.copyProperty("interrupts"),OSNoRetain);
        auto *globalData=OSDynamicCast(OSData,globals.get());
        auto *irqData=OSDynamicCast(OSData,interrupts.get());
        if (!globalData || globalData->getLength()!=4 || !globalData->getBytesNoCopy() ||
            little(static_cast<const uint8_t *>(globalData->getBytesNoCopy()))!=1 ||
            !irqData || irqData->getLength()%12 || irqData->getLength()/12<=bank+1 ||
            !irqData->getBytesNoCopy())
            return kIOReturnBadArgument;
        const auto *tuples=static_cast<const uint8_t *>(irqData->getBytesNoCopy());
        const auto *tuple=tuples+(bank+1)*12;
        if (little(tuple) || little(tuple+4)>987 || little(tuple+8)!=4)
            return kIOReturnUnsupported;
        intid=little(tuple+4)+32u;
        for (size_t i=0;i<irqData->getLength()/12;++i)
            if (i!=bank+1 && !little(tuples+i*12) && little(tuples+i*12+4)==intid-32u)
                return kIOReturnExclusiveAccess;
        s.gmu_context_intid=intid;

        // The IRQ handler can read only FSR from this bank. The previous
        // SCTLR probe and all register writes remain closed.
        __atomic_store_n(&s.gmu_context_fault_readable,true,__ATOMIC_RELEASE);
        uint32_t fsr=0;
        if (endpoint.atomic_io.read32(endpoint.atomic_io.cookie,0x58u,&fsr) || fsr) {
            __atomic_store_n(&s.gmu_context_fault_readable,false,__ATOMIC_RELEASE);
            return kIOReturnNotReady;
        }
        stage=3;
        const ZornGen7SmmuFaultIrqAuthority26 authority{&s,nullptr,nullptr,Storage::authorizeNativeGmuContextSpi};
        const auto registered=ZornGen7SmmuFaultIrq26::createMasked(s.controller,*endpoint.consumer,
            ZornGen7SmmuFaultIrq26::Scope::Context,bank,s.banks,endpoint.atomic_io,*endpoint.atomic_owner,
            *this,authority,*this,stopForContextFault,this,endpoint.fault_owner);
        if (registered!=kIOReturnSuccess) return registered;
        stage=4;
        // Keep it masked until the bank's context image can be programmed.
        return kIOReturnSuccess;
    }();
    unsigned blocked=0;
    unsigned streamSnapshot=0;
    IOReturn streamRaw=contextRaw;
    if (contextRaw==kIOReturnSuccess &&
        PE_parse_boot_argn("zorn26_gmu_blocked_stream",&blocked,sizeof(blocked)) && blocked==1) {
        streamRaw=kIOReturnNotReady;
        streamSnapshot=1;
        if (s.nativeControllerClaimHeld() && !s.failed() && s.global_atomic_owner &&
            s.global_fault_owner->verifyNoFault()==kIOReturnSuccess && endpoint.fault_owner &&
            s.context_probe_addresses[2]>=reservation.context_offset) {
            s.gmu_stream_base=s.context_probe_addresses[2]-uint32_t(reservation.context_offset);
            const uint32_t peers[]={s.endpoints[0].packed,s.endpoints[1].packed};
            const ZornGen7SmmuStreamAuthority26 authority{&s,Storage::acquireNativeBlockedGmuStream};
            __atomic_store_n(&s.gmu_stream_thread,current_thread(),__ATOMIC_RELEASE);
            streamRaw=ZornGen7SmmuStream26::prepareBlocked(s.controller,*endpoint.consumer,bank,s.id0,
                endpoint.packed,peers,2,s.stream_slots,s.global_atomic_io,*s.global_atomic_owner,
                *this,authority,*this,s.irq_faulted,endpoint.stream_owner);
            if (streamRaw==kIOReturnSuccess)
                streamRaw=endpoint.stream_owner->verifyBlocked();
            __atomic_store_n(&s.gmu_stream_thread,THREAD_NULL,__ATOMIC_RELEASE);
            if (streamRaw==kIOReturnSuccess &&
                (!s.nativeControllerClaimHeld() || s.failed() || s.gmu_stream_writes!=2))
                streamRaw=kIOReturnNotReady;
            if (streamRaw==kIOReturnSuccess) s.gmu_stream_ready=true;
            streamSnapshot=1u | (s.gmu_stream_writes<<1) |
                ((s.gmu_stream_slot<24 ? s.gmu_stream_slot+1 : 0)<<3) |
                (unsigned(s.gmu_stream_ready)<<8);
        }
    }
    unsigned program=0;
    unsigned bankSnapshot=0;
    if (streamRaw==kIOReturnSuccess && s.gmu_stream_ready &&
        PE_parse_boot_argn("zorn26_gmu_program_bank",&program,sizeof(program)) && program==1) {
        bankSnapshot=1;
        streamRaw=kIOReturnNotReady;
        if (s.nativeControllerClaimHeld() && !s.failed() && s.context_probe_verified &&
            s.firmware_holds_ready && endpoint.image_ready && s.gmu_stream_slot<s.mapping_groups &&
            s.global_fault_owner->verifyNoFault()==kIOReturnSuccess) {
            // The selected stream is still invalid. Recheck the complete
            // blocked image and arm its retained fault handler before the
            // common programmer can enable translation in this bank.
            __atomic_store_n(&s.gmu_stream_thread,current_thread(),__ATOMIC_RELEASE);
            streamRaw=endpoint.stream_owner->verifyBlocked();
            if (streamRaw==kIOReturnSuccess) streamRaw=endpoint.fault_owner->arm();
            if (streamRaw==kIOReturnSuccess) streamRaw=endpoint.fault_owner->verifyNoFault();
            if (streamRaw==kIOReturnSuccess) {
                bankSnapshot|=2;
                s.gmu_fault_irq_ready=true;
                s.gmu_bank_programming=true;
                streamRaw=programGmuContext(budget);
                s.gmu_bank_programming=false;
                bankSnapshot|=(s.gmu_program.phase&7u)<<2;
                bankSnapshot|=unsigned(s.gmu_program.readback_valid!=0)<<5;
                bankSnapshot|=unsigned(s.gmu_program.tlb_synchronized!=0)<<6;
                bankSnapshot|=unsigned(s.gmu_program.enabled!=0)<<7;
                if (streamRaw==kIOReturnSuccess &&
                    (!s.nativeControllerClaimHeld() || s.failed() ||
                     endpoint.fault_owner->verifyNoFault()!=kIOReturnSuccess))
                    streamRaw=kIOReturnNotReady;
                if (streamRaw==kIOReturnSuccess) bankSnapshot|=256;
            }
            __atomic_store_n(&s.gmu_stream_thread,THREAD_NULL,__ATOMIC_RELEASE);
        }
    }
    unsigned observe=0;
    if (streamRaw==kIOReturnSuccess && (bankSnapshot&256) &&
        PE_parse_boot_argn("zorn26_gmu_observe_reset",&observe,sizeof(observe)) && observe==1) {
        unsigned observation=1;
        uint64_t reset=0,gx=0;
        streamRaw=kIOReturnNotReady;
        if (s.nativeControllerClaimHeld() && !s.failed() && endpoint.packed==5 && bank==2 &&
            !maps.access(0x3d00000u+0x1f800u*4u,4,false,reset)) {
            observation|=2 | ((reset&1u)?4u:0u);
            if (!maps.access(0x3d00000u+0x1f8d0u*4u,4,false,gx)) {
                observation|=8 | (unsigned(gx&3u)<<4);
                if ((reset&1u) && (gx&3u)==3u && s.nativeControllerClaimHeld() && !s.failed())
                    streamRaw=kIOReturnSuccess;
            }
        }
        if (streamRaw==kIOReturnSuccess) {
            s.gmu_stream_activating=true;
            __atomic_store_n(&s.gmu_stream_thread,current_thread(),__ATOMIC_RELEASE);
            const auto step=[&]() -> IOReturn {
                if (!endpoint.stream_owner || !endpoint.fault_owner ||
                    s.gmu_stream_slot>=s.mapping_groups ||
                    endpoint.stream_owner->verifyBlocked()!=kIOReturnSuccess ||
                    s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess ||
                    endpoint.fault_owner->verifyNoFault()!=kIOReturnSuccess)
                    return kIOReturnNotReady;
                const auto &io=s.global_atomic_io;
                const unsigned offset=4u*s.gmu_stream_slot;
                uint32_t smr=0,s2cr=0;
                if (io.read32(io.cookie,0x800u+offset,&smr) || smr!=5u)
                    return kIOReturnNotReady;
                observation|=64;
                const uint32_t expected=0x300u|bank;
                if (io.write32(io.cookie,0xc00u+offset,expected) ||
                    io.barrier(io.cookie) ||
                    io.read32(io.cookie,0xc00u+offset,&s2cr) ||
                    io.read32(io.cookie,0x800u+offset,&smr))
                    return kIOReturnIOError;
                if (s2cr!=expected || smr!=5u || s.gmu_activation_writes!=1 ||
                    !s.nativeControllerClaimHeld() || s.failed() ||
                    s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess ||
                    endpoint.fault_owner->verifyNoFault()!=kIOReturnSuccess)
                    return kIOReturnNotReady;
                observation|=128;
                return kIOReturnSuccess;
            };
            streamRaw=step();
            __atomic_store_n(&s.gmu_stream_thread,THREAD_NULL,__ATOMIC_RELEASE);
            s.gmu_stream_activating=false;
        }
        __atomic_store_n(&zornGmuStreamActivationSnapshot,observation,__ATOMIC_RELEASE);
        unsigned deferred=0;
        if (streamRaw==kIOReturnSuccess && observation==255 &&
            PE_parse_boot_argn("zorn26_gmu_deferred_valid",&deferred,sizeof(deferred)) && (deferred>=1 && deferred<=21)) {
            zornGmuDeferredSmr=[](ZornGen7SmmuDomain26 &owner) -> unsigned {
                auto &s=*owner.storage_;
                IORecursiveLockLock(&s.gate);
                const unsigned observed=[&]() -> unsigned {
                    auto &e=s.endpoints[2];
                    if (!s.nativeControllerClaimHeld() || s.failed() || !s.gmu_program_ready ||
                        !s.register_maps || e.packed!=5 || e.reservation.bank!=2 ||
                        s.gmu_stream_slot>=s.mapping_groups || s.gmu_activation_writes!=1)
                        return 1;
                    const auto resetHeld=[&]() {
                        uint64_t reset=0,gx=0;
                        return !s.register_maps->access(0x3d00000u+0x1f800u*4u,4,false,reset) &&
                            !s.register_maps->access(0x3d00000u+0x1f8d0u*4u,4,false,gx) &&
                            (reset&1u) && (gx&3u)==3u;
                    };
                    if (!resetHeld() || s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess ||
                        e.fault_owner->verifyNoFault()!=kIOReturnSuccess)
                        return 2;
                    s.gmu_smr_validating=true;
                    __atomic_store_n(&s.gmu_stream_thread,current_thread(),__ATOMIC_RELEASE);
                    const auto result=[&]() -> unsigned {
                        const auto active=owner.activateGmuStream();
                        if (active!=kIOReturnSuccess) return s.gmu_activation_writes==2 ? 5 : 4;
                        if (s.gmu_activation_writes!=2 || !s.nativeControllerClaimHeld() ||
                            s.failed() || !resetHeld())
                            return 6;
                        unsigned load=0;
                        if (!PE_parse_boot_argn("zorn26_gmu_deferred_valid",&load,sizeof(load)) || (load<2 || load>21))
                            return 7;

                        using ResetCheck=decltype(resetHeld);
                        struct LoadContext { Storage &state; const ResetCheck &reset; };
                        LoadContext context{s,resetHeld};
                        const ZornGen7GmuLoadAuthority26 authority{&context,
                            [](void *cookie,IOService &gmu,IOService &controller) {
                                auto &c=*static_cast<LoadContext *>(cookie);
                                auto &state=c.state;
                                return IORecursiveLockHaveLock(&state.gate) &&
                                    state.nativeControllerClaimHeld() && state.gmu_activation_ready &&
                                    !state.failed() && &controller==&state.controller &&
                                    &gmu==state.endpoints[2].consumer && c.reset() ? 0 : 1;
                            }};
                        if (owner.loadGmuTcmAndShadow(owner,authority)!=kIOReturnSuccess) return 8;
                        for (size_t i=0;i<s.firmware_block_count;++i) {
                            const auto &block=s.firmware_blocks[i];
                            if (!block.size || (block.region!=GG_ITCM && block.region!=GG_DTCM)) continue;
                            const bool itcm=block.region==GG_ITCM;
                            const unsigned word=(block.address-(itcm?0u:0x10004000u))/4u;
                            for (unsigned index=0;index<block.size/4u;++index) {
                                if (s.failed()) return 9;
                                uint32_t actual=0;
                                if (itcm) actual=s.itcm_shadow[word+index];
                                else if (s.register_maps->accessGmuTcmWord(0x1c400u+word+index,false,actual))
                                    return 9;
                                if (actual!=little(s.firmware_bytes+block.payload_offset+index*4u))
                                    return 9;
                            }
                        }
                        if (!s.nativeControllerClaimHeld() || s.failed() || !resetHeld() ||
                            s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess ||
                            e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
                            e.stream_owner->verifyActive()!=kIOReturnSuccess)
                            return 9;
                        return 10;
                    }();
                    __atomic_store_n(&s.gmu_stream_thread,THREAD_NULL,__ATOMIC_RELEASE);
                    s.gmu_smr_validating=false;
                    if (result!=10 || !zornGmuTcmVerified || zornGmuTcmDomain!=&owner)
                        return result;
                    // The final reset, fault and stream readbacks above have returned.
                    if (!s.gmu_load_ready || !s.gmu_versions_ready || !s.boot_buffers || s.hwsched_buffers)
                        return 11;
                    s.gmu_cold_readback=true;
                    __atomic_store_n(&s.gmu_stream_thread,current_thread(),__ATOMIC_RELEASE);
                    const unsigned boardResult=zornGmuTcmVerified(*zornGmuTcmBoard,owner,s.versions);
                    if((boardResult==24 || boardResult==26 || boardResult==28 || boardResult==30 || boardResult==32 || boardResult==34 || boardResult==36 || boardResult==38 || boardResult==40 || boardResult==42 || boardResult==44 || boardResult==46 || boardResult==48 || boardResult==50 || boardResult==52 || boardResult==54) && (s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess ||
                       e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
                       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())){
                        __atomic_store_n(&s.gmu_stream_thread,THREAD_NULL,__ATOMIC_RELEASE);
                        s.gmu_cold_readback=false;
                        return boardResult-1;
                    }
                    __atomic_store_n(&s.gmu_stream_thread,THREAD_NULL,__ATOMIC_RELEASE);
                    s.gmu_cold_readback=false;
                    if(boardResult!=54)return boardResult;
                    const auto preflight=s.observeHostMmuPreflight();
                    if(preflight!=56 || !zornHostFenceHandoff)return preflight;
                    return zornHostFenceHandoff(*zornGmuTcmBoard,owner,
                        [](ZornGen7SmmuDomain26 &domain,OSObject &board,ZornGen7IccInputs26 &power,
                           unsigned budget,uint32_t &steps) -> IOReturn {
                            auto &state=*domain.storage_;
                            if(!IORecursiveLockHaveLock(&state.gate) || !state.host_context_images_ready ||
                               !state.nativeControllerClaimHeld() || state.failed() ||
                               !state.register_maps || !state.register_maps->providerClaimsHeld() ||
                               !state.global_fault_owner || state.global_fault_owner->verifyNoFault())
                                return kIOReturnNotReady;
                            auto &maps=*state.register_maps;
                            // Cold boot precedes oob_gpu and H2F_MSG_START.
                            // The source waits for GMU idle during slumber,
                            // which differs from exclusion of the powered-off GX.
                            const auto gxOff=[&](){
                                constexpr uint32_t gfxPowerClockStatus=0x03d00000u+0x1f8d0u*4u;
                                uint64_t value=0;
                                return !maps.access(gfxPowerClockStatus,4,false,value) && (value&3u)==3u;
                            };
                            if(!gxOff())return kIOReturnBusy;
                            if(state.host_gpu_mmu_attempted)return kIOReturnNotReady;
                            state.host_gpu_mmu_attempted=true;state.host_gpu_mmu_poll_budget=budget;
                            steps|=1;
                            auto raw=state.haltHostQtb(board,power,budget);
                            if(raw)return raw;
                            steps|=2;
                            if(state.failed() || !state.nativeControllerClaimHeld() ||
                               state.global_fault_owner->verifyNoFault() || !gxOff())
                                return kIOReturnNotReady;
                            steps|=4;
                            const ZornGen7SmmuFaultIrqAuthority26 faults{&state,nullptr,nullptr,
                                [](void *cookie,IOService &controller,IOService &consumer,
                                   unsigned bank,unsigned source,uint32_t intid) {
                                    auto &s=*static_cast<Storage *>(cookie);
                                    if(!IORecursiveLockHaveLock(&s.gate) || !s.nativeControllerClaimHeld() ||
                                       !s.host_gpu_qtb_result.held || s.failed() || &controller!=&s.controller ||
                                       bank>=2 || source!=bank+1 || intid!=709+bank ||
                                       s.endpoints[bank].consumer!=&consumer ||
                                       s.endpoints[bank].reservation.bank!=bank)
                                        return 1;
                                    const auto distributor=ml_io_map(0x17100000,0x4000);
                                    if(!distributor)return 1;
                                    const unsigned word=(intid/32)*4;
                                    const uint32_t bit=UINT32_C(1)<<(intid%32);
                                    const uint32_t occupied=ml_io_read32(distributor+0x100+word) |
                                        ml_io_read32(distributor+0x200+word) |
                                        ml_io_read32(distributor+0x300+word);
                                    return (occupied&bit)?1:0;
                                }};
                            const ZornGen7SmmuStreamAuthority26 streams{&state,Storage::acquireNativeBlockedHostStream};
                            for(unsigned i=0;i<2;++i){
                                auto &e=state.endpoints[i];
                                if(e.packed!=i || e.reservation.bank!=i || !e.consumer || !e.atomic_owner ||
                                   e.fault_owner || e.stream_owner || state.failed())return kIOReturnNotReady;
                                __atomic_store_n(&state.host_fault_readable[i],true,__ATOMIC_RELEASE);
                                uint32_t fsr=0;
                                if(e.atomic_io.read32(e.atomic_io.cookie,0x58,&fsr) || fsr){
                                    __atomic_store_n(&state.host_fault_readable[i],false,__ATOMIC_RELEASE);
                                    return kIOReturnNotReady;
                                }
                                raw=ZornGen7SmmuFaultIrq26::createAndArm(state.controller,*e.consumer,
                                    ZornGen7SmmuFaultIrq26::Scope::Context,i,state.banks,e.atomic_io,
                                    *e.atomic_owner,domain,faults,domain,stopForContextFault,&domain,e.fault_owner);
                                if(raw || state.failed() || e.fault_owner->verifyNoFault())
                                    return raw?raw:kIOReturnNotReady;
                                steps|=8u<<i;
                                const uint32_t peers[]={state.endpoints[1-i].packed,state.endpoints[2].packed};
                                state.host_blocked_endpoint=i;
                                state.host_blocked_slot=256;
                                state.host_blocked_writes=0;
                                __atomic_store_n(&state.host_blocked_thread,current_thread(),__ATOMIC_RELEASE);
                                raw=ZornGen7SmmuStream26::prepareBlocked(state.controller,*e.consumer,i,
                                    state.id0,e.packed,peers,2,state.stream_slots,state.global_atomic_io,
                                    *state.global_atomic_owner,domain,streams,domain,state.irq_faulted,e.stream_owner);
                                if(!raw)raw=e.stream_owner->verifyBlocked();
                                __atomic_store_n(&state.host_blocked_thread,THREAD_NULL,__ATOMIC_RELEASE);
                                if(raw || state.failed() || state.host_blocked_writes!=2)
                                    return raw?raw:kIOReturnNotReady;
                                steps|=32u<<i;
                            }
                            steps=1;
                            if(!gxOff() || state.failed() || state.global_fault_owner->verifyNoFault() ||
                               !state.host_gpu_qtb_result.held || !state.nativeControllerClaimHeld() ||
                               !zornHostZero || zornHostZeroOwner!=state.firmware_owner)
                                return kIOReturnNotReady;
                            raw=state.prepareHostPrrZero(*zornHostZero);
                            if(raw)return raw;
                            raw=state.publishHostPrrZero();
                            if(raw)return raw;
                            steps|=2;

                            state.prr_expected[0]=uint32_t(state.host_zero_physical);
                            state.prr_expected[1]=uint32_t(state.host_zero_physical>>32);
                            __atomic_store_n(&state.host_context_thread,current_thread(),__ATOMIC_RELEASE);
                            const auto programRaw=[&]() -> IOReturn {
                                const auto &global=state.global_atomic_io;
                                state.host_prr_window=true;
                                for(unsigned i=0;i<2;++i)
                                    if(global.write32(global.cookie,0x6008+4u*i,state.prr_expected[i]))
                                        return kIOReturnIOError;
                                if(global.barrier(global.cookie))return kIOReturnIOError;
                                for(unsigned i=0;i<2;++i){
                                    uint32_t value=0;
                                    if(global.read32(global.cookie,0x6008+4u*i,&value) ||
                                       value!=state.prr_expected[i])return kIOReturnIOError;
                                }
                                state.host_prr_window=false;
                                steps|=4;
                                for(unsigned i=0;i<2;++i){
                                    auto &e=state.endpoints[i];
                                    const auto actlrRaw=ZornGen7SelectActlr(state.controller,e.packed,
                                        e.requested_actlr_present,e.requested_actlr);
                                    if(actlrRaw)return actlrRaw;
                                    if(!e.requested_actlr_present)return kIOReturnNotFound;
                                    state.host_program_bank=i;
                                    state.host_blocked_endpoint=i;
                                    state.host_blocked_slot=256;
                                    __atomic_store_n(&state.host_blocked_thread,current_thread(),__ATOMIC_RELEASE);
                                    const auto blocked=e.stream_owner->applyActlrToDisabledBank(e.atomic_io,
                                        e.program_route.io_,e.reservation.context_offset,e.reservation.asid,budget);
                                    __atomic_store_n(&state.host_blocked_thread,THREAD_NULL,__ATOMIC_RELEASE);
                                    if(blocked || state.failed())return blocked?blocked:kIOReturnNotReady;
                                    const auto &c=e.atomic_io;
                                    if(c.read32(c.cookie,4,&state.host_actlr_before[i]) ||
                                       c.write32(c.cookie,4,state.host_actlr_before[i]|(1u<<5)) ||
                                       c.barrier(c.cookie) || c.read32(c.cookie,4,&state.host_actlr_after[i]) ||
                                       state.host_actlr_after[i]!=(state.host_actlr_before[i]|(1u<<5)))
                                        return kIOReturnIOError;
                                    steps|=8u<<i;
                                    const auto configured=state.host_gpu_tables->programContext(i,e.program_route.io_,
                                        e.reservation.bank,e.reservation.context_offset,budget);
                                    if(configured || state.failed())return configured?configured:kIOReturnNotReady;
                                    steps|=32u<<i;
                                }
                                for(unsigned i=0;i<2;++i){
                                    auto &e=state.endpoints[i];
                                    state.host_program_bank=i;
                                    Zorn26TraceHostStream(i,1,0);
                                    const auto verified=state.host_gpu_tables->verifyContext(i,e.program_route.io_,
                                        e.reservation.bank,e.reservation.context_offset);
                                    Zorn26TraceHostStream(i,2,verified);
                                    if(verified || e.fault_owner->verifyNoFault() ||
                                       state.global_fault_owner->verifyNoFault() || state.failed() || !gxOff())
                                        return verified?verified:kIOReturnNotReady;
                                }
                                for(unsigned i=0;i<2;++i){
                                    auto &e=state.endpoints[i];
                                    state.host_program_bank=i;
                                    state.host_blocked_endpoint=i;
                                    if(!state.nativeControllerClaimHeld() || !state.host_gpu_qtb_result.held ||
                                       state.failed() || !gxOff())return kIOReturnNotReady;
                                    state.host_stream_activation=true;
                                    __atomic_store_n(&state.host_blocked_thread,current_thread(),__ATOMIC_RELEASE);
                                    const auto activated=e.stream_owner->activatePreparedWithPeer(
                                        state.endpoints[1-i].stream_owner);
                                    __atomic_store_n(&state.host_blocked_thread,THREAD_NULL,__ATOMIC_RELEASE);
                                    state.host_stream_activation=false;
                                    if(activated || state.failed())return activated?activated:kIOReturnNotReady;
                                    __atomic_fetch_or(&zornHostStreamSnapshot,1u<<i,__ATOMIC_RELEASE);
                                }
                                for(unsigned i=0;i<2;++i){
                                    auto &e=state.endpoints[i];
                                    state.host_program_bank=i;
                                    state.host_blocked_endpoint=i;
                                    __atomic_store_n(&state.host_blocked_thread,current_thread(),__ATOMIC_RELEASE);
                                    const auto active=e.stream_owner->verifyActive();
                                    __atomic_store_n(&state.host_blocked_thread,THREAD_NULL,__ATOMIC_RELEASE);
                                    const auto verified=state.host_gpu_tables->verifyContext(i,e.program_route.io_,
                                        e.reservation.bank,e.reservation.context_offset);
                                    if(active || verified || e.fault_owner->verifyNoFault() ||
                                       state.global_fault_owner->verifyNoFault() || state.failed() || !gxOff())
                                        return active?active:(verified?verified:kIOReturnNotReady);
                                    __atomic_fetch_or(&zornHostStreamSnapshot,4u<<i,__ATOMIC_RELEASE);
                                }
                                return kIOReturnSuccess;
                            }();
                            __atomic_store_n(&state.host_context_thread,THREAD_NULL,__ATOMIC_RELEASE);
                            state.host_prr_window=false;
                            state.host_program_bank=2;
                            if(programRaw)return programRaw;
                            raw=state.resumeHostQtb();
                            if(raw)return raw;
                            if(state.failed() || state.global_fault_owner->verifyNoFault() || !gxOff())
                                return kIOReturnNotReady;
                            state.host_gpu_qtb_released=true;state.host_gpu_mmu_ready=true;
                            state.native_host_runtime_ready=true;
                            steps|=128;
                            return kIOReturnSuccess;
                        });
                }();
                if (observed!=7 && observed!=10 && observed!=16 && observed!=20 && observed!=24 && observed!=26 && observed!=28 && observed!=30 && observed!=32 && observed!=34 && observed!=36 && observed!=38 && observed!=40 && observed!=42 && observed!=44 && observed!=46 && observed!=48 && observed!=50 && observed!=52 && observed!=56 && observed!=82 && observed!=84 && observed!=86 && observed!=88) s.stopped=true;
                IORecursiveLockUnlock(&s.gate);
                return observed;
            };
            retain();
            __atomic_store_n(&zornGmuDeferredOwner,this,__ATOMIC_RELEASE);
        }

    }
    // The common programmer validates the entire image before reporting
    // phase 5. The unswitched GMU context has only the two documented
    // one-direction differences below in that validator.
    unsigned readbackDelta=0;
    if (s.gmu_program.phase==5 && s.gmu_program.readback_valid) {
        const auto &actual=s.gmu_program.readback;
        const auto &expected=endpoint.image;
        readbackDelta=unsigned((actual.tcr2^expected.tcr2)&0x20u ? 1 : 0) |
            unsigned((actual.tcr2^expected.tcr2)&0x40u ? 2 : 0) |
            unsigned((actual.sctlr^expected.sctlr)&0x1000u ? 4 : 0);
    }
    const uint64_t snapshot=(uint64_t(readbackDelta&3u)<<62) |
        (uint64_t(readbackDelta>>2)<<31) |
        (uint64_t(bankSnapshot)<<53) | (uint64_t(streamSnapshot)<<44) |
        (uint64_t(intid)<<16) | (uint64_t(bank)<<8) | stage;
    __atomic_store_n(&zornGmuContextIrqSnapshot,snapshot,__ATOMIC_RELEASE);
    if (streamRaw!=kIOReturnSuccess) s.stopped=true;
    return streamRaw;
}
IOReturn ZornGen7SmmuDomain26::prepareNativeColdController(OSObject &owner,
    const ZornGen7SmmuColdAuthority26 &cold,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || !budget || budget>1048576)return kIOReturnBadArgument;
    auto &s=*storage_;
    if(!s.native_controller_mode || !s.nativeControllerClaimHeld() || !s.ready || s.failed() || !s.power ||
       !s.native_global_masked_irq || !s.native_qtb_owner || !s.native_qtb_result.held ||
       s.controller_start_attempted || s.global_fault_attempted || !cold.acquireActualColdController)return kIOReturnNotReady;
    s.controller_start_attempted=true;auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    auto *maps=static_cast<ZornGen7RegisterMaps26 *>(s.native_global_fault_io.cookie);
    if(!maps)return refuse(kIOReturnNotReady);ArmSmmu4KIo probe{};
    if(!maps->bindNativeSmmuControlIo(s.controller,s.gate,probe))return refuse(kIOReturnNotReady);
    uint32_t before=0;if(probe.read32(probe.cookie,0,&before))return refuse(kIOReturnIOError);
    if(!(before&1u))return refuse(kIOReturnNotReady); // Active fault-control path is distinct.
    auto &g=s.cold_geometry;g.id[0]=s.id0;g.id[1]=s.id1;g.id[2]=s.id2;g.groups=s.mapping_groups;
    g.banks=s.banks;g.contextBase=s.context_base;g.stride=s.register_stride;g.matching=s.stream_matching;
    uint32_t expected=0;if(!ZornGen7SmmuCold26::ExpectedCr0(g,before,expected))return refuse(kIOReturnUnsupported);
    owner.retain();s.cold_authority_owner=&owner;s.cold_authority=cold;
    // Independent real whole-controller exclusion is still mandatory. The
    // actual QTB fence is one prerequisite,never a fabricated all-bank/security grant.
    s.cold_grant_raw=cold.acquireActualColdController(cold.cookie,s.controller,g.id,before,expected,g.groups,g.banks,g.contextBase,g.stride);
    s.cold_grant_returned=true;if(s.cold_grant_raw || s.failed())return refuse(kIOReturnNotPermitted);
    ArmSmmu4KIo io{};
    if(!maps->bindNativeColdSmmuIo(s.controller,s.gate,g.groups,g.banks,g.contextBase,g.stride,g.matching,expected,io))return refuse(kIOReturnNotReady);
    s.global_fault_attempted=true;
    s.cold_raw=ZornGen7SmmuCold26::Initialize(io,g,before,budget,s.irq_faulted,s.cold_result);s.cold_returned=true;
    if(s.cold_raw!=kIOReturnSuccess || !s.cold_result.complete || s.failed())return refuse(s.cold_raw==kIOReturnSuccess?kIOReturnNotReady:s.cold_raw);
    const auto arm=s.native_global_masked_irq->armNativeGlobalAfterControl();
    if(arm!=kIOReturnSuccess || s.native_global_masked_irq->verifyNoFault()!=kIOReturnSuccess || s.failed())return refuse(arm==kIOReturnSuccess?kIOReturnNotReady:arm);
    s.global_fault_owner=s.native_global_masked_irq;s.global_cr0_before=before;s.global_cr0_expected=expected;s.global_cr0_readback=s.cold_result.cr0Readback;s.global_fault_ready=true;
    return resumeNativeQtbAfterColdInit();
}
IOReturn ZornGen7SmmuDomain26::prepareControllerAndGlobalFaults(OSObject &owner,
    const ZornGen7SmmuColdAuthority26 &cold,const ZornGen7SmmuFaultIrqAuthority26 &authority,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || !budget || budget>1048576)return kIOReturnNotReady;
    auto &s=*storage_;
    if(s.native_global_masked_irq)return prepareNativeColdController(owner,cold,budget); // Reuse actual masked owner;never double-register SPI.
    if(!s.ready || s.failed() || s.busy || !s.power || !s.context_views_ready || !s.global_atomic_owner ||
       s.global_fault_attempted || s.controller_start_attempted)return kIOReturnNotReady;
    s.controller_start_attempted=true;auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    uint32_t cr0=0;const auto &io=s.global_atomic_io;
    const int initialRaw=io.read32(io.cookie,0,&cr0);if(initialRaw)return refuse(kIOReturnIOError);
    if(!(cr0&1u))return prepareGlobalFaultReporting(owner,authority,budget);
    // Distinct disabled-controller initialization. No enabled/foreign stream
    // is reset by the preserved active-controller fault-reporting path.
    if(!cold.acquireActualColdController)return refuse(kIOReturnNotPermitted);
    auto &g=s.cold_geometry;for(unsigned i=0;i<3;++i)g.id[i]=i==0?s.id0:(i==1?s.id1:s.id2);
    g.groups=s.mapping_groups;g.banks=s.banks;g.contextBase=s.context_base;g.stride=s.register_stride;g.matching=s.stream_matching;
    uint32_t proposed=0;if(!ZornGen7SmmuCold26::ExpectedCr0(g,cr0,proposed))return refuse(kIOReturnUnsupported);
    owner.retain();s.cold_authority_owner=&owner;s.cold_authority=cold;
    s.cold_grant_raw=cold.acquireActualColdController(cold.cookie,s.controller,g.id,cr0,proposed,
        g.groups,g.banks,g.contextBase,g.stride);s.cold_grant_returned=true;
    if(s.cold_grant_raw || s.failed())return refuse(kIOReturnNotPermitted);
    // Register the genuine global IRQ masked. Source stale-fault clearing is
    // allowed only inside cold initialization;arming first could immediately
    // consume a stale status as a new run's terminal fault.
    s.global_fault_attempted=true;
    const auto raw=ZornGen7SmmuFaultIrq26::createMasked(s.controller,s.controller,
        ZornGen7SmmuFaultIrq26::Scope::Global,0,s.banks,io,*s.global_atomic_owner,owner,
        authority,*this,stopForContextFault,this,s.global_fault_owner);
    if(raw!=kIOReturnSuccess || !s.global_fault_owner || s.failed())return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.cold_raw=ZornGen7SmmuCold26::Initialize(io,g,cr0,budget,s.irq_faulted,s.cold_result);s.cold_returned=true;
    if(s.cold_raw!=kIOReturnSuccess || !s.cold_result.complete || s.failed())return refuse(s.cold_raw==kIOReturnSuccess?kIOReturnNotReady:s.cold_raw);
    const auto armRaw=s.global_fault_owner->arm();
    if(armRaw!=kIOReturnSuccess || s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || s.failed())return refuse(armRaw==kIOReturnSuccess?kIOReturnNotReady:armRaw);
    s.global_cr0_before=cr0;s.global_cr0_expected=s.cold_result.cr0Expected;s.global_cr0_readback=s.cold_result.cr0Readback;
    s.global_fault_ready=true;
    if(s.native_qtb_owner)return resumeNativeQtbAfterColdInit();
    return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::prepareGlobalFaultReporting(OSObject &owner,
    const ZornGen7SmmuFaultIrqAuthority26 &authority,unsigned budget)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    if(!budget || budget>1048576 || !authority.acquireActualFaultControl)return kIOReturnBadArgument;
    auto &s=*storage_;
    if(!s.ready || s.failed() || s.busy || !s.power || !s.context_views_ready ||
       !s.global_atomic_owner || s.global_fault_attempted)return kIOReturnNotReady;
    s.global_fault_attempted=true;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    const auto raw=ZornGen7SmmuFaultIrq26::createAndArm(s.controller,s.controller,
        ZornGen7SmmuFaultIrq26::Scope::Global,0,s.banks,s.global_atomic_io,
        *s.global_atomic_owner,owner,authority,*this,stopForContextFault,this,s.global_fault_owner);
    if(raw!=kIOReturnSuccess || s.failed() || !s.global_fault_owner || !s.global_fault_owner->ready())
        return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    const auto &io=s.global_atomic_io;
    if(io.read32(io.cookie,0,&s.global_cr0_before))return refuse(kIOReturnIOError);
    // This non-reset path reuses an already enabled controller. CLIENTPD is
    // not silently cleared: doing so may activate every foreign stream.
    // A disabled controller needs a separate full-controller cold-init path.
    if(s.global_cr0_before&1u)return refuse(kIOReturnNotReady);
    // Exact GFRE/GFIE/GCFGFRE/GCFGFIE source bits only. Preserve EXID, bypass,
    // sharing, broadcasting and every other global field/unknown firmware user.
    s.global_cr0_expected=s.global_cr0_before|UINT32_C(0x36);
    s.global_grant_raw=authority.acquireActualFaultControl(authority.cookie,s.controller,
        s.global_cr0_before,s.global_cr0_expected);s.global_grant_returned=true;
    if(s.global_grant_raw)return refuse(kIOReturnNotPermitted);
    uint32_t current=0;
    if(io.read32(io.cookie,0,&current))return refuse(kIOReturnIOError);
    if(current!=s.global_cr0_before || s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || s.failed())
        return refuse(kIOReturnNotReady);
    // Source global sync ordering without flushing unowned translations or
    // resetting tables/banks. Caller supplies the existing bounded read count;
    // this is not a claim of Linux elapsed-time timeout equivalence.
    s.global_sync_write_raw=io.write32(io.cookie,0x70,UINT32_MAX);s.global_sync_write_returned=true;
    if(s.global_sync_write_raw || io.barrier(io.cookie))return refuse(kIOReturnIOError);
    bool synchronized=false;
    for(unsigned i=0;i<budget;++i) {
        if(s.failed() || !s.global_fault_owner->ready())return refuse(kIOReturnNotReady);
        s.global_sync_read_raw=io.read32(io.cookie,0x74,&s.global_sync_status);
        s.global_sync_read_returned=true;++s.global_sync_reads;
        if(s.global_sync_read_raw)return refuse(kIOReturnIOError);
        if(!(s.global_sync_status&1u)){synchronized=true;break;}
    }
    if(!synchronized)return refuse(kIOReturnTimeout);
    if(io.barrier(io.cookie))return refuse(kIOReturnIOError);
    if(s.failed() || !s.global_fault_owner->ready())return refuse(kIOReturnNotReady);
    s.global_cr0_write_raw=io.write32(io.cookie,0,s.global_cr0_expected);s.global_cr0_write_returned=true;
    if(s.global_cr0_write_raw || io.barrier(io.cookie) ||
       io.read32(io.cookie,0,&s.global_cr0_readback))return refuse(kIOReturnIOError);
    if(s.global_cr0_readback!=s.global_cr0_expected ||
       s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    s.global_fault_ready=true;return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::activateGmuStream()
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_program_ready || !s.gmu_stream_ready ||
       !s.firmware_holds_ready || !s.boot_buffers_ready || !s.global_fault_ready || !s.global_fault_owner ||
       !s.global_fault_owner->ready() || !s.gmu_fault_irq_ready || !e.fault_owner || !e.fault_owner->ready() ||
       !e.stream_owner || !e.stream_owner->ready() || !e.image_ready || e.state.poisoned ||
       s.gmu_activation_attempted)return kIOReturnNotReady;
    s.gmu_activation_attempted=true;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.fault_owner->verifyNoFault()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    s.activation_before_status=ZornSmmuSparse4KObserveOwnedContext(&e.program_route.io_,
        e.reservation.bank,&e.context,&s.activation_before);
    if(s.activation_before_status!=ZornSmmuSparse4KSuccess || !s.activation_before.enabled ||
       !s.activation_before.readback_valid || s.activation_before.context_offset!=e.reservation.context_offset ||
       !nativeGmuImage(s.activation_before.readback,e.image,s.native_controller_mode &&
           e.packed==5 && e.reservation.bank==2 && !e.context.ttbr0_switched && !e.context.upper) || s.failed())return refuse(kIOReturnNotReady);
    auto raw=e.stream_owner->activatePrepared();
    if(raw!=kIOReturnSuccess || s.failed())return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.activation_after_status=ZornSmmuSparse4KObserveOwnedContext(&e.program_route.io_,
        e.reservation.bank,&e.context,&s.activation_after);
    if(s.activation_after_status!=ZornSmmuSparse4KSuccess || !s.activation_after.enabled ||
       !s.activation_after.readback_valid || s.activation_after.context_offset!=e.reservation.context_offset ||
       !nativeGmuImage(s.activation_after.readback,e.image,s.native_controller_mode &&
           e.packed==5 && e.reservation.bank==2 && !e.context.ttbr0_switched && !e.context.upper) || s.failed())return refuse(kIOReturnNotReady);
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.fault_owner->verifyNoFault()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    raw=e.stream_owner->verifyActive();if(raw!=kIOReturnSuccess || s.failed())
        return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    // This source state only follows real successful IO. It is not a GPU
    // completion/fence, release permission or proof of a working GMU/HFI.
    s.gmu_activation_ready=true;return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::loadGmuTcmAndShadow(OSObject &owner,
    const ZornGen7GmuLoadAuthority26 &authority)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) ||
       !authority.acquireResetHeldFirmwareLoad)return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_activation_ready || !s.register_maps ||
       !s.firmware_holds_ready || !s.boot_buffers_ready || !s.firmware_memory ||
       !s.global_fault_owner || !s.global_fault_owner->ready() || !e.fault_owner || !e.fault_owner->ready() ||
       !e.stream_owner || !e.image_ready || e.state.poisoned || s.gmu_load_attempted)return kIOReturnNotReady;
    s.gmu_load_attempted=true;owner.retain();
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    // Reuse the immutable parser plan and actual five objects prepared/held
    // earlier. All payload destinations are preflighted before the first TCM
    // store. External RAM already contains the very same fresh firmware copy;
    // compare it privately rather than copying onto a device-held object again.
    if(!s.firmware_bytes || s.firmware_size!=FHG_GMU_BYTES || !s.firmware_block_count ||
       s.firmware_block_count>GG_FW_MAX_BLOCKS)return refuse(kIOReturnNotReady);
    // Acquire genuine reset/exclusion before reading device-held RAM too.
    s.gmu_load_grant_raw=authority.acquireResetHeldFirmwareLoad(authority.cookie,*e.consumer,s.controller);
    s.gmu_load_grant_returned=true;
    if(s.gmu_load_grant_raw)return refuse(kIOReturnNotPermitted);
    for(size_t i=0;i<s.firmware_block_count;++i) {
        const auto &b=s.firmware_blocks[i];if(!b.size)continue;
        if((b.address&3u) || (b.size&3u) || b.payload_offset>s.firmware_size ||
           b.size>s.firmware_size-b.payload_offset)return refuse(kIOReturnBadArgument);
        if(b.region==GG_ITCM || b.region==GG_DTCM) {
            const uint32_t base=b.region==GG_ITCM?0u:0x10004000u;
            if(b.address<base || b.address-base>0x4000u || b.size>0x4000u-(b.address-base))
                return refuse(kIOReturnBadArgument);
        } else {
            bool covered=false;
            for(unsigned k=0;k<5;++k) {
                const auto &r=s.firmware_ranges[k];
                if(b.address<r.iova || b.size>r.bytes || uint64_t(b.address)-r.iova>r.bytes-b.size)continue;
                const auto &m=s.firmware_memory->bo(k);
                if(m.quarantined() || !m.deviceReferences() || !m.mapping() ||
                   m.bytes()!=r.bytes)return refuse(kIOReturnNotReady);
                const auto *cpu=static_cast<const volatile uint8_t *>(m.mapping());
                const size_t offset=size_t(uint64_t(b.address)-r.iova);
                for(size_t at=0;at<b.size;++at)
                    if(cpu[offset+at]!=s.firmware_bytes[b.payload_offset+at])return refuse(kIOReturnBadArgument);
                covered=true;break;
            }
            if(!covered)return refuse(kIOReturnBadArgument);
        }
    }
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    for(size_t i=0;i<s.firmware_block_count;++i) {
        const auto &b=s.firmware_blocks[i];if(!b.size || (b.region!=GG_ITCM && b.region!=GG_DTCM))continue;
        const uint32_t base=b.region==GG_ITCM?0u:0x10004000u;
        const uint32_t first=(b.region==GG_ITCM?0x1b400u:0x1c400u)+(b.address-base)/4u;
        for(size_t at=0;at<b.size;at+=4) {
            if(s.failed())return refuse(kIOReturnNotReady);
            uint32_t actual=little(s.firmware_bytes+b.payload_offset+at);
            s.gmu_load_last_returned=false;
            s.gmu_load_last_raw=s.register_maps->accessGmuTcmWord(first+uint32_t(at/4),true,actual);
            s.gmu_load_last_returned=true;
            if(s.gmu_load_last_raw)return refuse(kIOReturnIOError);
            ++s.tcm_words_written;
        }
    }
    __asm__ volatile("dsb sy" ::: "memory"); // Original final wmb, not cache cleaning.
    // Registered direct source keeps its earlier read. HWSCHED source reads
    // versions only after SCM and register_config;never duplicate that read here.
    if(!s.hwsched_buffers){
        const auto raw=readActualGmuVersions();if(raw!=kIOReturnSuccess)return raw;
    }
    s.itcm_shadow=static_cast<uint32_t *>(IOMallocZero(0x4000));
    if(!s.itcm_shadow)return refuse(kIOReturnNoMemory);
    for(unsigned i=0;i<0x1000;++i) {
        if(s.failed())return refuse(kIOReturnNotReady);
        uint32_t actual=0;s.gmu_load_last_returned=false;
        s.gmu_load_last_raw=s.register_maps->accessGmuTcmWord(0x1b400u+i,false,actual);
        s.gmu_load_last_returned=true;
        if(s.gmu_load_last_raw)return refuse(kIOReturnIOError);
        s.itcm_shadow[i]=actual;++s.itcm_shadow_words;
    }
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    // Source load/shadow (plus direct-only earlier version read). No SYSRESET write, firmware auth claim,
    // GMU/CM3 init bits, HFI/ACK, normal release, retry or recovery is produced.
    s.gmu_load_ready=true;return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::configureGmuRegisters(ZornGen7GmuIrq26 &irq,uint32_t revision,
    ZornGen7RegisterConfig::KnownState bcl)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_load_ready ||
       !s.gmu_activation_ready || !s.firmware_holds_ready || !s.boot_buffers_ready || (!s.boot_buffers && !s.hwsched_buffers) ||
       !s.global_fault_owner || !s.global_fault_owner->ready() || !e.fault_owner || !e.fault_owner->ready() ||
       !e.stream_owner || !e.image_ready || e.state.poisoned || s.gmu_config_attempted || irq.halted())
        return kIOReturnNotReady;
    s.gmu_config_attempted=true;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    // Match canonical actual objects without assuming sorted array positions.
    // No zero tail in the maximum-capacity array is treated as a real range.
    ZornSmmuSparse4KRange actual[7]{};size_t count=0;
    if(s.hwsched_buffers) {
        if(!s.hwsched_buffers->copyPreparedRanges(actual))return refuse(kIOReturnNotReady);count=7;
    }else{
        ZornSmmuSparse4KRange direct[2]{};
        if(!s.boot_buffers->copyPreparedRanges(direct))return refuse(kIOReturnNotReady);
        for(size_t i=0;i<2;++i)actual[i]=direct[i];count=2;
    }
    for(size_t i=0;i<count;++i) {
        const auto &buffer=actual[i];unsigned matches=0;
        for(size_t j=0;j<s.initial_range_count;++j) {
            const auto &range=s.initial_ranges[j];
            if(buffer.iova==range.iova && buffer.physical==range.physical && buffer.bytes==range.bytes &&
               buffer.permissions==range.permissions && buffer.writeback==range.writeback &&
               buffer.shareability==range.shareability)++matches;
        }
        if(matches!=1)return refuse(kIOReturnNotReady);
    }
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    const auto raw=s.hwsched_buffers?s.hwsched_buffers->configureCold(irq,revision,bcl):s.boot_buffers->configureCold(irq,revision,bcl);
    if(raw!=kIOReturnSuccess || s.failed() || irq.halted())return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.gmu_config_ready=true;return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::prepareDirectHfi(ZornGen7GmuIrq26 &irq,IOWorkLoop &loop,
    ZornGen7DirectHfi26 *&out)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || out)return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_config_ready || !s.boot_buffers_ready ||
       !s.boot_buffers || !s.register_maps || irq.halted())return kIOReturnNotReady;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    const auto raw=s.boot_buffers->prepareReceiver(*this,irq,*s.register_maps,loop,out);
    if(raw!=kIOReturnSuccess || s.failed() || irq.halted())return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::prepareHwschedHfi(ZornGen7GmuIrq26 &irq,IOWorkLoop &loop,
    ZornGen7HwschedHfi26 *&out)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || out)return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_config_ready || !s.gmu_versions_ready || !s.boot_buffers_ready ||
       !s.hwsched_buffers || s.boot_buffers || s.initial_range_count!=12 || !s.register_maps || irq.halted())return kIOReturnNotReady;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    const auto raw=ZornGen7HwschedHfi26::createPrepared(*s.hwsched_buffers,s.gate,*this,irq,*s.register_maps,loop,out);
    if(raw!=kIOReturnSuccess || !out || out->halted() || s.failed() || irq.halted())return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    return kIOReturnSuccess; // Bound real masked transport,not protocol or hardware success.
}

IOReturn ZornGen7SmmuDomain26::readActualGmuVersions()
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;if(s.failed() || !s.register_maps || s.gmu_versions_attempted)return kIOReturnNotReady;
    s.gmu_versions_attempted=true;auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    for(unsigned i=0;i<5;++i) {
        if(s.failed())return refuse(kIOReturnNotReady);
        uint32_t actual=0;s.gmu_load_last_returned=false;
        s.gmu_load_last_raw=s.register_maps->accessGmuTcmWord(0x1c400u+0xff8u+i,false,actual);
        s.gmu_load_last_returned=true;
        if(s.gmu_load_last_raw)return refuse(kIOReturnIOError);
        s.versions[i]=actual;++s.version_words_returned;
    }
    if(s.versions[0]<s.minimum_core_version)return refuse(kIOReturnUnsupported);
    s.gmu_versions_ready=true;return kIOReturnSuccess;
}
IOReturn ZornGen7SmmuDomain26::readHwschedGmuVersions(ZornGen7GmuIrq26 &irq,uint32_t (&actualOutput)[5])
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_config_ready || !s.gmu_load_ready ||
       !s.hwsched_buffers || s.boot_buffers || !s.gmu_activation_ready || !s.register_maps || irq.halted() ||
       s.gmu_versions_attempted)return kIOReturnNotReady;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    const auto raw=readActualGmuVersions();if(raw!=kIOReturnSuccess)return raw;
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed() || irq.halted())return refuse(kIOReturnNotReady);
    for(unsigned i=0;i<5;++i)actualOutput[i]=s.versions[i];
    return kIOReturnSuccess; // Actual five returned reads,not a firmware image-derived version.
}

IOReturn ZornGen7SmmuDomain26::prepareHostHfi(ZornGen7GmuIrq26 &irq,IOWorkLoop &loop,
    ZornGen7HwschedHfi26 *&out)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || out)return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_config_ready || !s.gmu_versions_ready || !s.boot_buffers_ready ||
       !s.hwsched_buffers || s.boot_buffers || s.initial_range_count!=12 || !s.register_maps || irq.halted())return kIOReturnNotReady;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    const auto raw=ZornGen7HwschedHfi26::createHostPrepared(*s.hwsched_buffers,s.gate,*this,irq,*s.register_maps,loop,out);
    if(raw!=kIOReturnSuccess || !out || out->halted() || s.failed() || irq.halted())return refuse(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    return kIOReturnSuccess; // Bound real masked transport,not protocol or hardware success.
}

IOReturn ZornGen7SmmuDomain26::readHostGmuVersions(ZornGen7GmuIrq26 &irq,uint32_t (&actualOutput)[5])
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;auto &e=s.endpoints[2];
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_config_ready || !s.gmu_load_ready ||
       !s.hwsched_buffers || s.boot_buffers || !s.gmu_activation_ready || !s.register_maps || irq.halted() ||
       s.gmu_versions_attempted)return kIOReturnNotReady;
    auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())return refuse(kIOReturnNotReady);
    e.sparse_status=ZornSmmuSparse4KLiveAudit(&e.arena,&e.state,s.initial_ranges,s.initial_range_count,&e.audit);
    if(e.sparse_status!=ZornSmmuSparse4KSuccess || !e.audit.complete)return refuse(kIOReturnIOError);
    const auto raw=readActualGmuVersions();if(raw!=kIOReturnSuccess)return raw;
    if(s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed() || irq.halted())return refuse(kIOReturnNotReady);
    for(unsigned i=0;i<5;++i)actualOutput[i]=s.versions[i];
    return kIOReturnSuccess; // Actual five returned reads,not a firmware image-derived version.
}

IOReturn ZornGen7SmmuDomain26::prepareHostGpuTables(FhgStorage &graph,HoujiFullHostNativeMemory &memory,OSObject &parent)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;
    if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_activation_ready || !s.sparse_ready ||
       (!s.context_views_ready && !(s.native_controller_mode && s.context_probe_verified &&
           s.gmu_cold_readback && s.nativeControllerClaimHeld())) ||
       s.firmware_memory!=&memory || s.firmware_owner!=&parent || s.host_gpu_tables_attempted)return kIOReturnNotReady;
    for(unsigned i=0;i<2;++i){const auto &e=s.endpoints[i];
        if(!e.reservation.acquired || !e.atomic_owner || !e.tables || !e.state.prepared || e.state.poisoned || e.state.context_offset || e.image_ready || e.stream_owner)return kIOReturnNotReady;}
    s.host_gpu_tables_attempted=true;
    const auto raw=ZornGen7HostGpuTables26::create(s.gate,*this,graph,memory,parent,s.s1_input_bits,
        s.s1_output_bits,s.physical_output_bits,s.host_gpu_tables);
    if(raw!=kIOReturnSuccess || s.failed() || !s.host_gpu_tables || !s.host_gpu_tables->prepared()){
        s.stopped=true;return raw==kIOReturnSuccess?kIOReturnNotReady:raw;}
    s.host_gpu_tables_ready=true;return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::verifyHostGpuMmuStartAuthorization(IOService &controller,
    IOService &user,IOService &lpac,const uint16_t (&banks)[2],const uint16_t (&asids)[2],
    const uint32_t (&prrBefore)[2],IOMemoryDescriptor &zero,uint64_t zeroPhysical)
{
    if(!storage_ || !normal() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(&s.gate);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(&s.gate);return raw;};
    if(!s.ready || s.failed() || s.busy || !s.host_gpu_mmu_attempted || s.host_gpu_mmu_ready ||
       s.host_gpu_mmu_grant_returned || !s.host_gpu_tables_ready || !s.host_gpu_tables ||
       !s.global_fault_ready || !s.global_fault_owner || !s.global_atomic_owner ||
       !s.host_zero || s.host_zero->descriptor()!=&zero || s.host_zero_physical!=zeroPhysical ||
       &controller!=&s.controller || !s.endpoints[0].consumer || !s.endpoints[1].consumer ||
       &user!=s.endpoints[0].consumer || &lpac!=s.endpoints[1].consumer ||
       !s.endpoints[2].stream_owner || !s.endpoints[2].fault_owner ||
       s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       s.endpoints[2].fault_owner->verifyNoFault()!=kIOReturnSuccess ||
       s.endpoints[2].stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())
        return finish(kIOReturnNotReady);
    for(unsigned i=0;i<2;++i){
        const auto &e=s.endpoints[i];
        if(!e.reservation.acquired || !e.atomic_owner || !e.program_route.io_.cookie ||
           e.stream_owner || e.fault_owner || e.reservation.bank!=s.host_banks[i] ||
           e.reservation.asid!=s.host_asids[i] || banks[i]!=s.host_banks[i] ||
           asids[i]!=s.host_asids[i] || prrBefore[i]!=s.prr_before[i] ||
           e.reservation.bank==s.endpoints[2].reservation.bank)
            return finish(kIOReturnNotReady);
    }
    return finish(kIOReturnSuccess);
}

IOReturn ZornGen7SmmuDomain26::verifyHostGpuPostCpRestoreAuthorization(IOService &controller,
    IOService &user,uint16_t bank,uint16_t asid,uint32_t expectedTcr,uint32_t actualTcr)
{
    if(!storage_ || !normal() || ml_at_interrupt_context() || !ml_get_interrupts_enabled() ||
       IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(&s.gate);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(&s.gate);return raw;};
    if(!s.ready || s.failed() || s.busy || !s.host_gpu_mmu_attempted || !s.host_gpu_mmu_ready ||
       (!s.host_gpu_mmu_grant_returned && !(s.native_controller_mode && s.native_host_runtime_ready && s.host_post_cp_access && s.nativeControllerClaimHeld())) || !s.post_cp_context_attempted || !s.post_cp_restore_needed ||
       s.post_cp_context_ready || s.post_cp_grant_returned || &controller!=&s.controller ||
       !s.endpoints[0].consumer || &user!=s.endpoints[0].consumer ||
       bank!=s.host_banks[0] || asid!=s.host_asids[0] ||
       expectedTcr!=s.post_cp_expected_tcr || actualTcr!=s.post_cp_observed_tcr ||
       expectedTcr==actualTcr || !s.global_fault_owner ||
       s.global_fault_owner->verifyNoFault()!=kIOReturnSuccess || s.failed())
        return finish(kIOReturnNotReady);
    for(unsigned i=0;i<2;++i){s.selectNativeHostPostCpBank(i);
        const auto &e=s.endpoints[i];
        if(!e.fault_owner || !e.stream_owner || e.fault_owner->verifyNoFault()!=kIOReturnSuccess ||
           e.stream_owner->verifyActive()!=kIOReturnSuccess || s.failed())
            return finish(kIOReturnNotReady);
    }
    return finish(kIOReturnSuccess);
}

IOReturn ZornGen7SmmuDomain26::startHostGpuMmu(NativeAdrenoMemory &zero,OSObject &parent,OSObject &owner,OSObject &irqStreamOwner,
    ZornGen7IccInputs26 &tbuPower,const ZornGen7GpuMmuAuthority26 &authority,
    const ZornGen7SmmuFaultIrqAuthority26 &faults,const ZornGen7SmmuStreamAuthority26 &streams,unsigned budget)
{
    if(!storage_ || !normal() || !ml_get_interrupts_enabled() || !IORecursiveLockHaveLock(&storage_->gate) ||
       !budget || budget>1048576 || !authority.acquireExclusiveGpuMmuStart || !authority.authorizePostCpUserRestore)return kIOReturnNotReady;
    auto &s=*storage_;if(!s.ready || s.failed() || s.busy || !s.power || !s.gmu_activation_ready || !s.register_maps ||
       !s.host_gpu_tables_ready || !s.host_gpu_tables || !s.host_gpu_tables->prepared() ||
       !s.global_fault_ready || !s.global_fault_owner || !s.global_atomic_owner || !s.native_root ||
       s.firmware_owner!=&parent || s.host_gpu_mmu_attempted)return kIOReturnNotReady;
    s.host_gpu_mmu_attempted=true;s.host_gpu_mmu_poll_budget=budget;auto refuse=[&](IOReturn raw){s.stopped=true;return raw;};
    const auto &io=s.global_atomic_io;
    if(!io.cookie || !io.read32 || !io.write32 || !io.barrier || io.register_bytes<0x6010)return refuse(kIOReturnNotReady);
    auto raw=s.prepareHostContextImages();
    if(raw)return refuse(raw);
    raw=s.prepareHostPrrZero(zero);
    if(raw)return refuse(raw);
    for(unsigned i=0;i<2;++i){s.prr_read_raw[i]=io.read32(io.cookie,0x6008+4u*i,&s.prr_before[i]);if(s.prr_read_raw[i])return refuse(kIOReturnIOError);}
    owner.retain();s.host_gpu_mmu_owner=&owner;s.host_gpu_mmu_authority=authority;irqStreamOwner.retain();
    // Board has latched StoppedRetained and parent has latched its attempt.
    // Foreign whole-window acquisition is outside startup/access gates;IRQ
    // containment remains possible. No CPU lock is treated as a hardware grant.
    IORecursiveLockUnlock(&s.gate);
    s.host_gpu_mmu_grant_raw=s.host_gpu_mmu_authority.acquireExclusiveGpuMmuStart(s.host_gpu_mmu_authority.cookie,
        s.controller,*s.endpoints[0].consumer,*s.endpoints[1].consumer,s.host_banks,s.host_asids,s.prr_before,
        *zero.descriptor(),s.host_zero_physical);
    IORecursiveLockLock(&s.gate);s.host_gpu_mmu_grant_returned=true;
    if(s.host_gpu_mmu_grant_raw || s.failed())return refuse(kIOReturnNotPermitted);
    for(unsigned i=0;i<2;++i){s.prr_read_raw[i]=io.read32(io.cookie,0x6008+4u*i,&s.prr_after[i]);
        if(s.prr_read_raw[i] || s.prr_after[i]!=s.prr_before[i])return refuse(kIOReturnNotReady);}
    // Whole-GPU MMU-start authority is necessary, but a TBU ACK is only a
    // transport fence. Also wait for real GMU idle and both ordered GBIF halt
    // acknowledgements before touching host GPU contexts or stream entries.
    raw=s.register_maps->haltGpuBusForSmmuTableUpdate();
    if(raw || s.failed())return refuse(raw?raw:kIOReturnNotReady);
    raw=s.haltHostQtb(owner,tbuPower,budget);
    if(raw)return refuse(raw);
    raw=s.publishHostPrrZero();
    if(raw)return refuse(raw);
    for(unsigned i=0;i<2;++i){auto &e=s.endpoints[i];
        raw=ZornGen7SmmuFaultIrq26::createAndArm(s.controller,*e.consumer,ZornGen7SmmuFaultIrq26::Scope::Context,
            e.reservation.bank,s.banks,e.atomic_io,*e.atomic_owner,irqStreamOwner,faults,*this,stopForContextFault,this,e.fault_owner);
        if(raw || s.failed() || !e.fault_owner || !e.fault_owner->ready())return refuse(raw?raw:kIOReturnNotReady);
        const uint32_t others[]={s.endpoints[1-i].packed,s.endpoints[2].packed};
        raw=ZornGen7SmmuStream26::prepareBlocked(s.controller,*e.consumer,e.reservation.bank,s.id0,e.packed,
            others,2,s.stream_slots,io,*s.global_atomic_owner,irqStreamOwner,streams,*this,s.irq_faulted,e.stream_owner);
        if(raw || s.failed() || !e.stream_owner || !e.stream_owner->ready())return refuse(raw?raw:kIOReturnNotReady);
        raw=e.stream_owner->applyActlrToDisabledBank(e.atomic_io,e.program_route.io_,e.reservation.context_offset,e.reservation.asid,budget);
        if(raw || s.failed())return refuse(raw?raw:kIOReturnNotReady);
    }
    // Actual qcom,qsmmu-v500 source excludes the older hazard/DORA writes.
    // Global PRR is published once for both contexts,under its distinct grant.
    s.prr_expected[0]=uint32_t(s.host_zero_physical);s.prr_expected[1]=uint32_t(s.host_zero_physical>>32);
    if(s.global_fault_owner->verifyNoFault() || s.failed())return refuse(kIOReturnNotReady);
    for(unsigned i=0;i<2;++i){if(s.failed())return refuse(kIOReturnNotReady);s.prr_write_raw[i]=io.write32(io.cookie,0x6008+4u*i,s.prr_expected[i]);if(s.prr_write_raw[i])return refuse(kIOReturnIOError);}
    s.prr_barrier_raw=io.barrier(io.cookie);if(s.prr_barrier_raw)return refuse(kIOReturnIOError);
    auto verifyPrr=[&](){for(unsigned i=0;i<2;++i){s.prr_read_raw[i]=io.read32(io.cookie,0x6008+4u*i,&s.prr_after[i]);
        if(s.prr_read_raw[i] || s.prr_after[i]!=s.prr_expected[i])return false;}return !s.failed();};
    if(!verifyPrr())return refuse(kIOReturnNotReady);
    for(unsigned i=0;i<2;++i){auto &e=s.endpoints[i];const auto &c=e.atomic_io;
        if(s.failed())return refuse(kIOReturnNotReady);
        s.host_actlr_read_raw[i]=c.read32(c.cookie,4,&s.host_actlr_before[i]);
        if(s.host_actlr_read_raw[i] || s.failed())return refuse(kIOReturnIOError);
        s.host_actlr_write_raw[i]=c.write32(c.cookie,4,s.host_actlr_before[i]|(1u<<5));
        if(s.host_actlr_write_raw[i] || s.failed())return refuse(kIOReturnIOError);
        s.host_actlr_barrier_raw[i]=c.barrier(c.cookie);
        if(s.host_actlr_barrier_raw[i] || s.failed())return refuse(kIOReturnIOError);
        s.host_actlr_read_raw[i]=c.read32(c.cookie,4,&s.host_actlr_after[i]);
        if(s.host_actlr_read_raw[i] || s.host_actlr_after[i]!=(s.host_actlr_before[i]|(1u<<5)) || s.failed())return refuse(kIOReturnIOError);
        if(e.fault_owner->verifyNoFault() || e.stream_owner->verifyBlocked() || s.failed())return refuse(kIOReturnNotReady);
        raw=s.host_gpu_tables->programContext(i,e.program_route.io_,e.reservation.bank,e.reservation.context_offset,budget);
        if(raw || s.failed())return refuse(raw?raw:kIOReturnNotReady);
    }
    for(unsigned i=0;i<2;++i){auto &e=s.endpoints[i];
        raw=s.host_gpu_tables->verifyContext(i,e.program_route.io_,e.reservation.bank,e.reservation.context_offset);
        if(raw || !verifyPrr() || s.global_fault_owner->verifyNoFault() || e.fault_owner->verifyNoFault() || e.stream_owner->verifyBlocked() || s.failed())return refuse(raw?raw:kIOReturnNotReady);
        raw=e.stream_owner->activatePreparedWithPeer(s.endpoints[1-i].stream_owner);
        if(raw || s.failed())return refuse(raw?raw:kIOReturnNotReady);
        raw=s.host_gpu_tables->verifyContext(i,e.program_route.io_,e.reservation.bank,e.reservation.context_offset);
        if(raw || e.stream_owner->verifyActive() || s.global_fault_owner->verifyNoFault() || e.fault_owner->verifyNoFault() || !verifyPrr() || s.failed())return refuse(raw?raw:kIOReturnNotReady);
    }
    // Re-observe BOTH contexts/streams/ACTLRs after the second activation.
    // This is still only a bounded actual snapshot,not a GPU completion.
    for(unsigned i=0;i<2;++i){auto &e=s.endpoints[i];const auto &c=e.atomic_io;
        raw=s.host_gpu_tables->verifyContext(i,e.program_route.io_,e.reservation.bank,e.reservation.context_offset);
        if(raw || s.failed())return refuse(raw?raw:kIOReturnNotReady);
        s.host_actlr_read_raw[i]=c.read32(c.cookie,4,&s.host_actlr_after[i]);
        if(s.host_actlr_read_raw[i] || s.host_actlr_after[i]!=(s.host_actlr_before[i]|(1u<<5)) ||
           e.stream_owner->verifyActive() || e.fault_owner->verifyNoFault() || s.failed())return refuse(kIOReturnNotReady);
    }
    if(!verifyPrr() || s.global_fault_owner->verifyNoFault() || zero.deviceReferences()!=1 || s.failed())return refuse(kIOReturnNotReady);
    for(unsigned i=0;i<2;++i){auto &e=s.endpoints[i];
        if(!e.stream_owner || !e.fault_owner || e.stream_owner->verifyActive() || e.fault_owner->verifyNoFault() || s.failed())
            return refuse(kIOReturnNotReady);
        raw=s.host_gpu_tables->verifyContext(i,e.program_route.io_,e.reservation.bank,e.reservation.context_offset);
        if(raw || s.failed())return refuse(raw?raw:kIOReturnNotReady);
    }
    raw=s.resumeHostQtb();
    if(raw)return refuse(raw);
    raw=s.register_maps->releaseGpuBusAfterSmmuTableUpdate();
    if(raw || s.failed())return refuse(raw?raw:kIOReturnNotReady);
    s.host_gpu_qtb_released=true;s.host_gpu_mmu_ready=true;return kIOReturnSuccess;
    // No GMU bank/global reset,secure domain creation,release or retry. Real
    // success remains conditional on actual grants/IO;this source is unexecuted.
}

IOReturn ZornGen7SmmuDomain26::bindNativePostCpAuthority(OSObject &owner,const ZornGen7GpuMmuAuthority26 &authority)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;auto &s=*storage_;
    if(!s.native_controller_mode || !s.native_host_runtime_ready || !s.host_gpu_mmu_ready || !s.nativeControllerClaimHeld() ||
       s.failed() || s.host_gpu_mmu_owner || !authority.authorizePostCpUserRestore || authority.acquireExclusiveGpuMmuStart)return kIOReturnNotReady;
    owner.retain();s.host_gpu_mmu_owner=&owner;s.host_gpu_mmu_authority=authority;return kIOReturnSuccess;
}

IOReturn ZornGen7SmmuDomain26::buildHostFirstContext(ZornGen7HostRing26 &ring,uint32_t (&words)[25])
{
    if(!storage_ || !normal() || !ring.modeExitIdleForDomain(*this))return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;IORecursiveLockLock(&s.gate);
    if(!s.beginNativeHostPostCpWindow()){IORecursiveLockUnlock(&s.gate);return kIOReturnNotReady;}
    auto finish=[&](IOReturn raw){s.endNativeHostPostCpWindow();IORecursiveLockUnlock(&s.gate);return raw;};
    if(s.failed() || !s.host_gpu_mmu_ready || !s.host_gpu_tables_ready || !s.host_gpu_tables ||
       !s.global_fault_owner || s.global_fault_owner->verifyNoFault())return finish(kIOReturnNotReady);
    for(unsigned i=0;i<2;++i){s.selectNativeHostPostCpBank(i);auto &e=s.endpoints[i];
        if(!e.fault_owner || !e.stream_owner || e.fault_owner->verifyNoFault() || e.stream_owner->verifyActive() || s.failed())return finish(kIOReturnNotReady);
        const auto raw=s.host_gpu_tables->verifyContext(i,e.program_route.io_,e.reservation.bank,e.reservation.context_offset);
        if(raw || s.failed())return finish(raw?raw:kIOReturnNotReady);
    }
    return finish(s.host_gpu_tables->buildFirstContextWords(words));
    // Only actual root/ASID privately consumed in original packet producer.
    // No public root/address getter or new mapping/owner/stop authorization.
}

IOReturn ZornGen7SmmuDomain26::restoreHostPostCpContext(ZornGen7HostRing26 &ring)
{
    if(!storage_ || !normal() || !ring.contextIdleForDomain(*this))return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;IORecursiveLockLock(&s.gate);
    if(!s.beginNativeHostPostCpWindow()){IORecursiveLockUnlock(&s.gate);return kIOReturnNotReady;}
    auto finish=[&](IOReturn raw){if(raw)s.stopped=true;s.endNativeHostPostCpWindow();IORecursiveLockUnlock(&s.gate);return raw;};
    if(s.failed() || !s.host_gpu_mmu_ready || !s.host_gpu_tables || s.post_cp_context_attempted || !s.global_fault_owner ||
       s.global_fault_owner->verifyNoFault())return finish(kIOReturnNotReady);
    s.post_cp_context_attempted=true;auto &e=s.endpoints[0];
    for(unsigned i=0;i<2;++i){s.selectNativeHostPostCpBank(i);if(!s.endpoints[i].fault_owner || !s.endpoints[i].stream_owner ||
        s.endpoints[i].fault_owner->verifyNoFault() || s.endpoints[i].stream_owner->verifyActive())return finish(kIOReturnNotReady);}
    s.selectNativeHostPostCpBank(0);
    auto raw=s.host_gpu_tables->inspectPostCpContext(e.program_route.io_,e.reservation.bank,e.reservation.context_offset,
        s.post_cp_restore_needed,s.post_cp_expected_tcr,s.post_cp_observed_tcr);
    if(raw || s.failed())return finish(raw?raw:kIOReturnNotReady);
    if(s.post_cp_restore_needed){
        if(!s.host_gpu_mmu_authority.authorizePostCpUserRestore)return finish(kIOReturnNotReady);
        IORecursiveLockUnlock(&s.gate);
        s.post_cp_grant_raw=s.host_gpu_mmu_authority.authorizePostCpUserRestore(s.host_gpu_mmu_authority.cookie,
            s.controller,*e.consumer,e.reservation.bank,e.reservation.asid,s.post_cp_expected_tcr,s.post_cp_observed_tcr);
        IORecursiveLockLock(&s.gate);s.post_cp_grant_returned=true;
        if(s.post_cp_grant_raw || s.failed() || !ring.contextIdleForDomain(*this))return finish(kIOReturnNotPermitted);
        s.selectNativeHostPostCpBank(0);
        raw=s.host_gpu_tables->restorePostCpContext(e.program_route.io_,e.reservation.bank,e.reservation.context_offset,s.host_gpu_mmu_poll_budget);
        if(raw || s.failed())return finish(raw?raw:kIOReturnNotReady);
    }
    for(unsigned i=0;i<2;++i){s.selectNativeHostPostCpBank(i);auto &q=s.endpoints[i];
        raw=s.host_gpu_tables->verifyContext(i,q.program_route.io_,q.reservation.bank,q.reservation.context_offset);
        if(raw || s.failed() || q.fault_owner->verifyNoFault() || q.stream_owner->verifyActive())return finish(raw?raw:kIOReturnNotReady);}
    if(s.global_fault_owner->verifyNoFault() || !ring.contextIdleForDomain(*this))return finish(kIOReturnNotReady);
    s.post_cp_context_ready=true;return finish(kIOReturnSuccess);
}
IOReturn ZornGen7SmmuDomain26::verifyHostRuntimeContexts()
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return kIOReturnNotReady;IORecursiveLockLock(&s.gate);
    if(!s.beginNativeHostPostCpWindow()){IORecursiveLockUnlock(&s.gate);return kIOReturnNotReady;}
    auto finish=[&](IOReturn raw){if(raw)s.stopped=true;s.endNativeHostPostCpWindow();IORecursiveLockUnlock(&s.gate);return raw;};
    if(s.failed() || !s.post_cp_context_ready || !s.host_gpu_mmu_ready || !s.host_gpu_tables ||
       !s.global_fault_owner || s.global_fault_owner->verifyNoFault())return finish(kIOReturnNotReady);
    for(unsigned i=0;i<2;++i){s.selectNativeHostPostCpBank(i);auto &e=s.endpoints[i];
        if(!e.fault_owner || !e.stream_owner || e.fault_owner->verifyNoFault() || e.stream_owner->verifyActive())return finish(kIOReturnNotReady);
        const auto raw=s.host_gpu_tables->verifyContext(i,e.program_route.io_,e.reservation.bank,e.reservation.context_offset);
        if(raw || s.failed())return finish(raw?raw:kIOReturnNotReady);}
    return finish(kIOReturnSuccess);
}

IOReturn ZornGen7SmmuDomain26::attachHostDirectRuntime(ZornGen7HostRing26 &boot,ZornGen7DirectVm26 &vm,
    ZornGen7DirectSubmit26 &submit,NativeAdrenoRing &ring,OSObject &owner,
    const ZornGen7DirectRuntimeAuthority26 &authority,size_t capacity,ZornGen7PresentProgress26 &present)
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate) || !authority.acquireNativeRuntime ||
       !boot.completedBootstrapForDomain(*this))return kIOReturnNotReady;auto &s=*storage_;
    if(s.failed() || !s.post_cp_context_ready || !s.host_gpu_mmu_ready || !s.host_gpu_tables ||
       !s.register_maps || s.runtime_attempted)return kIOReturnNotReady;
    if(!s.beginNativeHostPostCpWindow())return kIOReturnNotReady;
    s.host_runtime_observation=s.native_controller_mode;
    auto finish=[&](IOReturn raw){
        const auto bus=s.register_maps->readGpuBusStopResult();
        zornRuntimeObservation[0]=unsigned(raw);
        zornRuntimeObservation[2]=(s.runtime_attempted?1u:0u)|(s.runtime_attach_quiesced?2u:0u)|
            (s.runtime_grant_returned?4u:0u)|(s.runtime_active?8u:0u)|(s.runtime_ready?16u:0u)|(s.runtime_attach_metadata_only?32u:0u);
        zornRuntimeObservation[3]=unsigned(s.runtime_grant_raw);zornRuntimeObservation[4]=unsigned(bus.phase);
        zornRuntimeObservation[8]=vm.poisoned();zornRuntimeObservation[9]=submit.poisoned();
        zornRuntimeObservation[10]=unsigned(s.runtime_route_raw);zornRuntimeObservation[11]=unsigned(capacity);
        const auto access=s.register_maps->readResult();
        zornRuntimeObservation[12]=bus.idlePolls;zornRuntimeObservation[13]=unsigned(bus.idleReadRaw);
        zornRuntimeObservation[14]=bus.busyStatus;zornRuntimeObservation[15]=unsigned(bus.clientHaltWriteRaw);
        zornRuntimeObservation[16]=unsigned(bus.clientAckReadRaw);zornRuntimeObservation[17]=bus.clientAck;
        zornRuntimeObservation[18]=unsigned(bus.arbHaltWriteRaw);zornRuntimeObservation[19]=unsigned(bus.arbAckReadRaw);
        zornRuntimeObservation[20]=bus.arbAck;zornRuntimeObservation[21]=unsigned(access.lastAccessGuardStatus);
        zornRuntimeObservation[22]=unsigned(access.lastAccessObserverStatus);
        zornRuntimeObservation[23]=(access.lastAccessGuardReturned?1u:0u)|(access.lastAccessPrimitiveReturned?2u:0u)|
            (access.lastAccessObserverReturned?4u:0u)|(bus.clientHaltWriteReturned?8u:0u)|
            (bus.arbHaltWriteReturned?16u:0u)|(bus.releaseWriteReturned?32u:0u);
        s.host_runtime_observation=false;s.endNativeHostPostCpWindow();return raw;
    };
    zornRuntimeObservation[1]=1;
    s.runtime_attempted=true;owner.retain();s.runtime_owner=&owner;s.runtime_authority=authority;
    boot.retain();s.runtime_boot=&boot;
    // Native attachSeeded and Submit::attach only allocate/adopt CPU metadata
    // and audit the already live boot mappings. This window forbids register
    // writes and no normal producer has been published. It is NOT a DMA-stop
    // claim. The completed real bootstrap is checked before and after callout.
    // Actual map/unmap still requires haltDirectRuntime/releaseDirectRuntime.
    if(s.native_controller_mode)s.runtime_attach_metadata_only=true;
    else {
        const auto haltRaw=s.register_maps->haltGpuBusForSmmuTableUpdate();
        zornRuntimeObservation[5]=unsigned(haltRaw);
        if(haltRaw){s.stopped=true;return finish(haltRaw);}
        s.runtime_attach_quiesced=true;
    }
    zornRuntimeObservation[1]=2;
    IORecursiveLockUnlock(&s.gate);
    s.runtime_grant_raw=s.runtime_authority.acquireNativeRuntime(s.runtime_authority.cookie,s.controller,*s.endpoints[0].consumer,*s.endpoints[1].consumer,boot);
    IORecursiveLockLock(&s.gate);s.runtime_grant_returned=true;
    if(s.runtime_grant_raw || s.failed() || !boot.completedBootstrapForDomain(*this)){
        s.stopped=true;return finish(kIOReturnNotPermitted);
    }
    zornRuntimeObservation[1]=3;
    s.runtime_active=true;s.runtime_routes={this,s.endpoints[0].reservation.bank,observeDirectRuntime,faultDirectRuntime,
        haltDirectRuntime,releaseDirectRuntime,beginDirectSubmission,endDirectSubmission};
    auto &e=s.endpoints[0];
    auto raw=s.host_gpu_tables->attachDirectVm(vm,e.program_route.io_,s.runtime_routes,capacity,s.host_gpu_mmu_poll_budget);
    if(!raw)raw=submit.attach(&vm,&ring,&present);
    s.runtime_active=false;
    zornRuntimeObservation[6]=unsigned(raw);
    if(raw){s.stopped=true;return finish(raw);}
    zornRuntimeObservation[1]=4;
    if(s.runtime_attach_quiesced){
        const auto releaseRaw=s.register_maps->releaseGpuBusAfterSmmuTableUpdate();
        zornRuntimeObservation[7]=unsigned(releaseRaw);
        if(releaseRaw){s.stopped=true;return finish(releaseRaw);}
        s.runtime_attach_quiesced=false;
    }
    s.runtime_ready=true;zornRuntimeObservation[1]=5;return finish(kIOReturnSuccess);
    // Real metadata attachment only. No normal submission,client publication,
    // BO mapping or speculative callback result is executed by construction.
}
bool ZornGen7SmmuDomain26::runtimeEndpointBindingsMatch(IOService &controller,IOService &user,IOService &lpac) const
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return false;const auto &s=*storage_;
    return s.runtime_attempted && (s.runtime_attach_quiesced ||
        (s.native_controller_mode && s.runtime_attach_metadata_only && s.host_runtime_observation &&
         s.host_post_cp_access && s.native_host_runtime_ready)) && !s.runtime_grant_returned &&
        !s.runtime_active && !s.runtime_ready && s.host_gpu_mmu_ready && s.post_cp_context_ready &&
        s.host_gpu_tables && s.register_maps && &s.controller==&controller &&
        s.endpoints[0].consumer==&user && s.endpoints[1].consumer==&lpac &&
        !s.failed() && s.global_fault_owner && s.endpoints[0].fault_owner &&
        s.endpoints[1].fault_owner && s.endpoints[0].stream_owner && s.endpoints[1].stream_owner;
}
ZornSmmuSparse4KStatus ZornGen7SmmuDomain26::observeDirectRuntime(void *context,bool full)
{
    auto *o=static_cast<ZornGen7SmmuDomain26 *>(context);if(!o || !o->storage_ || !normal())return ZornSmmuSparse4KArgument;auto &s=*o->storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || s.failed() || (!s.runtime_active && !s.runtime_ready) ||
       !s.runtime_grant_returned || s.runtime_grant_raw || !s.global_fault_owner || s.global_fault_owner->verifyNoFault())return ZornSmmuSparse4KIoError;
    const bool open=s.native_controller_mode && !s.host_post_cp_access;
    if(open && !s.beginNativeHostPostCpWindow())return ZornSmmuSparse4KIoError;
    if(s.native_controller_mode && (__atomic_load_n(&s.host_context_thread,__ATOMIC_ACQUIRE)!=current_thread() ||
       !s.host_runtime_observation && !open &&
       !(s.host_runtime_mutation && s.runtime_mapping_halted && s.runtime_transaction_thread==current_thread())))return ZornSmmuSparse4KIoError;
    const bool wasObservation=s.host_runtime_observation;
    if(s.native_controller_mode)s.host_runtime_observation=true;
    auto finish=[&](ZornSmmuSparse4KStatus raw){
        s.host_runtime_observation=wasObservation;
        if(open)s.endNativeHostPostCpWindow();return raw;
    };
    auto &e=s.endpoints[0];s.selectNativeHostPostCpBank(0);
    s.runtime_route_raw=full?e.stream_owner->verifyActiveConflicts():e.stream_owner->verifyActive();
    if(s.runtime_route_raw || e.fault_owner->verifyNoFault() || s.endpoints[1].fault_owner->verifyNoFault() || s.failed())return finish(ZornSmmuSparse4KIoError);
    s.selectNativeHostPostCpBank(1);s.runtime_route_raw=s.endpoints[1].stream_owner->verifyActive();
    if(s.runtime_route_raw || s.failed())return finish(ZornSmmuSparse4KIoError);
    s.selectNativeHostPostCpBank(0);s.runtime_route_raw=s.host_gpu_tables->observeRuntimeUser(e.program_route.io_,e.reservation.bank,e.reservation.context_offset);
    return finish(s.runtime_route_raw?ZornSmmuSparse4KStateMismatch:ZornSmmuSparse4KSuccess);
}

ZornSmmuSparse4KStatus ZornGen7SmmuDomain26::faultDirectRuntime(void *context)
{
    auto *o=static_cast<ZornGen7SmmuDomain26 *>(context);if(!o || !o->storage_ || !normal())return ZornSmmuSparse4KArgument;auto &s=*o->storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || !s.runtime_grant_returned || s.runtime_grant_raw ||
       (!s.runtime_active && !s.runtime_ready) || !s.endpoints[0].stream_owner)return ZornSmmuSparse4KArgument;
    if(s.native_controller_mode){
        s.host_runtime_mutation=false;s.runtime_transaction_thread=THREAD_NULL;
        s.runtime_process=nullptr;s.runtime_process_asid=0;
        s.host_runtime_observation=false;s.endNativeHostPostCpWindow();
    }
    s.runtime_route_raw=s.endpoints[0].stream_owner->faultActiveForRuntime();s.stopped=true;
    return s.runtime_route_raw?ZornSmmuSparse4KIoError:ZornSmmuSparse4KSuccess;
    // Actual owned S2CR containment;uncertainty retains everything,no reset.
}
ZornSmmuSparse4KStatus ZornGen7SmmuDomain26::haltDirectRuntime(void *context)
{
    auto *o=static_cast<ZornGen7SmmuDomain26 *>(context);
    if(!o || !o->storage_ || !normal())return ZornSmmuSparse4KArgument;
    auto &s=*o->storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || s.failed() || !s.runtime_ready ||
       s.runtime_mapping_halted || !s.register_maps)return ZornSmmuSparse4KIoError;
    const auto observed=observeDirectRuntime(o,true);if(observed)return observed;
    if(s.native_controller_mode){
        if(!s.runtime_boot || s.host_runtime_mutation || s.runtime_transaction_thread ||
           s.runtime_boot->beginNativeKernelTableLease(*o) || !s.beginNativeHostPostCpWindow()){
            s.stopped=true;return ZornSmmuSparse4KIoError;
        }
        s.runtime_transaction_thread=current_thread();s.runtime_mapping_halted=true;s.host_runtime_mutation=true;
        s.selectNativeHostPostCpBank(0);return ZornSmmuSparse4KSuccess;
    }
    const auto raw=s.register_maps->haltGpuBusForSmmuTableUpdate();
    if(raw){s.stopped=true;return ZornSmmuSparse4KIoError;}
    s.runtime_mapping_halted=true;return ZornSmmuSparse4KSuccess;
}
ZornSmmuSparse4KStatus ZornGen7SmmuDomain26::releaseDirectRuntime(void *context)
{
    auto *o=static_cast<ZornGen7SmmuDomain26 *>(context);
    if(!o || !o->storage_ || !normal())return ZornSmmuSparse4KArgument;
    auto &s=*o->storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || s.failed() || !s.runtime_ready ||
       !s.runtime_mapping_halted || !s.register_maps)return ZornSmmuSparse4KIoError;
    const auto observed=observeDirectRuntime(o,true);if(observed)return observed;
    if(s.native_controller_mode){
        if(!s.host_runtime_mutation || s.runtime_transaction_thread!=current_thread() ||
           !s.runtime_boot || s.runtime_boot->endNativeKernelTableLease(*o)){
            s.host_runtime_mutation=false;s.runtime_transaction_thread=THREAD_NULL;
            s.endNativeHostPostCpWindow();s.stopped=true;return ZornSmmuSparse4KIoError;
        }
        s.host_runtime_mutation=false;s.runtime_transaction_thread=THREAD_NULL;
        s.endNativeHostPostCpWindow();s.runtime_mapping_halted=false;return ZornSmmuSparse4KSuccess;
    }
    const auto raw=s.register_maps->releaseGpuBusAfterSmmuTableUpdate();
    if(raw){s.stopped=true;return ZornSmmuSparse4KIoError;}
    s.runtime_mapping_halted=false;return ZornSmmuSparse4KSuccess;
}
IOReturn ZornGen7SmmuDomain26::beginDirectSubmission(void *context)
{
    auto *o=static_cast<ZornGen7SmmuDomain26 *>(context);
    if(!o || !o->storage_ || !normal())return kIOReturnNotReady;
    auto &s=*o->storage_;IORecursiveLockLock(&s.gate);
    const auto observed=observeDirectRuntime(o,true);
    if(observed){IORecursiveLockUnlock(&s.gate);return kIOReturnNotPermitted;}
    return kIOReturnSuccess;
}
void ZornGen7SmmuDomain26::endDirectSubmission(void *context)
{
    auto *o=static_cast<ZornGen7SmmuDomain26 *>(context);
    if(o && o->storage_ && IORecursiveLockHaveLock(&o->storage_->gate))IORecursiveLockUnlock(&o->storage_->gate);
}

IOReturn ZornGen7SmmuDomain26::transitionHostProcessTables(ZornGen7HostRing26 &ring,
    ZornGen7ProcessTableOperation26 operation,ZornGen7ProcessTables26 *&p,unsigned inputBits,size_t capacity)
{
    auto observe=[&](uint32_t stage,IOReturn raw,uint32_t detail=0){
        if(operation==ZornGen7ProcessTableOperation26::Prepare)ring.observeApplicationPrepare(stage,raw,detail);
    };
    if(!storage_ || !normal() || !ring.processTransitionHeldForDomain(*this)){observe(40,kIOReturnNotReady);return kIOReturnNotReady;}
    observe(40,0);
    auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate)){observe(41,kIOReturnNotReady);return kIOReturnNotReady;}
    observe(41,0);
    IORecursiveLockLock(&s.gate);
    bool nativeWindow=false;
    auto finish=[&](IOReturn raw){
        if(nativeWindow){
            s.host_process_transition=false;s.host_process_write_root=false;s.host_process_invalidate=false;
            s.host_process_ttbr0=0;s.host_process_asid=0;s.host_runtime_observation=false;
            s.endNativeHostPostCpWindow();
        }
        IORecursiveLockUnlock(&s.gate);return raw;
    };
    if(s.native_controller_mode){
        if(s.runtime_boot!=&ring || s.host_runtime_mutation || s.runtime_mapping_halted){observe(42,kIOReturnNotReady);return finish(kIOReturnNotReady);}
        observe(42,0);
        uint32_t failedPredicate=0;
        const bool opened=s.beginNativeHostPostCpWindow(operation==ZornGen7ProcessTableOperation26::Prepare?&failedPredicate:nullptr);
        observe(61,opened?kIOReturnSuccess:kIOReturnNotReady,failedPredicate);
        if(!opened){observe(43,kIOReturnNotReady);return finish(kIOReturnNotReady);}
        observe(43,0);
        nativeWindow=true;s.host_process_transition=true;s.host_runtime_observation=true;
    }
    if(!ring.processTransitionHeldForDomain(*this) || s.failed() || !s.runtime_ready ||
       !s.runtime_grant_returned || s.runtime_grant_raw || !s.post_cp_context_ready ||
       !s.host_gpu_mmu_ready || !s.host_gpu_tables || !s.global_fault_owner){observe(44,kIOReturnNotReady);return finish(kIOReturnNotReady);}
    observe(44,0);
    const auto globalFault=s.global_fault_owner->verifyNoFault();observe(45,globalFault);
    if(globalFault)return finish(kIOReturnNotReady);
    for(unsigned i=0;i<2;++i){s.selectNativeHostPostCpBank(i);auto &e=s.endpoints[i];
        if(!e.fault_owner || !e.stream_owner){observe(46,kIOReturnNotReady,i);return finish(kIOReturnNotReady);}
        observe(46,0,i);
        const auto fault=e.fault_owner->verifyNoFault();observe(47,fault,i);if(fault)return finish(kIOReturnNotReady);
        const auto conflict=e.stream_owner->verifyActiveConflicts();observe(48,conflict,i);if(conflict)return finish(kIOReturnNotReady);
        if(s.failed()){observe(49,kIOReturnNotReady,i);return finish(kIOReturnNotReady);}
        observe(49,0,i);
    }
    s.selectNativeHostPostCpBank(0);
    auto &e=s.endpoints[0];IOReturn raw=kIOReturnBadArgument;
    if(s.native_controller_mode){
        // Native controller owns this exact reserved USER bank and stream.
        // Its child owner alone allocates process ASIDs beyond every bank tag.
        // The actual Ring has drained all jobs under its current held issuer
        // and client OOB. No caller-supplied root or ASID enters this window.
        if(!e.consumer || e.reservation.consumer!=e.consumer || !e.reservation.acquired ||
           e.reservation.bank>=s.banks || !s.reserved[e.reservation.bank] ||
           !s.nativeControllerClaimHeld() || !ring.processTransitionHeldForDomain(*this)){
            observe(50,kIOReturnNotPermitted);return finish(kIOReturnNotPermitted);}
        observe(50,0);
        const bool metadata=operation==ZornGen7ProcessTableOperation26::Prepare ||
            operation==ZornGen7ProcessTableOperation26::DiscardNeverInstalled;
        if(!metadata && (!p || p->ringOwner_!=&ring ||
           !s.host_gpu_tables->nativeProcessWindow(*p,operation,e.reservation.bank,e.reservation.context_offset,
               s.host_process_ttbr0,s.host_process_asid,s.host_process_write_root,s.host_process_invalidate)))
            return finish(kIOReturnNotPermitted);
        s.host_runtime_observation=metadata || !s.host_process_invalidate;
    }
    switch(operation){
    case ZornGen7ProcessTableOperation26::Prepare:
        raw=s.host_gpu_tables->prepareProcessTables(inputBits,p);
        // All partials are already retained by the actual owner. Read only
        // source-defined software progress; no allocation or memory teardown.
        observe(51,raw,p?(1u|(p->ranges_?2u:0u)|(p->pages_?4u:0u)|(p->arena_.pages?8u:0u)|
            (p->seed_.complete?16u:0u)|(p->audit_.complete?32u:0u)|(p->asidHeld_?64u:0u)|
            (p->prepared_?128u:0u)|(p->state_.poisoned?256u:0u)):0u);break;
    case ZornGen7ProcessTableOperation26::Select:
        if(!p || p->parent_!=s.host_gpu_tables || !p->prepared_ || !p->asidHeld_)break;
        if(s.native_controller_mode){
            // Both independent authorities were checked above: actual native
            // controller/client execution and exact live child table identity.
            // Keep each child's attempt/result, including terminal refusal.
            if(!p->bankGrantAttempted_){
                p->bankGrantAttempted_=true;
                p->bankGrantRaw_=(s.nativeControllerClaimHeld() && ring.processTransitionHeldForDomain(*this))?
                    kIOReturnSuccess:kIOReturnNotPermitted;
                p->bankGrantReturned_=true;
            }
        }else{
            if(!s.authority.acquireActualBank){raw=kIOReturnNotPermitted;break;}
            if(!p->bankGrantAttempted_){
                p->bankGrantAttempted_=true;
                p->bankGrantRaw_=s.authority.acquireActualBank(s.authority.cookie,s.controller,
                    *e.consumer,e.reservation.bank,p->asid_,&e.packed,1);
                p->bankGrantReturned_=true;
            }
        }
        if(!p->bankGrantReturned_ || p->bankGrantRaw_ || s.failed() ||
           !ring.processTransitionHeldForDomain(*this)){raw=kIOReturnNotPermitted;break;}
        raw=s.host_gpu_tables->selectProcessTables(*p,e.program_route.io_,e.reservation.bank,
            e.reservation.context_offset,s.host_gpu_mmu_poll_budget);break;
    case ZornGen7ProcessTableOperation26::RestoreKernel:
        raw=s.host_gpu_tables->restoreKernelTables(e.program_route.io_,e.reservation.bank,
            e.reservation.context_offset,s.host_gpu_mmu_poll_budget);break;
    case ZornGen7ProcessTableOperation26::RetireDetached:
        raw=s.host_gpu_tables->retireDetachedProcessTables(p,e.program_route.io_,e.reservation.bank,
            e.reservation.context_offset,s.host_gpu_mmu_poll_budget);break;
    case ZornGen7ProcessTableOperation26::DiscardNeverInstalled:
        raw=s.host_gpu_tables->discardProcessTables(p);break;
    case ZornGen7ProcessTableOperation26::AttachVm:
        if(!p || p->parent_!=s.host_gpu_tables || !p->bankGrantReturned_ || p->bankGrantRaw_ ||
           p->domain_ || p->vmAttachAttempted_)break;
        p->domain_=this;p->routes_={p,e.reservation.bank,observeProcessRuntime,faultProcessRuntime,
            haltProcessRuntime,releaseProcessRuntime,beginProcessSubmission,endProcessSubmission};
        raw=s.host_gpu_tables->attachProcessVm(*p,e.program_route.io_,capacity,s.host_gpu_mmu_poll_budget);break;
    case ZornGen7ProcessTableOperation26::DetachVm:
        if(p && p->domain_==this)raw=s.host_gpu_tables->detachProcessVm(*p);break;
    }
    // Any failed hardware transition is terminal in the existing controller.
    // No reset,rollback,automatic restore,release of uncertainty or retry.
    if(raw && operation!=ZornGen7ProcessTableOperation26::Prepare &&
       operation!=ZornGen7ProcessTableOperation26::DiscardNeverInstalled)s.stopped=true;
    if(!raw && (s.failed() || !ring.processTransitionHeldForDomain(*this)))raw=kIOReturnNotReady;
    observe(52,raw);return finish(raw);
}

ZornSmmuSparse4KStatus ZornGen7SmmuDomain26::observeProcessRuntime(void *cookie,bool full)
{
    auto *p=static_cast<ZornGen7ProcessTables26 *>(cookie);
    if(!p || !p->domain_ || !p->domain_->storage_ || !normal())return ZornSmmuSparse4KArgument;
    auto &s=*p->domain_->storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || s.failed() || !s.runtime_ready ||
       !s.runtime_grant_returned || s.runtime_grant_raw || p->parent_!=s.host_gpu_tables ||
       !p->bankGrantReturned_ || p->bankGrantRaw_ || !p->vmAttachAttempted_ ||
       !s.global_fault_owner || s.global_fault_owner->verifyNoFault())return ZornSmmuSparse4KIoError;
    const bool open=s.native_controller_mode && !s.host_post_cp_access;
    if(s.native_controller_mode && (!s.runtime_boot ||
       !s.runtime_boot->nativeProcessContextHeldForDomain(*p->domain_,*p) ||
       (open && !s.beginNativeHostPostCpWindow())))return ZornSmmuSparse4KIoError;
    if(s.native_controller_mode && (__atomic_load_n(&s.host_context_thread,__ATOMIC_ACQUIRE)!=current_thread() ||
       (!open && !s.host_process_transition &&
        !(s.host_runtime_mutation && s.runtime_mapping_halted && s.runtime_process==p &&
          s.runtime_transaction_thread==current_thread() && s.runtime_process_asid==p->asid_))))
        return ZornSmmuSparse4KIoError;
    const bool wasObservation=s.host_runtime_observation;
    if(s.native_controller_mode)s.host_runtime_observation=true;
    auto finish=[&](ZornSmmuSparse4KStatus raw){
        s.host_runtime_observation=wasObservation;s.selectNativeHostPostCpBank(0);
        if(open)s.endNativeHostPostCpWindow();return raw;
    };
    for(unsigned i=0;i<2;++i){s.selectNativeHostPostCpBank(i);auto &e=s.endpoints[i];
        if(!e.fault_owner || !e.stream_owner || e.fault_owner->verifyNoFault() ||
           (full?e.stream_owner->verifyActiveConflicts():e.stream_owner->verifyActive()) || s.failed())
            return finish(ZornSmmuSparse4KIoError);
    }
    s.selectNativeHostPostCpBank(0);auto &e=s.endpoints[0];
    return finish(s.host_gpu_tables->observeProcessTables(*p,e.program_route.io_,e.reservation.bank,e.reservation.context_offset)?
        ZornSmmuSparse4KStateMismatch:ZornSmmuSparse4KSuccess);
}

ZornSmmuSparse4KStatus ZornGen7SmmuDomain26::faultProcessRuntime(void *cookie)
{
    auto *p=static_cast<ZornGen7ProcessTables26 *>(cookie);
    if(!p || !p->domain_ || !p->domain_->storage_ || !normal())return ZornSmmuSparse4KArgument;
    if(!IORecursiveLockHaveLock(&p->domain_->storage_->gate))return ZornSmmuSparse4KArgument;
    return faultDirectRuntime(p->domain_);
}
ZornSmmuSparse4KStatus ZornGen7SmmuDomain26::haltProcessRuntime(void *cookie)
{
    auto *p=static_cast<ZornGen7ProcessTables26 *>(cookie);
    if(!p || !p->domain_ || !p->domain_->storage_ || !normal())return ZornSmmuSparse4KArgument;
    auto &s=*p->domain_->storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || s.failed() || !s.runtime_ready ||
       s.runtime_mapping_halted || !s.register_maps)return ZornSmmuSparse4KIoError;
    const auto observed=observeProcessRuntime(p,true);if(observed)return observed;
    if(s.native_controller_mode){
        if(!s.runtime_boot || s.host_runtime_mutation || s.host_process_transition ||
           s.runtime_transaction_thread || s.runtime_process || s.process_submission_depth ||
           !p->asidHeld_ || p->context_.asid!=p->asid_ ||
           s.runtime_boot->beginNativeProcessTableLease(*p->domain_,*p) ||
           !s.beginNativeHostPostCpWindow()){
            s.stopped=true;return ZornSmmuSparse4KIoError;
        }
        // Child lifetime/selected root and exact tag were observed under the
        // same held issuer. Only this process's ASID invalidation is opened.
        s.runtime_process=p;s.runtime_process_asid=p->asid_;s.runtime_transaction_thread=current_thread();
        s.runtime_mapping_halted=true;s.host_runtime_mutation=true;
        s.selectNativeHostPostCpBank(0);return ZornSmmuSparse4KSuccess;
    }
    const auto raw=s.register_maps->haltGpuBusForSmmuTableUpdate();
    if(raw){s.stopped=true;return ZornSmmuSparse4KIoError;}
    s.runtime_mapping_halted=true;return ZornSmmuSparse4KSuccess;
}
ZornSmmuSparse4KStatus ZornGen7SmmuDomain26::releaseProcessRuntime(void *cookie)
{
    auto *p=static_cast<ZornGen7ProcessTables26 *>(cookie);
    if(!p || !p->domain_ || !p->domain_->storage_ || !normal())return ZornSmmuSparse4KArgument;
    auto &s=*p->domain_->storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || s.failed() || !s.runtime_ready ||
       !s.runtime_mapping_halted || !s.register_maps)return ZornSmmuSparse4KIoError;
    const auto observed=observeProcessRuntime(p,true);
    if(s.native_controller_mode){
        const bool same=s.host_runtime_mutation && s.runtime_process==p &&
            s.runtime_transaction_thread==current_thread() && s.runtime_process_asid==p->asid_;
        const auto raw=(!observed && same && s.runtime_boot)?
            s.runtime_boot->endNativeProcessTableLease(*p->domain_,*p):kIOReturnNotReady;
        // Revoke MMIO permissions even if hardware/owner validation failed.
        // The Ring retains an unsuccessful lease and the VM retains backing.
        s.host_runtime_mutation=false;s.runtime_transaction_thread=THREAD_NULL;
        s.runtime_process=nullptr;s.runtime_process_asid=0;s.endNativeHostPostCpWindow();
        if(raw){s.stopped=true;return ZornSmmuSparse4KIoError;}
        s.runtime_mapping_halted=false;return ZornSmmuSparse4KSuccess;
    }
    if(observed)return observed;
    const auto raw=s.register_maps->releaseGpuBusAfterSmmuTableUpdate();
    if(raw){s.stopped=true;return ZornSmmuSparse4KIoError;}
    s.runtime_mapping_halted=false;return ZornSmmuSparse4KSuccess;
}
bool ZornGen7SmmuDomain26::nativeProcessSubmissionHeldForRing(const ZornGen7HostRing26 &ring) const
{
    if(!storage_ || !normal())return false;const auto &s=*storage_;auto *p=s.process_submission_owner;
    return IORecursiveLockHaveLock(&s.gate) && s.native_controller_mode && !s.failed() &&
        s.runtime_ready && s.runtime_boot==&ring && p && p->domain_==this &&
        s.process_submission_depth && s.process_submission_thread==current_thread() &&
        !s.runtime_mapping_halted && !s.host_runtime_mutation && !s.host_process_transition &&
        !s.host_post_cp_access && p->vmAttached_ && !p->vmDetached_ && !p->state_.detached &&
        p->submitAttached_ && p->clientState_ && !p->vm_.poisoned() &&
        ring.nativeProcessContextHeldForDomain(*this,*p);
}
IOReturn ZornGen7SmmuDomain26::beginProcessSubmission(void *cookie)
{
    auto *p=static_cast<ZornGen7ProcessTables26 *>(cookie);
    if(!p || !p->domain_ || !p->domain_->storage_ || !normal())return kIOReturnNotReady;
    auto &s=*p->domain_->storage_;IORecursiveLockLock(&s.gate);
    if(s.native_controller_mode && (s.runtime_mapping_halted || s.host_runtime_mutation ||
       s.host_process_transition || s.runtime_process || s.process_submission_depth==UINT32_MAX ||
       (s.process_submission_depth && (s.process_submission_owner!=p ||
        s.process_submission_thread!=current_thread())))){
        IORecursiveLockUnlock(&s.gate);return kIOReturnNotPermitted;
    }
    const auto observed=observeProcessRuntime(p,true);
    if(observed){IORecursiveLockUnlock(&s.gate);return kIOReturnNotPermitted;}
    if(s.native_controller_mode){
        // Submit::submit calls retireCompleted recursively. Balance each real
        // recursive gate acquisition without opening a second process/thread.
        s.process_submission_owner=p;s.process_submission_thread=current_thread();++s.process_submission_depth;
    }
    return kIOReturnSuccess;
}
void ZornGen7SmmuDomain26::endProcessSubmission(void *cookie)
{
    auto *p=static_cast<ZornGen7ProcessTables26 *>(cookie);
    if(!p || !p->domain_ || !p->domain_->storage_)return;auto &s=*p->domain_->storage_;
    if(!IORecursiveLockHaveLock(&s.gate))return;
    if(s.native_controller_mode){
        if(!s.process_submission_depth || s.process_submission_owner!=p ||
           s.process_submission_thread!=current_thread()){s.stopped=true;return;}
        if(!--s.process_submission_depth){s.process_submission_owner=nullptr;s.process_submission_thread=THREAD_NULL;}
    }
    IORecursiveLockUnlock(&s.gate);
}
