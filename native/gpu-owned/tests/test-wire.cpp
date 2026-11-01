#include "ZornGpuMemoryWire.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <vector>
using namespace ZornGpuMemoryWire;
static uint8_t src[4096],wire[4096],before[4096];
static ZornGpuMemoryReport prepared(){
 ZornGpuMemoryReport r{};r.state=ZGOM_CPU_PREPARED;r.phase=5;r.index=8;r.output_policy_bits=40;r.epoch=1;
 r.plan_attempted=1;r.attempted_mask=r.backed_mask=r.described_mask=255;r.allocated_bytes=r.retained_bytes=565248;
 for(unsigned i=0;i<8;++i){auto &s=r.snapshots[i];s.owner=reinterpret_cast<const NativeAdrenoMemory *>(uintptr_t(0x1000+i*0x100));
 s.cpu=reinterpret_cast<void *>(uintptr_t(0x100000+i*0x100000));s.physical=0x30000000+i*0x100000;s.bytes=Pages[i]*4096;s.epoch=1;s.span_count=1;}
 return r;
}
static void refuse(const ZornGpuMemoryReport &r){memset(wire,0x69,sizeof(wire));memcpy(before,wire,4096);auto original=std::vector<uint8_t>(src,src+4096);
 assert(!encode(src,r,wire));assert(!memcmp(wire,before,4096));assert(!memcmp(src,original.data(),4096));}
static void save(const char *root,unsigned i){char p[4096];snprintf(p,sizeof(p),"%s/wire-%u.bin",root,i);std::ofstream f(p,std::ios::binary);f.write((char*)wire,4096);}
int main(int argc,char **argv){assert(argc==2);
 for(unsigned i=0;i<4096;++i)src[i]=uint8_t(i*17+3);
 memcpy(src,"ZORNLOGD",8);memcpy(src+1024,"ZORNGUI1",8);store32(src+1032,18);store32(src+1036,3072);
 for(unsigned slot:ZornDisplayProgress::Slots)store32(src+DisplayAt+slot*8+4,0);
 {char p[4096];snprintf(p,sizeof(p),"%s/source.bin",argv[1]);std::ofstream f(p,std::ios::binary);f.write((char*)src,4096);}
 unsigned count=0;auto r=prepared();auto keep=r;assert(encode(src,r,wire));assert(!memcmp(&r,&keep,sizeof(r)));save(argv[1],count++);
 // Every representable full-width PA and epoch boundary is checked, not truncated.
 r=prepared();r.epoch=UINT32_MAX;for(auto &s:r.snapshots)s.epoch=r.epoch;r.snapshots[0].physical=uint64_t(UINT32_MAX)<<12;
 assert(encode(src,r,wire));save(argv[1],count++);
 // Each native failure preserves its exact32-bit error and all not-attempted statuses.
 for(unsigned i=0;i<8;++i){r={};r.state=3;r.phase=2;r.index=i;r.failure_source=2;r.output_policy_bits=40;r.epoch=1;r.plan_attempted=1;
 r.attempted_mask=(1u<<(i+1))-1;r.backed_mask=r.described_mask=(1u<<i)-1;r.returned_status=r.original_native_status=kIOReturnNoMemory;
 for(unsigned j=0;j<8;++j){r.allocation_status[j]=j<i?kIOReturnSuccess:j==i?r.returned_status:kIOReturnNotReady;
 if(j<i){r.snapshots[j]=prepared().snapshots[j];r.allocated_bytes+=Pages[j]*4096;r.retained_bytes+=Pages[j]*4096;}}
 assert(encode(src,r,wire));save(argv[1],count++);}
 r={};r.state=3;r.phase=1;r.failure_source=3;r.output_policy_bits=40;r.epoch=1;r.returned_status=r.original_gate_status=kIOReturnNotReady;
 for(auto &s:r.allocation_status)s=kIOReturnNotReady;assert(encode(src,r,wire));save(argv[1],count++);
 unsigned rejected=0;
 for(unsigned i=0;i<16;++i){r=prepared();store32(src+DisplayAt+ZornDisplayProgress::Slots[i]*8+4,1);refuse(r);store32(src+DisplayAt+ZornDisplayProgress::Slots[i]*8+4,0);++rejected;}
 for(unsigned i=0;i<8;++i){r=prepared();r.snapshots[i].physical=uint64_t(1)<<44;refuse(r);++rejected;r=prepared();r.snapshots[i].bytes+=4096;refuse(r);++rejected;}
 r=prepared();r.epoch=uint64_t(1)<<32;refuse(r);++rejected;
 r=prepared();r.original_native_status=kIOReturnIOError;refuse(r);++rejected;
 r=prepared();r.allocation_status[0]=kIOReturnNotReady;refuse(r);++rejected;
 r=prepared();r.retained_bytes=1;refuse(r);++rejected;
 r=prepared();r.allocated_bytes=1;refuse(r);++rejected;
 r=prepared();r.output_policy_bits=41;refuse(r);++rejected;
 r=prepared();r.runtime_complete=1;refuse(r);++rejected;
 r={};r.state=3;r.phase=1;r.failure_source=3;r.output_policy_bits=40;r.epoch=1;r.returned_status=r.original_gate_status=kIOReturnNotReady;
 for(auto &s:r.allocation_status)s=kIOReturnNotReady;r.snapshots[0].device_references=1;refuse(r);++rejected;
 r=prepared();auto copy=std::vector<uint8_t>(src,src+4096);assert(!encode(src,r,src));assert(!memcmp(src,copy.data(),4096));
 alignas(ZornGpuMemoryReport) uint8_t alias[sizeof(r)+4096]{};auto *a=new(alias) ZornGpuMemoryReport(prepared());
 assert(!encode(src,*a,alias));assert(!memcmp(a,&r,sizeof(r)));
 printf("{\"wire_examples\":%u,\"fallback_controls\":%u,\"alias_controls\":2}\n",count,rejected);
}
