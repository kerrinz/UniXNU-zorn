/* SPDX-License-Identifier: GPL-2.0-only */
#include "ZornGen7HostTables26.h"
#include "ZornGen7HostVoteData26.h"
#include "ZornGen7HwschedHfi26.h"
#include "ZornGen7DirectHfi26.h"
#include "ZornGen7HostBootSource26.inc"
#include "ZornGen7HostBandwidthArithmetic26.h"
#include "ZornGen7IccInputs26.h"
#include <IOKit/IOService.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSSharedPtr.h>
#include <IOKit/IOLib.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <string.h>
OSDefineMetaClassAndStructors(ZornGen7HostTables26,OSObject)
namespace {bool normal(){return preemption_enabled() && !ml_at_interrupt_context();}}
struct ZornGen7HostTables26::Storage {
    IORecursiveLock &gate;ZornGen7HostVote26::Gen791BoardVoteData board;
    ZornCommandDbFileEntry scratch[ZCDF_MAX_ENTRIES]{};
    ZornGen7HostVote26::CommandDbVoteInputs *inputs=nullptr;
    ZornGen7HostVote26::BcmBandwidthTables *tables=nullptr;
    uint8_t fdtDigest[32]{};uint32_t suffix=0;
    uint32_t perf[58]{},bw[159]{};
    ZornGen7HostVote26::BandwidthPreparation preparation{};
    bool boardMatched=false,prepared=false,attempted=false;
    bool directPerformanceAccepted=false,directBandwidthAttempted=false;
    bool freshPowerReady=false,clockAttempted=false,clockReturned=false,rdpmMxSourceAbsent=false;
    uint32_t defaultLevel=0,activeLevel=0,previousLevel=0,thermalMax=0,thermalFloor=0,maxLevel=0,minLevel=0;
    IOReturn clockRaw=kIOReturnNotReady;
    bool abQueryReturned=false,abSupported=false,bwAttempted=false,bwReturned=false,bwReady=false;
    IOReturn abQueryRaw=kIOReturnNotReady,bwRaw=kIOReturnNotReady,hlosAverageRaw=kIOReturnNotReady;
    bool axiOn=false,hlosAverageReturned=false;uint32_t curDcvsBuslevel=0,curBuslevel=0,curAb=0,requestedAb=0,encodedBw=0;
    ZornGen7IccInputs26 *boundIcc=nullptr;
    IOReturn profileRaw=kIOReturnNotReady;bool profileReturned=false;
    explicit Storage(IORecursiveLock &g):gate(g){}
    static void *operator new(size_t,void *p)noexcept{return p;}
};
IOReturn ZornGen7HostTables26::createAndPrepare(IORecursiveLock &gate,OSObject &boardOwner,
    const ZornGen7Rpmh::ActualXoCommandDbSnapshot &snapshot,OSObject &snapshotOwner,
    const ZornGen7HostTableSelection26 &selection,ZornGen7HostTables26 *&out)
{return createAndPrepareInput(gate,boardOwner,&snapshot,nullptr,snapshotOwner,selection,out);}
IOReturn ZornGen7HostTables26::createAndPrepareResources(IORecursiveLock &gate,OSObject &boardOwner,
    ZornGen7Rpmh::NativeCommandDbResourceReader &reader,OSObject &sourceOwner,
    const ZornGen7HostTableSelection26 &selection,ZornGen7HostTables26 *&out)
{return createAndPrepareInput(gate,boardOwner,nullptr,&reader,sourceOwner,selection,out);}
IOReturn ZornGen7HostTables26::createAndPrepareInput(IORecursiveLock &gate,OSObject &boardOwner,
    const ZornGen7Rpmh::ActualXoCommandDbSnapshot *snapshot,ZornGen7Rpmh::NativeCommandDbResourceReader *reader,
    OSObject &snapshotOwner,const ZornGen7HostTableSelection26 &selection,ZornGen7HostTables26 *&out)
{
    using namespace ZornGen7HostVote26;
    if(out || !normal() || !IORecursiveLockHaveLock(&gate) || bool(snapshot)==bool(reader) ||
       (snapshot && (!snapshot->bytes || !snapshot->byte_count)))return kIOReturnNotReady;
    auto *p=new ZornGen7HostTables26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;boardOwner.retain();snapshotOwner.retain();selection.actualSelectionOwner.retain();
    void *memory=IOMallocZero(sizeof(Storage));if(!memory)return kIOReturnNoMemory;
    p->storage_=new(memory)Storage(gate);auto &s=*p->storage_;
    memcpy(s.fdtDigest,selection.actualStockFdtDigest,32);s.suffix=selection.actualSelectedSuffix;
    s.boardMatched=s.board.prepareFromStockFdt(s.fdtDigest,s.suffix);
    if(!s.boardMatched)return kIOReturnUnsupported;
    memory=IOMallocZero(sizeof(CommandDbVoteInputs));if(!memory)return kIOReturnNoMemory;
    s.inputs=reader ? ::new(memory)CommandDbVoteInputs(*reader,s.board.config_) :
        ::new(memory)CommandDbVoteInputs(snapshot->bytes,snapshot->byte_count,
        snapshot->independently_expected_version,s.scratch,ZCDF_MAX_ENTRIES,s.board.config_);
    memory=IOMallocZero(sizeof(BcmBandwidthTables));if(!memory)return kIOReturnNoMemory;
    s.tables=::new(memory)BcmBandwidthTables(s.board.power_,*s.inputs);
    s.preparation=s.tables->prepare();
    if(s.preparation.assessment!=BandwidthAssessment::SourceBandwidthPrepared)return kIOReturnNotReady;
    const auto &dcvs=s.tables->arc_.table_;const auto &ddr=s.tables->ddr_view_;const auto &cnoc=s.tables->cnoc_view_;
    // Exact legacy host PERF/BW wire capacities. No modern-table fallback,
    // interpolated values,host OPPs or source-missing zero-filled active row.
    if(!dcvs.gpu_level_num || dcvs.gpu_level_num>16 || !dcvs.gmu_level_num || dcvs.gmu_level_num>4 ||
       ddr.num_levels>16 || ddr.num_cmds>8 || cnoc.num_levels>2 || cnoc.num_cmds>6 ||
       s.tables->cnoc_source_!=CnocSource::ActualPresent)return kIOReturnUnsupported;
    s.perf[0]=dcvs.gpu_level_num;s.perf[1]=dcvs.gmu_level_num;
    memcpy(s.perf+2,dcvs.gx_votes,size_t(dcvs.gpu_level_num)*sizeof(GxOpp));
    memcpy(s.perf+50,dcvs.cx_votes,size_t(dcvs.gmu_level_num)*sizeof(CxOpp));
    // Same StartupTables fixed160word layout with its header removed.
    s.bw[0]=ddr.num_levels;s.bw[1]=cnoc.num_cmds;s.bw[2]=ddr.num_cmds;s.bw[3]=cnoc.wait_bitmask;s.bw[4]=ddr.wait_bitmask;
    for(uint32_t j=0;j<cnoc.num_cmds;++j)s.bw[5+j]=cnoc.addrs[j];
    for(uint32_t i=0;i<cnoc.num_levels;++i)for(uint32_t j=0;j<cnoc.num_cmds;++j)s.bw[11+size_t(i)*6u+j]=cnoc.cmds[i][j];
    for(uint32_t j=0;j<ddr.num_cmds;++j)s.bw[23+j]=ddr.addrs[j];
    for(uint32_t i=0;i<ddr.num_levels;++i)for(uint32_t j=0;j<ddr.num_cmds;++j)s.bw[31+size_t(i)*8u+j]=ddr.cmds[i][j];
    // Own fresh CPU power state follows the actual selected K80 node and
    // original adreno_of_get_initial_pwrlevels/kgsl_pwrctrl_init. No live
    // Android state,other client,thermal vote or arbitrary frequency is read.
    // Only this exact source digest supplies the optional-resource absence.
    if(!memcmp(s.fdtDigest,ZornGen7HostBootSource26::fdtDigest,32)){
        for(const auto &row:ZornGen7HostBootSource26::rows)if(row.suffix==s.suffix){
            const uint32_t count=s.board.power_.num_pwrlevels;
            if(!count)return kIOReturnUnsupported;
            uint32_t level=row.level;
            if((level&0x80000000u) || level>=count)level=1;
            if(level>=count)return kIOReturnUnsupported;
            s.defaultLevel=level;s.activeLevel=level;s.maxLevel=0;
            uint32_t minimum=row.hasMinimum?row.minimum:count-1u;
            if((minimum&0x80000000u) || minimum>=count || minimum<level)minimum=count-1u;
            s.minLevel=minimum;s.thermalMax=0;s.thermalFloor=count-1u;s.freshPowerReady=true;break;
        }
    }
    s.prepared=true;return kIOReturnSuccess; // CPU data prepared,not applied clock/vote or HFI response.
}
IOReturn ZornGen7HostTables26::sendDirectPerformance(ZornGen7DirectHfi26 &transport,
    uint32_t version,uint32_t (&record)[4])
{
    if(!storage_ || !normal())return kIOReturnNotReady;
    auto &s=*storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || !s.prepared || s.attempted ||
       !transport.healthy())return kIOReturnNotReady;
    s.attempted=true;

    // gen7_hfi_send_gpu_perf_table uses the typed table at HFI 2.6.1.
    // The checked K80 vote owner already built the source GX and CX rows.
    uint32_t payload[58]{};
    const uint32_t *data=s.perf;
    size_t words=sizeof(s.perf)/sizeof(s.perf[0]);
    unsigned id=4; // H2F_MSG_PERF_TBL.
    if(version>=0x20060001u){
        id=15; // H2F_MSG_TABLE.
        const uint32_t gpu=s.perf[0], gmu=s.perf[1];
        if(!gpu || gpu>16 || !gmu || gmu>4)return kIOReturnBadArgument;
        payload[0]=0; // version
        payload[1]=1; // HFI_TABLE_GPU_PERF
        payload[2]=gpu;
        payload[3]=3;
        memcpy(payload+4,s.perf+2,size_t(gpu)*3*sizeof(uint32_t));
        words=4+size_t(gpu)*3;
        payload[words++]=gmu;
        payload[words++]=2;
        memcpy(payload+words,s.perf+50,size_t(gmu)*2*sizeof(uint32_t));
        words+=size_t(gmu)*2;
        data=payload;
    }
    const auto reply=transport.exchange(id,data,words);
    record[0]=(id<<24) | (uint32_t(words+1)<<16) |
        (uint32_t(reply.outcome)<<8) | reply.words;
    record[1]=reply.packet[1];
    record[2]=reply.packet[2];
    record[3]=reply.packet[3];
    s.directPerformanceAccepted=reply.outcome==ZornGen7DirectHfi26::Outcome::ReturnedAck &&
        reply.words>=3 && reply.packet[2]==0 && transport.healthy();
    return s.directPerformanceAccepted?kIOReturnSuccess:kIOReturnNotReady;
}

IOReturn ZornGen7HostTables26::sendDirectBandwidth(ZornGen7DirectHfi26 &transport,uint32_t (&record)[4])
{
    if(!storage_ || !normal())return kIOReturnNotReady;
    auto &s=*storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || !s.prepared || !s.directPerformanceAccepted ||
       s.directBandwidthAttempted || !transport.healthy())return kIOReturnNotReady;
    s.directBandwidthAttempted=true;

    constexpr unsigned id=3; // H2F_MSG_BW_VOTE_TBL with the full source payload.
    const auto reply=transport.exchange(id,s.bw,sizeof(s.bw)/sizeof(s.bw[0]));
    record[0]=(id<<24) | (160u<<16) | (uint32_t(reply.outcome)<<8) | reply.words;
    record[1]=reply.packet[1];
    record[2]=reply.packet[2];
    record[3]=reply.packet[3];
    return reply.outcome==ZornGen7DirectHfi26::Outcome::ReturnedAck &&
        reply.words>=3 && reply.packet[2]==0 && transport.healthy() ?
        kIOReturnSuccess:kIOReturnNotReady;
}

IOReturn ZornGen7HostTables26::runHostProfile(ZornGen7HwschedHfi26 &transport)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || !s.prepared || s.attempted)return kIOReturnNotReady;
    s.attempted=true;
    // Actual transport forbids workloop dispatch/wait inversion. Do not retain
    // the board/domain gate across its inline request/IRQ/debug service loop.
    IORecursiveLockUnlock(&s.gate);auto raw=transport.runHostProfile(*this,s.perf,s.bw);
    if(raw==kIOReturnSuccess){
        bool actualSupported=false;const auto queried=transport.queryHostAbSupport(*this,actualSupported);
        IORecursiveLockLock(&s.gate);s.abQueryRaw=queried;s.abQueryReturned=true;
        if(queried==kIOReturnSuccess)s.abSupported=actualSupported;
        IORecursiveLockUnlock(&s.gate);raw=queried;
    }
    IORecursiveLockLock(&s.gate);s.profileRaw=raw;s.profileReturned=true;return raw;
}
void ZornGen7HostTables26::free(){if(pinned_)return;OSObject::free();}

IOReturn ZornGen7HostTables26::requestDefaultClock(ZornGen7HwschedHfi26 &transport,IOService &gpu)
{
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || !s.prepared || !s.freshPowerReady || s.clockAttempted ||
       !s.profileReturned || s.profileRaw!=kIOReturnSuccess)return kIOReturnNotReady;
    s.clockAttempted=true;gpu.retain();
    OSSharedPtr<OSObject> namesObject(gpu.copyProperty("reg-names"),OSNoRetain);
    auto *names=OSDynamicCast(OSData,namesObject.get());
    // Source absence must agree with the actual retained native resource
    // declaration. Missing property/map failure never means optional absent.
    constexpr auto &nativeNames=ZornGen7HostBootSource26::nativeRegNames;
    if(!names || !names->getBytesNoCopy() || names->getLength()!=sizeof(nativeNames) ||
       memcmp(names->getBytesNoCopy(),nativeNames,sizeof(nativeNames)) ||
       !ZornGen7HostBootSource26::sourceRdpmMxAbsent)return kIOReturnUnsupported;
    const uint32_t requested=s.defaultLevel,old=s.activeLevel;
    uint32_t upper=s.thermalMax>s.maxLevel?s.thermalMax:s.maxLevel;
    uint32_t lower=s.thermalFloor<s.minLevel?s.thermalFloor:s.minLevel;
    upper=upper<s.thermalFloor?upper:s.thermalFloor;lower=lower>s.thermalMax?lower:s.thermalMax;
    const uint32_t adjusted=requested<upper?upper:(requested>lower?lower:requested);
    const uint32_t count=s.tables->arc_.table_.gpu_level_num;
    if(count!=s.board.power_.num_pwrlevels+1u || adjusted>=count-1u)return kIOReturnUnsupported;
    // Original publication order remains before the request,including failure.
    s.activeLevel=adjusted;s.previousLevel=old;
    IORecursiveLockUnlock(&s.gate);
    const auto raw=transport.requestHostClock(*this,adjusted);
    IORecursiveLockLock(&s.gate);s.clockRaw=raw;s.clockReturned=true;
    if(raw!=kIOReturnSuccess)return raw;
    s.rdpmMxSourceAbsent=true;return kIOReturnSuccess;
    // Direct GMU clock ACK plus known optional RDPM absence only. No CPU-QoS
    // hint exists in this direct clock source;AXI/GX/OOB/CP are not completed.
}

IOReturn ZornGen7HostTables26::requestDefaultBandwidth(ZornGen7HwschedHfi26 &transport,ZornGen7IccInputs26 &icc)
{
    using namespace ZornGen7HostBandwidth26;
    if(!storage_ || !normal())return kIOReturnNotReady;auto &s=*storage_;
    if(!IORecursiveLockHaveLock(&s.gate) || !s.prepared || !s.freshPowerReady || !s.clockReturned ||
       s.clockRaw!=kIOReturnSuccess || !s.rdpmMxSourceAbsent || !s.abQueryReturned ||
       s.abQueryRaw!=kIOReturnSuccess || s.bwAttempted)return kIOReturnNotReady;
    s.bwAttempted=true;icc.retain();s.boundIcc=&icc;
    const auto &power=s.board.power_;const auto &ddr=s.board.config_.ddr;
    if(!sourceAcvVote || !ddr.levels_kbps || !ddr.num_levels || ddr.num_levels>16 ||
       ddr.level_bytes<size_t(ddr.num_levels)*4u || s.activeLevel>=power.num_pwrlevels)return kIOReturnUnsupported;
    // Fresh private source state has ctrl_flags0,AXI-off,bus_mod0 and no RT
    // hint or AB overrides. It is not copied from Android or another client.
    s.axiOn=true;
    const uint32_t cur=power.pwrlevels[s.activeLevel].bus_freq;
    uint32_t bus=cur<power.pwrlevels[0].bus_max?cur:power.pwrlevels[0].bus_max;if(bus<1)bus=1;
    if(bus>=ddr.num_levels || ddr.levels_kbps[bus]>UINT32_MAX/25u)return kIOReturnUnsupported;
    s.curDcvsBuslevel=bus;const uint32_t average=freshAverageMbps(ddr.levels_kbps[bus]);s.requestedAb=average;
    const uint32_t busRequest=bus==s.curBuslevel?0xffu:bus;
    const uint32_t abRequest=(average==s.curAb || !average)?0xffffu:average;
    uint32_t encodedAb=0;if(!encodeAb(s.abSupported,abRequest,ddr.levels_kbps[ddr.num_levels-1u],encodedAb))return kIOReturnUnsupported;
    s.encodedBw=busRequest|encodedAb;
    if(abRequest==0xffffu && busRequest==0xffu)return kIOReturnNotReady; // Fresh source cannot silently become an applied vote.
    IORecursiveLockUnlock(&s.gate);const auto raw=transport.requestHostBandwidth(*this,s.encodedBw);IORecursiveLockLock(&s.gate);
    s.bwRaw=raw;s.bwReturned=true;if(raw!=kIOReturnSuccess)return raw;
    if(busRequest!=0xffu)s.curBuslevel=busRequest;
    if(abRequest!=0xffffu){
        if(!s.abSupported){
            s.hlosAverageRaw=icc.applyHostAverageMbps(abRequest);s.hlosAverageReturned=true;
            if(s.hlosAverageRaw!=kIOReturnSuccess)return s.hlosAverageRaw;
        }
        s.curAb=abRequest;
    }
    s.bwReady=true;return kIOReturnSuccess;
    // Actual request/ICC source completion only,not measured fabric bandwidth,
    // GX OOB,CP/ring/fence. Failure preserves AXI/publication and all resources.
}
