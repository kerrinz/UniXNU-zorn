#!/usr/bin/env python3
"""Only three Ring commit callback errors; real iOS17 static compilation,zero execution."""
from pathlib import Path
import hashlib,importlib.util,json,re,shlex,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-native-ring-commit-errors';P=R/'out/zorn/gpu-native-vm-cache-composition';S=R/'out/zorn/gpu-native-submit-retention';M=R/'out/zorn/gpu-gen7-map-retention';N=R/'UniXNU/drivers/NativeAdreno'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('extent_util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
CALLS=[('cache_.publish(cache_.cookie,ring_,ring_bytes_)','published','CommitPublish'),('io_.barrier(io_.cookie)','ordered','CommitBarrier'),('io_.write32(io_.cookie,RingWptr,end)','committed','CommitWptr')]
def check(header,source,oldheader,oldsource):
 body=util.body(source,'NativeAdrenoRing::submitWords');restored=body
 for call,var,stage in CALLS:
  new=f'    const int {var}={call};\n    if({var})return poisonCommitCallback({var},{stage});'
  assert restored.count(new)==1,'exact callback int before original poison: '+stage
  restored=restored.replace(new,f'    if({call})return poison();')
 assert restored==util.body(oldsource,'NativeAdrenoRing::submitWords'),'original commit ordering/counters/returns unchanged'
 helper=util.body(source,'NativeAdrenoRing::poisonCommitCallback')
 assert 'if(status && !first_commit_callback_error_available_)' in helper
 assert 'first_commit_callback_error_=status;' in helper and 'first_commit_callback_stage_=stage;' in helper
 assert helper.index('first_commit_callback_error_=status;')<helper.index('first_commit_callback_error_available_=true;')<helper.index('return poison();')
 assert 'int first_commit_callback_error_=0;' in header and 'uint32_t first_commit_callback_stage_=0;' in header
 assert 'CommitPublish=1,CommitBarrier=2,CommitWptr=3' in header
 for fn in ['poison','readRptr','attach','detach','observeFence','wait','emitFence','emitFramedFence']:
  assert util.body(source,'NativeAdrenoRing::'+fn)==util.body(oldsource,'NativeAdrenoRing::'+fn),fn+' outside scoped three callbacks'
 for tag in ['NativeAdrenoRingIo','NativeAdrenoRingCache','NativeAdrenoRingClock']:
  pat=r'struct '+tag+r'\s*\{.*?\n\};';assert re.search(pat,header,re.S).group()==re.search(pat,oldheader,re.S).group(),tag+' ABI changed'
 assert source.count('poisonCommitCallback(')==4,'helper definition plus exactly three commit sites'
 assert source.count('first_commit_callback_error_available_=true;')==1

def main():
 if (O/'compile-result.json').exists():raise SystemExit('completed;do not repeat')
 pins=json.loads((O/'source-pins.json').read_text())
 for p,h in pins.items():assert sha(Path(p))==h,p
 header=(O/'NativeAdrenoRing.h').read_text();source=(O/'NativeAdrenoRing.cpp').read_text();oldheader=(O/'NativeAdrenoRing.h.preimage').read_text();oldsource=(O/'NativeAdrenoRing.cpp.preimage').read_text();check(header,source,oldheader,oldsource)
 for n in ['NativeAdrenoVm.h','NativeAdrenoVm.cpp','NativeAdrenoSubmit.h','NativeAdrenoSubmit.cpp']:assert (O/n).read_bytes()==(P/n).read_bytes()
 neg=[]
 for name,which,a,b in [('publication-value-discarded','source','poisonCommitCallback(published,CommitPublish)','poisonCommitCallback(1,CommitPublish)'),('first-callback-error-overwritten','source','if(status && !first_commit_callback_error_available_)','if(status)'),('public-error-changed','source','    return poison();\n}\nIOReturn NativeAdrenoRing::poison()','    return status;\n}\nIOReturn NativeAdrenoRing::poison()'),('callback-raw16','header','int first_commit_callback_error_=0;','int16_t first_commit_callback_error_=0;')]:
  h,s=header,source
  if which=='source':assert a in s;s=s.replace(a,b)
  else:assert a in h;h=h.replace(a,b)
  try:check(h,s,oldheader,oldsource)
  except (AssertionError,ValueError) as e:neg.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('new source negative survived '+name)
 commands=[]
 def run(a,name,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,directory=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0,name
  return p.stdout+p.stderr
 d=O/'source-review-base'
 names=['NativeAdrenoRing.h','NativeAdrenoRing.cpp','NativeAdrenoVm.h','NativeAdrenoVm.cpp','NativeAdrenoSubmit.h','NativeAdrenoSubmit.cpp']
 for n in names:
  p=d/'drivers/NativeAdreno'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((N/n).read_bytes())
 for name,patch in [('old-map',M/'native-cache-error-retention.UNAPPLIED.patch'),('old-cache',P/'vm-publish-acquire-errors.UNAPPLIED.patch'),('old-submit',S/'submit-reference-retention.UNAPPLIED.patch'),('new-ring',O/'ring-commit-callback-errors.UNAPPLIED.patch')]:
  run(['git','apply','--no-index','--check',patch],name+'-patch-check',d);run(['git','apply','--no-index',patch],name+'-review-copy',d)
 for n in names:assert (d/'drivers/NativeAdreno'/n).read_bytes()==(O/n).read_bytes()
 abi=O/'ring-commit-ABI.cpp';abi.write_text('''/* SPDX-License-Identifier: MIT */
#include "NativeAdrenoRing.h"
#include "NativeAdrenoVm.h"
#include "NativeAdrenoSubmit.h"
using Publish=int(*)(void*,const volatile uint32_t*,size_t);
using Barrier=int(*)(void*);
using Write=int(*)(void*,uint32_t,uint32_t);
static_assert(__is_same(decltype(NativeAdrenoRingCache::publish),Publish));
static_assert(__is_same(decltype(NativeAdrenoRingIo::barrier),Barrier));
static_assert(__is_same(decltype(NativeAdrenoRingIo::write32),Write));
static_assert(sizeof(int)==4 && int(-1)<0 && sizeof(size_t)==8);
static_assert(sizeof(NativeAdrenoRingIo)==32 && sizeof(NativeAdrenoRingCache)==24);
static_assert(sizeof(NativeAdrenoRing)==144);
static_assert(sizeof(NativeAdrenoVm)==280 && sizeof(NativeAdrenoVmNativeFailure)==24);
static_assert(sizeof(NativeAdrenoSubmit)==1360);
extern "C" const unsigned ring_commit_sizes[]={sizeof(NativeAdrenoRing),sizeof(NativeAdrenoRingIo),sizeof(NativeAdrenoRingCache),sizeof(int)};
''')
 B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';recipe=B/'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';rec=json.JSONDecoder().raw_decode(recipe.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in rec['arguments'];inputs={str(recipe):sha(recipe)};objects={};builds={}
 inc=['-I'+str(O),'-I'+str(N),'-I'+str(R/'UniXNU/kits/ArmSmmu4K'),'-I'+str(R/'UniXNU/kits/AdrenoPM4')]
 for name,src in [('retained-ring',O/'NativeAdrenoRing.cpp'),('affected-submit',O/'NativeAdrenoSubmit.cpp'),('commit-ABI',abi)]:
  a=list(rec['arguments']);a[a.index(rec['file'])]=str(src);obj=O/(name+'.o');a[a.index('-o')+1]=str(obj);a+=inc+['-mgeneral-regs-only']
  if name=='commit-ABI':a+=['-Xclang','-fdump-record-layouts']
  run(a,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(a,name+'-independent',rec['directory']);assert sha(first)==sha(obj);objects[name]=dict(source=str(src),source_sha256=sha(src),object_sha256=sha(obj),independent_raw_SHA_equal=True);builds[name]=a
  imports=run(['nm','-u',obj],name+'-imports');assert '__mod_init_func' not in run(['otool','-l',obj],name+'-sections');run(['otool','-tvV',obj],name+'-disassembly');run(['otool','-rv',obj],name+'-relocations')
  if name=='commit-ABI':assert not imports.strip()
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
 bad=O/'wrong-callback-return-width.cpp';bad.write_text(abi.read_text().replace('using Publish=int(*)','using Publish=int64_t(*)'));a=list(builds['commit-ABI']);a[a.index(str(abi))]=str(bad);a[a.index('-o')+1]=str(O/'wrong-callback-return-width.o');run(a,'wrong-callback-return-width-refused',rec['directory'],good=False)
 parent=json.loads((P/'compile-result.json').read_text());parent_recipes=json.loads((P/'sealed-recipe-identity.json').read_text())['recipe_files']
 for p,h in parent_recipes.items():assert sha(Path(p))==h,p
 reuse={};reuse_inputs={};(O/'sealed-dependencies').mkdir()
 # Parent VM has no changed Ring header. Do not reuse parent's old Ring.
 obj=P/'companion-vm.o';assert sha(obj)==parent['fresh_objects']['companion-vm']['object_sha256'];deps={}
 for n in shlex.split((P/'companion-vm.d').read_text().replace('\\\n',' ').split(':',1)[1]):
  p=Path(n)
  if not p.is_absolute():p=Path(rec['directory'])/p
  assert p.name!='NativeAdrenoRing.h',p;h=sha(p);assert h==parent['fresh_compile_inputs'][str(p)],p;deps[str(p)]=h
 candidates=[('sealed-vm',obj,sha(obj),deps)]
 for name in ['current-memory','current-cpu','current-smmu-memory','current-PM4']:
  old=parent['sealed_dependency_reuse'][name];candidates.append((name,Path(old['copied_object']),old['sha256'],old['actual_dependencies']))
 for name,obj,h,deps in candidates:
  assert sha(obj)==h,obj;dst=O/'sealed-dependencies'/(name+'.o');dst.write_bytes(obj.read_bytes());assert sha(dst)==h and dst.stat().st_ino!=obj.stat().st_ino
  for p,expected in deps.items():assert Path(p).name!='NativeAdrenoRing.h' and sha(Path(p))==expected,p;reuse_inputs[p]=expected
  reuse[name]=dict(parent_object=str(obj),copied_object=str(dst),sha256=h,actual_dependencies=deps,no_changed_Ring_header_dependency=True,independent_inode=True,fresh_rebuild_not_claimed=True)
 linked=O/'ring-submit-vm-component.o';run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',O/'retained-ring.o',O/'affected-submit.o',*[e['copied_object'] for e in reuse.values()],'-o',linked],'component-link');imports=run(['nm','-u',linked],'component-imports').split()
 assert not any('NativeAdreno' in n for n in imports);assert imports==parent['composition_imports'];assert '__mod_init_func' not in run(['otool','-l',linked],'component-sections')
 for p,h in pins.items():assert sha(Path(p))==h,p
 for n in ['NativeAdrenoVm.h','NativeAdrenoVm.cpp','NativeAdrenoSubmit.h','NativeAdrenoSubmit.cpp']:assert (O/n).read_bytes()==(P/n).read_bytes()
 (O/'compile-result.json').write_text(json.dumps(dict(fresh_objects=objects,fresh_compile_inputs=inputs,sealed_dependency_reuse=reuse,sealed_dependency_inputs=reuse_inputs,sealed_recipe_files=parent_recipes,commands=commands,new_source_corruptions_refused=neg,new_wrong_callback_width_compile_refused=True,composition_imports=imports,composition_sha256=sha(linked),native_method_imports_closed=True,all_imports_identical_to_parent=True,source_review_exact_compiled_bytes=True,VM_Submit_sources_unchanged=True,only_three_new_object_pairs_five_sealed_dependencies_explicitly_reused=True,no_native_method_callback_provider_or_host_peer_execution=True,patch_unapplied=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('3 fresh current iOS17 object pairs;5 sealed deps exclude changed Ring header;4 source/1 ABI-width refusals;7-object native closure;zero callback invocation')
if __name__=='__main__':main()
