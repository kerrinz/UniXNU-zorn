#!/usr/bin/env python3
"""Specific Gen7 reservation-size source/target check; no VM/provider execution."""
from pathlib import Path
import hashlib,json,subprocess,shlex,re
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-gen7-vma-contract';D=R/'UniXNU-zorn/native/gpu-owned/runtime';P=R/'out/zorn/gpu-discovery-20261030/profile-reference'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def body(text,name):
 start=text.index(name+'(');start=text.index('{',start);level=1;at=start+1
 while level:
  level+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[start:at]
def audit_reference(text):
 dyn=body(text,'_map_gmu_dynamic');static=body(text,'_map_gmu_static')
 assert 'ALIGN(md->size, hfi_get_gmu_sz_alignment(align))' in dyn,'reservation rounds backing size'
 assert dyn.index('insert_va(vma, addr, size)')<dyn.index('gmu_core_map_memdesc'),'reservation must precede map'
 assert 'find_va(vma, md->gmuaddr, size)' in dyn,'failure lookup uses descriptor address, not local reserved addr'
 assert static.index('gmu_core_map_memdesc')<static.index('md->gmuaddr = addr;')<static.index('vma->next_va = md->gmuaddr + size;'),'static cursor commit after map'
 free=body(text,'gen7_free_gmu_block');assert 'md->size != iommu_unmap' in free and free.index('goto free;')<free.index('rb_erase'),'partial unmap keeps reservation node'
def main():
 if (O/'check-result.json').exists():raise SystemExit('completed; do not repeat')
 pins=json.loads((R/'out/zorn/gpu-dynamic-backing-contract/combined-result.json').read_text())['inputs']
 for p,d in pins.items():assert sha(Path(p))==d
 entries=json.loads((P/'manifest.json').read_text())['files'];entry=next(e for e in entries if e['name']=='adreno_hfi.h' and e.get('ok'));assert sha(P/'adreno_hfi.h')==entry['sha256'];pins[str(P/'adreno_hfi.h')]=entry['sha256']
 for p in [D/'ZornGpuStartupPlan.h',D/'ZornGpuStartupPlan.c',R/'UniXNU/drivers/NativeAdreno/NativeAdrenoVm.h',R/'UniXNU/drivers/NativeAdreno/NativeAdrenoVm.cpp']:pins[str(p)]=sha(p)
 (O/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
 original=(P/'adreno_gen7_gmu.c').read_text();audit_reference(original);source_controls=[]
 for name,a,b in [('round-request-not-backing','ALIGN(md->size, hfi_get_gmu_sz_alignment(align))','ALIGN(0, hfi_get_gmu_sz_alignment(align))'),('failure-lookup-local-address','find_va(vma, md->gmuaddr, size)','find_va(vma, addr, size)'),('advance-static-by-unrounded-length','vma->next_va = md->gmuaddr + size;','vma->next_va = md->gmuaddr + md->size;')]:
  changed=original.replace(a,b);assert changed!=original
  try:audit_reference(changed)
  except (AssertionError,ValueError) as e:source_controls.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('source corruption survived '+name)
 commands=[]
 def run(args,name,cwd=R,good=True):
  args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=args,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p.stdout
 flags=['-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(O),'-I'+str(D)]
 run(['clang',*flags,O/'ZornGpuGmuExtent.c',D/'ZornGpuStartupPlan.c',O/'test-extent.c','-o',O/'test-extent'],'host-build');run([O/'test-extent'],'host-run');negative=[];source=(O/'ZornGpuGmuExtent.c').read_text()
 for name,a,b in [('wrong-round-base','(backing+q.size_alignment-1)','((uint64_t)q.size+q.size_alignment-1)'),('secure-admitted','ZG_REQUIRE_SECURE|ZG_REQUIRE_FIXED_RESOURCE','ZG_REQUIRE_FIXED_RESOURCE'),('reservation-size-ignored','reservation!=rounded','0')]:
  assert source.count(a)==1;p=O/(name+'.c');p.write_text(source.replace(a,b));exe=O/name
  run(['clang',*flags,p,D/'ZornGpuStartupPlan.c',O/'test-extent.c','-o',exe],name+'-build');run([exe],name+'-refused',good=False);negative.append(name)
 recipe=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/bsd_init.o.json';rec=json.JSONDecoder().raw_decode(recipe.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in rec['arguments'];inputs={str(recipe):sha(recipe)};objects={}
 for name,path in [('extent',O/'ZornGpuGmuExtent.c'),('planner',D/'ZornGpuStartupPlan.c')]:
  args=list(rec['arguments']);args[args.index(rec['file'])]=str(path);obj=O/(name+'.o');args[args.index('-o')+1]=str(obj);args+=['-I'+str(O),'-I'+str(D),'-mgeneral-regs-only']
  run(args,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(args,name+'-independent',rec['directory']);assert sha(first)==sha(obj);objects[name]=sha(obj)
  sections=run(['otool','-l',obj],name+'-sections');assert '__mod_init_func' not in sections
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
 run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',O/'extent.o',O/'planner.o','-o',O/'extent-and-real-planner.o'],'link');imports=run(['nm','-u',O/'extent-and-real-planner.o'],'imports').split();assert not any('ZGPlan' in n or 'NativeAdreno' in n for n in imports);assert set(imports)<=set(['_memcpy','_memcmp','___stack_chk_fail','___stack_chk_guard'])
 (O/'check-result.json').write_text(json.dumps(dict(source_controls=source_controls,actual_extent_source_negatives=negative,independent_objects=objects,inputs=inputs,commands=commands,remaining_imports=imports,no_initializer=True,no_generated_or_exported_addresses=True,no_allocator_mapping_callback_or_phone_calls=True,only_supplied_size_arithmetic_not_native_observation=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('New Gen7 extent/source contract checked;3 reference/3 executable corruptions refuse;2 fresh iOS17 objects independently match;zero native calls')
if __name__=='__main__':main()
