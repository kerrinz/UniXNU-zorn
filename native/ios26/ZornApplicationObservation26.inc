// SPDX-License-Identifier: MIT
// Diagnostic only; try-lock never waits and never influences native results.
#include "ZornMapGate222.h"
static unsigned appObservationGate,appObservationDropped;
static uintptr_t appObservationClient;
// Filter unrelated clients before the shared diagnostic lock. This is only a
// published observation identity; it never supplies native GPU authority.
static uintptr_t appObservationActiveClient;
static ZornApplicationObservation26 appObservation;
static bool appObservationLock(){unsigned zero=0;return __atomic_compare_exchange_n(&appObservationGate,&zero,1,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);}
static void appObservationUnlock(){__atomic_store_n(&appObservationGate,0,__ATOMIC_RELEASE);}
static void appObservationDrop(){__atomic_fetch_add(&appObservationDropped,1,__ATOMIC_RELAXED);}
static void appObservationRemember();
extern "C" int zorn26_application_observes_map222(uintptr_t client){
 if(!client || !appObservationLock())return 0;
 const bool take=client==appObservationClient && appObservation.unique &&
  appObservation.sessions && !appObservation.closeReturned &&
  (appObservation.flags&15u)==15u && appObservation.method==13 && !appObservation.raw;
 appObservationUnlock();return take?1:0;
}
static void appObservationBind(uintptr_t client,uint64_t unique,uint32_t pid){
 if(!client || !unique || !pid)return;
 if(!appObservationLock()){appObservationDrop();return;}
 // Diagnostics follow up to four sequential sessions of the same actual task.
 // This cannot grant or change native ownership, and never hides prior sessions.
 if(appObservation.sessions && (unique!=appObservation.unique || !appObservation.closeReturned || appObservation.closeRaw)){
  ++appObservation.sessionRejected;appObservationUnlock();return;
 }
 if(appObservation.sessions>=4){++appObservation.sessionRejected;appObservationUnlock();return;}
 appObservation.nativeReturn225={};
 appObservationClient=client;appObservation.unique=unique;appObservation.pid=pid;
 ++appObservation.sessions;appObservation.flags=1;appObservation.calls=0;appObservation.method=0;appObservation.raw=0;
 appObservation.closeReturned=0;appObservation.closeRaw=0;appObservation.prepareMask=0;
 appObservation.prepareStage=0;appObservation.prepareRaw=0;appObservation.prepareDetail=0;
 appObservation.prepareEvents=0;appObservation.prepareFailed=0;
 __atomic_store_n(&appObservationActiveClient,client,__ATOMIC_RELEASE);
 appObservationRemember();appObservationUnlock();
}
static void appObservationRemember(){
 if(!appObservation.sessions || appObservation.sessions>4)return;
 auto &h=appObservation.history[appObservation.sessions-1];
 h.flags=appObservation.flags;h.calls=appObservation.calls;h.method=appObservation.method;h.raw=appObservation.raw;
 h.closeReturned=appObservation.closeReturned;h.closeRaw=appObservation.closeRaw;
 h.prepareMask=appObservation.prepareMask;h.prepareStage=appObservation.prepareStage;h.prepareRaw=appObservation.prepareRaw;
 h.prepareDetail=appObservation.prepareDetail;h.prepareEvents=appObservation.prepareEvents;h.prepareFailed=appObservation.prepareFailed;
}
static void appObservationEvent(uintptr_t client,uint32_t flags,uint32_t method,uint32_t raw,bool closed=false){
 if(!client || client!=__atomic_load_n(&appObservationActiveClient,__ATOMIC_ACQUIRE))return;
 if(!appObservationLock()){appObservationDrop();return;}
 if(client==appObservationClient && appObservation.sessions && !appObservation.closeReturned){appObservation.flags|=flags;appObservation.method=method;appObservation.raw=raw;
  if(appObservation.calls<65535)++appObservation.calls;else appObservationDrop();
  if(closed){appObservation.closeReturned=1;appObservation.closeRaw=raw;
   __atomic_store_n(&appObservationActiveClient,uintptr_t(0),__ATOMIC_RELEASE);}appObservationRemember();}
 appObservationUnlock();
}
// Bounded software-only observation of actual preparation calls. Latch the
// first nonzero native result; later wrapper/close errors cannot replace it.
extern "C" void zorn26_application_prepare_event(uintptr_t client,uint32_t stage,uint32_t raw,uint32_t detail){
 if(!client || !stage || stage>=64)return;
 if(client!=__atomic_load_n(&appObservationActiveClient,__ATOMIC_ACQUIRE))return;
 if(!appObservationLock()){appObservationDrop();return;}
 if(client==appObservationClient && appObservation.sessions && !appObservation.closeReturned){
  if(appObservation.prepareEvents<128){
   ++appObservation.prepareEvents;appObservation.prepareMask|=UINT64_C(1)<<stage;
   if(!appObservation.prepareFailed){appObservation.prepareStage=stage;appObservation.prepareRaw=raw;
    appObservation.prepareDetail=detail;appObservation.prepareFailed=raw!=0;}
  }else appObservationDrop();
  appObservationRemember();
 }
 appObservationUnlock();
}
extern "C" int zorn26_application_snapshot(ZornApplicationObservation26 *out){
 if(!out || !appObservationLock())return 0;
 *out=appObservation;out->dropped=__atomic_load_n(&appObservationDropped,__ATOMIC_RELAXED);appObservationUnlock();return 1;
}
extern "C" int zorn26_application_stderr_reserve(uint64_t unique,uint32_t pid){
 if(!unique || !pid || !appObservationLock())return 0;
 if(appObservation.unique && unique!=appObservation.unique){appObservationDrop();appObservationUnlock();return 0;}
 if(!appObservation.reportUnique){appObservation.reportUnique=unique;appObservation.reportPid=pid;}
 const bool take=unique==appObservation.reportUnique && pid==appObservation.reportPid &&
  (!appObservation.unique || unique==appObservation.unique) && appObservation.attempts<256;
 if(take)++appObservation.attempts;else appObservationDrop();appObservationUnlock();return take;
}
extern "C" void zorn26_application_stderr_commit(uint64_t unique,const char *text,uint32_t bytes,int error){
 if(!appObservationLock()){appObservationDrop();return;}
 if(unique==appObservation.reportUnique && unique){
  if(error)++appObservation.copyErrors;
  else if(text && bytes>0 && bytes<sizeof(appObservation.text)){
   constexpr char prefix[]="ZORN193MTL run=65f3efb4a587473a9caebe54d7a99aea ";
   bool valid=bytes>=sizeof(prefix) && !memcmp(text,prefix,sizeof(prefix)-1) && text[bytes-1]=='\n';
   for(uint32_t i=0;i+1<bytes && valid;++i)if(text[i]<32 || text[i]>126)valid=false;
   if(valid){
    memcpy(appObservation.text,text,bytes);appObservation.text[bytes]=0;appObservation.bytes=bytes;++appObservation.lines;
    // A text terminal marker only controls observation timing, never GPU decisions.
    const char *body=text+sizeof(prefix)-1;
    if(!strncmp(body,"phase=11 ",9))appObservation.reportTerminal=1;
   }else {
    // Keep original context and most recent errors within the same fixed buffer.
    // The marker and rawDropped explicitly disclose omitted middle bytes.
    constexpr uint32_t capacity=sizeof(appObservation.rawText)-1,head=96;
    constexpr char omitted[]="\n...\n";
    constexpr uint32_t marker=sizeof(omitted)-1,tail=capacity-head-marker;
    static_assert(capacity==383 && tail==282);
    const uint32_t have=appObservation.rawBytes;
    if(bytes<=capacity-have){
     memcpy(appObservation.rawText+have,text,bytes);appObservation.rawBytes=have+bytes;
    }else {
     if(have<head){
      // Overflow guarantees enough incoming bytes to finish the original head.
      memcpy(appObservation.rawText+have,text,head-have);
     }
     if(bytes>=tail)memcpy(appObservation.rawText+head+marker,text+bytes-tail,tail);
     else {
      const uint32_t keep=tail-bytes;
      memmove(appObservation.rawText+head+marker,appObservation.rawText+have-keep,keep);
      memcpy(appObservation.rawText+head+marker+keep,text,bytes);
     }
     memcpy(appObservation.rawText+head,omitted,marker);appObservation.rawBytes=capacity;
    }
    appObservation.rawText[appObservation.rawBytes]=0;
    if(bytes>capacity-have || bytes==383)++appObservation.rawDropped;
   }
  }
 }
 appObservationUnlock();
}

extern "C" void zorn26_application_native_return225(uintptr_t client,uintptr_t request,uint32_t method,uint32_t stage,uint32_t raw){
 if(!client || !request)return;
 if(client!=__atomic_load_n(&appObservationActiveClient,__ATOMIC_ACQUIRE))return;
 if(!appObservationLock()){appObservationDrop();return;}
 if(client==appObservationClient && appObservation.sessions && !appObservation.closeReturned)
  if(stage==1 || appObservation.nativeReturn225.sequence)(void)zorn_native_return225_event(appObservation.nativeReturn225,request,method,stage,raw);
 appObservationUnlock();
}
