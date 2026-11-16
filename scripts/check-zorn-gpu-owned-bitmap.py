#!/usr/bin/env python3
"""Isolated bitmap publication repair plus exact selected UBSan source;static only."""
from pathlib import Path
import hashlib,importlib.util,json,shlex,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-owned-bitmap-init';P=R/'out/zorn/gpu-catalog-cpu-memory';N=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
NOTE='if(!bits) {__atomic_store_n(&ownedMapIncomplete,true,__ATOMIC_RELEASE);return;}'
QUERY='if(!bits || __atomic_load_n(&ownedMapIncomplete,__ATOMIC_ACQUIRE))return true;'
def check(s,old):
 owned=util.body(s,'ownedMap')
 assert '__atomic_compare_exchange_n(&ownedMapState,&expected,1,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)' in owned
 assert owned.index('ownedBits=bits;')<owned.index('__atomic_store_n(&ownedMapState,bits?2u:3u,__ATOMIC_RELEASE);')
 assert owned.index('if(__atomic_load_n(&ownedMapState,__ATOMIC_ACQUIRE)!=2)return nullptr;')<owned.rindex('return ownedBits;')
 assert owned.count('IOMallocZero(')==1 and 'while(' not in owned and 'for(' not in owned
 assert s.count(NOTE)==1 and s.count(QUERY)==1
 # Exactly the private helper block and conservative absence handling differ.
 a=s.index('uint64_t *ownedBits;');b=s.index('void noteOwned(',a);x=old.index('uint64_t *ownedBits;');y=old.index('void noteOwned(',x)
 restored=s[:a]+old[x:y]+s[b:];restored=restored.replace(NOTE,'if(!bits)return;').replace(QUERY,'if(!bits)return true;')
 assert restored==old,'public allocator/cache/cleanup/error bodies changed'
 assert s.count('&ownedMapIncomplete')==2,'sticky latch must not reset'
 assert 'IOLock' not in owned and 'IOSleep' not in owned

def main():
 if (O/'compile-result.json').exists():raise SystemExit('completed;do not repeat')
 pins=json.loads((O/'source-pins.json').read_text())
 for n,h in pins.items():assert sha(Path(n))==h,n
 s=(O/'NativeAdrenoMemory.cpp').read_text();old=(O/'NativeAdrenoMemory.cpp.preimage').read_text();check(s,old);neg=[]
 for name,a,b in [('pointer-published-after-ready','ownedBits=bits;\n            __atomic_store_n(&ownedMapState,bits?2u:3u,__ATOMIC_RELEASE);','__atomic_store_n(&ownedMapState,bits?2u:3u,__ATOMIC_RELEASE);\n            ownedBits=bits;'),('skipped-note-not-latched',NOTE,'if(!bits)return;'),('incomplete-query-trusted',QUERY,'if(!bits)return true;')]:
  assert a in s
  try:check(s.replace(a,b),old)
  except AssertionError as e:neg.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('new publication mutation survived '+name)
 commands=[]
 def run(a,name,cwd=R):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,directory=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr);p.check_returncode();return p.stdout
 d=O/'source-review';d.mkdir();(d/'NativeAdrenoMemory.cpp').write_bytes((N/'NativeAdrenoMemory.cpp').read_bytes());run(['git','apply','--no-index','--check',O/'owned-bitmap-init.UNAPPLIED.patch'],'patch-check',d);run(['git','apply','--no-index',O/'owned-bitmap-init.UNAPPLIED.patch'],'patch-replay',d);assert (d/'NativeAdrenoMemory.cpp').read_bytes()==(O/'NativeAdrenoMemory.cpp').read_bytes()
 recipes={'memory':B/'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json','ubsan':B/'san/DEVELOPMENT/ubsan_minimal.o.json'};inputs={};objects={}
 for name,path in recipes.items():
  inputs[str(path)]=sha(path);rec=json.JSONDecoder().raw_decode(path.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in rec['arguments'];a=list(rec['arguments']);obj=O/(name+'.o');a[a.index('-o')+1]=str(obj)
  if name=='memory':a[a.index(rec['file'])]=str(O/'NativeAdrenoMemory.cpp');a+=['-I'+str(N),'-mgeneral-regs-only']
  # UBSan uses its exact recorded sanitizer flags,source,cwd and selected config.
  if name=='ubsan':assert '-fsanitize-minimal-runtime' in a and '-fsanitize=signed-integer-overflow' in a
  run(a,name+'-first',rec['directory']);copy=O/(name+'-first.o');copy.write_bytes(obj.read_bytes());run(a,name+'-independent',rec['directory']);assert sha(copy)==sha(obj)
  objects[name]=dict(source=str(O/'NativeAdrenoMemory.cpp') if name=='memory' else rec['file'],object_sha256=sha(obj),independent_raw_SHA_equal=True)
  run(['nm','-u',obj],name+'-imports');run(['nm','-g',obj],name+'-symbols');run(['otool','-tvV',obj],name+'-disassembly');run(['otool','-rv',obj],name+'-relocations');run(['otool','-l',obj],name+'-sections')
  pp=[];i=0
  while i<len(a):
   if a[i] in ['-o','-MF','-MT','-MJ']:i+=2
   elif a[i]=='-c':i+=1
   else:pp.append(a[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',dep,'-MT','input'],name+'-deps',rec['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(rec['directory'])/p
   inputs[str(p)]=sha(p)
 parent=json.loads((P/'compile-result.json').read_text());sealed={};sealed_inputs={};(O/'sealed-dependencies').mkdir()
 for name in ['registry-selected','current-cpu','planner']:
  obj=P/(name+'.o');h=parent['objects'][name]['object_sha256'];assert sha(obj)==h
  cmd=next(e for e in parent['commands'] if '-o' in e['arguments'] and str(obj) in e['arguments']);cwd=Path(cmd['directory']);deps={}
  for n in shlex.split((P/(name+'.d')).read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=cwd/p
   value=sha(p);assert value==parent['actual_recursive_inputs'][str(p)],p;deps[str(p)]=value;sealed_inputs[str(p)]=value
  dst=O/'sealed-dependencies'/(name+'.o');dst.write_bytes(obj.read_bytes());assert sha(dst)==h and dst.stat().st_ino!=obj.stat().st_ino
  sealed[name]=dict(parent_object=str(obj),copied_object=str(dst),sha256=h,actual_dependencies=deps,no_header_or_source_change=True,fresh_rebuild_not_claimed=True)
 assert (O/'memory-imports.log').read_text()==(P/'current-memory-imports.log').read_text(),'bitmap repair should add no imports'
 linked=O/'bitmap-ubsan-component.o';run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',O/'memory.o',O/'ubsan.o',*[e['copied_object'] for e in sealed.values()],'-o',linked],'component-link')
 imports=run(['nm','-u',linked],'component-imports').split();symbols=run(['nm','-n',linked],'component-all-symbols');run(['otool','-l',linked],'component-sections')
 assert '___ubsan_handle_negate_overflow_minimal' not in imports and any((' '+kind+' ___ubsan_handle_negate_overflow_minimal') in symbols for kind in ['T','t'])
 assert not any(t in n for n in imports for t in ['NativeAdreno','ZornGpu','ZGPlan'])
 for n,h in pins.items():assert sha(Path(n))==h,n
 result=dict(objects=objects,fresh_recursive_inputs=inputs,sealed_dependencies=sealed,sealed_dependency_inputs=sealed_inputs,commands=commands,
 new_source_mutations_refused=neg,source_review_exact=True,all_public_method_and_error_bodies_unchanged=True,memory_imports_unchanged=True,
 exact_recorded_XNU_ubsan_source_and_flags=True,strong_negate_resolved_only_in_new_relocatable_link=True,
 component_imports=imports,component_sha256=sha(linked),component_native_helper_methods_closed=True,
 source_pointer_publication_and_sticky_conservative_incomplete_note=True,no_global_alias_concurrency_lifetime_or_hardware_owner_proof=True,
 full_UBSan_startup_sysctl_metadata_retained_unexecuted_not_appendable_to_already_linked_baseline=True,
 no_native_allocator_lock_runtime_cache_provider_phone_or_success_peer_calls=True,
 no_component_runtimecaller_selection_FD_kernel_device_candidate=True,patch_unapplied=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'compile-result.json').write_text(json.dumps(result,indent=2)+'\n');print('2 fresh object pairs;',len(inputs),'new inputs;3 explicit sealed dependencies;',len(sealed_inputs),'sealed inputs;real selected UBSan binds negate in static component;no invocation')
if __name__=='__main__':main()
