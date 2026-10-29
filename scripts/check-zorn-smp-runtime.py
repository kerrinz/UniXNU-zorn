#!/usr/bin/env python3
"""Host rejection checks for the explicit, pre-root eight-core profile."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/smp'
spec=importlib.util.spec_from_file_location('runtime',ROOT/'UniXNU-zorn/scripts/prepare-zorn-smp-runtime.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pins=json.loads((m.NATIVE/'runtime-source-pins.json').read_text())
profile=json.loads((m.OUT/'profile.json').read_text());assert profile['mode']=='preflight8'
for relative,record in pins.items():
    before=(m.OUT/'baseline'/relative).read_bytes();original=(m.TREE/'refer/xnu'/relative).read_bytes()
    assert m.sha(before)==record['before'] and m.sha(original)==record['original']
    desired=m.transform(relative,before,original)
    assert desired==(m.WORK/relative).read_bytes()
    assert m.sha(desired)==profile['files'][relative]['after']
    if relative.endswith('lock_rw.c') or relative.endswith('pmap_internal.h'):assert desired==original
    if relative.endswith('pmap.c'):
        for name in ('alloc_asid','pmap_destroy_internal'):
            a,b=m.span(desired.decode(),name);c,d=m.span(original.decode(),name)
            assert desired.decode()[a:b]==original.decode()[c:d]
    if relative.endswith('tlb.h'):
        assert desired.count(b'__atomic_load_n(&zorn_smp_tlb_ready')==6
source=r'''
#include <cassert>
#include "ZornSmpPolicy.h"
int main(){
 uint32_t beats[8],timers[8],ipis[8],tlb[8];
 for(unsigned i=0;i<8;++i){
  assert(ZornSmpPolicy::identity(i,ZornSmpPolicy::midr(i),i*0x100));
  assert(!ZornSmpPolicy::identity(i,0,i*0x100));
  assert(!ZornSmpPolicy::identity(i,ZornSmpPolicy::midr(i),(i^1)*0x100));
  beats[i]=10;timers[i]=ipis[i]=tlb[i]=1;
 }
 assert(!ZornSmpPolicy::identity(8,0x410fd821,0x800));
 assert(ZornSmpPolicy::complete(255,beats,timers,ipis,tlb));
 for(unsigned i=0;i<8;++i){
  assert(!ZornSmpPolicy::complete(255^(1<<i),beats,timers,ipis,tlb));
  --beats[i];assert(!ZornSmpPolicy::complete(255,beats,timers,ipis,tlb));++beats[i];
  timers[i]=0;assert(!ZornSmpPolicy::complete(255,beats,timers,ipis,tlb));timers[i]=1;
  ipis[i]=0;assert(!ZornSmpPolicy::complete(255,beats,timers,ipis,tlb));ipis[i]=1;
  tlb[i]=0;assert(!ZornSmpPolicy::complete(255,beats,timers,ipis,tlb));tlb[i]=1;
 }
}
'''
OUT.mkdir(parents=True,exist_ok=True);(OUT/'policy-check.cpp').write_text(source)
subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
    '-I',str(m.NATIVE),str(OUT/'policy-check.cpp'),'-o',str(OUT/'policy-check')],check=True)
subprocess.run([str(OUT/'policy-check')],check=True)
spec=importlib.util.spec_from_file_location('payload',ROOT/'uefi-zorn/scripts/make-zorn-payload.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
base=(ROOT/'out/zorn/kernel.macho.adt').read_bytes()
adt=p.trustcache_adt(base,omit_ramdisk=True,smp_preflight=8)
for bad in (dict(smp_preflight=2),dict(smp_preflight=8,packed_data=True),dict(smp_preflight=8,omit_ramdisk=False)):
    try:p.trustcache_adt(base,**bad)
    except ValueError:pass
    else:raise AssertionError('invalid profile accepted')
try:p.trustcache_adt(adt,omit_ramdisk=True,smp_preflight=8)
except ValueError:pass
else:raise AssertionError('existing multicore ADT accepted')
result=dict(profile_sha256=hashlib.sha256((m.OUT/'profile.json').read_bytes()).hexdigest(),
    source_profiles_pinned=True,original_rwlock_exact=True,original_asid_allocator=True,original_pmap_destroy=True,
    global_tlb_entrypoints=6,policy_missing_core_timer_ipi_tlb_rejected=True,policy_asan_ubsan=True,
    invalid_payload_modes_rejected=True,hardware_qualified=False)
(OUT/'runtime-host-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
