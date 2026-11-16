// SPDX-License-Identifier: MIT
#include <IOKit/IOKitLib.h>
#include <mach/mach.h>
#include <stdio.h>
#include <unistd.h>
#include "ZornGpuApplicationProbe26.h"
namespace {
void report(const ZornGpuProbeResult26 &r){
    fprintf(stderr,"ZORN186APP run=d55c2bab3d6d436386ca54c7b6a74f06 pid=%d phase=%u method=%u raw=%x flags=%x iova=%llx fence=%llu crc=%08x firstBad=%x ticks=%llu closed=%u\n",
        getpid(),r.phase,r.method,unsigned(r.raw),r.flags,(unsigned long long)r.iova,(unsigned long long)r.fence,
        r.crc,r.firstBad,(unsigned long long)r.ticks,unsigned(r.closed));fflush(stderr);
}
}
int main()
{
    // This board publishes the application service after its 150s platform
    // checkpoint. Wait at most 240s, within the independent 300s watchdog.
    // Match only the exact owned class; no alternate service or open retry.
    io_service_t service=IO_OBJECT_NULL;
    for(unsigned i=0;i<480 && !service;++i){
        auto matching=IOServiceMatching("ZornGen7AppIoService26");if(!matching)return 1;
        service=IOServiceGetMatchingService(kIOMainPortDefault,matching);
        if(!service)usleep(500000);
    }
    ZornGpuProbeResult26 result{};
    if(!service){result.raw=-10;report(result);return 2;}
    io_connect_t connection=IO_OBJECT_NULL;
    result.raw=IOServiceOpen(service,mach_task_self(),0x4147,&connection);IOObjectRelease(service);
    if(result.raw || !connection){if(!result.raw)result.raw=-11;report(result);return 3;}
    ZornGpuProbeTransport26 io{};io.cookie=&connection;
    io.call=[](void *p,uint32_t method,const void *in,size_t bytes,void *out,size_t *outBytes){
        return int(IOConnectCallStructMethod(*static_cast<io_connect_t *>(p),method,in,bytes,out,outBytes));};
    io.map=[](void *p,uint32_t token,uint64_t *address,uint64_t *bytes){
        return int(IOConnectMapMemory64(*static_cast<io_connect_t *>(p),token,mach_task_self(),address,bytes,kIOMapAnywhere|kIOMapWriteCombineCache));};
    io.unmap=[](void *p,uint32_t token,uint64_t address){
        return int(IOConnectUnmapMemory64(*static_cast<io_connect_t *>(p),token,mach_task_self(),address));};
    io.close=[](void *p){return int(IOServiceClose(*static_cast<io_connect_t *>(p)));};
    io.trace=[](void *,const ZornGpuProbeResult26 &r){report(r);};
    const int raw=zornGpuApplicationProbe26(io,result);report(result);
    return raw?4:0;
}
