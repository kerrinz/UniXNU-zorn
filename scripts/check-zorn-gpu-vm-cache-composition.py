#!/usr/bin/env python3
"""New publish/acquire raw-error composition only; no native/host-provider execution."""
from pathlib import Path
import hashlib,importlib.util,json,re,shlex,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-native-vm-cache-composition';P=R/'out/zorn/gpu-native-submit-retention';M=R/'out/zorn/gpu-gen7-map-retention';N=R/'UniXNU/drivers/NativeAdreno'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('extent_util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
OPS=[('publishMapped','m.memory->publishForDevice(0,m.memory->bytes(),true,distrust_write_combined_)','first_publish_mapped_cache_error'),('acquireImported','m.memory->acquireDeviceWrites(0,m.memory->bytes())','first_acquire_imported_cache_error')]
def capture(call,prefix):
 return f'''const IOReturn native_status={call};
        if(native_status) {{
            if(!native_failure_.{prefix}_available) {{
                native_failure_.{prefix}=native_status;
                native_failure_.{prefix}_available=1;
            }}
            return fail(ArmSmmu4KIoError);
        }}'''
def check(header,source,oldheader,oldsource):
 for fn,call,prefix in OPS:
  body=util.body(source,'NativeAdrenoVm::'+fn);old=util.body(oldsource,'NativeAdrenoVm::'+fn);block=capture(call,prefix)
  assert body.count(block)==1,fn+' exact native status before fold,inside failed-call guard'
  assert body.replace(block,'if('+call+')return fail(ArmSmmu4KIoError);')==old,fn+' skip/call/poison/return semantics unchanged'
  assert body.index('continue;}')<body.index('const IOReturn native_status'),fn+' skip before native call'
  assert f'IOReturn {prefix}=0;' in header and f'uint32_t {prefix}_available=0;' in header,'full typed raw width/explicit unavailable'
 for fn in ['map','unmap','fail','coherentMapping','importedUntouched']:
  name=fn if fn in ['coherentMapping','importedUntouched'] else 'NativeAdrenoVm::'+fn
  assert util.body(source,name)==util.body(oldsource,name),fn+' outside new cache composition scope'
 assert 'IOReturn first_map_cache_error=0;\n    uint32_t first_map_cache_error_available=0;' in header
 assert 'const NativeAdrenoVmNativeFailure &nativeFailure() const {return native_failure_;}' in header
 assert source.count('first_publish_mapped_cache_error_available=1;')==1 and source.count('first_acquire_imported_cache_error_available=1;')==1

def main():
 if (O/'compile-result.json').exists():raise SystemExit('completed;do not repeat')
 pins=json.loads((O/'source-pins.json').read_text())
 for p,h in pins.items():assert sha(Path(p))==h,p
 header=(O/'NativeAdrenoVm.h').read_text();source=(O/'NativeAdrenoVm.cpp').read_text();oldheader=(O/'NativeAdrenoVm.h.preimage').read_text();oldsource=(O/'NativeAdrenoVm.cpp.preimage').read_text();check(header,source,oldheader,oldsource)
 for n in ['NativeAdrenoSubmit.h','NativeAdrenoSubmit.cpp']:assert (O/n).read_bytes()==(P/n).read_bytes()
 assert 'return writeback && native_adreno_io_coherent;' in util.body(source,'coherentMapping')
 assert 'return memory->imported() && native_adreno_io_coherent;' in util.body(source,'importedUntouched')
 # Record only this new source's negative controls,not old map/Submit suites.
 neg=[]
 for name,which,a,b in [('publish-error-folded-before-capture','source','first_publish_mapped_cache_error=native_status;','first_publish_mapped_cache_error=kIOReturnIOError;'),('acquire-first-error-overwritten','source','if(!native_failure_.first_acquire_imported_cache_error_available)','if(true)'),('skip-forged-publish-availability','source','if(!m.memory)continue;','if(!m.memory){native_failure_.first_publish_mapped_cache_error_available=1;continue;}'),('publish-raw16','header','IOReturn first_publish_mapped_cache_error=0;','uint16_t first_publish_mapped_cache_error=0;')]:
  h,s=header,source
  if which=='source':assert a in s;s=s.replace(a,b)
  else:assert a in h;h=h.replace(a,b)
  try:check(h,s,oldheader,oldsource)
  except (AssertionError,ValueError) as e:neg.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('new composition negative survived '+name)
 commands=[]
 def run(a,name,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,directory=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0,name
  return p.stdout+p.stderr
 # Sequential source-review replay uses private fresh files only.
 d=O/'source-review-base'
 for n in ['NativeAdrenoVm.h','NativeAdrenoVm.cpp','NativeAdrenoSubmit.h','NativeAdrenoSubmit.cpp']:
  p=d/'drivers/NativeAdreno'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((N/n).read_bytes())
 for name,patch in [('old-map',M/'native-cache-error-retention.UNAPPLIED.patch'),('new-cache',O/'vm-publish-acquire-errors.UNAPPLIED.patch'),('old-submit',P/'submit-reference-retention.UNAPPLIED.patch')]:
  run(['git','apply','--no-index','--check',patch],name+'-patch-check',d);run(['git','apply','--no-index',patch],name+'-patch-review-copy',d)
 for n in ['NativeAdrenoVm.h','NativeAdrenoVm.cpp','NativeAdrenoSubmit.h','NativeAdrenoSubmit.cpp']:assert (d/'drivers/NativeAdreno'/n).read_bytes()==(O/n).read_bytes()
 abi=O/'cache-companion-ABI.cpp';abi.write_text('''/* SPDX-License-Identifier: MIT */
#include "NativeAdrenoVm.h"
#include "NativeAdrenoSubmit.h"
#include <stddef.h>
using Publish=IOReturn(NativeAdrenoMemory::*)(size_t,size_t,bool,bool);
using Acquire=IOReturn(NativeAdrenoMemory::*)(size_t,size_t);
static_assert(__is_same(decltype(&NativeAdrenoMemory::publishForDevice),Publish));
static_assert(__is_same(decltype(&NativeAdrenoMemory::acquireDeviceWrites),Acquire));
static_assert(sizeof(IOReturn)==4 && sizeof(NativeAdrenoVmNativeFailure)==24);
static_assert(__is_same(decltype(NativeAdrenoVmNativeFailure::first_publish_mapped_cache_error),IOReturn));
static_assert(__is_same(decltype(NativeAdrenoVmNativeFailure::first_acquire_imported_cache_error),IOReturn));
static_assert(offsetof(NativeAdrenoVmNativeFailure,first_map_cache_error)==0);
static_assert(offsetof(NativeAdrenoVmNativeFailure,first_map_cache_error_available)==4);
static_assert(offsetof(NativeAdrenoVmNativeFailure,first_publish_mapped_cache_error)==8);
static_assert(offsetof(NativeAdrenoVmNativeFailure,first_publish_mapped_cache_error_available)==12);
static_assert(offsetof(NativeAdrenoVmNativeFailure,first_acquire_imported_cache_error)==16);
static_assert(offsetof(NativeAdrenoVmNativeFailure,first_acquire_imported_cache_error_available)==20);
static_assert(sizeof(NativeAdrenoSubmit)==1360 && sizeof(NativeAdrenoSubmitStats)==40);
extern "C" const unsigned cache_companion_sizes[]={sizeof(NativeAdrenoVm),sizeof(NativeAdrenoVmNativeFailure),sizeof(NativeAdrenoSubmit)};
''')
 B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';recipe=B/'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';rec=json.JSONDecoder().raw_decode(recipe.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in rec['arguments']
 inputs={str(recipe):sha(recipe)};objects={};includes=['-I'+str(O),'-I'+str(N),'-I'+str(R/'UniXNU/kits/ArmSmmu4K'),'-I'+str(R/'UniXNU/kits/AdrenoPM4')];builds={}
 for name,src in [('companion-vm',O/'NativeAdrenoVm.cpp'),('composed-submit',O/'NativeAdrenoSubmit.cpp'),('companion-ABI',abi)]:
  a=list(rec['arguments']);a[a.index(rec['file'])]=str(src);obj=O/(name+'.o');a[a.index('-o')+1]=str(obj);a+=includes+['-mgeneral-regs-only']
  if name=='companion-ABI':a+=['-Xclang','-fdump-record-layouts']
  run(a,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(a,name+'-independent',rec['directory']);assert sha(first)==sha(obj);objects[name]=dict(source=str(src),source_sha256=sha(src),object_sha256=sha(obj),independent_raw_SHA_equal=True);builds[name]=a
  imports=run(['nm','-u',obj],name+'-imports');assert '__mod_init_func' not in run(['otool','-l',obj],name+'-sections');run(['otool','-tvV',obj],name+'-disassembly');run(['otool','-rv',obj],name+'-relocations')
  if name=='companion-ABI':assert not imports.strip()
  pp=[];i=0
  while i<len(a):
   if a[i] in ['-o','-MF','-MT','-MJ']:i+=2
   elif a[i]=='-c':i+=1
   elif a[i]=='-Xclang' and a[i+1]=='-fdump-record-layouts':i+=2
   else:pp.append(a[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',dep,'-MT','input'],name+'-deps',rec['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(rec['directory'])/p
   inputs[str(p)]=sha(p)
 # Reuse only sealed,byte-bound dependencies with no changed VM/Submit header
 # in their actual per-object dependency lists. Never label them fresh builds.
 parent=json.loads((P/'compile-result.json').read_text());reuse={};reuse_inputs={};(O/'sealed-dependencies').mkdir()
 for q in [recipe,B/'bsd/DEVELOPMENT/bsd_init.o.json']:assert sha(q)==parent['inputs'][str(q)],'sealed dependency recipe changed'
 for name in ['current-ring','current-memory','current-cpu','current-smmu-memory','current-PM4']:
  obj=P/(name+'.o');assert sha(obj)==parent['objects'][name]['object_sha256'];dst=O/'sealed-dependencies'/obj.name;dst.write_bytes(obj.read_bytes());assert sha(dst)==sha(obj) and dst.stat().st_ino!=obj.stat().st_ino
  cwd=rec['directory']
  if name=='current-PM4':cwd=json.JSONDecoder().raw_decode((B/'bsd/DEVELOPMENT/bsd_init.o.json').read_text())[0]['directory']
  deps={}
  for n in shlex.split((P/(name+'.d')).read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(cwd)/p
   assert p.name not in ['NativeAdrenoVm.h','NativeAdrenoSubmit.h'],(name,p)
   h=sha(p);assert h==parent['inputs'][str(p)],p;deps[str(p)]=h;reuse_inputs[str(p)]=h
  reuse[name]=dict(parent_object=str(obj),copied_object=str(dst),sha256=sha(obj),independent_inode=True,actual_dependencies=deps,does_not_depend_on_changed_VM_or_Submit_header=True,new_compile_not_claimed=True)
 negative=O/'wrong-publish-width';negative.mkdir();(negative/'NativeAdrenoVm.h').write_text(header.replace('IOReturn first_publish_mapped_cache_error=0;','uint16_t first_publish_mapped_cache_error=0;'));bad=negative/'ABI.cpp';bad.write_bytes(abi.read_bytes());a=list(builds['companion-ABI']);a[a.index(str(abi))]=str(bad);a[a.index('-o')+1]=str(negative/'ABI.o');run(a,'wrong-publish-width-refused',rec['directory'],good=False)
 linked=O/'vm-submit-companion.o';run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',O/'companion-vm.o',O/'composed-submit.o',*[e['copied_object'] for e in reuse.values()],'-o',linked],'companion-link')
 imports=run(['nm','-u',linked],'companion-imports').split();assert not any('NativeAdreno' in n for n in imports),'native method imports not closed';assert '__mod_init_func' not in run(['otool','-l',linked],'companion-sections')
 for p,h in pins.items():assert sha(Path(p))==h,p
 for n in ['NativeAdrenoSubmit.h','NativeAdrenoSubmit.cpp']:assert (O/n).read_bytes()==(P/n).read_bytes()
 result=dict(fresh_objects=objects,fresh_compile_inputs=inputs,sealed_dependency_reuse=reuse,sealed_dependency_inputs=reuse_inputs,commands=commands,new_source_corruptions_refused=neg,new_raw_width_compile_refused=True,
  composition_imports=imports,composition_sha256=sha(linked),native_method_imports_closed=True,source_review_replays_exact_compiled_candidate=True,
  previous_map_method_and_failure_semantics_source_unchanged=True,Submit_sources_byte_identical=True,three_fresh_object_pairs_and_five_explicitly_reused_sealed_dependencies=True,
  no_native_cache_VM_allocator_ring_fence_provider_or_host_peer_executed=True,no_new_runtime_caller_FD_kernel_device_candidate=True,patch_unapplied=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'compile-result.json').write_text(json.dumps(result,indent=2)+'\n');print('3 new iOS17 independent object pairs;5 sealed header-independent deps explicitly reused;4 source/1 width refusals;native method imports close;zero invocation')
if __name__=='__main__':main()
