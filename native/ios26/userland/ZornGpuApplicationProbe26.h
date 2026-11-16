// SPDX-License-Identifier: MIT
#pragma once
#include "NativeAdrenoABI.h"
#include "K80KnownImage26.h"
// One bounded ordinary-task ABI transaction. All GPU commands come from the
// same source-defined K80 2D image that passed v185; no caller packet input.
struct ZornGpuProbeResult26 {
    unsigned phase=0,method=0;int raw=0;uint32_t flags=0,crc=0,firstBad=UINT32_MAX;
    uint64_t handle=0,iova=0,fence=0,ticks=0;uint32_t token=0;bool closed=false;
};
struct ZornGpuProbeTransport26 {
    void *cookie;
    int (*call)(void *,uint32_t,const void *,size_t,void *,size_t *);
    int (*map)(void *,uint32_t,uint64_t *,uint64_t *);
    int (*unmap)(void *,uint32_t,uint64_t);
    int (*close)(void *);
    void (*trace)(void *,const ZornGpuProbeResult26 &);
};
inline int zornGpuApplicationProbe26(const ZornGpuProbeTransport26 &io,ZornGpuProbeResult26 &r)
{
    constexpr int badReply=-1,badImage=-2;
    if(!io.call || !io.map || !io.unmap || !io.close)return r.raw=badReply;
    auto step=[&](unsigned phase){r.phase=phase;if(io.trace)io.trace(io.cookie,r);};
    auto call=[&](uint32_t method,const void *in,size_t inBytes,void *out,size_t outBytes){
        r.method=method;size_t actual=outBytes;
        const auto raw=io.call(io.cookie,method,in,inBytes,out,&actual);
        r.raw=raw?raw:actual==outBytes?0:badReply;return r.raw;
    };
    step(1);NativeAdrenoAbiParams params{};NativeAdrenoAbiDeviceInfo info{};
    if(call(NativeAdrenoMethodQuery,nullptr,0,&params,sizeof(params)))return r.raw;
    if(params.abi_version!=NativeAdrenoAbiVersion || params.input_bits!=32 || params.output_bits!=36 || params.max_bo_bytes<32768)return r.raw=badReply;
    if(call(NativeAdrenoMethodGetDeviceInfo,nullptr,0,&info,sizeof(info)))return r.raw;
    if(!(info.flags&NativeAdrenoDeviceClientIova) || info.va_size<32768 || !k80KnownImageLayout26(info.va_start))return r.raw=badReply;
    r.iova=info.va_start;r.flags|=1;
    step(2);NativeAdrenoAbiBoAlloc alloc{32768,12,0};NativeAdrenoAbiBoAllocReply allocated{};
    if(call(NativeAdrenoMethodBoAlloc,&alloc,sizeof(alloc),&allocated,sizeof(allocated)))return r.raw;
    if(!allocated.handle)return r.raw=badReply;r.handle=allocated.handle;r.flags|=2;
    step(3);NativeAdrenoAbiBoCpuMap cpu{r.handle};NativeAdrenoAbiBoCpuMapReply view{};
    if(call(NativeAdrenoMethodBoCpuMap,&cpu,sizeof(cpu),&view,sizeof(view)))return r.raw;
    if(!view.token || view.reserved || view.bytes!=32768)return r.raw=badReply;r.token=view.token;
    uint64_t address=0,bytes=0;r.raw=io.map(io.cookie,view.token,&address,&bytes);if(r.raw)return r.raw;
    if(!address || (address&4095u) || bytes!=32768)return r.raw=badReply;r.flags|=4;
    auto *memory=reinterpret_cast<void *>(uintptr_t(address));
    if(!k80KnownImageBuild26(memory,32768,r.iova))return r.raw=badReply;
#if defined(__aarch64__)
    __asm__ volatile("dsb sy" ::: "memory");
#else
    __atomic_thread_fence(__ATOMIC_SEQ_CST); // host transaction fixture only
#endif
    step(4);NativeAdrenoAbiBoMap map{r.handle,r.iova,3,0,3,0};NativeAdrenoAbiBoMapReply mapped{};
    if(call(NativeAdrenoMethodBoMap,&map,sizeof(map),&mapped,sizeof(mapped)))return r.raw;
    if(mapped.iova!=r.iova)return r.raw=badReply;r.flags|=8;
    step(5);NativeAdrenoAbiSubmit submit{};NativeAdrenoAbiSubmitReply submitted{};
    submit.buffer_count=1;submit.buffers[0]={r.handle,r.iova+4*4096,HGKI_SELECTED_COMMAND_WORDS*4};
    if(call(NativeAdrenoMethodSubmit,&submit,sizeof(submit),&submitted,sizeof(submitted)))return r.raw;
    if(!submitted.fence || submitted.fence>UINT32_MAX)return r.raw=badReply;r.fence=submitted.fence;r.flags|=16;
    step(6);NativeAdrenoAbiWaitFence wait{submitted.fence,1000000000};
    if(call(NativeAdrenoMethodWaitFence,&wait,sizeof(wait),nullptr,0))return r.raw;r.flags|=32;
#if defined(__aarch64__)
    __asm__ volatile("dsb sy" ::: "memory");
#else
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
#endif
    // Actual IOConnect CPU alias is write-combined; GPU/CPU visibility and the
    // matching kernel's completion path must still be demonstrated on K80.
    step(7);hgki_result image{};
    if(!k80KnownImageVerify26(memory,32768,r.iova,image)){
        r.crc=image.output_crc;r.firstBad=image.first_bad;return r.raw=badImage;}
    r.crc=image.output_crc;r.firstBad=image.first_bad;r.flags|=64;
    NativeAdrenoAbiTimestamp timestamp{};
    if(call(NativeAdrenoMethodGetTimestamp,nullptr,0,&timestamp,sizeof(timestamp)))return r.raw;r.ticks=timestamp.ticks;
    step(8);r.raw=io.unmap(io.cookie,r.token,address);if(r.raw)return r.raw;
    address=0;memory=nullptr;
    NativeAdrenoAbiBoCpuUnmap unmap{r.handle,r.token,0};
    if(call(NativeAdrenoMethodBoCpuUnmap,&unmap,sizeof(unmap),nullptr,0))return r.raw;r.flags|=128;
    step(9);NativeAdrenoAbiBoFree free{r.handle};
    if(call(NativeAdrenoMethodBoFree,&free,sizeof(free),nullptr,0))return r.raw;r.flags|=256;
    step(10);r.raw=io.close(io.cookie);if(r.raw)return r.raw;r.closed=true;r.flags|=512;
    step(11);return r.raw=0;
    // Failed explicit paths issue no further GPU/free/unmap/close requests.
    // The actual client's normal task-death handler must retain uncertainty.
}
