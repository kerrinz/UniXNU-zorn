/* SPDX-License-Identifier: MIT */
#include "ZornGpuFirmwarePlan.h"
#include "NativeAdrenoSha256.h"
#include <string.h>

static const uint32_t zgp_sizes[4]={78588,85300,33176,12088};
static const uint8_t zgp_sha[4][32]={
 {0x96,0x85,0xf6,0x2c,0x42,0x54,0x3b,0xef,0xca,0xee,0x68,0xd2,0x53,0x55,0xe1,0x6b,0xf5,0x5c,0xdb,0x0d,0x57,0x3b,0xdd,0xcc,0x9f,0x66,0x33,0xf5,0x9e,0xec,0x3f,0x72},
 {0x8e,0x2c,0x5c,0xe7,0x41,0x40,0xde,0x7e,0x16,0x1f,0x14,0x65,0x4b,0x44,0xde,0x99,0x98,0x55,0xbc,0xe0,0x1b,0x69,0x0f,0xdd,0x18,0xc3,0x35,0x8a,0x73,0x49,0x8c,0xd1},
 {0x25,0x23,0x7c,0x16,0x1d,0x72,0x7b,0x8e,0xa9,0x2b,0x4b,0xeb,0x83,0x7a,0x31,0x65,0x1b,0x44,0xea,0x78,0xbf,0xc3,0x4d,0x95,0x67,0x2a,0xf8,0xf3,0x46,0xa4,0x58,0x25},
 {0x89,0x0f,0x7e,0x9d,0xa0,0x07,0x89,0x0a,0x40,0x80,0x4d,0x31,0x10,0x16,0x9c,0xcc,0x88,0x7e,0x8a,0x03,0xbd,0xf2,0x9e,0x8b,0x7b,0xc3,0xdf,0x00,0x16,0xbf,0x98,0x60}};
static const AdrenoFirmwareRegion zgp_regions[]={
 {0,0x4000,0},{0x4000,0xffc000,1},{0x10004000,0x4000,2},
 {0x60000000,0x20000000,3},{0xc0000000,0x20000000,4}};
static bool zgp_span(const void *p,size_t bytes) {
    return p && bytes && uintptr_t(p)<=UINTPTR_MAX-(bytes-1);
}
static bool zgp_overlap(const void *a,size_t na,const void *b,size_t nb) {
    return uintptr_t(a)<=uintptr_t(b)?uintptr_t(b)-uintptr_t(a)<na:
        uintptr_t(a)-uintptr_t(b)<nb;
}
static uint32_t zgp_region(uint32_t address,uint32_t bytes) {
    if(!bytes || (address&3) || (bytes&3))return UINT32_MAX;
    for(unsigned i=0;i<5;++i) {
        const auto &r=zgp_regions[i];
        if(address>=r.address && bytes<=r.bytes && uint64_t(address)-r.address<=r.bytes-bytes)
            return r.identifier;
    }
    return UINT32_MAX;
}
static ZornGpuPlanStatus zgp_add_backing(ZornGpuFirmwarePlan *p,const ZornGpuLimits &l,
    uint32_t iova,uint32_t bytes,uint32_t region,bool fixed,bool persistent,uint32_t purpose,uint32_t *index) {
    if(!bytes || uint64_t(bytes)+4095>UINT32_MAX)return ZGP_RANGE;
    const uint32_t rounded=(bytes+4095)&~4095u;
    if(fixed && ((iova&4095) || zgp_region(iova,rounded)!=region))return ZGP_RANGE;
    for(uint32_t i=0;i<p->backing_count && fixed;++i) {
        auto &b=p->backings[i];
        if(!b.fixed_iova || b.region!=region)continue;
        if(iova>=b.iova && uint64_t(iova)+bytes<=uint64_t(b.iova)+b.bytes) {
            b.persistent_requested|=persistent;*index=i;return ZGP_OK;
        }
        if(uint64_t(iova)<uint64_t(b.iova)+b.bytes && uint64_t(b.iova)<uint64_t(iova)+rounded)
            return ZGP_RANGE;
    }
    if(p->backing_count>=l.backings || p->backing_count>=16 ||
        uint64_t(p->backing_bytes)+rounded>l.backing_bytes)return ZGP_CAPACITY;
    *index=p->backing_count++;
    p->backings[*index]={iova,rounded,region,uint32_t(fixed),uint32_t(persistent),purpose};
    p->backing_bytes+=rounded;return ZGP_OK;
}
/* Private bounded descriptor over already decoded records. Unit tests include
 * this translation unit to inject malformed records; no bypass API is exported. */
static ZornGpuPlanStatus zgp_describe(ZornGpuFirmwarePlan *p,const ZornGpuLimits &l) {
    if(!p->block_count || p->block_count>64 || p->block_count>l.blocks)return ZGP_CAPACITY;
    bool payload_seen=false;
    for(uint32_t i=0;i<p->block_count;++i) {
        const auto &b=p->blocks[i];
        if(b.bytes) {payload_seen=true;++p->payload_count;continue;}
        if(payload_seen || (b.type!=1 && b.type!=7))return ZGP_REQUIREMENT;
        const uint32_t region=zgp_region(b.address,b.value);
        if(region==UINT32_MAX)return ZGP_RANGE;
        ZornGpuRequest r={b.address,b.value,b.type,region,uint32_t(b.type==7),UINT32_MAX};
        if(r.persistent)++p->persistent_requests;
        if(region!=0 && region!=2) {
            const auto status=zgp_add_backing(p,l,b.address,b.value,region,true,r.persistent,0,&r.backing_index);
            if(status!=ZGP_OK)return status;
        }
        p->requests[p->request_count++]=r;
    }
    if(!payload_seen)return ZGP_FORMAT;
    for(uint32_t i=0;i<p->block_count;++i) {
        const auto &b=p->blocks[i];if(!b.bytes)continue;
        const auto region=zgp_region(b.address,b.bytes);
        if(region==UINT32_MAX || region!=b.region_identifier)return ZGP_RANGE;
        if(region==0 || region==2)continue;
        bool covered=false;
        for(uint32_t j=0;j<p->backing_count;++j) {
            const auto &a=p->backings[j];
            if(a.fixed_iova && a.region==region && b.address>=a.iova &&
                uint64_t(b.address)+b.bytes<=uint64_t(a.iova)+a.bytes)covered=true;
        }
        if(!covered)return ZGP_REQUIREMENT;
    }
    p->queue_count=17;p->hfi_table_bytes=24+48*17;
    p->hfi_queue_offset=(p->hfi_table_bytes+15)&~15u;
    p->hfi_request_bytes=p->hfi_table_bytes+16+4096*17;
    p->hfi_backing_bytes=(p->hfi_request_bytes+4095)&~4095u;p->log_backing_bytes=65536;
    if(l.hfi_bytes<p->hfi_backing_bytes)return ZGP_CAPACITY;
    for(uint32_t i=0;i<17;++i) {
        const uint32_t prio=i<=6?0:i<=10?1:i<=13?2:i<=15?3:4;
        p->queues[i]={i,prio,p->hfi_queue_offset+i*4096,4096};
    }
    uint32_t index;
    auto status=zgp_add_backing(p,l,0,p->log_backing_bytes,3,false,false,1,&index);
    if(status!=ZGP_OK)return status;
    status=zgp_add_backing(p,l,0,p->hfi_backing_bytes,3,false,false,2,&index);
    if(status!=ZGP_OK)return status;
    p->sqe_offset=4;p->sqe_bytes=zgp_sizes[ZGP_SQE]-4;
    p->aqe_offset=4;p->aqe_bytes=zgp_sizes[ZGP_AQE]-4;
    p->zap_requires_authentication=1;p->runtime_complete=0;
    return ZGP_OK;
}
ZornGpuPlanStatus ZornGpuBuildFirmwarePlan(const ZornGpuBlob images[ZGP_IMAGES],
    const ZornGpuLimits *limits,ZornGpuFirmwarePlan *scratch,ZornGpuFirmwarePlan *output) {
    if(!zgp_span(images,sizeof(ZornGpuBlob)*4) || !zgp_span(limits,sizeof(*limits)) ||
        !zgp_span(scratch,sizeof(*scratch)) || !zgp_span(output,sizeof(*output)))return ZGP_ARGUMENT;
    if(uintptr_t(images)%alignof(ZornGpuBlob) || uintptr_t(limits)%alignof(ZornGpuLimits) ||
        uintptr_t(scratch)%alignof(ZornGpuFirmwarePlan) || uintptr_t(output)%alignof(ZornGpuFirmwarePlan))return ZGP_ARGUMENT;
    const ZornGpuLimits l=*limits;
    if(!l.blocks || l.blocks>64 || !l.backings || l.backings>16 || !l.backing_bytes)return ZGP_ARGUMENT;
    if(zgp_overlap(scratch,sizeof(*scratch),output,sizeof(*output)) ||
        zgp_overlap(scratch,sizeof(*scratch),images,sizeof(ZornGpuBlob)*4) ||
        zgp_overlap(output,sizeof(*output),images,sizeof(ZornGpuBlob)*4) ||
        zgp_overlap(scratch,sizeof(*scratch),limits,sizeof(*limits)) ||
        zgp_overlap(output,sizeof(*output),limits,sizeof(*limits)))return ZGP_ALIAS;
    for(unsigned i=0;i<4;++i) {
        if(images[i].bytes!=zgp_sizes[i] || !zgp_span(images[i].data,images[i].bytes))return ZGP_ARGUMENT;
        if(zgp_overlap(images[i].data,images[i].bytes,scratch,sizeof(*scratch)) ||
            zgp_overlap(images[i].data,images[i].bytes,output,sizeof(*output)) ||
            zgp_overlap(images[i].data,images[i].bytes,images,sizeof(ZornGpuBlob)*4) ||
            zgp_overlap(images[i].data,images[i].bytes,limits,sizeof(*limits)))return ZGP_ALIAS;
        for(unsigned j=0;j<i;++j)
            if(zgp_overlap(images[i].data,images[i].bytes,images[j].data,images[j].bytes))return ZGP_ALIAS;
    }
    for(unsigned i=0;i<4;++i) {
        uint8_t digest[32];NativeAdrenoSha256::hash(images[i].data,images[i].bytes,digest);
        if(memcmp(digest,zgp_sha[i],32))return ZGP_HASH;
    }
    memset(scratch,0,sizeof(*scratch));size_t count=0;
    const auto result=AdrenoFirmwarePlanGmu(images[ZGP_GMU].data,images[ZGP_GMU].bytes,
        zgp_regions,5,scratch->blocks,l.blocks,&count);
    if(result!=AdrenoFirmwareSuccess)return result==AdrenoFirmwareNoSpace?ZGP_CAPACITY:ZGP_FORMAT;
    scratch->block_count=uint32_t(count);
    const auto status=zgp_describe(scratch,l);if(status!=ZGP_OK)return status;
    memcpy(output,scratch,sizeof(*output));return ZGP_OK;
}
