#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <thread>
#include <vector>
#include <atomic>
#include "observer/ZornCpuActive.h"
extern "C" {
#include "observer/active-log-v2-codec.h"
#include "observer/observer-host-shim.h"
}
static const char *mode;
static uint64_t nowMs;
static unsigned readCalls,clockCalls;
extern "C" uint64_t mach_absolute_time(void){return 192000000ULL+nowMs*19200;}
extern "C" void clock_timebase_info(mach_timebase_info_data_t *v){v->numer=625;v->denom=12;}
extern "C" int zorn_active_profile_ready(void){return 1;}
extern "C" int zorn_active_sampler_ready(void){return std::strcmp(mode,"not-ready")!=0;}
extern "C" int zorn_active_read_core(void *,unsigned id,uint64_t out[2]) {
    ++readCalls;if(!std::strcmp(mode,"busy") && id==3)return 1;
    out[0]=(nowMs/10+id)*192000;out[1]=(nowMs/20+id)*192000;
    if(!std::strcmp(mode,"overflow"))out[0]=((uint64_t)UINT32_MAX+1)*192000;
    return 0;
}
extern "C" int zorn_active_clock_info(void *,uint32_t *raw,uint64_t *ns) {
    ++clockCalls;*raw=192000;*ns=10000000;
    if(!std::strcmp(mode,"clock-bad")){*raw=0;*ns=0;return 0;}return 1;
}
typedef int IOReturn;
enum {kIOReturnBadArgument=-1,kIOReturnSuccess=0};
struct Block {uint8_t bytes[4096];};
static Block gLogBlock;
static bool gGuiWatch=true;
static int gLogBusy;
static uint64_t gLogWriteAttempts,gLogWriteSuccesses,gLogWriteNanoseconds;
alignas(64) static uint8_t gCpuActiveWire[4096],gCpuActiveScratch[4096];
static std::atomic<unsigned> inWrite{0};
static unsigned packedWrites,plainWrites;
static void zorn_gui_fill_footer(){assert(__atomic_load_n(&gLogBusy,__ATOMIC_RELAXED)==1);}
static void absolutetime_to_nanoseconds(uint64_t delta,uint64_t *ns){*ns=delta*625/12;}
static IOReturn hostWriteLog4k(const void *source) {
    assert(inWrite.fetch_add(1)==0);assert(__atomic_load_n(&gLogBusy,__ATOMIC_RELAXED)==1);
    uint8_t wire[4096],scratch[4096];std::memcpy(wire,source,4096);
    if(!std::memcmp(wire,"ZORNLOGE",8)) {
        ZornSweepCapture c;assert(zorn_active_v2_decode(wire,4096,&c,scratch,4096)==0);++packedWrites;
        assert((c.error==0)==!std::strcmp(mode,"healthy"));
    } else ++plainWrites;
    assert(!std::memcmp(wire,&gLogBlock,4096)); // latest complete old log, not a stale cached frame
    assert(!std::memcmp(&gLogBlock,"ZORNLOGD",8));
    assert(inWrite.fetch_sub(1)==1);return 0;
}
// Exact candidate function body, extracted by the test driver.
#include "writer-body.inc"
int main(int argc,char **argv) {
    assert(argc==4);mode=argv[1];FILE *f=std::fopen(argv[2],"rb");assert(f);
    assert(std::fread(&gLogBlock,1,4096,f)==4096);std::fclose(f);
    uint8_t before[4096];std::memcpy(before,&gLogBlock,4096);
    assert(zorn_cpu_active_transport(&gLogBlock,4096,gCpuActiveWire,gCpuActiveScratch)==&gLogBlock);
    zorn_cpu_active_configure(std::strcmp(mode,"off")!=0,192000000);
    zorn_cpu_active_configure(0,0); // repeated initialization never resets an exposed state
    if(std::strcmp(mode,"absent")) {
        nowMs=!std::strcmp(mode,"late")?120001:60000;zorn_cpu_active_gui_tick();
        assert(zorn_cpu_active_transport(&gLogBlock,4096,gCpuActiveWire,gCpuActiveScratch)==&gLogBlock);
        nowMs=!std::strcmp(mode,"late")?270001:!std::strcmp(mode,"backward")?59999:240000;zorn_cpu_active_gui_tick();
    }
    nowMs=300000;zorn_cpu_active_gui_finish();
    const unsigned reads=readCalls,clocks=clockCalls;
    assert(reads<=16 && clocks<=4);
    assert(zorn_cpu_active_transport(&gLogBlock,4096,(uint8_t *)&gLogBlock,gCpuActiveScratch)==&gLogBlock);
    assert(!std::memcmp(before,&gLogBlock,4096));
    for(unsigned i=0;i<8;++i) {
        gLogBlock.bytes[16]=(uint8_t)('A'+i);
        __atomic_store_n(&gLogBusy,1,__ATOMIC_RELEASE);
        assert(zorn_write_log4k(&gLogBlock)==0);__atomic_store_n(&gLogBusy,0,__ATOMIC_RELEASE);
    }
    unsigned packedBefore=packedWrites;
    std::vector<std::thread> threads;
    for(unsigned t=0;t<8;++t)threads.emplace_back([t] {
        for(unsigned i=0;i<20;++i)if(__sync_bool_compare_and_swap(&gLogBusy,0,1)) {
            gLogBlock.bytes[17]=(uint8_t)('A'+t);
            assert(zorn_write_log4k(&gLogBlock)==0);__sync_lock_release(&gLogBusy);
        }
    });
    for(auto &thread:threads)thread.join();
    assert(!inWrite && readCalls==reads && clockCalls==clocks);
    assert(gLogWriteSuccesses==gLogWriteAttempts && zorn_write_log4k(nullptr)==kIOReturnBadArgument);
    const void *wire=zorn_cpu_active_transport(&gLogBlock,4096,gCpuActiveWire,gCpuActiveScratch);
    f=std::fopen(argv[3],"wb");assert(f && std::fwrite(wire,1,4096,f)==4096);std::fclose(f);
    // Incompatible original text falls back without mutating the canonical page.
    gLogBlock.bytes[27]=1;std::memcpy(before,&gLogBlock,4096);
    assert(zorn_cpu_active_transport(&gLogBlock,4096,gCpuActiveWire,gCpuActiveScratch)==&gLogBlock);
    assert(!std::memcmp(before,&gLogBlock,4096));
    if(!std::strcmp(mode,"off"))assert(!packedWrites && !reads && !clocks);
    else assert(packedBefore==8 && packedWrites>=8);
    std::printf("{\"mode\":\"%s\",\"reads\":%u,\"clock_reads\":%u,\"packed_writes\":%u,\"plain_writes\":%u,\"canonical_preserved\":true,\"no_sampling_in_writer\":true}\n",mode,reads,clocks,packedWrites,plainWrites);
}
