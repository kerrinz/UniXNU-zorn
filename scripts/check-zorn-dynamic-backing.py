#!/usr/bin/env python3
"""Bind dynamic allocation ownership semantics without an allocator double."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parents[2]
O=R/'out/zorn/gpu-dynamic-backing-contract'
P=R/'out/zorn/gpu-discovery-20261030'
S=P/'layout/adreno_gen7_hwsched_hfi.c'
EXPECTED='306930a131d0fa3bc3cc3873dbfaf205b6bd5a4243f55a74cced411c08de6782'
def function(s,name):
 m=re.search(r'(?:static )?(?:struct hfi_mem_alloc_entry \*|int |void )'+name+r'\([^;]*?\)\n\{.*?\n\}',s,re.S)
 if not m:raise ValueError('missing function '+name)
 return m[0]
def check(s):
 lookup=function(s,'lookup_mem_alloc_table');alloc=function(s,'get_mem_alloc_entry');process=function(s,'process_mem_alloc');reply=function(s,'mem_alloc_reply');reset=function(s,'reset_hfi_mem_records')
 for token in ['entry->desc.mem_kind == desc->mem_kind','entry->desc.gmu_mem_handle == desc->gmu_mem_handle']:
  if token not in lookup:raise ValueError('duplicate key')
 if 'entry->desc.size ==' in lookup:raise ValueError('source reuse semantics changed')
 if alloc.index('if (entry)')>alloc.index('if (desc->mem_kind >='):raise ValueError('reuse ordering')
 for token in ['memset(entry, 0, sizeof(*entry));','return ERR_PTR(ret);','hfi->mem_alloc_entries++;','HFI_MEMKIND_HW_FENCE','HFI_MEMKIND_MEMSTORE','gmu_import_buffer(adreno_dev, entry)']:
  if token not in alloc:raise ValueError('allocation branch '+token)
 fail=alloc[alloc.index('ret = gmu_import_buffer'):]
 if 'kgsl_free' in fail or 'live with' not in alloc:raise ValueError('import-failure retention semantics')
 if 'mad->host_mem_handle = mad->gmu_mem_handle;' not in process:raise ValueError('success handle publication')
 if reply.index('if (ret)')>reply.index('memcpy(&out.desc'):raise ValueError('reply after failure')
 if 'memset(md->hostptr, 0x0, md->size);' not in reset or 'free' in reset:raise ValueError('reset lifetime')
 return {n:function(s,n) for n in ['lookup_mem_alloc_table','get_mem_alloc_entry','process_mem_alloc','mem_alloc_reply','reset_hfi_mem_records']}
def main():
 if (O/'combined-result.json').exists():raise SystemExit('Completed; do not repeat')
 s=S.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 if sha(S)!=EXPECTED:raise ValueError('pinned reference changed')
 functions=check(s);negative=[]
 for name,a,b in [('key-handle','entry->desc.gmu_mem_handle == desc->gmu_mem_handle','entry->desc.gmu_mem_handle != desc->gmu_mem_handle'),('entry-count','hfi->mem_alloc_entries++;','/* missing publication count */'),('success-handle','mad->host_mem_handle = mad->gmu_mem_handle;','mad->host_mem_handle = 0;'),('reset-size','memset(md->hostptr, 0x0, md->size);','memset(md->hostptr, 0x0, 4);')]:
  if s.count(a)!=1:raise ValueError('ambiguous mutation '+name)
  bad=s.replace(a,b);(O/(name+'.c')).write_text(bad)
  try:check(bad)
  except ValueError as e:negative.append(dict(name=name,refused=str(e)))
  else:raise ValueError('mutation survived '+name)
 (O/'exact-consumer-functions.c').write_text('/* Pinned reference fragments, not compiled/executed. */\n'+'\n\n'.join(functions.values())+'\n')
 inputs={str(S):sha(S)}
 for f in [P/'layout/adreno_gen7_hwsched_hfi.h',P/'profile-reference/adreno_gen7_gmu.c',R/'UniXNU/drivers/NativeAdreno/NativeAdrenoMemory.h',R/'UniXNU/drivers/NativeAdreno/NativeAdrenoMemory.cpp']:
  inputs[str(f)]=sha(f)
 result=dict(state='dynamic-backing-consumer-ownership-contract-bound-native-provider-not-yet-implemented',inputs=inputs,reference_revision='453d8875f815bf9dfad9035982861226a4823a6c; reference not Xiaomi exact stock source',registry_capacity=32,duplicate_key=['mem_kind','gmu_mem_handle'],duplicate_size_flags_align_revalidation_in_reference=False,
  minimum_native_changes=['Reject key reuse with changed size/flags/align; explicit local stricter policy, not an OEM claim.','Persistent real NativeAdrenoMemory ownership per attempted allocation including uncounted/failed slots. Preserve raw allocation/import/gate errors separately; do not erase failure descriptor or retry.','Separate CPU backing from GPU-global/GMU-import/IPC/preallocated fence/memstore; no PA-as-IOVA, no invented domain or translation lease.','GMU import failure after GPU allocation must remain retained/quarantined; destructor must not release it.','HOST_INIT zeroing requires actual stopped/exclusive lifetime; reset is not free. Completion of HFI transport or ACK does not retire backing.'],
  native_API='Current upstream NativeAdrenoMemory::allocate/release/quarantine getters; no pool reservation, WC policy or device hold is selected.',
  missing_native_contracts=['Runtime consumer/caller serialization/epoch ownership','Actual GMU domain and GPU VA import rights','Preallocated HW_FENCE/MEMSTORE providers','Per-kind physical backing suitability and true stop/release proof'],
  new_semantic_refusals=negative,host_success_allocator_or_address_model=False,decoder_or_HFI_reply_changed=False,new_native_component_or_target=False,phone_or_provider_calls=0,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'combined-result.json').write_text(json.dumps(result,indent=2)+'\n');print('Dynamic lifecycle source bound;4 new semantic refusals;no allocator/address model or old suite repeated')
if __name__=='__main__':main()
