#!/usr/bin/env python3
"""Exercise the actual failure reporter with mocked PSCI and static memory; no USB."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'out/zorn/smp/startup-report-host'
spec = importlib.util.spec_from_file_location('runtime', ROOT / 'UniXNU-zorn/scripts/prepare-zorn-smp-runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
text = (ROOT / 'UniXNU-zorn/native/smp/ZornSmpRuntime.inc').read_text()
a, b = runtime.span(text, 'void ArmCpu::zornReport')
function = text[a:b]
prefix = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
using vm_offset_t=uintptr_t;
struct ArmCpu {
 unsigned id;
 uint64_t signalTarget() const {return uint64_t(id)*256;}
 static void zornReport(bool,bool);
};
ArmCpu peers[8],*gZornCpus[8];
unsigned gui=1,calls=0;bool conduit=true,lastHvc=false;
unsigned traceCalls=0;
void zornTraceRead(unsigned id,uint64_t out[6]) {
 assert(id<8);++traceCalls;for(unsigned n=0;n<6;++n)out[n]=UINT64_MAX;
}
int64_t answer=0;uint64_t lastFid=0,lastAffinity=0;
volatile uint32_t zornPhase=90,zornSeen=1,zornBound=0,zornFailure=261,zorn_smp_tlb_ready=1;
volatile uint32_t armcpu_smp_step[8],armcpu_smp_fail[8],armcpu_core_timer[8],armcpu_core_sgi[8];
volatile int32_t armcpu_smp_psci_rc[8];
volatile uint32_t zornCoreBeats[8],zornCoreTlb[8],zornRemapAck[8],zornRemapError[8];
volatile uint64_t zornCoreMidr[8],zornCoreMpidr[8],zornCoreSys[8][4],zornRemapObserved[8];
uint64_t cpu_ttep=0x8c1234000ULL;
volatile uint64_t zornCpuRootBefore=UINT64_MAX;
volatile uint32_t zornCpuRootPublish=1;
char LowResetVectorBase[32]={},start_cpu[32]={},ResetHandlerData[32]={},const_boot_args[32]={},CpuDataEntries[128]={};
alignas(4096) char cpuData[8][4096]={};
std::string output;
bool PE_parse_boot_argn(const char *name,void *p,unsigned n) {
 assert(!strcmp(name,"zorn_smp_continue") && n==sizeof(gui));memcpy(p,&gui,n);return true;
}
bool psciConduit(bool *hvc){*hvc=false;return conduit;}
int64_t psciCall(bool hvc,uint64_t fid,uint64_t aff,uint64_t level,uint64_t zero) {
 ++calls;lastHvc=hvc;lastFid=fid;lastAffinity=aff;
 assert(fid==0xc4000004ULL && level==0 && zero==0);return answer;
}
vm_offset_t ml_static_vtop(vm_offset_t p){return p;}
vm_offset_t ml_vtophys(vm_offset_t p) {
 uintptr_t base=reinterpret_cast<uintptr_t>(cpuData);
 return p>=base && p<base+sizeof(cpuData)?p:0;
}
void panic(const char *s){throw std::runtime_error(s);}
void zorn_ufs_smp_record(const char *p,unsigned n,int) {
 assert(n>0 && n<2400 && (!gui || n<=800));output.assign(p,n);
}
'''
suffix = r'''
int main() {
 for(unsigned i=0;i<8;++i) {
  peers[i].id=i;gZornCpus[i]=&peers[i];armcpu_smp_step[i]=4;
  zornCoreMidr[i]=0x410fd801;zornCoreMpidr[i]=0x81000000+i*256;
  armcpu_core_timer[i]=armcpu_core_sgi[i]=zornCoreBeats[i]=zornRemapAck[i]=UINT32_MAX;
  uint64_t pointer=reinterpret_cast<uintptr_t>(cpuData[i]),handler=0x8c780000cULL;
  memcpy(CpuDataEntries+i*16,&pointer,8);memcpy(CpuDataEntries+i*16+8,&pointer,8);
  memcpy(cpuData[i]+168,&handler,8);unsigned physical=i*256;memcpy(cpuData[i]+440,&physical,4);
 }
 // Successful or still-in-progress reports must never call firmware queries.
 zornFailure=0;ArmCpu::zornReport(true,true);
 assert(!calls && traceCalls==1 && output.find("AI=")==std::string::npos);
 assert(output.find("K=8c1234000/")!=std::string::npos && output.find("T1=")!=std::string::npos);
 // Realistic maximum trace words must retain all eight qualification records.
 for(unsigned i=0;i<8;++i) {
  armcpu_core_timer[i]=i?20:2032;armcpu_core_sgi[i]=i?23:85;
  zornCoreBeats[i]=10;zornRemapAck[i]=9;zornRemapError[i]=0;
 }
 ArmCpu::zornReport(true,true);assert(!calls && traceCalls==2);
 for(unsigned i=0;i<8;++i) {
  auto begin=output.find("C"+std::to_string(i)+" t="),end=output.find(";",begin);
  assert(begin!=std::string::npos && end!=std::string::npos);
  assert(output.substr(begin,end-begin).find("r=9 e=0")!=std::string::npos);
 }
 unsigned tracesBefore=traceCalls;ArmCpu::zornReport(false,true);
 assert(!calls && traceCalls==tracesBefore && output.find("T1=")==std::string::npos);
 assert(output.find("C0 m=")!=std::string::npos);
 // Restore extreme counter coverage for the failure footer tests.
 for(unsigned i=0;i<8;++i)armcpu_core_timer[i]=armcpu_core_sgi[i]=zornCoreBeats[i]=zornRemapAck[i]=UINT32_MAX;
 traceCalls=0;
 zornFailure=261;ArmCpu::zornReport(false,false);assert(!calls && !traceCalls && output.find("AI=")==std::string::npos);
 gui=0;ArmCpu::zornReport(true,false);assert(!calls && !traceCalls);gui=1;
 for(unsigned failure:{259U,268U}) {zornFailure=failure;ArmCpu::zornReport(true,false);assert(!calls);}
 for(unsigned id=0;id<8;++id) {
  zornFailure=260+id;unsigned before=calls;answer=id%3;
  ArmCpu::zornReport(true,false);
  assert(calls==before+1 && !lastHvc && lastAffinity==uint64_t(id)*256);
  assert(output.find("START"+std::to_string(id)+" step=4 rc=0 fail=0")!=std::string::npos);
  assert(output.find("AI="+std::to_string(answer)+" ")!=std::string::npos);
  assert(output.find("K=8c1234000/")!=std::string::npos);
  assert(output.find("H=8c780000c ")!=std::string::npos && output.find(" Q=1 ")!=std::string::npos);
 }
 for(int64_t error:{-1LL,-2LL,-6LL}) {
  answer=error;ArmCpu::zornReport(true,false);
  assert(output.find("AI="+std::to_string(error)+" ")!=std::string::npos);
 }
 conduit=false;unsigned before=calls;ArmCpu::zornReport(true,false);
 assert(calls==before && output.find("AI=-1001 ")!=std::string::npos);
 conduit=true;gZornCpus[7]=nullptr;before=calls;ArmCpu::zornReport(true,false);
 assert(calls==before && output.find("AI=")==std::string::npos);
 gZornCpus[7]=&peers[7];uint64_t invalid=1;memcpy(CpuDataEntries+7*16+8,&invalid,8);
 ArmCpu::zornReport(true,false);assert(output.find("H=0 P=0 Q=0 ")!=std::string::npos);
}
'''
OUT.mkdir(parents=True, exist_ok=True)
source = OUT / 'check.cpp'
source.write_text(prefix + function + suffix)
subprocess.run(['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', str(source), '-o', str(OUT / 'check')], check=True)
subprocess.run([str(OUT / 'check')], check=True)
result = dict(actual_report_sha256=hashlib.sha256(function.encode()).hexdigest(),
              asan_ubsan=True, successful_and_nonfinal_reports_never_query=True,
              successful_final_reports_local_cpu1_snapshot=True,
              nonfinal_reports_never_trace=True, normal_eight_core_records_fit_budget=True,
              only_affinity_info64_queried=True, all_eight_affinities=True,
              negative_psci_errors_preserved=True, missing_conduit_and_peer_bounded=True,
              invalid_cpu_data_pair_never_dereferenced=True,
              existing_800_byte_gui_budget=True, hardware_qualified=False)
(OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
