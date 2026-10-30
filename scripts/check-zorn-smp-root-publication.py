#!/usr/bin/env python3
"""Exercise the real root preparation function without USB or cache instructions."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/smp/root-publication-host'
spec=importlib.util.spec_from_file_location('runtime',ROOT/'UniXNU-zorn/scripts/prepare-zorn-smp-runtime.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
s=(ROOT/'UniXNU-zorn/native/smp/ZornSmpRuntime.inc').read_text();a,b=m.span(s,'static __attribute__((noinline)) void zornPrepareCpuRoot');function=s[a:b]
prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <initializer_list>
#include <stdexcept>
uint64_t cpu_ttep=0x8c8931000ULL;
volatile uint64_t zornCpuRootBefore;
volatile uint32_t zornCpuRootPublish;
unsigned requested=0,cleanCalls=0;bool present=true;
bool PE_parse_boot_argn(const char *name,void *p,unsigned size){assert(!strcmp(name,"zorn_smp_root_publish") && size==sizeof(requested));if(present)memcpy(p,&requested,size);return present;}
void cleanToMemory(const void *p,size_t size){assert(p==&cpu_ttep && size==8);++cleanCalls;}
[[noreturn]] void panic(const char *s){throw std::runtime_error(s);}
'''
suffix=r'''
int main(){
 for(unsigned mode:{0U,1U}) {
  requested=mode;cleanCalls=0;zornCpuRootBefore=0;zornCpuRootPublish=99;
  zornPrepareCpuRoot();assert(cpu_ttep==0x8c8931000ULL && zornCpuRootBefore==cpu_ttep && zornCpuRootPublish==mode && cleanCalls==mode);
 }
 present=false;requested=1;cleanCalls=0;zornPrepareCpuRoot();assert(zornCpuRootPublish==0 && !cleanCalls);present=true;
 for(unsigned mode:{0U,1U,2U})for(uint64_t root:{uint64_t(0),uint64_t(1),uint64_t(0x8c8931001ULL),uint64_t(0x8c8931000ULL)}) {
  if(mode<2 && root==0x8c8931000ULL)continue;
  requested=mode;cpu_ttep=root;cleanCalls=0;bool rejected=false;
  try{zornPrepareCpuRoot();}catch(const std::runtime_error&){rejected=true;}
  assert(rejected && !cleanCalls && cpu_ttep==root);
 }
}
'''
OUT.mkdir(parents=True,exist_ok=True);p=OUT/'check.cpp';p.write_text(prefix+function+suffix)
subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(OUT/'check')],check=True)
subprocess.run([str(OUT/'check')],check=True)
r=dict(actual_prepare_sha256=hashlib.sha256(function.encode()).hexdigest(),asan_ubsan=True,default_control_zero=True,explicit_zero_never_cleans=True,explicit_one_only_static_root_8bytes=True,snapshot_before_worker=True,invalid_mode_zero_or_unaligned_root_rejected=True,root_value_never_written=True,hardware_qualified=False)
(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
