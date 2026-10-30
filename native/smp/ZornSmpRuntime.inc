// SPDX-License-Identifier: BSD-2-Clause-Patent
// Included by the board's generated, pinned ArmCpu adapter, never upstream.
#include <kern/clock.h>
#include <kern/cpu_number.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <vm/vm_kern.h>
#include <vm/pmap.h>
#include <arm/memory_types.h>
#include "ZornSmpPolicy.h"
extern "C" processor_t thread_bind(processor_t);
extern "C" void zorn_ufs_smp_record(const char *,unsigned,int);
// Exact Darwin23 private signatures from osfmk/vm/pmap.h. The IOKit recipe
// does not export the MACH_KERNEL_PRIVATE declarations. CONFIG_SPTM=0:
// pmap_mapping_type_t is uint8_t and PMAP_MAPPING_TYPE_DEFAULT is1.
#if defined(CONFIG_SPTM) && CONFIG_SPTM
#error unexpected protected pmap ABI
#endif
extern "C" kern_return_t pmap_enter_options_addr(pmap_t,vm_map_offset_t,uint64_t,
    vm_prot_t,vm_prot_t,unsigned int,boolean_t,unsigned int,void *,uint8_t);
extern "C" void pmap_remove(pmap_t,vm_map_offset_t,vm_map_offset_t);
extern "C" const pmap_t kernel_pmap;
extern "C" char start_cpu[], CpuDataEntries[];
extern "C" vm_offset_t ml_vtophys(vm_offset_t);
// Darwin23 ARM64 pmap_public.h defines pmap_paddr_t as uint64_t;
// its private typedef is unavailable in the IOKit driver headers.
extern "C" uint64_t cpu_ttep;
extern "C" {
volatile unsigned zorn_smp_tlb_ready;
volatile unsigned zorn_smp_preflight_active=1;
volatile uint64_t zornCpuRootBefore;
volatile uint32_t zornCpuRootPublish;
// Explicit assembly diagnostic layer owns one cache line per CPU. CPU0
// publishes zeroes before CPU_ON, then never writes a secondary's line.
alignas(64) volatile uint64_t zorn_cpu1_trace[8][8]={};
}
static void zornTraceRead(unsigned id,uint64_t out[6]) {
    uint64_t ctr;__asm__ volatile("mrs %0,ctr_el0":"=r"(ctr));
    if(id>=8 || (4ULL<<((ctr>>16)&15))!=64){out[0]=~uint64_t(0);return;}
    auto address=reinterpret_cast<uintptr_t>(&zorn_cpu1_trace[id][0]);
    // Its only CPU0 store was cleaned/invalidated before the worker started.
    // Invalidate that clean reader alias before observing MMU-off PA stores.
    __asm__ volatile("dc ivac,%0\n\tdsb sy\n\tisb"::"r"(address):"memory");
    for(unsigned n=0;n<6;++n)out[n]=__atomic_load_n(&zorn_cpu1_trace[id][n],__ATOMIC_RELAXED);
}
static volatile uint64_t zornCoreMidr[8],zornCoreMpidr[8],zornCoreSys[8][4];
static volatile uint32_t zornCoreBeats[8],zornCoreTlb[8];
static volatile uint32_t zornSeen,zornBound,zornPhase,zornFailure,zornAbort,zornCoordinatorDone;
static volatile uint32_t zornRemapEpoch,zornRemapStop,zornRemapStopped;
#include "ZornActiveHandles.inc"
static volatile uint32_t zornRemapAck[8],zornRemapError[8];
static volatile uint64_t zornRemapObserved[8];
static volatile uint64_t *zornRemapAlias;
static constexpr uint64_t zornRemapA=0x4b38305f50414741ULL,zornRemapB=0x4b38305f50414742ULL;

void ArmCpu::zornRemapWorker(void *arg,wait_result_t) {
    unsigned id=unsigned(reinterpret_cast<uintptr_t>(arg));
    thread_bind(gZornCpus[id]->machProcessor);thread_block(THREAD_CONTINUE_NULL);
    unsigned previous=0;
    while(!__atomic_load_n(&zornRemapStop,__ATOMIC_ACQUIRE)) {
        unsigned epoch=__atomic_load_n(&zornRemapEpoch,__ATOMIC_ACQUIRE);
        if(!epoch || epoch==previous){IOSleep(1);continue;}
        if(cpu_number()!=int(id)){__atomic_store_n(&zornRemapError[id],1U,__ATOMIC_RELEASE);break;}
        uint64_t observed=*zornRemapAlias;
        __atomic_store_n(&zornRemapObserved[id],observed,__ATOMIC_RELEASE);
        if(observed!=(epoch&1?zornRemapA:zornRemapB)) {
            __atomic_store_n(&zornRemapError[id],epoch+10,__ATOMIC_RELEASE);break;
        }
        previous=epoch;__atomic_store_n(&zornRemapAck[id],epoch,__ATOMIC_RELEASE);
    }
    thread_bind(PROCESSOR_NULL);
    __atomic_fetch_or(&zornRemapStopped,1U<<id,__ATOMIC_RELEASE);
    thread_terminate(current_thread());
}

bool ArmCpu::zornRemapProbe(void) {
    thread_bind(gZornCpus[0]->machProcessor);thread_block(THREAD_CONTINUE_NULL);
    __atomic_store_n(&zornPhase,70U,__ATOMIC_RELEASE);zornReport(false,false);
    OSSharedPtr<IOBufferMemoryDescriptor> memory(IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,
        IOOptionBits(kIODirectionInOut)|IOOptionBits(kIOMemoryPhysicallyContiguous),8192,4096),OSNoRetain);
    if(!memory){__atomic_store_n(&zornFailure,400U,__ATOMIC_RELEASE);return false;}
    __atomic_store_n(&zornPhase,71U,__ATOMIC_RELEASE);zornReport(false,false);
    IOByteCount length=0;uint64_t pa=memory->getPhysicalSegment(0,&length);
    if(!pa || (pa&4095) || length<8192){__atomic_store_n(&zornFailure,401U,__ATOMIC_RELEASE);return false;}
    __atomic_store_n(&zornPhase,72U,__ATOMIC_RELEASE);zornReport(false,false);
    auto contents=static_cast<volatile uint64_t *>(memory->getBytesNoCopy());
    contents[0]=zornRemapA;contents[512]=zornRemapB;
    vm_offset_t alias=0;
    __atomic_store_n(&zornPhase,73U,__ATOMIC_RELEASE);zornReport(false,false);
    // This entry reserves VA only. Its mappings point to separately wired
    // descriptor pages, not resident pages in this entry's VM object. Keep
    // the entry unwired so kmem_free does not attempt to unwire absent pages.
    if(kernel_memory_allocate(kernel_map,&alias,4096,0,kma_flags_t(KMA_VAONLY|KMA_PAGEABLE),VM_KERN_MEMORY_IOKIT)!=KERN_SUCCESS) {
        __atomic_store_n(&zornFailure,402U,__ATOMIC_RELEASE);return false;
    }
    zornRemapAlias=reinterpret_cast<volatile uint64_t *>(alias);
    __atomic_store_n(&zornPhase,74U,__ATOMIC_RELEASE);zornReport(false,false);
    unsigned started=0;bool ok=true;
    // All workers retain the same kernel VA. Only CPU0 changes its PTE.
    for(unsigned id=0;id<8;++id) {
        thread_t worker=THREAD_NULL;
        if(kernel_thread_start(zornRemapWorker,reinterpret_cast<void *>(uintptr_t(id)),&worker)!=KERN_SUCCESS) {
            __atomic_store_n(&zornFailure,410U+id,__ATOMIC_RELEASE);ok=false;break;
        }
        started|=1U<<id;thread_deallocate(worker);
    }
    for(unsigned epoch=1;ok && epoch<=9;++epoch) {
        __atomic_store_n(&zornPhase,60U+epoch,__ATOMIC_RELEASE);
        kern_return_t kr=pmap_enter_options_addr(kernel_pmap,alias,pa+(epoch&1?0:4096),
            VM_PROT_READ,VM_PROT_NONE,2U,TRUE,0,nullptr,uint8_t(1)); // VM_MEM_COHERENT
        if(kr){__atomic_store_n(&zornFailure,440U+epoch,__ATOMIC_RELEASE);ok=false;break;}
        __atomic_store_n(&zornRemapEpoch,epoch,__ATOMIC_RELEASE);
        uint64_t deadline;nanoseconds_to_deadline(2*NSEC_PER_SEC,&deadline);
        for(unsigned id=0;id<8;++id) {
            while(__atomic_load_n(&zornRemapAck[id],__ATOMIC_ACQUIRE)!=epoch &&
                  !__atomic_load_n(&zornRemapError[id],__ATOMIC_ACQUIRE) && mach_absolute_time()<deadline)IOSleep(1);
            if(__atomic_load_n(&zornRemapAck[id],__ATOMIC_ACQUIRE)!=epoch ||
               __atomic_load_n(&zornRemapError[id],__ATOMIC_ACQUIRE)) {
                __atomic_store_n(&zornFailure,420U+id,__ATOMIC_RELEASE);ok=false;break;
            }
        }
    }
    __atomic_store_n(&zornRemapStop,1U,__ATOMIC_RELEASE);
    uint64_t deadline;nanoseconds_to_deadline(NSEC_PER_SEC,&deadline);
    while(__atomic_load_n(&zornRemapStopped,__ATOMIC_ACQUIRE)!=started && mach_absolute_time()<deadline)IOSleep(1);
    if(__atomic_load_n(&zornRemapStopped,__ATOMIC_ACQUIRE)!=started) {
        // Preserve backing memory if a worker has not acknowledged stopping.
        (void)memory.detach();__atomic_store_n(&zornFailure,460U,__ATOMIC_RELEASE);return false;
    }
    __atomic_store_n(&zornPhase,75U,__ATOMIC_RELEASE);zornReport(false,false);
    pmap_remove(kernel_pmap,alias,alias+4096);
    __atomic_store_n(&zornPhase,76U,__ATOMIC_RELEASE);zornReport(false,false);
    kmem_free(kernel_map,alias,4096);
    __atomic_store_n(&zornPhase,77U,__ATOMIC_RELEASE);zornReport(false,false);
    return ok;
}

extern "C" __attribute__((noinline)) void zorn_smp_tlb_flush(void) {
    // Coarse, all-ASID inner-shareable operation. No ASID-specific TLBI.
    __asm__ volatile("dsb ishst\n\ttlbi vmalle1is\n\tdsb ish\n\tisb" ::: "memory");
}

void ArmCpu::zornCaptureIdentity(void) {
    uint64_t midr,mpidr,el,sctlr,tcr,mair;
    __asm__ volatile("mrs %0,midr_el1\n\tmrs %1,mpidr_el1\n\tmrs %2,CurrentEL\n\tmrs %3,sctlr_el1\n\tmrs %4,tcr_el1\n\tmrs %5,mair_el1"
        :"=r"(midr),"=r"(mpidr),"=r"(el),"=r"(sctlr),"=r"(tcr),"=r"(mair));
    if(logicalId>=8)panic("zorn SMP logical index");
    __atomic_store_n(&zornCoreMidr[logicalId],midr,__ATOMIC_RELEASE);
    __atomic_store_n(&zornCoreMpidr[logicalId],mpidr,__ATOMIC_RELEASE);
    const uint64_t values[4]={el,sctlr,tcr,mair};
    for(unsigned i=0;i<4;++i)__atomic_store_n(&zornCoreSys[logicalId][i],values[i],__ATOMIC_RELEASE);
    if(!ZornSmpPolicy::identity(logicalId,midr,mpidr) || cpu_number()!=int(logicalId) || el!=4) {
        __atomic_store_n(&zornFailure,100+logicalId,__ATOMIC_RELEASE);
        if(!logicalId)panic("zorn SMP boot identity mismatch");
        for(;;)__asm__ volatile("wfe");
    }
    __atomic_fetch_or(&zornSeen,1U<<logicalId,__ATOMIC_RELEASE);
}

void ArmCpu::zornReport(bool final,bool pass) {
    char text[2400];
    unsigned gui=0;PE_parse_boot_argn("zorn_smp_continue",&gui,sizeof(gui));
    int n=snprintf(text,sizeof(text),"SMP %s target=8 phase=%u seen=%x bound=%x failure=%u tlb=%u ",
        final?(pass?"PASS":"FAIL"):"STATE",__atomic_load_n(&zornPhase,__ATOMIC_ACQUIRE),
        __atomic_load_n(&zornSeen,__ATOMIC_ACQUIRE),__atomic_load_n(&zornBound,__ATOMIC_ACQUIRE),
        __atomic_load_n(&zornFailure,__ATOMIC_ACQUIRE),__atomic_load_n(&zorn_smp_tlb_ready,__ATOMIC_ACQUIRE));
    // The GUI footer's small ring must retain the failing CPU's startup
    // stage and PSCI result, not only its still-zero identity. Observation only.
    unsigned failure=__atomic_load_n(&zornFailure,__ATOMIC_ACQUIRE);
    if(gui==1 && failure>=260 && failure<268 && n>0 && unsigned(n)<sizeof(text)) {
        unsigned id=failure-260;
        n+=snprintf(text+n,sizeof(text)-unsigned(n),"START%u step=%u rc=%d fail=%u ",id,
            __atomic_load_n(&armcpu_smp_step[id],__ATOMIC_ACQUIRE),
            __atomic_load_n(&armcpu_smp_psci_rc[id],__ATOMIC_ACQUIRE),
            __atomic_load_n(&armcpu_smp_fail[id],__ATOMIC_ACQUIRE));
        if(final && gZornCpus[id] && n>0 && unsigned(n)<sizeof(text)) {
            // Observation after the existing gate failed, never another CPU_ON.
            // PSCI 1.0 AFFINITY_INFO64, lowest affinity level zero:
            // 0=ON, 1=OFF, 2=ON_PENDING; preserve all negative errors.
            bool hvc=false;
            int64_t info=psciConduit(&hvc)?psciCall(hvc,0xc4000004ULL,
                gZornCpus[id]->signalTarget()&0xff00ffffffULL,0,0):-1001;
            uint64_t entries=0,bootBases[2]={},slot[2]={},handler=0,trace[6]={};uint32_t vector[2]={},physicalId=0;
            // Pinned Darwin23 ARM64 assym: CPU_DATA_ENTRIES=8,
            // BA_VIRT_BASE=8, BA_PHYS_BASE=16. Only known static objects read.
            memcpy(&entries,ResetHandlerData+8,sizeof(entries));
            memcpy(bootBases,const_boot_args+8,sizeof(bootBases));
            memcpy(vector,LowResetVectorBase,sizeof(vector));
            memcpy(slot,CpuDataEntries+id*16,sizeof(slot));
            // The real CPU table owns this wired allocation. Validate its
            // virtual/physical pair before reading pinned Darwin23 fields.
            bool readable=slot[0] && slot[1] && slot[1]<=~uint64_t(0)-444 &&
                ml_vtophys(static_cast<vm_offset_t>(slot[1]))==slot[0] &&
                ml_vtophys(static_cast<vm_offset_t>(slot[1]+443))==slot[0]+443;
            if(readable) {
                memcpy(&handler,reinterpret_cast<const void *>(slot[1]+168),sizeof(handler));
                memcpy(&physicalId,reinterpret_cast<const void *>(slot[1]+440),sizeof(physicalId));
            }
            zornTraceRead(id,trace);
            n+=snprintf(text+n,sizeof(text)-unsigned(n),
                "AI=%lld K=%llx/%llx P0=%llx/%u V=%llx S=%llx R=%llx C=%llx/%llx B=%llx/%llx W=%08x/%08x D=%llx H=%llx P=%x Q=%u T=%llx/%llx/%llx/%llx/%llx/%llx ",
                info,static_cast<uint64_t>(cpu_ttep),static_cast<uint64_t>(ml_static_vtop(reinterpret_cast<vm_offset_t>(&cpu_ttep))),
                __atomic_load_n(&zornCpuRootBefore,__ATOMIC_ACQUIRE),__atomic_load_n(&zornCpuRootPublish,__ATOMIC_ACQUIRE),
                static_cast<uint64_t>(ml_static_vtop(reinterpret_cast<vm_offset_t>(LowResetVectorBase))),
                static_cast<uint64_t>(ml_static_vtop(reinterpret_cast<vm_offset_t>(start_cpu))),
                static_cast<uint64_t>(ml_static_vtop(reinterpret_cast<vm_offset_t>(ResetHandlerData))),
                entries,static_cast<uint64_t>(ml_static_vtop(reinterpret_cast<vm_offset_t>(CpuDataEntries))),
                bootBases[0],bootBases[1],vector[0],vector[1],slot[0],handler,physicalId,readable?1U:0U,
                trace[0],trace[1],trace[2],trace[3],trace[4],trace[5]);
        }
    }
    // A final successful GUI report is the explicit preflight-stop profile.
    // Sample only our CPU1 slot and known static root, without firmware calls.
    // Normal GUI continuation uses a non-final report and never enters here.
    const bool compactSuccessSnapshot=final && pass && gui==1 && failure==0;
    if(compactSuccessSnapshot && n>0 && unsigned(n)<sizeof(text)) {
        uint64_t trace[6]={};zornTraceRead(1,trace);
        n+=snprintf(text+n,sizeof(text)-unsigned(n),
            "K=%llx/%llx P0=%llx/%u T1=%llx/%llx/%llx/%llx/%llx/%llx ",
            static_cast<uint64_t>(cpu_ttep),static_cast<uint64_t>(ml_static_vtop(reinterpret_cast<vm_offset_t>(&cpu_ttep))),
            __atomic_load_n(&zornCpuRootBefore,__ATOMIC_ACQUIRE),__atomic_load_n(&zornCpuRootPublish,__ATOMIC_ACQUIRE),
            trace[0],trace[1],trace[2],trace[3],trace[4],trace[5]);
    }
    for(unsigned id=0;id<8 && n>0 && unsigned(n)<sizeof(text);++id) {
        // Keep the final failure snapshot within the existing GUI log budget.
        // Seen/bound masks retain the other cores' progress; do not drop the
        // failed core's evidence; preserve successful per-core records.
        if(gui==1 && final && failure>=260 && failure<268 && id!=0 && id!=failure-260)continue;
        if(compactSuccessSnapshot) {
            // Identity checks still ran. Keep all eight counters plus root
            // evidence inside800 bytes, including maximal diagnostic values.
            n+=snprintf(text+n,sizeof(text)-unsigned(n),"C%u t=%u i=%u b=%u r=%u e=%u; ",id,
                __atomic_load_n(&armcpu_core_timer[id],__ATOMIC_RELAXED),__atomic_load_n(&armcpu_core_sgi[id],__ATOMIC_RELAXED),
                __atomic_load_n(&zornCoreBeats[id],__ATOMIC_ACQUIRE),__atomic_load_n(&zornRemapAck[id],__ATOMIC_ACQUIRE),
                __atomic_load_n(&zornRemapError[id],__ATOMIC_ACQUIRE));
            continue;
        }
        if(gui==1) {
            n+=snprintf(text+n,sizeof(text)-unsigned(n),"C%u m=%llx p=%llx t=%u i=%u b=%u r=%u e=%u; ",id,
                __atomic_load_n(&zornCoreMidr[id],__ATOMIC_ACQUIRE),__atomic_load_n(&zornCoreMpidr[id],__ATOMIC_ACQUIRE),
                __atomic_load_n(&armcpu_core_timer[id],__ATOMIC_RELAXED),__atomic_load_n(&armcpu_core_sgi[id],__ATOMIC_RELAXED),
                __atomic_load_n(&zornCoreBeats[id],__ATOMIC_ACQUIRE),__atomic_load_n(&zornRemapAck[id],__ATOMIC_ACQUIRE),
                __atomic_load_n(&zornRemapError[id],__ATOMIC_ACQUIRE));
            continue;
        }
        n+=snprintf(text+n,sizeof(text)-n,"C%u step=%u rc=%d fail=%u MIDR=%llx MPIDR=%llx timer=%u ipi=%u beats=%u tlb=%u EL=%llx SCTLR=%llx TCR=%llx MAIR=%llx remap=%u err=%u value=%llx; ",
            id,__atomic_load_n(&armcpu_smp_step[id],__ATOMIC_ACQUIRE),
            __atomic_load_n(&armcpu_smp_psci_rc[id],__ATOMIC_ACQUIRE),
            __atomic_load_n(&armcpu_smp_fail[id],__ATOMIC_ACQUIRE),
            __atomic_load_n(&zornCoreMidr[id],__ATOMIC_ACQUIRE),__atomic_load_n(&zornCoreMpidr[id],__ATOMIC_ACQUIRE),
            __atomic_load_n(&armcpu_core_timer[id],__ATOMIC_RELAXED),__atomic_load_n(&armcpu_core_sgi[id],__ATOMIC_RELAXED),
            __atomic_load_n(&zornCoreBeats[id],__ATOMIC_ACQUIRE),__atomic_load_n(&zornCoreTlb[id],__ATOMIC_ACQUIRE),
            __atomic_load_n(&zornCoreSys[id][0],__ATOMIC_ACQUIRE),__atomic_load_n(&zornCoreSys[id][1],__ATOMIC_ACQUIRE),
            __atomic_load_n(&zornCoreSys[id][2],__ATOMIC_ACQUIRE),__atomic_load_n(&zornCoreSys[id][3],__ATOMIC_ACQUIRE),
            __atomic_load_n(&zornRemapAck[id],__ATOMIC_ACQUIRE),__atomic_load_n(&zornRemapError[id],__ATOMIC_ACQUIRE),
            __atomic_load_n(&zornRemapObserved[id],__ATOMIC_ACQUIRE));
    }
    if(n<=0 || unsigned(n)>=sizeof(text))panic("zorn SMP report bounds");
    if(gui==1 && n>800)panic("zorn SMP compact log bounds");
    zorn_ufs_smp_record(text,unsigned(n),final?1:0);
}

void ArmCpu::zornCoordinator(void *,wait_result_t) {
    thread_bind(gZornCpus[0]->machProcessor);
    if(cpu_number()!=0)thread_block(THREAD_CONTINUE_NULL);
    for(unsigned id=1;id<8 && !__atomic_load_n(&zornAbort,__ATOMIC_ACQUIRE);++id) {
        uint64_t deadline;nanoseconds_to_deadline(3*NSEC_PER_SEC,&deadline);
        ArmCpu *cpu=nullptr;
        while(!(cpu=__atomic_exchange_n(&gPending[id],static_cast<ArmCpu *>(nullptr),__ATOMIC_ACQ_REL))) {
            if(mach_absolute_time()>deadline){__atomic_store_n(&zornFailure,200+id,__ATOMIC_RELEASE);goto done;}
            IOSleep(5);
        }
        __atomic_store_n(&zornPhase,10+id,__ATOMIC_RELEASE);zornReport(false,false);
        if(!cpu->finishSecondary()){__atomic_store_n(&zornFailure,220+id,__ATOMIC_RELEASE);cpu->release();goto done;}
        __atomic_store_n(&zornPhase,30+id,__ATOMIC_RELEASE);zornReport(false,false);
        kern_return_t result=processor_start(cpu->machProcessor);
        if(result){__atomic_store_n(&zornFailure,240+id,__ATOMIC_RELEASE);cpu->release();goto done;}
        gZornCpus[0]->signalCPU(cpu);
        nanoseconds_to_deadline(2*NSEC_PER_SEC,&deadline);
        while(cpu->getCPUState()!=kIOCPUStateRunning || !__atomic_load_n(&armcpu_core_sgi[id],__ATOMIC_RELAXED)) {
            if(mach_absolute_time()>deadline){__atomic_store_n(&zornFailure,260+id,__ATOMIC_RELEASE);cpu->release();goto done;}
            IOSleep(5);
        }
        cpu->registerService();cpu->release();zornReport(false,false);
    }
    if(__atomic_load_n(&zornAbort,__ATOMIC_ACQUIRE))goto done;
    for(unsigned id=1;id<8;++id)gZornCpus[0]->signalCPU(gZornCpus[id]);
    for(unsigned id=0;id<8 && !__atomic_load_n(&zornAbort,__ATOMIC_ACQUIRE);++id) {
        __atomic_store_n(&zornPhase,50+id,__ATOMIC_RELEASE);
        thread_bind(gZornCpus[id]->machProcessor);thread_block(THREAD_CONTINUE_NULL);
        if(cpu_number()!=int(id) || !ZornSmpPolicy::identity(id,__atomic_load_n(&zornCoreMidr[id],__ATOMIC_ACQUIRE),__atomic_load_n(&zornCoreMpidr[id],__ATOMIC_ACQUIRE))) {
            __atomic_store_n(&zornFailure,300+id,__ATOMIC_RELEASE);goto done;
        }
        zorn_smp_tlb_flush();__atomic_store_n(&zornCoreTlb[id],1U,__ATOMIC_RELEASE);
        for(unsigned beat=0;beat<10;++beat) {
            if(cpu_number()!=int(id)){__atomic_store_n(&zornFailure,320+id,__ATOMIC_RELEASE);goto done;}
            gZornCpus[id]->signalCPU(gZornCpus[0]);
            __atomic_fetch_add(&zornCoreBeats[id],1U,__ATOMIC_RELEASE);IOSleep(20);
        }
        __atomic_fetch_or(&zornBound,1U<<id,__ATOMIC_RELEASE);
    }
    if(!__atomic_load_n(&zornAbort,__ATOMIC_ACQUIRE)) (void)zornRemapProbe();
done:
    thread_bind(PROCESSOR_NULL);
    __atomic_store_n(&zornCoordinatorDone,1U,__ATOMIC_RELEASE);
    thread_terminate(current_thread());
}

static __attribute__((noinline)) void zornPrepareCpuRoot(void) {
    unsigned publication=0;
    PE_parse_boot_argn("zorn_smp_root_publish",&publication,sizeof(publication));
    if(publication>1)panic("zorn SMP root publication mode");
    uint64_t root=__atomic_load_n(&cpu_ttep,__ATOMIC_ACQUIRE);
    if(!root || (root&4095))panic("zorn SMP root unavailable before CPU_ON");
    __atomic_store_n(&zornCpuRootBefore,root,__ATOMIC_RELEASE);
    __atomic_store_n(&zornCpuRootPublish,publication,__ATOMIC_RELEASE);
    // The MMU-off warm path loads this known static root from physical RAM.
    // Explicit experiment1 publishes only its containing cache line, not tables.
    if(publication==1)cleanToMemory(&cpu_ttep,sizeof(cpu_ttep));
}

bool ArmCpu::zornPreflight(void) {
    unsigned mode=0;PE_parse_boot_argn("zorn_smp_preflight",&mode,sizeof(mode));
    if(mode!=8 || ml_get_max_cpu_number()!=7 || !gZornCpus[0] || !gZornHold)panic("zorn SMP preflight configuration");
    zornPrepareCpuRoot(); // CPU0 snapshot/publication precedes the startup worker
    // Per-boot initialization: a stage is evidence only after this core writes it.
    for(unsigned id=0;id<8;++id)for(unsigned word=0;word<8;++word)
        __atomic_store_n(&zorn_cpu1_trace[id][word],uint64_t(0),__ATOMIC_RELAXED);
    cleanToMemory(const_cast<const uint64_t *>(&zorn_cpu1_trace[0][0]),sizeof(zorn_cpu1_trace));
    __atomic_store_n(&zornPhase,1U,__ATOMIC_RELEASE);zornReport(false,false);
    zorn_smp_tlb_flush(); // watchdog bounds a non-returning architectural probe
    __atomic_store_n(&zorn_smp_tlb_ready,1U,__ATOMIC_RELEASE);
    __atomic_store_n(&zornPhase,2U,__ATOMIC_RELEASE);zornReport(false,false);
    thread_t worker=THREAD_NULL;
    if(kernel_thread_start(zornCoordinator,nullptr,&worker)!=KERN_SUCCESS)panic("zorn SMP coordinator allocation");
    thread_deallocate(worker);
    uint64_t deadline;nanoseconds_to_deadline(30*NSEC_PER_SEC,&deadline);
    while(!__atomic_load_n(&zornCoordinatorDone,__ATOMIC_ACQUIRE) && !__atomic_load_n(&zornFailure,__ATOMIC_ACQUIRE) && mach_absolute_time()<deadline) {
        IOSleep(250);zornReport(false,false);
    }
    bool pass=__atomic_load_n(&zornCoordinatorDone,__ATOMIC_ACQUIRE) && !__atomic_load_n(&zornFailure,__ATOMIC_ACQUIRE);
    uint32_t beats[8],timers[8],ipis[8],tlb[8];
    for(unsigned id=0;id<8;++id){beats[id]=__atomic_load_n(&zornCoreBeats[id],__ATOMIC_ACQUIRE);timers[id]=__atomic_load_n(&armcpu_core_timer[id],__ATOMIC_RELAXED);ipis[id]=__atomic_load_n(&armcpu_core_sgi[id],__ATOMIC_RELAXED);tlb[id]=__atomic_load_n(&zornCoreTlb[id],__ATOMIC_ACQUIRE);}
    pass=pass && ZornSmpPolicy::complete(__atomic_load_n(&zornBound,__ATOMIC_ACQUIRE),beats,timers,ipis,tlb);
    for(unsigned id=0;id<8;++id)pass=pass &&
        __atomic_load_n(&zornRemapAck[id],__ATOMIC_ACQUIRE)==9 &&
        !__atomic_load_n(&zornRemapError[id],__ATOMIC_ACQUIRE);
    __atomic_store_n(&zornAbort,1U,__ATOMIC_RELEASE);
    __atomic_store_n(&zornPhase,pass?80U:90U,__ATOMIC_RELEASE);
    unsigned gui=0;PE_parse_boot_argn("zorn_smp_continue",&gui,sizeof(gui));
    if(pass && gui==1) {
        unsigned stop=0;PE_parse_boot_argn("zorn_smp_stop",&stop,sizeof(stop));
        if(stop==1) {
            zornReport(true,true); // full preflight passed; no root/Data publication
            panic("zorn SMP pass-stop recovery returned");
        }
        zornActiveCaptureHandles(); // optional diagnostics; original gates already passed
        zornReport(false,true);
        __atomic_store_n(&zorn_smp_preflight_active,0U,__ATOMIC_RELEASE);
        return true;
    }
    zornReport(true,pass);
    panic("zorn SMP recovery returned");
}
extern "C" int zorn_armcpu_preflight(void){return ArmCpu::zornPreflight();}
extern "C" int zorn_armcpu_runtime(char *text,unsigned capacity) {
    uint32_t timers=0,ipis=0,remap=0;
    for(unsigned id=0;id<8;++id) {
        if(__atomic_load_n(&armcpu_core_timer[id],__ATOMIC_RELAXED))timers|=1U<<id;
        if(__atomic_load_n(&armcpu_core_sgi[id],__ATOMIC_RELAXED))ipis|=1U<<id;
        if(__atomic_load_n(&zornRemapAck[id],__ATOMIC_ACQUIRE)==9 && !__atomic_load_n(&zornRemapError[id],__ATOMIC_ACQUIRE))remap|=1U<<id;
    }
    return snprintf(text,capacity,"SMP8 phase=%u seen=%x bound=%x remap=%x timers=%x ipis=%x failure=%u tlb=%u ",
        __atomic_load_n(&zornPhase,__ATOMIC_ACQUIRE),__atomic_load_n(&zornSeen,__ATOMIC_ACQUIRE),
        __atomic_load_n(&zornBound,__ATOMIC_ACQUIRE),remap,timers,ipis,
        __atomic_load_n(&zornFailure,__ATOMIC_ACQUIRE),__atomic_load_n(&zorn_smp_tlb_ready,__ATOMIC_ACQUIRE));
}
