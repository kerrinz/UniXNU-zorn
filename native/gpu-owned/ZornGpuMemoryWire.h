/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_GPU_MEMORY_WIRE_H
#define ZORN_GPU_MEMORY_WIRE_H
#include "ZornGpuOwnedMemory.h"
#include "../display/ZornDisplayProgress.h"
namespace ZornGpuMemoryWire {
static_assert(sizeof(IOReturn)==4,"GPU wire requires exact32-bit IOReturn");
static constexpr unsigned Version=21,DisplayAt=1104,CrcAt=DisplayAt+31*8+4;
static constexpr uint32_t Magic=0x314d5047; // GPM1, not a firmware protocol
static constexpr uint32_t Pages[8]={19,27,19,37,1,1,16,18};
static inline uint32_t load32(const uint8_t *p){return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
static inline void store32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;++i)p[i]=uint8_t(v>>(8*i));}
static inline uint32_t crc(const uint8_t *b){uint32_t c=UINT32_MAX;
 for(unsigned i=0;i<4096;++i){c^=(i>=CrcAt && i<CrcAt+4)?0:b[i];for(unsigned bit=0;bit<8;++bit)c=(c>>1)^((c&1)?0xedb88320u:0);}
 return ~c;
}
/* Snapshot is immutable after release publication. Entire output untouched on
 * unrepresentable/error input. PA frame is32bits => exact44-bit aligned PA;
 * page count is8bits, checked, not silently truncated. Raw snapshots on a
 * rejected alias remain present even if described_mask has not accepted them.
 * Request sizes are fixed by public stock-SHA plan; no PA becomes an IOVA. */
static inline bool values(const ZornGpuMemoryReport &r,uint64_t out[16]){
 if((r.state!=ZGOM_CPU_PREPARED && r.state!=ZGOM_RETAINED_FAILURE) || r.phase<1 || r.phase>5 || r.index>8 ||
    r.failure_source>ZGOM_FAILURE_SNAPSHOT || r.output_policy_bits>63 || !r.epoch || r.epoch>UINT32_MAX ||
    r.plan_attempted>1 || r.plan_status>ZGP_CAPACITY || r.runtime_complete ||
    (r.attempted_mask|r.backed_mask|r.described_mask|r.quarantined_mask)>255 ||
    (r.backed_mask&~r.attempted_mask) || (r.described_mask&~r.backed_mask) ||
    (r.quarantined_mask&~r.backed_mask) || r.cleanup_status_unavailable_mask!=r.quarantined_mask ||
    (r.attempted_mask&(r.attempted_mask+1)))return false;
 if(!(r.output_policy_bits==32 || r.output_policy_bits==36 || r.output_policy_bits==40 ||
      r.output_policy_bits==42 || r.output_policy_bits==44 || r.output_policy_bits==48))return false;
 if(r.state==ZGOM_CPU_PREPARED && (r.failure_source || r.returned_status || r.attempted_mask!=255 ||
    r.backed_mask!=255 || r.described_mask!=255 || r.quarantined_mask || !r.plan_attempted || r.plan_status))return false;
 if(r.state==ZGOM_RETAINED_FAILURE && (!r.failure_source || !r.returned_status))return false;
 // All transported errors are exact or uniquely reconstructible. Refuse
 // a report with any additional raw error rather than silently dropping it.
 if(!r.plan_attempted && r.plan_status)return false;
 if(r.original_native_status!=(r.failure_source==ZGOM_FAILURE_NATIVE?r.returned_status:0) ||
    r.original_gate_status!=(r.failure_source==ZGOM_FAILURE_GATE?r.returned_status:0) ||
    r.original_snapshot_status!=((r.failure_source==ZGOM_FAILURE_SNAPSHOT ||
        (r.failure_source==ZGOM_FAILURE_GATE && r.phase==ZGOM_GATE_SNAPSHOT))?r.returned_status:0))return false;
 for(unsigned i=0;i<8;++i){
    const IOReturn expected=(r.attempted_mask&(1u<<i))?
        ((r.failure_source==ZGOM_FAILURE_NATIVE && r.index==i)?r.returned_status:kIOReturnSuccess):kIOReturnNotReady;
    if(r.allocation_status[i]!=expected)return false;
 }
 uint64_t v[16]={};v[0]=r.state|(r.phase<<4)|(r.index<<8)|(r.failure_source<<12)|
    (r.output_policy_bits<<16)|(r.plan_attempted<<22)|(r.plan_status<<23);
 v[1]=uint32_t(r.returned_status);v[2]=r.attempted_mask|(r.backed_mask<<8)|(r.described_mask<<16)|(r.quarantined_mask<<24);
 v[3]=r.epoch;unsigned retained=0,allocated=0;
 for(unsigned i=0;i<8;++i){
    if(r.backed_mask&(1u<<i))retained+=Pages[i]*4096;
    if((r.attempted_mask&(1u<<i)) && !(r.failure_source==ZGOM_FAILURE_NATIVE && r.index==i))allocated+=Pages[i]*4096;
    const auto &s=r.snapshots[i];const bool present=s.owner || s.cpu || s.physical || s.bytes || s.epoch || s.span_count ||
        s.runtime_complete || s.device_references || s.write_combined;
    if(!present){if(r.described_mask&(1u<<i))return false;continue;}
    if(!(r.backed_mask&(1u<<i)) || !s.owner || !s.cpu || !s.physical || (s.physical&4095) ||
       s.physical>>12>UINT32_MAX || s.bytes!=Pages[i]*4096 || (s.bytes>>12)>255 ||
       s.epoch!=r.epoch || s.span_count!=1 || s.runtime_complete || s.device_references || s.write_combined)return false;
    v[4+i]=s.physical>>12;v[12+i/4]|=(s.bytes>>12)<<((i%4)*8);
 }
 if(retained!=r.retained_bytes || allocated!=r.allocated_bytes)return false;
 v[14]=Magic;for(unsigned i=0;i<16;++i)out[i]=v[i];return true;
}
/* Canonical log remains D/v18. Caller holds original writer ownership and an
 * independent stable4096B wire copy. No input/output alias and no sampling or
 * allocation here. Reuses original16 high32 carrier helper; CRC covers all
 *4096 bytes, including text/footer/touch, with only its own high32 field zero. */
static inline bool encode(const uint8_t *source,const ZornGpuMemoryReport &r,uint8_t *wire){
 if(!source || !wire || uintptr_t(source)>UINTPTR_MAX-4095 || uintptr_t(wire)>UINTPTR_MAX-4095 ||
    (uintptr_t(source)<=uintptr_t(wire)?uintptr_t(wire)-uintptr_t(source)<4096:uintptr_t(source)-uintptr_t(wire)<4096))return false;
 const uintptr_t a=uintptr_t(&r),b=uintptr_t(wire);
 if(a>UINTPTR_MAX-(sizeof(r)-1) || (a<=b?b-a<sizeof(r):a-b<4096))return false;
 const char log[]="ZORNLOGD",gui[]="ZORNGUI1";
 for(unsigned i=0;i<8;++i)if(source[i]!=uint8_t(log[i]) || source[1024+i]!=uint8_t(gui[i]))return false;
 if(load32(source+1032)!=18 || load32(source+1036)!=3072)return false;
 uint64_t vals[16],display[32];if(!values(r,vals))return false;
 for(unsigned i=0;i<32;++i)display[i]=uint64_t(load32(source+DisplayAt+i*8))|(uint64_t(load32(source+DisplayAt+i*8+4))<<32);
 if(!ZornDisplayProgress::encode(display,vals))return false;
 for(unsigned i=0;i<4096;++i)wire[i]=source[i];
 for(unsigned i=0;i<32;++i){store32(wire+DisplayAt+i*8,uint32_t(display[i]));store32(wire+DisplayAt+i*8+4,uint32_t(display[i]>>32));}
 store32(wire+1032,Version);store32(wire+CrcAt,crc(wire));return true;
}
}
#endif
