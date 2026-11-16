/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuTablePreparation.h"
#ifndef ZORN_TABLE_PREPARE_COMPILE_ONLY
#define ZORN_TABLE_PREPARE_COMPILE_ONLY 0
#endif
#if ZORN_TABLE_PREPARE_COMPILE_ONLY != 0 && ZORN_TABLE_PREPARE_COMPILE_ONLY != 1
#error Invalid table prepare selector
#endif
bool ZornGpuTablePreparation::enter(){uint32_t zero=0;return __atomic_compare_exchange_n(&busy_,&zero,1,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);}
void ZornGpuTablePreparation::leave(){__atomic_store_n(&busy_,0,__ATOMIC_RELEASE);}
bool ZornGpuTablePreparation::separate(const void *p,size_t n,const void *q,size_t m){
 uintptr_t a=(uintptr_t)p,b=(uintptr_t)q;
 return p&&q&&n&&m&&a<=UINTPTR_MAX-(n-1)&&b<=UINTPTR_MAX-(m-1)&&(a>b?a-b>=m:b-a>=n);
}
bool ZornGpuTablePreparation::disjoint(const void *p,size_t n) const{return separate(p,n,this,sizeof(*this));}
bool ZornGpuTablePreparation::zeroState(const ArmSmmu4KLiveState *s){
 return !s->prepared&&!s->poisoned&&!s->generation&&!s->context_offset&&
  !s->tables.root_physical&&!s->tables.mair&&!s->tables.table_pages&&!s->tables.leaf_pages&&
  !s->tables.start_level&&!s->tables.upper_region;
}
void ZornGpuTablePreparation::retain(NativeAdrenoMemory *m,ArmSmmu4KLiveState *s,uint32_t error){
 report_.retained=1;if(!report_.adapter_error)report_.adapter_error=error;
 s->poisoned=1;m->quarantine();
}
int ZornGpuTablePreparation::prepare(NativeAdrenoMemory *memory,const Geometry *geometry,
 ArmSmmu4KLiveArena *arena,ArmSmmu4KLiveState *state,ArmSmmu4KLiveVisibility *out){
 if(!enter())return Busy;
 if(report_.attempted){leave();return Retained;}
 report_.attempted=1;
#if !ZORN_TABLE_PREPARE_COMPILE_ONLY
 (void)memory;(void)geometry;(void)arena;(void)state;(void)out;
 report_.adapter_error=Disabled;leave();return Disabled;
#else
 // Must query the ACTUAL publisher object code, not this TU's macro value.
 report_.publisher_mode_selected=publisher_.selectedMode();report_.publisher_mode_available=1;
 if(!report_.publisher_mode_selected){report_.adapter_error=ModeMismatch;leave();return ModeMismatch;}
 const void *args[]={memory,geometry,arena,state,out};
 const size_t sizes[]={sizeof(*memory),sizeof(*geometry),sizeof(*arena),sizeof(*state),sizeof(*out)};
 const size_t aligns[]={alignof(NativeAdrenoMemory),alignof(Geometry),alignof(ArmSmmu4KLiveArena),alignof(ArmSmmu4KLiveState),alignof(ArmSmmu4KLiveVisibility)};
 for(unsigned i=0;i<5;++i){
  if(!disjoint(args[i],sizes[i])||(uintptr_t)args[i]%aligns[i]){report_.adapter_error=Invalid;leave();return Invalid;}
  for(unsigned j=0;j<i;++j)if(!separate(args[i],sizes[i],args[j],sizes[j])){report_.adapter_error=Invalid;leave();return Invalid;}
 }
 if(out->cookie||out->publish_table_page||!zeroState(state)){report_.adapter_error=Invalid;leave();return Invalid;}
 // Protect caller metadata from the real writable table pool. Valid stable
 // native objects remain a precondition; these checks are not authentication.
 void *pool=memory->mapping();size_t poolbytes=memory->bytes();
 if(!pool||!poolbytes||!separate(this,sizeof(*this),pool,poolbytes)){report_.adapter_error=Invalid;leave();return Invalid;}
 for(unsigned i=0;i<5;++i)if(!separate(args[i],sizes[i],pool,poolbytes)){report_.adapter_error=Invalid;leave();return Invalid;}
 Geometry g=*geometry;
 report_.native_attempted=1;
 IOReturn native=NativeAdrenoPrepareSmmuMemory(memory,g.input_bits,g.output_bits,g.iova,g.bytes,g.upper,g.leaf_budget,arena,state,&legacy_);
 report_.native_return=native;report_.native_status_available=1;
 if(native!=kIOReturnSuccess){retain(memory,state,PrepareFailure);leave();return PrepareFailure;}
 // Even a successful preparation is only CPU table/ref bookkeeping. The
 // legacy callback stays private; no SMMU context or stream was established.
 if(!state->prepared||state->poisoned||!state->tables.table_pages||legacy_.cookie!=memory||!legacy_.publish_table_page){
  retain(memory,state,PrepareOutputInvalid);leave();return PrepareOutputInvalid;
 }
 ArmSmmu4KLiveVisibility fresh{};report_.bind_attempted=1;
 int bound=publisher_.bind(memory,&fresh);
 report_.bind_result=bound;report_.bind_result_available=1;
 if(bound!=ZornGpuTableVisibility::Ok||!fresh.cookie||!fresh.publish_table_page||state->poisoned){
  retain(memory,state,BindFailure);leave();return BindFailure;
 }
 *out=fresh;report_.callback_exported=1;leave();return Ok;
#endif
}
int ZornGpuTablePreparation::snapshot(Report *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(Report))return Invalid;
 if(!enter())return Busy;Report copy=report_;
 copy.legacy_callback_observed=copy.native_status_available;
 copy.legacy_callback_present=copy.native_status_available&&(legacy_.cookie||legacy_.publish_table_page);
 *out=copy;leave();return Ok;
}
int ZornGpuTablePreparation::snapshotPublisher(ZornGpuTableVisibility::Report *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(ZornGpuTableVisibility::Report))return Invalid;
 if(!enter())return Busy;int result=publisher_.snapshot(out);leave();return result;
}
