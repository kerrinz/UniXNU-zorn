/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuGmuRuntime.h"
#include <string.h>
bool ZornGpuGmuRuntime::enter(){uint32_t zero=0;return __atomic_compare_exchange_n(&busy_,&zero,1,false,__ATOMIC_ACQUIRE,__ATOMIC_RELAXED);}
void ZornGpuGmuRuntime::leave(){__atomic_store_n(&busy_,0,__ATOMIC_RELEASE);}
bool ZornGpuGmuRuntime::disjoint(const void *p,size_t n) const {
 uintptr_t a=(uintptr_t)p,b=(uintptr_t)this;
 return p&&n&&a<=UINTPTR_MAX-(n-1)&&b<=UINTPTR_MAX-(sizeof(*this)-1)&&
  (a>b?a-b>=sizeof(*this):b-a>=n);
}
int ZornGpuGmuRuntime::reserve(const ZGMemRequirement *request,uint32_t *index){
 if(!disjoint(request,sizeof(*request))||!disjoint(index,sizeof(*index))||
    (uintptr_t)request%alignof(ZGMemRequirement)||(uintptr_t)index%alignof(uint32_t))return Invalid;
 uintptr_t a=(uintptr_t)request,b=(uintptr_t)index;
 if(a>b?a-b<sizeof(*index):b-a<sizeof(*request))return Invalid;
 if(!enter())return Busy;
 ZGMemRequirement canonical{};
 // Reuse the existing parser/requirement validator; no additional wire codec.
 if(request->raw_count>11||ZGPlanMemAlloc(request->raw,request->raw_count,&canonical)!=ZG_OK||
    !canonical.format_available||canonical.runtime_complete||
    memcmp(&canonical,request,sizeof(canonical))){leave();return Invalid;}
 for(uint32_t i=0;i<count_;++i){const auto &old=slots_[i].requirement;
  if(old.kind!=canonical.kind||old.gmu_handle!=canonical.gmu_handle)continue;
  // Local stricter policy: every request word except the message header must
  // remain identical. Original raw addresses/handles stay private/untrusted.
  if(old.raw_count!=canonical.raw_count||memcmp(old.raw+1,canonical.raw+1,(old.raw_count-1)*4)){
   leave();return Conflict;
  }
  if(slots_[i].failed){leave();return Retained;}
  *index=i;leave();return Ok;
 }
 if(count_==32){leave();return Full;}
 uint32_t i=count_;slots_[i].requirement=canonical;++count_;*index=i;
 leave();return Ok;
}
int ZornGpuGmuRuntime::retainFailure(uint32_t index,int64_t error){
 if(!error)return Invalid;
 if(!enter())return Busy;
 if(index>=count_){leave();return Invalid;}
 if(slots_[index].failed){leave();return Retained;}
 retainGmuLocked(index,error);leave();return Ok;
}
int ZornGpuGmuRuntime::snapshot(Summary *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(Summary))return Invalid;
 if(!enter())return Busy;
 Summary s{};s.entries=count_;s.reserved_cpu_bytes=attempted_bytes_;
 for(uint32_t i=0;i<count_;++i){uint32_t bit=UINT32_C(1)<<i;s.reserved|=bit;s.unknown|=bit;if(slots_[i].failed)s.retained|=bit;
  if(cpu_[i].attempted)s.native_attempted|=bit;if(cpu_[i].backed)s.allocated|=bit;
  if(cpu_[i].native_status_available)s.native_status_available|=bit;}
 // Masks reflect returned CPU-native observations only; runtime_complete stays0.
 *out=s;leave();return Ok;
}
int ZornGpuGmuRuntime::copyFailure(uint32_t index,Failure *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(Failure))return Invalid;
 if(!enter())return Busy;
 if(index>=count_){leave();return Invalid;}
 Failure f{};f.available=slots_[index].adapter_available;f.adapter_error=slots_[index].error;f.native_status_available=cpu_[index].native_status_available;
 *out=f;leave();return Ok;
}

#ifndef ZGBR_CPU_PREPARE_COMPILE_ONLY
#define ZGBR_CPU_PREPARE_COMPILE_ONLY 0
#endif
#if ZGBR_CPU_PREPARE_COMPILE_ONLY != 0 && ZGBR_CPU_PREPARE_COMPILE_ONLY != 1
#error Invalid CPU prepare selector
#endif
// Policy concerns CPU backing only. It never supplies mapping/stop/DMA rights.
int ZornGpuGmuRuntime::checkCpuPolicy(const ZGMemRequirement *r,const CpuPolicy *p){
 if(!r||!p||(uintptr_t)r%alignof(ZGMemRequirement)||(uintptr_t)p%alignof(CpuPolicy))return Invalid;
 ZGMemRequirement q{};
 if(r->raw_count>11||ZGPlanMemAlloc(r->raw,r->raw_count,&q)!=ZG_OK||!q.format_available||memcmp(&q,r,sizeof(q)))return Invalid;
 bool width=p->output_bits==32||p->output_bits==36||p->output_bits==40||p->output_bits==42||p->output_bits==44||p->output_bits==48;
 // Initial local policy: generic host-accessible RAM, no supplied mappings,
 // 4K alignment only. All other resource classes remain unsupported.
 if(p->kind!=0||q.kind!=0||q.path!=ZG_PATH_GMU_RAM||
    !(q.flags&256)||(q.flags&~UINT32_C(768))||q.gpu_addr||q.gmu_addr||q.host_handle||
    q.va_alignment!=4096||q.size_alignment!=4096||!width||p->contiguous>1||p->reserved||
    !p->per_allocation_budget||p->per_allocation_budget>UINT64_C(268435456)||
    !p->total_budget||p->total_budget>UINT64_C(268435456)||
    q.rounded_size>p->per_allocation_budget||p->per_allocation_budget>p->total_budget)return Invalid;
 return Ok;
}
int ZornGpuGmuRuntime::prepareCpu(uint32_t index,const CpuPolicy *policy){
#if !ZGBR_CPU_PREPARE_COMPILE_ONLY
 (void)index;(void)policy;return Disabled;
#else
 if(!disjoint(policy,sizeof(*policy))||(uintptr_t)policy%alignof(CpuPolicy))return Invalid;
 if(!enter())return Busy;
 if(index>=count_){leave();return Invalid;}
 auto &slot=slots_[index];auto &report=cpu_[index];
 if(slot.failed||report.attempted){leave();return Retained;}
 CpuPolicy p=*policy;
 if(checkCpuPolicy(&slot.requirement,&p)!=Ok){leave();return Invalid;}
 uint64_t bytes=slot.requirement.rounded_size;
 if(attempted_bytes_>p.total_budget||bytes>p.total_budget-attempted_bytes_){leave();return Full;}
 // Reserve logical backing budget BEFORE calling the real native allocator.
 // Failed reservations are never recycled; IOKit auxiliary overhead is unknown.
 attempted_bytes_+=bytes;report.attempted=1;
 IOReturn native=memory_[index].allocate((size_t)bytes,p.output_bits,p.contiguous!=0,(size_t)p.per_allocation_budget,false);
 report.native_status=native;report.native_status_available=1;
 report.backed=memory_[index].backed();
 bool valid=native==kIOReturnSuccess&&report.backed&&!memory_[index].quarantined()&&
  memory_[index].bytes()==bytes&&memory_[index].spanCount()>0&&memory_[index].mapping()&&
  !memory_[index].deviceReferences();
 if(!valid){
  // Never replace the original native result with the adapter's assessment.
  slot.failed=1;memory_[index].quarantine();report.quarantined=1;
  if(native==kIOReturnSuccess){slot.error=BackingInvalid;slot.adapter_available=1;}
  leave();return native==kIOReturnSuccess?BackingInvalid:NativeFailure;
 }
 report.cpu_prepared=1;leave();return Ok;
#endif
}
int ZornGpuGmuRuntime::copyCpuReport(uint32_t index,CpuReport *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(CpuReport))return Invalid;
 if(!enter())return Busy;
 if(index>=count_){leave();return Invalid;}
 *out=cpu_[index];leave();return Ok;
}


#ifndef ZGGMU_RECORD_COMPILE_ONLY
#define ZGGMU_RECORD_COMPILE_ONLY 0
#endif
#if ZGGMU_RECORD_COMPILE_ONLY != 0 && ZGGMU_RECORD_COMPILE_ONLY != 1
#error Invalid GMU record selector
#endif
__attribute__((noinline)) bool ZornGpuGmuRuntime::compiledCpuPrepareSelected() const {
 return ZGBR_CPU_PREPARE_COMPILE_ONLY!=0;
}
void ZornGpuGmuRuntime::retainGmuLocked(uint32_t index,int64_t error){
 auto &slot=slots_[index];auto &report=gmu_[index];
 if(!slot.adapter_available){slot.error=error;slot.adapter_available=1;}slot.failed=1;
 if(!report.attempted)return;
 if(!report.adapter_available){report.adapter_error=error;report.adapter_available=1;}
 report.metadata_retained=1;
 if(report.local_index_available&&!report.retention_attempted){
  report.retention_attempted=1;
  int result=ledger_.retainFailure(report.local_index,error);
  report.retention_result=result;report.retention_result_available=1;
 }
}
int ZornGpuGmuRuntime::rememberGmu(uint32_t index,const GmuRequest *request){
#if !ZGGMU_RECORD_COMPILE_ONLY
 (void)index;(void)request;return Disabled;
#else
 // Query our actual CPU-prepare implementation's compiled configuration.
 // Both functions live in this TU; this is never hardware eligibility.
 if(!compiledCpuPrepareSelected())return GmuModeMismatch;
 if(!disjoint(request,sizeof(*request))||(uintptr_t)request%alignof(GmuRequest))return Invalid;
 if(!enter())return Busy;
 if(index>=count_){leave();return Invalid;}
 auto &slot=slots_[index];const auto &cpu=cpu_[index];auto &report=gmu_[index];
 if(slot.failed||report.attempted){leave();return Retained;}
 if(!cpu.attempted||!cpu.native_status_available||cpu.native_status!=kIOReturnSuccess||
  !cpu.backed||!cpu.cpu_prepared||cpu.quarantined){leave();return GmuNotPrepared;}
 // No native getter occurs before actual CPU success/prepared evidence above.
 report.attempted=1;uint64_t bytes=memory_[index].bytes();
 report.backing_bytes=bytes;report.backing_bytes_available=1;
 if(!memory_[index].backed()||memory_[index].quarantined()||!bytes||
  !memory_[index].mapping()||!memory_[index].spanCount()||memory_[index].deviceReferences()){
  retainGmuLocked(index,GmuBackingChanged);leave();return GmuBackingChanged;
 }
 ZornGpuGmuReservations::Reservation reservation{request->supplied_start,bytes,request->reservation_bytes};
 uint32_t local=0;report.ledger_attempted=1;
 int result=ledger_.remember(&slot.requirement,&memory_[index],&reservation,&local);
 report.ledger_result=result;report.ledger_result_available=1;
 if(result!=ZornGpuGmuReservations::Ok){retainGmuLocked(index,GmuRecordFailure);leave();return GmuRecordFailure;}
 report.local_index=local;report.local_index_available=1;
 // Owner gate -> private ledger only. Ledger cannot call back or expose refs.
 if(memory_[index].bytes()!=bytes||!memory_[index].backed()||memory_[index].quarantined()||memory_[index].deviceReferences()){
  retainGmuLocked(index,GmuBackingChanged);leave();return GmuBackingChanged;
 }
 leave();return Ok;
#endif
}
int ZornGpuGmuRuntime::copyGmuReport(uint32_t index,GmuReport *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(GmuReport))return Invalid;
 if(!enter())return Busy;
 if(index>=count_){leave();return Invalid;}
 *out=gmu_[index];leave();return Ok;
}
int ZornGpuGmuRuntime::copyGmuSummary(ZornGpuGmuReservations::Summary *out){
 if(!disjoint(out,sizeof(*out))||(uintptr_t)out%alignof(ZornGpuGmuReservations::Summary))return Invalid;
 if(!enter())return Busy;
 int result=ledger_.snapshot(out);leave();return result;
}
