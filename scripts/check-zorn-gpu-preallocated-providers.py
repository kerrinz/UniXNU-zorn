#!/usr/bin/env python3
"""Exact preallocated-provider source gaps, typed port barrier and pure AO status classification.

No HW fence/client/native provider, IRQ/MMIO callback or memory method executes.
"""
from pathlib import Path
import json,hashlib,re,subprocess,importlib.util,difflib,shlex
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-gen7-preallocated-providers';P=R/'out/zorn/gpu-discovery-20261030/profile-reference';S=R/'out/zorn/gpu-discovery-20261030/stock';H=R/'out/zorn/gpu-discovery-20261030/layout/adreno_gen7_hwsched_hfi.c';N=R/'UniXNU/drivers/NativeAdreno'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('extent_util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
def norm(s):return ' '.join(s.split())
def check_consumers(hfi,hwsched,kgsl,header):
 b=norm(util.body(hfi,'get_mem_alloc_entry'))
 assert 'if (!(desc->flags & HFI_MEMFLAG_GFX_ACC) && (desc->mem_kind != HFI_MEMKIND_HW_FENCE))' in b,'HW_FENCE special branch'
 assert 'case HFI_MEMKIND_HW_FENCE: entry->md = &adreno_dev->hwsched.hw_fence.memdesc;' in b,'external HW queue descriptor'
 assert 'case HFI_MEMKIND_MEMSTORE: entry->md = device->memstore;' in b,'device-global memstore descriptor'
 reg=norm(util.body(hwsched,'adreno_hwsched_register_hw_fence'))
 assert reg.index('if (!adreno_hwsched_context_queue_enabled(adreno_dev))')<reg.index('msm_hw_fence_register('),'context queue prerequisite'
 assert 'hw_fence->memdesc.physaddr = hw_fence->mem_descriptor.device_addr;' in reg,'borrow external descriptor, not ordinary BO'
 assert 'hw_fence->memdesc.size = hw_fence->mem_descriptor.size;' in reg and 'hw_fence->memdesc.hostptr = hw_fence->mem_descriptor.virtual_addr;' in reg
 assert 'PAGE_SIZE * 8' in kgsl,'Linux page-dependent memstore allocation size'
 assert 'void adreno_hwsched_deregister_hw_fence(struct adreno_device *adreno_dev);' in header,'deregister requires GPU owner, not opaque manager handle'
def main():
 if (O/'check-result.json').exists():raise SystemExit('completed; do not repeat')
 pins={}
 for manifest in ['primary-fetch.json','memstore-primary-fetch.json']:
  for e in json.loads((O/manifest).read_text()):
   assert e.get('status')==200,e
   p=O/e['name'];assert sha(p)==e['sha256'];pins[str(p)]=e['sha256']
 e=json.loads((O/'kgsl.h.fetch.json').read_text());assert e['status']==200 and sha(O/'kgsl.h')==e['sha256'];pins[str(O/'kgsl.h')]=e['sha256']
 manifest=json.loads((P/'manifest.json').read_text())['files'];e=next(e for e in manifest if e['name']=='adreno.c' and e.get('ok'));assert sha(P/'adreno.c')==e['sha256']
 macros=json.loads((S/'gmu-format-sources.json').read_text());e=next(e for e in macros if e['file']=='kgsl_gmu_core.h');assert sha(S/e['file'])==e['sha256'];pins[str(S/e['file'])]=e['sha256']
 old=json.loads((R/'out/zorn/gpu-dynamic-backing-contract/combined-result.json').read_text())['inputs'];assert sha(H)==old[str(H)]
 for p in [H,P/'adreno.c',P/'adreno_gen7_gmu.c',P/'adreno_gen7_gmu.h',N/'NativeAdrenoRing.h',N/'NativeAdrenoRing.cpp',N/'NativeAdrenoSubmit.h',N/'NativeAdrenoSubmit.cpp',N/'NativeAdrenoGmuContext.h',N/'NativeAdrenoIrq.h',N/'NativeAdrenoIrq.cpp']:pins[str(p)]=sha(p)
 (O/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
 hfi=H.read_text();hw=(O/'adreno_hwsched.c').read_text();kgsl=(O/'kgsl.h').read_text();header=(O/'adreno_hwsched.h').read_text();check_consumers(hfi,hw,kgsl,header);controls=[]
 for name,which,a,b in [('memstore-replaced-by-scratch','hfi','case HFI_MEMKIND_MEMSTORE:\n\t\tentry->md = device->memstore;','case HFI_MEMKIND_MEMSTORE:\n\t\tentry->md = device->scratch;'),('context-queue-gate-erased','hw','if (!adreno_hwsched_context_queue_enabled(adreno_dev))','if (false)'),('queue-address-field-substituted','hw','physaddr = hw_fence->mem_descriptor.device_addr;','physaddr = 0;'),('memstore-one-page','kgsl','PAGE_SIZE * 8','PAGE_SIZE * 1')]:
  values=dict(hfi=hfi,hw=hw,kgsl=kgsl);assert a in values[which];values[which]=values[which].replace(a,b)
  try:check_consumers(values['hfi'],values['hw'],values['kgsl'],header)
  except (AssertionError,ValueError) as e:controls.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('provider corruption survived '+name)
 # Actual known prototype, not a guessed DAL/private signature. Linux C permits
 # void* conversion; the C++ port barrier below deliberately rejects it.
 declaration='void adreno_hwsched_deregister_hw_fence(struct adreno_device *adreno_dev);';assert declaration in header
 badcall='adreno_hwsched_deregister_hw_fence(hwsched->hw_fence.handle);';assert hfi.count(badcall)==1
 candidate=hfi.replace(badcall,'adreno_hwsched_deregister_hw_fence(adreno_dev);');(O/'adreno_gen7_hwsched_hfi.c').write_text(candidate)
 patch=''.join(difflib.unified_diff(hfi.splitlines(True),candidate.splitlines(True),fromfile='a/vendor/qcom/opensource/graphics-kernel/adreno_gen7_hwsched_hfi.c',tofile='b/vendor/qcom/opensource/graphics-kernel/adreno_gen7_hwsched_hfi.c'));(O/'wrong-deregister-owner.UNAPPLIED.patch').write_text(patch)
 # Exact plain UAPI structure, without pretending the complete Linux driver
 # layout, kernel PAGE_SIZE or external HW-manager descriptor is now known.
 uapi=(O/'msm_kgsl.h').read_text();start=uapi.index('struct kgsl_devmemstore {');end=uapi.index('};',start)+2;structbody=uapi[start:end]
 (O/'kgsl_devmemstore.exact.inc').write_text(structbody+'\n')
 abi=O/'preallocated-port-ABI.cpp';abi.write_text('// SPDX-License-Identifier: GPL-2.0-only\n#include <stddef.h>\n#include "NativeAdrenoRing.h"\n#include "ZornGpuGmuAoStatus.h"\nstruct adreno_device;\n'+declaration+'\n'+structbody+'\nusing Deregister=void(*)(adreno_device*);\nstatic_assert(__is_same(decltype(&adreno_hwsched_deregister_hw_fence),Deregister));\nstatic_assert(sizeof(unsigned int)==4&&sizeof(kgsl_devmemstore)==40);\nstatic_assert(offsetof(kgsl_devmemstore,eoptimestamp)==8);\nstatic_assert(offsetof(kgsl_devmemstore,eoptimestamp)!=4);\nstatic_assert(sizeof(ZGGmuAoStatus)==24);\nextern "C" const unsigned zorn_preallocated_port_sizes[]={sizeof(kgsl_devmemstore),offsetof(kgsl_devmemstore,eoptimestamp),sizeof(NativeAdrenoRingCache),sizeof(ZGGmuAoStatus)};\n')
 # Source-domain barrier: AO handler/masks are distinct from native RBBM/CP.
 macros=(S/'kgsl_gmu_core.h').read_text();bits={name:int(re.search(r'#define\s+'+name+r'\s+BIT\((\d+)\)',macros).group(1)) for name in ['GMU_INT_WDOG_BITE','GMU_INT_FENCE_ERR','GMU_INT_HOST_AHB_BUS_ERR']};assert list(bits.values())==[0,3,5]
 gmu=(P/'adreno_gen7_gmu.c').read_text();handler=util.body(gmu,'gen7_gmu_irq_handler');assert 'GEN7_GMU_AO_HOST_INTERRUPT_STATUS' in handler and 'GEN7_GMU_AHB_FENCE_STATUS' in handler and 'status & ~GMU_AO_INT_MASK' in handler
 native_irq=(N/'NativeAdrenoIrq.cpp').read_text();assert 'IrqRbbmStatus = 0x0201' in native_irq and 'IrqBitCpFence = 1u << 20' in native_irq
 commands=[]
 def run(args,name,cwd=R,good=True):
  args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=args,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p.stdout+p.stderr
 flags=['-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(O)];source=(O/'ZornGpuGmuAoStatus.c').read_text()
 run(['clang',*flags,O/'ZornGpuGmuAoStatus.c',O/'test-ao-status.c','-o',O/'test-ao-status'],'AO-host-build');run([O/'test-ao-status'],'AO-host-run');neg=[]
 for name,a,b in [('watchdog-misclassified','watchdog=UINT32_C(1)<<0','watchdog=UINT32_C(1)<<1'),('named-unhandled-bits-lost','raw&~(watchdog|fence|ahb)','raw&~(watchdog|fence|ahb|UINT32_C(0x12))'),('auxiliary-fence-status-forged','raw&~(watchdog|fence|ahb),!!(raw&fence)','raw&~(watchdog|fence|ahb),0')]:
  assert source.count(a)==1;p=O/(name+'.c');p.write_text(source.replace(a,b));exe=O/name;run(['clang',*flags,p,O/'test-ao-status.c','-o',exe],name+'-build');run([exe],name+'-refused',good=False);neg.append(name)
 B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';recipes={};inputs=dict(pins);objects={}
 for kind,rel in [('c','bsd/DEVELOPMENT/bsd_init.o.json'),('cxx','iokit/DEVELOPMENT/IOPlatformExpert.cpo.json')]:
  p=B/rel;inputs[str(p)]=sha(p);recipes[kind]=json.JSONDecoder().raw_decode(p.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in recipes[kind]['arguments']
 for name,p,kind in [('AO-status',O/'ZornGpuGmuAoStatus.c','c'),('port-ABI',abi,'cxx')]:
  rec=recipes[kind];args=list(rec['arguments']);args[args.index(rec['file'])]=str(p);obj=O/(name+'.o');args[args.index('-o')+1]=str(obj);args+=['-I'+str(O),'-I'+str(N),'-mgeneral-regs-only'];run(args,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(args,name+'-independent',rec['directory']);assert sha(first)==sha(obj);objects[name]=sha(obj)
  assert '__mod_init_func' not in run(['otool','-l',obj],name+'-sections');imports=run(['nm','-u',obj],name+'-imports').split();assert not any('NativeAdreno' in n or 'adreno_hwsched' in n for n in imports)
  if name=='port-ABI':assert not imports
  run(['otool','-tvV',obj],name+'-disassembly')
  pp=[];i=0
  while i<len(args):
   if args[i] in ['-o','-MF','-MT','-MJ']:i+=2
   elif args[i]=='-c':i+=1
   else:pp.append(args[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',str(dep),'-MT','input'],name+'-deps',rec['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(rec['directory'])/p
   inputs[str(p)]=sha(p)
 bad=O/'wrong-opaque-owner.cpp';bad.write_text('struct adreno_device;\n'+declaration+'\nvoid bad_port(void *manager_handle){adreno_hwsched_deregister_hw_fence(manager_handle);}\n');rec=recipes['cxx'];args=list(rec['arguments']);args[args.index(rec['file'])]=str(bad);args[args.index('-o')+1]=str(O/'wrong-opaque-owner.o');run(args,'opaque-owner-CXX-refused',rec['directory'],good=False)
 for p,h in pins.items():assert sha(Path(p))==h,p
 (O/'check-result.json').write_text(json.dumps(dict(commands=commands,inputs=inputs,objects=objects,new_provider_semantic_corruptions_refused=controls,new_AO_actual_source_negatives=neg,wrong_opaque_owner_CXX_port_compile_refused=True,original_Linux_C_void_pointer_conversion_not_claimed_to_fail=True,wrong_owner_patch_unapplied=True,actual_native_preallocated_provider_unavailable=True,borrowed_resource_adapter_not_created=True,independent_AO_masks=bits,AO_scalar_classification_not_native_observation=True,no_new_IRQ_handler_MMIO_ACK_or_fence_completion=True,no_native_getter_allocator_provider_callback_phone_calls=True,no_successful_backing_address_handle_fence_model=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('Preallocated owner/type gap bound;4 provider source/3 pure AO source corruptions +1 C++ port refusal;2 independent iOS17 objects;no native adapter/calls')
if __name__=='__main__':main()
