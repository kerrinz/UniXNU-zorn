#!/usr/bin/env python3
"""Isolated CPU backing source/target inspection; never runs native allocator."""
from pathlib import Path
import json,hashlib,subprocess,shlex,shutil,re
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-runtime-cpu-prepare';P=R/'out/zorn/gpu-runtime-backing-registry';D=R/'out/zorn/gpu-discovery-20261030/startup-contract';N=R/'UniXNU/drivers/NativeAdreno'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def main():
 if (O/'check-result.json').exists():raise SystemExit('Completed; do not repeat')
 commands=[]
 def run(a,name,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p
 # Only scalar host declarations; real NativeAdrenoMemory class, no allocator double.
 shutil.copytree(P/'host-include',O/'host-include',dirs_exist_ok=True)
 flags=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined'];inc=['-I'+str(O/'host-include'),'-I'+str(N),'-I'+str(D),'-I'+str(O)]
 run(['clang','-std=c11',*flags,'-c',D/'ZornGpuStartupPlan.c','-o',O/'planner-host.o'],'planner-host-dependency')
 def host(source,name,extra=(),good=True):
  exe=O/name
  p=run(['clang++','-std=c++17',*flags,*inc,*extra,source,O/'test-policy.cpp',O/'planner-host.o','-o',exe],name+'-build',good=good)
  return exe,p
 exe,_=host(O/'ZornGpuRuntimeBackings.cpp','test-policy');result=run([exe],'policy-run')
 original=(O/'ZornGpuRuntimeBackings.cpp').read_text();neg=[]
 for name,a,b in [('secure-flags-admitted','(q.flags&~UINT32_C(768))','false'),('width-check-removed','||!width||','||(!width&&false)||')]:
  assert original.count(a)==1;source=O/(name+'.cpp');source.write_text(original.replace(a,b));exe,_=host(source,name);p=run([exe],name+'-refused',good=False);neg.append(dict(name=name,stage='actual-source-policy-execution',returncode=p.returncode))
 _,p=host(O/'ZornGpuRuntimeBackings.cpp','native-ON-host-link-refused',['-DZGBR_CPU_PREPARE_COMPILE_ONLY=1'],good=False)
 assert 'allocate' in p.stderr;neg.append(dict(name='native-ON-host-link-refused-without-stubs',stage='link',returncode=p.returncode))
 recipe=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';d=json.JSONDecoder().raw_decode(recipe.read_text())[0]
 assert '--target=arm64-apple-ios17.0.0' in d['arguments']
 def args(source,obj,selected):
  a=list(d['arguments']);a[a.index(d['file'])]=str(source);a[a.index('-o')+1]=str(obj)
  return a+['-I'+str(O),'-I'+str(N),'-I'+str(D),'-mgeneral-regs-only','-DZGBR_CPU_PREPARE_COMPILE_ONLY='+str(selected)]
 objects={};inputs={str(recipe):sha(recipe),str(N/'NativeAdrenoMemory.cpp'):sha(N/'NativeAdrenoMemory.cpp')}
 for selected in [0,1]:
  obj=O/('prepare-'+str(selected)+'.o');a=args(O/'ZornGpuRuntimeBackings.cpp',obj,selected)
  run(a,'target-'+str(selected)+'-first',d['directory']);first=O/('prepare-'+str(selected)+'-first.o');first.write_bytes(obj.read_bytes());run(a,'target-'+str(selected)+'-independent',d['directory']);assert sha(obj)==sha(first)
  imports=run(['nm','-u',obj],'imports-'+str(selected)).stdout.split();allocate=[x for x in imports if 'NativeAdrenoMemory8allocate' in x]
  assert len(allocate)==selected
  assert not any(t in n for n in imports for t in ['release','holdForDevice','reservePool','makeWriteCombined','importTask'])
  dis=run(['otool','-tvV',obj],'disassembly-'+str(selected)).stdout
  instructions='\n'.join(l.split('\t',1)[-1] for l in dis.splitlines() if re.match(r'^[0-9a-f]{16}\s',l));assert not re.search(r'\b(?:v\d+\.|[qdsbh]\d+)\b',instructions)
  objects[str(selected)]={'sha256':sha(obj),'imports':imports,'independent_raw_SHA_equal':True}
  pp=[];i=0
  while i<len(a):
   if a[i] in ['-o','-MF','-MJ','-MT']:i+=2
   elif a[i]=='-c':i+=1
   else:pp.append(a[i]);i+=1
  dep=O/('prepare-'+str(selected)+'.d');run(pp+['-M','-MF',str(dep),'-MT','input'],'deps-'+str(selected),d['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(d['directory'])/p
   inputs[str(p)]=sha(p)
 storage=O/'storage.cpp';storage.write_text('#include "ZornGpuRuntimeBackings.h"\nconstinit ZornGpuRuntimeBackings zorn_runtime_cpu;\n');run(args(storage,O/'storage-native.o',0),'storage-compile',d['directory']);sections=run(['otool','-l',O/'storage-native.o'],'storage-sections').stdout;assert '__mod_init_func' not in sections
 # Static selected-source invariants, not successful native execution fixtures.
 for token in ['attempted_bytes_+=bytes;report.attempted=1;','report.native_status=native;report.native_status_available=1;','slot.failed=1;memory_[index].quarantine();report.quarantined=1;']:
  assert original.count(token)==1
 assert original.index('report.attempted=1;')<original.index('memory_[index].allocate')<original.index('report.native_status=native;')
 (O/'check-result.json').write_text(json.dumps(dict(host=result.stdout.strip(),new_negative_controls=neg,objects=objects,inputs=inputs,commands=commands,selected_is_compile_only_not_run=True,host_has_no_allocator_object_address_success_double=True,native_allocator_calls=0,persistent_storage_constinit_no_initializer=True,real_native_error_width=32,adapter_error_width=64,cleanup_status_available=0,no_new_FD_kernel_candidate=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('New policy/OFF host checks +3 negative controls and OFF/selected independent iOS17 objects passed;zero native allocation calls')
if __name__=='__main__':main()
