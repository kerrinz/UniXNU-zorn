/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuStartupPlan.h"
#include <string.h>
static int span(const void *p,size_t n,size_t a)
{return p && n && !((uintptr_t)p%a) && (uintptr_t)p<=UINTPTR_MAX-(n-1);}
static int overlap(const void *a,size_t na,const void *b,size_t nb)
{return (uintptr_t)a<=(uintptr_t)b?(uintptr_t)b-(uintptr_t)a<na:(uintptr_t)a-(uintptr_t)b<nb;}
int ZGPlanStartupStep(uint32_t stage,const ZGVersion *version,
    const ZGPreemptPolicy *policy,ZGStartupStep *out)
{
    if(stage>=ZG_STAGE_COUNT || !span(version,sizeof(*version),_Alignof(ZGVersion)) ||
       !span(out,sizeof(*out),_Alignof(ZGStartupStep)) || overlap(version,sizeof(*version),out,sizeof(*out)))return ZG_INVALID;
    if(policy && (!span(policy,sizeof(*policy),_Alignof(ZGPreemptPolicy)) ||
       overlap(policy,sizeof(*policy),out,sizeof(*out)) ||
       overlap(policy,sizeof(*policy),version,sizeof(*version))))return ZG_INVALID;
    if(policy && (policy->supplied>1 || policy->enable>1 || (policy->data&~15u)))return ZG_INVALID;
    ZGStartupStep p={0};p.stage=stage;p.version=*version;
    const uint32_t minor=(version->raw>>16)&4095;
    if(version->source!=ZG_VERSION_LIVE_ASSERTED || !version->epoch)p.missing|=ZG_NEED_LIVE_VERSION;
    if((version->raw>>28)!=2)p.missing|=ZG_NEED_VERSION_SUPPORT;
    switch(stage){
    case ZG_PERF_TABLE:
        if(!p.missing)p.id=version->raw>=UINT32_C(0x20060001)?15:4;
        p.missing|=ZG_NEED_BOARD_VOTES;p.ack_contract=ZG_ACK_ZERO_WORD2;break;
    case ZG_BW_TABLE:p.id=3;p.missing|=ZG_NEED_BOARD_VOTES;p.ack_contract=ZG_ACK_ZERO_WORD2;break;
    case ZG_CORE_START:p.id=14;p.payload_words=1;p.ack_contract=ZG_ACK_ZERO_WORD2;break;
    case ZG_CONTEXT_QUERY:
        p.id=12;p.payload_words=2;p.payload[0]=121;p.query=1;
        if(minor<3)p.missing|=ZG_NEED_NEWER_MINOR;break;
    case ZG_START:p.id=10;p.ack_contract=ZG_ACK_SENTINEL;break;
    default:
        p.id=11;p.payload_words=3;p.payload[1]=1;
        if(stage==ZG_HWSCHED)p.payload[0]=1;
        else if(stage==ZG_KPROF)p.payload[0]=16;
        else if(stage==ZG_AQE)p.payload[0]=29;
        else {
            p.payload[0]=2;
            if(!policy || !policy->supplied)p.missing|=ZG_NEED_PREEMPT_POLICY;
            else {p.payload[1]=policy->enable;p.payload[2]=policy->data;}
        }
    }
    if(!p.ack_contract)p.ack_contract=minor<=4?ZG_ACK_ZERO_WORD2:ZG_ACK_V5;
    if(p.missing&(ZG_NEED_LIVE_VERSION|ZG_NEED_VERSION_SUPPORT))p.ack_contract=ZG_ACK_UNKNOWN;
    p.packet_ready=!p.missing;p.runtime_complete=0;memcpy(out,&p,sizeof(p));return ZG_OK;
}
int ZGAssessStartupAck(const ZGStartupStep *step,uint32_t expected,
    const uint32_t *raw,size_t count,ZGAckAssessment *out)
{
    if(!span(step,sizeof(*step),_Alignof(ZGStartupStep)) || count<1 || count>19 ||
       !span(raw,count*4,_Alignof(uint32_t)) || !span(out,sizeof(*out),_Alignof(ZGAckAssessment)) ||
       overlap(raw,count*4,out,sizeof(*out)) || overlap(step,sizeof(*step),out,sizeof(*out)) ||
       overlap(step,sizeof(*step),raw,count*4))return ZG_INVALID;
    ZGAckAssessment a={0};a.count=(uint32_t)count;
    for(unsigned i=0;i<count;++i)a.raw[i]=raw[i];
    a.assessment=ZG_ACK_CONTRACT_UNAVAILABLE;
    /* Reconstruct the candidate without trusting a caller-mutated ACK contract. */
    ZGStartupStep actual;ZGPreemptPolicy policy={1,step->payload[1],step->payload[2]};
    if(ZGPlanStartupStep(step->stage,&step->version,step->stage==ZG_PREEMPT?&policy:0,&actual)!=ZG_OK ||
       !step->packet_ready || actual.stage!=step->stage || actual.id!=step->id ||
       actual.payload_words!=step->payload_words || actual.ack_contract!=step->ack_contract ||
       actual.query!=step->query || actual.missing!=step->missing ||
       actual.packet_ready!=step->packet_ready || actual.runtime_complete!=step->runtime_complete ||
       actual.payload[0]!=step->payload[0] || actual.payload[1]!=step->payload[1] ||
       actual.payload[2]!=step->payload[2])goto done;
    if((expected&255)!=step->id || ((expected>>8)&255)!=step->payload_words+1 ||
       (expected&UINT32_C(0x70000))) {a.assessment=ZG_ACK_MISMATCH;goto done;}
    if(count<3 || ((raw[0]>>8)&255)!=count || ((raw[0]>>16)&15)!=1){a.assessment=ZG_ACK_MALFORMED;goto done;}
    if((raw[1]&~(UINT32_C(1)<<19))!=(expected&~(UINT32_C(1)<<19))){a.assessment=ZG_ACK_MISMATCH;goto done;}
    a.value=raw[2];
    if(count>=4){a.status_present=1;a.status=raw[3];}
    if(step->ack_contract==ZG_ACK_ZERO_WORD2)a.assessment=raw[2]?ZG_ACK_REJECTED:ZG_ACK_MATCHED_ZERO;
    else if(step->ack_contract==ZG_ACK_SENTINEL)a.assessment=raw[2]==UINT32_MAX?ZG_ACK_REJECTED:ZG_ACK_MATCHED_SENTINEL;
    else {
        if(count<4){a.assessment=ZG_ACK_MALFORMED;goto done;}
        if(raw[3]==8)a.assessment=ZG_ACK_NO_ENTRY;
        else if(raw[3]==6)a.assessment=ZG_ACK_TIMEOUT;
        else if(raw[3])a.assessment=ZG_ACK_REJECTED;
        else if(raw[2]&UINT32_C(0x80000000))a.assessment=ZG_ACK_REJECTED;
        else if(step->query){a.assessment=ZG_ACK_MATCHED_VALUE;a.has_value=1;}
        else a.assessment=raw[2]?ZG_ACK_REJECTED:ZG_ACK_MATCHED_ZERO;
    }
done:
    memcpy(out,&a,sizeof(a));return ZG_OK;
}
int ZGPlanMemAlloc(const uint32_t *raw,size_t count,ZGMemRequirement *out)
{
    if(count<1 || count>11 || !span(raw,count*4,_Alignof(uint32_t)) ||
       !span(out,sizeof(*out),_Alignof(ZGMemRequirement)) || overlap(raw,count*4,out,sizeof(*out)))return ZG_INVALID;
    ZGMemRequirement p={0};p.raw_count=(uint32_t)count;
    for(unsigned i=0;i<count;++i)p.raw[i]=raw[i];
    if((raw[0]&255)!=20 || ((raw[0]>>16)&15)!=0 || ((raw[0]>>8)&255)!=count)p.issues|=ZG_MEM_WIRE;
    if(count<2){p.issues|=ZG_MEM_LENGTH;goto done;}
    p.version=raw[1];
    if(p.version>1){p.issues|=ZG_MEM_VERSION;goto done;}
    if(count!=(p.version?11u:10u)){p.issues|=ZG_MEM_LENGTH;goto done;}
    if(p.issues)goto done;
    p.decoded=1;p.gpu_addr=(uint64_t)raw[2]|((uint64_t)raw[3]<<32);
    p.flags=raw[4];p.kind=raw[5];p.host_handle=raw[6];p.gmu_handle=raw[7];
    p.gmu_addr=raw[8];p.size=raw[9];p.align=p.version?raw[10]:0;
    if(p.flags&~UINT32_C(0x13ff))p.issues|=ZG_MEM_FLAGS;
    if(p.kind>=26)p.issues|=ZG_MEM_KIND;
    if(!p.size)p.issues|=ZG_MEM_SIZE;
    const unsigned va=p.align&255,sz=(p.align>>8)&255;
    if(p.align&UINT32_C(0xffff0000) || va>31 || sz>31)p.issues|=ZG_MEM_ALIGNMENT;
    else {
        p.va_alignment=UINT32_C(1)<<(va>12?va:12);
        p.size_alignment=UINT32_C(1)<<(sz>12?sz:12);
        p.rounded_size=((uint64_t)p.size+p.size_alignment-1)&~((uint64_t)p.size_alignment-1);
        if(p.rounded_size>UINT32_MAX ||
           (p.gmu_addr && ((p.gmu_addr&(p.va_alignment-1)) || (uint64_t)p.gmu_addr+p.rounded_size>UINT64_C(0x100000000))) ||
           (p.gpu_addr && p.gpu_addr>UINT64_MAX-(p.rounded_size?p.rounded_size-1:0)))p.issues|=ZG_MEM_RANGE;
    }
    if(!(p.flags&1) && p.kind!=23){
        p.path=p.kind==19?ZG_PATH_IPC_CORE:ZG_PATH_GMU_RAM;p.requirements|=ZG_REQUIRE_GMU_MAP;
    } else {
        p.path=p.kind==23?ZG_PATH_HW_FENCE:p.kind==22?ZG_PATH_MEMSTORE:ZG_PATH_GPU_GLOBAL;
        p.requirements|=ZG_REQUIRE_GPU_MAP;
        if(p.flags&8)p.requirements|=ZG_REQUIRE_GMU_MAP;
    }
    if(p.path==ZG_PATH_HW_FENCE || p.path==ZG_PATH_MEMSTORE)p.requirements|=ZG_REQUIRE_PREALLOCATED;
    if(p.kind==11 || p.kind==12 || p.kind==13 || p.kind==19 || p.kind==20){
        p.issues|=ZG_MEM_MMIO_REVIEW;p.requirements|=ZG_REQUIRE_FIXED_RESOURCE;
    }
    if(p.flags&4096)p.requirements|=ZG_REQUIRE_SECURE;
    if(p.flags&256)p.requirements|=ZG_REQUIRE_HOST_ACCESS;
    if(p.flags&512)p.requirements|=ZG_REQUIRE_HOST_INIT;
    if(p.requirements&ZG_REQUIRE_GMU_MAP){
        p.gmu_cacheable=!!(p.flags&128);
        p.gmu_access=p.path==ZG_PATH_GMU_RAM?ZG_ACCESS_READ|ZG_ACCESS_WRITE|ZG_ACCESS_PRIV:
            ZG_ACCESS_READ|((p.flags&32)?ZG_ACCESS_WRITE:0)|((p.flags&16)?ZG_ACCESS_PRIV:0);
    }
    if(p.requirements&ZG_REQUIRE_GPU_MAP)
        p.gpu_access=ZG_ACCESS_READ|((p.flags&4)?ZG_ACCESS_WRITE:0)|((p.flags&2)?ZG_ACCESS_PRIV:0);
    p.format_available=!p.issues;
done:
    p.runtime_complete=0;memcpy(out,&p,sizeof(p));return ZG_OK;
}
