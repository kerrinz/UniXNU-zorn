/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGen7HostGpuRegisters26.h"
#include "ZornGen7InactiveOwner26.h"
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7HwschedHfi26.h"
#include "ZornGen7DirectHfi26.h"
#include "ZornGen7GmuIrq26.h"
#include "ZornGen7SmmuDomain26.h"
#include "ZornGen7FirmwareAssets26.h"
#include "GpuCodeMemory.h"
#include "GpuGen7Config.h"
#include "Adreno740/NativeAdrenoABI.h"
#include <IOKit/IOLib.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <libkern/c++/OSSharedPtr.h>
#include <libkern/c++/OSData.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <string.h>
OSDefineMetaClassAndStructors(ZornGen7HostGpuRegisters26,OSObject)
static uint32_t zornGxRegistersObservation[6];
void Zorn26RecordGxRegistersResult(IOReturn raw){zornGxRegistersObservation[0]=uint32_t(raw);}
extern "C" void zorn26_native_gx_registers_observation(uint32_t (&out)[6])
{memcpy(out,zornGxRegistersObservation,sizeof(out));}
namespace {
bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}
bool property(IORegistryEntry &node,const char *name,const void *bytes,size_t count)
{
    OSSharedPtr<OSObject> o(node.copyProperty(name),OSNoRetain);auto *d=OSDynamicCast(OSData,o.get());
    return d && d->getBytesNoCopy() && d->getLength()==count && !memcmp(d->getBytesNoCopy(),bytes,count);
}
}
struct ZornGen7HostGpuRegisters26::Storage {
    IORecursiveLock &gate;FhgStorage &graph;HoujiFullHostNativeMemory &memory;ZornGen7InactiveOwner26 &parent;
    IORegistryEntry &root;IOService &gpu;ZornGen7RegisterMaps26 &maps;ZornGen7GmuIrq26 &irq;
    OSObject &hfi;bool (*halted)(OSObject &);ZornGen7SmmuDomain26 &domain;OSObject &authorityOwner;const ZornGen7GpuRegisterAuthority26 authority;
    h7c_result configuration{};bool attempted=false,ready=false,grantReturned=false;IOReturn grantRaw=kIOReturnNotReady;
    uint32_t scache[2]{},after[2]{};bool ioReturned=false;int ioRaw=0;uint32_t ioAddress=0;bool ioWrite=false;
    bool publishReturned=false;IOReturn publishRaw=kIOReturnNotReady;
    Storage(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,ZornGen7InactiveOwner26 &p,IORegistryEntry &r,
        IOService &u,ZornGen7RegisterMaps26 &v,ZornGen7GmuIrq26 &q,OSObject &h,bool (*check)(OSObject &),ZornGen7SmmuDomain26 &d,
        OSObject &o,const ZornGen7GpuRegisterAuthority26 &a):gate(g),graph(f),memory(m),parent(p),root(r),gpu(u),maps(v),irq(q),hfi(h),halted(check),domain(d),authorityOwner(o),authority(a){}
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7HostGpuRegisters26::create(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,IORegistryEntry &r,IOService &u,ZornGen7RegisterMaps26 &v,ZornGen7GmuIrq26 &q,
    ZornGen7HwschedHfi26 &h,ZornGen7SmmuDomain26 &d,OSObject &a,const ZornGen7GpuRegisterAuthority26 &authority,ZornGen7HostGpuRegisters26 *&out)
{
    return createTransport(g,f,m,p,r,u,v,q,h,[](OSObject &o){return static_cast<ZornGen7HwschedHfi26 &>(o).halted();},d,a,authority,out);
}
IOReturn ZornGen7HostGpuRegisters26::create(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,IORegistryEntry &r,IOService &u,ZornGen7RegisterMaps26 &v,ZornGen7GmuIrq26 &q,
    ZornGen7DirectHfi26 &h,ZornGen7SmmuDomain26 &d,OSObject &a,const ZornGen7GpuRegisterAuthority26 &authority,ZornGen7HostGpuRegisters26 *&out)
{
    return createTransport(g,f,m,p,r,u,v,q,h,[](OSObject &o){return static_cast<ZornGen7DirectHfi26 &>(o).halted();},d,a,authority,out);
}
IOReturn ZornGen7HostGpuRegisters26::createTransport(IORecursiveLock &g,FhgStorage &f,HoujiFullHostNativeMemory &m,
    ZornGen7InactiveOwner26 &p,IORegistryEntry &r,IOService &u,ZornGen7RegisterMaps26 &v,ZornGen7GmuIrq26 &q,
    OSObject &h,bool (*halted)(OSObject &),ZornGen7SmmuDomain26 &d,OSObject &a,const ZornGen7GpuRegisterAuthority26 &authority,ZornGen7HostGpuRegisters26 *&out)
{
    if(out || !normal() || !IORecursiveLockHaveLock(&g) || !authority.acquireExclusiveGpuRegisterConfiguration)return kIOReturnNotReady;
    auto *o=new ZornGen7HostGpuRegisters26;if(!o)return kIOReturnNoMemory;
    if(!o->init()){o->release();return kIOReturnNoMemory;}o->retain();o->pinned_=true;out=o;
    p.retain();r.retain();u.retain();v.retain();q.retain();h.retain();d.retain();a.retain();
    void *bytes=IOMallocZero(sizeof(Storage));if(!bytes)return kIOReturnNoMemory;
    o->storage_=new(bytes)Storage(g,f,m,p,r,u,v,q,h,halted,d,a,authority);
    const auto raw=o->run();
    auto &state=*o->storage_;
    zornGxRegistersObservation[0]=uint32_t(raw);
    zornGxRegistersObservation[1]=state.configuration.completed;
    zornGxRegistersObservation[2]=state.ioAddress;
    zornGxRegistersObservation[3]=uint32_t(state.ioRaw);
    zornGxRegistersObservation[4]=state.configuration.code;
    zornGxRegistersObservation[5]=state.configuration.record_ready;
    return raw;
}
int ZornGen7HostGpuRegisters26::guard(void *context)
{
    auto *o=static_cast<ZornGen7HostGpuRegisters26 *>(context);
    if(!o || !o->storage_ || !normal())return 1;auto &s=*o->storage_;
    return !IORecursiveLockHaveLock(&s.gate) || s.irq.halted() || s.halted(s.hfi) || s.domain.faulted();
}
int ZornGen7HostGpuRegisters26::read(void *context,uint32_t at,uint32_t *out)
{
    if(!out || guard(context))return 1;auto &s=*static_cast<ZornGen7HostGpuRegisters26 *>(context)->storage_;
    uint32_t value=0;s.ioReturned=false;s.ioAddress=at;s.ioWrite=false;s.ioRaw=s.maps.accessHostGpuRegisterWord(at,false,value);s.ioReturned=true;
    if(!s.ioRaw)*out=value;return s.ioRaw;
}
int ZornGen7HostGpuRegisters26::write(void *context,uint32_t at,uint32_t value)
{
    if(guard(context))return 1;auto &s=*static_cast<ZornGen7HostGpuRegisters26 *>(context)->storage_;
    s.ioReturned=false;s.ioAddress=at;s.ioWrite=true;s.ioRaw=s.maps.accessHostGpuRegisterWord(at,true,value);s.ioReturned=true;return s.ioRaw;
}
int ZornGen7HostGpuRegisters26::delay(void *context,unsigned us)
{
    if(guard(context) || us!=1)return 1;IODelay(us);return guard(context);
}
int ZornGen7HostGpuRegisters26::publish(void *context,const uint32_t *words,unsigned count)
{
    if(guard(context) || !words || count!=H7C_WORDS)return 1;auto &s=*static_cast<ZornGen7HostGpuRegisters26 *>(context)->storage_;
    if(s.configuration.completed!=H7C_OPS || s.configuration.power_pairs!=H7C_PAIRS ||
       words[0] || words[1] || words[2] || words[3]!=(H7C_IFPC|(H7C_PREEMPT<<8)))return 1;
    for(unsigned i=0;i<H7C_PAIRS;++i)if(words[4+i*2]!=(h7c_power_regs[i].address-0x3d00000)/4 || words[5+i*2]!=s.configuration.power_values[i])return 1;
    auto &bo=const_cast<NativeAdrenoMemory &>(s.memory.bo(FHG_CODE_SLOT));
    if(bo.quarantined() || !bo.writeCombined() || bo.imported() || bo.readOnly() || bo.deviceReferences()!=1 ||
       !bo.mapping() || bo.bytes()!=HCC_BYTES || bo.ownedBytes()!=HCC_BYTES)return 1;
    auto *to=reinterpret_cast<volatile uint32_t *>(static_cast<uint8_t *>(bo.mapping())+HCC_RECORD_OFFSET);
    for(unsigned i=0;i<1024;++i)if(to[i])return 1;
    for(unsigned i=0;i<count;++i)to[i]=words[i];
    for(unsigned i=0;i<1024;++i)if(to[i]!=(i<count?words[i]:0))return 1;
    if(guard(context))return 1;s.publishRaw=bo.publishForDevice(HCC_RECORD_OFFSET,4096,true);s.publishReturned=true;
    if(s.publishRaw || guard(context))return 1;
    s.configuration.record_crc=hcc_crc32(static_cast<const uint8_t *>(bo.mapping())+HCC_RECORD_OFFSET,4096);return 0;
}
IOReturn ZornGen7HostGpuRegisters26::run()
{
    if(guard(this))return kIOReturnNotReady;auto &s=*storage_;if(s.attempted)return kIOReturnNotReady;s.attempted=true;
    constexpr char compatible[]="qcom,adreno-gpu-gen7-9-1\0qcom,kgsl-3d0";
    constexpr uint32_t mal=32,ubwc=4,ddr=8;
    OSSharedPtr<IORegistryEntry> chosen(IORegistryEntry::fromPath("chosen",gIODTPlane,nullptr,nullptr,&s.root),OSNoRetain);
    // Actual native declarations checked against exact retained K80 source,
    // not another board default or claimed hardware fuse/capability result.
    if(!chosen || !property(s.gpu,"compatible",compatible,sizeof(compatible)) ||
       !property(s.gpu,"qcom,min-access-length",&mal,4) || !property(s.gpu,"qcom,ubwc-mode",&ubwc,4) ||
       !property(*chosen,"zorn,ddr-device-type",&ddr,4) || !s.memory.prepared())return kIOReturnUnsupported;
    const auto &bo=s.memory.bo(FHG_CODE_SLOT);
    if(!bo.descriptor() || !ZornGen7ValidateOwnedGpuCode26(bo) || !s.maps.bindHostGpuRegisters(*this,s.parent,s.gpu))return kIOReturnNotReady;
    if(read(this,0x3d0f004,&s.scache[0]) || read(this,0x3d0f008,&s.scache[1]))return kIOReturnIOError;
    // Foreign window acquisition outside the startup gate and map/access locks.
    IORecursiveLockUnlock(&s.gate);
    s.grantRaw=s.maps.acquireHostGpuRegisterWindow(s.authorityOwner,s.authority,*bo.descriptor(),s.scache);
    IORecursiveLockLock(&s.gate);s.grantReturned=true;if(s.grantRaw || guard(this))return s.grantRaw?s.grantRaw:kIOReturnNotReady;
    if(read(this,0x3d0f004,&s.after[0]) || read(this,0x3d0f008,&s.after[1]) ||
       s.after[0]!=s.scache[0] || s.after[1]!=s.scache[1] || s.after[0] || s.after[1])return kIOReturnNotReady;
    uint32_t sqe=0;if(read(this,0x3d02020,&sqe) || sqe)return kIOReturnNotReady;
    // Reuse original102-op/75-snapshot source algorithm with its explicit
    // register verification masks and1000x1us poll. This does not qualify
    // unverified/masked bits or establish TEE/LLCC/fuse/stop rights.
    const h7c_io io{this,guard,read,write,delay,publish};const unsigned code=h7c_run(&io,&s.configuration);
    if(code!=H7C_OK || s.configuration.completed!=H7C_OPS || !s.configuration.record_ready ||
       s.configuration.power_pairs!=H7C_PAIRS || s.configuration.control_after || guard(this))return kIOReturnIOError;
    if(read(this,0x3d0f004,&s.after[0]) || read(this,0x3d0f008,&s.after[1]) || s.after[0] || s.after[1])return kIOReturnNotReady;
    s.ready=true;return kIOReturnSuccess;
    // SQE still disabled. No CP packet/trust switch/PAS,IRQ enable,reset,
    // recovery,LLCC activation,release or retry. All real resources retained.
}
void ZornGen7HostGpuRegisters26::free(){if(pinned_)return;OSObject::free();}

bool ZornGen7HostGpuRegisters26::verifyRecord(const NativeAdrenoMemory &bo)const
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return false;const auto &s=*storage_;
    if(!s.ready || !s.configuration.record_ready || &bo!=&s.memory.bo(FHG_CODE_SLOT) || bo.quarantined() ||
       !bo.writeCombined() || bo.imported() || bo.readOnly() || bo.deviceReferences()!=1 || !bo.mapping() || bo.bytes()!=HCC_BYTES)return false;
    const auto *p=reinterpret_cast<const volatile uint32_t *>(static_cast<const uint8_t *>(bo.mapping())+HCC_RECORD_OFFSET);
    if(p[0] || p[1] || p[2] || p[3]!=(H7C_IFPC|(H7C_PREEMPT<<8)))return false;
    for(unsigned i=0;i<H7C_PAIRS;++i)if(p[4+i*2]!=(h7c_power_regs[i].address-0x3d00000)/4 || p[5+i*2]!=s.configuration.power_values[i])return false;
    for(unsigned i=H7C_WORDS;i<1024;++i)if(p[i])return false;
    return hcc_crc32(static_cast<const uint8_t *>(bo.mapping())+HCC_RECORD_OFFSET,4096)==s.configuration.record_crc;
}

// Called outside the startup gate before native event-source construction.
// The actual completed configuration retains these exact source objects.
// No MMIO,grant callback,allocation or parameter-derived success occurs here.
bool ZornGen7HostGpuRegisters26::holdsCompletedIrqPrerequisite(IOService &gpu,
    ZornGen7InactiveOwner26 &parent,ZornGen7RegisterMaps26 &maps) const
{
    if(!storage_ || !normal())return false;auto &s=*storage_;
    if(IORecursiveLockHaveLock(&s.gate))return false;
    IORecursiveLockLock(&s.gate);
    const bool ready=s.attempted && s.ready && &s.gpu==&gpu && &s.parent==&parent && &s.maps==&maps &&
        !s.irq.halted() && !s.halted(s.hfi) && !s.domain.faulted();
    IORecursiveLockUnlock(&s.gate);return ready;
}

// Configuration metadata,not a capability query or hardware ownership grant.
// Called only by the real ring while its startup/issuer scope is held. No
// register access,callback,allocator,resource release or guessed chip value.
IOReturn ZornGen7HostGpuRegisters26::copyConfiguredDeviceInfo(NativeAdrenoAbiDeviceInfo &out) const
{
    if(!storage_ || !normal() || !IORecursiveLockHaveLock(&storage_->gate))return kIOReturnNotReady;
    const auto &s=*storage_;
    if(!s.ready || !s.configuration.record_ready || s.configuration.code!=H7C_OK ||
       s.configuration.completed!=H7C_OPS || !s.grantReturned || s.grantRaw ||
       s.irq.halted() || s.halted(s.hfi) || s.domain.faulted())return kIOReturnNotReady;
    OSSharedPtr<OSObject> chip(s.gpu.copyProperty("qcom,chipid"),OSNoRetain);
    auto *data=OSDynamicCast(OSData,chip.get());uint32_t chipId=0;
    if(!data || data->getLength()!=sizeof(chipId) || !data->getBytesNoCopy())return kIOReturnNotReady;
    memcpy(&chipId,data->getBytesNoCopy(),sizeof(chipId));if(!chipId)return kIOReturnUnsupported;
    constexpr uint32_t mode=4;
    if(!property(s.gpu,"qcom,ubwc-mode",&mode,sizeof(mode)))return kIOReturnUnsupported;
    auto configured=[&](const char *name,uint32_t &value)->bool {
        for(unsigned i=0;i<H7C_OPS;++i)if(!strcmp(h7c_ops[i].name,name)){
            const auto &op=h7c_ops[i];const auto &record=s.configuration.records[i];
            if(op.kind!=0 || !record.written || (record.valid&6u)!=6u ||
               ((record.after^record.expected)&op.verify))return false;
            // Use the exact requested logical value for unimplemented/readback
            // masked bits too. This reports configured GMEM extent,never claims
            // an unobserved low-bit readback or a physical capacity probe.
            value=record.expected;return true;
        }return false;
    };
    uint32_t minLo=0,minHi=0,maxLo=0,maxHi=0,trapLo=0,trapHi=0,rb=0,tp=0,gras=0;
    if(!configured("UCHE_GMEM_RANGE_MIN_LO",minLo) || !configured("UCHE_GMEM_RANGE_MIN_HI",minHi) ||
       !configured("UCHE_GMEM_RANGE_MAX_LO",maxLo) || !configured("UCHE_GMEM_RANGE_MAX_HI",maxHi) ||
       !configured("UCHE_TRAP_BASE_LO",trapLo) || !configured("UCHE_TRAP_BASE_HI",trapHi) ||
       !configured("RB_NC_MODE_CNTL",rb) || !configured("TPL1_NC_MODE_CNTL",tp) ||
       !configured("GRAS_NC_MODE_CNTL",gras))return kIOReturnNotReady;
    const uint64_t begin=(uint64_t(minHi)<<32)|minLo,end=(uint64_t(maxHi)<<32)|maxLo;
    if(end<begin || end-begin>=UINT32_MAX)return kIOReturnUnsupported;
    const uint32_t bank=((gras>>5)&15u)+13u;
    if(bank!=13u+((rb>>1)&3u)+(((rb>>10)&1u)<<2) ||
       bank!=13u+((tp>>1)&3u)+(((tp>>4)&1u)<<2) || !(rb&(1u<<11)))return kIOReturnNotReady;
    NativeAdrenoAbiDeviceInfo info{};info.chip_id=chipId;info.gmem_bytes=uint32_t(end-begin+1);
    info.gmem_base=begin;info.uche_trap_base=(uint64_t(trapHi)<<32)|trapLo;info.highest_bank_bit=bank;
    // Exact retained tu_knl_kgsl.cc UBWC4 mapping:6 and8-channel mode.
    // These are source configuration semantics,not another board's defaults.
    info.ubwc_version=mode;info.ubwc_swizzle=6;info.macrotile_mode=1;
    info.flags=NativeAdrenoDeviceClientIova; // actual existing explicit BoMap API only
    out=info;return kIOReturnSuccess;
}
