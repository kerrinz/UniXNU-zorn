#include "ZornProgressGate203.h"
extern "C" void Zorn26RecordRuntimeResult(unsigned);
extern "C" void Zorn26RecordKnownImageResult(unsigned);
#include "ZornGen7CpBootstrapAuthority26.h"
/* SPDX-License-Identifier: GPL-2.0-only */
#include "ZornGen7DarwinBoardOwner.h"
#include "ZornGen7InactiveOwner26.h"
#include "ZornGen7HostGpuCode26.h"
#include "ZornGen7HostGpuRegisters26.h"
#include "ZornGen7GpuIrq26.h"
#include "ZornGen7HostRing26.h"
#include "ZornGen7AppExecution26.h"
#include <kern/task.h>
#include "ZornGen7FirmwareAssets26.h"
#include "ZornGen7RscRuntime26.h"
#include <IOKit/IOLib.h>
#include <kern/clock.h>
#include <kern/sched_prim.h>
#include <IOKit/IOPlatformExpert.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <libkern/c++/OSSymbol.h>
#include <libkern/c++/OSSharedPtr.h>
#include <libkern/c++/OSData.h>
#include "ZornGen7StockGmuClockMetadata.inc"
#include "ZornGen7GmuFrequencySource26.inc"
#include "ZornGen7AhbControl.h"
#include "ZornGen7StockClockGraphMetadata.inc"
#include "ZornGen7ClockSupplierSource.inc"
#include "ZornGen7GccSupplySource26.inc"
#include "ZornGen7ClockBuildConfig26.h"
#include "ZornGen79HubSource26.inc"
#include "ZornGen7DdrSource26.inc"
#include "ZornGen79InitFields.h"
#include "ZornGen79CoreSource26.inc"
#include "ZornGen7CxGdscSource26.inc"
#include "ZornGen7CxGdscRegisterEnable.h"
#include "ZornGen7CxCoreSource26.inc"
#include "ZornGen7CxCompletionSource26.inc"
#include "ZornGen7SmmuControllerPower.h"
#include "ZornGen7SmmuPowerSource26.inc"
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7ScmOwner26.h"
#include "ZornGen7ZapOwner26.h"
#include "ZornGen7GmuIrq26.h"
#include "ZornGen7DirectHfi26.h"
#include "ZornGen7HwschedHfi26.h"
#include "ZornGen7HostTables26.h"
#include "ZornGen7HostBandwidthArithmetic26.h"
#include "ZornGen7CommandDbResources26.h"
#include "ZornGen7IccInputs26.h"
#include "ZornGen7SmmuRuntimePm26.h"
#include "ZornGen7SmmuDomain26.h"
#include "ZornGen7GpuMmuAuthority26.h"
#include "ZornGen7DirectRuntimeAuthority26.h"
#include "ZornGen7ProxySourceMetadata.inc"
#include "ZornGen7CoreSourceMetadata.inc"
#include "ZornGen7MmcxProxySourceMetadata.inc"

// Publication outcome only: bit32 marks a returned call; low32 is IOReturn.
// This is not application submission/completion evidence.
static uint64_t nativeApplicationPublication;
extern "C" uint64_t zorn26_native_application_publication()
{return __atomic_load_n(&nativeApplicationPublication,__ATOMIC_ACQUIRE);}

using ZornHostMmuFence=IOReturn (*)(ZornGen7SmmuDomain26 &,OSObject &,ZornGen7IccInputs26 &,unsigned,uint32_t &);
void Zorn26RecordHostMmuFence(uint32_t,IOReturn);
void Zorn26RecordCodeBindResult(IOReturn);
void Zorn26RecordGxRegistersResult(IOReturn);
void Zorn26RecordGpuIrqResult(IOReturn);
void Zorn26RecordCpResult(IOReturn);
void Zorn26RecordZapResult(IOReturn);
void Zorn26RecordBootstrapResult(IOReturn);
extern "C" IOReturn zorn26_zap_acquire_cpu_window(IOMemoryDescriptor *,uint64_t,uint64_t);
extern "C" bool zorn26_zap_cpu_window_held(IOMemoryDescriptor *);
extern "C" void zorn26_native_gpu_oob_observation(uint32_t (&out)[5])
{
    extern void Zorn26CopyGpuOob(uint32_t (&)[5]);
    Zorn26CopyGpuOob(out);
}
void Zorn26RegisterGmuTcmHandoff(ZornGen7SmmuDomain26 &, OSObject &,
    unsigned (*)(OSObject &, ZornGen7SmmuDomain26 &, const uint32_t (&)[5]),
    unsigned (*)(OSObject &,ZornGen7SmmuDomain26 &,ZornHostMmuFence));

namespace {
uint32_t nativeHfiControlObservation;
uint32_t nativeGpuOobObservation[5];
uint32_t nativeGpuStartObservation[5];
uint32_t nativeHfiQueryObservation[5];
uint32_t nativeHfiPerfObservation[5];
uint32_t nativeHfiBwObservation[5];
uint32_t nativeHfiCoreObservation[4];
uint32_t nativeHfiDcvsObservation[5];
uint32_t nativeGpuTablesObservation;
uint64_t nativeCxScmStatus;
bool nativeCxScmStatusAvailable;
}
extern "C" uint32_t zorn26_native_hfi_control_observation()
{
    return __atomic_load_n(&nativeHfiControlObservation,__ATOMIC_ACQUIRE);
}
extern "C" void zorn26_native_hfi_query_observation(uint32_t (&out)[5])
{
    out[0]=__atomic_load_n(&nativeHfiQueryObservation[0],__ATOMIC_ACQUIRE);
    for(unsigned i=1;i<5;++i)out[i]=nativeHfiQueryObservation[i];
}
extern "C" void zorn26_native_hfi_perf_observation(uint32_t (&out)[5])
{
    out[0]=__atomic_load_n(&nativeHfiPerfObservation[0],__ATOMIC_ACQUIRE);
    for(unsigned i=1;i<5;++i)out[i]=nativeHfiPerfObservation[i];
}
extern "C" void zorn26_native_hfi_bw_observation(uint32_t (&out)[5])
{
    out[0]=__atomic_load_n(&nativeHfiBwObservation[0],__ATOMIC_ACQUIRE);
    for(unsigned i=1;i<5;++i)out[i]=nativeHfiBwObservation[i];
}
extern "C" void zorn26_native_hfi_core_observation(uint32_t (&out)[4])
{
    for(unsigned i=0;i<4;++i)out[i]=nativeHfiCoreObservation[i];
}
extern "C" void zorn26_native_hfi_dcvs_observation(uint32_t (&out)[5])
{
    for(unsigned i=0;i<5;++i)out[i]=nativeHfiDcvsObservation[i];
}
extern "C" uint32_t zorn26_native_gpu_tables_observation()
{
    return __atomic_load_n(&nativeGpuTablesObservation,__ATOMIC_ACQUIRE);
}
extern "C" bool zorn26_cx_scm_read_status(uint64_t *out)
{
    if(!out || !__atomic_load_n(&nativeCxScmStatusAvailable,__ATOMIC_ACQUIRE))return false;
    *out=nativeCxScmStatus;
    return true;
}

namespace {
struct Allocation {Allocation *next;void *base;size_t bytes;};
struct Dependency {Dependency *next;OSObject *object;};
// Exact fixed-clock source: no device, no parents, flags0, optional accuracy0.
// False runtime-PM/sync cells describe its absent runtime device, not a rail,
// power or clock-enable success. Rate/accuracy come from actual native data.
struct OwnedBoardXo {
    const uint64_t rate,accuracy,fixed_flags=0;
    const bool runtime_pm_enabled=false,provider_has_sync_state=false;
    ZornGen7Clock::ActualNativeClockProviderFields provider{};
    const ZornGen7Clock::NativeClockSourceOps ops{
        ZornGen7Clock::NativeRateOps::MiCodeRegisteredFixedRate,
        ZornGen7Clock::NativePrepareOps::MiCodeRegisteredFixedRateNoPrepare};
    ZornGen7Clock::ActualNativeClockInitData init;
    ZornGen7Clock::NativeClockHardware hardware;
    OwnedBoardXo(uint32_t r,uint32_t a):rate(r),accuracy(a),
        init{{"xo_board",sizeof("xo_board")},&ops,0,0,nullptr,0,nullptr,0,nullptr,0,
            &runtime_pm_enabled,&provider_has_sync_state,&provider,nullptr},hardware(&init)
    {provider.fixed_rate=&rate;provider.fixed_accuracy=&accuracy;provider.fixed_flags=&fixed_flags;}
};
struct NativeClockRegulator {
    NativeClockRegulator *next;const ZornGen7Clock::ActualClockSupplierFields *fields;
    const ZornGen7Clock::NativeClockFirmwareNode *node;IOService *device;
    ZornGen7Rpmh::NativeCoreConsumer **head;volatile uint32_t *open_count;const volatile bool *exclusive;
    uint32_t source_index;uint8_t digest[32];
};
// Real private controller lifecycle records. The PM cell is observed from the
// actual LP64 native provider, whose IOServicePM sets pm_vars to non-NULL when
// PMinit completes. This cold source path admits only its stable unmanaged
// epoch, not Linux PM flags, a powered-domain result or permission from a node.
struct OwnedNativeClockController {
    using Sync=ZornGen7Clock::ClockSyncStateResult (ZornGen7Clock::NativeClockRoot::*)(
        const ZornGen7Clock::NativeClockFirmwareNode &);
    IOService &provider;OSSharedPtr<const OSSymbol> name;
    const bool runtime_pm_enabled;
    const Sync sync;const bool provider_has_sync_state;bool sync_attempted=false,sync_completion_ready=false;
    const ZornGen7Clock::NativeClockFirmwareNode *bound_node=nullptr;
    OwnedNativeClockController(IOService &p,Sync callback):provider(p),
        name(p.copyName(gIOServicePlane),OSNoRetain),runtime_pm_enabled(p.pm_vars!=nullptr),
        sync(callback),provider_has_sync_state(sync!=nullptr){}
    ZornGen7Clock::ClockSyncStateResult syncActualHeld(ZornGen7Clock::NativeClockRoot &root,
        const ZornGen7Clock::NativeClockFirmwareNode &actualProviderNode)
    {
        if(sync_attempted || !sync || !sync_completion_ready || bound_node!=&actualProviderNode || provider.pm_vars || provider.getState()!=0)return {};
        sync_attempted=true;return (root.*sync)(actualProviderNode);
    }
};
struct NativeClockRegulatorConsumer {
    ZornGen7Rpmh::NativeCoreConsumer projection;NativeClockRegulator *supplier;
    char supply_name[64];bool always_on;IOService *device;
};
// Canonical native software fields: fresh zero is unpublished hub metadata
// and NONE state, never a clock getter, power-off or hardware-ready result.
// The real later core-init producer must publish hub frequency before enable.
struct OwnedGmuClockSoftwareState {
    volatile uint64_t hub_frequency=0;
    volatile uint32_t device_state=0;
    volatile uint64_t flags=0; // Source fresh kzalloc flags;not hardware state.
    uint32_t versions[5]{};volatile uint64_t hwsched_flags=0;
};
struct OwnedNativeCxCore {
    IOService &provider,&gmu;
    ZornGen7Rpmh::NativeCoreConsumer *consumers=nullptr;
    ZornGen7Rpmh::NativeCoreConsumer primary{};
    ZornGen7Rpmh::NativeNotifierNode *notifications=nullptr;
    uint32_t valid_ops=ZornGen7CxCoreSource26::valid_ops,n_coupled=0,n_resolved=0,use_count=0,open_count=0;
    int32_t min_value=0,max_value=0,offset=0,max_step=0;
    bool custom_balancer=false,has_supply=true,has_gpio=false,gpio_state=false,registered=false;
    uint32_t min_dropout=0,ramp=0,descriptor_ramp=0,settling=0,settling_up=0,settling_down=0;
    uint32_t enable_time=0,descriptor_enable_time=0,off_on_delay=0,poll_enabled=0;
    uint64_t last_off=0;
    OwnedNativeCxCore *coupled[1]{};
    const ZornGen7Rpmh::ActualCoreVoltageFields voltage;
    const ZornGen7Rpmh::ActualCoreEnableFields enable;
    ZornGen7Rpmh::NativeRegulatorNotifiers notifiers;
    const ZornGen7CxGdsc::ActualArcParentSupply parent;
    ZornGen7CxGdsc::RegulatorCore core;
    OwnedNativeCxCore(IOService &p,IOService &g,IORecursiveLock *startup,IOLock *dependent,IORWLock *notifier,
        const ZornGen7Clock::ActualClockSupplierFields &supply,ZornGen7Rpmh::NativeCoreConsumer &consumer,
        ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation,
        ZornGen7CxGdsc::RegisterEnable &hardware):
      provider(p),gmu(g),voltage{dependent,&consumers,&valid_ops,&min_value,&max_value,&offset,&max_step,
        &n_coupled,&n_resolved,&custom_balancer,&has_supply,supply.voltage.valid_ops_mask,&min_dropout,
        &ramp,&descriptor_ramp,&settling,&settling_up,&settling_down},
      enable{&use_count,&has_gpio,&gpio_state,&enable_time,&descriptor_enable_time,&off_on_delay,&poll_enabled,&last_off},
      notifiers(notifier,&notifications),
      parent{supply.voltage,supply.enable,consumer,supply.arc,supply.voter,cache,reservation,supply.notifiers},
      core(startup,voltage,enable,primary,parent,hardware,notifiers){}
};
// Real controller allocation and its distinct regulator consumer. Fresh CPU
// power_count0 never observes hardware off. The MMIO view starts unavailable;
// normal suspend and domain/TLB paths still require genuine mapping/PM owners.
struct OwnedSmmuPowerFrame {
    IOService &provider;IOMemoryDescriptor &descriptor;
    OSSharedPtr<const OSSymbol> name;
    ZornGen7Rpmh::NativeCoreConsumer vdd{};
    char supply_name[64]{};
    volatile int32_t power_count=0,registered_regulators=0;
    const bool has_resume=false,has_suspend=false;
    ZornGen7Icc::NativePath *icc_path=nullptr;
    ArmSmmu4KMmio global_page{};
    ArmSmmu4KIo guarded_global_io{};
    ArmSmmu4KIo native_probe_io{};
    IOLock *power_lock;
    ZornGen7Clock::NativeClockFirmwareConsumer clocks;
    ZornGen7Smmu::ControllerPower *operation=nullptr;
    IOService *native_claimant=nullptr,*native_claim_parent=nullptr;
    bool native_power_attempted=false,native_provider_opened=false;
    ZornGen7Smmu::ControllerPower::Reference *native_reference=nullptr;
    ZornGen7ColdBoot::OperationResult native_power_result{ZornGen7ColdBoot::Disposition::Unavailable,ZornGen7ColdBoot::StatusDomain::Unavailable,0,0};
    OwnedSmmuPowerFrame(IOService &p,IOMemoryDescriptor &d,IOLock *lock,
        const ZornGen7Clock::NativeClockFirmwareNode &node,OSObject &owner):
      provider(p),descriptor(d),name(p.copyName(gIOServicePlane),OSNoRetain),power_lock(lock),
      clocks{ZornGen7Clock::ClockPropertyState::Present,&node,
        name?name->getCStringNoCopy():nullptr,name?size_t(name->getLength())+1u:0u,&owner}{}
};
struct OwnedNativeClockGraphInputs {
    const ZornGen7Clock::ActualNativeGmuClockGraphInputs graph;
    const ZornGen7Clock::NativeClockFirmwareConsumer gmu;
    OwnedNativeClockGraphInputs(const ZornGen7Clock::ActualStockGmuClockGraphFields &in,
        const ZornGen7Clock::NativeClockFirmwareConsumer (&consumers)[4],const OwnedNativeClockController &rpmh):
      graph{in.registered_xo_board,consumers[0],consumers[1],consumers[2],
        {{&rpmh.runtime_pm_enabled,&rpmh.provider_has_sync_state},in.controllers[1],in.controllers[2]},
        {in.physical[0],in.physical[1],in.physical[2],in.physical[3],in.physical[4],in.physical[5],
         in.physical[6],in.physical[7],in.physical[8],in.physical[9],in.physical[10],in.physical[11],
         in.physical[12],in.physical[13],in.physical[14],in.physical[15],in.physical[16],in.physical[17],in.physical[18],in.physical[19],in.physical[20],in.physical[21],in.physical[22],in.physical[23],in.physical[24]},
        in.command_db,in.rpmh_cache,in.rpmh_reservation,ZornGen7Clock::ClockControllerNodeLayout::ZornNative26,in.command_db_reader},gmu(consumers[3]){}
};

struct OwnedRegulatorProxyRecord {
    OwnedRegulatorProxyRecord *owned_next,*live_next;
    NativeClockRegulatorConsumer consumer;
    ZornGen7Rpmh::NativeOwnedRegulatorProxy *operation;
};
struct OwnedSuppliedProxyRecord {
    OwnedSuppliedProxyRecord *owned_next,*live_next;
    NativeClockRegulatorConsumer consumer;
    ZornGen7Rpmh::NativeOwnedSuppliedRegulatorProxy *operation;
};
struct OwnedArcStartupFrame {
    union Input {
        ZornGen7Rpmh::ActualXoCommandDbSnapshot snapshot;
        ZornGen7Rpmh::NativeCommandDbResourceReader *reader;
        explicit Input(const ZornGen7Rpmh::ActualXoCommandDbSnapshot &s):snapshot(s){}
        explicit Input(ZornGen7Rpmh::NativeCommandDbResourceReader &r):reader(&r){}
    };
    const Input input;const bool resourceRoute;
    ZornGen7Rpmh::NativeCommandCache &cache;ZornGen7Rpmh::NativeReservation &reservation;
    OSObject &snapshot_storage,&rsc_storage;
    uint8_t digest[32]{};
    const ZornGen7Clock::NativeClockFirmwareNode *nodes[5][4]{};
    IOService *devices[5][4]{};
    const ZornGen7Clock::NativeClockFirmwareNode *first_nodes[3]{},*parents[3]{},*upstream_nodes[2]{},*mmcx_nodes[3]{};
    IOService *first_devices[3]{},*parent_devices[3]{},*upstream_devices[2]{},*mmcx_devices[3]{};
    OSSharedPtr<IORegistryEntry> native_parents[5]{};
    OSSharedPtr<const OSSymbol> parent_name_storage[3]{};
    ZornGen7Clock::NativeClockRegistrationName parent_names[3]{};
    ZornGen7Rpmh::OwnedArcStartupResult result{};
    OwnedArcStartupFrame(const ZornGen7Rpmh::ActualXoCommandDbSnapshot &s,ZornGen7Rpmh::NativeCommandCache &c,
        ZornGen7Rpmh::NativeReservation &r,OSObject &snapshot_owner,OSObject &rsc_owner):
        input(s),resourceRoute(false),cache(c),reservation(r),snapshot_storage(snapshot_owner),rsc_storage(rsc_owner){}
    OwnedArcStartupFrame(ZornGen7Rpmh::NativeCommandDbResourceReader &reader,ZornGen7Rpmh::NativeCommandCache &c,
        ZornGen7Rpmh::NativeReservation &r,OSObject &owner,OSObject &rsc_owner):
        input(reader),resourceRoute(true),cache(c),reservation(r),snapshot_storage(owner),rsc_storage(rsc_owner){}
};
struct StockGmuClockMetadata {
    ZornGen7Clock::NativeClockFirmwareSpecifier clocks[ZornGen7StockGmuClock::count];
    ZornGen7Clock::NativeClockFirmwareNode node;
    ZornGen7Clock::NativeClockFirmwareConsumer consumer;
    StockGmuClockMetadata(const ZornGen7Clock::NativeClockFirmwareNode &soc,
        const ZornGen7Clock::NativeClockFirmwareNode &gpucc,const ZornGen7Clock::NativeClockFirmwareNode &gcc,OSObject &owner):
      node{&soc,ZornGen7Clock::ClockPropertyState::Present,ZornGen7Clock::ClockPropertyState::Unobserved,
        clocks,ZornGen7StockGmuClock::count,ZornGen7StockGmuClock::names,ZornGen7StockGmuClock::name_bytes,
        ZornGen7StockGmuClock::count,0,&owner,"/soc/qcom,gmu@3d69000",sizeof("/soc/qcom,gmu@3d69000")},
      // device_id is unused by indexed of_clk_get. No dev_name query, guessed
      // Linux device name or named-clkdev fallback is introduced.
      consumer{ZornGen7Clock::ClockPropertyState::Present,&node,nullptr,0,&owner}
    {
        for(size_t i=0;i<ZornGen7StockGmuClock::count;++i)
            clocks[i]={ZornGen7StockGmuClock::providers[i]?&gcc:&gpucc,&ZornGen7StockGmuClock::indices[i],1};
    }
    static void *operator new(size_t,void *p) noexcept {return p;}
};
struct StockClockGraphMetadata {
    ZornGen7Clock::NativeClockFirmwareNode nodes[ZornGen7StockClockGraph::node_count]{};
    ZornGen7Clock::NativeClockFirmwareSpecifier specifiers[ZornGen7StockClockGraph::spec_count]{};
    ZornGen7Clock::ActualNativeGmuClockGraphInputs graph;
    ZornGen7Clock::NativeClockFirmwareConsumer gmu;
    StockClockGraphMetadata(const ZornGen7Clock::ActualStockGmuClockGraphFields &in,OSObject &owner):
      graph{in.registered_xo_board,
        {ZornGen7Clock::ClockPropertyState::Present,&nodes[ZornGen7StockClockGraph::rpmh],in.device_names[0].bytes,in.device_names[0].extent,&owner},
        {ZornGen7Clock::ClockPropertyState::Present,&nodes[ZornGen7StockClockGraph::gcc],in.device_names[1].bytes,in.device_names[1].extent,&owner},
        {ZornGen7Clock::ClockPropertyState::Present,&nodes[ZornGen7StockClockGraph::gpucc],in.device_names[2].bytes,in.device_names[2].extent,&owner},
        {in.controllers[0],in.controllers[1],in.controllers[2]},
        {in.physical[0],in.physical[1],in.physical[2],in.physical[3],in.physical[4],in.physical[5],
          in.physical[6],in.physical[7],in.physical[8],in.physical[9],in.physical[10],in.physical[11],
          in.physical[12],in.physical[13],in.physical[14],in.physical[15],in.physical[16],in.physical[17],in.physical[18],in.physical[19],in.physical[20],in.physical[21],in.physical[22],in.physical[23],in.physical[24]},in.command_db,in.rpmh_cache,in.rpmh_reservation,ZornGen7Clock::ClockControllerNodeLayout::LinuxSource,in.command_db_reader},
      // Indexed of_clk_get consumes this genuine node directly; device_id is
      // not consumed here, never used as a named-clkdev/null-device observation.
      gmu{ZornGen7Clock::ClockPropertyState::Present,&nodes[ZornGen7StockClockGraph::gmu],nullptr,0,&owner}
    {
        for(size_t i=0;i<ZornGen7StockClockGraph::spec_count;++i) {
            const auto &s=ZornGen7StockClockGraph::specs[i];specifiers[i]={&nodes[s.provider],s.arguments,s.count};
        }
        for(size_t i=0;i<ZornGen7StockClockGraph::node_count;++i) {
            const auto &s=ZornGen7StockClockGraph::nodes[i];
            nodes[i]={s.parent<0?nullptr:&nodes[s.parent],s.clocks_state,s.ranges_state,
                s.spec_count?&specifiers[s.spec_start]:nullptr,s.spec_count,s.names,s.name_bytes,s.name_count,
                s.cells,&owner,s.path,s.path_bytes};
        }
    }
    static void *operator new(size_t,void *p) noexcept {return p;}
};
bool actualDeviceName(const ZornGen7Clock::NativeClockRegistrationName &name)
{
    const uintptr_t at=reinterpret_cast<uintptr_t>(name.bytes);
    if(!at || !name.extent || name.extent-1u>UINTPTR_MAX-at)return false;
    for(size_t i=0;i<name.extent;++i)if(!name.bytes[i])return true;return false;
}
bool sourcePath(const ZornGen7Clock::NativeClockFirmwareNode &node,const char *path,size_t bytes)
{
    if(!node.lifetime || !node.full_name || node.full_name_extent<bytes)return false;
    for(size_t i=0;i<bytes;++i)if(node.full_name[i]!=path[i])return false;
    return true;
}
struct alignas(8) SupplyPending {uint32_t group=0,voter=0;bool present=false;};

}
struct ZornGen7DarwinBoardOwner::Storage {
    CpuGates gates{};
    IOService *platform=nullptr;
    Allocation *allocations=nullptr;
    Dependency *dependencies=nullptr;
    bool lifetime_pinned=false;
    Stage stage=Stage::CpuConstruction;
    ZornGen7Clock::NativeClockRoot *clocks=nullptr;
    ZornGen7GmuIrq26 *gmu_irq=nullptr;bool gmu_irq_attempted=false,gmu_irq_ready=false;
    bool gmu_config_attempted=false,gmu_config_ready=false;
    ZornGen7DirectHfi26 *direct_hfi=nullptr;
    ZornGen7HostTables26 *host_tables=nullptr;bool host_tables_attempted=false,host_tables_ready=false,host_profile_attempted=false,host_default_clock_attempted=false,host_default_bw_attempted=false,host_bootstrap_unvoted=false,host_gpu_oob_attempted=false,host_gpu_tables_attempted=false,host_gpu_mmu_attempted=false,host_gpu_mmu_ready=false,host_gpu_oob_ready=false,host_gpu_code_attempted=false;
    bool host_gpu_start_window_attempted=false,host_gpu_start_window_held=false;
    bool host_gpu_mmu_lease_attempted=false,host_gpu_mmu_lease_held=false;
    bool host_gpu_post_cp_restore_attempted=false,host_gpu_post_cp_restore_held=false;
    bool host_direct_runtime_window_attempted=false,host_direct_runtime_window_held=false;
    int host_direct_runtime_window_raw=kIOReturnNotReady;
    ZornGen7DirectRuntimeAuthority26 forwarded_direct_runtime_authority{};
    int host_gpu_mmu_lease_raw=kIOReturnNotReady,host_gpu_post_cp_restore_raw=kIOReturnNotReady;
    int host_gpu_start_window_raw=kIOReturnNotReady;
    ZornGen7InactiveOwner26 *native_direct_memory_owner=nullptr;
    ZornGen7InactiveOwner26 *host_gpu_mmu_parent=nullptr;
    ZornGen7RegisterMaps26 *host_gpu_mmu_maps=nullptr;
    IOService *host_gpu_start_gpu=nullptr,*host_gpu_start_gmu=nullptr;
    IOMemoryDescriptor *host_gpu_start_gpu_resource=nullptr,*host_gpu_start_gmu_resource=nullptr;
    ZornGen7HostGpuCode26 *host_gpu_code=nullptr;bool host_gpu_code_ready=false,host_gpu_registers_attempted=false;
    ZornGen7HostGpuRegisters26 *host_gpu_registers=nullptr;bool host_gpu_registers_ready=false,host_gpu_irq_attempted=false;
    ZornGen7GpuIrq26 *host_gpu_irq=nullptr;bool host_gpu_irq_ready=false,host_cp_attempted=false,host_cp_init_idle=false;
    ZornGen7HostRing26 *host_ring=nullptr;
    IOMemoryDescriptor *direct_register_code=nullptr,*direct_cp_pool=nullptr;
    IOMemoryDescriptor *direct_zap_parent=nullptr,*direct_zap_metadata=nullptr;uint32_t direct_zap_epoch=0;
    uint32_t direct_oob_epoch=0;
    IOMemoryDescriptor *direct_task_image=nullptr;thread_t direct_task_thread=THREAD_NULL;
    bool direct_task_attempted=false,direct_task_granted=false,direct_task_release_allowed=false;
    // Identity only, not an owning reference. Ring retains the actual client
    // before grant and clears its owner before the successful final release.
    const void *direct_client_identity=nullptr;
    bool direct_client_attempted=false,direct_client_granted=false,direct_client_release_allowed=false;
    // Distinct application session. AppExecution retains the actual client,
    // opening task and this board before calling us; these are identity refs.
    IOUserClient *direct_app_identity=nullptr;task_t direct_app_task=TASK_NULL;
    bool direct_app_publish_attempted=false,direct_app_attempted=false,direct_app_granted=false;
    uint32_t direct_app_acquires=0,direct_app_releases=0;
    bool nativeApplicationWindowHeld(IOUserClient &client,task_t task,unsigned phase,ZornGen7AppOperation26 operation)
    {
        return normal() && IORecursiveLockHaveLock(gates.startup) && stage==Stage::CpuReady &&
            direct_app_publish_attempted && direct_app_granted && direct_app_identity==&client &&
            direct_app_task==task && task && task!=kernel_task && !direct_client_attempted &&
            direct_app_acquires==direct_app_releases+1 &&
            __atomic_load_n(&direct_oob_epoch,__ATOMIC_ACQUIRE)==6 && host_known_image_ready &&
            direct_task_release_allowed && host_direct_runtime_ready && host_direct_runtime_window_held && host_bootstrap_ready &&
            host_zap_authenticated && host_zap && host_ring && host_ring->nativeApplicationBinding(client,task,phase,operation) &&
            host_gpu_start_window_held && host_gpu_mmu_ready && host_gpu_oob_ready &&
            native_direct_memory_owner && native_cx_maps && native_cx_gpu && native_cx_gmu &&
            host_gpu_start_gpu==native_cx_gpu && host_gpu_start_gmu==native_cx_gmu &&
            host_gpu_start_gpu_resource && host_gpu_start_gmu_resource &&
            host_gpu_irq && !host_gpu_irq->halted() && gmu_irq && gmu_irq->forwardAllowed() &&
            direct_hfi && direct_hfi->healthy() && smmu_domains && !smmu_domains->faulted() &&
            rsc_storage && rsc_storage->forwardAllowed() && smmu_pm && smmu_power &&
            smmu_pm->nativeHeldFor(smmu_power->provider,*gates.startup) &&
            native_direct_memory_owner->gpuProviderClaimsHeld() &&
            native_cx_maps->hostGpuStartPairIs(*native_direct_memory_owner,*native_cx_gpu,
                *host_gpu_start_gpu_resource,*native_cx_gmu,*host_gpu_start_gmu_resource);
    }
    bool nativeClientWindowHeld(IOUserClient &client,unsigned phase)
    {
        return normal() && IORecursiveLockHaveLock(gates.startup) && stage==Stage::CpuReady &&
            direct_client_granted && direct_client_identity==&client &&
            __atomic_load_n(&direct_oob_epoch,__ATOMIC_ACQUIRE)==5 && host_known_image_ready &&
            direct_task_release_allowed && host_direct_runtime_ready && host_direct_runtime_window_held && host_bootstrap_ready &&
            host_zap_authenticated && host_zap && host_ring && host_ring->nativeKernelClientBinding(client,phase) &&
            host_gpu_start_window_held && host_gpu_mmu_ready && host_gpu_oob_ready &&
            native_direct_memory_owner && native_cx_maps && native_cx_gpu && native_cx_gmu &&
            host_gpu_start_gpu==native_cx_gpu && host_gpu_start_gmu==native_cx_gmu &&
            host_gpu_start_gpu_resource && host_gpu_start_gmu_resource &&
            host_gpu_irq && !host_gpu_irq->halted() && gmu_irq && gmu_irq->forwardAllowed() &&
            direct_hfi && direct_hfi->healthy() && smmu_domains && !smmu_domains->faulted() &&
            rsc_storage && rsc_storage->forwardAllowed() && smmu_pm && smmu_power &&
            smmu_pm->nativeHeldFor(smmu_power->provider,*gates.startup) &&
            native_direct_memory_owner->gpuProviderClaimsHeld() &&
            native_cx_maps->hostGpuStartPairIs(*native_direct_memory_owner,*native_cx_gpu,
                *host_gpu_start_gpu_resource,*native_cx_gmu,*host_gpu_start_gmu_resource);
    }
    bool nativeTaskWindowHeld(IOMemoryDescriptor &image,unsigned phase)
    {
        return normal() && IORecursiveLockHaveLock(gates.startup) && stage==Stage::StoppedRetained &&
            direct_task_granted && direct_task_image==&image && direct_task_thread==current_thread() &&
            __atomic_load_n(&direct_oob_epoch,__ATOMIC_ACQUIRE)==3 && host_known_image_attempted && !host_known_image_ready &&
            host_direct_runtime_ready && host_direct_runtime_window_held && host_bootstrap_ready &&
            host_zap_authenticated && host_zap && host_ring && host_ring->nativeKernelTaskBinding(image,phase) &&
            host_gpu_start_window_held && host_gpu_mmu_ready && host_gpu_oob_ready &&
            native_direct_memory_owner && native_cx_maps && native_cx_gpu && native_cx_gmu &&
            host_gpu_start_gpu==native_cx_gpu && host_gpu_start_gmu==native_cx_gmu &&
            host_gpu_start_gpu_resource && host_gpu_start_gmu_resource &&
            host_gpu_irq && !host_gpu_irq->halted() && gmu_irq && gmu_irq->forwardAllowed() &&
            direct_hfi && direct_hfi->healthy() && smmu_domains && !smmu_domains->faulted() &&
            rsc_storage && rsc_storage->forwardAllowed() && smmu_pm && smmu_power &&
            smmu_pm->nativeHeldFor(smmu_power->provider,*gates.startup) &&
            native_direct_memory_owner->gpuProviderClaimsHeld() &&
            native_cx_maps->hostGpuStartPairIs(*native_direct_memory_owner,*native_cx_gpu,
                *host_gpu_start_gpu_resource,*native_cx_gmu,*host_gpu_start_gmu_resource);
    }
    ZornGen7ZapOwner26 *host_zap=nullptr;bool host_zap_attempted=false,host_zap_authenticated=false,host_bootstrap_attempted=false,host_bootstrap_ready=false,host_direct_runtime_attempted=false,host_direct_runtime_ready=false,host_known_image_attempted=false,host_known_image_ready=false;
    ZornGen7HwschedHfi26 *host_hfi=nullptr;bool host_hfi_attempted=false,host_hfi_ready=false;
    bool host_irq_arm_attempted=false,host_irq_armed=false;
    bool host_gmu_start_attempted=false,host_first_query_ready=false;
    ZornGen7HwschedHfi26 *hwsched_hfi=nullptr;bool hwsched_hfi_attempted=false,hwsched_hfi_ready=false;bool direct_hfi_attempted=false,direct_hfi_ready=false;
    ZornGen7IccInputs26 *gpu_icc_inputs=nullptr;bool gpu_icc_inputs_attempted=false,gpu_icc_inputs_ready=false;
    bool gpu_icc_initial_attempted=false,gpu_icc_initial_ready=false,gpu_icc_qos_attempted=false,gpu_icc_qos_ready=false;
    bool gpu_bootstrap_bw_attempted=false,gpu_bootstrap_bw_ready=false;
    IORegistryEntry *native_cx_root=nullptr;
    IOService *native_cx_gpu=nullptr;
    IORegistryEntry *native_cx_scm=nullptr;
    ZornGen7RegisterMaps26 *native_cx_maps=nullptr;
    IOService *native_cx_gmu=nullptr;
    IOWorkLoop *native_gmu_irq_loop=nullptr;
    bool native_gmu_config_window=false;
    bool gmu_tcm_loaded_ready=false,cx_security_attempted=false,cx_security_ready=false;
    ZornGen7ScmOwner26 *cx_scm_owner=nullptr;
    ZornGen7ColdBoot::OperationResult cx_scm_result{ZornGen7ColdBoot::Disposition::Unavailable,
        ZornGen7ColdBoot::StatusDomain::Unavailable,0,0};
    bool cx_bcl_enabled_after_scm=false,cx_bcl_publication_valid=false;
    bool cx_timer_attempted=false,cx_timer_ready=false;
    bool gmu_ahb_attempted=false,gmu_ahb_ready=false;
    ZornGen7AhbControl::Result gmu_ahb_result{ZornGen7AhbControl::Assessment::InputUnavailable,0};
    bool cold_gmu_clocks_attempted=false,cold_gmu_clocks_ready=false;
    uint32_t cold_gmu_frequencies[2]{},cold_gmu_voltage_levels[2]{};
    // Native equivalent of gen7_gmu_rdpm_probe's missing named resource.
    // These cells are used only after actual GPU reg-names confirms absence.
    volatile void *cold_rdpm_cx_mapping=nullptr;volatile uint64_t cold_rdpm_cx_bytes=0;
    bool hwsched_irq_arm_attempted=false,hwsched_irq_armed=false;
    bool gmu_versions_attempted=false,gmu_versions_ready=false;
    bool pdc_rsc_attempted=false,pdc_rsc_ready=false;
    ZornGen7Clock::GmuClockEnable *cold_gmu_clocks=nullptr;
    ZornGen7Clock::GmuClockEnableResult cold_gmu_clock_result{};
    // Appended private source binding storage; prior owner-storage offsets stay fixed.
    ZornGen7Clock::NativeGmuPhysicalClockBindings *physical_clocks=nullptr;
    bool physical_attempted=false;
    ZornGen7Clock::NativeGpuccClockProbe *gpucc_probe=nullptr;bool gpucc_attempted=false;
    ZornGen7Clock::NativeGpuccProxyVote *gpucc_proxy=nullptr;bool gpucc_proxy_attempted=false;
    ZornGen7Rpmh::NativeVddRail *owned_clock_rails[4]{};
    ZornGen7Rpmh::NativeCoreConsumer *owned_clock_consumers[4]{};
    NativeClockRegulator *registered_clock_regulators=nullptr;
    NativeClockRegulatorConsumer *registered_clock_consumers[4]{};
    ZornGen7Rpmh::NativeOwnedArcSource *owned_arc_sources[3]{};
    bool arc_source_attempted=false;
    ZornGen7Rpmh::NativeOwnedArcCore *owned_arc_cores[3]{};
    ZornGen7Clock::ActualClockSupplierFields *owned_core_supplier_fields=nullptr;
    bool owned_core_attempted=false;
    IOLock *regulator_proxy_gate=nullptr;
    OwnedRegulatorProxyRecord *owned_regulator_proxies=nullptr,*live_regulator_proxies=nullptr;
    bool regulator_proxies_removed=false,regulator_proxy_attempted=false,regulator_proxies_returned=false;
    ZornGen7Rpmh::NativeOwnedArcCore *owned_sibling_cores[3][4]{};
    NativeClockRegulator *registered_sibling_regulators=nullptr;
    uint32_t completed_source_siblings[3]{};bool sibling_attempted=false;
    ZornGen7Rpmh::NativeOwnedArcSource *upstream_arc_sources[2]{};
    ZornGen7Rpmh::NativeOwnedArcCore *upstream_arc_cores[2]{};
    NativeClockRegulator *registered_upstream_regulators=nullptr;bool upstream_prefix_attempted=false;
    SupplyPending pending_supply{};
    bool supplied_core_attempted[5][4]{};
    OwnedSuppliedProxyRecord *owned_supplied_proxies=nullptr,*live_supplied_proxies=nullptr;
    bool mmcx_proxy_attempted=false,mmcx_proxy_returned=false;
    ZornGen7Rpmh::NativeOwnedArcCore *owned_mmcx_sibling_cores[3]{};
    bool mmcx_siblings_attempted=false,mmcx_siblings_returned=false;
    OwnedArcStartupFrame *arc_startup=nullptr;bool arc_startup_attempted=false;
    OSObject *clock_resources=nullptr;
    ZornGen7RegisterConfig::Region owned_gcc{},owned_gpucc{};
    OwnedBoardXo *board_xo=nullptr;
    bool board_xo_attempted=false;
    ZornGen7Clock::ClockCoreFactoryResult board_xo_result{};
    bool owned_clock_startup_attempted=false;
    ClockStartupResult owned_clock_startup{};
    ZornGen7RscRuntime26 *rsc_storage=nullptr;
    ZornGen7Rpmh::NativeCommandCache *rsc_cache=nullptr;
    ZornGen7Rpmh::NativeReservation *rsc_reservation=nullptr;
    OSObject *command_db_storage=nullptr;
    ZornGen7Rpmh::ActualXoCommandDbSnapshot owned_command_db{};
    ZornGen7CommandDbResources26 *command_db_reader=nullptr;
    OSObject *arc_native_nodes=nullptr;
    IOService *arc_parent_devices[5]{};
    IOService *clock_provider_devices[2]{};
    IOLock *owned_global_vdd_gate=nullptr;
    ZornGen7Clock::RegisteredClockRailResult owned_rail_result{};
    bool owned_rails_ready=false;
    OwnedNativeClockController *owned_controllers[2]{};
    bool owned_controller_fields_attempted=false,owned_controller_fields_ready=false;
    OwnedNativeClockController *owned_rpmh_controller=nullptr;
    OwnedNativeClockGraphInputs *owned_native_clock_graph=nullptr;
    bool native_clock_nodes_attempted=false,native_clock_nodes_ready=false;
    bool owned_gpucc_prefix_attempted=false;
    ZornGen7Clock::OwnedGpuccPrefixResult owned_gpucc_prefix{};
    NativeClockRegulatorConsumer *extra_gcc_consumers[2]{};
    ZornGen7Rpmh::NativeCoreConsumer *extra_gcc_core_consumers[2]{};
    ZornGen7Rpmh::NativeVddRail *extra_gcc_rails[2]{};
    ZornGen7Clock::NativeGmuPhysicalClockBindings::Class *extra_gcc_classes[2]{};
    ZornGen7Clock::RegisteredClockRailResult owned_gcc_rail_result{};
    bool owned_gcc_rails_attempted=false,owned_gcc_rails_ready=false;
    ZornGen7Clock::NativeGccGpuPrefix *gcc_gpu_prefix=nullptr;bool gcc_gpu_prefix_attempted=false;
    bool owned_native_graph_attempted=false;ZornGen7Clock::GmuClockGraphResult owned_native_graph{};
    OwnedGmuClockSoftwareState *owned_gmu_software=nullptr;
    bool owned_native_list_attempted=false;
    ZornGen7Clock::ClockConsumerListResult owned_native_list{};
    bool gen79_hub_metadata_attempted=false,gen79_hub_metadata_published=false;
    bool ddr_metadata_attempted=false,ddr_metadata_ready=false;
    IORegistryEntry *ddr_metadata_node=nullptr;OSObject *ddr_metadata_property=nullptr;
    volatile int32_t owned_ddr_type=0; // Unavailable until ddr_metadata_ready.
    const ZornGen7ColdBoot::ActualGen79InitFields *owned_gen79_core_inputs=nullptr;
    bool gen79_core_inputs_attempted=false,gen79_core_inputs_ready=false;
    ZornGen7CxGdsc::NativeCxGdscProbe *cx_gdsc_probe=nullptr;
    bool cx_gdsc_probe_attempted=false;
    NativeClockRegulatorConsumer *cx_supply_consumer=nullptr;
    ZornGen7CxGdsc::RegisterEnable *cx_register_enable=nullptr;
    OwnedNativeCxCore *cx_core=nullptr;bool cx_core_attempted=false;
    IOLock *cx_dependent=nullptr;IORWLock *cx_notifier=nullptr;
    IOLock *cx_completion_gate=nullptr;ZornGen7CxGdsc::Completion *cx_completion=nullptr;
    bool cx_completion_attempted=false;
    ZornGen7CxGdsc::OwnedCompletionResult cx_completion_result{};
    const ZornGen7Clock::NativeClockFirmwareNode *smmu_clock_node=nullptr;
    OwnedSmmuPowerFrame *smmu_power=nullptr;bool smmu_power_attempted=false,smmu_power_ready=false;
    ZornGen7Clock::ControllerClockListResult smmu_clocks{};
    bool smmu_io_attempted=false,smmu_io_bound=false;
    ZornGen7SmmuRuntimePm26 *smmu_pm=nullptr;bool smmu_pm_attempted=false,smmu_pm_ready=false;
    ZornGen7SmmuDomain26 *smmu_domains=nullptr;bool smmu_domains_attempted=false,smmu_domains_ready=false;






    static void *operator new(size_t,void *p) noexcept {return p;}
};
OSDefineMetaClassAndStructors(ZornGen7DarwinBoardOwner,OSObject)
bool ZornGen7DarwinBoardOwner::normal()
{
    constexpr uint64_t mask=(uint64_t(1)<<6)|(uint64_t(1)<<7)|(uint64_t(1)<<8);
    return !(__builtin_arm_rsr64("DAIF")&mask);
}
bool ZornGen7DarwinBoardOwner::callable() const
{return storage_ && normal() && (!storage_->direct_hfi || !storage_->direct_hfi->halted()) && (!storage_->hwsched_hfi || !storage_->hwsched_hfi->halted()) && (!storage_->host_hfi || !storage_->host_hfi->halted()) && (!storage_->gmu_irq || !storage_->gmu_irq->halted()) && (!storage_->smmu_domains || !storage_->smmu_domains->faulted()) && (!storage_->rsc_storage || storage_->rsc_storage->forwardAllowed()) && storage_->gates.startup && storage_->gates.clock_prepare &&
    !IORecursiveLockHaveLock(storage_->gates.startup) && !IORecursiveLockHaveLock(storage_->gates.clock_prepare);}
void *ZornGen7DarwinBoardOwner::allocate(size_t bytes,size_t alignment)
{
    if(!storage_||!bytes||!alignment||(alignment&(alignment-1u))) return nullptr;
    const size_t a=alignment>alignof(Allocation)?alignment:alignof(Allocation);
    if(a-1u>SIZE_MAX-sizeof(Allocation)||bytes>SIZE_MAX-sizeof(Allocation)-(a-1u)) return nullptr;
    const size_t total=sizeof(Allocation)+bytes+a-1u;void *base=IOMallocZero(total);if(!base)return nullptr;
    const uintptr_t address=reinterpret_cast<uintptr_t>(base);
    const uintptr_t header=(address+alignof(Allocation)-1u)&~uintptr_t(alignof(Allocation)-1u);
    auto *owned=reinterpret_cast<Allocation *>(header);owned->base=base;owned->bytes=total;
    owned->next=storage_->allocations;storage_->allocations=owned;
    return reinterpret_cast<void *>((header+sizeof(Allocation)+alignment-1u)&~uintptr_t(alignment-1u));
}
bool ZornGen7DarwinBoardOwner::retainDependency(OSObject &object)
{
    auto *d=static_cast<Dependency *>(allocate(sizeof(Dependency),alignof(Dependency)));if(!d)return false;
    object.retain();d->object=&object;d->next=storage_->dependencies;storage_->dependencies=d;return true;
}
IOReturn ZornGen7DarwinBoardOwner::create(IOService &platform,ZornGen7DarwinBoardOwner *&output)
{
    if(output||!normal()) return kIOReturnBadArgument;
    auto *owner=new ZornGen7DarwinBoardOwner;if(!owner)return kIOReturnNoMemory;
    if(!owner->init()) {owner->release();return kIOReturnNoMemory;}
    void *memory=IOMallocZero(sizeof(Storage));if(!memory){owner->release();return kIOReturnNoMemory;}
    owner->storage_=new(memory) Storage;auto &s=*owner->storage_;
    // The extra real reference precedes any platform or callback borrow. There
    // is no release API for this pin until an actual teardown is implemented.
    owner->retain();s.lifetime_pinned=true;output=owner;
    platform.retain();s.platform=&platform;
    auto &g=s.gates;g.startup=IORecursiveLockAlloc();g.clock_prepare=IORecursiveLockAlloc();
    g.clock_enable=IOSimpleLockAlloc();
    if(!g.startup||!g.clock_prepare||!g.clock_enable) {s.stage=Stage::StoppedRetained;return kIOReturnNoMemory;}
    auto *clock=owner->allocate(sizeof(ZornGen7Clock::NativeClockRoot),alignof(ZornGen7Clock::NativeClockRoot));
    if(!clock) {s.stage=Stage::StoppedRetained;return kIOReturnNoMemory;}
    s.clocks=::new(clock) ZornGen7Clock::NativeClockRoot(g.clock_prepare,g.clock_enable);
    s.stage=Stage::CpuReady;return kIOReturnSuccess;
}
const ZornGen7DarwinBoardOwner::CpuGates *ZornGen7DarwinBoardOwner::borrowCpuGates() const
{return storage_ && storage_->clocks?&storage_->gates:nullptr;}
const ZornGen7Clock::ActualClockParentFramework *ZornGen7DarwinBoardOwner::borrowCpuClockFramework() const
{return storage_ && storage_->clocks?&storage_->clocks->registry_.framework_:nullptr;}
ZornGen7Clock::ClockCoreFactoryResult ZornGen7DarwinBoardOwner::registerClock(ZornGen7Clock::NativeClockHardware &hw,OSObject &lifetime)
{
    if(!callable()||!storage_->clocks)return {};
    IORecursiveLockLock(storage_->gates.startup);
    if(storage_->stage!=Stage::CpuReady){IORecursiveLockUnlock(storage_->gates.startup);return {};}if(!retainDependency(lifetime)) {
        storage_->stage=Stage::StoppedRetained;ZornGen7Clock::ClockCoreFactoryResult failed{};
        failed.assessment=ZornGen7Clock::ClockCoreFactoryAssessment::AllocationRetained;
        IORecursiveLockUnlock(storage_->gates.startup);return failed;
    }
    const auto result=storage_->clocks->registerActual(hw,lifetime);
    if(!result.core_initialized)storage_->stage=Stage::StoppedRetained;
    IORecursiveLockUnlock(storage_->gates.startup);return result;
}
ZornGen7Clock::NativeClockRoot::NamespaceResult ZornGen7DarwinBoardOwner::publishClockProvider(
    const ZornGen7Clock::NativeClockFirmwareNode &node,ZornGen7Clock::NativeClockProviderKind kind,
    ZornGen7Clock::NativeClockHardware *const *hw,size_t count,OSObject &owner,
    ZornGen7Clock::NativeClockHardware *const *regmap,size_t regmap_count)
{
    if(!callable()||!storage_->clocks)return {};
    IORecursiveLockLock(storage_->gates.startup);
    if(storage_->stage!=Stage::CpuReady){IORecursiveLockUnlock(storage_->gates.startup);return {};}const auto result=storage_->clocks->publishFirmwareProvider(node,kind,hw,count,owner,regmap,regmap_count);
    if(result.record!=ZornGen7Clock::ClockNamespaceAssessment::RecordPublished || !result.orphan_scan_returned)storage_->stage=Stage::StoppedRetained;
    IORecursiveLockUnlock(storage_->gates.startup);return result;
}
ZornGen7Clock::ClockNamespaceAssessment ZornGen7DarwinBoardOwner::publishClkdev(const char *device,size_t dn,
    const char *connection,size_t cn,ZornGen7Clock::NativeClockHardware &hw,OSObject &owner)
{
    using A=ZornGen7Clock::ClockNamespaceAssessment;
    if(!callable()||!storage_->clocks)return A::InputUnavailable;
    IORecursiveLockLock(storage_->gates.startup);
    if(storage_->stage!=Stage::CpuReady){IORecursiveLockUnlock(storage_->gates.startup);return A::InputUnavailable;}const auto result=storage_->clocks->publishClkdev(device,dn,connection,cn,hw,owner);
    if(result!=A::RecordPublished)storage_->stage=Stage::StoppedRetained;
    IORecursiveLockUnlock(storage_->gates.startup);return result;
}
ZornGen7Clock::ClockConsumerListResult ZornGen7DarwinBoardOwner::constructGmuClockList(
    const ZornGen7Clock::NativeClockFirmwareConsumer &input,bool qdss,const volatile uint64_t *hub,
    volatile uint32_t *state,OSObject &fields_owner)
{
    using A=ZornGen7Clock::ClockConsumerListAssessment;
    if(!callable()||!storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady){IORecursiveLockUnlock(s.gates.startup);return {};}
    const auto result=s.clocks->buildGmuList(input,qdss,s.gates.startup,hub,state,fields_owner);
    if(result.assessment!=A::ListPublished)s.stage=Stage::StoppedRetained;
    IORecursiveLockUnlock(s.gates.startup);return result;
}
ZornGen7Clock::ClockConsumerListResult ZornGen7DarwinBoardOwner::constructStockGmuClockList(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode &soc,
    const ZornGen7Clock::NativeClockFirmwareNode &gpucc,const ZornGen7Clock::NativeClockFirmwareNode &gcc,
    bool qdss,const volatile uint64_t *hub,volatile uint32_t *state,OSObject &fields_owner)
{
    using A=ZornGen7Clock::ClockConsumerListAssessment;
    if(!callable()||!storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || s.clocks->initialFields()) {IORecursiveLockUnlock(s.gates.startup);return {};}
    s.stage=Stage::StoppedRetained;
    if(!ZornGen7StockGmuClock::matches(digest) || gpucc.parent!=&soc || gcc.parent!=&soc || gpucc.clock_cells!=1 || gcc.clock_cells!=1 ||
       !sourcePath(soc,"/soc",sizeof("/soc")) ||
       !sourcePath(gpucc,"/soc/clock-controller@3d90000",sizeof("/soc/clock-controller@3d90000")) ||
       !sourcePath(gcc,"/soc/clock-controller@100000",sizeof("/soc/clock-controller@100000"))) {
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    // Retain the actual native node/array lifetimes before storing any of their
    // references. No provider, HW, mapping or successful clock is constructed.
    if(!retainDependency(*soc.lifetime)||!retainDependency(*gpucc.lifetime)||!retainDependency(*gcc.lifetime)) {
        IORecursiveLockUnlock(s.gates.startup);return {A::NativeAllocationRefused,false,0,0};
    }
    void *memory=allocate(sizeof(StockGmuClockMetadata),alignof(StockGmuClockMetadata));
    if(!memory){IORecursiveLockUnlock(s.gates.startup);return {A::NativeAllocationRefused,false,0,0};}
    auto *metadata=new(memory) StockGmuClockMetadata(soc,gpucc,gcc,*this);
    const auto result=s.clocks->buildGmuList(metadata->consumer,qdss,s.gates.startup,hub,state,fields_owner);
    if(result.assessment==A::ListPublished)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return result;
}
ZornGen7Rpmh::OwnedArcStartupResult ZornGen7DarwinBoardOwner::initializeOwnedArcRegulatorSources(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode *const (&nodes)[5][4],
    IOService *const (&devices)[5][4],const ZornGen7Rpmh::ActualXoCommandDbSnapshot &snapshot,
    OSObject &snapshot_storage,ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation,
    OSObject &rsc_storage)
{return initializeArcSourcesFromInput(digest,nodes,devices,&snapshot,nullptr,snapshot_storage,cache,reservation,rsc_storage);}
ZornGen7Rpmh::OwnedArcStartupResult ZornGen7DarwinBoardOwner::initializeArcSourcesFromInput(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode *const (&nodes)[5][4],
    IOService *const (&devices)[5][4],const ZornGen7Rpmh::ActualXoCommandDbSnapshot *snapshot,
    ZornGen7Rpmh::NativeCommandDbResourceReader *reader,OSObject &snapshot_storage,
    ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation,OSObject &rsc_storage)
{
    if(bool(snapshot)==bool(reader))return {};
    using A=ZornGen7Rpmh::OwnedArcStartupStage;using C=ZornGen7Rpmh::OwnedCoreAssessment;
    using S=ZornGen7Rpmh::OwnedArcAssessment;using P=ZornGen7Rpmh::OwnedProxyAssessment;
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto refuse=[&]{IORecursiveLockUnlock(s.gates.startup);return ZornGen7Rpmh::OwnedArcStartupResult{};};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || s.arc_startup_attempted || s.arc_source_attempted ||
       s.owned_core_attempted || s.regulator_proxy_attempted || s.upstream_prefix_attempted || s.sibling_attempted ||
       s.registered_clock_regulators || !s.clocks || !ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest))return refuse();
    s.arc_startup_attempted=true;s.stage=Stage::StoppedRetained;
    void *memory=allocate(sizeof(OwnedArcStartupFrame),alignof(OwnedArcStartupFrame));
    if(!memory){IORecursiveLockUnlock(s.gates.startup);ZornGen7Rpmh::OwnedArcStartupResult out{};out.stage=A::NativeAllocationRetained;return out;}
    auto *frame=reader ? ::new(memory) OwnedArcStartupFrame(*reader,cache,reservation,snapshot_storage,rsc_storage) :
        ::new(memory) OwnedArcStartupFrame(*snapshot,cache,reservation,snapshot_storage,rsc_storage);s.arc_startup=frame;
    auto &f=*frame;auto &out=f.result;
    auto input_failed=[&]{IORecursiveLockUnlock(s.gates.startup);return out;};
    if(!retainDependency(snapshot_storage) || !retainDependency(rsc_storage)){out.stage=A::NativeAllocationRetained;return input_failed();}
    for(size_t i=0;i<32;++i)f.digest[i]=digest[i];
    // Copy only the exact admitted source rows. Unused array slots are never
    // consumed, and neither a software index nor the digest is an IO grant.
    for(size_t g=0;g<ZornGen7CoreSourceMetadata::group_count;++g) {
        const auto &first=ZornGen7CoreSourceMetadata::groups[g][0];
        if(!nodes[g][0] || !devices[g][0] || !nodes[g][0]->parent || !nodes[g][0]->parent->lifetime)return input_failed();
        const auto &parent=*nodes[g][0]->parent;
        size_t prefix=first.path_bytes-1u;while(prefix && first.path[prefix]!='/')--prefix;
        if(!prefix || !parent.full_name || parent.full_name_extent<prefix+1u || parent.full_name[prefix])return input_failed();
        for(size_t k=0;k<prefix;++k)if(parent.full_name[k]!=first.path[k])return input_failed();
        if(!retainDependency(*parent.lifetime)){out.stage=A::NativeAllocationRetained;return input_failed();}
        f.native_parents[g]=OSSharedPtr<IORegistryEntry>(devices[g][0]->copyParentEntry(gIOServicePlane),OSNoRetain);
        auto *parent_device=OSDynamicCast(IOService,f.native_parents[g].get());if(!parent_device)return input_failed();
        if(s.arc_native_nodes && s.arc_parent_devices[g]!=parent_device)return input_failed();
        for(size_t v=0;v<ZornGen7CoreSourceMetadata::counts[g];++v) {
            const auto &m=ZornGen7CoreSourceMetadata::groups[g][v];
            if(!nodes[g][v] || !devices[g][v] || nodes[g][v]->parent!=&parent || !sourcePath(*nodes[g][v],m.path,m.path_bytes))return input_failed();
            OSSharedPtr<IORegistryEntry> observed_parent(devices[g][v]->copyParentEntry(gIOServicePlane),OSNoRetain);
            if(observed_parent.get()!=parent_device)return input_failed();
            if(!retainDependency(*nodes[g][v]->lifetime) || !retainDependency(*devices[g][v])){out.stage=A::NativeAllocationRetained;return input_failed();}
            f.nodes[g][v]=nodes[g][v];f.devices[g][v]=devices[g][v];
        }
        if(g<3) {
            f.first_nodes[g]=f.nodes[g][0];f.first_devices[g]=f.devices[g][0];f.parents[g]=&parent;f.parent_devices[g]=parent_device;
            f.parent_name_storage[g]=OSSharedPtr<const OSSymbol>(parent_device->copyName(gIOServicePlane),OSNoRetain);
            if(!f.parent_name_storage[g])return input_failed();
            f.parent_names[g]={f.parent_name_storage[g]->getCStringNoCopy(),size_t(f.parent_name_storage[g]->getLength())+1u};
        } else {f.upstream_nodes[g-3u]=f.nodes[g][0];f.upstream_devices[g-3u]=f.devices[g][0];}
    }
    for(size_t i=0;i<3;++i){f.mmcx_nodes[i]=f.nodes[3][i];f.mmcx_devices[i]=f.devices[3][i];}
    out.actual_inputs_pinned=true;out.stage=A::InputsPinned;s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);
    auto stop=[&]{IORecursiveLockLock(s.gates.startup);s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);return out;};
    out.stage=A::FirstSources;out.sources=f.resourceRoute ? constructArcSourcesFromResourceReader(f.digest,*f.input.reader,f.snapshot_storage) :
        constructClockRegulatorArcSources(f.digest,f.input.snapshot,f.snapshot_storage);
    if(out.sources.last.assessment!=S::FirstVoterPrepared || out.sources.groups_prepared!=3)return stop();
    out.stage=A::FirstCores;out.first_cores=constructAndRegisterOwnedClockRegulatorCores(f.digest,f.first_nodes,f.first_devices);
    if(out.first_cores.last.assessment!=C::CoreFieldsPrepared || out.first_cores.cores_prepared!=3 || out.first_cores.native_records_registered!=3 ||
       out.first_cores.registration.assessment!=ZornGen7Clock::ClockRegulatorAssessment::Registered)return stop();
    out.stage=A::FirstProxies;out.first_proxies=applyOwnedClockRegulatorProxies(f.digest,f.parents,f.parent_devices,f.parent_names,f.cache,f.reservation,f.rsc_storage);
    if(out.first_proxies.proxies_registered!=3 || !out.first_proxies.last.source_return_available || out.first_proxies.last.source_return ||
       out.first_proxies.last.assessment!=P::SourceProxyForwardReturned)return stop();
    out.stage=A::UpstreamPrefixes;out.upstream=prepareOwnedRegulatorUpstreamPrefixes(f.digest,f.upstream_nodes,f.upstream_devices);
    if(out.upstream.source_groups_prepared!=2 || out.upstream.gfx_records_registered!=1 || out.upstream.gfx_core.assessment!=C::CoreFieldsPrepared ||
       !out.upstream.mmcx_core_requires_actual_supply)return stop();
    const ZornGen7Clock::NativeClockFirmwareNode *ordinary_nodes[3][4]{};IOService *ordinary_devices[3][4]{};
    for(size_t g=0;g<3;++g)for(size_t v=0;v<ZornGen7CoreSourceMetadata::counts[g];++v){ordinary_nodes[g][v]=f.nodes[g][v];ordinary_devices[g][v]=f.devices[g][v];}
    out.stage=A::OrdinarySiblings;out.ordinary_siblings=continueOwnedClockRegulatorSiblings(f.digest,ordinary_nodes,ordinary_devices);
    // This is the exact internal pre-mutation dependency frontier, not an
    // errno or failed native request. It is visited once and never retried.
    if(out.ordinary_siblings.assessment!=C::NeedsActualSupply || out.ordinary_siblings.group!=2 || out.ordinary_siblings.voter!=2 ||
       out.ordinary_siblings.siblings_registered!=4)return stop();
    IORecursiveLockLock(s.gates.startup);
    const bool pending=s.pending_supply.present && s.pending_supply.group==2 && s.pending_supply.voter==2;
    IORecursiveLockUnlock(s.gates.startup);if(!pending)return stop();
    out.stage=A::MmcxSuppliedCore;out.mmcx_core=prepareOwnedSuppliedArcCore(f.digest,*f.nodes[3][0],*f.devices[3][0],*f.nodes[0][2],f.cache,f.reservation,f.rsc_storage);
    if(out.mmcx_core.core.assessment!=C::CoreFieldsPrepared || !out.mmcx_core.supply_consumer_acquired || !out.mmcx_core.core_registered || !out.mmcx_core.proxy_still_required)return stop();
    out.stage=A::MmcxProxy;out.mmcx_proxy=applyOwnedMmcxRegulatorProxy(f.digest,*f.nodes[3][0]->parent,
        *OSDynamicCast(IOService,f.native_parents[3].get()),f.cache,f.reservation,f.rsc_storage);
    if(!out.mmcx_proxy.proxy.source_return_available || out.mmcx_proxy.proxy.source_return || !out.mmcx_proxy.proxy_list_published ||
       !out.mmcx_proxy.consumer_acquired || out.mmcx_proxy.proxy.assessment!=P::SourceProxyForwardReturned)return stop();
    out.stage=A::MmcxSiblings;out.mmcx_siblings=continueOwnedMmcxRegulatorSiblings(f.digest,f.mmcx_nodes,f.mmcx_devices);
    if(out.mmcx_siblings.assessment!=C::CoreFieldsPrepared || out.mmcx_siblings.siblings_registered!=2)return stop();
    out.stage=A::MxcMmcxVoter;out.mxc_supplied[0]=prepareOwnedSuppliedArcCore(f.digest,*f.nodes[2][2],*f.devices[2][2],*f.nodes[3][0],f.cache,f.reservation,f.rsc_storage);
    if(out.mxc_supplied[0].core.assessment!=C::CoreFieldsPrepared || !out.mxc_supplied[0].supply_consumer_acquired || !out.mxc_supplied[0].core_registered || out.mxc_supplied[0].proxy_still_required)return stop();
    out.stage=A::MxcGfxVoter;out.mxc_supplied[1]=prepareOwnedSuppliedArcCore(f.digest,*f.nodes[2][3],*f.devices[2][3],*f.nodes[4][0],f.cache,f.reservation,f.rsc_storage);
    if(out.mxc_supplied[1].core.assessment!=C::CoreFieldsPrepared || !out.mxc_supplied[1].supply_consumer_acquired || !out.mxc_supplied[1].core_registered || out.mxc_supplied[1].proxy_still_required)return stop();
    IORecursiveLockLock(s.gates.startup);
    bool complete=s.stage==Stage::CpuReady && !s.pending_supply.present && s.regulator_proxies_returned && s.mmcx_proxy_returned && s.mmcx_siblings_returned;
    for(size_t g=0;g<5;++g) {
        auto *source=g<3?s.owned_arc_sources[g]:s.upstream_arc_sources[g-3u];
        if(!source || source->result_.voters_initialized!=ZornGen7CoreSourceMetadata::counts[g])complete=false;
    }
    if(complete){out.stage=A::SourceForwardReturned;out.source_forward_returned=true;}
    else s.stage=Stage::StoppedRetained;
    IORecursiveLockUnlock(s.gates.startup);return out;
}
ZornGen7Rpmh::OwnedArcSourcesResult ZornGen7DarwinBoardOwner::constructClockRegulatorArcSources(
    const uint8_t (&digest)[32],const ZornGen7Rpmh::ActualXoCommandDbSnapshot &snapshot,OSObject &snapshot_owner)
{return constructArcSourcesFromInput(digest,&snapshot,nullptr,snapshot_owner);}
ZornGen7Rpmh::OwnedArcSourcesResult ZornGen7DarwinBoardOwner::constructArcSourcesFromResourceReader(
    const uint8_t (&digest)[32],ZornGen7Rpmh::NativeCommandDbResourceReader &reader,OSObject &owner)
{return constructArcSourcesFromInput(digest,nullptr,&reader,owner);}
ZornGen7Rpmh::OwnedArcSourcesResult ZornGen7DarwinBoardOwner::constructArcSourcesFromInput(
    const uint8_t (&digest)[32],const ZornGen7Rpmh::ActualXoCommandDbSnapshot *snapshot,
    ZornGen7Rpmh::NativeCommandDbResourceReader *reader,OSObject &snapshot_owner)
{
    using A=ZornGen7Rpmh::OwnedArcAssessment;
    ZornGen7Rpmh::OwnedArcSourcesResult result{};
    if(!callable() || !storage_->clocks || bool(snapshot)==bool(reader))return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&] {IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || s.arc_source_attempted)return finish();
    s.arc_source_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest))return finish();
    if(!retainDependency(snapshot_owner)){result.last.assessment=A::NativeAllocationRetained;return finish();}
    for(size_t i=0;i<3;++i) {
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcSource),alignof(ZornGen7Rpmh::NativeOwnedArcSource));
        if(!memory){result.last.assessment=A::NativeAllocationRetained;return finish();}
        IOLock *gate=IOLockAlloc();
        // Actual native lock allocation belongs to the persistent source object
        // before a bind can retain partial decode or initialized voter fields.
        s.owned_arc_sources[i]=reader ? ::new(memory) ZornGen7Rpmh::NativeOwnedArcSource(*reader,gate,i) :
            ::new(memory) ZornGen7Rpmh::NativeOwnedArcSource(*snapshot,gate,i);
        if(!gate){result.last.assessment=A::NativeAllocationRetained;return finish();}
        result.last=s.owned_arc_sources[i]->bindActualSource(s.gates.startup);
        if(result.last.assessment!=A::SourceArrayPrepared)return finish();
        result.last=s.owned_arc_sources[i]->initializeFirstActualVoter(s.gates.startup);
        if(result.last.assessment!=A::FirstVoterPrepared)return finish();
        ++result.groups_prepared;
    }
    s.stage=Stage::CpuReady;return finish();
}
ZornGen7Rpmh::OwnedArcCoresResult ZornGen7DarwinBoardOwner::constructAndRegisterOwnedClockRegulatorCores(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode *const (&nodes)[3],
    IOService *const (&devices)[3])
{
    using A=ZornGen7Rpmh::OwnedCoreAssessment;using R=ZornGen7Clock::ClockRegulatorAssessment;
    ZornGen7Rpmh::OwnedArcCoresResult result{};
    if(!callable())return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&] {IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || s.owned_core_attempted || s.registered_clock_regulators)return finish();
    s.owned_core_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest))return finish();
    for(size_t i=0;i<3;++i) {
        if(!nodes[i] || !devices[i] || !sourcePath(*nodes[i],ZornGen7ClockSupplierSource::supplier_paths[i],
           ZornGen7ClockSupplierSource::supplier_path_bytes[i]) || !s.owned_arc_sources[i] ||
           s.owned_arc_sources[i]->result_.assessment!=ZornGen7Rpmh::OwnedArcAssessment::FirstVoterPrepared)return finish();
        if(!retainDependency(*nodes[i]->lifetime) || !retainDependency(*devices[i])) {
            result.last.assessment=A::NativeAllocationRetained;return finish();
        }
    }
    void *fields=allocate(3u*sizeof(ZornGen7Clock::ActualClockSupplierFields),alignof(ZornGen7Clock::ActualClockSupplierFields));
    if(!fields){result.last.assessment=A::NativeAllocationRetained;return finish();}
    s.owned_core_supplier_fields=static_cast<ZornGen7Clock::ActualClockSupplierFields *>(fields);
    for(size_t i=0;i<3;++i) {
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcCore),alignof(ZornGen7Rpmh::NativeOwnedArcCore));
        if(!memory){result.last.assessment=A::NativeAllocationRetained;return finish();}
        IOLock *dependent=IOLockAlloc();IORWLock *notifier=IORWLockAlloc();
        s.owned_arc_cores[i]=::new(memory) ZornGen7Rpmh::NativeOwnedArcCore(*s.owned_arc_sources[i],dependent,notifier);
        if(!dependent || !notifier){result.last.assessment=A::NativeAllocationRetained;return finish();}
        result.last=s.owned_arc_cores[i]->prepareFirstActualCore(s.gates.startup);
        if(result.last.assessment!=A::CoreFieldsPrepared)return finish();
        ::new(&s.owned_core_supplier_fields[i]) ZornGen7Clock::ActualClockSupplierFields(s.owned_arc_cores[i]->supplier_);
        ++result.cores_prepared;
    }
    // Existing entry owns its gate. Drop it before those real CPU registrations;
    // this is no multi-device transaction or successful platform-probe claim.
    s.stage=Stage::CpuReady;IORecursiveLockUnlock(s.gates.startup);
    for(size_t i=0;i<3;++i) {
        auto &core=*s.owned_arc_cores[i];
        const ZornGen7Clock::ActualClockRegulatorRegistration in{*nodes[i],*devices[i],s.owned_core_supplier_fields[i],
            &core.consumers_,&core.open_count_,&core.exclusive_,*this};
        result.registration=registerClockRegulator(digest,in);
        if(result.registration.assessment!=R::Registered) {
            IORecursiveLockLock(s.gates.startup);s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);return result;
        }
        ++result.native_records_registered;
    }
    // Source regulator-proxy/debug/device-add/module/PM dependencies are NOT
    // replaced by registration in this private namespace. No later voter or
    // rail/GPUCC action is dispatched by this prefix.
    return result;
}
ZornGen7Rpmh::OwnedProxyBatchResult ZornGen7DarwinBoardOwner::applyOwnedClockRegulatorProxies(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode *const (&parents)[3],
    IOService *const (&devices)[3],const ZornGen7Clock::NativeClockRegistrationName (&names)[3],
    ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation,OSObject &rsc_owner)
{
    using A=ZornGen7Rpmh::OwnedProxyAssessment;
    ZornGen7Rpmh::OwnedProxyBatchResult batch{};
    if(!callable())return batch;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto refuse=[&]{IORecursiveLockUnlock(s.gates.startup);return batch;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || s.regulator_proxy_attempted || !s.owned_core_supplier_fields)return refuse();
    s.regulator_proxy_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest))return refuse();
    for(size_t i=0;i<3;++i) {
        const auto &meta=ZornGen7ProxySourceMetadata::proxies[i];
        if(!parents[i] || !devices[i] || !actualDeviceName(names[i]) ||
           !sourcePath(*parents[i],meta.parent,meta.parent_bytes) || !s.owned_arc_cores[i] ||
           s.owned_arc_cores[i]->result_.assessment!=ZornGen7Rpmh::OwnedCoreAssessment::CoreFieldsPrepared)return refuse();
        if(!retainDependency(*parents[i]->lifetime) || !retainDependency(*devices[i])) {
            batch.last.assessment=A::NativeAllocationRetained;return refuse();
        }
    }
    if(!retainDependency(rsc_owner)){batch.last.assessment=A::NativeAllocationRetained;return refuse();}
    s.regulator_proxy_gate=IOLockAlloc();
    if(!s.regulator_proxy_gate){batch.last.assessment=A::NativeAllocationRetained;return refuse();}
    // No startup->proxy lock edge is held across the lower operations. Native
    // RSC completion uses its own sender/IRQ lock and validates workloop context.
    IORecursiveLockUnlock(s.gates.startup);IOLockLock(s.regulator_proxy_gate);
    auto finish=[&]{IOLockUnlock(s.regulator_proxy_gate);return batch;};
    if(s.regulator_proxies_removed) {
        batch.last.assessment=A::ForwardErrorRetained;batch.last.source_return_available=true;batch.last.source_return=-1;return finish();
    }
    for(size_t i=0;i<3;++i) {
        IORecursiveLockLock(s.gates.startup);
        auto prepare_failed=[&]{IORecursiveLockUnlock(s.gates.startup);return finish();};
        const auto &meta=ZornGen7ProxySourceMetadata::proxies[i];NativeClockRegulator *supplier=nullptr;
        for(auto *p=s.registered_clock_regulators;p;p=p->next)if(p->source_index==i)supplier=p;
        if(!supplier || supplier->fields!=&s.owned_core_supplier_fields[i] ||
           supplier->node->parent!=parents[i])return prepare_failed();
        for(size_t j=0;j<32;++j)if(supplier->digest[j]!=digest[j])return prepare_failed();
        // Exact source parent proxy-supply maps to the first admitted native
        // child node. Resolve THIS real registry entry and retain both devices.
        if(!retainDependency(*supplier->device) || !retainDependency(*supplier->node->lifetime)) {
            batch.last.assessment=A::NativeAllocationRetained;return prepare_failed();
        }
        auto &core=*s.owned_arc_cores[i];IOLockLock(core.dependent_);
        auto get_error=[&](int32_t raw){batch.last.assessment=A::ForwardErrorRetained;
            batch.last.source_return_available=true;batch.last.source_return=raw;};
        if(core.exclusive_){get_error(-1);IOLockUnlock(core.dependent_);return prepare_failed();}
        if(core.n_resolved_!=core.n_coupled_){get_error(-517);IOLockUnlock(core.dependent_);return prepare_failed();}
        if(core.has_supply_ || core.valid_ops_!=9u){IOLockUnlock(core.dependent_);return prepare_failed();}
        void *record_memory=allocate(sizeof(OwnedRegulatorProxyRecord),alignof(OwnedRegulatorProxyRecord));
        if(!record_memory){batch.last.assessment=A::NativeAllocationRetained;IOLockUnlock(core.dependent_);return prepare_failed();}
        auto *record=::new(record_memory) OwnedRegulatorProxyRecord{};
        record->owned_next=s.owned_regulator_proxies;s.owned_regulator_proxies=record;
        auto &consumer=record->consumer;consumer.supplier=supplier;consumer.device=devices[i];
        size_t length=0;while(length<names[i].extent && names[i].bytes[length])++length;
        // Same create_regulator REG_STR_SIZE64 name check; source overflow is
        // its NULL/-ENOMEM path, not a fabricated IOMalloc failure observation.
        if(length>=sizeof(consumer.supply_name) || sizeof("proxy")>sizeof(consumer.supply_name)-length-1u) {
            get_error(-12);IOLockUnlock(core.dependent_);return prepare_failed();
        }
        for(size_t j=0;j<length;++j)consumer.supply_name[j]=names[i].bytes[j];consumer.supply_name[length]='-';
        const char id[]="proxy";for(size_t j=0;j<sizeof(id);++j)consumer.supply_name[length+1+j]=id[j];
        // Fresh native consumer's min/max/load/enable/always_on are genuine
        // zero fields. Actual mask9 includes CHANGE_STATUS, so create_regulator
        // performs no conditional always_on getter for this exact source path.
        consumer.projection.next=core.consumers_;core.consumers_=&consumer.projection;core.open_count_+=1u;
        ++batch.consumers_acquired;IOLockUnlock(core.dependent_);
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedRegulatorProxy),alignof(ZornGen7Rpmh::NativeOwnedRegulatorProxy));
        if(!memory){batch.last.assessment=A::NativeAllocationRetained;return prepare_failed();}
        const auto &fields=*supplier->fields;
        record->operation=::new(memory) ZornGen7Rpmh::NativeOwnedRegulatorProxy(fields,consumer.projection,cache,reservation,
            s.gates.startup,s.regulator_proxy_gate,meta.min_value,meta.max_value,meta.enable);
        // The owner record, source core consumer and persistent IRQ operation
        // are all published before the startup gate is dropped and any issue.
        IORecursiveLockUnlock(s.gates.startup);
        batch.last=record->operation->applyActualHeldProxyGate(s.regulator_proxy_gate);
        if(!batch.last.source_return_available || batch.last.source_return)return finish();
        record->live_next=s.live_regulator_proxies;s.live_regulator_proxies=record;
        ++batch.proxies_registered;
    }
    IORecursiveLockLock(s.gates.startup);s.regulator_proxies_returned=true;s.stage=Stage::CpuReady;IORecursiveLockUnlock(s.gates.startup);
    return finish();
}
ZornGen7Rpmh::OwnedSiblingResult ZornGen7DarwinBoardOwner::continueOwnedClockRegulatorSiblings(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode *const (&nodes)[3][4],
    IOService *const (&devices)[3][4])
{
    using A=ZornGen7Rpmh::OwnedCoreAssessment;
    ZornGen7Rpmh::OwnedSiblingResult result{};
    if(!callable())return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&]{IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || s.sibling_attempted || !s.regulator_proxies_returned ||
       !ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest))return finish();
    s.sibling_attempted=true;s.stage=Stage::StoppedRetained;
    // Derive prior completion from the actual same-owner first proxy path.
    // No caller-supplied ACK/registration-success flag advances a source voter.
    for(size_t i=0;i<3;++i) {
        if(!s.owned_arc_sources[i] || !s.owned_arc_cores[i] ||
           s.owned_arc_cores[i]->result_.assessment!=A::CoreFieldsPrepared ||
           s.owned_arc_sources[i]->result_.voters_initialized!=1 ||
           s.owned_arc_sources[i]->voter_count_!=int32_t(ZornGen7CoreSourceMetadata::counts[i]))return finish();
        s.completed_source_siblings[i]=1;
    }
    for(size_t i=0;i<3;++i)for(size_t j=1;j<ZornGen7CoreSourceMetadata::counts[i];++j) {
        result.group=uint32_t(i);result.voter=uint32_t(j);
        const auto &meta=ZornGen7CoreSourceMetadata::groups[i][j];auto *source=s.owned_arc_sources[i];
        NativeClockRegulator *first=nullptr;
        for(auto *p=s.registered_clock_regulators;p;p=p->next)if(p->source_index==i)first=p;
        if(!first || first->fields!=&s.owned_core_supplier_fields[i] || !first->node || !first->node->parent)return finish();
        if(!nodes[i][j] || !devices[i][j] || !sourcePath(*nodes[i][j],meta.path,meta.path_bytes) ||
           nodes[i][j]->parent!=first->node->parent || s.completed_source_siblings[i]!=j || meta.has_proxy)return finish();
        // Exact source path is known. Real upstream native provider/supply
        // resolution is not: refuse before mutating this next voter. This is
        // unavailable qualification, never a guessed ENODEV/EPROBE_DEFER/0.
        if(meta.upstream){s.pending_supply={uint32_t(i),uint32_t(j),true};result.assessment=A::NeedsActualSupply;return finish();}
        if(!retainDependency(*nodes[i][j]->lifetime) || !retainDependency(*devices[i][j])) {
            result.assessment=A::NativeAllocationRetained;return finish();
        }
        result.source=source->initializeNextActualVoter(s.gates.startup,j);
        if(result.source.assessment!=ZornGen7Rpmh::OwnedArcAssessment::LaterVoterPrepared)return finish();
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcCore),alignof(ZornGen7Rpmh::NativeOwnedArcCore));
        if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
        IOLock *dependent=IOLockAlloc();IORWLock *notifier=IORWLockAlloc();
        s.owned_sibling_cores[i][j]=::new(memory) ZornGen7Rpmh::NativeOwnedArcCore(*source,dependent,notifier,j);
        if(!dependent || !notifier){result.assessment=A::NativeAllocationRetained;return finish();}
        auto &core=*s.owned_sibling_cores[i][j];result.core=core.prepareActualCore(s.gates.startup);
        if(result.core.assessment!=A::CoreFieldsPrepared)return finish();
        // Separate actual native sibling membership keeps the first-only clock
        // routes unchanged. A future generic supply resolver must search both
        // namespaces by actual node identity, not treat this count as a lease.
        memory=allocate(sizeof(NativeClockRegulator),alignof(NativeClockRegulator));
        if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
        auto *record=::new(memory) NativeClockRegulator{};
        record->fields=&core.supplier_;record->node=nodes[i][j];record->device=devices[i][j];
        record->head=&core.consumers_;record->open_count=&core.open_count_;record->exclusive=&core.exclusive_;record->source_index=uint32_t(i);
        for(size_t k=0;k<32;++k)record->digest[k]=digest[k];
        record->next=s.registered_sibling_regulators;s.registered_sibling_regulators=record;
        // The exact later nodes have no proxy properties, so their helper has
        // no voltage/enable work. This private lifetime record is not a Linux
        // devres/device_add/debug-registration return or successful platform probe.
        ++s.completed_source_siblings[i];++result.siblings_registered;
    }
    result.assessment=A::CoreFieldsPrepared;s.stage=Stage::CpuReady;return finish();
}
ZornGen7Rpmh::OwnedUpstreamPrefixesResult ZornGen7DarwinBoardOwner::prepareOwnedRegulatorUpstreamPrefixes(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode *const (&nodes)[2],
    IOService *const (&devices)[2])
{
    using A=ZornGen7Rpmh::OwnedArcAssessment;using C=ZornGen7Rpmh::OwnedCoreAssessment;
    ZornGen7Rpmh::OwnedUpstreamPrefixesResult result{};
    if(!callable())return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&]{IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || s.upstream_prefix_attempted || !s.owned_arc_sources[0] ||
       !ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest))return finish();
    s.upstream_prefix_attempted=true;s.stage=Stage::StoppedRetained;
    for(size_t i=0;i<2;++i) {
        const size_t group=i+3u;const auto &meta=ZornGen7CoreSourceMetadata::groups[group][0];
        if(!nodes[i] || !devices[i] || !sourcePath(*nodes[i],meta.path,meta.path_bytes))return finish();
        if(!retainDependency(*nodes[i]->lifetime) || !retainDependency(*devices[i])) {
            result.source.assessment=A::NativeAllocationRetained;return finish();
        }
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcSource),alignof(ZornGen7Rpmh::NativeOwnedArcSource));
        if(!memory){result.source.assessment=A::NativeAllocationRetained;return finish();}
        IOLock *gate=IOLockAlloc();
        // Reuse the SAME already-pinned actual snapshot/version/scratch domain,
        // not a host fixture, auxiliary success object or source-derived address.
        auto &origin=*s.owned_arc_sources[0];
        s.upstream_arc_sources[i]=origin.resource_route_ ?
            ::new(memory) ZornGen7Rpmh::NativeOwnedArcSource(*origin.input_.reader,gate,group) :
            ::new(memory) ZornGen7Rpmh::NativeOwnedArcSource(origin.input_.snapshot,gate,group);
        if(!gate){result.source.assessment=A::NativeAllocationRetained;return finish();}
        result.source=s.upstream_arc_sources[i]->bindActualSource(s.gates.startup);
        if(result.source.assessment!=A::SourceArrayPrepared)return finish();
        result.source=s.upstream_arc_sources[i]->initializeFirstActualVoter(s.gates.startup);
        if(result.source.assessment!=A::FirstVoterPrepared)return finish();
        ++result.source_groups_prepared;
        if(meta.upstream) {
            // MMCX -> actual CX mmcx-sup node is a required live supply path.
            // Prepare its source input prefix, but do not create a pretend
            // resolved core, private provider or successful proxy/whole probe.
            result.mmcx_core_requires_actual_supply=true;continue;
        }
        if(meta.has_proxy)return finish(); // GFX's observed property absence only.
        memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcCore),alignof(ZornGen7Rpmh::NativeOwnedArcCore));
        if(!memory){result.gfx_core.assessment=C::NativeAllocationRetained;return finish();}
        IOLock *dependent=IOLockAlloc();IORWLock *notifier=IORWLockAlloc();
        s.upstream_arc_cores[i]=::new(memory) ZornGen7Rpmh::NativeOwnedArcCore(*s.upstream_arc_sources[i],dependent,notifier);
        if(!dependent || !notifier){result.gfx_core.assessment=C::NativeAllocationRetained;return finish();}
        auto &core=*s.upstream_arc_cores[i];result.gfx_core=core.prepareFirstActualCore(s.gates.startup);
        if(result.gfx_core.assessment!=C::CoreFieldsPrepared)return finish();
        memory=allocate(sizeof(NativeClockRegulator),alignof(NativeClockRegulator));
        if(!memory){result.gfx_core.assessment=C::NativeAllocationRetained;return finish();}
        auto *record=::new(memory) NativeClockRegulator{};
        record->fields=&core.supplier_;record->node=nodes[i];record->device=devices[i];record->source_index=uint32_t(group);
        record->head=&core.consumers_;record->open_count=&core.open_count_;record->exclusive=&core.exclusive_;
        for(size_t k=0;k<32;++k)record->digest[k]=digest[k];
        record->next=s.registered_upstream_regulators;s.registered_upstream_regulators=record;++result.gfx_records_registered;
    }
    // Requested CPU prefix is prepared. This is not MMCX supply resolution,
    // Linux driver binding/global PM/proxy completion or hardware readiness.
    s.stage=Stage::CpuReady;return finish();
}
ZornGen7Rpmh::OwnedSuppliedCoreResult ZornGen7DarwinBoardOwner::prepareOwnedSuppliedArcCore(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode &node,IOService &device,
    const ZornGen7Clock::NativeClockFirmwareNode &upstream_node,ZornGen7Rpmh::NativeCommandCache &cache,
    ZornGen7Rpmh::NativeReservation &reservation,OSObject &rsc_storage)
{
    using A=ZornGen7Rpmh::OwnedCoreAssessment;
    ZornGen7Rpmh::OwnedSuppliedCoreResult result{};
    if(!callable())return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&]{IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.physical_attempted || !ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest))return finish();
    size_t group=5,voter=0;
    for(size_t g=0;g<5;++g)for(size_t v=0;v<ZornGen7CoreSourceMetadata::counts[g];++v) {
        const auto &m=ZornGen7CoreSourceMetadata::groups[g][v];
        if(m.upstream && sourcePath(node,m.path,m.path_bytes)){group=g;voter=v;}
    }
    if(group==5 || s.supplied_core_attempted[group][voter])return finish();
    const auto &meta=ZornGen7CoreSourceMetadata::groups[group][voter];
    // Resume only an explicit source supply boundary, never a raw failed or
    // unobservable operation. MMCX is a prerequisite of the parked MXC voter.
    bool parked=s.stage==Stage::StoppedRetained && s.pending_supply.present;
    if(s.stage!=Stage::CpuReady && !(parked &&
       ((group==s.pending_supply.group && voter==s.pending_supply.voter) ||
        (group==3 && voter==0 && s.pending_supply.group==2 && s.pending_supply.voter==2))))return finish();
    if(!sourcePath(upstream_node,meta.upstream,__builtin_strlen(meta.upstream)+1u))return finish();
    NativeClockRegulator *upstream=nullptr;
    NativeClockRegulator *const lists[]={s.registered_clock_regulators,s.registered_sibling_regulators,s.registered_upstream_regulators};
    for(auto *head:lists)for(auto *p=head;p;p=p->next) {
        if(p->node==&node)return finish();
        if(p->node==&upstream_node){if(upstream)return finish();upstream=p;}
    }
    if(!upstream || !upstream->device || upstream->device==&device)return finish();
    ZornGen7Rpmh::NativeOwnedArcCore *supply=nullptr;
    for(size_t i=0;i<3;++i)if(s.owned_core_supplier_fields && upstream->fields==&s.owned_core_supplier_fields[i])supply=s.owned_arc_cores[i];
    auto match=[&](ZornGen7Rpmh::NativeOwnedArcCore *c){if(c && upstream->fields==&c->supplier_)supply=c;};
    for(auto &g:s.owned_sibling_cores)for(auto *c:g)match(c);
    for(auto *c:s.upstream_arc_cores)match(c);
    for(auto *c:s.owned_mmcx_sibling_cores)match(c);
    if(!supply || supply->result_.assessment!=A::CoreFieldsPrepared || upstream->head!=&supply->consumers_ ||
       upstream->open_count!=&supply->open_count_)return finish();
    for(size_t k=0;k<32;++k)if(upstream->digest[k]!=digest[k])return finish();
    // Genuine retained registry parent copies, not getProvider's borrowed
    // cached pointer and never an open/registered/matched/bound-success flag.
    // The copies establish identity/lifetime only, not an ongoing stop/power
    // lease. Actual external owner/attachment continuity remains mandatory.
    OSSharedPtr<IORegistryEntry> parent(device.copyParentEntry(gIOServicePlane),OSNoRetain);
    OSSharedPtr<IORegistryEntry> upstream_parent(upstream->device->copyParentEntry(gIOServicePlane),OSNoRetain);
    auto *parent_service=OSDynamicCast(IOService,parent.get());
    auto *upstream_service=OSDynamicCast(IOService,upstream_parent.get());
    if(!parent_service || !upstream_service ||
       (parent_service!=upstream_service &&
        (!s.arc_startup || s.arc_parent_devices[group]!=parent_service ||
         s.arc_startup->nodes[group][voter]!=&node || s.arc_startup->devices[group][voter]!=&device ||
         !actualArcParentBound(upstream->source_index,*upstream_service)))) {
        result.core.assessment=A::NeedsActualParentBinding;return finish();
    }
    auto *source=group==3?s.upstream_arc_sources[0]:s.owned_arc_sources[group];
    auto **slot=group==3?&s.upstream_arc_cores[0]:&s.owned_sibling_cores[group][voter];
    if(!source || *slot || (group!=3 && (group!=2 || s.completed_source_siblings[group]!=voter)))return finish();
    if(group==3 && (voter!=0 || source->result_.voters_initialized!=1))return finish();
    s.supplied_core_attempted[group][voter]=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(device) || !retainDependency(*parent_service) || !retainDependency(*upstream->device) ||
       !retainDependency(*node.lifetime) || !retainDependency(*upstream_node.lifetime) || !retainDependency(rsc_storage)) {
        result.core.assessment=A::NativeAllocationRetained;return finish();
    }
    // Native built-in code and the upstream core are already pinned by this
    // owner. No Linux try_module_get/device-link/sysfs/debugfs return is forged.
    if(group!=3) {
        auto initialized=source->initializeNextActualVoter(s.gates.startup,voter);
        if(initialized.assessment!=ZornGen7Rpmh::OwnedArcAssessment::LaterVoterPrepared)return finish();
    }
    void *memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcCore),alignof(ZornGen7Rpmh::NativeOwnedArcCore));
    if(!memory){result.core.assessment=A::NativeAllocationRetained;return finish();}
    IOLock *dependent=IOLockAlloc();IORWLock *notifier=IORWLockAlloc();
    auto *core=::new(memory) ZornGen7Rpmh::NativeOwnedArcCore(*source,dependent,notifier,voter);*slot=core;
    if(!dependent || !notifier){result.core.assessment=A::NativeAllocationRetained;return finish();}
    // The source create_regulator name is based on the ACTUAL device name,
    // not a synthesized regulator.N/ID. Keep its64B bound and originalENOMEM.
    OSSharedPtr<const OSSymbol> actual_name(device.copyName(gIOServicePlane),OSNoRetain);
    const char *name=actual_name?actual_name->getCStringNoCopy():nullptr;if(!name)return finish();
    size_t bytes=0;while(bytes<64 && name[bytes])++bytes;
    if(bytes>=64 || sizeof("SUPPLY")>64u-bytes-1u) {
        result.core.assessment=A::SourceErrorRetained;result.core.source_error_available=true;result.core.source_error=-12;return finish();
    }
    char *owned_name=static_cast<char *>(allocate(64,1));
    if(!owned_name){result.core.assessment=A::NativeAllocationRetained;return finish();}
    for(size_t i=0;i<bytes;++i)owned_name[i]=name[i];owned_name[bytes]='-';
    const char id[]="SUPPLY";for(size_t i=0;i<sizeof(id);++i)owned_name[bytes+1u+i]=id[i];
    IOLock *first=dependent,*second=supply->dependent_;
    if(reinterpret_cast<uintptr_t>(first)>reinterpret_cast<uintptr_t>(second)){auto *tmp=first;first=second;second=tmp;}
    IOLockLock(first);IOLockLock(second);
    if(supply->valid_ops_!=9u || core->has_supply_ || core->supply_) {
        IOLockUnlock(second);IOLockUnlock(first);return finish();
    }
    // Exact same-owner set_supply: actual embedded upstream consumer/list and
    // source unsigned open_count. Actual mask9 skips conditional always_on
    // getter in create_regulator; fresh consumer values remain genuine zeros.
    core->supply_consumer_.next=supply->consumers_;supply->consumers_=&core->supply_consumer_;
    supply->open_count_+=1u;core->supply_=supply;core->has_supply_=true;core->supply_ops_=supply->valid_ops_;core->supply_name_=owned_name;
    result.supply_consumer_acquired=true;
    IOLockUnlock(second);IOLockUnlock(first);
    result.core=core->prepareActualCore(s.gates.startup);
    if(result.core.assessment==A::NeedsActualMachineSupplyEnable) {
        memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcEnable),alignof(ZornGen7Rpmh::NativeOwnedArcEnable));
        if(!memory){result.core.assessment=A::NativeAllocationRetained;return finish();}
        auto *operation=::new(memory) ZornGen7Rpmh::NativeOwnedArcEnable(*supply,core->supply_consumer_,cache,reservation,s.gates.startup);
        if(!operation->prepareActualHeldStartup())return finish();
        IORecursiveLockUnlock(s.gates.startup);result.upstream_enable=operation->enableActual();IORecursiveLockLock(s.gates.startup);
        if(!result.upstream_enable.source_return_available || result.upstream_enable.source_return) {
            // Approved retained-failure variant keeps the supply consumer and
            // all resources. Linux _regulator_put/error cleanup is not run.
            if(result.upstream_enable.source_return_available) {
                result.core.assessment=A::SourceErrorRetained;result.core.source_error_available=true;
                result.core.source_error=result.upstream_enable.source_return;
            }
            return finish();
        }
        result.core=core->completeActualSupplyMachineConstraints(s.gates.startup,*operation);
    }
    if(result.core.assessment!=A::CoreFieldsPrepared)return finish();
    memory=allocate(sizeof(NativeClockRegulator),alignof(NativeClockRegulator));
    if(!memory){result.core.assessment=A::NativeAllocationRetained;return finish();}
    auto *record=::new(memory) NativeClockRegulator{};
    record->fields=&core->supplier_;record->node=&node;record->device=&device;record->source_index=uint32_t(group);
    record->head=&core->consumers_;record->open_count=&core->open_count_;record->exclusive=&core->exclusive_;
    for(size_t i=0;i<32;++i)record->digest[i]=digest[i];
    if(group==3){record->next=s.registered_upstream_regulators;s.registered_upstream_regulators=record;}
    else {record->next=s.registered_sibling_regulators;s.registered_sibling_regulators=record;++s.completed_source_siblings[group];
        if(voter+1u<ZornGen7CoreSourceMetadata::counts[group])s.pending_supply={uint32_t(group),uint32_t(voter+1u),true};
        else s.pending_supply.present=false;}
    result.core_registered=true;result.proxy_still_required=meta.has_proxy;s.stage=Stage::CpuReady;return finish();
}
ZornGen7Rpmh::OwnedSuppliedProxyResult ZornGen7DarwinBoardOwner::applyOwnedMmcxRegulatorProxy(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode &parent,IOService &parent_device,
    ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation,OSObject &rsc_storage)
{
    using A=ZornGen7Rpmh::OwnedProxyAssessment;namespace Meta=ZornGen7MmcxProxySourceMetadata;
    ZornGen7Rpmh::OwnedSuppliedProxyResult result{};
    if(!callable())return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto early=[&]{IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || s.mmcx_proxy_attempted || !s.regulator_proxy_gate ||
       !s.regulator_proxies_returned || !ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest) ||
       !sourcePath(parent,Meta::parent,sizeof(Meta::parent)))return early();
    auto *core=s.upstream_arc_cores[0];NativeClockRegulator *supplier=nullptr;
    for(auto *p=s.registered_upstream_regulators;p;p=p->next)if(core && p->fields==&core->supplier_) {
        if(supplier)return early();supplier=p;
    }
    if(!supplier || !supplier->node || supplier->node->parent!=&parent || !supplier->device ||
       !sourcePath(*supplier->node,Meta::supplier,sizeof(Meta::supplier)) ||
       core->result_.assessment!=ZornGen7Rpmh::OwnedCoreAssessment::CoreFieldsPrepared || !core->supply_ || !core->has_supply_)return early();
    for(size_t i=0;i<32;++i)if(supplier->digest[i]!=digest[i])return early();
    OSSharedPtr<IORegistryEntry> actual_parent(supplier->device->copyParentEntry(gIOServicePlane),OSNoRetain);
    if(actual_parent.get()!=&parent_device)return early();
    if(!retainDependency(parent_device) || !retainDependency(*parent.lifetime) ||
       !retainDependency(*supplier->device) || !retainDependency(*supplier->node->lifetime) || !retainDependency(rsc_storage)) {
        result.proxy.assessment=A::NativeAllocationRetained;return early();
    }
    s.mmcx_proxy_attempted=true;s.stage=Stage::StoppedRetained;
    IORecursiveLockUnlock(s.gates.startup);IOLockLock(s.regulator_proxy_gate);
    auto finish=[&]{IOLockUnlock(s.regulator_proxy_gate);return result;};
    auto error=[&](int32_t raw){result.proxy.assessment=A::ForwardErrorRetained;
        result.proxy.source_return_available=true;result.proxy.source_return=raw;};
    if(s.regulator_proxies_removed){error(-1);return finish();}
    IORecursiveLockLock(s.gates.startup);
    auto prepare_failed=[&]{IORecursiveLockUnlock(s.gates.startup);return finish();};
    IOLockLock(core->dependent_);
    if(core->exclusive_){error(-1);IOLockUnlock(core->dependent_);return prepare_failed();}
    if(core->n_resolved_!=core->n_coupled_){error(-517);IOLockUnlock(core->dependent_);return prepare_failed();}
    if(core->valid_ops_!=9u || !core->has_supply_ || !core->supply_) {IOLockUnlock(core->dependent_);return prepare_failed();}
    void *memory=allocate(sizeof(OwnedSuppliedProxyRecord),alignof(OwnedSuppliedProxyRecord));
    if(!memory){result.proxy.assessment=A::NativeAllocationRetained;IOLockUnlock(core->dependent_);return prepare_failed();}
    auto *record=::new(memory) OwnedSuppliedProxyRecord{};
    record->owned_next=s.owned_supplied_proxies;s.owned_supplied_proxies=record;
    auto &consumer=record->consumer;consumer.supplier=supplier;consumer.device=&parent_device;
    OSSharedPtr<const OSSymbol> actual_name(parent_device.copyName(gIOServicePlane),OSNoRetain);
    const char *name=actual_name?actual_name->getCStringNoCopy():nullptr;
    if(!name){IOLockUnlock(core->dependent_);return prepare_failed();}
    size_t bytes=0;while(bytes<sizeof(consumer.supply_name) && name[bytes])++bytes;
    const char id[]="proxy";
    if(bytes>=sizeof(consumer.supply_name) || sizeof(id)>sizeof(consumer.supply_name)-bytes-1u) {
        error(-12);IOLockUnlock(core->dependent_);return prepare_failed();
    }
    for(size_t i=0;i<bytes;++i)consumer.supply_name[i]=name[i];consumer.supply_name[bytes]='-';
    for(size_t i=0;i<sizeof(id);++i)consumer.supply_name[bytes+1u+i]=id[i];
    // Normal-get on the actual already resolved owned MMCX core. Mask9
    // preserves the source no-always_on-getter branch for a fresh consumer.
    consumer.projection.next=core->consumers_;core->consumers_=&consumer.projection;core->open_count_+=1u;
    result.consumer_acquired=true;IOLockUnlock(core->dependent_);
    memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedSuppliedRegulatorProxy),alignof(ZornGen7Rpmh::NativeOwnedSuppliedRegulatorProxy));
    if(!memory){result.proxy.assessment=A::NativeAllocationRetained;return prepare_failed();}
    record->operation=::new(memory) ZornGen7Rpmh::NativeOwnedSuppliedRegulatorProxy(*core,consumer.projection,
        cache,reservation,s.gates.startup,s.regulator_proxy_gate,Meta::min_value,Meta::max_value,Meta::enable);
    if(!record->operation->prepareActualHeldStartup())return prepare_failed();
    // All frames, consumer state and real dependencies are retained before any
    // issue. Completion paths can progress without the startup gate held.
    IORecursiveLockUnlock(s.gates.startup);
    result=record->operation->applyActualHeldProxyGate(s.regulator_proxy_gate);result.consumer_acquired=true;
    if(!result.proxy.source_return_available || result.proxy.source_return)return finish();
    IORecursiveLockLock(s.gates.startup);
    record->live_next=s.live_supplied_proxies;s.live_supplied_proxies=record;result.proxy_list_published=true;
    s.mmcx_proxy_returned=true;s.stage=Stage::CpuReady;IORecursiveLockUnlock(s.gates.startup);return finish();
}
ZornGen7Rpmh::OwnedSiblingResult ZornGen7DarwinBoardOwner::continueOwnedMmcxRegulatorSiblings(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode *const (&nodes)[3],
    IOService *const (&devices)[3])
{
    using A=ZornGen7Rpmh::OwnedCoreAssessment;
    ZornGen7Rpmh::OwnedSiblingResult result{};result.group=3;
    if(!callable())return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&]{IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || s.mmcx_siblings_attempted || !s.mmcx_proxy_returned ||
       !ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest))return finish();
    auto *source=s.upstream_arc_sources[0];auto *first_core=s.upstream_arc_cores[0];NativeClockRegulator *first=nullptr;
    for(auto *p=s.registered_upstream_regulators;p;p=p->next)if(first_core && p->fields==&first_core->supplier_)first=p;
    if(!source || !first || !nodes[0] || !devices[0] || first->node!=nodes[0] || first->device!=devices[0] ||
       first_core->result_.assessment!=A::CoreFieldsPrepared || source->result_.voters_initialized!=1 || source->voter_count_!=3)return finish();
    s.mmcx_siblings_attempted=true;s.stage=Stage::StoppedRetained;
    for(size_t j=1;j<ZornGen7CoreSourceMetadata::counts[3];++j) {
        result.voter=uint32_t(j);const auto &meta=ZornGen7CoreSourceMetadata::groups[3][j];
        if(!nodes[j] || !devices[j] || !sourcePath(*nodes[j],meta.path,meta.path_bytes) ||
           nodes[j]->parent!=first->node->parent || meta.upstream || meta.has_proxy || s.owned_mmcx_sibling_cores[j])return finish();
        if(!retainDependency(*nodes[j]->lifetime) || !retainDependency(*devices[j])) {
            result.assessment=A::NativeAllocationRetained;return finish();
        }
        result.source=source->initializeNextActualVoter(s.gates.startup,j);
        if(result.source.assessment!=ZornGen7Rpmh::OwnedArcAssessment::LaterVoterPrepared)return finish();
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcCore),alignof(ZornGen7Rpmh::NativeOwnedArcCore));
        if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
        IOLock *dependent=IOLockAlloc();IORWLock *notifier=IORWLockAlloc();
        auto *core=::new(memory) ZornGen7Rpmh::NativeOwnedArcCore(*source,dependent,notifier,j);s.owned_mmcx_sibling_cores[j]=core;
        if(!dependent || !notifier){result.assessment=A::NativeAllocationRetained;return finish();}
        result.core=core->prepareActualCore(s.gates.startup);
        if(result.core.assessment!=A::CoreFieldsPrepared)return finish();
        memory=allocate(sizeof(NativeClockRegulator),alignof(NativeClockRegulator));
        if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
        auto *record=::new(memory) NativeClockRegulator{};
        record->fields=&core->supplier_;record->node=nodes[j];record->device=devices[j];record->source_index=3;
        record->head=&core->consumers_;record->open_count=&core->open_count_;record->exclusive=&core->exclusive_;
        for(size_t i=0;i<32;++i)record->digest[i]=digest[i];
        record->next=s.registered_upstream_regulators;s.registered_upstream_regulators=record;++result.siblings_registered;
    }
    // Exact later nodes have neither supply nor proxy. This advances their
    // actual source CPU fields/private namespace, not Linux device_add/probe,
    // PM sync_state, parent driver binding or a hardware-ready observation.
    result.assessment=A::CoreFieldsPrepared;s.mmcx_siblings_returned=true;s.stage=Stage::CpuReady;return finish();
}
ZornGen7Rpmh::OwnedSupplyEnableResult ZornGen7DarwinBoardOwner::enableOwnedArcConsumer(
    const ZornGen7Clock::NativeClockFirmwareNode &node,ZornGen7Rpmh::NativeCoreConsumer &consumer,
    ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation,OSObject &rsc_storage)
{
    using A=ZornGen7Rpmh::OwnedSupplyEnableAssessment;
    ZornGen7Rpmh::OwnedSupplyEnableResult result{};
    if(!callable())return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&]{IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted)return finish();
    // Identity is the real registered native node, never a path/group number.
    NativeClockRegulator *record=nullptr;
    NativeClockRegulator *const lists[]={s.registered_clock_regulators,s.registered_sibling_regulators,s.registered_upstream_regulators};
    for(auto *head:lists)for(auto *p=head;p;p=p->next)if(p->node==&node) {
        if(record)return finish();record=p;
    }
    if(!record)return finish();
    ZornGen7Rpmh::NativeOwnedArcCore *core=nullptr;
    auto match=[&](ZornGen7Rpmh::NativeOwnedArcCore *candidate){
        if(candidate && &candidate->supplier_==record->fields)core=candidate;
    };
    for(size_t i=0;i<3;++i)if(s.owned_core_supplier_fields && record->fields==&s.owned_core_supplier_fields[i])core=s.owned_arc_cores[i];
    for(auto &group:s.owned_sibling_cores)for(auto *candidate:group)match(candidate);
    for(auto *candidate:s.upstream_arc_cores)match(candidate);
    for(auto *candidate:s.owned_mmcx_sibling_cores)match(candidate);
    if(!core || record->head!=&core->consumers_ || record->open_count!=&core->open_count_)return finish();
    s.stage=Stage::StoppedRetained;
    if(!retainDependency(rsc_storage)) {result.assessment=A::NativeAllocationRetained;return finish();}
    void *memory=allocate(sizeof(ZornGen7Rpmh::NativeOwnedArcEnable),alignof(ZornGen7Rpmh::NativeOwnedArcEnable));
    if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
    auto *operation=::new(memory) ZornGen7Rpmh::NativeOwnedArcEnable(*core,consumer,cache,reservation,s.gates.startup);
    if(!operation->prepareActualHeldStartup()) {result=operation->result_;return finish();}
    // The allocation ledger retains every call frame before the startup gate
    // is dropped. No new get, fabricated supply or lifecycle flag is accepted.
    IORecursiveLockUnlock(s.gates.startup);
    result=operation->enableActual();
    IORecursiveLockLock(s.gates.startup);
    if(result.source_return_available && result.source_return==0)s.stage=Stage::CpuReady;
    return finish();
}
ZornGen7Clock::ClockRegulatorResult ZornGen7DarwinBoardOwner::registerClockRegulator(
    const uint8_t (&digest)[32],const ZornGen7Clock::ActualClockRegulatorRegistration &in)
{
    using A=ZornGen7Clock::ClockRegulatorAssessment;
    ZornGen7Clock::ClockRegulatorResult result{};
    if(!callable())return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&] {IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || !ZornGen7ClockSupplierSource::admits(digest))return finish();
    size_t index=3;
    for(size_t j=0;j<3;++j)if(sourcePath(in.node,ZornGen7ClockSupplierSource::supplier_paths[j],
        ZornGen7ClockSupplierSource::supplier_path_bytes[j]))index=j;
    const auto &v=in.fields.voltage;
    if(index==3 || !in.consumer_head || in.consumer_head!=v.consumers || !v.dependent_lock ||
       !v.n_coupled || !v.n_resolved || !v.has_supply || !v.valid_ops_mask || !in.open_count || !in.exclusive ||
       static_cast<const void *>(v.dependent_lock)==s.gates.startup)return finish();
    // No replacement or idempotent-success token: every source index and node
    // has a single real native registry member owned by this self-pinned board.
    for(auto *p=s.registered_clock_regulators;p;p=p->next)
        if(p->source_index==index || p->node==&in.node)return finish();
    if(!retainDependency(in.fields_lifetime) || !retainDependency(in.device) || !retainDependency(*in.node.lifetime)) {
        result.assessment=A::NativeAllocationRetained;s.stage=Stage::StoppedRetained;return finish();
    }
    auto *p=static_cast<NativeClockRegulator *>(allocate(sizeof(NativeClockRegulator),alignof(NativeClockRegulator)));
    if(!p){result.assessment=A::NativeAllocationRetained;s.stage=Stage::StoppedRetained;return finish();}
    p->fields=&in.fields;p->node=&in.node;p->device=&in.device;p->head=in.consumer_head;
    p->open_count=in.open_count;p->exclusive=in.exclusive;p->source_index=uint32_t(index);
    for(size_t j=0;j<32;++j)p->digest[j]=digest[j];
    p->next=s.registered_clock_regulators;s.registered_clock_regulators=p;
    result.assessment=A::Registered;return finish();
}
ZornGen7Clock::ClockRegulatorResult ZornGen7DarwinBoardOwner::acquireClockConsumerHeld(size_t i,
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode &node,
    const ZornGen7Clock::ActualClockSupplierFields &supplier,IOService &device,
    const ZornGen7Clock::NativeClockRegistrationName &name,IOLock &global_gate)
{
    using A=ZornGen7Clock::ClockRegulatorAssessment;ZornGen7Clock::ClockRegulatorResult out{};
    auto &s=*storage_;
    if(!IORecursiveLockHaveLock(s.gates.startup) || i>=6 || !actualDeviceName(name))return out;
    auto &registered=i<4?s.registered_clock_consumers[i]:s.extra_gcc_consumers[i-4];
    auto &owned=i<4?s.owned_clock_consumers[i]:s.extra_gcc_core_consumers[i-4];
    if(registered || owned)return out;
    const uint32_t index=i<4?ZornGen7ClockSupplierSource::supplier_for_rail[i]:ZornGen7GccSupplySource26::groups[i-4];
    const char *id=i<4?ZornGen7ClockSupplierSource::rail_ids[i]:ZornGen7GccSupplySource26::ids[i-4];
    const size_t id_bytes=i<4?ZornGen7ClockSupplierSource::rail_id_bytes[i]:ZornGen7GccSupplySource26::id_bytes[i-4];
    // Only GCC's CX-AO source comes from the actual registered sibling list;
    // its MXA name resolves to the normal MX core, never a new physical rail.
    auto *head=i==4?s.registered_sibling_regulators:s.registered_clock_regulators;
    NativeClockRegulator *p=nullptr;
    for(auto *r=head;r;r=r->next)if(r->node==&node && r->source_index==index)p=r;
    // A retained source node with no registered native device is the exact
    // DT lookup-deferred case, not an absent/dummy regulator success.
    auto error=[&](int32_t raw) {out.assessment=A::SourceGetErrorRetained;
        out.source_error_available=true;out.source_error=raw;};
    if(!p){error(-517);return out;}
    if(p->fields!=&supplier)return out;
    for(size_t j=0;j<32;++j)if(p->digest[j]!=digest[j])return out;
    const auto &rail=*p->fields;const auto &v=rail.voltage;const auto &a=rail.arc;
    if(!v.dependent_lock || !p->head || p->head!=v.consumers || !p->open_count || !p->exclusive ||
       !v.valid_ops_mask || !v.n_coupled || !v.n_resolved || !v.has_supply ||
       !a.aggregate_lock || a.aggregate_lock==v.dependent_lock || a.aggregate_lock==&global_gate ||
       v.dependent_lock==&global_gate || !rail.enable.has_enable_gpio)return out;
    // Actual device + fields + immutable node get independent references
    // BEFORE consumer construction; no module-get or device-link stub.
    if(!retainDependency(*p->device) || !retainDependency(*p->node->lifetime)) {
        out.assessment=A::NativeAllocationRetained;return out;
    }
    IOLockLock(v.dependent_lock);
    auto unlock=[&] {IOLockUnlock(v.dependent_lock);};
    if(*p->exclusive){error(-1);unlock();return out;}
    if(!*v.n_coupled){unlock();return out;}
    if(*v.n_resolved!=*v.n_coupled){error(-517);unlock();return out;}
    // Descriptor absence is insufficient if init_data overrides supply.
    // Actual live supply state remains authoritative; no recursive success.
    if(*v.has_supply){out.assessment=A::NeedsActualSupply;unlock();return out;}
    void *memory=allocate(sizeof(NativeClockRegulatorConsumer),alignof(NativeClockRegulatorConsumer));
    if(!memory){out.assessment=A::NativeAllocationRetained;unlock();return out;}
    auto *consumer=::new(memory) NativeClockRegulatorConsumer{};
    registered=consumer;consumer->supplier=p;consumer->device=&device;
    size_t n=0;
    while(n<name.extent && name.bytes[n])++n;
    // Exact create_regulator REG_STR_SIZE64 name admission, without logging.
    if(n>=sizeof(consumer->supply_name) || id_bytes>sizeof(consumer->supply_name)-n-1u) {
        error(-12);unlock();return out;
    }
    for(size_t j=0;j<n;++j)consumer->supply_name[j]=name.bytes[j];
    consumer->supply_name[n]='-';
    for(size_t j=0;j<id_bytes;++j)consumer->supply_name[n+1+j]=id[j];
    consumer->projection.next=*p->head;*p->head=&consumer->projection;
    bool always_on=false;
    if(!(*v.valid_ops_mask&8u)) {
        if(*rail.enable.has_enable_gpio) {
            if(!rail.enable.enable_gpio_state){unlock();return out;}
            always_on=*rail.enable.enable_gpio_state;
        } else {
            if(!a.level_count || *a.level_count<=0 || size_t(*a.level_count)>a.levels_capacity ||
               !a.levels || !a.voter_count || *a.voter_count<=0 || size_t(*a.voter_count)>a.voters_capacity || !a.voters) {
                unlock();return out;
            }
            bool member=false;for(int32_t j=0;j<*a.voter_count;++j)if(&a.voters[j]==&rail.voter)member=true;
            if(!member){unlock();return out;}
            if(a.levels[0]!=0)always_on=true; // Exact removed-is_enabled-op source assumption.
            else {IOLockLock(a.aggregate_lock);always_on=rail.voter.req.reg[1]!=0;IOLockUnlock(a.aggregate_lock);}
        }
    }
    consumer->always_on=always_on;
    *p->open_count=*p->open_count+1u; // Source unsigned arithmetic on actual live count.
    owned=&consumer->projection;
    ++out.consumers_acquired;unlock();
    out.assessment=A::NativeConsumerAcquired;return out;
}
ZornGen7Clock::OwnedClockRailResult ZornGen7DarwinBoardOwner::constructRegisteredRailsHeld(IOLock &global_gate,
    ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation)
{
    using R=ZornGen7Clock::OwnedClockRailAssessment;ZornGen7Clock::OwnedClockRailResult out{};
    auto &s=*storage_;if(!IORecursiveLockHaveLock(s.gates.startup))return out;
    for(size_t i=0;i<4;++i)if(!s.registered_clock_consumers[i] || !s.owned_clock_consumers[i] || s.owned_clock_rails[i])return out;
    for(size_t i=0;i<4;++i) {
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeVddRail),alignof(ZornGen7Rpmh::NativeVddRail));
        if(!memory){out.assessment=R::NativeAllocationRetained;return out;}
        const auto &rail=*s.registered_clock_consumers[i]->supplier->fields;
        s.owned_clock_rails[i]=::new(memory) ZornGen7Rpmh::NativeVddRail(&global_gate,rail.voltage,rail.enable,
            s.owned_clock_consumers[i],rail.arc,&rail.voter,cache,reservation,rail.notifiers,rail.normal_disable);
        ++out.rails_constructed;
    }
    out.assessment=R::FieldsConstructed;return out;
}
IOReturn ZornGen7DarwinBoardOwner::constructOwnedClockRails(const uint8_t (&digest)[32])
{
    using A=ZornGen7Clock::ClockRegulatorAssessment;using R=ZornGen7Clock::OwnedClockRailAssessment;
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || s.physical_attempted || !s.arc_startup || !s.arc_startup->result.source_forward_returned ||
       !s.clock_resources || !s.clock_provider_devices[0] || !s.clock_provider_devices[1] || !s.owned_core_supplier_fields ||
       !s.rsc_storage || !s.rsc_cache || !s.rsc_reservation || !ZornGen7ClockSupplierSource::admits(digest))return finish(kIOReturnNotReady);
    s.physical_attempted=true;s.stage=Stage::StoppedRetained;
    for(size_t g=0;g<3;++g)if(!s.arc_parent_devices[g] || !actualArcParentBound(g,*s.arc_parent_devices[g]))return finish(kIOReturnNotReady);
    s.owned_global_vdd_gate=IOLockAlloc();if(!s.owned_global_vdd_gate)return finish(kIOReturnNoMemory);
    OSSharedPtr<const OSSymbol> names[2];
    for(size_t p=0;p<2;++p) {
        names[p]=OSSharedPtr<const OSSymbol>(s.clock_provider_devices[p]->copyName(gIOServicePlane),OSNoRetain);
        if(!names[p])return finish(kIOReturnNotReady);
    }
    auto &out=s.owned_rail_result;
    for(size_t i=0;i<4;++i) {
        const auto index=ZornGen7ClockSupplierSource::supplier_for_rail[i];
        auto *node=s.arc_startup->nodes[index][0];auto *device=s.arc_startup->devices[index][0];
        if(!node || !device || !sourcePath(*node,ZornGen7ClockSupplierSource::supplier_paths[index],
            ZornGen7ClockSupplierSource::supplier_path_bytes[index]))return finish(kIOReturnNotReady);
        auto &consumer=*s.clock_provider_devices[i?1:0];
        // Resolve the actual native supply edge, rather than treating static
        // source paths/indices as a returned provider. Handles here are only
        // native DT identifiers and carry no physical/address/access rights.
        char key[32]{};const auto prefix=ZornGen7ClockSupplierSource::rail_id_bytes[i]-1u;
        constexpr char suffix[]="-supply";
        if(prefix+sizeof(suffix)>sizeof(key))return finish(kIOReturnBadArgument);
        for(size_t k=0;k<prefix;++k)key[k]=ZornGen7ClockSupplierSource::rail_ids[i][k];
        for(size_t k=0;k<sizeof(suffix);++k)key[prefix+k]=suffix[k];
        OSSharedPtr<OSObject> edge(consumer.copyProperty(key),OSNoRetain),handle(device->copyProperty("phandle"),OSNoRetain);
        auto *e=OSDynamicCast(OSData,edge.get()),*h=OSDynamicCast(OSData,handle.get());
        if(!e || !h || e->getLength()!=4 || h->getLength()!=4 || !e->getBytesNoCopy() || !h->getBytesNoCopy())return finish(kIOReturnNotReady);
        const auto *eb=static_cast<const uint8_t *>(e->getBytesNoCopy()),*hb=static_cast<const uint8_t *>(h->getBytesNoCopy());
        bool nonzero=false;for(size_t k=0;k<4;++k){if(eb[k]!=hb[k])return finish(kIOReturnNotReady);nonzero|=hb[k]!=0;}
        if(!nonzero)return finish(kIOReturnNotReady);
        const auto &name=names[i?1:0];
        ZornGen7Clock::NativeClockRegistrationName actual_name{name->getCStringNoCopy(),size_t(name->getLength())+1u};
        const auto prior=out.acquisition.consumers_acquired;
        out.acquisition=acquireClockConsumerHeld(i,digest,*node,s.owned_core_supplier_fields[index],consumer,
            actual_name,*s.owned_global_vdd_gate);out.acquisition.consumers_acquired+=prior;
        if(out.acquisition.assessment!=A::NativeConsumerAcquired)return finish(kIOReturnNotReady);
    }
    out.rails=constructRegisteredRailsHeld(*s.owned_global_vdd_gate,*s.rsc_cache,*s.rsc_reservation);
    if(out.rails.assessment!=R::FieldsConstructed || out.rails.rails_constructed!=4)return finish(kIOReturnNotReady);
    // This is the real consumer/open-count/rail CPU prefix. Controller PM/sync
    // metadata, physical clock registration and hardware operations remain a
    // subsequent forward stage, not synthetic successful fields or a retry.
    s.owned_rails_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::constructOwnedGccClockRails()
{
    using A=ZornGen7Clock::ClockRegulatorAssessment;
    using R=ZornGen7Clock::OwnedClockRailAssessment;
    using C=ZornGen7Rpmh::OwnedCoreAssessment;
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.native_clock_nodes_ready || !s.physical_clocks || !s.arc_startup ||
       !s.arc_startup->result.source_forward_returned || !s.owned_global_vdd_gate || !s.owned_core_supplier_fields ||
       !s.rsc_cache || !s.rsc_reservation || !s.owned_clock_rails[0] || s.owned_gcc_rails_attempted ||
       s.gpucc_attempted || s.clocks->graph_attempted_ || !s.owned_controllers[0])return finish(kIOReturnNotReady);
    s.owned_gcc_rails_attempted=true;s.stage=Stage::StoppedRetained;
    const auto &digest=s.arc_startup->digest;
    if(!ZornGen7GccSupplySource26::admits(digest))return finish(kIOReturnUnsupported);
    auto &gcc=*s.clock_provider_devices[0];const auto &name=s.owned_controllers[0]->name;
    if(!name || gcc.getState()!=0 || gcc.pm_vars)return finish(kIOReturnNotReady);
    for(size_t g=0;g<2;++g)if(!s.arc_parent_devices[g] || !actualArcParentBound(g,*s.arc_parent_devices[g]))return finish(kIOReturnNotReady);
    auto &out=s.owned_gcc_rail_result;
    for(size_t i=0;i<2;++i) {
        const auto group=ZornGen7GccSupplySource26::groups[i],voter=ZornGen7GccSupplySource26::voters[i];
        auto *core=voter?s.owned_sibling_cores[group][voter]:s.owned_arc_cores[group];
        auto *node=s.arc_startup->nodes[group][voter];auto *device=s.arc_startup->devices[group][voter];
        if(!core || core->result_.assessment!=C::CoreFieldsPrepared || !node || !device ||
           !sourcePath(*node,ZornGen7GccSupplySource26::paths[i],ZornGen7GccSupplySource26::path_bytes[i]))return finish(kIOReturnNotReady);
        const auto &supplier=voter?core->supplier_:s.owned_core_supplier_fields[group];
        char key[32]{};const auto prefix=ZornGen7GccSupplySource26::id_bytes[i]-1u;constexpr char suffix[]="-supply";
        if(prefix+sizeof(suffix)>sizeof(key))return finish(kIOReturnBadArgument);
        for(size_t k=0;k<prefix;++k)key[k]=ZornGen7GccSupplySource26::ids[i][k];
        for(size_t k=0;k<sizeof(suffix);++k)key[prefix+k]=suffix[k];
        OSSharedPtr<OSObject> edge(gcc.copyProperty(key),OSNoRetain),handle(device->copyProperty("phandle"),OSNoRetain);
        auto *e=OSDynamicCast(OSData,edge.get()),*h=OSDynamicCast(OSData,handle.get());
        if(!e || !h || e->getLength()!=4 || h->getLength()!=4 || !e->getBytesNoCopy() || !h->getBytesNoCopy())return finish(kIOReturnNotReady);
        const auto *eb=static_cast<const uint8_t *>(e->getBytesNoCopy()),*hb=static_cast<const uint8_t *>(h->getBytesNoCopy());
        bool nonzero=false;for(size_t k=0;k<4;++k){if(eb[k]!=hb[k])return finish(kIOReturnNotReady);nonzero|=hb[k]!=0;}
        if(!nonzero)return finish(kIOReturnNotReady);
        ZornGen7Clock::NativeClockRegistrationName actual_name{name->getCStringNoCopy(),size_t(name->getLength())+1u};
        const auto before=out.acquisition.consumers_acquired;
        out.acquisition=acquireClockConsumerHeld(i+4u,digest,*node,supplier,gcc,actual_name,*s.owned_global_vdd_gate);
        out.acquisition.consumers_acquired+=before;
        if(out.acquisition.assessment!=A::NativeConsumerAcquired)return finish(kIOReturnNotReady);
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeVddRail),alignof(ZornGen7Rpmh::NativeVddRail));
        if(!memory){out.rails.assessment=R::NativeAllocationRetained;return finish(kIOReturnNoMemory);}
        s.extra_gcc_rails[i]=::new(memory) ZornGen7Rpmh::NativeVddRail(s.owned_global_vdd_gate,supplier.voltage,supplier.enable,
            s.extra_gcc_core_consumers[i],supplier.arc,&supplier.voter,*s.rsc_cache,*s.rsc_reservation,supplier.notifiers,supplier.normal_disable);
        ++out.rails.rails_constructed;
        using Class=ZornGen7Clock::NativeGmuPhysicalClockBindings::Class;
        memory=allocate(sizeof(Class),alignof(Class));
        if(!memory){out.rails.assessment=R::NativeAllocationRetained;return finish(kIOReturnNoMemory);}
        s.extra_gcc_classes[i]=::new(memory) Class(s.owned_global_vdd_gate,*s.extra_gcc_rails[i]);
    }
    // Genuine consumer membership/open counts, retained rail fields and the
    // same source Class implementation only. No voltage/proxy/GCC operation
    // or UFS clock change is invoked by this CPU construction stage.
    if(!s.physical_clocks->bindAoClass(s.extra_gcc_classes[0]->vote))return finish(kIOReturnNotReady);
    out.rails.assessment=R::FieldsConstructed;s.owned_gcc_rails_ready=true;s.stage=Stage::CpuReady;
    return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::constructOwnedPhysicalClockFields()
{
    static_assert(sizeof(void *)==8,"This producer is the actual LP64 native PM representation");
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || !s.owned_rails_ready || !s.owned_global_vdd_gate || s.physical_clocks ||
       s.owned_controller_fields_attempted || !s.board_xo || !s.board_xo_result.core_initialized ||
       !s.command_db_storage || !s.rsc_cache || !s.rsc_reservation || !s.clock_resources)return finish(kIOReturnNotReady);
    s.owned_controller_fields_attempted=true;s.stage=Stage::StoppedRetained;
    for(size_t i=0;i<2;++i) {
        auto *provider=s.clock_provider_devices[i];
        if(!provider || provider->getState()!=0 || provider->pm_vars)return finish(kIOReturnUnsupported);
        void *memory=allocate(sizeof(OwnedNativeClockController),alignof(OwnedNativeClockController));
        if(!memory)return finish(kIOReturnNoMemory);
        // An actual implemented native sync callback, not a supplied success
        // flag. Its invocation waits for real downstream-consumer completion;
        // neither this constructor nor graph registration calls normal release.
        s.owned_controllers[i]=::new(memory) OwnedNativeClockController(*provider,
            &ZornGen7Clock::NativeClockRoot::syncProviderWithActualHeldGate);
        const auto &controller=*s.owned_controllers[i];
        if(controller.runtime_pm_enabled || !controller.name || !controller.provider_has_sync_state)return finish(kIOReturnNotReady);
    }
    for(size_t i=0;i<4;++i)if(!s.owned_clock_rails[i])return finish(kIOReturnNotReady);
    const auto &gcc=*s.owned_controllers[0],&gpucc=*s.owned_controllers[1];
    // RPMh clock-provider metadata remains explicitly unobserved here. It is
    // not consumed by the eighteen physical GCC/GPUCC fields. The full graph
    // still refuses until its genuine RPMh producer/node has been supplied.
    ZornGen7Clock::ActualGmuPhysicalClockInputs fields{s.board_xo->hardware,
        {{nullptr,0},{gcc.name->getCStringNoCopy(),size_t(gcc.name->getLength())+1u},
         {gpucc.name->getCStringNoCopy(),size_t(gpucc.name->getLength())+1u}},
        {{nullptr,nullptr},{&gcc.runtime_pm_enabled,&gcc.provider_has_sync_state},
         {&gpucc.runtime_pm_enabled,&gpucc.provider_has_sync_state}},
        s.owned_gcc,s.owned_gpucc,&gpucc.runtime_pm_enabled,*s.owned_global_vdd_gate,
        *s.owned_clock_rails[0],*s.owned_clock_rails[1],*s.owned_clock_rails[2],*s.owned_clock_rails[3],
        s.owned_command_db,*s.rsc_cache,*s.rsc_reservation,s.command_db_reader};
    void *memory=allocate(sizeof(ZornGen7Clock::NativeGmuPhysicalClockBindings),alignof(ZornGen7Clock::NativeGmuPhysicalClockBindings));
    if(!memory)return finish(kIOReturnNoMemory);
    s.physical_clocks=::new(memory) ZornGen7Clock::NativeGmuPhysicalClockBindings(fields,s.gates.clock_prepare);
    s.owned_controller_fields_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
ZornGen7Clock::RegisteredClockRailResult ZornGen7DarwinBoardOwner::constructClockRailsFromRegisteredRegulators(
    const ZornGen7Clock::ActualClockRailResources &in,
    const ZornGen7Clock::NativeClockFirmwareNode *const (&nodes)[3],
    IOService &gcc_consumer,IOService &gpucc_consumer,OSObject &fields_owner)
{
    using A=ZornGen7Clock::ClockRegulatorAssessment;using R=ZornGen7Clock::OwnedClockRailAssessment;
    using F=ZornGen7Clock::PhysicalClockBindingAssessment;
    ZornGen7Clock::RegisteredClockRailResult out{};
    if(!callable() || !storage_->clocks)return out;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&] {IORecursiveLockUnlock(s.gates.startup);return out;};
    if(!s.owned_gcc_rails_ready || !s.extra_gcc_classes[0] || s.owned_global_vdd_gate!=&in.global_vdd_gate || s.stage!=Stage::CpuReady || s.physical_attempted || s.clocks->initialFields())return finish();
    s.physical_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen7ClockSupplierSource::admits(in.source_digest) || !in.gpucc_regmap_device_pm ||
       !in.gcc.mapped || !in.gpucc.mapped || in.gcc.bytes<4 || in.gpucc.bytes<4 ||
       (reinterpret_cast<uintptr_t>(in.gcc.mapped)&3u) || (reinterpret_cast<uintptr_t>(in.gpucc.mapped)&3u))return finish();
    for(size_t i=0;i<3;++i)if(!actualDeviceName(in.device_names[i]) ||
        !in.controllers[i].runtime_pm_enabled || !in.controllers[i].provider_has_sync_state)return finish();
    // Missing registry membership can mean deferred only after an actual native
    // supplier node is supplied; immutable stock-source digest alone cannot.
    for(size_t i=0;i<3;++i)if(!nodes[i] || !sourcePath(*nodes[i],ZornGen7ClockSupplierSource::supplier_paths[i],
        ZornGen7ClockSupplierSource::supplier_path_bytes[i]))return finish();
    for(size_t i=0;i<3;++i)if(!retainDependency(*nodes[i]->lifetime)) {
        out.acquisition.assessment=A::NativeAllocationRetained;return finish();
    }
    if(!retainDependency(fields_owner) || !retainDependency(gcc_consumer) || !retainDependency(gpucc_consumer)){out.acquisition.assessment=A::NativeAllocationRetained;return finish();}
    for(size_t i=0;i<4;++i) {
        const auto index=ZornGen7ClockSupplierSource::supplier_for_rail[i];
        const auto prior=out.acquisition.consumers_acquired;
        out.acquisition=acquireClockConsumerHeld(i,in.source_digest,*nodes[index],in.suppliers[index],
            i?gpucc_consumer:gcc_consumer,in.device_names[i?2:1],in.global_vdd_gate);
        out.acquisition.consumers_acquired+=prior;
        if(out.acquisition.assessment!=A::NativeConsumerAcquired)return finish();
    }
    out.acquisition.assessment=A::NativeConsumerAcquired;
    out.rails=constructRegisteredRailsHeld(in.global_vdd_gate,in.rpmh_cache,in.rpmh_reservation);
    if(out.rails.assessment!=R::FieldsConstructed)return finish();
    ZornGen7Clock::ActualGmuPhysicalClockInputs fields{in.registered_xo_board,
        {in.device_names[0],in.device_names[1],in.device_names[2]},
        {in.controllers[0],in.controllers[1],in.controllers[2]},in.gcc,in.gpucc,in.gpucc_regmap_device_pm,in.global_vdd_gate,
        *s.owned_clock_rails[0],*s.owned_clock_rails[1],*s.owned_clock_rails[2],*s.owned_clock_rails[3],
        in.command_db,in.rpmh_cache,in.rpmh_reservation,in.command_db_reader};
    void *memory=allocate(sizeof(ZornGen7Clock::NativeGmuPhysicalClockBindings),alignof(ZornGen7Clock::NativeGmuPhysicalClockBindings));
    if(!memory){out.rails.assessment=R::NativeAllocationRetained;return finish();}
    s.physical_clocks=::new(memory) ZornGen7Clock::NativeGmuPhysicalClockBindings(fields,s.gates.clock_prepare);
    if(!s.physical_clocks->bindAoClass(s.extra_gcc_classes[0]->vote))return finish();
    out.rails.fields={F::FieldsConstructed,25,5,false};out.rails.assessment=R::FieldsConstructed;s.stage=Stage::CpuReady;
    return finish();
}
ZornGen7Clock::OwnedClockRailResult ZornGen7DarwinBoardOwner::constructClockConsumerProjectionsAndRails(
    const ZornGen7Clock::ActualClockRailResources &in,
    ZornGen7Rpmh::NativeCoreConsumer **const (&heads)[3],OSObject &fields_owner)
{
    using A=ZornGen7Clock::OwnedClockRailAssessment;using F=ZornGen7Clock::PhysicalClockBindingAssessment;
    ZornGen7Clock::OwnedClockRailResult result{};
    if(!callable() || !storage_->clocks)return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(!s.owned_gcc_rails_ready || !s.extra_gcc_classes[0] || s.owned_global_vdd_gate!=&in.global_vdd_gate || s.stage!=Stage::CpuReady || s.physical_attempted || s.clocks->initialFields()) {IORecursiveLockUnlock(s.gates.startup);return result;}
    s.physical_attempted=true;s.stage=Stage::StoppedRetained;
    auto finish=[&] {IORecursiveLockUnlock(s.gates.startup);return result;};
    if(!in.gpucc_regmap_device_pm || !in.gcc.mapped || !in.gpucc.mapped ||
       (reinterpret_cast<uintptr_t>(in.gcc.mapped)&3u) || (reinterpret_cast<uintptr_t>(in.gpucc.mapped)&3u) ||
       in.gcc.bytes<4 || in.gpucc.bytes<4)return finish();
    for(size_t i=0;i<3;++i)if(!actualDeviceName(in.device_names[i]) ||
       !in.controllers[i].runtime_pm_enabled || !in.controllers[i].provider_has_sync_state)return finish();
    if(!ZornGen7ClockSupplierSource::admits(in.source_digest))return finish();
    for(size_t i=0;i<3;++i) {
        const auto &rail=in.suppliers[i];const auto &v=rail.voltage;const auto &a=rail.arc;
        // Presence/lock-identity checks are not a fabricated regulator lookup,
        // ownership proof or lower operation. Values stay actual live borrows.
        if(!heads[i] || heads[i]!=v.consumers || !v.dependent_lock || !v.consumers || !v.valid_ops_mask || !v.constraint_min || !v.constraint_max ||
           !v.offset || !v.max_step || !v.n_coupled || !v.n_resolved || !v.has_custom_balancer || !v.has_supply ||
           !rail.enable.use_count || !a.aggregate_lock || !a.voters || !a.voter_count || !a.levels ||
           !a.level_count || !a.command_db_address || !a.always_wait_for_ack || !a.next_wait_for_ack ||
           !a.sleep_request_sent || !a.aggr_active || !a.aggr_sleep ||
           v.dependent_lock==&in.global_vdd_gate || a.aggregate_lock==&in.global_vdd_gate ||
           a.aggregate_lock==v.dependent_lock)return finish();
    }
    // Every actual input object is pinned BEFORE allocation/constructors can
    // retain a borrowed native consumer, voter, notifier or late request field.
    if(!retainDependency(fields_owner)) {result.assessment=A::NativeAllocationRetained;return finish();}
    for(size_t i=0;i<4;++i) {
        const uint32_t supplier=ZornGen7ClockSupplierSource::supplier_for_rail[i];
        auto *lock=in.suppliers[supplier].voltage.dependent_lock;
        IOLockLock(lock);
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeCoreConsumer),alignof(ZornGen7Rpmh::NativeCoreConsumer));
        if(!memory) {IOLockUnlock(lock);result.assessment=A::NativeAllocationRetained;return finish();}
        auto *consumer=::new(memory) ZornGen7Rpmh::NativeCoreConsumer{};
        s.owned_clock_consumers[i]=consumer;
        // Exact zero allocation of the consumed normal-get CPU fields and head
        // insertion under the real supplier dependency lock. No always_on
        // getter, successful regulator handle, module get or open_count made.
        consumer->next=*heads[supplier];*heads[supplier]=consumer;
        IOLockUnlock(lock);
    }
    for(size_t i=0;i<4;++i) {
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeVddRail),alignof(ZornGen7Rpmh::NativeVddRail));
        if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
        const auto &rail=in.suppliers[ZornGen7ClockSupplierSource::supplier_for_rail[i]];
        s.owned_clock_rails[i]=::new(memory) ZornGen7Rpmh::NativeVddRail(&in.global_vdd_gate,rail.voltage,rail.enable,
            s.owned_clock_consumers[i],rail.arc,&rail.voter,in.rpmh_cache,in.rpmh_reservation,rail.notifiers,rail.normal_disable);
        ++result.rails_constructed;
    }
    ZornGen7Clock::ActualGmuPhysicalClockInputs fields{in.registered_xo_board,
        {in.device_names[0],in.device_names[1],in.device_names[2]},
        {in.controllers[0],in.controllers[1],in.controllers[2]},in.gcc,in.gpucc,in.gpucc_regmap_device_pm,in.global_vdd_gate,
        *s.owned_clock_rails[0],*s.owned_clock_rails[1],*s.owned_clock_rails[2],*s.owned_clock_rails[3],
        in.command_db,in.rpmh_cache,in.rpmh_reservation,in.command_db_reader};
    void *memory=allocate(sizeof(ZornGen7Clock::NativeGmuPhysicalClockBindings),alignof(ZornGen7Clock::NativeGmuPhysicalClockBindings));
    if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
    s.physical_clocks=::new(memory) ZornGen7Clock::NativeGmuPhysicalClockBindings(fields,s.gates.clock_prepare);
    if(!s.physical_clocks->bindAoClass(s.extra_gcc_classes[0]->vote))return finish();
    result.fields={F::FieldsConstructed,25,5,false};result.assessment=A::FieldsConstructed;s.stage=Stage::CpuReady;
    return finish(); // Native CPU objects only; no regulator operation or controller/voltage success.
}
ZornGen7Clock::OwnedClockRailResult ZornGen7DarwinBoardOwner::constructPhysicalClockBindingsWithOwnedRails(
    const ZornGen7Clock::ActualOwnedClockRailInputs &in,OSObject &fields_owner)
{
    using A=ZornGen7Clock::OwnedClockRailAssessment;using F=ZornGen7Clock::PhysicalClockBindingAssessment;
    ZornGen7Clock::OwnedClockRailResult result{};
    if(!callable() || !storage_->clocks)return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(!s.owned_gcc_rails_ready || !s.extra_gcc_classes[0] || s.owned_global_vdd_gate!=&in.global_vdd_gate || s.stage!=Stage::CpuReady || s.physical_attempted || s.clocks->initialFields()) {IORecursiveLockUnlock(s.gates.startup);return result;}
    s.physical_attempted=true;s.stage=Stage::StoppedRetained;
    auto finish=[&] {IORecursiveLockUnlock(s.gates.startup);return result;};
    if(!in.gpucc_regmap_device_pm || !in.gcc.mapped || !in.gpucc.mapped ||
       (reinterpret_cast<uintptr_t>(in.gcc.mapped)&3u) || (reinterpret_cast<uintptr_t>(in.gpucc.mapped)&3u) ||
       in.gcc.bytes<4 || in.gpucc.bytes<4)return finish();
    for(size_t i=0;i<3;++i)if(!actualDeviceName(in.device_names[i]) ||
       !in.controllers[i].runtime_pm_enabled || !in.controllers[i].provider_has_sync_state)return finish();
    if(!ZornGen7ClockSupplierSource::admits(in.source_digest))return finish();
    for(size_t i=0;i<4;++i)if(!in.consumers[i])return finish();
    for(size_t i=0;i<3;++i) {
        const auto &rail=in.suppliers[i];const auto &v=rail.voltage;const auto &a=rail.arc;
        // Presence/lock-identity checks are not a fabricated regulator lookup,
        // ownership proof or lower operation. Values stay actual live borrows.
        if(!v.dependent_lock || !v.consumers || !v.valid_ops_mask || !v.constraint_min || !v.constraint_max ||
           !v.offset || !v.max_step || !v.n_coupled || !v.n_resolved || !v.has_custom_balancer || !v.has_supply ||
           !rail.enable.use_count || !a.aggregate_lock || !a.voters || !a.voter_count || !a.levels ||
           !a.level_count || !a.command_db_address || !a.always_wait_for_ack || !a.next_wait_for_ack ||
           !a.sleep_request_sent || !a.aggr_active || !a.aggr_sleep ||
           v.dependent_lock==&in.global_vdd_gate || a.aggregate_lock==&in.global_vdd_gate ||
           a.aggregate_lock==v.dependent_lock)return finish();
    }
    // Every actual input object is pinned BEFORE allocation/constructors can
    // retain a borrowed native consumer, voter, notifier or late request field.
    if(!retainDependency(fields_owner)) {result.assessment=A::NativeAllocationRetained;return finish();}
    for(size_t i=0;i<4;++i) {
        void *memory=allocate(sizeof(ZornGen7Rpmh::NativeVddRail),alignof(ZornGen7Rpmh::NativeVddRail));
        if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
        const auto &rail=in.suppliers[ZornGen7ClockSupplierSource::supplier_for_rail[i]];
        s.owned_clock_rails[i]=::new(memory) ZornGen7Rpmh::NativeVddRail(&in.global_vdd_gate,rail.voltage,rail.enable,
            in.consumers[i],rail.arc,&rail.voter,in.rpmh_cache,in.rpmh_reservation,rail.notifiers,rail.normal_disable);
        ++result.rails_constructed;
    }
    ZornGen7Clock::ActualGmuPhysicalClockInputs fields{in.registered_xo_board,
        {in.device_names[0],in.device_names[1],in.device_names[2]},
        {in.controllers[0],in.controllers[1],in.controllers[2]},in.gcc,in.gpucc,in.gpucc_regmap_device_pm,in.global_vdd_gate,
        *s.owned_clock_rails[0],*s.owned_clock_rails[1],*s.owned_clock_rails[2],*s.owned_clock_rails[3],
        in.command_db,in.rpmh_cache,in.rpmh_reservation,in.command_db_reader};
    void *memory=allocate(sizeof(ZornGen7Clock::NativeGmuPhysicalClockBindings),alignof(ZornGen7Clock::NativeGmuPhysicalClockBindings));
    if(!memory){result.assessment=A::NativeAllocationRetained;return finish();}
    s.physical_clocks=::new(memory) ZornGen7Clock::NativeGmuPhysicalClockBindings(fields,s.gates.clock_prepare);
    if(!s.physical_clocks->bindAoClass(s.extra_gcc_classes[0]->vote))return finish();
    result.fields={F::FieldsConstructed,25,5,false};result.assessment=A::FieldsConstructed;s.stage=Stage::CpuReady;
    return finish(); // Native CPU objects only; no regulator operation or controller/voltage success.
}
ZornGen7Clock::GccGpuPrefixResult ZornGen7DarwinBoardOwner::prepareGccGpuClockPrefix()
{
    using A=ZornGen7Clock::GccGpuPrefixAssessment;
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](ZornGen7Clock::GccGpuPrefixResult r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || !s.native_clock_nodes_ready || !s.owned_native_clock_graph ||
       !s.owned_gcc_rails_ready || !s.extra_gcc_classes[0] || !s.extra_gcc_classes[1] || !s.physical_clocks ||
       s.gcc_gpu_prefix_attempted || s.gpucc_attempted || s.clocks->graph_attempted_ || s.clocks->list_attempted_)return finish({});
    s.gcc_gpu_prefix_attempted=true;s.stage=Stage::StoppedRetained;
    // This route is the source-qualified private GPU closure, not the full
    // Linux controller. Actual retained access/exclusion remains mandatory.
    if(!s.arc_startup || !ZornGen7GccSupplySource26::admits(s.arc_startup->digest) ||
       s.clock_provider_devices[0]->getState()!=0 || s.clock_provider_devices[0]->pm_vars)return finish({});
    void *memory=allocate(sizeof(ZornGen7Clock::NativeGccGpuPrefix),alignof(ZornGen7Clock::NativeGccGpuPrefix));
    if(!memory){ZornGen7Clock::GccGpuPrefixResult r{};r.assessment=A::AllocationRetained;return finish(r);}
    s.gcc_gpu_prefix=::new(memory) ZornGen7Clock::NativeGccGpuPrefix(s.gates.clock_prepare,*s.physical_clocks,
        *s.extra_gcc_classes[0],*s.extra_gcc_classes[1]);
    IORecursiveLockLock(s.gates.clock_prepare);
    const auto result=s.gcc_gpu_prefix->initializeWithActualHeldGate(s.gates.clock_prepare);
    IORecursiveLockUnlock(s.gates.clock_prepare);
    if(result.native_closure_prefix_returned)s.stage=Stage::CpuReady;
    return finish(result);
}
ZornGen7Clock::GmuClockGraphResult ZornGen7DarwinBoardOwner::constructOwnedNativeGmuClockGraph()
{
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](ZornGen7Clock::GmuClockGraphResult r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(!s.physical_clocks || !s.physical_clocks->ao_class_bound_ || !s.owned_gcc_rails_ready || s.stage!=Stage::CpuReady || !s.owned_native_clock_graph || !s.native_clock_nodes_ready ||
       !s.gcc_gpu_prefix || !s.gcc_gpu_prefix->result_.native_closure_prefix_returned ||
       !s.owned_gpucc_prefix.source_prefix_complete || s.owned_native_graph_attempted ||
       s.clocks->graph_attempted_ || s.clocks->list_attempted_)return finish({});
    s.owned_native_graph_attempted=true;s.stage=Stage::StoppedRetained;
    s.owned_native_graph=s.clocks->materializeGmuGraph(s.owned_native_clock_graph->graph,*this);
    if(s.owned_native_graph.cpu_graph_complete)s.stage=Stage::CpuReady;
    return finish(s.owned_native_graph); // Actual native CCF graph only; no GMU list, sync or GPU-ready result.
}
ZornGen7Clock::ClockConsumerListResult ZornGen7DarwinBoardOwner::constructOwnedNativeGmuClockList()
{
    using A=ZornGen7Clock::ClockConsumerListAssessment;
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](){auto result=s.owned_native_list;IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || !s.owned_native_clock_graph || !s.owned_native_graph.cpu_graph_complete ||
       s.owned_native_list_attempted || s.clocks->list_attempted_ || s.clocks->initialFields()) {
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    s.owned_native_list_attempted=true;s.stage=Stage::StoppedRetained;
    void *memory=allocate(sizeof(OwnedGmuClockSoftwareState),alignof(OwnedGmuClockSoftwareState));
    if(!memory){s.owned_native_list.assessment=A::NativeAllocationRefused;return finish();}
    s.owned_gmu_software=::new(memory) OwnedGmuClockSoftwareState;
    // Existing exact indexed-get/consumer/bulk producer retains this owner and
    // the genuine native node lifetime. It borrows fields without reading hub
    // frequency or claiming completion of the later core-init producer.
    s.owned_native_list=s.clocks->buildGmuList(s.owned_native_clock_graph->gmu,
        ZornGen7ClockBuild26::qdss_stm_enabled,s.gates.startup,&s.owned_gmu_software->hub_frequency,
        &s.owned_gmu_software->device_state,*this);
    if(s.owned_native_list.assessment==A::ListPublished && s.clocks->initialFields() && s.clocks->bulkFields())
        s.stage=Stage::CpuReady;
    return finish();
}
IOReturn ZornGen7DarwinBoardOwner::publishOwnedGen79HubMetadata()
{
    if(!callable() || !storage_->clocks)return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.owned_gmu_software || !s.arc_startup || s.gen79_hub_metadata_attempted ||
       s.owned_native_list.assessment!=ZornGen7Clock::ClockConsumerListAssessment::ListPublished)return finish(kIOReturnNotReady);
    s.gen79_hub_metadata_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen79HubSource26::admits(s.arc_startup->digest))return finish(kIOReturnUnsupported);
    const auto *fields=s.clocks->initialFields();
    if(!fields || fields->startup_gate!=s.gates.startup || fields->hub_frequency!=&s.owned_gmu_software->hub_frequency ||
       fields->device_state!=&s.owned_gmu_software->device_state ||
       __atomic_load_n(&s.owned_gmu_software->hub_frequency,__ATOMIC_RELAXED)!=0 ||
       __atomic_load_n(&s.owned_gmu_software->device_state,__ATOMIC_RELAXED)!=0)return finish(kIOReturnNotReady);
    // Exact gen7_init source metadata assignment occurs before its DDR branch.
    // This writes a real owned CPU configuration field only, not hardware or a
    // measured rate. DDR-dependent geometry, features and full core-init phase
    // remain unqualified until their actual producers complete.
    __atomic_store_n(&s.owned_gmu_software->hub_frequency,ZornGen79HubSource26::configured_hub_hz,__ATOMIC_RELAXED);
    s.gen79_hub_metadata_published=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::captureOwnedDdrMetadata(IORegistryEntry &root,OSObject &treeOwner)
{
    if(!callable() || !storage_->clocks)return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gen79_hub_metadata_published || !s.arc_startup ||
       s.ddr_metadata_attempted || s.owned_native_list.assessment!=ZornGen7Clock::ClockConsumerListAssessment::ListPublished)
        return finish(kIOReturnNotReady);
    s.ddr_metadata_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen7DdrSource26::admits(s.arc_startup->digest))return finish(kIOReturnUnsupported);
    if(!retainDependency(root) || !retainDependency(treeOwner))return finish(kIOReturnNoMemory);
    // Native OS translation of the actual Linux DT scalar, not a RAM node,
    // memory resource/provider, SMEM query or physical observation. Returned
    // node/property references remain this owner's real retained storage.
    s.ddr_metadata_node=IORegistryEntry::fromPath("chosen",gIODTPlane,nullptr,nullptr,&root);
    if(!s.ddr_metadata_node)return finish(kIOReturnNotFound);
    s.ddr_metadata_property=s.ddr_metadata_node->copyProperty(ZornGen7DdrSource26::native_property);
    auto *data=OSDynamicCast(OSData,s.ddr_metadata_property);
    if(!data || data->getLength()!=4 || !data->getBytesNoCopy())return finish(kIOReturnNotReady);
    const auto *p=static_cast<const uint8_t *>(data->getBytesNoCopy());
    const uint32_t value=uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);
    if(value>INT32_MAX || value!=ZornGen7DdrSource26::source_raw_type)return finish(kIOReturnUnsupported);
    __atomic_store_n(&s.owned_ddr_type,static_cast<int32_t>(value),__ATOMIC_RELAXED);
    s.native_cx_root=&root;
    s.ddr_metadata_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
    // No bank-bit/OAS, CPU memory-size, clock, ownership or full init result.
}
IOReturn ZornGen7DarwinBoardOwner::constructOwnedGen79CoreInputs()
{
    using Fields=ZornGen7ColdBoot::ActualGen79InitFields;
    static_assert(sizeof(unsigned long)==8 && sizeof(Fields)==56 && alignof(Fields)==8,"Original LP64 source input layout");
    if(!callable() || !storage_->clocks)return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.ddr_metadata_ready || !s.gen79_hub_metadata_published ||
       !s.owned_gmu_software || !s.arc_startup || s.gen79_core_inputs_attempted ||
       s.owned_native_list.assessment!=ZornGen7Clock::ClockConsumerListAssessment::ListPublished)
        return finish(kIOReturnNotReady);
    s.gen79_core_inputs_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen79CoreSource26::admits(s.arc_startup->digest))return finish(kIOReturnUnsupported);
    const auto *clocks=s.clocks->initialFields();
    if(!clocks || clocks->hub_frequency!=&s.owned_gmu_software->hub_frequency ||
       clocks->device_state!=&s.owned_gmu_software->device_state ||
       __atomic_load_n(&s.owned_ddr_type,__ATOMIC_RELAXED)!=int32_t(ZornGen7DdrSource26::source_raw_type) ||
       __atomic_load_n(&s.owned_gmu_software->hub_frequency,__ATOMIC_RELAXED)!=ZornGen79CoreSource26::hub_hz)
        return finish(kIOReturnNotReady);
    void *memory=allocate(sizeof(Fields),alignof(Fields));if(!memory)return finish(kIOReturnNoMemory);
    // Actual existing input shape and canonical real source cells, not a
    // separate DDR/hub sample or a successful hardware/provider result.
    s.owned_gen79_core_inputs=::new(memory) Fields{&ZornGen79CoreSource26::features,
        ZornGen79CoreSource26::hub_hz,ZornGen79CoreSource26::highest_bank_bit,
        ZornGen79CoreSource26::noc_timeout_us,ZornGen79CoreSource26::bcl_data,
        &s.owned_ddr_type,&s.owned_gmu_software->hub_frequency,nullptr};
    // This is explicitly metadata-only. A genuine retained CX/SCM session
    // and a concrete mode-qualified host are still needed before execution;
    // no backend is installed or made ready by constructing these inputs.
    s.gen79_core_inputs_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
ZornGen7CxGdsc::OwnedCompletionResult ZornGen7DarwinBoardOwner::registerOwnedCxCompletion()
{
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&]{const auto result=s.cx_completion_result;IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || !s.cx_core || !s.cx_core->registered || !s.clock_resources ||
       !s.arc_startup || s.cx_completion_attempted)return finish();
    s.cx_completion_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen7CxCompletionSource26::admits(s.arc_startup->digest))return finish();
    const auto &controller=s.owned_gpucc;const uintptr_t base=reinterpret_cast<uintptr_t>(controller.mapped);
    // The actual bound full GPUCC window has controller-relative word0.
    // Rebase only its logical source origin to the GPU-wide regmap origin.
    // This shares the existing map/authority; no descriptor or map is made.
    if(!base || (base&3u) || controller.source_word_origin!=0 ||
       controller.bytes!=ZornGen7CxCompletionSource26::gpucc_bytes ||
       ZornGen7CxCompletionSource26::cfg_word<ZornGen7CxCompletionSource26::gpucc_global_word_origin)
        return finish();
    const size_t offset=size_t(ZornGen7CxCompletionSource26::cfg_word-
        ZornGen7CxCompletionSource26::gpucc_global_word_origin)*4u;
    if(offset>controller.bytes || 4u>controller.bytes-offset || base>UINTPTR_MAX-offset ||
       base+offset>UINTPTR_MAX-3u)return finish();
    const ZornGen7RegisterConfig::Region cxView{controller.mapped,controller.bytes,
        ZornGen7CxCompletionSource26::gpucc_global_word_origin};
    s.cx_completion_gate=IOLockAlloc();
    if(!s.cx_completion_gate){s.cx_completion_result.allocation_failed=true;return finish();}
    void *memory=allocate(sizeof(ZornGen7CxGdsc::Completion),alignof(ZornGen7CxGdsc::Completion));
    if(!memory){s.cx_completion_result.allocation_failed=true;return finish();}
    // The same owner retains core, notifier chain, mapping and independent
    // access/code lifetime through every continuation and uncertain return.
    s.cx_completion=::new(memory) ZornGen7CxGdsc::Completion(s.cx_core->core,s.cx_completion_gate,cxView);
    s.cx_completion_result.notification=s.cx_completion->registerActual(&s.cx_core->notifications);
    const auto &actual=s.cx_completion_result.notification;
    if(actual.actual_return_available && actual.actual_return==0) {
        s.cx_completion_result.registered=true;s.stage=Stage::CpuReady;
    }
    return finish(); // Registration/initial completion only, never power-on or a TLB flush.
}
bool ZornGen7DarwinBoardOwner::cxCoreNodeInputsAdmitted(IOService &platform) const
{
    if(!callable())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    const bool admitted=s.platform==&platform && s.stage==Stage::CpuReady && s.cx_gdsc_probe &&
        s.cx_gdsc_probe->result_.native_prefix_returned && !s.cx_core_attempted && s.rsc_cache &&
        s.rsc_reservation && s.arc_startup && s.owned_global_vdd_gate;
    IORecursiveLockUnlock(s.gates.startup);return admitted;
}
IOReturn ZornGen7DarwinBoardOwner::constructOwnedCxGdscCore(IOService &provider,IOService &gmu,
    uint32_t parentPhandle,const ZornGen7Clock::NativeClockRegistrationName &name,OSObject &nodeOwner)
{
    using namespace ZornGen7Rpmh;
    if(!callable() || !actualDeviceName(name))return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || s.cx_core_attempted || !s.cx_gdsc_probe ||
       !s.cx_gdsc_probe->result_.native_prefix_returned || !s.arc_startup ||
       !s.rsc_cache || !s.rsc_reservation || !s.owned_global_vdd_gate || !s.owned_core_supplier_fields ||
       !ZornGen7CxCoreSource26::admits(s.arc_startup->digest))return finish(kIOReturnNotReady);
    s.cx_core_attempted=true;s.stage=Stage::StoppedRetained;
    NativeClockRegulator *supply=nullptr;
    for(auto *p=s.registered_clock_regulators;p;p=p->next)if(p->source_index==0) {
        if(supply)return finish(kIOReturnNotReady);supply=p;
    }
    if(!supply || !supply->device || !supply->node || !supply->node->lifetime ||
       supply->node!=s.arc_startup->nodes[0][0] || !supply->fields ||
       supply->fields!=&s.owned_core_supplier_fields[0])return finish(kIOReturnNotReady);
    for(size_t i=0;i<32;++i)if(supply->digest[i]!=s.arc_startup->digest[i])return finish(kIOReturnUnsupported);
    OSSharedPtr<OSObject> property(supply->device->copyProperty("phandle"),OSNoRetain);
    auto *handle=OSDynamicCast(OSData,property.get());
    if(!handle || handle->getLength()!=4 || !handle->getBytesNoCopy())return finish(kIOReturnNotReady);
    const auto *bytes=static_cast<const uint8_t *>(handle->getBytesNoCopy());
    const uint32_t actual=uint32_t(bytes[0])|(uint32_t(bytes[1])<<8)|(uint32_t(bytes[2])<<16)|(uint32_t(bytes[3])<<24);
    if(!actual || actual!=parentPhandle)return finish(kIOReturnNotReady);
    const auto &rail=*supply->fields;const auto &v=rail.voltage;const auto &a=rail.arc;
    if(!v.dependent_lock || !supply->head || supply->head!=v.consumers || !supply->open_count ||
       !supply->exclusive || !v.n_coupled || !v.n_resolved || !v.has_supply || !v.valid_ops_mask ||
       !a.aggregate_lock || a.aggregate_lock==v.dependent_lock)return finish(kIOReturnNotReady);
    if(!retainDependency(provider) || !retainDependency(gmu) || !retainDependency(nodeOwner) ||
       !retainDependency(*supply->device) || !retainDependency(*supply->node->lifetime))return finish(kIOReturnNoMemory);
    // regulator_resolve_supply -> set_supply creates an independent SUPPLY
    // consumer. This is not regulator_get("parent") or a reused clock client.
    IOLockLock(v.dependent_lock);
    auto parentFinish=[&](IOReturn raw){IOLockUnlock(v.dependent_lock);return finish(raw);};
    if(*supply->exclusive || *v.n_coupled!=1 || *v.n_resolved!=1 || *v.has_supply)
        return parentFinish(kIOReturnNotReady);
    bool alwaysOn=false;
    if(!(*v.valid_ops_mask&8u)) {
        if(!a.level_count || *a.level_count<=0 || size_t(*a.level_count)>a.levels_capacity || !a.levels ||
           !a.voter_count || *a.voter_count<=0 || size_t(*a.voter_count)>a.voters_capacity || !a.voters)
            return parentFinish(kIOReturnNotReady);
        bool member=false;for(int32_t i=0;i<*a.voter_count;++i)if(&a.voters[i]==&rail.voter)member=true;
        if(!member)return parentFinish(kIOReturnNotReady);
        if(a.levels[0]!=0)alwaysOn=true; // Actual source removed-enable-op assumption only.
        else {IOLockLock(a.aggregate_lock);alwaysOn=rail.voter.req.reg[1]!=0;IOLockUnlock(a.aggregate_lock);}
    }
    size_t length=0;while(length<name.extent && name.bytes[length])++length;
    constexpr size_t suffix=sizeof(ZornGen7CxCoreSource26::supply_id);
    if(length>=64 || suffix>64-length-1u)return parentFinish(kIOReturnNoMemory);
    void *memory=allocate(sizeof(NativeClockRegulatorConsumer),alignof(NativeClockRegulatorConsumer));
    if(!memory)return parentFinish(kIOReturnNoMemory);
    s.cx_supply_consumer=::new(memory) NativeClockRegulatorConsumer{};
    auto &consumer=*s.cx_supply_consumer;consumer.supplier=supply;consumer.device=&provider;
    for(size_t i=0;i<length;++i)consumer.supply_name[i]=name.bytes[i];consumer.supply_name[length]='-';
    for(size_t i=0;i<suffix;++i)consumer.supply_name[length+1u+i]=ZornGen7CxCoreSource26::supply_id[i];
    consumer.always_on=alwaysOn;consumer.projection.next=*supply->head;*supply->head=&consumer.projection;
    *supply->open_count=*supply->open_count+1u;
    IOLockUnlock(v.dependent_lock);
    // Stable provider views come from the same already authorized GPUCC
    // mapping, with source-qualified control/HW-status offsets and real state.
    auto word=[&](uint32_t sourceByte,volatile void *&out)->bool {
        const auto &r=s.owned_gpucc;const uint32_t sourceWord=sourceByte/4u;
        if(sourceByte%4u || sourceWord<r.source_word_origin)return false;
        const size_t at=size_t(sourceWord-r.source_word_origin)*4u;
        const uintptr_t base=reinterpret_cast<uintptr_t>(r.mapped);
        if(!base || (base&3u) || at>r.bytes || 4u>r.bytes-at || base>UINTPTR_MAX-at || base+at>UINTPTR_MAX-3u)return false;
        out=reinterpret_cast<volatile void *>(base+at);return true;
    };
    volatile void *control=nullptr,*status=nullptr;
    if(!word(ZornGen7CxCoreSource26::control_byte,control) || !word(ZornGen7CxCoreSource26::status_byte,status))
        return finish(kIOReturnNotReady);
    memory=allocate(sizeof(ZornGen7CxGdsc::RegisterEnable),alignof(ZornGen7CxGdsc::RegisterEnable));
    if(!memory)return finish(kIOReturnNoMemory);
    const ZornGen7CxGdsc::Inputs inputs{ZornGen7CxGdsc::Source::ActualDirectCxWithHwStatusAndRetain,
        control,4,status,4,ZornGen7CxCoreSource26::poll_count,s.gates.clock_prepare,&s.cx_gdsc_probe->logical_enabled_};
    s.cx_register_enable=::new(memory) ZornGen7CxGdsc::RegisterEnable(inputs);
    s.cx_dependent=IOLockAlloc();s.cx_notifier=IORWLockAlloc();
    if(!s.cx_dependent || !s.cx_notifier)return finish(kIOReturnNoMemory);
    memory=allocate(sizeof(OwnedNativeCxCore),alignof(OwnedNativeCxCore));if(!memory)return finish(kIOReturnNoMemory);
    s.cx_core=::new(memory) OwnedNativeCxCore(provider,gmu,s.gates.startup,s.cx_dependent,s.cx_notifier,
        rail,consumer.projection,*s.rsc_cache,*s.rsc_reservation,*s.cx_register_enable);
    auto &core=*s.cx_core;IOLockLock(s.cx_dependent);
    // Exact uncoupled native registration: real self link and fresh software
    // counts. No always-on/boot-on constraint exists for this source node.
    core.coupled[0]=&core;core.n_coupled=1;core.n_resolved+=1u;
    // Actual primary get belongs to the GMU pdev in gen7_gmu_probe.
    core.primary.next=core.consumers;core.consumers=&core.primary;core.open_count+=1u;
    core.registered=true;IOLockUnlock(s.cx_dependent);
    s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
    // No parent/CX enable, completion, SMMU flush, native module publication
    // or successful hardware/controller session is synthesized here.
}
ZornGen7CxGdsc::NativeProbeResult ZornGen7DarwinBoardOwner::initializeOwnedCxGdscRegisters()
{
    using Probe=ZornGen7CxGdsc::NativeCxGdscProbe;
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](ZornGen7CxGdsc::NativeProbeResult value){IORecursiveLockUnlock(s.gates.startup);return value;};
    if(s.stage!=Stage::CpuReady || !s.gen79_core_inputs_ready || !s.arc_startup || !s.clock_resources ||
       !s.physical_clocks || !s.owned_gpucc_prefix.source_prefix_complete || s.cx_gdsc_probe_attempted)
        return finish({});
    s.cx_gdsc_probe_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen7CxGdscSource26::admits(s.arc_startup->digest))return finish({});
    // The original resource owner retains its full GPUCC read/write window
    // and power/security/clock exclusion. This source prefix needs that same
    // real authority; neither source identity nor graph publication supplies it.
    void *memory=allocate(sizeof(Probe),alignof(Probe));if(!memory)return finish({});
    s.cx_gdsc_probe=::new(memory) Probe(s.gates.clock_prepare,s.owned_gpucc);
    IORecursiveLockLock(s.gates.clock_prepare);
    const auto result=s.cx_gdsc_probe->initializeWithActualHeldGate(s.gates.clock_prepare);
    IORecursiveLockUnlock(s.gates.clock_prepare);
    if(result.native_prefix_returned)s.stage=Stage::CpuReady;
    return finish(result);
}
ZornGen7Clock::OwnedGpuccPrefixResult ZornGen7DarwinBoardOwner::prepareNativeGpuccPrefix()
{
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](){auto result=s.owned_gpucc_prefix;IORecursiveLockUnlock(s.gates.startup);return result;};
    if(s.stage!=Stage::CpuReady || !s.native_clock_nodes_ready || !s.owned_gcc_rails_ready || !s.owned_native_clock_graph ||
       !s.owned_controller_fields_ready || !s.physical_clocks || !s.arc_startup ||
       !s.gcc_gpu_prefix || !s.gcc_gpu_prefix->result_.native_closure_prefix_returned ||
       s.owned_gpucc_prefix_attempted || s.gpucc_attempted || s.gpucc_proxy_attempted ||
       s.clocks->graph_attempted_ || s.clocks->list_attempted_) {
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    s.owned_gpucc_prefix_attempted=true;
    const auto *controller=s.owned_controllers[1];
    if(!controller || controller->bound_node!=s.owned_native_clock_graph->graph.gpucc.node ||
       controller->provider.getState()!=0 || controller->provider.pm_vars ||
       !ZornGen7Clock::NativeGpuccProxyVote::admitsSourceIdentity(s.arc_startup->digest)) {
        s.stage=Stage::StoppedRetained;return finish();
    }
    // Source configurations and class order come from the qualified fixed
    // MiCode files. The digest gates those inputs only, never hardware access.
    // The actual native map authority and shared VDD/RSC owners remain pinned.
    auto &out=s.owned_gpucc_prefix;out.admitted=true;out.probe_called=true;
    out.probe=initializeGpuccWithStartupHeld();
    if(!out.probe.native_prefix_returned)return finish();
    out.proxy_called=true;out.proxy=voteGpuccProxyWithStartupHeld(s.arc_startup->digest);
    if(!out.proxy.native_sequence_returned)return finish();
    out.source_prefix_complete=true;return finish();
    // No graph/provider registration, GCC reinitialization, consumer sync,
    // automatic unvote/reset/release or retry follows this prefix.
}
ZornGen7Clock::GpuccProxyResult ZornGen7DarwinBoardOwner::voteGpuccProxyFromPhysicalFields(const uint8_t (&digest)[32])
{
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    const auto result=voteGpuccProxyWithStartupHeld(digest);
    IORecursiveLockUnlock(s.gates.startup);return result;
}
ZornGen7Clock::GpuccProxyResult ZornGen7DarwinBoardOwner::voteGpuccProxyWithStartupHeld(const uint8_t (&digest)[32])
{
    using A=ZornGen7Clock::GpuccProxyAssessment;
    if(!storage_ || !storage_->clocks || !IORecursiveLockHaveLock(storage_->gates.startup))return {};
    auto &s=*storage_;
    if(s.stage!=Stage::CpuReady || !s.physical_clocks || !s.gpucc_probe ||
       !s.gpucc_probe->result_.native_prefix_returned || s.gpucc_proxy_attempted ||
       s.clocks->graph_attempted_ || s.clocks->list_attempted_) {return {};}
    s.gpucc_proxy_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen7Clock::NativeGpuccProxyVote::admitsSourceIdentity(digest)) {return {};}
    // The source physical fields, native device names, real rails and shared
    // VDD gate were retained before physical construction. Pin the new native
    // caller before a rail can publish any actual sync/async request frame.
    void *memory=allocate(sizeof(ZornGen7Clock::NativeGpuccProxyVote),alignof(ZornGen7Clock::NativeGpuccProxyVote));
    if(!memory) {ZornGen7Clock::GpuccProxyResult failed{};failed.assessment=A::NativeAllocationRetained;return failed;}
    s.gpucc_proxy=::new(memory) ZornGen7Clock::NativeGpuccProxyVote(s.gates.clock_prepare,*s.physical_clocks,digest);
    IORecursiveLockLock(s.gates.clock_prepare);
    const auto result=s.gpucc_proxy->voteWithActualHeldGate(s.gates.clock_prepare);
    IORecursiveLockUnlock(s.gates.clock_prepare);
    if(result.native_sequence_returned)s.stage=Stage::CpuReady;
    return result;
}
ZornGen7Clock::GpuccProbeResult ZornGen7DarwinBoardOwner::initializeGpuccFromPhysicalFields()
{
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    const auto result=initializeGpuccWithStartupHeld();
    IORecursiveLockUnlock(s.gates.startup);return result;
}
ZornGen7Clock::GpuccProbeResult ZornGen7DarwinBoardOwner::initializeGpuccWithStartupHeld()
{
    using A=ZornGen7Clock::GpuccProbeAssessment;
    if(!storage_ || !storage_->clocks || !IORecursiveLockHaveLock(storage_->gates.startup))return {};
    auto &s=*storage_;
    if(s.stage!=Stage::CpuReady || !s.physical_clocks || s.gpucc_attempted || s.clocks->initialFields()) {
        return {};
    }
    s.gpucc_attempted=true;s.stage=Stage::StoppedRetained;
    void *memory=allocate(sizeof(ZornGen7Clock::NativeGpuccClockProbe),alignof(ZornGen7Clock::NativeGpuccClockProbe));
    if(!memory){ZornGen7Clock::GpuccProbeResult failed{};failed.assessment=A::NativeAllocationRetained;return failed;}
    s.gpucc_probe=::new(memory) ZornGen7Clock::NativeGpuccClockProbe(s.gates.clock_prepare,*s.physical_clocks);
    IORecursiveLockLock(s.gates.clock_prepare);
    const auto result=s.gpucc_probe->initializeWithActualHeldGate(s.gates.clock_prepare);
    IORecursiveLockUnlock(s.gates.clock_prepare);
    if(result.native_prefix_returned)s.stage=Stage::CpuReady;
    return result;
}
ZornGen7Clock::PhysicalClockBindingResult ZornGen7DarwinBoardOwner::constructPhysicalClockBindings(
    const ZornGen7Clock::ActualGmuPhysicalClockInputs &in,OSObject &fields_owner)
{
    using A=ZornGen7Clock::PhysicalClockBindingAssessment;
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(!s.owned_gcc_rails_ready || !s.extra_gcc_classes[0] || s.owned_global_vdd_gate!=&in.global_vdd_gate || s.stage!=Stage::CpuReady || s.physical_attempted || s.clocks->initialFields()) {IORecursiveLockUnlock(s.gates.startup);return {};}
    s.physical_attempted=true;s.stage=Stage::StoppedRetained;
    if(!in.gpucc_regmap_device_pm || !in.gcc.mapped || !in.gpucc.mapped ||
       (reinterpret_cast<uintptr_t>(in.gcc.mapped)&3u) || (reinterpret_cast<uintptr_t>(in.gpucc.mapped)&3u) ||
       in.gcc.bytes<4 || in.gpucc.bytes<4 || in.gcc_cx.global_!=&in.global_vdd_gate ||
       in.gpu_cx.global_!=&in.global_vdd_gate || in.gpu_mx.global_!=&in.global_vdd_gate ||
       in.gpu_mxc.global_!=&in.global_vdd_gate) {IORecursiveLockUnlock(s.gates.startup);return {};}
    for(size_t i=0;i<3;++i)if(!actualDeviceName(in.device_names[i]) ||
       !in.controllers[i].runtime_pm_enabled || !in.controllers[i].provider_has_sync_state) {
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    if(!retainDependency(fields_owner)) {IORecursiveLockUnlock(s.gates.startup);return {A::NativeAllocationRetained,0,0,false};}
    void *memory=allocate(sizeof(ZornGen7Clock::NativeGmuPhysicalClockBindings),alignof(ZornGen7Clock::NativeGmuPhysicalClockBindings));
    if(!memory) {IORecursiveLockUnlock(s.gates.startup);return {A::NativeAllocationRetained,0,0,false};}
    s.physical_clocks=::new(memory) ZornGen7Clock::NativeGmuPhysicalClockBindings(in,s.gates.clock_prepare);
    if(!s.physical_clocks->bindAoClass(s.extra_gcc_classes[0]->vote)){IORecursiveLockUnlock(s.gates.startup);return {};}
    // CPU fields constructed only. Keep controller probe/physical initialization
    // and later graph/list calls separate until their real source prerequisites
    // and the same actual owner have been bound; no ready/clock/rail success.
    s.stage=Stage::CpuReady;IORecursiveLockUnlock(s.gates.startup);return {A::FieldsConstructed,25,5,false};
}
ZornGen7Clock::StockGmuClockGraphResult ZornGen7DarwinBoardOwner::constructStockGmuClockGraph(
    const uint8_t (&digest)[32],const ZornGen7Clock::ActualStockGmuClockGraphFields &in,
    bool qdss,const volatile uint64_t *hub,volatile uint32_t *state,OSObject &fields_owner)
{
    ZornGen7Clock::StockGmuClockGraphResult result{};
    if(!callable() || !storage_->clocks)return result;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || s.clocks->initialFields()) {IORecursiveLockUnlock(s.gates.startup);return result;}
    s.stage=Stage::StoppedRetained;
    if(!ZornGen7StockGmuClock::matches(digest)) {IORecursiveLockUnlock(s.gates.startup);return result;}
    for(size_t i=0;i<3;++i)if(!actualDeviceName(in.device_names[i])) {IORecursiveLockUnlock(s.gates.startup);return result;}
    // Pin real physical/source fields and native device-name storage before
    // copying borrows or constructing the metadata. Actual native clock cores
    // later retain THIS owner and its stable metadata through every callback.
    if(!retainDependency(fields_owner)) {
        result.graph.assessment=ZornGen7Clock::GmuClockGraphAssessment::NativeAllocationRetained;
        IORecursiveLockUnlock(s.gates.startup);return result;
    }
    void *memory=allocate(sizeof(StockClockGraphMetadata),alignof(StockClockGraphMetadata));
    if(!memory) {
        result.graph.assessment=ZornGen7Clock::GmuClockGraphAssessment::NativeAllocationRetained;
        IORecursiveLockUnlock(s.gates.startup);return result;
    }
    auto *metadata=new(memory) StockClockGraphMetadata(in,*this);result.immutable_metadata_constructed=true;
    result.graph=s.clocks->materializeGmuGraph(metadata->graph,*this);
    if(result.graph.cpu_graph_complete) {
        result.list=s.clocks->buildGmuList(metadata->gmu,qdss,s.gates.startup,hub,state,fields_owner);
        if(result.list.assessment==ZornGen7Clock::ClockConsumerListAssessment::ListPublished) {
            result.source_clock_list_complete=true;s.stage=Stage::CpuReady;
        }
    }
    IORecursiveLockUnlock(s.gates.startup);return result;
}
ZornGen7Clock::GmuClockGraphResult ZornGen7DarwinBoardOwner::constructGmuSourceGraph(
    const ZornGen7Clock::ActualNativeGmuClockGraphInputs &inputs,OSObject &input_owner)
{
    using A=ZornGen7Clock::GmuClockGraphAssessment;
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || s.clocks->initialFields()) {IORecursiveLockUnlock(s.gates.startup);return {};}
    s.stage=Stage::StoppedRetained;
    if(!retainDependency(input_owner)) {
        ZornGen7Clock::GmuClockGraphResult result{};result.assessment=A::NativeAllocationRetained;
        IORecursiveLockUnlock(s.gates.startup);return result;
    }
    const auto result=s.clocks->materializeGmuGraph(inputs,*this);
    if(result.cpu_graph_complete)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return result;
}
const ZornGen7Clock::ActualInitialClockFields *ZornGen7DarwinBoardOwner::borrowInitialClockFields() const
{
    if(!callable()||!storage_->clocks)return nullptr;
    IORecursiveLockLock(storage_->gates.startup);const auto *fields=storage_->clocks->initialFields();
    IORecursiveLockUnlock(storage_->gates.startup);return fields;
}
const ZornGen7Clock::ActualCcfBulkFields *ZornGen7DarwinBoardOwner::borrowBulkClockFields() const
{
    if(!callable()||!storage_->clocks)return nullptr;
    IORecursiveLockLock(storage_->gates.startup);const auto *fields=storage_->clocks->bulkFields();
    IORecursiveLockUnlock(storage_->gates.startup);return fields;
}
ZornGen7Clock::ClockCoreFactoryResult ZornGen7DarwinBoardOwner::registerBoardXoFromNativeNode(
    IORegistryEntry &node,OSObject &node_owner)
{
    using A=ZornGen7Clock::ClockCoreFactoryAssessment;
    if(!callable() || !storage_->clocks)return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&]{const auto out=s.board_xo_result;IORecursiveLockUnlock(s.gates.startup);return out;};
    if(s.board_xo_attempted || s.stage!=Stage::CpuReady || s.physical_attempted ||
       s.clocks->graph_attempted_ || s.clocks->list_attempted_)return finish();
    s.board_xo_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(node) || !retainDependency(node_owner)) {
        s.board_xo_result.assessment=A::AllocationRetained;return finish();
    }
    OSSharedPtr<OSObject> compat(node.copyProperty("compatible"),OSNoRetain);
    OSSharedPtr<OSObject> names(node.copyProperty("clock-output-names"),OSNoRetain);
    OSSharedPtr<OSObject> cells(node.copyProperty("#clock-cells"),OSNoRetain);
    OSSharedPtr<OSObject> frequency(node.copyProperty("clock-frequency"),OSNoRetain);
    OSSharedPtr<OSObject> accuracy(node.copyProperty("clock-accuracy"),OSNoRetain);
    auto text=[&](OSObject *object,const char *expected,size_t bytes) {
        auto *data=OSDynamicCast(OSData,object);
        if(!data || data->getLength()!=bytes)return false;
        const auto *p=static_cast<const char *>(data->getBytesNoCopy());
        if(!p)return false;for(size_t i=0;i<bytes;++i)if(p[i]!=expected[i])return false;return true;
    };
    auto word=[&](OSObject *object,uint32_t &out) {
        auto *data=OSDynamicCast(OSData,object);
        if(!data || data->getLength()!=sizeof(out) || !data->getBytesNoCopy())return false;
        memcpy(&out,data->getBytesNoCopy(),sizeof(out));return true;
    };
    uint32_t rate=0,acc=0,num_cells=0;
    if(!text(compat.get(),"fixed-clock",sizeof("fixed-clock")) ||
       !text(names.get(),"xo_board",sizeof("xo_board")) ||
       !word(cells.get(),num_cells) || num_cells || !word(frequency.get(),rate) ||
       (accuracy && !word(accuracy.get(),acc)))return finish();
    void *memory=allocate(sizeof(OwnedBoardXo),alignof(OwnedBoardXo));
    if(!memory){s.board_xo_result.assessment=A::AllocationRetained;return finish();}
    s.board_xo=::new(memory) OwnedBoardXo(rate,acc);
    s.board_xo_result=s.clocks->registerActual(s.board_xo->hardware,*this);
    if(s.board_xo_result.core_initialized)s.stage=Stage::CpuReady;
    return finish();
}
ZornGen7Clock::PhysicalClockBindingResult ZornGen7DarwinBoardOwner::constructOwnedPhysicalClockBindings(
    const OwnedPhysicalClockInputs &in,OSObject &fields)
{
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(!s.owned_gcc_rails_ready || !s.extra_gcc_classes[0] || s.owned_global_vdd_gate!=&in.global_vdd_gate || s.stage!=Stage::CpuReady || !s.board_xo || !s.board_xo_result.core_initialized ||
       !s.clock_resources || !s.command_db_storage || !s.rsc_storage || !s.rsc_cache || !s.rsc_reservation) {
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    ZornGen7Clock::ActualGmuPhysicalClockInputs actual{s.board_xo->hardware,
        {in.device_names[0],in.device_names[1],in.device_names[2]},
        {in.controllers[0],in.controllers[1],in.controllers[2]}, {},{},in.gpucc_regmap_device_pm,
        in.global_vdd_gate,in.gcc_cx,in.gpu_cx,in.gpu_mx,in.gpu_mxc,
        s.owned_command_db,*s.rsc_cache,*s.rsc_reservation,s.command_db_reader};
    IORecursiveLockUnlock(s.gates.startup);
    return constructPhysicalClockBindingsWithOwnedMappings(actual,fields);
}
ZornGen7Clock::StockGmuClockGraphResult ZornGen7DarwinBoardOwner::constructOwnedStockGmuClockGraph(
    const uint8_t (&digest)[32],bool qdss,const volatile uint64_t *hub,volatile uint32_t *state,OSObject &fields)
{
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.physical_clocks || !s.gpucc_probe || !s.gpucc_proxy ||
       !s.gpucc_probe->result_.native_prefix_returned || !s.gpucc_proxy->result_.native_sequence_returned) {
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    const auto actual=s.physical_clocks->graph_fields_;
    IORecursiveLockUnlock(s.gates.startup);
    return constructStockGmuClockGraph(digest,actual,qdss,hub,state,fields);
}
ZornGen7DarwinBoardOwner::ClockStartupResult ZornGen7DarwinBoardOwner::prepareOwnedClockGraph(
    const OwnedPhysicalClockInputs &in,const uint8_t (&digest)[32],bool qdss,
    const volatile uint64_t *hub,volatile uint32_t *state,OSObject &fields)
{
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.owned_clock_startup_attempted || s.stage!=Stage::CpuReady) {
        const auto out=s.owned_clock_startup;IORecursiveLockUnlock(s.gates.startup);return out;
    }
    s.owned_clock_startup_attempted=true;
    if(!ZornGen7StockGmuClock::matches(digest) ||
       !ZornGen7Clock::NativeGpuccProxyVote::admitsSourceIdentity(digest)) {
        s.stage=Stage::StoppedRetained;
        IORecursiveLockUnlock(s.gates.startup);return s.owned_clock_startup;
    }
    IORecursiveLockUnlock(s.gates.startup);
    ClockStartupResult progress;
    auto publish=[&]{IORecursiveLockLock(s.gates.startup);s.owned_clock_startup=progress;IORecursiveLockUnlock(s.gates.startup);};
    progress.stage=ClockStartupStage::PhysicalFields;publish();
    progress.physical=constructOwnedPhysicalClockBindings(in,fields);publish();
    if(progress.physical.assessment!=ZornGen7Clock::PhysicalClockBindingAssessment::FieldsConstructed)return progress;
    progress.stage=ClockStartupStage::GpuccProbe;publish();
    progress.probe=initializeGpuccFromPhysicalFields();publish();
    if(!progress.probe.native_prefix_returned)return progress;
    progress.stage=ClockStartupStage::ProxyVote;publish();
    progress.proxy=voteGpuccProxyFromPhysicalFields(digest);publish();
    if(!progress.proxy.native_sequence_returned)return progress;
    progress.stage=ClockStartupStage::Graph;publish();
    progress.graph=constructOwnedStockGmuClockGraph(digest,qdss,hub,state,fields);publish();
    if(!progress.graph.source_clock_list_complete)return progress;
    progress.source_forward_returned=true;progress.stage=ClockStartupStage::Returned;publish();
    return progress;
}
IOReturn ZornGen7DarwinBoardOwner::bindActualCommandDbResources(IOService &platform,ZornGen7CommandDbResources26 &reader)
{
    if(!callable() || !reader.readResult().dataReady)return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.platform!=&platform || s.stage!=Stage::CpuReady || s.command_db_storage ||
       s.arc_source_attempted || s.arc_startup_attempted || s.physical_attempted || s.clocks->graph_attempted_)return finish(kIOReturnNotReady);
    if(!retainDependency(reader)){s.stage=Stage::StoppedRetained;return finish(kIOReturnNoMemory);}
    s.command_db_storage=&reader;s.command_db_reader=&reader;return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::bindActualCommandDbSnapshot(IOService &platform,OSObject &snapshot_owner,
    const ZornGen7Rpmh::ActualXoCommandDbSnapshot &snapshot)
{
    if(!callable() || !snapshot.bytes || snapshot.byte_count<ZCDF_HEADER_BYTES ||
       snapshot.byte_count>ZCDF_MAX_FILE_BYTES || !snapshot.scratch ||
       snapshot.scratch_capacity!=ZCDF_MAX_ENTRIES)return kIOReturnBadArgument;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.platform!=&platform || s.stage!=Stage::CpuReady || s.command_db_storage ||
       s.arc_source_attempted || s.arc_startup_attempted || s.physical_attempted || s.clocks->graph_attempted_) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    if(!retainDependency(snapshot_owner)) {
        s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);return kIOReturnNoMemory;
    }
    s.command_db_storage=&snapshot_owner;s.owned_command_db=snapshot;
    IORecursiveLockUnlock(s.gates.startup);return kIOReturnSuccess;
}
bool ZornGen7DarwinBoardOwner::arcNativeInputsAdmitted(IOService &platform,const uint8_t (&digest)[32]) const
{
    if(!callable())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    const bool allowed=s.platform==&platform && s.stage==Stage::CpuReady && s.rsc_storage && s.command_db_storage &&
        !s.arc_native_nodes && !s.arc_startup_attempted && !s.arc_source_attempted &&
        ZornGen7Rpmh::NativeOwnedArcSource::admitsSource(digest);
    IORecursiveLockUnlock(s.gates.startup);return allowed;
}
IOReturn ZornGen7DarwinBoardOwner::bindActualArcNodeOwner(IOService &platform,OSObject &owner,
    IOService *const (&groups)[5])
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.platform!=&platform || s.stage!=Stage::CpuReady || !s.rsc_storage || !s.command_db_storage ||
       s.arc_native_nodes || s.arc_startup_attempted || s.arc_source_attempted)return finish(kIOReturnNotReady);
    OSSharedPtr<IORegistryEntry> drv;
    for(size_t g=0;g<5;++g) {
        if(!groups[g])return finish(kIOReturnBadArgument);
        for(size_t j=0;j<g;++j)if(groups[j]==groups[g])return finish(kIOReturnBadArgument);
        OSSharedPtr<IORegistryEntry> parent(groups[g]->copyParentEntry(gIOServicePlane),OSNoRetain);
        if(!OSDynamicCast(IOService,parent.get()) || (drv && drv.get()!=parent.get()))return finish(kIOReturnNotReady);
        if(!drv)drv=parent;
    }
    // Only ArcNodes' real transferred/attached topology calls this private
    // method. This pin establishes lifetime, NOT driver completion or access.
    if(!retainDependency(owner))return finish(kIOReturnNoMemory);
    s.arc_native_nodes=&owner;for(size_t g=0;g<5;++g)s.arc_parent_devices[g]=groups[g];
    return finish(kIOReturnSuccess);
}
bool ZornGen7DarwinBoardOwner::actualArcParentBound(size_t group,IOService &parent) const
{
    using A=ZornGen7Rpmh::OwnedCoreAssessment;
    const auto &s=*storage_;
    if(!IORecursiveLockHaveLock(s.gates.startup) || group>=5 || !s.arc_native_nodes || !s.arc_startup ||
       s.arc_parent_devices[group]!=&parent || s.arc_startup->native_parents[group].get()!=&parent)return false;
    auto *source=group<3?s.owned_arc_sources[group]:s.upstream_arc_sources[group-3u];
    const size_t count=ZornGen7CoreSourceMetadata::counts[group];
    if(!source || source->result_.voters_initialized!=count || source->voter_count_!=int32_t(count))return false;
    if(group<3 && (!s.regulator_proxies_returned || s.completed_source_siblings[group]!=count))return false;
    if(group==3 && (!s.mmcx_proxy_returned || !s.mmcx_siblings_returned))return false;
    for(size_t v=0;v<count;++v) {
        auto *core=group<3?(v?s.owned_sibling_cores[group][v]:s.owned_arc_cores[group]):
            group==3?(v?s.owned_mmcx_sibling_cores[v]:s.upstream_arc_cores[0]):s.upstream_arc_cores[1];
        if(!core || core->result_.assessment!=A::CoreFieldsPrepared)return false;
        const auto *fields=group<3 && !v?(s.owned_core_supplier_fields?&s.owned_core_supplier_fields[group]:nullptr):&core->supplier_;
        NativeClockRegulator *found=nullptr;
        NativeClockRegulator *const lists[]={s.registered_clock_regulators,s.registered_sibling_regulators,s.registered_upstream_regulators};
        for(auto *head:lists)for(auto *p=head;p;p=p->next)if(p->fields==fields){if(found)return false;found=p;}
        if(!found || found->source_index!=group || found->head!=&core->consumers_ || found->open_count!=&core->open_count_ ||
           found->node!=s.arc_startup->nodes[group][v] || found->device!=s.arc_startup->devices[group][v])return false;
        for(size_t k=0;k<32;++k)if(found->digest[k]!=s.arc_startup->digest[k])return false;
        OSSharedPtr<IORegistryEntry> observed(found->device->copyParentEntry(gIOServicePlane),OSNoRetain);
        if(observed.get()!=&parent)return false;
    }
    // Native equivalent of the source's cross-parent binding requirement:
    // every real upstream voter/core and required proxy has returned, its
    // private built-in owner and group attachment remain pinned, and this
    // candidate has no deferred-probe/unregister path. No Linux device_is_bound
    // result, IOService matching flag, HW readiness or stop lease is invented.
    return true;
}
ZornGen7Rpmh::OwnedArcStartupResult ZornGen7DarwinBoardOwner::initializeArcRegulatorsFromOwnedSnapshot(
    const uint8_t (&digest)[32],const ZornGen7Clock::NativeClockFirmwareNode *const (&nodes)[5][4],
    IOService *const (&devices)[5][4])
{
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.command_db_storage || !s.rsc_storage || !s.rsc_cache || !s.rsc_reservation || s.arc_startup_attempted) {
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    if(s.command_db_reader){
        auto *reader=s.command_db_reader;auto *owner=s.command_db_storage;
        auto *cache=s.rsc_cache;auto *reservation=s.rsc_reservation;auto *rsc=s.rsc_storage;
        IORecursiveLockUnlock(s.gates.startup);
        return initializeArcSourcesFromInput(digest,nodes,devices,nullptr,reader,*owner,*cache,*reservation,*rsc);
    }
    const auto snapshot=s.owned_command_db;auto *owner=s.command_db_storage;
    auto *cache=s.rsc_cache;auto *reservation=s.rsc_reservation;auto *rsc=s.rsc_storage;
    IORecursiveLockUnlock(s.gates.startup);
    return initializeOwnedArcRegulatorSources(digest,nodes,devices,snapshot,*owner,*cache,*reservation,*rsc);
}
bool ZornGen7DarwinBoardOwner::nativeClockNodeInputsAdmitted(IOService &platform) const
{
    if(!callable())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    const bool ready=s.platform==&platform && s.stage==Stage::CpuReady && s.owned_controller_fields_ready &&
        s.physical_clocks && !s.native_clock_nodes_attempted && !s.clocks->graph_attempted_;
    IORecursiveLockUnlock(s.gates.startup);return ready;
}
IOReturn ZornGen7DarwinBoardOwner::constructOwnedSmmuPower(IOService &platform,IOService &controller,
    IOMemoryDescriptor &descriptor,OSObject &inputOwner)
{
    using namespace ZornGen7Clock;
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || s.platform!=&platform || s.smmu_power_attempted ||
       !s.cx_core || !s.cx_core->registered || !s.cx_completion_result.registered ||
       !s.smmu_clock_node || !s.smmu_clock_node->lifetime || !s.owned_native_graph.cpu_graph_complete ||
       !s.arc_startup || !s.clocks)return finish(kIOReturnNotReady);
    s.smmu_power_attempted=true;s.stage=Stage::StoppedRetained;
    for(size_t i=0;i<32;++i)if(s.arc_startup->digest[i]!=ZornGen7SmmuPowerSource26::digest[i])
        return finish(kIOReturnUnsupported);
    // These actual properties were qualified by ClockNodes before promotion;
    // re-read supply admission from the same retained native provider.
    OSSharedPtr<OSObject> supply(controller.copyProperty("vdd-supply"),OSNoRetain),
        regulators(controller.copyProperty("qcom,regulator-names"),OSNoRetain),
        interconnect(controller.copyProperty("interconnects"),OSNoRetain),
        cxHandle(s.cx_core->provider.copyProperty("phandle"),OSNoRetain);
    auto *vdd=OSDynamicCast(OSData,supply.get()),*names=OSDynamicCast(OSData,regulators.get()),
         *cx=OSDynamicCast(OSData,cxHandle.get());
    if(!vdd || !cx || vdd->getLength()!=4 || cx->getLength()!=4 || !vdd->getBytesNoCopy() ||
       !cx->getBytesNoCopy() || !names || names->getLength()!=sizeof(ZornGen7SmmuPowerSource26::supply) ||
       !names->getBytesNoCopy() || interconnect)return finish(kIOReturnBadArgument);
    const auto *a=static_cast<const uint8_t *>(vdd->getBytesNoCopy()),
               *b=static_cast<const uint8_t *>(cx->getBytesNoCopy());
    uint32_t phandle=0;for(size_t i=0;i<4;++i){if(a[i]!=b[i])return finish(kIOReturnBadArgument);phandle|=uint32_t(a[i])<<(8u*i);}
    if(phandle!=ZornGen7SmmuPowerSource26::native_cx)return finish(kIOReturnBadArgument);
    const auto *id=static_cast<const char *>(names->getBytesNoCopy());
    for(size_t i=0;i<sizeof(ZornGen7SmmuPowerSource26::supply);++i)
        if(id[i]!=ZornGen7SmmuPowerSource26::supply[i])return finish(kIOReturnBadArgument);
    if(!retainDependency(controller) || !retainDependency(descriptor) || !retainDependency(inputOwner) ||
       !retainDependency(*s.smmu_clock_node->lifetime))return finish(kIOReturnNoMemory);
    IOLock *lock=IOLockAlloc();if(!lock)return finish(kIOReturnNoMemory);
    void *memory=allocate(sizeof(OwnedSmmuPowerFrame),alignof(OwnedSmmuPowerFrame));
    if(!memory)return finish(kIOReturnNoMemory);
    s.smmu_power=::new(memory) OwnedSmmuPowerFrame(controller,descriptor,lock,*s.smmu_clock_node,*this);
    auto &frame=*s.smmu_power;
    if(!frame.name || !actualDeviceName({frame.clocks.device_id,frame.clocks.device_id_extent}))
        return finish(kIOReturnNotReady);
    // Original initialization order: named clocks first; regulator acquisition
    // second; optional ICC last. No clock enable or PM resume occurs here.
    s.smmu_clocks=s.clocks->buildSmmuList(frame.clocks,s.gates.startup,*this);
    if(s.smmu_clocks.assessment!=ClockConsumerListAssessment::ListPublished)
        return finish(s.smmu_clocks.source_return_available?kIOReturnError:kIOReturnNotReady);
    const auto *bulk=s.clocks->smmuBulkFields();if(!bulk)return finish(kIOReturnNotReady);
    const size_t n=frame.name->getLength();
    if(n+1u+sizeof(ZornGen7SmmuPowerSource26::supply)>sizeof(frame.supply_name))return finish(kIOReturnBadArgument);
    for(size_t i=0;i<n;++i)frame.supply_name[i]=frame.clocks.device_id[i];frame.supply_name[n]='-';
    for(size_t i=0;i<sizeof(ZornGen7SmmuPowerSource26::supply);++i)
        frame.supply_name[n+1u+i]=ZornGen7SmmuPowerSource26::supply[i];
    auto &core=*s.cx_core;IOLockLock(s.cx_dependent);
    if(core.n_coupled!=1 || core.n_resolved!=1 || core.coupled[0]!=&core ||
       !core.open_count || core.open_count==UINT32_MAX || core.valid_ops!=8u) {
        IOLockUnlock(s.cx_dependent);return finish(kIOReturnNotReady);
    }
    bool primary=false;for(auto *p=core.consumers;p;p=p->next)if(p==&core.primary)primary=true;
    if(!primary){IOLockUnlock(s.cx_dependent);return finish(kIOReturnNotReady);}
    frame.vdd.next=core.consumers;core.consumers=&frame.vdd;++core.open_count;
    frame.registered_regulators=1;IOLockUnlock(s.cx_dependent);
    // Exact source controller has no optional ICC property or extra power
    // hooks. This does not establish runtime-PM or any context-bank domain.
    memory=allocate(sizeof(ZornGen7Smmu::ControllerPower),alignof(ZornGen7Smmu::ControllerPower));
    if(!memory)return finish(kIOReturnNoMemory);
    const ZornGen7Smmu::ControllerPowerFields fields{frame.power_lock,&frame.power_count,
        &frame.registered_regulators,&frame.has_resume,&frame.has_suspend,*bulk,
        &frame.icc_path,nullptr,&frame.global_page,&frame.guarded_global_io};
    frame.operation=::new(memory) ZornGen7Smmu::ControllerPower(fields,core.core,frame.vdd);
    s.smmu_power_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::bindOwnedSmmuGlobalIo(ZornGen7RegisterMaps26 &maps)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || !s.smmu_power_ready || !s.smmu_power ||
       !s.smmu_power->operation || s.smmu_io_attempted)return finish(kIOReturnNotReady);
    s.smmu_io_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(maps))return finish(kIOReturnNoMemory);
    auto &frame=*s.smmu_power;
    if(!maps.bindSmmuIo(*this,frame.provider,frame.descriptor,frame.guarded_global_io))
        return finish(kIOReturnNotReady);
    s.smmu_io_bound=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
// Native CX primary prefix only. Controller runtime-PM resume and TLB hints
// are later operations; this shared Completion primitive does not use them.
ZornGen7CxGdsc::EnablePrefixResult ZornGen7DarwinBoardOwner::prepareNativeCxPrimary()
{
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_power_ready || !s.smmu_power ||
       !s.smmu_io_bound || !s.owned_gpucc_prefix.source_prefix_complete ||
       !s.cx_core || !s.cx_core->registered || !s.cx_completion || !s.cx_completion_result.registered){
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    s.stage=Stage::StoppedRetained;
    const auto result=s.cx_completion->waitAndEnablePrimary();
    if(result.wait.assessment==ZornGen7CxGdsc::WaitAssessment::Completed &&
       result.regulator.disposition==ZornGen7ColdBoot::Disposition::Complete)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return result;
}
ZornGen7CxGdsc::EnablePrefixResult ZornGen7DarwinBoardOwner::prepareCxForDomainProbe()
{
    if(!callable())return {};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_pm_ready || !s.cx_completion ||
       !s.cx_completion_result.registered) {IORecursiveLockUnlock(s.gates.startup);return {};}
    s.stage=Stage::StoppedRetained;
    const auto result=s.cx_completion->waitAndEnablePrimary();
    if(result.wait.assessment==ZornGen7CxGdsc::WaitAssessment::Completed &&
       result.regulator.disposition==ZornGen7ColdBoot::Disposition::Complete)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return result;
}
IOReturn ZornGen7DarwinBoardOwner::probeNativeSmmuCapabilities(ZornGen7RegisterMaps26 &maps,
    OSObject &owner,ZornGen7NativeSmmuProbeResult26 &out)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.smmu_pm_ready || !s.smmu_pm || !s.smmu_power ||
       !s.smmu_io_bound || s.smmu_power->guarded_global_io.cookie!=&maps || s.smmu_domains_attempted)return finish(kIOReturnNotReady);
    s.smmu_domains_attempted=true;s.stage=Stage::StoppedRetained;auto &f=*s.smmu_power;
    out.ioBound=maps.bindNativeSmmuProbeIo(*this,f.provider,f.descriptor,*s.smmu_pm,*s.gates.startup,f.native_probe_io);
    if(!out.ioBound)return finish(kIOReturnNotReady);
    const auto raw=ZornGen7SmmuDomain26::createNativeAndProbe(f.provider,*s.smmu_pm,f.native_probe_io,
        *s.gates.startup,*this,owner,s.smmu_domains);
    if(s.smmu_domains)s.smmu_domains->copyProbeResult(out);
    if(raw==kIOReturnSuccess){s.smmu_domains_ready=true;s.stage=Stage::CpuReady;}
    return finish(raw);
}
IOReturn ZornGen7DarwinBoardOwner::probeOwnedSmmuDomains(OSObject &owner,const ZornGen7SmmuBankAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || !s.smmu_pm_ready || !s.smmu_pm || !s.smmu_power ||
       !s.smmu_io_bound || s.smmu_domains_attempted)return finish(kIOReturnNotReady);
    s.smmu_domains_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=ZornGen7SmmuDomain26::createAndProbe(s.smmu_power->provider,*s.smmu_pm,
        s.smmu_power->guarded_global_io,*s.gates.startup,*this,owner,authority,s.smmu_domains);
    if(raw!=kIOReturnSuccess)return finish(raw);
    s.smmu_domains_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
ZornGen7ColdBoot::OperationResult ZornGen7DarwinBoardOwner::reserveOwnedSmmuEndpoints(
    IORegistryEntry &root,IOService &gmu,OSObject &treeOwner)
{
    if(!callable())return {ZornGen7ColdBoot::Disposition::Unavailable,ZornGen7ColdBoot::StatusDomain::Unavailable,0,0};
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains || !s.platform) {
        IORecursiveLockUnlock(s.gates.startup);return {ZornGen7ColdBoot::Disposition::Unavailable,ZornGen7ColdBoot::StatusDomain::Unavailable,0,0};
    }
    s.stage=Stage::StoppedRetained;
    const auto result=s.smmu_domains->reserveNativeEndpoints(*s.platform,root,gmu,treeOwner);
    if(result.disposition==ZornGen7ColdBoot::Disposition::Complete)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return result;
}
IOReturn ZornGen7DarwinBoardOwner::bindOwnedSmmuContextViews(ZornGen7RegisterMaps26 &maps,
    OSObject &owner,const ZornGen7AtomicSmmuGuard26 &guard)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains || !s.smmu_power ||
       !s.smmu_io_bound || s.smmu_power->guarded_global_io.cookie!=&maps) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->bindContextViews(maps,s.smmu_power->descriptor,owner,guard);
    if(raw==kIOReturnSuccess)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return raw;
}
IOReturn ZornGen7DarwinBoardOwner::prepareOwnedSmmuRootPages()
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->prepareRootPages();
    if(raw==kIOReturnSuccess)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return raw;
}
IOReturn ZornGen7DarwinBoardOwner::prepareOwnedSmmuSparseArenas()
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->prepareSparseArenas();
    if(raw==kIOReturnSuccess)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return raw;
}
IOReturn ZornGen7DarwinBoardOwner::prepareOwnedGmuContextImage()
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->prepareGmuContextImage();
    if(raw==kIOReturnSuccess)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return raw;
}
ZornGen7ColdBoot::OperationResult ZornGen7DarwinBoardOwner::resumeNativeSmmuPower(ZornGen7NativeSmmuPowerProgress26 &progress)
{
    using namespace ZornGen7ColdBoot;constexpr OperationResult unavailable{Disposition::Unavailable,StatusDomain::Unavailable,0,0};
    if(!callable())return unavailable;
    progress.caller_phase=2;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](OperationResult r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || !s.smmu_power_ready || !s.smmu_io_bound || !s.smmu_power ||
       !s.smmu_power->operation || s.smmu_pm_attempted || s.smmu_domains_attempted)return finish(unavailable);
    progress.caller_phase=3;
    auto &f=*s.smmu_power;if(f.native_power_attempted)return finish(unavailable);
    f.native_power_attempted=true;s.stage=Stage::StoppedRetained;
    const auto *meta=f.provider.getMetaClass();
    if((meta!=IOPlatformDevice::metaClass && meta!=IOService::metaClass) || f.provider.isInactive())return finish(unavailable);
    progress.caller_phase=4;
    f.native_claim_parent=f.provider.getProvider();if(!f.native_claim_parent)return finish(unavailable);f.native_claim_parent->retain();
    progress.caller_phase=5;
    f.native_claimant=new IOService;if(!f.native_claimant)return finish(unavailable);
    progress.caller_phase=6;
    if(!f.native_claimant->init())return finish(unavailable);progress.caller_phase=7;
    if(!f.native_claimant->attach(f.native_claim_parent))return finish(unavailable);progress.caller_phase=8;
    f.native_provider_opened=f.provider.open(f.native_claimant,0,nullptr);
    if(!f.native_provider_opened)return finish(unavailable);progress.caller_phase=9;
    if(!f.provider.isOpen(f.native_claimant))return finish(unavailable);progress.caller_phase=10;
    using Reference=ZornGen7Smmu::ControllerPower::Reference;
    void *memory=allocate(sizeof(Reference),alignof(Reference));if(!memory)return finish(unavailable);
    f.native_reference=::new(memory)Reference(*f.operation);progress.caller_phase=11;
    f.native_power_result=f.operation->resumeActual(*f.native_reference);progress.caller_phase=12;
    progress.source_phase=f.operation->resume_phase_;
    const auto &bulk=f.operation->resume_clocks_;
    progress.bulk_assessment=unsigned(bulk.assessment);
    progress.prepare_assessment=unsigned(bulk.prepare.assessment);
    progress.enable_assessment=unsigned(bulk.enable.assessment);
    progress.prepare_entries=bulk.prepare_entries_returned;progress.enable_entries=bulk.enable_entries_returned;
    if(f.native_power_result.disposition==Disposition::Complete)s.stage=Stage::CpuReady;
    return finish(f.native_power_result);
}
IOReturn ZornGen7DarwinBoardOwner::constructNativeHeldSmmuRuntimePm(IOWorkLoop &loop,OSObject &owner)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || !s.smmu_power || !s.smmu_power->operation ||
       !s.smmu_power->native_reference || !s.smmu_power->native_claimant ||
       s.smmu_power->native_power_result.disposition!=ZornGen7ColdBoot::Disposition::Complete ||
       s.smmu_pm_attempted || !s.rsc_storage || !s.rsc_storage->usesCompletionWorkloop(loop) || loop.inGate())return finish(kIOReturnNotReady);
    s.smmu_pm_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(loop) || !retainDependency(owner))return finish(kIOReturnNoMemory);
    auto &f=*s.smmu_power;
    const auto raw=ZornGen7SmmuRuntimePm26::createNativeHeld(f.provider,*f.operation,*f.native_reference,
        *f.native_claimant,*s.gates.startup,loop,*s.rsc_storage,*this,owner,s.smmu_pm);
    if(raw!=kIOReturnSuccess)return finish(raw);
    // Exercise the real adapter once above the retained startup use. The
    // completed source reference must be returned unchanged,then balanced.
    const auto acquired=s.smmu_pm->resumeAndGet();
    if(acquired.operation.disposition!=ZornGen7ColdBoot::Disposition::Complete ||
       acquired.active_controller!=f.native_reference)return finish(kIOReturnNotReady);
    const auto busy=s.smmu_pm->markLastBusy(*acquired.active_controller);
    if(busy.disposition!=ZornGen7ColdBoot::Disposition::Complete)return finish(kIOReturnNotReady);
    const auto put=s.smmu_pm->putAutosuspend(*acquired.active_controller);
    if(put.disposition!=ZornGen7ColdBoot::Disposition::Complete)return finish(kIOReturnNotReady);
    s.smmu_pm_ready=true;s.stage=Stage::CpuReady;
    return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::constructOwnedSmmuRuntimePm(IOWorkLoop &loop,OSObject &owner,
    const ZornGen7SmmuRuntimeAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.stage!=Stage::CpuReady || !s.smmu_io_bound || !s.smmu_power || !s.smmu_power->operation ||
       s.smmu_pm_attempted || !s.rsc_storage || !s.rsc_storage->usesCompletionWorkloop(loop) ||
       loop.inGate())return finish(kIOReturnNotReady);
    s.smmu_pm_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(owner) || !retainDependency(loop))return finish(kIOReturnNoMemory);
    const auto raw=ZornGen7SmmuRuntimePm26::create(s.smmu_power->provider,*s.smmu_power->operation,
        *s.gates.startup,loop,*s.rsc_storage,*this,owner,authority,s.smmu_pm);
    if(raw!=kIOReturnSuccess)return finish(raw);
    s.smmu_pm_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::bindNativeClockGraphInputs(IOService &platform,IOService &rpmh,
    IOService &gcc,IOService &gpucc,const ZornGen7Clock::NativeClockFirmwareConsumer (&consumers)[4],
    const ZornGen7Clock::NativeClockFirmwareNode &smmu,OSObject &nodeOwner)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn r){IORecursiveLockUnlock(s.gates.startup);return r;};
    if(s.platform!=&platform || s.stage!=Stage::CpuReady || !s.owned_controller_fields_ready || !s.physical_clocks ||
       s.native_clock_nodes_attempted || s.clocks->graph_attempted_ || &gcc!=s.clock_provider_devices[0] ||
       &gpucc!=s.clock_provider_devices[1] || &rpmh==&gcc || &rpmh==&gpucc)return finish(kIOReturnNotReady);
    s.native_clock_nodes_attempted=true;s.stage=Stage::StoppedRetained;
    for(const auto &c:consumers)if(c.node_state!=ZornGen7Clock::ClockPropertyState::Present || !c.node ||
        c.lifetime!=&nodeOwner || c.node->lifetime!=&nodeOwner || !actualDeviceName({c.device_id,c.device_id_extent}))return finish(kIOReturnBadArgument);
    if(smmu.lifetime!=&nodeOwner || smmu.clock_count!=4 || smmu.name_count!=4 ||
       smmu.clocks_state!=ZornGen7Clock::ClockPropertyState::Present ||
       !smmu.clocks || !smmu.clock_names || !smmu.name_extents)return finish(kIOReturnBadArgument);
    for(size_t i=0;i<4;++i) {
        const auto &spec=smmu.clocks[i];const size_t provider=(i==0 || i==3)?2:1;
        if(spec.provider!=consumers[provider].node || spec.argument_count!=1 || !spec.arguments ||
           spec.arguments[0]!=ZornGen7SmmuPowerSource26::clock_indices[i])return finish(kIOReturnBadArgument);
        const char *expected=ZornGen7SmmuPowerSource26::clock_names[i];size_t n=0;while(expected[n])++n;
        if(smmu.name_extents[i]!=n+1u || !smmu.clock_names[i])return finish(kIOReturnBadArgument);
        for(size_t k=0;k<=n;++k)if(smmu.clock_names[i][k]!=expected[k])return finish(kIOReturnBadArgument);
    }
    OSSharedPtr<IORegistryEntry> drv(rpmh.copyParentEntry(gIOServicePlane),OSNoRetain),
        actualDrv(s.arc_parent_devices[0]?s.arc_parent_devices[0]->copyParentEntry(gIOServicePlane):nullptr,OSNoRetain);
    if(!drv || drv.get()!=actualDrv.get() || rpmh.getState()!=0 || rpmh.pm_vars)return finish(kIOReturnNotReady);
    if(!retainDependency(nodeOwner) || !retainDependency(rpmh))return finish(kIOReturnNoMemory);
    void *memory=allocate(sizeof(OwnedNativeClockController),alignof(OwnedNativeClockController));
    if(!memory)return finish(kIOReturnNoMemory);
    // Exact clk-rpmh source has no sync-state callback. Native PM is observed
    // from this genuine new provider; no disabled-PM success is supplied.
    s.owned_rpmh_controller=::new(memory) OwnedNativeClockController(rpmh,nullptr);
    if(s.owned_rpmh_controller->runtime_pm_enabled || !s.owned_rpmh_controller->name)return finish(kIOReturnNotReady);
    memory=allocate(sizeof(OwnedNativeClockGraphInputs),alignof(OwnedNativeClockGraphInputs));
    if(!memory)return finish(kIOReturnNoMemory);
    s.owned_native_clock_graph=::new(memory) OwnedNativeClockGraphInputs(s.physical_clocks->graph_fields_,consumers,*s.owned_rpmh_controller);
    // Bind actual same-owner provider-node identities, without publishing a
    // namespace, registering a clock, asserting consumer completion or invoking
    // sync. Required GCC/GPUCC source probe/proxy phases remain ahead.
    s.owned_controllers[0]->bound_node=consumers[1].node;
    s.owned_controllers[1]->bound_node=consumers[2].node;
    s.smmu_clock_node=&smmu;
    s.native_clock_nodes_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
bool ZornGen7DarwinBoardOwner::clockResourcePlatformAdmitted(IOService &platform) const
{
    if(!callable())return false;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    const bool admitted=s.platform==&platform && s.stage==Stage::CpuReady &&
        !s.clock_resources && !s.physical_attempted;
    IORecursiveLockUnlock(s.gates.startup);return admitted;
}
IOReturn ZornGen7DarwinBoardOwner::bindActualClockResources(IOService &platform,OSObject &resources,
    IOService &gcc_provider,IOService &gpucc_provider,
    const ZornGen7RegisterConfig::Region &gcc,const ZornGen7RegisterConfig::Region &gpucc)
{
    if(!callable() || &gcc_provider==&gpucc_provider || !gcc.mapped || !gpucc.mapped || !gcc.bytes || !gpucc.bytes ||
       gcc.source_word_origin || gpucc.source_word_origin)return kIOReturnBadArgument;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.platform!=&platform || s.stage!=Stage::CpuReady || s.clock_resources || s.physical_attempted) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    if(!retainDependency(resources) ||
       !retainDependency(gcc_provider) || !retainDependency(gpucc_provider)) {
        s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);return kIOReturnNoMemory;
    }
    s.clock_resources=&resources;s.owned_gcc=gcc;s.owned_gpucc=gpucc;
    s.clock_provider_devices[0]=&gcc_provider;s.clock_provider_devices[1]=&gpucc_provider;
    IORecursiveLockUnlock(s.gates.startup);return kIOReturnSuccess;
}
ZornGen7Clock::PhysicalClockBindingResult ZornGen7DarwinBoardOwner::constructPhysicalClockBindingsWithOwnedMappings(
    const ZornGen7Clock::ActualGmuPhysicalClockInputs &in,OSObject &fields)
{
    if(!callable() || in.gcc.mapped || in.gcc.bytes || in.gcc.source_word_origin ||
       in.gpucc.mapped || in.gpucc.bytes || in.gpucc.source_word_origin)return {};
    auto qualified=in;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.clock_resources || s.physical_attempted) {
        IORecursiveLockUnlock(s.gates.startup);return {};
    }
    qualified.gcc=s.owned_gcc;qualified.gpucc=s.owned_gpucc;
    IORecursiveLockUnlock(s.gates.startup);
    // Existing same-owner serialized construction performs the real allocation
    // and binds the eighteen native source clock fields to these actual maps.
    return constructPhysicalClockBindings(qualified,fields);
}
void ZornGen7DarwinBoardOwner::free()
{
    // After the first borrow, the extra real reference prevents destruction.
    // No teardown entry consumes that reference or releases the borrowed resources.
    if(storage_ && storage_->lifetime_pinned)return;
    if(storage_) {IOFree(storage_,sizeof(Storage));storage_=nullptr;}
    OSObject::free();
}

IOReturn ZornGen7DarwinBoardOwner::bindActualRscRuntime(IOService &platform,ZornGen7RscRuntime26 &rsc,
    ZornGen7Rpmh::NativeCommandCache &cache,ZornGen7Rpmh::NativeReservation &reservation)
{
    if(!callable() || !rsc.forwardAllowed())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.platform!=&platform || s.stage!=Stage::CpuReady || s.rsc_storage ||
        !s.command_db_storage || s.physical_attempted || s.arc_startup_attempted) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    if(!retainDependency(rsc)){IORecursiveLockUnlock(s.gates.startup);return kIOReturnNoMemory;}
    s.rsc_storage=&rsc;s.rsc_cache=&cache;s.rsc_reservation=&reservation;
    IORecursiveLockUnlock(s.gates.startup);return kIOReturnSuccess;
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedGmuFirmwareSeed(
    const HoujiFullHostNativeMemory &memory,OSObject &owner)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;
    const auto raw=ZornGen7SeedFirmwareAssets26(*s.smmu_domains,memory,owner);
    if(raw==kIOReturnSuccess){
        s.native_direct_memory_owner=OSDynamicCast(ZornGen7InactiveOwner26,&owner);
        s.stage=Stage::CpuReady;
    }
    IORecursiveLockUnlock(s.gates.startup);return raw;
}

IOReturn ZornGen7DarwinBoardOwner::holdOwnedGmuFirmware(
    HoujiFullHostNativeMemory &memory,OSObject &owner)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->holdGmuFirmware(memory,owner);
    if(raw==kIOReturnSuccess)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);return raw;
}

IOReturn ZornGen7DarwinBoardOwner::installOwnedGmuFaultIrq(OSObject &owner,
    const ZornGen7SmmuFaultIrqAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->installGmuFaultIrq(owner,authority);
    const bool ready=raw==kIOReturnSuccess && !s.smmu_domains->faulted();
    if(ready)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedGmuStreamSlot(OSObject &owner,
    const ZornGen7SmmuStreamAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->prepareGmuStreamSlot(owner,authority);
    const bool ready=raw==kIOReturnSuccess && !s.smmu_domains->faulted();
    if(ready)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::programOwnedGmuContext(unsigned budget)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->programGmuContext(budget);
    const bool ready=raw==kIOReturnSuccess && !s.smmu_domains->faulted();
    if(ready)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedGlobalSmmuFaults(OSObject &owner,
    const ZornGen7SmmuFaultIrqAuthority26 &authority,unsigned budget)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->prepareGlobalFaultReporting(owner,authority,budget);
    const bool ready=raw==kIOReturnSuccess && !s.smmu_domains->faulted();
    if(ready)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedSmmuController(OSObject &owner,
    const ZornGen7SmmuColdAuthority26 &cold,const ZornGen7SmmuFaultIrqAuthority26 &fault,unsigned budget)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains){IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;}
    s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->prepareControllerAndGlobalFaults(owner,cold,fault,budget);
    const bool ready=raw==kIOReturnSuccess && !s.smmu_domains->faulted();
    if(ready)s.stage=Stage::CpuReady;IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::activateOwnedGmuStream()
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->activateGmuStream();
    const bool ready=raw==kIOReturnSuccess && !s.smmu_domains->faulted();
    if(ready)s.stage=Stage::CpuReady;
    IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::loadOwnedGmuTcmAndShadow(OSObject &owner,const ZornGen7GmuLoadAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.smmu_domains_ready || !s.smmu_domains || !s.cold_gmu_clocks_ready || !s.gmu_ahb_ready || !s.cx_timer_ready) {
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.stage=Stage::StoppedRetained;const auto raw=s.smmu_domains->loadGmuTcmAndShadow(owner,authority);
    const bool ready=raw==kIOReturnSuccess && !s.smmu_domains->faulted();
    if(ready){s.gmu_tcm_loaded_ready=true;s.stage=Stage::CpuReady;}
    IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::enableOwnedGmuColdClocks(IOService &gpu,IOService &gmu,OSObject &treeOwner)
{
    // Preserved OEM HWSCHED source caller. This is not the host mainline.
    return enableOwnedGmuColdClocksAtSourceLevel(gpu,gmu,treeOwner,
        ZornGen7GmuFrequencySource26::source_hwsched_firstboot_level);
}
IOReturn ZornGen7DarwinBoardOwner::enableOwnedHostGmuColdClocks(IOService &gpu,IOService &gmu,OSObject &treeOwner)
{
    // Actual gen7_gmu_first_boot direct caller passes index0. Resolve its
    // frequency from the real K80 property;never import houji's rate literal.
    return enableOwnedGmuColdClocksAtSourceLevel(gpu,gmu,treeOwner,
        ZornGen7GmuFrequencySource26::source_direct_firstboot_level);
}
IOReturn ZornGen7DarwinBoardOwner::enableNativeHostGmuColdClocks(IOService &gpu,IOService &gmu,
    OSObject &treeOwner,ZornGen7NativeGmuClockResult26 &out)
{
    // Direct firstboot's actual source index0 and native K80 property/table.
    // Firmware residency is not consumed by this clock operation.
    const auto raw=enableOwnedHostGmuColdClocks(gpu,gmu,treeOwner);
    if(storage_ && normal()){
        IORecursiveLockLock(storage_->gates.startup);
        if(storage_->cold_gmu_clocks){
            const auto &actual=storage_->cold_gmu_clock_result;
            out.assessment=unsigned(actual.assessment);out.source_return_available=actual.source_return_available;
            out.source_return=actual.source_return;out.state_published=actual.state_published;
            out.rdpm_assessment=unsigned(actual.rdpm.assessment);out.frequency_available=actual.rdpm.actual_frequency_available;
            out.frequency_hz=actual.rdpm.actual_frequency_hz;out.gmu_return_available=actual.gmu.source_return_available;
            out.gmu_return=actual.gmu.source_return;out.hub_return_available=actual.hub.source_return_available;
            out.hub_return=actual.hub.source_return;out.bulk_assessment=unsigned(actual.bulk.assessment);
            out.prepare_assessment=unsigned(actual.bulk.prepare.assessment);out.enable_assessment=unsigned(actual.bulk.enable.assessment);
            out.prepare_entries=actual.bulk.prepare_entries_returned;out.enable_entries=actual.bulk.enable_entries_returned;
        }
        IORecursiveLockUnlock(storage_->gates.startup);
    }
    return raw;
}
IOReturn ZornGen7DarwinBoardOwner::enableOwnedGmuColdClocksAtSourceLevel(
    IOService &gpu,IOService &gmu,OSObject &treeOwner,unsigned sourceLevel)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.clocks || !s.smmu_domains_ready || !s.smmu_domains ||
       s.cold_gmu_clocks_attempted || sourceLevel>=ZornGen7GmuFrequencySource26::count ||
       !s.gen79_core_inputs_ready || !s.gen79_hub_metadata_published ||
       s.owned_native_list.assessment!=ZornGen7Clock::ClockConsumerListAssessment::ListPublished)
        return finish(kIOReturnNotReady);
    s.cold_gmu_clocks_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(gpu) || !retainDependency(gmu) || !retainDependency(treeOwner))return finish(kIOReturnNoMemory);
    // Consume actual native projection of the exact K80 frequency/voltage
    // property. A missing/changed input never falls back to another board's
    // GMU_FREQ_MIN/MAX, frequencies, bin or source-selected HWSCHED level.
    OSSharedPtr<OSObject> tableObject(gmu.copyProperty("qcom,gmu-freq-table"),OSNoRetain);
    auto *table=OSDynamicCast(OSData,tableObject.get());
    if(!table || table->getLength()!=sizeof(ZornGen7GmuFrequencySource26::native_bytes) ||
       !table->getBytesNoCopy())return finish(kIOReturnNotReady);
    const auto *bytes=static_cast<const uint8_t *>(table->getBytesNoCopy());
    for(size_t i=0;i<sizeof(ZornGen7GmuFrequencySource26::native_bytes);++i)
        if(bytes[i]!=ZornGen7GmuFrequencySource26::native_bytes[i])return finish(kIOReturnUnsupported);
    uint32_t words[4]{};
    for(unsigned i=0;i<4;++i) {
        const auto *at=bytes+i*4u;
        words[i]=uint32_t(at[0])|(uint32_t(at[1])<<8)|(uint32_t(at[2])<<16)|(uint32_t(at[3])<<24);
    }
    for(unsigned i=0;i<2;++i) {
        s.cold_gmu_frequencies[i]=words[2*i];s.cold_gmu_voltage_levels[i]=words[2*i+1];
    }
    OSSharedPtr<OSObject> namesObject(gpu.copyProperty("reg-names"),OSNoRetain);
    auto *names=OSDynamicCast(OSData,namesObject.get());
    // Exact actual native GPU resource list: source K80 also has no rdpm_cx.
    // No missing property, assumed NULL provider or map failure is relabeled
    // as source absence. A new resource list needs a real probe/map producer.
    constexpr char expectedNames[]="kgsl_3d0_reg_memory\0rscc\0cx_misc";
    if(!names || names->getLength()!=sizeof(expectedNames) || !names->getBytesNoCopy())
        return finish(kIOReturnUnsupported);
    const auto *nameBytes=static_cast<const uint8_t *>(names->getBytesNoCopy());
    for(size_t i=0;i<sizeof(expectedNames);++i)
        if(nameBytes[i]!=uint8_t(expectedNames[i]))return finish(kIOReturnUnsupported);
    s.cold_rdpm_cx_mapping=nullptr;s.cold_rdpm_cx_bytes=0;
    const auto *fields=s.clocks->initialFields();const auto *bulk=s.clocks->bulkFields();
    if(!fields || !bulk || fields->startup_gate!=s.gates.startup || !s.owned_gmu_software ||
       fields->hub_frequency!=&s.owned_gmu_software->hub_frequency ||
       fields->device_state!=&s.owned_gmu_software->device_state)return finish(kIOReturnNotReady);
    ZornGen7Clock::ActualInitialCxRdpmFields rdpm{s.cold_gmu_frequencies,2,
        &s.cold_rdpm_cx_mapping,&s.cold_rdpm_cx_bytes};
    void *memory=allocate(sizeof(ZornGen7Clock::GmuClockEnable),alignof(ZornGen7Clock::GmuClockEnable));
    if(!memory)return finish(kIOReturnNoMemory);
    s.cold_gmu_clocks=::new(memory) ZornGen7Clock::GmuClockEnable(*fields,rdpm,
        sourceLevel,*bulk,s.clocks->registry_.framework_);
    s.cold_gmu_clock_result=s.cold_gmu_clocks->runActual();const auto &result=s.cold_gmu_clock_result;
    if(!result.source_return_available)return finish(kIOReturnNotReady);
    if(result.source_return)return finish(kIOReturnIOError); // Raw source value remains separate in result.
    if(result.assessment!=ZornGen7Clock::GmuClockEnableAssessment::SourceReturned || !result.state_published ||
       s.smmu_domains->faulted() || (s.rsc_storage && !s.rsc_storage->forwardAllowed()))
        return finish(kIOReturnNotReady);
    s.native_cx_gpu=&gpu;
    s.native_cx_gmu=&gmu;
    s.cold_gmu_clocks_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
    // Whole source caller returned0/AWARE only; not an applied-frequency
    // readback, power/security/ownership grant, CM3 start or HFI readiness.
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedGmuAhbSource()
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.cold_gmu_clocks_ready || !s.gen79_core_inputs_ready ||
       !s.owned_gen79_core_inputs || s.gmu_ahb_attempted)return finish(kIOReturnNotReady);
    s.gmu_ahb_attempted=true;s.stage=Stage::StoppedRetained;
    // Exact source adreno_get_ahb_timeout_val returns0 before any clock read
    // when noc_timeout_us is0. Gen7.9.1's core omits it (static zero-init).
    // This is a known source-disabled operation, never a timer-ready claim.
    // A future nonzero source needs its actual conversion/access path; do not
    // silently replace it with this board's zero or another core's timeout.
    const auto &actual=*s.owned_gen79_core_inputs;
    if(actual.core_noc_timeout_us!=ZornGen79CoreSource26::noc_timeout_us ||
       actual.core_noc_timeout_us!=0)return finish(kIOReturnUnsupported);
    s.gmu_ahb_result=ZornGen7AhbControl::Program(nullptr,0,0);
    if(s.gmu_ahb_result.assessment!=ZornGen7AhbControl::Assessment::SourceDisabled ||
       s.gmu_ahb_result.writes_returned || s.smmu_domains->faulted() ||
       (s.rsc_storage && !s.rsc_storage->forwardAllowed()))return finish(kIOReturnNotReady);
    s.gmu_ahb_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::prepareNativeGlobalMaskedSmmuIrq(ZornGen7RegisterMaps26 &maps,
    OSObject &owner,ZornGen7NativeSmmuIrqResult26 &out)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.cx_timer_ready || !s.cold_gmu_clocks_ready ||
       !s.smmu_domains_ready || !s.smmu_domains || s.smmu_domains->faulted() ||
       (s.rsc_storage && !s.rsc_storage->forwardAllowed()))return finish(kIOReturnNotReady);
    s.stage=Stage::StoppedRetained;if(!retainDependency(maps) || !retainDependency(owner))return finish(kIOReturnNoMemory);
    const auto raw=s.smmu_domains->prepareNativeGlobalMaskedIrq(maps,owner,out);
    if(raw!=kIOReturnSuccess)return finish(raw);
    unsigned qtb=0;
    if(PE_parse_boot_argn("zorn26_qtb_fence",&qtb,sizeof(qtb)) && qtb==1){
        if(!s.gpu_icc_inputs_ready || !s.gpu_icc_qos_ready || !s.gpu_icc_inputs)return finish(kIOReturnNotReady);
        const auto fence=s.smmu_domains->prepareNativeQtbFence(owner,*s.gpu_icc_inputs,4096);
        if(fence!=kIOReturnSuccess)return finish(fence);
    }
    unsigned faults=0;
    if(PE_parse_boot_argn("zorn26_smmu_active_faults",&faults,sizeof(faults)) && faults==1){
        unsigned deferred=0;
        if(PE_parse_boot_argn("zorn26_gmu_deferred_valid",&deferred,sizeof(deferred)) && (deferred>=3 && deferred<=21)) {
            s.native_cx_maps=&maps;
            Zorn26RegisterGmuTcmHandoff(*s.smmu_domains,*this,
                [](OSObject &object,ZornGen7SmmuDomain26 &domain,const uint32_t (&versions)[5]) -> unsigned {
                    auto &board=static_cast<ZornGen7DarwinBoardOwner &>(object);
                    if(!board.storage_ || !board.normal())return 12;
                    auto &state=*board.storage_;
                    if(!IORecursiveLockHaveLock(state.gates.startup) || state.stage!=Stage::CpuReady ||
                       state.smmu_domains!=&domain || domain.faulted() || !state.cx_timer_ready ||
                       !state.smmu_domains_ready || !state.cold_gmu_clocks_ready || !state.gmu_ahb_ready ||
                       state.gmu_tcm_loaded_ready || !state.owned_gmu_software ||
                       (state.rsc_storage && !state.rsc_storage->forwardAllowed()))return 12;
                    for(unsigned i=0;i<5;++i)state.owned_gmu_software->versions[i]=versions[i];
                    state.gmu_tcm_loaded_ready=true;

                    if(!state.native_cx_root || !state.native_cx_gpu)return 13;
                    auto &root=*state.native_cx_root;
                    OSSharedPtr<IORegistryEntry> gpu(IORegistryEntry::fromPath(
                        "arm-io/gpu",gIODTPlane,nullptr,nullptr,&root),OSNoRetain);
                    OSSharedPtr<IORegistryEntry> scm(IORegistryEntry::fromPath(
                        "firmware/qcom_scm",gIODTPlane,nullptr,nullptr,&root),OSNoRetain);
                    if(gpu.get()!=state.native_cx_gpu || !scm)return 13;
                    OSSharedPtr<OSObject> compatible(scm->copyProperty("compatible"),OSNoRetain);
                    auto *data=OSDynamicCast(OSData,compatible.get());
                    constexpr char expected[]="qcom,scm-v1.1\0qcom,scm";
                    if(!data || data->getLength()!=sizeof(expected) || !data->getBytesNoCopy() ||
                       memcmp(data->getBytesNoCopy(),expected,sizeof(expected)))return 14;
                    const auto *inputs=state.owned_gen79_core_inputs;
                    if(!state.gen79_core_inputs_ready || !inputs || !inputs->core_features ||
                       *inputs->core_features!=ZornGen79CoreSource26::features ||
                       !(*inputs->core_features&(1UL<<12)) || (*inputs->core_features&(1UL<<20)))
                        return 15;
                    unsigned mode=0;
                    if(!PE_parse_boot_argn("zorn26_gmu_deferred_valid",&mode,sizeof(mode)) || (mode<4 || mode>21))
                        return 16;
                    if(!state.native_cx_maps || !state.native_cx_maps->providerClaimsHeld() ||
                       !state.cx_core || !state.cx_core->registered || !state.cx_core->use_count ||
                       !state.cx_completion_result.registered || !state.smmu_power || !state.smmu_pm ||
                       !state.smmu_pm->nativeHeldFor(state.smmu_power->provider,*state.gates.startup))
                        return 17;

                    using namespace ZornGen7ColdBoot;
                    const ZornGen7ScmAuthority26 authority{&board,
                        [](void *cookie,IOService &actualGpu,IORegistryEntry &actualScm,
                            uint32_t request,uint32_t budget) -> OperationResult {
                            auto &owner=*static_cast<ZornGen7DarwinBoardOwner *>(cookie);
                            auto &current=*owner.storage_;
                            const bool held=IORecursiveLockHaveLock(current.gates.startup) &&
                                current.stage==Stage::StoppedRetained && current.cx_security_attempted &&
                                current.gmu_tcm_loaded_ready && current.cx_timer_ready &&
                                current.native_cx_gpu==&actualGpu && current.native_cx_scm==&actualScm &&
                                request==0xbu && budget==16 &&
                                current.native_cx_maps->providerClaimsHeld() &&
                                current.cx_core->registered && current.cx_core->use_count &&
                                current.smmu_pm->nativeHeldFor(current.smmu_power->provider,*current.gates.startup) &&
                                !current.smmu_domains->faulted() && current.rsc_storage &&
                                current.rsc_storage->forwardAllowed();
                            return {held?Disposition::Complete:Disposition::Unavailable,StatusDomain::Unavailable,0,0};
                        }};
                    // The retained SMMU/rail and exact provider claims produce the
                    // hardware grant. ScmOwner holds the shared normal-call gate
                    // for the probe/init and any secure continuation.
                    state.native_cx_scm=scm.get();
                    const auto raw=board.initializeOwnedCxSecurity(root,*state.native_cx_gpu,board,authority,16);
                    state.native_cx_scm=nullptr;
                    if(state.cx_scm_result.raw_status_available){
                        nativeCxScmStatus=state.cx_scm_result.raw_status;
                        __atomic_store_n(&nativeCxScmStatusAvailable,true,__ATOMIC_RELEASE);
                    }
                    if(raw!=kIOReturnSuccess || !state.cx_security_ready)
                        return state.cx_scm_result.raw_status_available?19:18;
                    if(mode==4)return 20;
                    auto &maps=*state.native_cx_maps;
                    const auto resetHeld=[&]() {
                        uint64_t reset=0,gx=0;
                        return !maps.access(0x3d00000u+0x1f800u*4u,4,false,reset) &&
                            !maps.access(0x3d00000u+0x1f8d0u*4u,4,false,gx) &&
                            (reset&1u) && (gx&3u)==3u;
                    };
                    if(!state.native_cx_gmu || !resetHeld() || domain.faulted())return 21;
                    state.native_gmu_irq_loop=IOWorkLoop::workLoop();
                    if(!state.native_gmu_irq_loop)return 21;
                    state.native_gmu_config_window=true;
                    const auto irq=board.prepareOwnedGmuIrqs(*state.native_cx_gmu,maps,
                        *state.native_gmu_irq_loop,board,{});
                    const auto config=irq==kIOReturnSuccess?board.configureOwnedGmuRegisters():irq;
                    const bool configured=config==kIOReturnSuccess && resetHeld() &&
                        !domain.faulted() && !state.gmu_irq->halted();
                    const auto hfi=configured && mode>=6 ?
                        board.prepareOwnedDirectHfi(*state.native_gmu_irq_loop) : kIOReturnNotReady;
                    const bool hfiBound=hfi==kIOReturnSuccess && resetHeld() &&
                        !domain.faulted() && !state.gmu_irq->halted() && !state.direct_hfi->halted();
                    const auto icc=hfiBound && mode>=7 && state.platform ?
                        board.prepareOwnedGpuIccInputs(*state.platform,root,*state.native_cx_gpu,board) :
                        kIOReturnNotReady;
                    const bool iccBound=icc==kIOReturnSuccess && resetHeld() &&
                        !domain.faulted() && !state.gmu_irq->halted() && !state.direct_hfi->halted();
                    const auto votes=iccBound && mode>=8 ?
                        board.initializeOwnedGpuIccVotes() : kIOReturnNotReady;
                    const bool votesReady=votes==kIOReturnSuccess && resetHeld() &&
                        !domain.faulted() && !state.gmu_irq->halted() && !state.direct_hfi->halted();
                    IOReturn qos=kIOReturnNotReady;
                    if(votesReady && mode>=9 && state.gpu_icc_initial_ready && state.rsc_storage &&
                       state.rsc_storage->forwardAllowed() && maps.providerClaimsHeld()){
                        state.stage=Stage::StoppedRetained;
                        state.gpu_icc_qos_attempted=true;
                        qos=state.gpu_icc_inputs->prepareNativeQos(board,mode>=10);
                    }
                    state.native_gmu_config_window=false;
                    if(irq!=kIOReturnSuccess)return 22;
                    if(!configured)return 23;
                    if(mode==5)return 24;
                    if(!hfiBound)return 25;
                    if(mode==6)return 26;
                    if(!iccBound)return 27;
                    if(mode==7)return 28;
                    if(!votesReady)return 29;
                    if(mode==8)return 30;
                    if(qos!=kIOReturnSuccess || !resetHeld() || domain.faulted() ||
                       state.gmu_irq->halted() || state.direct_hfi->halted() ||
                       !state.rsc_storage->forwardAllowed())return 31;
                    state.gpu_icc_qos_ready=true;
                    state.stage=Stage::CpuReady;
                    if(mode<11)return 32;
                    state.stage=Stage::StoppedRetained;
                    const auto arm=state.direct_hfi->armBoundReceiver();
                    const auto irqReady=[&]() {
                        return !domain.faulted() && !state.gmu_irq->halted() &&
                            state.gmu_irq->forwardAllowed() && state.direct_hfi->healthy() &&
                            state.rsc_storage->forwardAllowed();
                    };
                    if(arm!=kIOReturnSuccess || !resetHeld() || !irqReady()){
                        state.gmu_irq->stopAndMask();
                        return 33;
                    }
                    state.stage=Stage::CpuReady;
                    if(mode==11)return 34;

                    state.gpu_bootstrap_bw_attempted=true;
                    state.stage=Stage::StoppedRetained;
                    const auto bandwidth=state.gpu_icc_inputs->applyBootstrapBandwidth();
                    if(bandwidth!=kIOReturnSuccess || !resetHeld() || !irqReady()){
                        state.gmu_irq->stopAndMask();
                        return 35;
                    }
                    state.gpu_bootstrap_bw_ready=true;
                    state.stage=Stage::CpuReady;
                    if(mode==12)return 36;

                    // The actual map, startup gate, CX SCM epoch, stream, timer,
                    // IRQ and bootstrap vote all belong to this same board.
                    state.stage=Stage::StoppedRetained;
                    const ZornGen7GmuStartAuthority26 start{&board,
                        [](void *cookie,IOService &gmu,IOMemoryDescriptor &descriptor,
                           uint64_t physical,size_t bytes) -> int {
                            auto &owner=*static_cast<ZornGen7DarwinBoardOwner *>(cookie);
                            auto &current=*owner.storage_;
                            if(!owner.normal() || !IORecursiveLockHaveLock(current.gates.startup) ||
                               current.stage!=Stage::StoppedRetained || current.native_cx_gmu!=&gmu ||
                               !current.cx_security_ready || !current.cx_scm_owner ||
                               !current.gpu_bootstrap_bw_ready || !current.gmu_tcm_loaded_ready ||
                               !current.gmu_config_ready || !current.native_cx_maps->providerClaimsHeld() ||
                               !current.smmu_pm || !current.smmu_power ||
                               !current.smmu_pm->nativeHeldFor(current.smmu_power->provider,*current.gates.startup) ||
                               current.smmu_domains->faulted() || !current.direct_hfi->healthy() ||
                               !current.gmu_irq->forwardAllowed() || !current.rsc_storage->forwardAllowed() ||
                               physical!=0x3d68000u || bytes!=0x37000u || descriptor.getLength()!=bytes)
                                return kIOReturnNotReady;
                            IOByteCount contiguous=0;
                            if(descriptor.getPhysicalSegment(0,&contiguous,kIOMemoryMapperNone)!=physical ||
                               contiguous<bytes)return kIOReturnBadArgument;
                            uint64_t reset=0,gx=0;
                            if(current.native_cx_maps->access(0x3d00000u+0x1f800u*4u,4,false,reset) ||
                               current.native_cx_maps->access(0x3d00000u+0x1f8d0u*4u,4,false,gx) ||
                               !(reset&1u) || (gx&3u)!=3u)return kIOReturnNotReady;
                            return kIOReturnSuccess;
                        },nullptr};
                    if(maps.startHostCm3(board,start)!=kIOReturnSuccess || !irqReady()){
                        state.gmu_irq->stopAndMask();
                        return 37;
                    }
                    state.stage=Stage::CpuReady;
                    if(mode==13)return 38;

                    // The K80 direct cold path programs PDC and RSCC after
                    // CM3 initialization and before starting HFI control.
                    state.stage=Stage::StoppedRetained;
                    if(!state.owned_gmu_software || state.pdc_rsc_attempted ||
                       !state.gen79_core_inputs_ready || !irqReady() ||
                       !maps.providerClaimsHeld()){
                        state.gmu_irq->stopAndMask();
                        return 39;
                    }
                    state.pdc_rsc_attempted=true;
                    const auto pdc=maps.loadPdcRsc(board,&state.owned_gmu_software->flags);
                    if(pdc!=kIOReturnSuccess || !irqReady()){
                        state.gmu_irq->stopAndMask();
                        return 39;
                    }
                    state.pdc_rsc_ready=true;
                    state.stage=Stage::CpuReady;
                    if(mode==14)return 40;

                    // gen7_gmu_hfi_start: one control write and a bounded
                    // init-bit poll. The source resets queue indices at
                    // gen7_hfi_start, together with the first protocol command.
                    state.stage=Stage::StoppedRetained;
                    auto &receiver=*state.gmu_irq;
                    uint32_t init=1,status=0;
                    int result=receiver.accessHfiWord(0x1f986,true,init);
                    uint32_t observed=1u<<31;
                    if(!result){
                        observed|=1u<<30;
                        uint64_t deadline=0;
                        clock_interval_to_deadline(100,1000000,&deadline);
                        for(;;){
                            result=receiver.accessHfiWord(0x1f980,false,status);
                            if(result)break;
                            observed|=1u<<29;
                            if((status&1u) || !irqReady())break;
                            uint64_t now=0;
                            clock_get_uptime(&now);
                            if(now>=deadline)break;
                            delay_for_interval_with_leeway(26,74,1000);
                        }
                    }
                    observed|=(uint32_t(result)&0xfffu)<<16;
                    observed|=status&0xffffu;
                    __atomic_store_n(&nativeHfiControlObservation,observed,__ATOMIC_RELEASE);
                    if(result || !(status&1u) || !irqReady()){
                        receiver.stopAndMask();
                        return 41;
                    }
                    state.stage=Stage::CpuReady;
                    if(mode==15)return 42;

                    // Probe the first no-record K80 stock GET_VALUE
                    // (GMU_WARMBOOT, subtype zero) on the three-queue
                    // direct receiver. Do not switch the firmware into
                    // a scheduling mode or start CP.
                    state.stage=Stage::StoppedRetained;
                    const uint32_t payload[]={125,0};
                    const auto reply=state.direct_hfi->exchange(12,payload,2);
                    const uint32_t minor=(versions[4]>>16)&0xfffu;
                    nativeHfiQueryObservation[1]=reply.packet[0];
                    nativeHfiQueryObservation[2]=reply.packet[1];
                    nativeHfiQueryObservation[3]=reply.packet[2];
                    nativeHfiQueryObservation[4]=reply.packet[3];
                    const uint32_t detail=(1u<<31) | (uint32_t(reply.outcome)<<24) |
                        (reply.words<<16) | minor;
                    __atomic_store_n(&nativeHfiQueryObservation[0],detail,__ATOMIC_RELEASE);
                    using Outcome=ZornGen7DirectHfi26::Outcome;
                    if(reply.outcome!=Outcome::ReturnedAck ||
                       (minor>4 ? (reply.words<4 || reply.packet[3]!=0 || reply.packet[2]>1) :
                           (reply.words<3 || reply.packet[2]!=0)) || !irqReady()){
                        receiver.stopAndMask();
                        return 43;
                    }
                    state.stage=Stage::CpuReady;
                    if(mode==16)return 44;

                    // The bound AB Power SKU selects source bin 3 for every
                    // possible corrected speed fuse. The host compared this
                    // device's actual GPU/GMU tables to the retained source.
                    constexpr uint8_t sourceDigest[]={ 0xb0, 0x82, 0xa6, 0xb8, 0x81, 0x3d, 0x39, 0x2b, 0x6f, 0xdb, 0x55, 0x4e, 0xd4, 0x62, 0x12, 0xa9, 0xb0, 0x64, 0xa7, 0x39, 0x9f, 0x34, 0x1d, 0xd2, 0x91, 0x0b, 0x06, 0x81, 0x9f, 0x08, 0xf5, 0x11 };
                    const ZornGen7HostTableSelection26 selection{sourceDigest,3,board};
                    const auto prepared=board.prepareOwnedHostTables(selection);
                    if(prepared!=kIOReturnSuccess || !state.host_tables || !irqReady()){
                        __atomic_store_n(&nativeHfiPerfObservation[0],uint32_t(prepared),__ATOMIC_RELEASE);
                        receiver.stopAndMask();
                        return 45;
                    }
                    state.stage=Stage::StoppedRetained;
                    uint32_t perf[4]{};
                    const auto sent=state.host_tables->sendDirectPerformance(*state.direct_hfi,versions[4],perf);
                    for(unsigned i=0;i<4;++i)nativeHfiPerfObservation[i+1]=perf[i];
                    __atomic_store_n(&nativeHfiPerfObservation[0],uint32_t(sent),__ATOMIC_RELEASE);
                    if(sent!=kIOReturnSuccess || !irqReady()){
                        receiver.stopAndMask();
                        return 45;
                    }
                    state.stage=Stage::CpuReady;
                    if(mode==17)return 46;

                    state.stage=Stage::StoppedRetained;
                    uint32_t bw[4]{};
                    const auto bwSent=state.host_tables->sendDirectBandwidth(*state.direct_hfi,bw);
                    for(unsigned i=0;i<4;++i)nativeHfiBwObservation[i+1]=bw[i];
                    __atomic_store_n(&nativeHfiBwObservation[0],uint32_t(bwSent),__ATOMIC_RELEASE);
                    if(bwSent!=kIOReturnSuccess || !irqReady()){
                        receiver.stopAndMask();
                        return 47;
                    }
                    state.stage=Stage::CpuReady;
                    if(mode==18)return 48;

                    // This cold path has no acquired GPU AOP mailbox, so
                    // the source ACD condition stays false. Gen7.9.1 has no
                    // CLX feature. Use the same BCL state published by SCM
                    // and the Gen7.9.1 IFPC cold-probe timer value.
                    state.stage=Stage::StoppedRetained;
                    if(!state.cx_bcl_publication_valid || !state.cx_bcl_enabled_after_scm ||
                       !(*state.owned_gen79_core_inputs->core_features&(1ul<<6))){
                        receiver.stopAndMask();
                        return 49;
                    }
                    const uint32_t bcl[]={11,1,ZornGen79CoreSource26::bcl_data};
                    const uint32_t ifpc[]={9,1,0x1680};
                    const uint32_t core[]={0};
                    const struct {unsigned id;const uint32_t *payload;size_t words;bool v5;} commands[]={
                        {11,bcl,3,minor>4}, {11,ifpc,3,minor>4}, {14,core,1,false}
                    };
                    for(unsigned i=0;i<3;++i){
                        const auto &cmd=commands[i];
                        const auto answer=state.direct_hfi->exchange(cmd.id,cmd.payload,cmd.words);
                        nativeHfiCoreObservation[i]=((i+1u)<<28) | (uint32_t(answer.outcome)<<24) |
                            (answer.words<<16) | ((answer.packet[2]&0xffu)<<8) | (answer.packet[3]&0xffu);
                        nativeHfiCoreObservation[3]=answer.packet[1];
                        using Outcome=ZornGen7DirectHfi26::Outcome;
                        const bool accepted=answer.outcome==Outcome::ReturnedAck &&
                            (cmd.v5 ? (answer.words>=4 && answer.packet[3]==0 && !(answer.packet[2]>>31)) :
                                (answer.words>=3 && answer.packet[2]==0));
                        if(!accepted || !irqReady()){
                            receiver.stopAndMask();
                            return 49;
                        }
                    }
                    state.stage=Stage::CpuReady;
                    if(mode==19)return 50;

                    // Proven bound AB SKU bin 3 has 12 levels and selects
                    // row 11 as its default. PERF prepends the zero row.
                    constexpr uint32_t activeRows=12,defaultLevel=11;
                    constexpr uint32_t perfIndex=activeRows-defaultLevel;
                    constexpr uint32_t invalidClock=0xffu,invalidAB=0xffff00ffu;
                    // The source's first AXI bus request has fresh zero
                    // bus state and the same default row's qcom,bus-freq=1.
                    // Before its AB query the GMU sees the unsupported-AB
                    // sentinel. The host average and AB query are a later step.
                    constexpr uint32_t initialBus=1;
                    const uint32_t clockVote[]={1,perfIndex,invalidAB};
                    const uint32_t busVote[]={1,invalidClock,0xffff0000u|initialBus};
                    const uint32_t abQuery[]={122,0};
                    state.stage=Stage::StoppedRetained;
                    const auto clock=state.direct_hfi->exchange(30,clockVote,3);
                    using Outcome=ZornGen7DirectHfi26::Outcome;
                    const auto accepted=[&](const ZornGen7DirectHfi26::Reply &ack){
                        return ack.outcome==Outcome::ReturnedAck && ack.words>=3 && !ack.packet[2] && irqReady();
                    };
                    const auto dcvsDetail=[](const ZornGen7DirectHfi26::Reply &ack){
                        return (uint32_t(ack.outcome)<<24) | (ack.words<<16) |
                            ((ack.packet[2]&0xffu)<<8) | (ack.packet[3]&0xffu);
                    };
                    nativeHfiDcvsObservation[0]=dcvsDetail(clock);
                    if(!accepted(clock)){receiver.stopAndMask();return 51;}
                    const auto bus=state.direct_hfi->exchange(30,busVote,3);
                    nativeHfiDcvsObservation[1]=dcvsDetail(bus);
                    if(!accepted(bus)){receiver.stopAndMask();return 51;}
                    const auto ab=state.direct_hfi->exchange(12,abQuery,2);
                    nativeHfiDcvsObservation[2]=dcvsDetail(ab);
                    nativeHfiDcvsObservation[3]=ab.packet[1];
                    nativeHfiDcvsObservation[4]=ab.packet[2];
                    if(ab.outcome!=Outcome::ReturnedAck || ab.words<4 || ab.packet[3] ||
                       ab.packet[2]>1 || !irqReady()){
                        receiver.stopAndMask();
                        return 51;
                    }
                    state.stage=Stage::CpuReady;
                    if(mode==20)return 52;

                    // Complete source bootstrap unvote with average preserved
                    // as the default bus request originally delegated to HLOS.
                    constexpr uint32_t firstDdr=2136718u,lastDdr=16500000u;
                    const uint32_t average=ZornGen7HostBandwidth26::freshAverageMbps(firstDdr);
                    uint32_t bandwidthWord=0;
                    state.stage=Stage::StoppedRetained;
                    uint32_t steps=0;
                    const auto stopTables=[&](uint32_t raw) {
                        __atomic_store_n(&nativeGpuTablesObservation,(steps<<24)|(raw&0xffffffu),__ATOMIC_RELEASE);
                        receiver.stopAndMask();
                        return 53;
                    };
                    if(!state.native_direct_memory_owner ||
                       !ZornGen7HostBandwidth26::encodeAb(ab.packet[2]==1,average,lastDdr,bandwidthWord))
                        return stopTables(kIOReturnNotReady);
                    const auto unvote=state.gpu_icc_inputs->finishHostBootstrap();
                    if(unvote!=kIOReturnSuccess || !irqReady())return stopTables(unvote);
                    state.host_bootstrap_unvoted=true;
                    steps|=1u;
                    if(ab.packet[2]==1){
                        const uint32_t averageVote[]={1,0xffu,bandwidthWord|0xffu};
                        if(!accepted(state.direct_hfi->exchange(30,averageVote,3)))
                            return stopTables(kIOReturnNotReady);
                    }else{
                        const auto raw=state.gpu_icc_inputs->applyHostAverageMbps(average);
                        if(raw!=kIOReturnSuccess || !irqReady())return stopTables(raw);
                    }
                    steps|=2u;
                    state.stage=Stage::CpuReady;
                    const auto tables=state.native_direct_memory_owner->prepareHostGpuTables();
                    if(tables!=kIOReturnSuccess || !irqReady())return stopTables(tables);
                    __atomic_store_n(&nativeGpuTablesObservation,0x07000000u,__ATOMIC_RELEASE);
                    state.stage=Stage::CpuReady;
                    return 54;
                },
                [](OSObject &object,ZornGen7SmmuDomain26 &domain,ZornHostMmuFence run) -> unsigned {
                    auto &board=static_cast<ZornGen7DarwinBoardOwner &>(object);
                    auto &s=*board.storage_;
                    uint32_t steps=0;
                    const auto forward=[&](){
                        return !domain.faulted() && s.gmu_irq && s.gmu_irq->forwardAllowed() &&
                            s.direct_hfi && s.direct_hfi->healthy() && s.rsc_storage &&
                            s.rsc_storage->forwardAllowed();
                    };
                    IOReturn raw=kIOReturnNotReady;
                    if(IORecursiveLockHaveLock(s.gates.startup) && s.stage==Stage::CpuReady &&
                       s.smmu_domains==&domain && s.host_gpu_tables_attempted &&
                       !s.host_gpu_mmu_attempted && !s.host_gpu_oob_attempted &&
                       s.host_bootstrap_unvoted && s.native_direct_memory_owner &&
                       s.native_direct_memory_owner->gpuProviderClaimsHeld() && s.native_cx_maps &&
                       s.native_cx_maps->boundAndReadyForGpuStart(*s.native_direct_memory_owner) &&
                       s.gpu_icc_qos_ready && s.gpu_icc_inputs && forward()){
                        s.stage=Stage::StoppedRetained;
                        raw=run(domain,board,*s.gpu_icc_inputs,4096,steps);
                        if(!raw && !forward())raw=kIOReturnNotReady;
                        if(!raw)s.stage=Stage::CpuReady;
                    }
                    Zorn26RecordHostMmuFence(steps,raw);
                    if(raw)return 63;
                    uint32_t progress=0,gx=0,ackValue=0,hostValue=0;
                    const auto observe=[&](IOReturn result){
                        nativeGpuOobObservation[0]=progress;
                        nativeGpuOobObservation[1]=uint32_t(result);
                        nativeGpuOobObservation[2]=gx;
                        nativeGpuOobObservation[3]=ackValue;
                        nativeGpuOobObservation[4]=hostValue;
                        return result?65u:66u;
                    };
                    if(!forward() || !s.native_cx_maps || s.host_gpu_oob_attempted ||
                       !s.native_direct_memory_owner->gpuProviderClaimsHeld() ||
                       !s.smmu_pm->nativeHeldFor(s.smmu_power->provider,*s.gates.startup))
                        return observe(kIOReturnNotReady);
                    s.host_gpu_oob_attempted=true;
                    s.host_gpu_mmu_ready=true;
                    s.stage=Stage::StoppedRetained;
                    auto &maps=*s.native_cx_maps;
                    const auto read=[&](uint32_t word,uint32_t &value){
                        return forward() && !maps.accessGmuHfiWord(word,false,value);
                    };
                    const auto write=[&](uint32_t word,uint32_t value){
                        return forward() && !maps.accessGmuHfiWord(word,true,value);
                    };
                    constexpr uint32_t request=1u<<30,ack=1u<<31;
                    if(!read(0x1f8d0,gx) || !read(0x1f992,ackValue) || !read(0x1f996,hostValue))
                        return observe(kIOReturnIOError);
                    if((gx&3u)!=3u || (ackValue&ack) || (hostValue&(request|ack)))
                        return observe(kIOReturnNotReady);
                    progress|=1;
                    if(!write(0x1f994,request))return observe(kIOReturnIOError);
                    progress|=2;
                    const auto poll=[&](uint32_t word,uint32_t mask,uint32_t expected,uint32_t &value){
                        uint64_t deadline=0;
                        clock_interval_to_deadline(100,1000000,&deadline);
                        for(;;){
                            if(!read(word,value))return kIOReturnIOError;
                            if((value&mask)==expected)return kIOReturnSuccess;
                            uint64_t now=0;
                            clock_get_uptime(&now);
                            if(now>=deadline)return kIOReturnTimeout;
                            delay_for_interval_with_leeway(26,74,1000);
                        }
                    };
                    raw=poll(0x1f992,ack,ack,ackValue);
                    if(raw)return observe(raw);
                    progress|=4;
                    if(!write(0x1f991,ack))return observe(kIOReturnIOError);
                    progress|=8;
                    if(!read(0x1f992,ackValue) || (ackValue&ack))
                        return observe(kIOReturnNotReady);
                    progress|=16;
                    raw=poll(0x1f8d0,3u,0u,gx);
                    if(raw)return observe(raw);
                    progress|=32;
                    s.host_gpu_oob_ready=true;
                    __atomic_store_n(&s.direct_oob_epoch,1u,__ATOMIC_RELEASE);
                    s.stage=Stage::CpuReady;
                    observe(kIOReturnSuccess);
                    const auto start=s.direct_hfi->exchange(10,nullptr,0);
                    nativeGpuStartObservation[0]=uint32_t(start.outcome);
                    nativeGpuStartObservation[1]=start.words;
                    for(unsigned i=0;i<3;++i)nativeGpuStartObservation[2+i]=start.packet[i];
                    using Outcome=ZornGen7DirectHfi26::Outcome;
                    if(start.outcome!=Outcome::ReturnedAck || start.words!=3 ||
                       start.packet[2] || (start.packet[1]&0xffu)!=10 ||
                       ((start.packet[1]>>8)&0xffu)!=1 || !forward()){
                        s.stage=Stage::StoppedRetained;
                        return 67;
                    }
                    const auto code=s.native_direct_memory_owner->bindHostGpuCode();
                    Zorn26RecordCodeBindResult(code);
                    if(code)return 69;
                    ZornGen7GpuRegisterAuthority26 authority{};
                    const auto configured=s.native_direct_memory_owner->configureHostGpuRegisters(board,authority);
                    Zorn26RecordGxRegistersResult(configured);
                    if(configured)return 71;
                    ZornGen7GpuIrqAuthority26 irqAuthority{};
                    const auto irq=s.native_direct_memory_owner->prepareHostGpuIrq(*s.native_gmu_irq_loop,board,irqAuthority);
                    Zorn26RecordGpuIrqResult(irq);
                    if(irq)return 73;
                    ZornGen7CpStartAuthority26 cpAuthority{};
                    const auto cp=s.native_direct_memory_owner->initializeHostCp(board,cpAuthority);
                    Zorn26RecordCpResult(cp);if(cp)return 75;
                    ZornGen7ZapAuthority26 zapAuthority{};
                    const auto zap=s.native_direct_memory_owner->authenticateHostZap(board,zapAuthority);
                    Zorn26RecordZapResult(zap);if(zap)return 77;
                    ZornGen7CpBootstrapAuthority26 bootstrap{};
                    const auto complete=s.native_direct_memory_owner->completeHostBootstrap(board,bootstrap);
                    Zorn26RecordBootstrapResult(complete);if(complete)return 79;
                    ZornGen7DirectRuntimeAuthority26 runtime{};
                    const auto attached=s.native_direct_memory_owner->prepareHostDirectRuntime(board,runtime,4096);
                    Zorn26RecordRuntimeResult(attached);if(attached)return 81;
                    const auto image=s.native_direct_memory_owner->runHostKnownImage();
                    Zorn26RecordKnownImageResult(image);if(image)return 83;
                    // The existing publication/grant path requires no startup
                    // lock across service/client callouts. This callback owns
                    // that lock on entry and must restore it before returning.
                    auto *owner=s.native_direct_memory_owner;auto *ring=s.host_ring;
                    IOReturn client=kIOReturnNotReady;
                    if(IORecursiveLockHaveLock(s.gates.startup) && s.stage==Stage::CpuReady &&
                       s.host_known_image_ready && owner && ring && forward()){
                        owner->retain();ring->retain();
                        IORecursiveLockUnlock(s.gates.startup);
                        if(!IORecursiveLockHaveLock(s.gates.startup)){
                            // Native Board supplies its actual app authority.
                            // Do not consume the mutually exclusive kernel-client session.
                            ZornGen7AppAuthority26 application{};
                            // Actual known-image path above returned success. Keep the
                            // original startup unlock across this diagnostic wait and callout.
                            // Timeout retains the existing stopped resources and skips publication.
                            if(zorn26_gpu_diagnostic_gate203(2))
                                client=owner->publishHostApplicationIo(board,application);
                            else client=kIOReturnTimeout;
                        }
                        IORecursiveLockLock(s.gates.startup);
                        if(!client && (s.native_direct_memory_owner!=owner || s.host_ring!=ring ||
                           s.stage!=Stage::CpuReady || !s.host_known_image_ready || !forward()))
                            client=kIOReturnNotReady;
                        ring->release();owner->release();
                    }
                    if(client)s.stage=Stage::StoppedRetained;
                    __atomic_store_n(&nativeApplicationPublication,
                        (UINT64_C(1)<<32)|uint32_t(client),__ATOMIC_RELEASE);
                    return client?87:88;
                });
        }
        const auto control=s.smmu_domains->prepareNativeActiveGlobalFaults(maps,out.control,4096);
        if(control!=kIOReturnSuccess)return finish(control);
    }
    if(s.smmu_domains->faulted() || (s.rsc_storage && !s.rsc_storage->forwardAllowed()))return finish(kIOReturnNotReady);
    s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::initializeNativeCxTimer(ZornGen7RegisterMaps26 &maps,
    IOService &gpu,IOService &gmu,OSObject &owner,ZornGen7NativeCxTimerResult26 &out)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gmu_ahb_ready || !s.cold_gmu_clocks_ready ||
       !s.gen79_core_inputs_ready || !s.smmu_domains_ready || !s.smmu_domains ||
       s.cx_timer_attempted || s.smmu_domains->faulted() ||
       (s.rsc_storage && !s.rsc_storage->forwardAllowed()))return finish(kIOReturnNotReady);
    s.cx_timer_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(maps) || !retainDependency(owner))return finish(kIOReturnNoMemory);
    // Same actual startup gate pins clock/core power state through both IRQ
    // regions and any Darwin AST on restore. No generic guard is fabricated.
    const auto raw=maps.initializeNativeFreshCxTimer(gpu,gmu,*s.gates.startup,owner,out);
    if(raw!=kIOReturnSuccess)return finish(raw);
    if(s.smmu_domains->faulted() || (s.rsc_storage && !s.rsc_storage->forwardAllowed()))
        return finish(kIOReturnNotReady);
    s.cx_timer_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::initializeOwnedCxTimer(ZornGen7RegisterMaps26 &maps,
    OSObject &owner,const ZornGen7CxTimerAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;
    auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gmu_ahb_ready || !s.cold_gmu_clocks_ready ||
       !s.smmu_domains_ready || !s.smmu_domains || s.cx_timer_attempted ||
       !authority.acquireFreshTimerWindow)return finish(kIOReturnNotReady);
    s.cx_timer_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(maps) || !retainDependency(owner))return finish(kIOReturnNoMemory);
    const auto raw=maps.initializeFreshCxTimer(owner,authority);
    if(raw!=kIOReturnSuccess)return finish(raw);
    if(s.smmu_domains->faulted() || (s.rsc_storage && !s.rsc_storage->forwardAllowed()))
        return finish(kIOReturnNotReady);
    s.cx_timer_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::initializeOwnedCxSecurity(IORegistryEntry &root,IOService &gpu,
    OSObject &owner,const ZornGen7ScmAuthority26 &authority,uint32_t budget)
{
    using namespace ZornGen7ColdBoot;
    if(!storage_)return kIOReturnNotReady;
    auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_cx_scm && s.native_cx_root==&root && s.native_cx_gpu==&gpu &&
        &owner==this && authority.cookie==this;
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gmu_tcm_loaded_ready || !s.cx_timer_ready || (!direct && !s.pdc_rsc_ready) ||
       !s.gen79_core_inputs_ready || !s.owned_gen79_core_inputs || s.cx_security_attempted ||
       !budget || !authority.acquireExclusiveCxEpoch)return finish(kIOReturnNotReady);
    s.cx_security_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(owner))return finish(kIOReturnNoMemory);
    const auto &actual=*s.owned_gen79_core_inputs;
    if(!actual.core_features || *actual.core_features!=ZornGen79CoreSource26::features)
        return finish(kIOReturnUnsupported);
    const unsigned long features=*actual.core_features;
    // Actual Gen7.9.1 core + gen7_scm_gpu_init_cx_regs source request.
    // Neither houji's fixed request nor an unknown/default convention supplies
    // K80 admission. No CLX register path is enabled for this actual core.
    constexpr unsigned long bclFeature=1UL<<12,clxFeature=1UL<<20;
    constexpr uint32_t alwaysRequest=1u<<0,bclRequest=1u<<1,clxRequest=1u<<2,tsenseRequest=1u<<3;
    const bool bcl=bool(features&bclFeature),clx=bool(features&clxFeature);
    const uint32_t request=alwaysRequest|(bcl?bclRequest:0)|(clx?clxRequest:0)|tsenseRequest;
    if(clx)return finish(kIOReturnUnsupported); // Source core omits CLX.
    const auto constructed=ZornGen7ScmOwner26::create(root,gpu,owner,authority,s.cx_scm_owner);
    if(constructed!=kIOReturnSuccess || !s.cx_scm_owner)return finish(constructed);
    s.cx_scm_result=s.cx_scm_owner->initializeCxRegisters(*s.gates.startup,request,budget);
    if(s.cx_scm_result.disposition!=Disposition::Complete)return finish(kIOReturnNotReady);
    if(s.smmu_domains->faulted() || (s.rsc_storage && !s.rsc_storage->forwardAllowed()))
        return finish(kIOReturnNotReady);
    if(bcl){s.cx_bcl_enabled_after_scm=true;s.cx_bcl_publication_valid=true;}
    s.cx_security_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
    // Complete preserves actual availability+init x0 return semantics. Missing
    // service/WAITQ/BUSY/unknown/budget stop;no Linux EOPNOTSUPP waiver, retry,
    // authentication, CM3 release or automatic secure-resource/session cleanup.
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedGmuIrqs(IOService &gmu,ZornGen7RegisterMaps26 &maps,
    IOWorkLoop &loop,OSObject &owner,const ZornGen7GmuIrqAuthority26 &)
{
    if(!storage_)return kIOReturnNotReady;
    auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) && s.native_gmu_config_window;
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.cx_security_ready || !s.cx_scm_owner || s.gmu_irq_attempted){IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;}
    s.gmu_irq_attempted=true;s.stage=Stage::StoppedRetained;
    // The private native route is reachable only after THIS owner's actual
    // CX operation completed. Retain that real session through IRQ lifetime;
    // metadata,an attached provider or a copied boolean cannot supply it.
    const auto raw=ZornGen7GmuIrq26::createDisabledWithNativeGic(gmu,maps,loop,owner,
        *s.cx_scm_owner,*s.gates.startup,s.gmu_irq);
    s.gmu_irq_ready=raw==kIOReturnSuccess && s.gmu_irq && !s.gmu_irq->halted() && !s.smmu_domains->faulted();
    if(s.gmu_irq_ready)s.stage=Stage::CpuReady;IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !s.gmu_irq_ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::configureOwnedGmuRegisters()
{
    using namespace ZornGen7RegisterConfig;
    if(!storage_)return kIOReturnNotReady;
    auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) && s.native_gmu_config_window;
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gmu_irq_ready || !s.gmu_irq || !s.cx_security_ready ||
       !s.cx_bcl_publication_valid || !s.cx_bcl_enabled_after_scm || !s.gmu_tcm_loaded_ready ||
       !s.gen79_core_inputs_ready || !s.owned_gen79_core_inputs || !s.arc_startup ||
       !s.smmu_domains_ready || !s.smmu_domains || s.gmu_config_attempted)return finish(kIOReturnNotReady);
    s.gmu_config_attempted=true;s.stage=Stage::StoppedRetained;
    if(!ZornGen79CoreSource26::admits(s.arc_startup->digest) ||
       !s.owned_gen79_core_inputs->core_features ||
       *s.owned_gen79_core_inputs->core_features!=ZornGen79CoreSource26::features)
        return finish(kIOReturnUnsupported);
    const auto raw=s.smmu_domains->configureGmuRegisters(*s.gmu_irq,ZornGen79CoreSource26::gpurev,KnownState::Yes);
    if(raw!=kIOReturnSuccess || s.smmu_domains->faulted() || s.gmu_irq->halted() ||
       (s.rsc_storage && !s.rsc_storage->forwardAllowed()))return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.gmu_config_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedDirectHfi(IOWorkLoop &loop)
{
    if(!storage_)return kIOReturnNotReady;
    auto &s=*storage_;
    // The deferred startup owns the board and SMMU gates and the read scope
    // for the active GMU stream. Use the same masked IRQ workloop.
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_gmu_config_window && s.native_gmu_irq_loop==&loop;
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gmu_config_ready || !s.gmu_irq_ready || !s.gmu_irq ||
       !s.smmu_domains_ready || !s.smmu_domains || s.direct_hfi_attempted)return finish(kIOReturnNotReady);
    s.direct_hfi_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->prepareDirectHfi(*s.gmu_irq,loop,s.direct_hfi);
    if(raw!=kIOReturnSuccess || !s.direct_hfi || s.direct_hfi->halted() ||
       s.smmu_domains->faulted() || s.gmu_irq->halted())return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.direct_hfi_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedGpuIccInputs(IOService &platform,
    IORegistryEntry &root,IOService &gpu,OSObject &treeOwner)
{
    if(!storage_)return kIOReturnNotReady;
    auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_gmu_config_window && s.direct_hfi_ready && s.native_cx_root==&root &&
        s.native_cx_gpu==&gpu && &treeOwner==this;
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || s.platform!=&platform || !s.ddr_metadata_ready ||
       !s.smmu_domains || s.smmu_domains->faulted() ||
       s.gpu_icc_inputs_attempted || !s.rsc_storage || !s.rsc_storage->forwardAllowed() || !s.command_db_storage ||
       !s.rsc_cache || !s.rsc_reservation || !s.owned_native_graph.cpu_graph_complete || !s.owned_native_clock_graph ||
       !s.owned_native_clock_graph->graph.gcc.node)return finish(kIOReturnNotReady);
    s.gpu_icc_inputs_attempted=true;s.stage=Stage::StoppedRetained;
    const uint32_t type=uint32_t(__atomic_load_n(&s.owned_ddr_type,__ATOMIC_RELAXED));
    const auto raw=ZornGen7IccInputs26::create(platform,root,gpu,treeOwner,type,s.gpu_icc_inputs);
    if(raw!=kIOReturnSuccess || !s.gpu_icc_inputs || !s.gpu_icc_inputs->sourceReady() ||
       s.smmu_domains->faulted() || (s.gmu_irq && s.gmu_irq->halted()) || (s.host_hfi && s.host_hfi->halted()))
        return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    const auto clockRaw=s.gpu_icc_inputs->bindClock(*s.clocks,*s.owned_native_clock_graph->graph.gcc.node,s.gates.startup);
    if(clockRaw!=kIOReturnSuccess || !s.gpu_icc_inputs->clockReady())return finish(clockRaw==kIOReturnSuccess?kIOReturnNotReady:clockRaw);
    const auto voterRaw=s.command_db_reader ?
        s.command_db_reader->prepareIccVoter(*s.gpu_icc_inputs,*s.rsc_storage,*s.rsc_cache,*s.rsc_reservation) :
        s.gpu_icc_inputs->bindVoter(*s.rsc_storage,*s.rsc_cache,*s.rsc_reservation,s.owned_command_db,*s.command_db_storage);
    if(voterRaw!=kIOReturnSuccess || !s.gpu_icc_inputs->voterReady())return finish(voterRaw==kIOReturnSuccess?kIOReturnNotReady:voterRaw);
    s.gpu_icc_inputs_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
    // Real registry/resource and actual clock consumer construction only; no ICC provider registration,
    // init-floor clearing, clock/QoS return or bootstrap bandwidth success.
}

IOReturn ZornGen7DarwinBoardOwner::initializeOwnedGpuIccVotes()
{
    if(!storage_)return kIOReturnNotReady;
    auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_gmu_config_window && s.direct_hfi_ready;
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gpu_icc_inputs_ready || !s.gpu_icc_inputs ||
       s.gpu_icc_initial_attempted || !s.rsc_storage || !s.rsc_storage->forwardAllowed() ||
       !s.smmu_domains || s.smmu_domains->faulted() || (s.gmu_irq && s.gmu_irq->halted()) ||
       (s.host_hfi && s.host_hfi->halted()))return finish(kIOReturnNotReady);
    s.gpu_icc_initial_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.gpu_icc_inputs->initializeInitialVotes();
    if(raw!=kIOReturnSuccess || !s.rsc_storage->forwardAllowed() || s.smmu_domains->faulted() ||
       (s.gmu_irq && s.gmu_irq->halted()) || (s.host_hfi && s.host_hfi->halted()))return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.gpu_icc_initial_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
    // Exact known-returned initial source calls only;no QoS/BW or physical
    // fabric ownership inferred, no CM3 release or HFI startup operation.
}

IOReturn ZornGen7DarwinBoardOwner::configureOwnedGpuIccQos(OSObject &owner,const ZornGen7OperationGuard26 &guard,
    const ZornGen7IccQosAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gpu_icc_initial_ready || !s.gpu_icc_inputs || s.gpu_icc_qos_attempted ||
       !s.rsc_storage || !s.rsc_storage->forwardAllowed() || !s.smmu_domains || s.smmu_domains->faulted() ||
       (s.gmu_irq && s.gmu_irq->halted()) || (s.host_hfi && s.host_hfi->halted()))return finish(kIOReturnNotReady);
    s.gpu_icc_qos_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.gpu_icc_inputs->configureQos(owner,guard,authority);
    if(raw!=kIOReturnSuccess || !s.rsc_storage->forwardAllowed() || s.smmu_domains->faulted() ||
       (s.gmu_irq && s.gmu_irq->halted()) || (s.host_hfi && s.host_hfi->halted()))return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.gpu_icc_qos_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::configureNativeOwnedGpuIccQos(OSObject &owner,const ZornGen7IccQosAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gpu_icc_initial_ready || !s.gpu_icc_inputs || s.gpu_icc_qos_attempted ||
       !s.rsc_storage || !s.rsc_storage->forwardAllowed() || !s.smmu_domains || s.smmu_domains->faulted() ||
       (s.gmu_irq && s.gmu_irq->halted()) || (s.host_hfi && s.host_hfi->halted()))return finish(kIOReturnNotReady);
    s.gpu_icc_qos_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(owner))return finish(kIOReturnNoMemory);
    const auto raw=s.gpu_icc_inputs->configureNativeQos(owner,authority);
    if(raw!=kIOReturnSuccess || !s.rsc_storage->forwardAllowed() || s.smmu_domains->faulted() ||
       (s.gmu_irq && s.gmu_irq->halted()) || (s.host_hfi && s.host_hfi->halted()))return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.gpu_icc_qos_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::applyOwnedGpuBootstrapBandwidth()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gpu_icc_qos_ready || !s.host_irq_armed || !s.gpu_icc_inputs || s.gpu_bootstrap_bw_attempted ||
       !s.rsc_storage || !s.rsc_storage->forwardAllowed() || !s.smmu_domains || s.smmu_domains->faulted() ||
       !s.gmu_irq || s.gmu_irq->halted() || !s.host_hfi || s.host_hfi->halted())return finish(kIOReturnNotReady);
    s.gpu_bootstrap_bw_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.gpu_icc_inputs->applyBootstrapBandwidth();
    if(raw!=kIOReturnSuccess || !s.rsc_storage->forwardAllowed() || s.smmu_domains->faulted() ||
       s.gmu_irq->halted() || s.host_hfi->halted())return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.gpu_bootstrap_bw_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedHwschedHfi(IOWorkLoop &loop)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gmu_config_ready || !s.gmu_versions_ready || !s.gmu_irq_ready || !s.gmu_irq ||
       !s.smmu_domains_ready || !s.smmu_domains || s.hwsched_hfi_attempted)return finish(kIOReturnNotReady);
    s.hwsched_hfi_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->prepareHwschedHfi(*s.gmu_irq,loop,s.hwsched_hfi);
    if(raw!=kIOReturnSuccess || !s.hwsched_hfi || s.hwsched_hfi->halted() ||
       s.smmu_domains->faulted() || s.gmu_irq->halted())return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.hwsched_hfi_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::loadOwnedPdcRsc(ZornGen7RegisterMaps26 &maps)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || s.pdc_rsc_attempted || !s.owned_gmu_software || !s.cold_gmu_clocks_ready ||
       !s.gmu_tcm_loaded_ready || !s.cx_timer_ready || !s.smmu_domains || s.smmu_domains->faulted() ||
       s.cx_security_attempted || !s.gen79_core_inputs_ready)return finish(kIOReturnNotReady);
    s.pdc_rsc_attempted=true;s.stage=Stage::StoppedRetained;
    if(!retainDependency(maps))return finish(kIOReturnNoMemory);
    const auto raw=maps.loadPdcRsc(*this,&s.owned_gmu_software->flags);
    if(raw!=kIOReturnSuccess || s.smmu_domains->faulted() || (s.rsc_storage && !s.rsc_storage->forwardAllowed()))
        return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.pdc_rsc_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::readOwnedHwschedGmuVersions()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || s.gmu_versions_attempted || !s.owned_gmu_software || !s.gmu_config_ready ||
       !s.cx_security_ready || !s.pdc_rsc_ready || !s.gmu_irq_ready || !s.gmu_irq ||
       !s.smmu_domains_ready || !s.smmu_domains)return finish(kIOReturnNotReady);
    s.gmu_versions_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->readHwschedGmuVersions(*s.gmu_irq,s.owned_gmu_software->versions);
    if(raw!=kIOReturnSuccess || s.smmu_domains->faulted() || s.gmu_irq->halted())
        return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    // Actual source GMU_VER_MINOR=bits16..27. This updates the same board's
    // source HWSCHED flags only after its real HFI version read returned.
    if(((s.owned_gmu_software->versions[4]>>16)&0xfffu)<2u)
        (void)__atomic_fetch_or(&s.owned_gmu_software->hwsched_flags,uint64_t(1)<<2,__ATOMIC_RELAXED);
    s.gmu_versions_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::armOwnedHwschedIrqs()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || s.hwsched_irq_arm_attempted || !s.gmu_versions_ready || !s.gmu_config_ready ||
       !s.hwsched_hfi_ready || !s.hwsched_hfi || s.hwsched_hfi->halted() || !s.gpu_icc_qos_ready ||
       !s.smmu_domains || s.smmu_domains->faulted() || !s.gmu_irq || s.gmu_irq->halted()){
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.hwsched_irq_arm_attempted=true;s.stage=Stage::StoppedRetained;
    // All referenced owners already have retained lifetimes. Release the
    // shared startup/domain gate while enabling native event delivery;worker
    // servicing must be able to take that gate without a lock inversion.
    IORecursiveLockUnlock(s.gates.startup);
    const auto raw=s.hwsched_hfi->armBoundReceiver();
    IORecursiveLockLock(s.gates.startup);
    const bool ready=raw==kIOReturnSuccess && s.gmu_irq->forwardAllowed() && !s.gmu_irq->halted() &&
        !s.hwsched_hfi->halted() && !s.smmu_domains->faulted();
    if(ready){s.hwsched_irq_armed=true;s.stage=Stage::CpuReady;}
    IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
    // Only genuine native arm returned. No CM3/HFI/GPU success or ACK is published.
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedHostHfi(IOWorkLoop &loop)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.gmu_config_ready || !s.gmu_versions_ready || !s.gmu_irq_ready || !s.gmu_irq ||
       !s.smmu_domains_ready || !s.smmu_domains || s.host_hfi_attempted)return finish(kIOReturnNotReady);
    s.host_hfi_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->prepareHostHfi(*s.gmu_irq,loop,s.host_hfi);
    if(raw!=kIOReturnSuccess || !s.host_hfi || s.host_hfi->halted() ||
       s.smmu_domains->faulted() || s.gmu_irq->halted())return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.host_hfi_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::armOwnedHostIrqs()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || s.host_irq_arm_attempted || !s.gmu_versions_ready || !s.gmu_config_ready ||
       !s.host_hfi_ready || !s.host_hfi || s.host_hfi->halted() || !s.gpu_icc_qos_ready ||
       !s.smmu_domains || s.smmu_domains->faulted() || !s.gmu_irq || s.gmu_irq->halted()){
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    s.host_irq_arm_attempted=true;s.stage=Stage::StoppedRetained;
    // All referenced owners already have retained lifetimes. Release the
    // shared startup/domain gate while enabling native event delivery;worker
    // servicing must be able to take that gate without a lock inversion.
    IORecursiveLockUnlock(s.gates.startup);
    const auto raw=s.host_hfi->armBoundReceiver();
    IORecursiveLockLock(s.gates.startup);
    const bool ready=raw==kIOReturnSuccess && s.gmu_irq->forwardAllowed() && !s.gmu_irq->halted() &&
        !s.host_hfi->halted() && !s.smmu_domains->faulted();
    if(ready){s.host_irq_armed=true;s.stage=Stage::CpuReady;}
    IORecursiveLockUnlock(s.gates.startup);
    return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
    // Only genuine native arm returned. No CM3/HFI/GPU success or ACK is published.
}

IOReturn ZornGen7DarwinBoardOwner::readOwnedHostGmuVersions()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || s.gmu_versions_attempted || !s.owned_gmu_software || !s.gmu_config_ready ||
       !s.cx_security_ready || !s.pdc_rsc_ready || !s.gmu_irq_ready || !s.gmu_irq ||
       !s.smmu_domains_ready || !s.smmu_domains)return finish(kIOReturnNotReady);
    s.gmu_versions_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->readHostGmuVersions(*s.gmu_irq,s.owned_gmu_software->versions);
    if(raw!=kIOReturnSuccess || s.smmu_domains->faulted() || s.gmu_irq->halted())
        return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    // Host profile retains actual returned versions. No HWSCHED context,
    // feature or scheduling state is enabled by this path.
    s.gmu_versions_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedHostTables(const ZornGen7HostTableSelection26 &selection)
{
    if(!storage_)return kIOReturnNotReady;
    auto &s=*storage_;
    // The same deferred board owner holds the gate after the real HFI ACK.
    // This path builds CPU payloads from the retained CommandDB source.
    const bool direct=&selection.actualSelectionOwner==this && normal() &&
        IORecursiveLockHaveLock(s.gates.startup) && !IORecursiveLockHaveLock(s.gates.clock_prepare) &&
        s.direct_hfi_ready && s.direct_hfi && s.direct_hfi->healthy() &&
        s.gmu_irq && s.gmu_irq->forwardAllowed() && s.pdc_rsc_ready &&
        s.gpu_bootstrap_bw_ready && s.rsc_storage && s.rsc_storage->forwardAllowed();
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || s.host_tables_attempted || !s.command_db_storage || !s.arc_startup ||
       !s.gen79_core_inputs_ready)return finish(kIOReturnNotReady);
    s.host_tables_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.command_db_reader ? s.command_db_reader->prepareHostTables(*s.gates.startup,*this,selection,s.host_tables) :
        ZornGen7HostTables26::createAndPrepare(*s.gates.startup,*this,s.owned_command_db,
        *s.command_db_storage,selection,s.host_tables);
    if(raw!=kIOReturnSuccess || !s.host_tables)return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.host_tables_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}
IOReturn ZornGen7DarwinBoardOwner::runOwnedHostProfile()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_tables_ready || !s.host_tables || !s.host_hfi_ready || !s.host_hfi ||
       !s.host_irq_armed || !s.gpu_bootstrap_bw_ready || !s.host_first_query_ready || s.host_profile_attempted)return finish(kIOReturnNotReady);
    s.host_profile_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.host_tables->runHostProfile(*s.host_hfi);
    if(raw!=kIOReturnSuccess || s.host_hfi->halted() || s.gmu_irq->halted() || s.smmu_domains->faulted())return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    if(!s.gpu_icc_inputs || !s.rsc_storage || !s.rsc_storage->forwardAllowed())return finish(kIOReturnNotReady);
    const auto unvote=s.gpu_icc_inputs->finishHostBootstrap();
    if(unvote!=kIOReturnSuccess || !s.rsc_storage->forwardAllowed() || s.smmu_domains->faulted() ||
       s.gmu_irq->halted() || s.host_hfi->halted())return finish(unvote==kIOReturnSuccess?kIOReturnNotReady:unvote);
    s.host_bootstrap_unvoted=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::startOwnedHostGmu(OSObject &owner,const ZornGen7GmuStartAuthority26 &authority)
{
    if(!callable() || !authority.acquireColdStartWindow || !authority.acquireHfiQueueReset)return kIOReturnNotReady;
    auto &s=*storage_;if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || s.host_gmu_start_attempted || !s.host_hfi_ready || !s.host_hfi ||
       !s.host_irq_armed || !s.gpu_bootstrap_bw_ready || !s.gmu_config_ready || !s.gmu_versions_ready ||
       !s.gmu_tcm_loaded_ready || !s.pdc_rsc_ready || !s.cx_security_ready || !s.cx_timer_ready ||
       !s.cold_gmu_clocks_ready || !s.gmu_irq || !s.smmu_domains){IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;}
    s.host_gmu_start_attempted=true;s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);
    // No startup/domain gate is held across AO sampling,HFI polling or the
    // genuine inline response/debug loop. Their resources have retained pins.
    const auto raw=s.host_hfi->startHostGmu(owner,authority);
    IORecursiveLockLock(s.gates.startup);
    const bool ready=raw==kIOReturnSuccess && !s.host_hfi->halted() && !s.gmu_irq->halted() && !s.smmu_domains->faulted();
    if(ready){s.host_first_query_ready=true;s.stage=Stage::CpuReady;}
    IORecursiveLockUnlock(s.gates.startup);return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::requestOwnedHostDefaultClock(IOService &gpu)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_tables_ready || !s.host_tables || !s.host_hfi_ready || !s.host_hfi ||
       !s.host_first_query_ready || !s.host_profile_attempted || !s.host_bootstrap_unvoted || s.host_default_clock_attempted)return finish(kIOReturnNotReady);
    s.host_default_clock_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.host_tables->requestDefaultClock(*s.host_hfi,gpu);
    if(raw!=kIOReturnSuccess || s.host_hfi->halted() || s.gmu_irq->halted() || s.smmu_domains->faulted())return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::requestOwnedHostDefaultBandwidth()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_tables_ready || !s.host_tables || !s.host_hfi || !s.host_bootstrap_unvoted ||
       !s.host_default_clock_attempted || !s.gpu_icc_inputs || s.host_default_bw_attempted)return finish(kIOReturnNotReady);
    s.host_default_bw_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.host_tables->requestDefaultBandwidth(*s.host_hfi,*s.gpu_icc_inputs);
    if(raw!=kIOReturnSuccess || !s.rsc_storage->forwardAllowed() || s.host_hfi->halted() ||
       s.gmu_irq->halted() || s.smmu_domains->faulted())return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

int ZornGen7DarwinBoardOwner::acquireOwnedGpuStartWindow(void *cookie,IOService &gpu,
    IOMemoryDescriptor &gpuResource,IOService &gmu,IOMemoryDescriptor &gmuResource)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    auto &s=*owner->storage_;
    if(!s.gates.startup || IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto *const boundParent=s.host_gpu_mmu_parent;
    auto *const boundMaps=s.host_gpu_mmu_maps;
    IORecursiveLockUnlock(s.gates.startup);
    // The board-owned references keep these immutable identities alive. Check
    // the map without the board gate to preserve the map/board lock order.
    if(!boundParent || !boundMaps ||
       !boundMaps->hostGpuStartPairIs(*boundParent,gpu,gpuResource,gmu,gmuResource))
        return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    if(s.host_gpu_mmu_parent!=boundParent || s.host_gpu_mmu_maps!=boundMaps){
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;
    }
    auto finish=[&](int raw){s.host_gpu_start_window_raw=raw;IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.host_gpu_start_window_attempted)return finish(kIOReturnExclusiveAccess);
    s.host_gpu_start_window_attempted=true;
    const bool exactPair=&gpu!=&gmu && &gpuResource!=&gmuResource && !gpu.isInactive() && !gmu.isInactive() &&
        gpuResource.getLength()!=0 && gmuResource.getLength()!=0 && gpu.getProvider()!=nullptr &&
        gpu.getProvider()==gmu.getProvider();
    const bool ownedEpoch=s.stage==Stage::StoppedRetained && s.host_gpu_oob_attempted &&
        !s.host_gpu_oob_ready && s.host_default_bw_attempted && s.host_gpu_mmu_ready &&
        s.gmu_tcm_loaded_ready && s.cx_security_ready && s.cx_scm_owner && s.cold_gmu_clocks_ready &&
        s.gmu_irq_ready && s.gmu_irq && !s.gmu_irq->halted() && s.host_hfi && s.host_hfi->healthy() &&
        s.smmu_domains && !s.smmu_domains->faulted() && s.smmu_power && s.smmu_power->operation &&
        s.smmu_power->native_reference && s.smmu_power->native_claimant && s.smmu_power->native_provider_opened &&
        s.smmu_power->native_power_result.disposition==ZornGen7ColdBoot::Disposition::Complete &&
        s.rsc_storage && s.rsc_storage->forwardAllowed();
    if(!exactPair || !ownedEpoch)return finish(kIOReturnNotReady);

    // The registry-map caller already holds and checks the exact base-provider
    // opens. Pin those service/resource identities in this real board owner as
    // well;the pin covers OOB,CP setup and the later GPU runtime epoch.
    gpu.retain();gmu.retain();gpuResource.retain();gmuResource.retain();
    s.host_gpu_start_gpu=&gpu;s.host_gpu_start_gmu=&gmu;
    s.host_gpu_start_gpu_resource=&gpuResource;s.host_gpu_start_gmu_resource=&gmuResource;
    s.host_gpu_start_window_held=true;
    return finish(kIOReturnSuccess);
}

int ZornGen7DarwinBoardOwner::acquireOwnedGpuMmuStartWindow(void *cookie,
    IOService &controller,IOService &user,IOService &lpac,const uint16_t (&banks)[2],
    const uint16_t (&asids)[2],const uint32_t (&prrBefore)[2],IOMemoryDescriptor &zero,
    uint64_t zeroPhysical)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    auto &s=*owner->storage_;
    if(!s.gates.startup || IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto *const parent=s.host_gpu_mmu_parent;
    auto *const maps=s.host_gpu_mmu_maps;
    auto *const domains=s.smmu_domains;
    const bool ready=s.stage==Stage::StoppedRetained && s.host_gpu_mmu_attempted &&
        !s.host_gpu_mmu_ready && !s.host_gpu_mmu_lease_attempted &&
        s.host_gpu_tables_attempted && !s.host_gpu_oob_attempted && !s.host_gpu_start_window_held &&
        s.gpu_icc_inputs_ready && s.gpu_icc_qos_ready && s.host_hfi && s.host_hfi->healthy() &&
        s.gmu_irq && !s.gmu_irq->halted() && s.smmu_power && s.rsc_storage &&
        s.smmu_domains && !s.smmu_domains->faulted() && parent && maps &&
        s.smmu_power->guarded_global_io.cookie==maps &&
        s.smmu_power->native_reference && s.smmu_power->native_claimant &&
        s.smmu_power->native_provider_opened &&
        s.smmu_power->native_power_result.disposition==ZornGen7ColdBoot::Disposition::Complete &&
        s.rsc_storage->forwardAllowed();
    if(s.host_gpu_mmu_lease_attempted){IORecursiveLockUnlock(s.gates.startup);return kIOReturnExclusiveAccess;}
    s.host_gpu_mmu_lease_attempted=true;
    IORecursiveLockUnlock(s.gates.startup);

    int raw=kIOReturnNotReady;
    if(ready && parent->gpuProviderClaimsHeld() && maps->boundAndReadyForGpuStart(*parent))
        raw=domains->verifyHostGpuMmuStartAuthorization(controller,user,lpac,banks,asids,
            prrBefore,zero,zeroPhysical);

    IORecursiveLockLock(s.gates.startup);
    const bool unchanged=s.stage==Stage::StoppedRetained && s.host_gpu_mmu_attempted &&
        s.host_gpu_mmu_parent==parent && s.host_gpu_mmu_maps==maps && s.smmu_domains==domains &&
        s.host_hfi && s.host_hfi->healthy() && s.gmu_irq && !s.gmu_irq->halted() &&
        !s.smmu_domains->faulted() && s.rsc_storage && s.rsc_storage->forwardAllowed();
    s.host_gpu_mmu_lease_raw=raw;
    if(raw==kIOReturnSuccess && unchanged)s.host_gpu_mmu_lease_held=true;
    else if(raw==kIOReturnSuccess)raw=s.host_gpu_mmu_lease_raw=kIOReturnNotReady;
    IORecursiveLockUnlock(s.gates.startup);
    return raw;
}

int ZornGen7DarwinBoardOwner::authorizeOwnedPostCpUserRestore(void *cookie,
    IOService &controller,IOService &user,uint16_t bank,uint16_t asid,
    uint32_t expectedTcr,uint32_t actualTcr)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    auto &s=*owner->storage_;
    if(!s.gates.startup || IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    const bool direct=s.direct_hfi && s.native_direct_memory_owner && s.native_cx_maps &&
        __atomic_load_n(&s.direct_oob_epoch,__ATOMIC_ACQUIRE)==1 && s.host_zap_authenticated && s.host_bootstrap_attempted;
    auto *const parent=direct?s.native_direct_memory_owner:s.host_gpu_mmu_parent;
    auto *const maps=direct?s.native_cx_maps:s.host_gpu_mmu_maps;
    auto *const domains=s.smmu_domains;
    const bool ready=s.stage==Stage::StoppedRetained && (direct || (s.host_gpu_mmu_attempted && s.host_gpu_mmu_lease_held)) &&
        s.host_gpu_mmu_ready && !s.host_gpu_post_cp_restore_attempted &&
        s.host_gpu_oob_ready && s.host_cp_attempted && (direct?s.direct_hfi->healthy():(s.host_hfi && s.host_hfi->healthy())) &&
        s.host_gpu_irq && !s.host_gpu_irq->halted() && s.gmu_irq && !s.gmu_irq->halted() &&
        s.smmu_domains && !s.smmu_domains->faulted() && parent && maps &&
        s.smmu_power && s.smmu_power->guarded_global_io.cookie==maps &&
        s.rsc_storage && s.rsc_storage->forwardAllowed();
    if(s.host_gpu_post_cp_restore_attempted){IORecursiveLockUnlock(s.gates.startup);return kIOReturnExclusiveAccess;}
    s.host_gpu_post_cp_restore_attempted=true;
    IORecursiveLockUnlock(s.gates.startup);

    int raw=kIOReturnNotReady;
    if(ready && parent->gpuProviderClaimsHeld() && maps->boundAndReadyForGpuStart(*parent))
        raw=domains->verifyHostGpuPostCpRestoreAuthorization(controller,user,bank,asid,
            expectedTcr,actualTcr);

    IORecursiveLockLock(s.gates.startup);
    const bool unchanged=s.stage==Stage::StoppedRetained && (direct ? (__atomic_load_n(&s.direct_oob_epoch,__ATOMIC_ACQUIRE)==1 &&
            s.native_direct_memory_owner==parent && s.native_cx_maps==maps) :
            (s.host_gpu_mmu_lease_held && s.host_gpu_mmu_parent==parent && s.host_gpu_mmu_maps==maps)) && s.smmu_domains==domains &&
        (direct?s.direct_hfi->healthy():(s.host_hfi && s.host_hfi->healthy())) && s.host_gpu_irq && !s.host_gpu_irq->halted() &&
        s.gmu_irq && !s.gmu_irq->halted() && !s.smmu_domains->faulted() &&
        s.rsc_storage && s.rsc_storage->forwardAllowed();
    s.host_gpu_post_cp_restore_raw=raw;
    if(raw==kIOReturnSuccess && unchanged)s.host_gpu_post_cp_restore_held=true;
    else if(raw==kIOReturnSuccess)raw=s.host_gpu_post_cp_restore_raw=kIOReturnNotReady;
    IORecursiveLockUnlock(s.gates.startup);
    return raw;
}

int ZornGen7DarwinBoardOwner::acquireOwnedNativeRuntimeWindow(void *cookie,
    IOService &controller,IOService &user,IOService &lpac,ZornGen7HostRing26 &bootstrap)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    auto &s=*owner->storage_;
    if(!s.gates.startup || IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    const bool direct=s.direct_hfi && s.native_direct_memory_owner && s.native_cx_maps &&
        __atomic_load_n(&s.direct_oob_epoch,__ATOMIC_ACQUIRE)==2 && s.direct_hfi->bootstrapOobReleaseReturned();
    auto *const parent=direct?s.native_direct_memory_owner:s.host_gpu_mmu_parent;
    auto *const maps=direct?s.native_cx_maps:s.host_gpu_mmu_maps;
    auto *const domains=s.smmu_domains;
    auto *const gpu=s.host_gpu_start_gpu;
    auto *const gmu=s.host_gpu_start_gmu;
    auto *const gpuResource=s.host_gpu_start_gpu_resource;
    auto *const gmuResource=s.host_gpu_start_gmu_resource;
    const bool ready=s.stage==Stage::StoppedRetained && s.host_direct_runtime_attempted &&
        !s.host_direct_runtime_ready && !s.host_direct_runtime_window_attempted &&
        s.host_bootstrap_ready && s.host_ring==&bootstrap && s.host_gpu_start_window_held &&
        s.host_gpu_mmu_ready && (direct || s.host_gpu_mmu_lease_held) && s.host_gpu_oob_ready &&
        s.host_gpu_irq_ready && s.host_gpu_irq && !s.host_gpu_irq->halted() &&
        (direct?s.direct_hfi->healthy():(s.host_hfi && s.host_hfi->healthy())) && s.gmu_irq && !s.gmu_irq->halted() &&
        domains && !domains->faulted() && s.smmu_power &&
        s.smmu_power->guarded_global_io.cookie==maps && s.rsc_storage &&
        s.rsc_storage->forwardAllowed() && parent && maps && gpu && gmu &&
        gpuResource && gmuResource && domains->runtimeEndpointBindingsMatch(controller,user,lpac);
    if(s.host_direct_runtime_window_attempted){IORecursiveLockUnlock(s.gates.startup);return kIOReturnExclusiveAccess;}
    s.host_direct_runtime_window_attempted=true;
    IORecursiveLockUnlock(s.gates.startup);

    int raw=kIOReturnNotReady;
    if(ready && parent->gpuProviderClaimsHeld() && maps->boundAndReadyForGpuStart(*parent) &&
       maps->hostGpuStartPairIs(*parent,*gpu,*gpuResource,*gmu,*gmuResource) &&
       bootstrap.completedBootstrapForDomain(*domains))raw=kIOReturnSuccess;

    IORecursiveLockLock(s.gates.startup);
    const bool unchanged=s.stage==Stage::StoppedRetained && s.host_direct_runtime_attempted &&
        (direct?(s.native_direct_memory_owner==parent && s.native_cx_maps==maps && __atomic_load_n(&s.direct_oob_epoch,__ATOMIC_ACQUIRE)==2):(s.host_gpu_mmu_parent==parent && s.host_gpu_mmu_maps==maps)) && s.smmu_domains==domains &&
        s.host_gpu_start_gpu==gpu && s.host_gpu_start_gmu==gmu &&
        s.host_gpu_start_gpu_resource==gpuResource && s.host_gpu_start_gmu_resource==gmuResource &&
        s.host_ring==&bootstrap && (direct?s.direct_hfi->healthy():(s.host_hfi && s.host_hfi->healthy())) &&
        s.host_gpu_irq && !s.host_gpu_irq->halted() && s.gmu_irq && !s.gmu_irq->halted() &&
        !s.smmu_domains->faulted() && s.rsc_storage && s.rsc_storage->forwardAllowed();
    s.host_direct_runtime_window_raw=raw;
    if(raw==kIOReturnSuccess && unchanged)s.host_direct_runtime_window_held=true;
    else if(raw==kIOReturnSuccess)raw=s.host_direct_runtime_window_raw=kIOReturnNotReady;
    IORecursiveLockUnlock(s.gates.startup);
    return raw;
}

int ZornGen7DarwinBoardOwner::forwardDirectRuntimeKernelTaskGrant(void *cookie,
    IOService &gpu,IOMemoryDescriptor &gpuRegisters,IOService &gmu,IOMemoryDescriptor &gmuRegisters,
    IOMemoryDescriptor &image)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    const auto &authority=owner->storage_->forwarded_direct_runtime_authority;
    return authority.acquireKernelTask ? authority.acquireKernelTask(authority.cookie,gpu,gpuRegisters,gmu,gmuRegisters,image) : kIOReturnNotReady;
}
int ZornGen7DarwinBoardOwner::forwardDirectRuntimeKernelTaskCheck(void *cookie,IOMemoryDescriptor &image,unsigned phase)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    const auto &authority=owner->storage_->forwarded_direct_runtime_authority;
    return authority.checkHeldKernelTask ? authority.checkHeldKernelTask(authority.cookie,image,phase) : kIOReturnNotReady;
}
int ZornGen7DarwinBoardOwner::forwardDirectRuntimeKernelTaskRelease(void *cookie,
    IOService &gpu,IOMemoryDescriptor &image)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    const auto &authority=owner->storage_->forwarded_direct_runtime_authority;
    return authority.authorizeKernelTaskRelease ? authority.authorizeKernelTaskRelease(authority.cookie,gpu,image) : kIOReturnNotReady;
}
int ZornGen7DarwinBoardOwner::forwardDirectRuntimeKernelClientGrant(void *cookie,IOUserClient &client,
    IOService &gpu,IOMemoryDescriptor &gpuRegisters,IOService &gmu,IOMemoryDescriptor &gmuRegisters)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    const auto &authority=owner->storage_->forwarded_direct_runtime_authority;
    return authority.acquireKernelClient ? authority.acquireKernelClient(authority.cookie,client,gpu,gpuRegisters,gmu,gmuRegisters) : kIOReturnNotReady;
}
int ZornGen7DarwinBoardOwner::forwardDirectRuntimeKernelClientCheck(void *cookie,IOUserClient &client,unsigned phase)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    const auto &authority=owner->storage_->forwarded_direct_runtime_authority;
    return authority.checkHeldKernelClient ? authority.checkHeldKernelClient(authority.cookie,client,phase) : kIOReturnNotReady;
}
int ZornGen7DarwinBoardOwner::forwardDirectRuntimeKernelClientRelease(void *cookie,IOUserClient &client)
{
    auto *owner=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
    if(!owner || !owner->storage_ || !normal())return kIOReturnNotReady;
    const auto &authority=owner->storage_->forwarded_direct_runtime_authority;
    return authority.authorizeKernelClientRelease ? authority.authorizeKernelClientRelease(authority.cookie,client) : kIOReturnNotReady;
}

extern "C" void zorn26_native_gpu_start_observation(uint32_t (&out)[5])
{
    memcpy(out,nativeGpuStartObservation,sizeof(out));
}

void Zorn26CopyGpuOob(uint32_t (&out)[5])
{
    memcpy(out,nativeGpuOobObservation,sizeof(out));
}

IOReturn ZornGen7DarwinBoardOwner::acquireOwnedHostGpuOob(ZornGen7InactiveOwner26 &parent,
    ZornGen7RegisterMaps26 &maps,OSObject &owner,const ZornGen7GpuStartAuthority26 &authority)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.host_hfi || !s.host_default_bw_attempted || !s.host_gpu_mmu_ready ||
       s.host_gpu_mmu_parent!=&parent || s.host_gpu_mmu_maps!=&maps || !s.smmu_power ||
       s.smmu_power->guarded_global_io.cookie!=&maps || s.host_gpu_oob_attempted){IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;}
    s.host_gpu_oob_attempted=true;s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);
    // The externally supplied callback is deliberately not trusted as a cold
    // start lease. Construct the authority here from this real board owner's
    // already-retained power/security/IRQ/SMMU/HFI epoch.
    (void)owner;(void)authority;
    ZornGen7GpuStartAuthority26 ownedAuthority{};ownedAuthority.cookie=this;
    ownedAuthority.acquireExclusiveGpuStart=acquireOwnedGpuStartWindow;
    const auto raw=s.host_hfi->acquireHostGpuOob(*this,ownedAuthority);IORecursiveLockLock(s.gates.startup);
    const bool ready=raw==kIOReturnSuccess && s.host_gpu_start_window_held && !s.host_hfi->halted() &&
        !s.gmu_irq->halted() && !s.smmu_domains->faulted() && s.rsc_storage->forwardAllowed();
    if(ready){s.host_gpu_oob_ready=true;s.stage=Stage::CpuReady;}IORecursiveLockUnlock(s.gates.startup);return raw==kIOReturnSuccess && !ready?kIOReturnNotReady:raw;
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedHostGpuTables(FhgStorage &graph,HoujiFullHostNativeMemory &memory,OSObject &parent)
{
    if(!storage_)return kIOReturnNotReady;
    auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_direct_memory_owner==&parent && s.host_bootstrap_unvoted &&
        s.direct_hfi_ready && s.direct_hfi && s.direct_hfi->healthy() &&
        s.gmu_irq && s.gmu_irq->forwardAllowed();
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    const bool host=s.host_default_bw_attempted && s.host_hfi && !s.host_hfi->halted();
    if(s.stage!=Stage::CpuReady || !s.smmu_domains || (!direct && !host) ||
       s.host_gpu_tables_attempted || s.host_gpu_oob_attempted)return finish(kIOReturnNotReady);
    s.host_gpu_tables_attempted=true;s.stage=Stage::StoppedRetained;
    const auto raw=s.smmu_domains->prepareHostGpuTables(graph,memory,parent);
    const bool transportReady=direct?s.direct_hfi->healthy():!s.host_hfi->halted();
    if(raw!=kIOReturnSuccess || s.smmu_domains->faulted() || s.gmu_irq->halted() || !transportReady)return finish(raw==kIOReturnSuccess?kIOReturnNotReady:raw);
    s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::startOwnedHostGpuMmu(NativeAdrenoMemory &zero,
    ZornGen7InactiveOwner26 &parent,ZornGen7RegisterMaps26 &maps,OSObject &mmuOwner,
    OSObject &irqStreamOwner,const ZornGen7GpuMmuAuthority26 &authority,
    const ZornGen7SmmuFaultIrqAuthority26 &faults,const ZornGen7SmmuStreamAuthority26 &streams,unsigned budget)
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.smmu_domains || !s.host_gpu_tables_attempted || s.host_gpu_oob_attempted ||
       s.host_gpu_mmu_attempted || !s.host_hfi || s.host_hfi->halted() ||
       !s.gpu_icc_inputs_ready || !s.gpu_icc_qos_ready || !s.gpu_icc_inputs || !s.smmu_power ||
       s.smmu_power->guarded_global_io.cookie!=&maps || !maps.boundAndReadyForGpuStart(parent) ||
       !parent.gpuProviderClaimsHeld())return finish(kIOReturnNotReady);
    s.host_gpu_mmu_attempted=true;s.stage=Stage::StoppedRetained;
    // Pin the exact owner/map before the first domain write. Failure or an
    // unknown hardware result keeps this epoch and its backing retained.
    parent.retain();maps.retain();s.host_gpu_mmu_parent=&parent;s.host_gpu_mmu_maps=&maps;
    ZornGen7GpuMmuAuthority26 ownedAuthority{};ownedAuthority.cookie=this;
    ownedAuthority.acquireExclusiveGpuMmuStart=acquireOwnedGpuMmuStartWindow;
    ownedAuthority.authorizePostCpUserRestore=authorizeOwnedPostCpUserRestore;
    (void)authority; // The board owner supplies the request-bound lease callbacks.
    const auto raw=s.smmu_domains->startHostGpuMmu(zero,parent,mmuOwner,irqStreamOwner,*s.gpu_icc_inputs,ownedAuthority,faults,streams,budget);
    if(raw || s.smmu_domains->faulted() || s.gmu_irq->halted() || s.host_hfi->halted() || !s.rsc_storage->forwardAllowed())return finish(raw?raw:kIOReturnNotReady);
    if(!s.host_gpu_mmu_lease_held)return finish(kIOReturnNotReady);
    s.host_gpu_mmu_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::bindOwnedHostGpuCode(FhgStorage &graph,HoujiFullHostNativeMemory &memory,ZornGen7InactiveOwner26 &parent,ZornGen7RegisterMaps26 &maps)
{
    if(!storage_)return kIOReturnNotReady;auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_direct_memory_owner==&parent && s.native_cx_maps==&maps &&
        s.direct_hfi && s.direct_hfi->healthy();
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_gpu_mmu_ready || !s.host_gpu_oob_ready || (!direct && !s.host_hfi) || !s.gmu_irq ||
       !s.smmu_domains || !s.smmu_power || s.smmu_power->guarded_global_io.cookie!=&maps || s.host_gpu_code_attempted || (!direct && s.host_hfi->halted()))return finish(kIOReturnNotReady);
    s.host_gpu_code_attempted=true;s.stage=Stage::StoppedRetained;
    if(direct){
        ZornGen7GpuStartAuthority26 window{};
        window.cookie=this;
        window.acquireExclusiveGpuStart=[](void *cookie,IOService &gpu,IOMemoryDescriptor &gpuResource,
            IOService &gmu,IOMemoryDescriptor &gmuResource)->int{
            auto &board=*static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            auto &state=*board.storage_;
            const bool ready=IORecursiveLockHaveLock(state.gates.startup) &&
                state.stage==Stage::StoppedRetained && state.host_gpu_mmu_ready && state.host_gpu_oob_ready &&
                state.direct_hfi && state.direct_hfi->healthy() && state.gmu_irq->forwardAllowed() &&
                !state.smmu_domains->faulted() && state.rsc_storage->forwardAllowed() &&
                state.native_cx_maps->hostGpuStartPairIs(*state.native_direct_memory_owner,
                    gpu,gpuResource,gmu,gmuResource);
            if(!ready)return kIOReturnNotReady;
            state.host_gpu_start_gpu=&gpu;state.host_gpu_start_gmu=&gmu;
            state.host_gpu_start_gpu_resource=&gpuResource;state.host_gpu_start_gmu_resource=&gmuResource;
            state.host_gpu_start_window_held=true;return 0;
        };
        const auto grant=maps.acquireHostGpuWindow(*this,window);
        if(grant)return finish(grant);
    }
    const auto raw=direct?ZornGen7HostGpuCode26::create(*s.gates.startup,graph,memory,parent,maps,*s.gmu_irq,*s.direct_hfi,*s.smmu_domains,s.host_gpu_code):
        ZornGen7HostGpuCode26::create(*s.gates.startup,graph,memory,parent,maps,*s.gmu_irq,*s.host_hfi,*s.smmu_domains,s.host_gpu_code);
    if(raw || (!direct && s.host_hfi->halted()) || s.gmu_irq->halted() || s.smmu_domains->faulted() || !s.rsc_storage->forwardAllowed())return finish(raw?raw:kIOReturnNotReady);
    s.host_gpu_code_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::configureOwnedHostGpuRegisters(FhgStorage &graph,HoujiFullHostNativeMemory &memory,
    ZornGen7InactiveOwner26 &parent,IORegistryEntry &root,IOService &gpu,ZornGen7RegisterMaps26 &maps,
    OSObject &owner,const ZornGen7GpuRegisterAuthority26 &authority)
{
    if(!storage_)return kIOReturnNotReady;auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_direct_memory_owner==&parent && s.native_cx_maps==&maps &&
        s.direct_hfi && s.direct_hfi->healthy();
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_gpu_code_ready || !s.host_gpu_mmu_ready || !s.host_gpu_oob_ready ||
       !s.smmu_domains || !s.smmu_power || s.smmu_power->guarded_global_io.cookie!=&maps || (!direct && !s.host_hfi) ||
       !s.gmu_irq || s.host_gpu_registers_attempted || (!direct && s.host_hfi->halted()))return finish(kIOReturnNotReady);
    s.host_gpu_registers_attempted=true;s.stage=Stage::StoppedRetained;
    ZornGen7GpuRegisterAuthority26 nativeAuthority=authority;
    if(direct){
        const auto &bo=memory.bo(FHG_CODE_SLOT);
        if(!bo.descriptor() || s.direct_register_code)return finish(kIOReturnNotReady);
        bo.descriptor()->retain();s.direct_register_code=bo.descriptor();
        nativeAuthority.cookie=this;
        nativeAuthority.acquireExclusiveGpuRegisterConfiguration=[](void *cookie,IOService &gpu,
            IOMemoryDescriptor &gpuResource,IOService &gmu,IOMemoryDescriptor &gmuResource,
            IOMemoryDescriptor &code,const uint32_t (&scache)[2],ZornGen7GpuRegisterProfile26 profile)->int{
            auto &board=*static_cast<ZornGen7DarwinBoardOwner *>(cookie);auto &state=*board.storage_;
            IORecursiveLockLock(state.gates.startup);
            const bool ready=state.stage==Stage::StoppedRetained && state.host_gpu_registers_attempted &&
                state.host_gpu_code_ready && state.host_gpu_oob_ready && state.host_gpu_mmu_ready &&
                state.direct_register_code==&code && !scache[0] && !scache[1] &&
                profile==ZornGen7GpuRegisterProfile26::DirectHostNoLlccNoLpacNoPreemptUntrustedTsb &&
                state.direct_hfi && state.direct_hfi->healthy() && state.gmu_irq->forwardAllowed() &&
                !state.smmu_domains->faulted() && state.rsc_storage->forwardAllowed() &&
                state.native_cx_maps->hostGpuStartPairIs(*state.native_direct_memory_owner,
                    gpu,gpuResource,gmu,gmuResource);
            IORecursiveLockUnlock(state.gates.startup);
            return ready?0:kIOReturnNotReady;
        };
    }
    const auto raw=direct?ZornGen7HostGpuRegisters26::create(*s.gates.startup,graph,memory,parent,root,gpu,maps,
        *s.gmu_irq,*s.direct_hfi,*s.smmu_domains,*this,nativeAuthority,s.host_gpu_registers):
        ZornGen7HostGpuRegisters26::create(*s.gates.startup,graph,memory,parent,root,gpu,maps,
        *s.gmu_irq,*s.host_hfi,*s.smmu_domains,owner,authority,s.host_gpu_registers);
    if(raw || (!direct && s.host_hfi->halted()) || s.gmu_irq->halted() || s.smmu_domains->faulted() || !s.rsc_storage->forwardAllowed())return finish(raw?raw:kIOReturnNotReady);
    s.host_gpu_registers_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedHostGpuIrq(IOService &gpu,ZornGen7InactiveOwner26 &parent,
    ZornGen7RegisterMaps26 &maps,IOWorkLoop &loop,OSObject &owner,const ZornGen7GpuIrqAuthority26 &)
{
    if(!storage_ || loop.onThread() || loop.inGate())return kIOReturnNotReady;auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_direct_memory_owner==&parent && s.native_cx_maps==&maps && s.direct_hfi && s.direct_hfi->healthy();
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.host_gpu_registers_ready || !s.host_gpu_registers || !s.host_gpu_oob_ready || !s.smmu_power ||
       s.smmu_power->guarded_global_io.cookie!=&maps || s.host_gpu_irq_attempted || (!direct && s.host_hfi->halted())){
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;}
    s.host_gpu_irq_attempted=true;s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);
    // Keep real event-source construction outside the startup gate. The private
    // native factory checks and retains this actual completed register owner.
    if(direct)IORecursiveLockUnlock(s.gates.startup);
    const auto raw=ZornGen7GpuIrq26::createDisabledWithNativeGic(gpu,parent,maps,loop,owner,
        *s.host_gpu_registers,s.host_gpu_irq);
    if(direct)IORecursiveLockLock(s.gates.startup);
    IORecursiveLockLock(s.gates.startup);
    const bool ready=!raw && s.host_gpu_irq && !s.host_gpu_irq->halted() && !s.gmu_irq->halted() &&
        !(!direct && s.host_hfi->halted()) && !s.smmu_domains->faulted() && s.rsc_storage->forwardAllowed();
    if(ready){s.host_gpu_irq_ready=true;s.stage=Stage::CpuReady;}IORecursiveLockUnlock(s.gates.startup);return raw?raw:(ready?kIOReturnSuccess:kIOReturnNotReady);
}

IOReturn ZornGen7DarwinBoardOwner::initializeOwnedHostCp(FhgStorage &graph,HoujiFullHostNativeMemory &memory,
    ZornGen7InactiveOwner26 &parent,ZornGen7RegisterMaps26 &maps,OSObject &owner,const ZornGen7CpStartAuthority26 &authority)
{
    if(!storage_)return kIOReturnNotReady;auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_direct_memory_owner==&parent && s.native_cx_maps==&maps && s.direct_hfi && s.direct_hfi->healthy();
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_gpu_irq_ready || !s.host_gpu_irq || !s.host_gpu_registers_ready || !s.host_gpu_registers ||
       !s.host_gpu_oob_ready || !s.smmu_power || s.smmu_power->guarded_global_io.cookie!=&maps || s.host_cp_attempted ||
       s.host_gpu_irq->halted() || s.gmu_irq->halted() || (!direct && (!s.host_hfi || s.host_hfi->halted())))return finish(kIOReturnNotReady);
    s.host_cp_attempted=true;s.stage=Stage::StoppedRetained;
    ZornGen7CpStartAuthority26 nativeAuthority=authority;
    if(direct){
        const auto &pool=memory.bo(FHG_GPU_POOL_SLOT);const auto &code=memory.bo(FHG_CODE_SLOT);
        if(!pool.descriptor() || !code.descriptor() || code.descriptor()!=s.direct_register_code || s.direct_cp_pool)return finish(kIOReturnNotReady);
        pool.descriptor()->retain();s.direct_cp_pool=pool.descriptor();nativeAuthority.cookie=this;
        nativeAuthority.acquireExclusiveCpInitialization=[](void *cookie,IOService &gpu,IOMemoryDescriptor &gpuResource,
            IOService &gmu,IOMemoryDescriptor &gmuResource,IOMemoryDescriptor &pool,IOMemoryDescriptor &code,ZornGen7CpProfile26 profile)->int{
            auto &board=*static_cast<ZornGen7DarwinBoardOwner *>(cookie);auto &state=*board.storage_;
            IORecursiveLockLock(state.gates.startup);
            const bool ready=state.stage==Stage::StoppedRetained && state.host_cp_attempted &&
                state.host_gpu_irq_ready && state.host_gpu_registers_ready && state.host_gpu_mmu_ready && state.host_gpu_oob_ready &&
                state.direct_cp_pool==&pool && state.direct_register_code==&code &&
                profile==ZornGen7CpProfile26::InitialNoDmsBeforeAuthenticatedModeTransition &&
                state.direct_hfi && state.direct_hfi->healthy() && state.gmu_irq->forwardAllowed() &&
                state.host_gpu_irq && !state.host_gpu_irq->halted() && !state.smmu_domains->faulted() && state.rsc_storage->forwardAllowed() &&
                state.native_cx_maps->hostGpuStartPairIs(*state.native_direct_memory_owner,gpu,gpuResource,gmu,gmuResource);
            IORecursiveLockUnlock(state.gates.startup);return ready?0:kIOReturnNotReady;
        };
    }
    // The caller owns one recursive startup hold. Give the ring exactly one:
    // its prepare() releases that hold around CP/IRQ accesses and bounded waits.
    if(direct)IORecursiveLockUnlock(s.gates.startup);
    const auto raw=direct?ZornGen7HostRing26::create(*s.gates.startup,graph,memory,parent,maps,*s.host_gpu_irq,*s.gmu_irq,
        *s.direct_hfi,*s.smmu_domains,*s.host_gpu_registers,*this,nativeAuthority,s.host_ring):
        ZornGen7HostRing26::create(*s.gates.startup,graph,memory,parent,maps,*s.host_gpu_irq,*s.gmu_irq,
        *s.host_hfi,*s.smmu_domains,*s.host_gpu_registers,owner,authority,s.host_ring);
    if(direct)IORecursiveLockLock(s.gates.startup);
    if(raw || s.host_gpu_irq->halted() || s.gmu_irq->halted() || (direct?!s.direct_hfi->healthy():s.host_hfi->halted()) ||
       s.smmu_domains->faulted() || !s.rsc_storage->forwardAllowed())return finish(raw?raw:kIOReturnNotReady);
    s.host_cp_init_idle=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::authenticateOwnedHostZap(IORegistryEntry &root,IOService &gpu,
    ZornGen7InactiveOwner26 &parent,OSObject &owner,const ZornGen7ZapAuthority26 &authority)
{
    if(!storage_)return kIOReturnNotReady;auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.native_direct_memory_owner==&parent && s.native_cx_gpu==&gpu && s.direct_hfi && s.direct_hfi->healthy();
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);
    auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_cp_init_idle || !s.host_ring || !s.cx_scm_owner || !s.host_gpu_oob_ready ||
       !s.host_gpu_irq || s.host_gpu_irq->halted() || s.gmu_irq->halted() || (!direct && (!s.host_hfi || s.host_hfi->halted())) ||
       s.smmu_domains->faulted() || !s.rsc_storage->forwardAllowed() || s.host_zap_attempted)return finish(kIOReturnNotReady);
    s.host_zap_attempted=true;s.stage=Stage::StoppedRetained;
    ZornGen7ZapAuthority26 nativeAuthority=authority;
    if(direct){
        nativeAuthority.cookie=this;
        nativeAuthority.acquireExclusiveZapWindow=[](void *cookie,IORegistryEntry &actualRoot,IOService &actualGpu,
            IORegistryEntry &actualScm,IOMemoryDescriptor &reservation,IOMemoryDescriptor &metadata,uint64_t base,size_t bytes)->int{
            auto &board=*static_cast<ZornGen7DarwinBoardOwner *>(cookie);auto &state=*board.storage_;
            OSSharedPtr<IORegistryEntry> scm(IORegistryEntry::fromPath("firmware/qcom_scm",gIODTPlane,nullptr,nullptr,&actualRoot),OSNoRetain);
            OSSharedPtr<IORegistryEntry> gpu(IORegistryEntry::fromPath("arm-io/gpu",gIODTPlane,nullptr,nullptr,&actualRoot),OSNoRetain);
            IORecursiveLockLock(state.gates.startup);
            const bool ready=gpu.get()==&actualGpu && scm.get()==&actualScm && state.native_cx_gpu==&actualGpu &&
                state.stage==Stage::StoppedRetained && state.host_zap_attempted && state.host_cp_init_idle && state.host_gpu_oob_ready &&
                state.host_gpu_irq && !state.host_gpu_irq->halted() && state.gmu_irq->forwardAllowed() &&
                state.direct_hfi && state.direct_hfi->healthy() && !state.smmu_domains->faulted() && state.rsc_storage->forwardAllowed() &&
                state.native_direct_memory_owner->gpuProviderClaimsHeld() &&
                state.smmu_pm->nativeHeldFor(state.smmu_power->provider,*state.gates.startup) && !state.direct_zap_parent;
            IOReturn raw=kIOReturnNotReady;
            if(ready)raw=zorn26_zap_acquire_cpu_window(&reservation,base,bytes);
            if(!raw){reservation.retain();metadata.retain();state.direct_zap_parent=&reservation;state.direct_zap_metadata=&metadata;
                __atomic_store_n(&state.direct_zap_epoch,1u,__ATOMIC_RELEASE);}
            IORecursiveLockUnlock(state.gates.startup);return raw;
        };
        nativeAuthority.checkHeldZapWindow=[](void *cookie,IOService &actualGpu,unsigned phase)->int{
            auto &state=*static_cast<ZornGen7DarwinBoardOwner *>(cookie)->storage_;
            // Invoked while the SCM session/normal-call locks may be held.
            // Never acquire startup in reverse order. The one-way epoch pins
            // retained power/resources; each live receiver/fault check remains.
            const bool held=normal() && phase>=1 && phase<=8 &&
                __atomic_load_n(&state.direct_zap_epoch,__ATOMIC_ACQUIRE)==1 && state.native_cx_gpu==&actualGpu &&
                state.direct_zap_parent && state.direct_zap_metadata && zorn26_zap_cpu_window_held(state.direct_zap_parent) &&
                state.direct_hfi->healthy() && !state.host_gpu_irq->halted() && state.gmu_irq->forwardAllowed() &&
                !state.smmu_domains->faulted() && state.rsc_storage->forwardAllowed();
            return held?0:kIOReturnNotReady;
        };
    }
    if(direct)IORecursiveLockUnlock(s.gates.startup);
    const auto raw=ZornGen7ZapOwner26::create(*s.gates.startup,root,gpu,parent,*s.host_ring,*s.cx_scm_owner,
        direct?static_cast<OSObject &>(*this):owner,nativeAuthority,s.host_zap);
    if(direct)IORecursiveLockLock(s.gates.startup);
    if(raw || s.host_gpu_irq->halted() || s.gmu_irq->halted() || (direct?!s.direct_hfi->healthy():s.host_hfi->halted()) ||
       s.smmu_domains->faulted() || !s.rsc_storage->forwardAllowed())return finish(raw?raw:kIOReturnNotReady);
    s.host_zap_authenticated=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::completeOwnedHostBootstrap(OSObject &owner,const ZornGen7CpBootstrapAuthority26 &authority)
{
    if(!storage_)return kIOReturnNotReady;auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) &&
        s.direct_hfi && s.native_direct_memory_owner && s.native_cx_maps && s.direct_hfi->healthy();
    if(!direct && !callable())return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_zap_authenticated || !s.host_zap || !s.host_ring || !s.host_gpu_oob_ready ||
       !s.host_gpu_irq || s.host_gpu_irq->halted() || s.gmu_irq->halted() || (!direct && (!s.host_hfi || s.host_hfi->halted())) ||
       s.smmu_domains->faulted() || !s.rsc_storage->forwardAllowed() || s.host_bootstrap_attempted)return finish(kIOReturnNotReady);
    s.host_bootstrap_attempted=true;s.stage=Stage::StoppedRetained;
    ZornGen7CpBootstrapAuthority26 nativeAuthority=authority;
    if(direct){
        const auto held=[](OSObject &object,const ZornGen7DirectHfi26 &hfi)->bool{
            const auto &state=*static_cast<ZornGen7DarwinBoardOwner &>(object).storage_;
            return normal() && state.direct_hfi==&hfi && __atomic_load_n(&state.direct_oob_epoch,__ATOMIC_ACQUIRE)==1 &&
                state.host_gpu_oob_ready && state.host_gpu_mmu_ready && state.host_bootstrap_attempted &&
                state.direct_cp_pool && state.direct_register_code && hfi.healthy() &&
                !state.host_gpu_irq->halted() && state.gmu_irq->forwardAllowed() &&
                !state.smmu_domains->faulted() && state.rsc_storage->forwardAllowed();
        };
        auto raw=s.direct_hfi->bindHeldHostGpuOob(*this,*s.gates.startup,held);if(raw)return finish(raw);
        ZornGen7GpuMmuAuthority26 mmu{};mmu.cookie=this;mmu.authorizePostCpUserRestore=authorizeOwnedPostCpUserRestore;
        raw=s.smmu_domains->bindNativePostCpAuthority(*this,mmu);if(raw)return finish(raw);
        nativeAuthority.cookie=this;
        nativeAuthority.acquireAuthenticatedBootstrap=[](void *cookie,IOService &gpu,IOMemoryDescriptor &gpuResource,
            IOService &gmu,IOMemoryDescriptor &gmuResource,IOMemoryDescriptor &pool,IOMemoryDescriptor &code,ZornGen7ZapOwner26 &zap)->int{
            auto &board=*static_cast<ZornGen7DarwinBoardOwner *>(cookie);auto &state=*board.storage_;
            IORecursiveLockLock(state.gates.startup);
            const bool ready=state.stage==Stage::StoppedRetained && state.host_bootstrap_attempted && state.host_zap_authenticated &&
                state.host_zap==&zap && state.host_ring && zap.authenticatedForRing(*state.host_ring) &&
                state.direct_cp_pool==&pool && state.direct_register_code==&code && state.direct_hfi->bootstrapOobHeld() &&
                !state.host_gpu_irq->halted() && state.gmu_irq->forwardAllowed() && !state.smmu_domains->faulted() &&
                state.rsc_storage->forwardAllowed() && state.smmu_pm->nativeHeldFor(state.smmu_power->provider,*state.gates.startup) &&
                state.native_cx_maps->hostGpuStartPairIs(*state.native_direct_memory_owner,gpu,gpuResource,gmu,gmuResource);
            IORecursiveLockUnlock(state.gates.startup);return ready?0:kIOReturnNotReady;
        };
        nativeAuthority.authorizeSuccessfulOobRelease=[](void *cookie,IOService &gpu,IOService &gmu,ZornGen7HostRing26 &ring)->int{
            auto &state=*static_cast<ZornGen7DarwinBoardOwner *>(cookie)->storage_;
            IORecursiveLockLock(state.gates.startup);
            const bool ready=state.stage==Stage::StoppedRetained && state.host_bootstrap_attempted && state.host_ring==&ring &&
                state.native_cx_gpu==&gpu && state.native_cx_gmu==&gmu &&
                __atomic_load_n(&state.direct_oob_epoch,__ATOMIC_ACQUIRE)==1 && state.host_zap_authenticated &&
                state.host_zap->authenticatedForRing(ring) && ring.bootstrapReadyForOobTransport(*state.direct_hfi) &&
                state.direct_hfi->healthy() && !state.host_gpu_irq->halted() && state.gmu_irq->forwardAllowed() &&
                !state.smmu_domains->faulted() && state.rsc_storage->forwardAllowed();
            IORecursiveLockUnlock(state.gates.startup);return ready?0:kIOReturnNotReady;
        };
    }
    if(direct)IORecursiveLockUnlock(s.gates.startup);
    const auto raw=s.host_ring->completeAuthenticatedBootstrap(*s.host_zap,direct?static_cast<OSObject &>(*this):owner,nativeAuthority);
    if(direct)IORecursiveLockLock(s.gates.startup);
    if(raw || s.host_gpu_irq->halted() || s.gmu_irq->halted() || (direct?!s.direct_hfi->healthy():s.host_hfi->halted()) ||
       s.smmu_domains->faulted() || !s.rsc_storage->forwardAllowed())return finish(raw?raw:kIOReturnNotReady);
    if(direct){if(!s.direct_hfi->bootstrapOobReleaseReturned())return finish(kIOReturnNotReady);
        __atomic_store_n(&s.direct_oob_epoch,2u,__ATOMIC_RELEASE);}
    s.host_bootstrap_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::prepareOwnedDirectRuntime(OSObject &owner,const ZornGen7DirectRuntimeAuthority26 &authority,size_t capacity)
{
    if(!storage_)return kIOReturnNotReady;auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) && s.direct_hfi &&
        s.native_direct_memory_owner && s.native_cx_maps && s.direct_hfi->healthy() &&
        __atomic_load_n(&s.direct_oob_epoch,__ATOMIC_ACQUIRE)==2 && s.direct_hfi->bootstrapOobReleaseReturned();
    if(!direct && (!callable() || IORecursiveLockHaveLock(s.gates.startup)))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_bootstrap_ready || !s.host_ring || s.host_direct_runtime_attempted ||
       s.host_gpu_irq->halted() || s.gmu_irq->halted() || (direct?!s.direct_hfi->healthy():(!s.host_hfi || s.host_hfi->halted())) || s.smmu_domains->faulted())return finish(kIOReturnNotReady);
    s.host_direct_runtime_attempted=true;s.stage=Stage::StoppedRetained;
    // Preserve the supplied real task/client permission callbacks and their
    // cookie behind this board owner's independent native-runtime cookie.
    // Missing callbacks remain absent, so later stages still fail closed.
    s.forwarded_direct_runtime_authority=authority;
    ZornGen7DirectRuntimeAuthority26 ownedAuthority{};ownedAuthority.cookie=this;
    ownedAuthority.acquireNativeRuntime=acquireOwnedNativeRuntimeWindow;
    if(authority.acquireKernelTask)ownedAuthority.acquireKernelTask=forwardDirectRuntimeKernelTaskGrant;
    if(authority.checkHeldKernelTask)ownedAuthority.checkHeldKernelTask=forwardDirectRuntimeKernelTaskCheck;
    if(authority.authorizeKernelTaskRelease)ownedAuthority.authorizeKernelTaskRelease=forwardDirectRuntimeKernelTaskRelease;
    if(authority.acquireKernelClient)ownedAuthority.acquireKernelClient=forwardDirectRuntimeKernelClientGrant;
    if(authority.checkHeldKernelClient)ownedAuthority.checkHeldKernelClient=forwardDirectRuntimeKernelClientCheck;
    if(authority.authorizeKernelClientRelease)ownedAuthority.authorizeKernelClientRelease=forwardDirectRuntimeKernelClientRelease;
    if(direct){
        ownedAuthority.acquireKernelTask=[](void *cookie,IOService &gpu,IOMemoryDescriptor &gpuRegisters,
            IOService &gmu,IOMemoryDescriptor &gmuRegisters,IOMemoryDescriptor &image)->int{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal())return kIOReturnNotReady;auto &state=*board->storage_;
            if(IORecursiveLockHaveLock(state.gates.startup))return kIOReturnNotReady;
            IORecursiveLockLock(state.gates.startup);
            auto finish=[&](int raw){IORecursiveLockUnlock(state.gates.startup);return raw;};
            if(state.direct_task_attempted)return finish(kIOReturnExclusiveAccess);
            state.direct_task_attempted=true;
            if(state.stage!=Stage::StoppedRetained || !state.host_known_image_attempted || !state.host_ring ||
               state.native_cx_gpu!=&gpu || state.native_cx_gmu!=&gmu ||
               state.host_gpu_start_gpu_resource!=&gpuRegisters || state.host_gpu_start_gmu_resource!=&gmuRegisters ||
               __atomic_load_n(&state.direct_oob_epoch,__ATOMIC_ACQUIRE)!=2 ||
               !state.direct_hfi || !state.direct_hfi->bootstrapOobReleaseReturned() ||
               !state.host_ring->nativeKernelTaskBinding(image,1))return finish(kIOReturnNotReady);
            image.retain();state.direct_task_image=&image;state.direct_task_thread=current_thread();state.direct_task_granted=true;
            __atomic_store_n(&state.direct_oob_epoch,3u,__ATOMIC_RELEASE);
            if(!state.nativeTaskWindowHeld(image,1)){state.direct_task_granted=false;return finish(kIOReturnNotReady);}
            return finish(kIOReturnSuccess);
        };
        ownedAuthority.checkHeldKernelTask=[](void *cookie,IOMemoryDescriptor &image,unsigned phase)->int{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal())return kIOReturnNotReady;auto &state=*board->storage_;
            IORecursiveLockLock(state.gates.startup);const bool ready=state.nativeTaskWindowHeld(image,phase);
            IORecursiveLockUnlock(state.gates.startup);return ready?kIOReturnSuccess:kIOReturnNotReady;
        };
        ownedAuthority.authorizeKernelTaskRelease=[](void *cookie,IOService &gpu,IOMemoryDescriptor &image)->int{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal())return kIOReturnNotReady;auto &state=*board->storage_;
            if(IORecursiveLockHaveLock(state.gates.startup))return kIOReturnNotReady;
            IORecursiveLockLock(state.gates.startup);
            const bool ready=!state.direct_task_release_allowed && state.native_cx_gpu==&gpu &&
                state.nativeTaskWindowHeld(image,5) && state.host_ring->nativeKernelTaskCanRelease(image);
            if(ready)state.direct_task_release_allowed=true;
            IORecursiveLockUnlock(state.gates.startup);return ready?kIOReturnSuccess:kIOReturnNotReady;
        };
    }
    if(direct){
        ownedAuthority.acquireKernelClient=[](void *cookie,IOUserClient &client,IOService &gpu,IOMemoryDescriptor &gpuRegisters,
            IOService &gmu,IOMemoryDescriptor &gmuRegisters)->int{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal())return kIOReturnNotReady;auto &state=*board->storage_;
            if(IORecursiveLockHaveLock(state.gates.startup))return kIOReturnNotReady;
            IORecursiveLockLock(state.gates.startup);
            auto finish=[&](int raw){IORecursiveLockUnlock(state.gates.startup);return raw;};
            if(state.direct_client_attempted)return finish(kIOReturnExclusiveAccess);
            state.direct_client_attempted=true;
            if(state.stage!=Stage::CpuReady || !state.host_known_image_ready || !state.direct_task_release_allowed ||
               !state.host_ring || state.native_cx_gpu!=&gpu || state.native_cx_gmu!=&gmu ||
               state.host_gpu_start_gpu_resource!=&gpuRegisters || state.host_gpu_start_gmu_resource!=&gmuRegisters ||
               __atomic_load_n(&state.direct_oob_epoch,__ATOMIC_ACQUIRE)!=4 || !state.direct_hfi ||
               !state.host_ring->nativeKernelClientBinding(client,1))return finish(kIOReturnNotReady);
            uint32_t image[8]{};state.direct_hfi->copyKernelTaskOobObservation(image);
            if(image[0]!=127 || image[7])return finish(kIOReturnNotReady);
            state.direct_client_identity=&client;state.direct_client_granted=true;
            __atomic_store_n(&state.direct_oob_epoch,5u,__ATOMIC_RELEASE);
            if(!state.nativeClientWindowHeld(client,1)){state.direct_client_granted=false;return finish(kIOReturnNotReady);}
            return finish(kIOReturnSuccess);
        };
        ownedAuthority.checkHeldKernelClient=[](void *cookie,IOUserClient &client,unsigned phase)->int{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal())return kIOReturnNotReady;auto &state=*board->storage_;
            IORecursiveLockLock(state.gates.startup);const bool ready=state.nativeClientWindowHeld(client,phase);
            IORecursiveLockUnlock(state.gates.startup);return ready?kIOReturnSuccess:kIOReturnNotReady;
        };
        ownedAuthority.authorizeKernelClientRelease=[](void *cookie,IOUserClient &client)->int{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal())return kIOReturnNotReady;auto &state=*board->storage_;
            if(IORecursiveLockHaveLock(state.gates.startup))return kIOReturnNotReady;
            IORecursiveLockLock(state.gates.startup);
            const bool ready=!state.direct_client_release_allowed && state.nativeClientWindowHeld(client,4) &&
                state.host_ring->nativeKernelClientCanRelease(client);
            if(ready)state.direct_client_release_allowed=true;
            IORecursiveLockUnlock(state.gates.startup);return ready?kIOReturnSuccess:kIOReturnNotReady;
            // Permission precedes the real OOB store, not a claimed hardware
            // stop. Ring owns successful client reference release afterward.
        };
    }
    if(direct)IORecursiveLockUnlock(s.gates.startup);
    const auto raw=s.host_ring->prepareDirectRuntime(direct?static_cast<OSObject &>(*this):owner,ownedAuthority,capacity);
    if(direct)IORecursiveLockLock(s.gates.startup);
    if(raw || s.host_gpu_irq->halted() || s.gmu_irq->halted() || (direct?!s.direct_hfi->healthy():(!s.host_hfi || s.host_hfi->halted())) || s.smmu_domains->faulted())return finish(raw?raw:kIOReturnNotReady);
    if(!s.host_direct_runtime_window_held)return finish(kIOReturnNotReady);
    s.host_direct_runtime_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::runOwnedKnownImage()
{
    if(!storage_)return kIOReturnNotReady;auto &s=*storage_;
    const bool direct=normal() && IORecursiveLockHaveLock(s.gates.startup) && s.direct_hfi &&
        s.direct_hfi->healthy() && __atomic_load_n(&s.direct_oob_epoch,__ATOMIC_ACQUIRE)==2;
    if(!direct && (!callable() || IORecursiveLockHaveLock(s.gates.startup)))return kIOReturnNotReady;
    IORecursiveLockLock(s.gates.startup);auto finish=[&](IOReturn raw){IORecursiveLockUnlock(s.gates.startup);return raw;};
    if(s.stage!=Stage::CpuReady || !s.host_direct_runtime_ready || !s.host_ring || s.host_known_image_attempted ||
       !s.rsc_storage || !s.rsc_storage->forwardAllowed() || s.host_gpu_irq->halted() || s.gmu_irq->halted() ||
       (direct?!s.direct_hfi->healthy():(!s.host_hfi || s.host_hfi->halted())) || s.smmu_domains->faulted())return finish(kIOReturnNotReady);
    s.host_known_image_attempted=true;s.stage=Stage::StoppedRetained;
    if(direct)IORecursiveLockUnlock(s.gates.startup);
    const auto raw=s.host_ring->runKnownImage();
    if(direct)IORecursiveLockLock(s.gates.startup);
    if(raw || !s.rsc_storage->forwardAllowed() || s.host_gpu_irq->halted() || s.gmu_irq->halted() ||
       (direct?!s.direct_hfi->healthy():(!s.host_hfi || s.host_hfi->halted())) || s.smmu_domains->faulted())return finish(raw?raw:kIOReturnNotReady);
    if(direct){uint32_t task[8]{};s.direct_hfi->copyKernelTaskOobObservation(task);
        if(!s.direct_task_release_allowed || task[0]!=127 || task[7])return finish(kIOReturnNotReady);
        __atomic_store_n(&s.direct_oob_epoch,4u,__ATOMIC_RELEASE);}
    s.host_known_image_ready=true;s.stage=Stage::CpuReady;return finish(kIOReturnSuccess);
}

IOReturn ZornGen7DarwinBoardOwner::copyOwnedKnownImageToConsole()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;IORecursiveLockLock(s.gates.startup);
    auto *ring=s.host_ring;const bool ready=s.stage==Stage::CpuReady && s.host_known_image_ready && ring &&
        s.rsc_storage && s.rsc_storage->forwardAllowed() && !s.host_gpu_irq->halted() && !s.gmu_irq->halted() &&
        !s.host_hfi->halted() && !s.smmu_domains->faulted();
    IORecursiveLockUnlock(s.gates.startup);return ready?ring->copyKnownImageToConsole():kIOReturnNotReady;
}

IOReturn ZornGen7DarwinBoardOwner::publishOwnedKernelIo()
{
    if(!callable())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;IORecursiveLockLock(s.gates.startup);
    auto *ring=s.host_ring;const bool ready=s.stage==Stage::CpuReady && s.host_known_image_ready && ring &&
        s.rsc_storage && s.rsc_storage->forwardAllowed() && !s.host_gpu_irq->halted() && !s.gmu_irq->halted() && !s.smmu_domains->faulted();
    IORecursiveLockUnlock(s.gates.startup);return ready?ring->publishKernelIo():kIOReturnNotReady;
}

IOReturn ZornGen7DarwinBoardOwner::publishOwnedApplicationIo(OSObject &owner,const ZornGen7AppAuthority26 &authority)
{
    // Native application publication uses this board's actual powered resource
    // owners and a distinct client/task session, never the kernel callback ABI.
    if(storage_ && normal() && storage_->direct_hfi){auto &s=*storage_;
        if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;
        IORecursiveLockLock(s.gates.startup);
        const bool ready=s.stage==Stage::CpuReady && !s.direct_app_publish_attempted && !s.direct_client_attempted &&
            s.host_direct_runtime_ready && s.host_known_image_ready && s.direct_task_release_allowed && s.host_ring &&
            __atomic_load_n(&s.direct_oob_epoch,__ATOMIC_ACQUIRE)==4 && s.direct_hfi->healthy() &&
            s.rsc_storage && s.rsc_storage->forwardAllowed() && s.host_gpu_irq && !s.host_gpu_irq->halted() &&
            s.gmu_irq && !s.gmu_irq->halted() && s.smmu_domains && !s.smmu_domains->faulted();
        if(!ready){IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;}
        s.direct_app_publish_attempted=true;auto *ring=s.host_ring;ring->retain();retain();
        IORecursiveLockUnlock(s.gates.startup);
        ZornGen7AppAuthority26 applicationAuthority{};applicationAuthority.cookie=this;
        applicationAuthority.acquire=[](void *cookie,IOUserClient &client,task_t task,ZornGen7HostRing26 &ring,
            IOService &gpu,IOMemoryDescriptor &gpuRegisters,IOService &gmu,IOMemoryDescriptor &gmuRegisters)->IOReturn{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal() || !task || task==kernel_task || task!=current_task())return kIOReturnNotReady;
            auto &state=*board->storage_;if(IORecursiveLockHaveLock(state.gates.startup))return kIOReturnNotReady;
            IORecursiveLockLock(state.gates.startup);
            auto finish=[&](IOReturn raw){IORecursiveLockUnlock(state.gates.startup);return raw;};
            if(state.direct_app_attempted || state.direct_app_granted || state.direct_app_identity || state.direct_app_task ||
               state.direct_app_acquires!=state.direct_app_releases || state.direct_app_acquires==UINT32_MAX)
                return finish(kIOReturnExclusiveAccess);
            state.direct_app_attempted=true;
            if(state.stage!=Stage::CpuReady || !state.direct_app_publish_attempted || state.direct_client_attempted ||
               state.host_ring!=&ring || state.native_cx_gpu!=&gpu || state.native_cx_gmu!=&gmu ||
               state.host_gpu_start_gpu_resource!=&gpuRegisters || state.host_gpu_start_gmu_resource!=&gmuRegisters ||
               __atomic_load_n(&state.direct_oob_epoch,__ATOMIC_ACQUIRE)!=4 || !state.direct_hfi ||
               !ring.nativeApplicationBinding(client,task,1,ZornGen7AppOperation26::PrepareTables))return finish(kIOReturnNotReady);
            uint32_t image[8]{};state.direct_hfi->copyKernelTaskOobObservation(image);
            if(image[0]!=127 || image[7])return finish(kIOReturnNotReady);
            state.direct_app_identity=&client;state.direct_app_task=task;state.direct_app_granted=true;++state.direct_app_acquires;
            __atomic_store_n(&state.direct_oob_epoch,6u,__ATOMIC_RELEASE);
            if(!state.nativeApplicationWindowHeld(client,task,1,ZornGen7AppOperation26::PrepareTables)){
                state.direct_app_granted=false;return finish(kIOReturnNotReady);}
            return finish(kIOReturnSuccess);
        };
        applicationAuthority.check=[](void *cookie,IOUserClient &client,task_t opening,task_t caller,
            ZornGen7AppOperation26 operation)->IOReturn{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal() || caller!=current_task() ||
               unsigned(operation)>unsigned(ZornGen7AppOperation26::Timestamp))return kIOReturnNotReady;
            auto &state=*board->storage_;if(IORecursiveLockHaveLock(state.gates.startup))return kIOReturnNotReady;
            IORecursiveLockLock(state.gates.startup);
            const bool held=state.nativeApplicationWindowHeld(client,opening,2,operation);
            IORecursiveLockUnlock(state.gates.startup);return held?kIOReturnSuccess:kIOReturnNotReady;
        };
        applicationAuthority.release=[](void *cookie,IOUserClient &client,task_t opening)->IOReturn{
            auto *board=static_cast<ZornGen7DarwinBoardOwner *>(cookie);
            if(!board || !board->storage_ || !normal())return kIOReturnNotReady;auto &state=*board->storage_;
            if(IORecursiveLockHaveLock(state.gates.startup))return kIOReturnNotReady;
            IORecursiveLockLock(state.gates.startup);
            // Exact Ring binding requires its actual process/VM retirement,
            // completed OOB clear and the same serialized clientClose thread.
            const bool held=state.nativeApplicationWindowHeld(client,opening,3,ZornGen7AppOperation26::Close);
            if(held){state.direct_app_identity=nullptr;state.direct_app_task=TASK_NULL;state.direct_app_granted=false;
                state.direct_app_attempted=false;++state.direct_app_releases;
                __atomic_store_n(&state.direct_oob_epoch,4u,__ATOMIC_RELEASE);}
            IORecursiveLockUnlock(state.gates.startup);return held?kIOReturnSuccess:kIOReturnNotReady;
            // Relinquish only this successful application session. Root PM and
            // provider claims remain owned; this is no power-off/DMA-stop claim.
        };
        // Keep the powered owner ready while registerService exposes the real
        // service. A newly admitted client can immediately check actual refs;
        // there is no temporary StoppedRetained publication race.
        const auto raw=ring->publishApplicationIo(*this,applicationAuthority);
        IORecursiveLockLock(s.gates.startup);
        const bool healthy=!raw && s.host_ring==ring && s.stage==Stage::CpuReady && s.rsc_storage->forwardAllowed() &&
            !s.host_gpu_irq->halted() && !s.gmu_irq->halted() && s.direct_hfi->healthy() && !s.smmu_domains->faulted();
        if(!healthy)s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);
        ring->release();release();return raw?raw:(healthy?kIOReturnSuccess:kIOReturnNotReady);
    }

    if(!callable())return kIOReturnNotReady;auto &s=*storage_;
    if(IORecursiveLockHaveLock(s.gates.startup))return kIOReturnNotReady;IORecursiveLockLock(s.gates.startup);
    if(s.stage!=Stage::CpuReady || !s.host_direct_runtime_ready || !s.host_known_image_ready || !s.host_ring ||
       !s.rsc_storage || !s.rsc_storage->forwardAllowed() || s.host_gpu_irq->halted() || s.gmu_irq->halted() ||
       s.host_hfi->halted() || s.smmu_domains->faulted()){
        IORecursiveLockUnlock(s.gates.startup);return kIOReturnNotReady;}
    s.stage=Stage::StoppedRetained;IORecursiveLockUnlock(s.gates.startup);
    const auto raw=s.host_ring->publishApplicationIo(owner,authority);
    IORecursiveLockLock(s.gates.startup);
    const bool healthy=!raw && s.rsc_storage->forwardAllowed() && !s.host_gpu_irq->halted() &&
        !s.gmu_irq->halted() && !s.host_hfi->halted() && !s.smmu_domains->faulted();
    if(healthy)s.stage=Stage::CpuReady;IORecursiveLockUnlock(s.gates.startup);
    return raw?raw:(healthy?kIOReturnSuccess:kIOReturnNotReady);
}
