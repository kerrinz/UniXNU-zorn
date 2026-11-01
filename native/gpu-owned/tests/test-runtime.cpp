#include "XnuMemoryFixture.h"
#include "ZornGpuOwnedRuntime.h"
#include "NativeAdrenoMemory.h"
#include <cassert>
#include <cstdio>
#include <fstream>
#include <vector>
#include <thread>
static bool ready=true;
extern "C" int zorn_gpu_memory_profile_ready(void){return ready;}
IOReturn NativeAdrenoQueryCpu4K(NativeAdrenoCpuState *p){*p={};return fixture.cpu_status;}
IOReturn NativeAdrenoMaintainOwnedPages(void *,size_t,NativeAdrenoCacheOperation){++fixture.cache_calls;return kIOReturnSuccess;}
IOReturn NativeAdrenoMaintainPhysicalPages(uint64_t,size_t,NativeAdrenoCacheOperation){assert(false);return 1;}
IOReturn NativeAdrenoSetPagesCacheMode(const NativeAdrenoPhysicalSpan *,size_t,bool){assert(false);return 1;}
IOReturn NativeAdrenoReassertWriteCombined(const NativeAdrenoPhysicalSpan *,size_t,uint32_t *){assert(false);return 1;}
int main(int argc,char **argv){assert(argc==4);unsigned mode=unsigned(atoi(argv[1]));
 std::ifstream f(argv[2],std::ios::binary);std::vector<uint8_t> src((std::istreambuf_iterator<char>(f)),{});assert(src.size()==4096);uint8_t wire[4096];
 // A writer before configuration/READY cannot collect, allocate or alter RAM.
 assert(zorn_gpu_owned_transport(src.data(),4096,wire)==src.data());assert(!fixture.created);
 if(mode==2)ready=false;if(mode==3)fixture.metadata_fail=fixture.complete_fail=true;
 zorn_gpu_owned_configure(mode?1:0);zorn_gpu_owned_configure(mode?0:1); // second call cannot reconfigure
 zorn_gpu_owned_gui_tick();unsigned created=fixture.created,cache=fixture.cache_calls;
 for(unsigned i=0;i<40;++i)zorn_gpu_owned_gui_tick();assert(created==fixture.created && cache==fixture.cache_calls);
 if(!mode){assert(!created && zorn_gpu_owned_transport(src.data(),4096,wire)==src.data());}
 else {auto p=zorn_gpu_owned_transport(src.data(),4096,wire);assert(p==wire);std::ofstream out(argv[3],std::ios::binary);out.write((char*)p,4096);
   if(mode==1)assert(created==8 && cache==8);if(mode==2)assert(!created);if(mode==3)assert(created==1);
   std::vector<std::thread> threads;for(unsigned t=0;t<8;++t)threads.emplace_back([&]{uint8_t privateWire[4096];for(unsigned i=0;i<32;++i){assert(zorn_gpu_owned_transport(src.data(),4096,privateWire)==privateWire);assert(!memcmp(privateWire,wire,4096));zorn_gpu_owned_gui_tick();}});
   for(auto &t:threads)t.join();assert(created==fixture.created && cache==fixture.cache_calls);
 }
 printf("{\"mode\":%u,\"allocations\":%u,\"cache_calls\":%u,\"releases\":%u}\n",mode,fixture.created,fixture.cache_calls,fixture.released);
 // Host-only process teardown, deliberately outside the runtime API.
 for(auto *p:fixture.live){free(p->raw);delete p;}for(void *p:fixture.metadata)free(p);
}
