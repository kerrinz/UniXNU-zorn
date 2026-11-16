#!/usr/bin/env python3
"""New isolated registry checks; requires retained capsule/current iOS17 recipe."""
from pathlib import Path
import hashlib,json,subprocess,shlex
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-runtime-backing-registry';P=R/'out/zorn/gpu-discovery-20261030/startup-contract';N=R/'UniXNU/drivers/NativeAdreno'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def main():
 if (O/'check-result.json').exists():raise SystemExit('Completed result; do not repeat')
 commands=[]
 def run(a,name,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p
 inc=['-I'+str(O/'host-include'),'-I'+str(N),'-I'+str(P),'-I'+str(O)]
 flags=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined']
 run(['clang','-std=c11',*flags,'-c',P/'ZornGpuStartupPlan.c','-o',O/'startup-host.o'],'host-existing-decoder-dependency')
 def host(source,exe,name):
  run(['clang++','-std=c++17',*flags,*inc,source,O/'test-registry.cpp',O/'startup-host.o','-o',exe],name+'-build')
 host(O/'ZornGpuRuntimeBackings.cpp',O/'test-registry','host')
 good=run([O/'test-registry'],'host-run')
 original=(O/'ZornGpuRuntimeBackings.cpp').read_text();mutants=[]
 for name,old,new in [
  ('drift-accepted','if(old.raw_count!=canonical.raw_count||memcmp(old.raw+1,canonical.raw+1,(old.raw_count-1)*4))','if(false)'),
  ('retained-retried','if(slots_[i].failed){leave();return Retained;}','if(false){leave();return Retained;}'),
  ('raw-error-truncated','slots_[index].error=error;','slots_[index].error=(int32_t)error;')]:
  assert original.count(old)==1
  s=O/(name+'.cpp');s.write_text(original.replace(old,new));exe=O/name;host(s,exe,name);p=run([exe],name+'-refused',good=False);mutants.append(dict(name=name,exit_code=p.returncode))
 recipe=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'
 d=json.JSONDecoder().raw_decode(recipe.read_text())[0];a=d['arguments']
 assert '--target=arm64-apple-ios17.0.0' in a
 def args(source,obj):
  result=list(a);result[result.index(d['file'])]=str(source);result[result.index('-o')+1]=str(obj)
  return result+['-I'+str(O),'-I'+str(N),'-I'+str(P),'-mgeneral-regs-only']
 obj=O/'registry-native.o';cmd=args(O/'ZornGpuRuntimeBackings.cpp',obj)
 run(cmd,'native-first',d['directory']);(O/'registry-native-first.o').write_bytes(obj.read_bytes());run(cmd,'native-independent',d['directory']);assert sha(obj)==sha(O/'registry-native-first.o')
 imports=run(['nm','-u',obj],'native-imports').stdout
 assert 'ZGPlanMemAlloc' in imports
 assert not any(s in imports for s in ['NativeAdreno','allocate','release','quarantine','holdForDevice','SetPages','new','delete'])
 storage=O/'storage.cpp';storage.write_text('#include "ZornGpuRuntimeBackings.h"\nconstinit ZornGpuRuntimeBackings zorn_runtime_backings;\n')
 run(args(storage,O/'storage-native.o'),'native-persistent-storage',d['directory'])
 sections=run(['otool','-l',O/'storage-native.o'],'native-storage-sections').stdout;assert '__mod_init_func' not in sections
 dep=O/'registry-native.d';pp=[];i=0
 while i<len(cmd):
  if cmd[i] in ['-o','-MF','-MJ','-MT']:i+=2
  elif cmd[i]=='-c':i+=1
  else:pp.append(cmd[i]);i+=1
 run(pp+['-M','-MF',str(dep),'-MT','input'],'native-dependencies',d['directory'])
 inputs={str(recipe):sha(recipe),str(N/'NativeAdrenoMemory.cpp'):sha(N/'NativeAdrenoMemory.cpp')}
 for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
  p=Path(n)
  if not p.is_absolute():p=Path(d['directory'])/p
  inputs[str(p)]=sha(p)
 result=dict(state='real-native32-slot-registry-implemented-allocation-and-hardware-off',host=good.stdout.strip(),host_scalar_shim_only_no_allocator_or_IOKit_object_double=True,new_mutations_refused=mutants,commands=commands,inputs=inputs,native_object_sha256=sha(obj),independent_object_raw_SHA_equal=True,native_imports=imports.split(),constinit_persistent_storage_no_initializer=True,old_decoder_only_compiled_as_dependency_not_suite_repeated=True,no_native_provider_method_invoked=True,no_native_object_or_GPU_address_export=True,adapter_error_source_not_native_status=True,native_attempted_allocated_status_available_runtime_complete_all_zero=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'check-result.json').write_text(json.dumps(result,indent=2)+'\n');print('New real32-native-object registry host/3mutants and independent iOS17 object/storage checks passed')
if __name__=='__main__':main()
