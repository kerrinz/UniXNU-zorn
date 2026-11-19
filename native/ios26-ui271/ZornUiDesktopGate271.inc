// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornDesktopIdentity271.h"
// Synthetic-input admission only. CPU metadata never stops DMA or authorizes
// native release/reset. A live compositor cannot use269's probe-exit gate.
extern "C" bool zorn26_ui_desktop_ready271() {
    if(__atomic_load_n(&zornProgress201.state,__ATOMIC_ACQUIRE)!=3 ||
       __atomic_load_n(&zornProgress201.result,__ATOMIC_RELAXED)!=88 ||
       __atomic_load_n(&zornProgress201.gate.failed,__ATOMIC_ACQUIRE) ||
       __atomic_load_n(&zornCallbackGate222.failed,__ATOMIC_ACQUIRE))return false;
    // Exact retained266 initial known-task contract;not later DMA-stop proof.
    uint32_t k[32]{};zorn26_native_known_image_observation(k);
    if(k[0] || k[1]!=6 || (k[2]&63u)!=63u || k[3] || k[4]!=k[5] ||
       !k[6] || k[6]!=k[7] || k[8] || k[9] || k[10] || k[11] || k[12] ||
       k[15]!=0xe843b26au || k[16]!=UINT32_MAX || k[17] || k[18] ||
       k[19]!=k[20] || (k[21]&(1u<<23)) || (k[22]&~1u) || k[23] ||
       k[24]!=127 || k[31])return false;
    uint64_t unique=0;uint32_t pid=0;
    if(!zorn26_desktop_identity271(&unique,&pid))return false;
    ZornApplicationObservation26 app{};
    if(!zorn26_application_snapshot(&app) || app.unique!=unique || app.pid!=pid ||
       (app.flags&15u)!=15u || !app.calls || app.closeReturned ||
       app.prepareFailed || app.dropped)return false;
    uint32_t p[16]{};
    // Exact245 actual presenter:lease2 alone also occurs for CPU surfaces.
    // Require the surface's real GPU access fence and completed ledger/copy.
    if(!zorn26_present_snapshot245(p) || p[0]!=2 || p[1]<64 || !p[2] ||
       p[3]!=2 || !p[4] || p[4]!=p[5] || p[2]>p[5] || !p[6] || !p[7] ||
       p[8]!=1 || p[9]!=1 || p[10]!=1 || p[12]!=p[11]+1u ||
       !p[13] || p[13]>16384 || !p[14] || p[14]>16384 ||
       !p[15] || p[15]>p[5])return false;
    ZornClientFailure261 first{};
    if(!zorn_failure_snapshot261(2,&first) || !first.records ||
       first.records>ZornFailureSlots261)return false;
    const uint32_t count=first.records,recycled=first.recycled;bool live=false;
    uint64_t ids[ZornFailureSlots261]{};
    for(unsigned i=0;i<count;++i){
        ZornClientFailure261 c{};
        if(!zorn_failure_snapshot261(2u+3u*i,&c) || c.records!=count ||
           c.recycled!=recycled || c.dropped || !c.id || c.unique!=unique || c.pid!=pid ||
           !(c.flags&ZornFailureRegistered261) || c.failure.sequence ||
           (c.flags&ZornFailureCloseFailed261))return false;
        for(unsigned j=0;j<i;++j)if(ids[j]==c.id)return false;
        ids[i]=c.id;
        if((c.flags&ZornFailureClosed261) &&
           (c.closeStage!=ZornFailureCloseReturn261 || c.closeRaw))return false;
        if(c.calls && !(c.flags&(ZornFailureClosing261|ZornFailureClosed261)))live=true;
    }
    // Active Scope is a normal serialized method,not a backend failure.
    // Capability rejects remain visible but do not impersonate backend errors.
    return live;
}
