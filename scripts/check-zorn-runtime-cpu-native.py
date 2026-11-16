#!/usr/bin/env python3
"""Fresh iOS17 dependency closure. Static objects only; no runtime/native call."""
from pathlib import Path
import json,hashlib,subprocess,shlex
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-runtime-cpu-native-closure';P=R/'out/zorn/gpu-runtime-cpu-prepare';N=R/'UniXNU/drivers/NativeAdreno';D=R/'out/zorn/gpu-discovery-20261030/startup-contract';B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def main():
 if (O/'compile-result.json').exists():raise SystemExit('Completed; do not repeat')
 commands=[];inputs={};objects={};recipes={}
 def run(a,n,cwd):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,cwd=str(cwd),returncode=p.returncode));(O/(n+'.log')).write_text(p.stdout+p.stderr);p.check_returncode();return p.stdout
 for kind,rel in [('cxx','iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'),('c','bsd/DEVELOPMENT/bsd_init.o.json'),('buffer','iokit/DEVELOPMENT/IOBufferMemoryDescriptor.cpo.json'),('descriptor','iokit/DEVELOPMENT/IOMemoryDescriptor.cpo.json')]:
  path=B/rel;inputs[str(path)]=sha(path);recipes[kind]=json.JSONDecoder().raw_decode(path.read_text())[0]
  assert '--target=arm64-apple-ios17.0.0' in recipes[kind]['arguments']
 for name,source,kind,selected in [('registry',P/'ZornGpuRuntimeBackings.cpp','cxx',True),('memory',N/'NativeAdrenoMemory.cpp','cxx',False),('cpu',N/'NativeAdrenoCpu.cpp','cxx',False),('planner',D/'ZornGpuStartupPlan.c','c',False),('buffer-vtable',Path(recipes['buffer']['file']),'buffer',False),('descriptor-vtable',Path(recipes['descriptor']['file']),'descriptor',False)]:
  d=recipes[kind];a=list(d['arguments']);a[a.index(d['file'])]=str(source);obj=O/(name+'.o');a[a.index('-o')+1]=str(obj)
  a+=['-I'+str(P),'-I'+str(N),'-I'+str(D),'-mgeneral-regs-only']
  if selected:a+=['-DZGBR_CPU_PREPARE_COMPILE_ONLY=1']
  run(a,name+'-first',d['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(a,name+'-independent',d['directory']);assert sha(obj)==sha(first)
  objects[name]={'source':str(source),'source_sha256':sha(source),'object_sha256':sha(obj),'independent_raw_SHA_equal':True}
  inputs[str(source)]=sha(source);pp=[];i=0
  while i<len(a):
   if a[i] in ['-o','-MF','-MJ','-MT']:i+=2
   elif a[i]=='-c':i+=1
   else:pp.append(a[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',str(dep),'-MT','input'],name+'-dependencies',d['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   f=Path(n)
   if not f.is_absolute():f=Path(d['directory'])/f
   inputs[str(f)]=sha(f)
 link=['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',*[O/(n+'.o') for n in ['registry','memory','cpu','planner']],'-o',O/'selected-cpu-backing.o']
 run(link,'new-component-link',R);imports=run(['nm','-u',O/'selected-cpu-backing.o'],'component-imports',R).split()
 assert not any(t in n for n in imports for t in ['NativeAdreno','ZornGpu','ZGPlan'])
 assert not any(t in n for n in imports for t in ['ColdStart','Scm','Pas','Smc','Mmio','__cxa_atexit'])
 sections=run(['otool','-l',O/'selected-cpu-backing.o'],'component-sections',R);assert '__mod_init_func' not in sections
 result=dict(objects=objects,inputs=inputs,commands=commands,component_imports=imports,component_sha256=sha(O/'selected-cpu-backing.o'),no_component_imports_or_initializer=True,no_old_objects_reused=True,actual_current_iOS17_recipe_derivation=True,source_and_objects_not_runtime_qualification=True,native_or_phone_invocation=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'compile-result.json').write_text(json.dumps(result,indent=2)+'\n');print('Six new source objects independently match;4-object selected CPU component closes native/planner imports; no initializer or invocation')
if __name__=='__main__':main()
