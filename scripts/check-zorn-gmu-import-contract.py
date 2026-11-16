#!/usr/bin/env python3
"""New native import/lifetime binding and isolated rollback repair inspection."""
from pathlib import Path
import json,hashlib,subprocess,shlex,re
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-gmu-import-contract';N=R/'UniXNU/drivers/NativeAdreno'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def inspect(source):
 for s in ['if(map_attempted_ || failure_latched_)return kIOReturnBusy;','map_attempted_=true;','if(vm->poisoned())return status;','cleanup_.status[previous]=rollback;','if(rollback==kIOReturnSuccess) {','} else break;','if(failure_latched_)return kIOReturnBusy;','for(uint64_t handle:handles_)if(handle)return kIOReturnBusy;']:
  if s not in source:raise ValueError('lost failure protection: '+s)
 block=source[source.index('const IOReturn rollback='):source.index('return status;',source.index('const IOReturn rollback='))]
 if block.index('handles_[previous]=0;')<block.index('if(rollback==kIOReturnSuccess)'):raise ValueError('handle lost on failed cleanup')
 if 'vm->unmap(handles_[previous]);handles_[previous]=0' in source:raise ValueError('unconditional handle erase')
def main():
 if (O/'check-result.json').exists():raise SystemExit('Completed; do not repeat')
 commands=[];inputs={}
 def run(a,name,cwd):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr);p.check_returncode();return p.stdout
 pins=json.loads((O/'source-preimages.json').read_text());assert all(sha(Path(p))==h for p,h in pins.items());source=(O/'NativeAdrenoGmuMemory.cpp').read_text();inspect(source);neg=[]
 for name,a,b in [('unmap-status-ignored','if(rollback==kIOReturnSuccess) {','if(true) {'),('poison-ignored','if(vm->poisoned())return status;','/* poison guard missing */'),('retry-allowed','if(map_attempted_ || failure_latched_)return kIOReturnBusy;','/* retry allowed */'),('cleanup-raw-lost','cleanup_.status[previous]=rollback;','/* status lost */')]:
  assert source.count(a)==1;s=source.replace(a,b);(O/(name+'.cpp')).write_text(s)
  try:inspect(s)
  except ValueError as e:neg.append(dict(name=name,refused=str(e)))
  else:raise ValueError('semantic mutation survived '+name)
 recipe=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';inputs[str(recipe)]=sha(recipe);d=json.JSONDecoder().raw_decode(recipe.read_text())[0];objects={}
 assert '--target=arm64-apple-ios17.0.0' in d['arguments']
 for name,path,local in [('gmu-original',N/'NativeAdrenoGmuMemory.cpp',False),('gmu-retained-candidate',O/'NativeAdrenoGmuMemory.cpp',True),('smmu-visibility-original',N/'NativeAdrenoSmmuMemory.cpp',False)]:
  a=list(d['arguments']);a[a.index(d['file'])]=str(path);obj=O/(name+'.o');a[a.index('-o')+1]=str(obj);a+=['-I'+str(N),'-I'+str(R/'UniXNU/kits/ArmSmmu4K'),'-mgeneral-regs-only']
  if local:a.insert(1,'-I'+str(O))
  run(a,name+'-first',d['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(a,name+'-independent',d['directory']);assert sha(obj)==sha(first);imports=run(['nm','-u',obj],name+'-imports',R).split();objects[name]=dict(source=str(path),sha256=sha(obj),independent_raw_SHA_equal=True,imports=imports)
  dis=run(['otool','-tvV',obj],name+'-disassembly',R);instructions='\n'.join(l.split('\t',1)[-1] for l in dis.splitlines() if re.match(r'^[0-9a-f]{16}\s',l));assert not re.search(r'\b(?:v\d+\.|[qdsbh]\d+)\b',instructions)
  pp=[];i=0
  while i<len(a):
   if a[i] in ['-o','-MF','-MJ','-MT']:i+=2
   elif a[i]=='-c':i+=1
   else:pp.append(a[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',str(dep),'-MT','input'],name+'-deps',d['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(d['directory'])/p
   inputs[str(p)]=sha(p)
 inputs.update(pins)
 result=dict(objects=objects,inputs=inputs,commands=commands,new_source_semantic_mutations_refused=neg,no_host_mapping_address_or_handle_success_model=True,no_allocator_VM_provider_method_invoked=True,original_upstream_files_unchanged=True,legacy_layout_not_K80_adapter=True,candidate_is_unselected_source_inspection_only=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'check-result.json').write_text(json.dumps(result,indent=2)+'\n');print('Three new actual native objects independently match;4 failure-protection corruptions refused; no maps or models executed')
if __name__=='__main__':main()
