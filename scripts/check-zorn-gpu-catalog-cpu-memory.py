#!/usr/bin/env python3
"""Main-pinned CPU allocation variant,real types/objects only;no native invocation."""
from pathlib import Path
import hashlib,importlib.util,json,re,shlex,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-cpu-memory';P=R/'out/zorn/gpu-catalog-service-dependencies';N=P/'Adreno740';B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
VARIANTS=[('ZornGpuCatalogBackings','ZornGpuRuntimeBackings',R/'UniXNU-zorn/native/gpu-owned/runtime'),('ZornGpuCatalogGmuRuntime','ZornGpuGmuRuntime',R/'UniXNU-zorn/native/gpu-owned/runtime/gmu/composition')]
def source_check(name,oldname,parent,text=None):
 s=text if text is not None else (O/(name+'.cpp')).read_text();old=(parent/(oldname+'.cpp')).read_text()
 restored=s.replace(name,oldname).replace('memory_[index].allocate((size_t)bytes,p.output_bits,p.contiguous!=0,(size_t)p.per_allocation_budget)','memory_[index].allocate((size_t)bytes,p.output_bits,p.contiguous!=0,(size_t)p.per_allocation_budget,false)')
 assert restored==old,'policy/retention/config body changed beyond new catalog arity'
 assert s.count('.allocate(')==1 and '.allocateSystem(' not in s and '.importTask(' not in s and '.borrow(' not in s
 body=util.body(s,name+'::prepareCpu');assert body.index('attempted_bytes_+=bytes;report.attempted=1;')<body.index('.allocate(')<body.index('report.native_status=native;report.native_status_available=1;')
 assert 'if(native==kIOReturnSuccess){slot.error=BackingInvalid;slot.adapter_available=1;}' in body
 assert 'slot.failed=1;memory_[index].quarantine();report.quarantined=1;' in body and '.release(' not in s
 header=(O/(name+'.h')).read_text().replace(name,oldname).replace('ZORN_GPU_CATALOG_BACKINGS_H','ZORN_GPU_RUNTIME_BACKINGS_H').replace('ZORN_GPU_CATALOG_GMU_RUNTIME_H','ZORN_GPU_GMU_RUNTIME_H')
 assert header==(parent/(oldname+'.h')).read_text()

def provider_check(source,cpu):
 a=util.body(source,'NativeAdrenoMemory::allocate');segments=util.body(source,'NativeAdrenoMemory::takeSegments');release=util.body(source,'NativeAdrenoMemory::release')
 assert '!bytes || (bytes&4095) || !outputWidth(bits) || !budget' in a and 'if(bytes>budget)return kIOReturnNoResources;' in a
 assert a.index('NativeAdrenoQueryCpu4K(&cpu)')<a.index('inTaskWithPhysicalMask')<a.index('descriptor_->prepare()')<a.index('takeSegments(')<a.index('bzero(mapping_,bytes)')<a.index('NativeAdrenoMaintainOwnedPages')<a.index('noteOwned(spans_,span_count_,true);owned_=true;')
 assert '(void)release();return status;' in a and 'return kIOReturnSuccess;' in a
 assert 'physical>=limit || 4096>limit-physical' in segments and 'contiguous && offset && physical!=spans_[0].physical+offset' in segments
 assert 'if(status!=kIOReturnSuccess) {quarantined_=true;return status;}' in release
 assert 'descriptor_->complete()' in release and release.index('descriptor_->complete()')<release.index('descriptor_->release()')
 q=util.body(cpu,'NativeAdrenoQueryCpu4K');assert 'PAGE_SIZE==4096' in q and 'out->kernel_map_page_bytes==4096' in q
 m=util.body(cpu,'maintainOwnedPages');assert 'end-address>64*4096' in m and 'line>4096' in m and 'enable_preemption();return kIOReturnUnsupported;' in m
 assert 'if(!ownedBits && !tried)' in source and 'if(!bits)return;' in util.body(source,'noteOwned')

def main():
 if (O/'compile-result.json').exists():raise SystemExit('complete;do not repeat')
 pins=json.loads((O/'source-pins.json').read_text())
 for n,h in pins.items():assert sha(Path(n))==h,n
 for name,old,parent in VARIANTS:source_check(name,old,parent)
 mem=(N/'NativeAdrenoMemory.cpp').read_text();cpu=(N/'NativeAdrenoCpu.cpp').read_text();provider_check(mem,cpu)
 neg=[]
 name,old,parent=VARIANTS[0];s=(O/(name+'.cpp')).read_text()
 for label,a,b in [('caller-native-cap-lost','p->per_allocation_budget>UINT64_C(268435456)','p->per_allocation_budget>UINT64_MAX'),('native-raw-status-folded','report.native_status=native;','report.native_status=native?1:0;')]:
  assert a in s
  try:source_check(name,old,parent,s.replace(a,b))
  except AssertionError as e:neg.append(dict(name=label,refused=str(e)))
  else:raise RuntimeError('new source mutation accepted '+label)
 commands=[]
 def run(args,name,cwd=R,good=True):
  args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=args,directory=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  return p
 recipes={};inputs={};objects={};builds={}
 for key,rel in [('cxx','iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'),('c','bsd/DEVELOPMENT/bsd_init.o.json')]:
  p=B/rel;inputs[str(p)]=sha(p);recipes[key]=json.JSONDecoder().raw_decode(p.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in recipes[key]['arguments']
 abi=O/'catalog-memory-ABI.cpp';abi.write_text('''/* SPDX-License-Identifier: BSD-2-Clause-Patent;no runtime invocation. */
#include "ZornGpuCatalogBackings.h"
#include "ZornGpuCatalogGmuRuntime.h"
using Allocate=IOReturn(NativeAdrenoMemory::*)(size_t,unsigned,bool,size_t);
static_assert(__is_same(decltype(&NativeAdrenoMemory::allocate),Allocate));
static_assert(__is_same(decltype(&NativeAdrenoMemory::bytes),size_t(NativeAdrenoMemory::*)() const));
static_assert(__is_same(decltype(&NativeAdrenoMemory::deviceReferences),uint32_t(NativeAdrenoMemory::*)() const));
static_assert(sizeof(IOReturn)==4 && sizeof(int64_t)==8);
static_assert(sizeof(ZornGpuCatalogBackings::CpuReport)==28);
static_assert(sizeof(ZornGpuCatalogBackings::Failure)==16);
namespace { [[maybe_unused]] constinit ZornGpuCatalogBackings catalog_cpu_owner;
[[maybe_unused]] constinit ZornGpuCatalogGmuRuntime catalog_gmu_owner; }
extern "C" const unsigned catalog_cpu_sizes[]={sizeof(NativeAdrenoMemory),sizeof(ZornGpuCatalogBackings),sizeof(ZornGpuCatalogGmuRuntime),sizeof(ZornGpuCatalogBackings::CpuReport)};
''')
 includes=['-I'+str(O),'-I'+str(N),*['-I'+str(P/'catalog-headers'/k) for k in ['ArmSmmu4K','AdrenoFirmware','AdrenoPM4']]]
 entries=[('registry-off',O/'ZornGpuCatalogBackings.cpp','cxx',[]),('registry-selected',O/'ZornGpuCatalogBackings.cpp','cxx',['-DZGBR_CPU_PREPARE_COMPILE_ONLY=1']),('composition-off',O/'ZornGpuCatalogGmuRuntime.cpp','cxx',[]),('composition-selected',O/'ZornGpuCatalogGmuRuntime.cpp','cxx',['-DZGBR_CPU_PREPARE_COMPILE_ONLY=1','-DZGGMU_RECORD_COMPILE_ONLY=1']),('current-memory',N/'NativeAdrenoMemory.cpp','cxx',[]),('current-cpu',N/'NativeAdrenoCpu.cpp','cxx',[]),('planner',O/'ZornGpuStartupPlan.c','c',[]),('extent',O/'ZornGpuGmuExtent.c','c',[]),('ledger',O/'ZornGpuGmuReservations.cpp','cxx',[]),('ABI',abi,'cxx',[])]
 for name,src,kind,flags in entries:
  rec=recipes[kind];args=list(rec['arguments']);args[args.index(rec['file'])]=str(src);obj=O/(name+'.o');args[args.index('-o')+1]=str(obj);args+=includes+['-mgeneral-regs-only']+flags
  if name=='ABI':args+=['-Xclang','-fdump-record-layouts']
  run(args,name+'-first',rec['directory']);copy=O/(name+'-first.o');copy.write_bytes(obj.read_bytes());run(args,name+'-independent',rec['directory']);assert sha(copy)==sha(obj)
  objects[name]=dict(source=str(src),source_sha256=sha(src),object_sha256=sha(obj),independent_raw_SHA_equal=True);builds[name]=args
  imports=run(['nm','-u',obj],name+'-imports').stdout.split();sections=run(['otool','-l',obj],name+'-sections').stdout;assert '__mod_init_func' not in sections
  run(['otool','-tvV',obj],name+'-disassembly');run(['otool','-rv',obj],name+'-relocations')
  if name.endswith('-off'):assert not any('allocate' in n for n in imports),name
  if name=='ABI':assert not imports
  pp=[];i=0
  while i<len(args):
   if args[i] in ['-o','-MF','-MJ','-MT']:i+=2
   elif args[i]=='-c':i+=1
   elif args[i]=='-Xclang' and args[i+1]=='-fdump-record-layouts':i+=2
   else:pp.append(args[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',dep,'-MT','input'],name+'-deps',rec['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(rec['directory'])/p
   inputs[str(p)]=sha(p)
 oldsource=R/'UniXNU-zorn/native/gpu-owned/runtime/ZornGpuRuntimeBackings.cpp';a=list(builds['registry-selected']);a[a.index(str(O/'ZornGpuCatalogBackings.cpp'))]=str(oldsource);a[a.index('-o')+1]=str(O/'old-five-args-refused.o');p=run(a,'old-five-args-refused',recipes['cxx']['directory'],False);assert p.returncode!=0 and 'too many arguments' in p.stderr
 compositions={}
 for name,names in [('registry-component',['registry-selected','current-memory','current-cpu','planner']),('gmu-component',['composition-selected','current-memory','current-cpu','planner','extent','ledger'])]:
  obj=O/(name+'.o');run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',*[O/(n+'.o') for n in names],'-o',obj],name+'-link');imports=run(['nm','-u',obj],name+'-imports').stdout.split();assert not any(any(t in n for t in ['NativeAdreno','ZornGpu','ZGPlan','ZGCheck']) for n in imports),imports
  assert '__mod_init_func' not in run(['otool','-l',obj],name+'-sections').stdout
  compositions[name]=dict(fresh_objects=names,imports=imports,sha256=sha(obj),native_and_helper_method_imports_closed=True)
 assert compositions['registry-component']['imports']==compositions['gmu-component']['imports']
 for n,h in pins.items():assert sha(Path(n))==h,n
 for name,old,parent in VARIANTS:source_check(name,old,parent)
 result=dict(objects=objects,actual_recursive_inputs=inputs,compositions=compositions,commands=commands,new_source_mutations_refused=neg,old_actual_five_argument_caller_compile_refused=True,
 all_objects_fresh_current_iOS17_no_old_object_reuse=True,default_OFF_has_no_allocator_import=True,constinit_owners_no_initializer=True,
 narrow_policy_and_error_retention_body_unchanged_except_type_rename_and_bound_arity=True,
 full_NativeMemory_source_defines_unused_paths_not_selected_or_authorized=True,only_native4_argument_allocate_reachable_from_selected_variants=True,
 global_bitmap_initialization_serialization_auxiliary_budget_and_cleanup_status_still_unknown=True,
 no_native_allocator_getter_cache_provider_VM_map_phone_or_host_success_peer_execution=True,no_component_or_runtime_caller_selection_FD_kernel_device_candidate=True,
 allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'compile-result.json').write_text(json.dumps(result,indent=2)+'\n');print('10 fresh current-catalog iOS17 pairs;',len(inputs),'recursive inputs;4-argument allocation bound;old caller compile refuses;OFF no import;no execution')
if __name__=='__main__':main()
