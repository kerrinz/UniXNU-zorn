// SPDX-License-Identifier: BSD-2-Clause-Patent
// Included by the actual UFS/CDC owner after its retained progress state exists.
// CPU snapshots only:permission for this separate synthetic UI scene,never
// authority to stop DMA,reset the GPU or release any native resource.
extern "C" bool zorn26_ui_scene_gpu_ready269() {
    if(__atomic_load_n(&zornProgress201.state,__ATOMIC_ACQUIRE)!=3 ||
       __atomic_load_n(&zornProgress201.result,__ATOMIC_RELAXED)!=88 ||
       __atomic_load_n(&zornProgress201.gate.failed,__ATOMIC_ACQUIRE) ||
       __atomic_load_n(&zornCallbackGate222.failed,__ATOMIC_ACQUIRE))return false;
    // Same source-defined retained initial-task fields as known-task266. This
    // is a frozen startup result,not a later global DMA-stop observation.
    uint32_t k[32]{};zorn26_native_known_image_observation(k);
    if(k[0] || k[1]!=6 || (k[2]&63u)!=63u || k[3] || k[4]!=k[5] ||
       !k[6] || k[6]!=k[7] || k[8] || k[9] || k[10] || k[11] || k[12] ||
       k[15]!=0xe843b26au || k[16]!=UINT32_MAX || k[17] || k[18] ||
       k[19]!=k[20] || (k[21]&(1u<<23)) || (k[22]&~1u) || k[23] ||
       k[24]!=127 || k[31])return false;
    // The actual journal API requires non-null output and capacity. Reading
    // one byte at cursor0 does not advance the CDC consumer's separate cursor.
    uint8_t byte=0;ZornJournalSnapshot248 journal{};
    if(!zorn26_journal_snapshot248(0,&byte,1,&journal) || !journal.unique || !journal.pid ||
       !journal.records || !journal.published || journal.seen_bytes!=journal.published ||
       journal.reserved!=journal.published || journal.pending || journal.gaps ||
       journal.exited!=1 || journal.exit_status)return false;
    // This exact root selects only the fixed267 probe,which opens four native
    // clients. Desktop-GPU policies require their own prospective scene gate.
    uint64_t ids[4]{};
    for(unsigned i=0;i<4;++i) {
        ZornClientFailure261 client{};
        if(!zorn_failure_snapshot261(2u+3u*i,&client) || client.records!=4 ||
           !client.id || client.unique!=journal.unique || client.pid!=journal.pid ||
           !(client.flags&ZornFailureRegistered261) || !(client.flags&ZornFailureClosed261) ||
           (client.flags&(ZornFailureScope261|ZornFailureCloseFailed261)) ||
           !client.calls || client.failure.sequence || client.dropped || client.recycled ||
           client.closeStage!=ZornFailureCloseReturn261 || client.closeRaw)return false;
        for(unsigned j=0;j<i;++j)if(ids[j]==client.id)return false;
        ids[i]=client.id;
    }
    return true;
}
