// Isolated candidate included after existing SMP static declarations.
// Snapshot handles only after the original complete preflight. GUI readers
// never dereference the board IOCPU objects, whose teardown is not our API.
static processor_t zornActiveHandles[8];
static volatile uint32_t zornActiveHandlesReady;
static bool zornActiveGates(bool final_preflight) {
    if(!final_preflight && __atomic_load_n(&zorn_smp_preflight_active,__ATOMIC_ACQUIRE)!=0)return false;
    return __atomic_load_n(&zornPhase,__ATOMIC_ACQUIRE)==80 &&
        __atomic_load_n(&zornCoordinatorDone,__ATOMIC_ACQUIRE)==1 &&
        __atomic_load_n(&zornBound,__ATOMIC_ACQUIRE)==255 &&
        __atomic_load_n(&zornSeen,__ATOMIC_ACQUIRE)==255 &&
        __atomic_load_n(&zornFailure,__ATOMIC_ACQUIRE)==0 &&
        __atomic_load_n(&zorn_smp_tlb_ready,__ATOMIC_ACQUIRE)==1;
}
static void zornActiveCaptureHandles(void) {
    if(__atomic_load_n(&zornActiveHandlesReady,__ATOMIC_ACQUIRE))return;
    unsigned enabled=0;
    PE_parse_boot_argn("zorn_cpu_active",&enabled,sizeof(enabled));
    if(enabled!=1 || !zornActiveGates(true))return;
    // Original preflight still owns live board references at this point.
    // No output table is visible unless all eight handles/IDs are valid.
    for(unsigned id=0;id<8;++id) {
        IOCPU *cpu=gZornCpus[id];
        if(!cpu || cpu->getCPUNumber()!=id)return;
        processor_t p=cpu->getMachProcessor();
        if(!p)return;
        for(unsigned previous=0;previous<id;++previous)if(zornActiveHandles[previous]==p)return;
        zornActiveHandles[id]=p;
    }
    __atomic_store_n(&zornActiveHandlesReady,1U,__ATOMIC_RELEASE);
    // Never reset or rewrite this per-boot table after release publication.
}
extern "C" int zorn_active_profile_ready(void) {
    return zornActiveGates(false) &&
        __atomic_load_n(&zornActiveHandlesReady,__ATOMIC_ACQUIRE)==1;
}
extern "C" int zorn_active_processor_handle(unsigned id,processor_t *out) {
    if(!out || id>=8 || !zorn_active_profile_ready())return 0;
    processor_t p=zornActiveHandles[id];
    if(!p)return 0;
    *out=p;return 1;
}
