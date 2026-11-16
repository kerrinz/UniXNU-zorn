#!/usr/bin/env python3
"""Gen7 CPU-only supplied-reservation bookkeeping; never maps or calls native methods."""
from pathlib import Path
import hashlib,json,subprocess,shlex,shutil,re
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-gen7-reservation-ledger';P=R/'UniXNU-zorn/native/gpu-owned/runtime';G=P/'gmu';N=R/'UniXNU/drivers/NativeAdreno'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def main():
 if (O/'check-result.json').exists():raise SystemExit('completed; do not repeat')
 pins={str(p):sha(p) for p in [N/'NativeAdrenoMemory.h',G/'ZornGpuGmuExtent.h',G/'ZornGpuGmuExtent.c',P/'ZornGpuStartupPlan.h',P/'ZornGpuStartupPlan.c',P/'source-profile.json',G/'source-profile.json']};(O/'source-preimages.json').write_text(json.dumps(pins,indent=2)+'\n')
 inc=O/'host-include/IOKit';inc.mkdir(parents=True,exist_ok=True);src=R/'out/zorn/gpu-runtime-backing-registry/host-include/IOKit/IOTypes.h';(inc/'IOTypes.h').write_bytes(src.read_bytes())
 commands=[]
 def run(args,name,cwd=R,good=True):
  args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=args,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p.stdout+p.stderr
 flags=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined'];includes=['-I'+str(O),'-I'+str(N),'-I'+str(P),'-I'+str(G),'-I'+str(O/'host-include')]
 for name,path in [('extent',G/'ZornGpuGmuExtent.c'),('planner',P/'ZornGpuStartupPlan.c')]:run(['clang','-std=c11',*flags,*includes,'-c',path,'-o',O/(name+'-host.o')],name+'-host-dependency')
 def host(path,name):
  exe=O/name;run(['clang++','-std=c++17',*flags,*includes,path,O/'test-ledger.cpp',O/'extent-host.o',O/'planner-host.o','-o',exe],name+'-build');return exe
 run([host(O/'ZornGpuGmuReservations.cpp','ledger-host')],'ledger-host-run');source=(O/'ZornGpuGmuReservations.cpp').read_text();neg=[]
 for name,a,b in [('rounded-tail-reused','a.reservation_bytes:','a.backing_bytes:'),('geometry-drift-admitted','memcmp(&old.reservation,reservation,sizeof(*reservation))','0'),('failed-retry-admitted','if(old.failed){leave();return Retained;}','if(false){leave();return Retained;}'),('first-local-error-overwritten','if(entry.failed){leave();return Retained;}','if(false){leave();return Retained;}')]:
  assert source.count(a)==1;p=O/(name+'.cpp');p.write_text(source.replace(a,b));run([host(p,name)],name+'-refused',good=False);neg.append(name)
 B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';recipes={};inputs=dict(pins)
 for kind,rel in [('cxx','iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'),('c','bsd/DEVELOPMENT/bsd_init.o.json')]:
  p=B/rel;inputs[str(p)]=sha(p);recipes[kind]=json.JSONDecoder().raw_decode(p.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in recipes[kind]['arguments']
 storage=O/'storage.cpp';storage.write_text('#include "ZornGpuGmuReservations.h"\nstatic_assert(sizeof(ZornGpuGmuReservations::Summary)==32);\nstatic_assert(sizeof(ZornGpuGmuReservations::Failure)==16);\nstatic_assert(sizeof(ZornGpuGmuReservations::Failure::adapter_error)==8);\nconstinit ZornGpuGmuReservations zorn_gmu_reservations;\n')
 objects={}
 for name,path,kind in [('ledger',O/'ZornGpuGmuReservations.cpp','cxx'),('extent',G/'ZornGpuGmuExtent.c','c'),('planner',P/'ZornGpuStartupPlan.c','c'),('storage-ABI',storage,'cxx')]:
  rec=recipes[kind];args=list(rec['arguments']);args[args.index(rec['file'])]=str(path);obj=O/(name+'.o');args[args.index('-o')+1]=str(obj);args+=['-I'+str(O),'-I'+str(N),'-I'+str(P),'-I'+str(G),'-mgeneral-regs-only'];run(args,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(args,name+'-independent',rec['directory']);assert sha(first)==sha(obj)
  sections=run(['otool','-l',obj],name+'-sections');assert '__mod_init_func' not in sections
  imports=run(['nm','-u',obj],name+'-imports').split();assert not any('NativeAdreno' in n for n in imports)
  dis=run(['otool','-tvV',obj],name+'-disassembly');instructions='\n'.join(l.split('\t',1)[-1] for l in dis.splitlines() if re.match(r'^[0-9a-f]{16}\s',l));assert not re.search(r'\b(?:v\d+\.|[qdsbh]\d+)\b',instructions)
  objects[name]=dict(sha256=sha(obj),imports=imports,independent_raw_SHA=True)
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
 run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',O/'ledger.o',O/'extent.o',O/'planner.o','-o',O/'ledger-closure.o'],'component-link');imports=run(['nm','-u',O/'ledger-closure.o'],'component-imports').split();assert set(imports)<=set(['_memcmp','_memcpy','___stack_chk_fail','___stack_chk_guard'])
 rec=recipes['cxx']
 for method in ['reset','release']:
  path=O/(method+'-absent.cpp');path.write_text('#include "ZornGpuGmuReservations.h"\nvoid forbidden(ZornGpuGmuReservations &r){r.'+method+'();}\n');args=list(rec['arguments']);args[args.index(rec['file'])]=str(path);args[args.index('-o')+1]=str(O/(method+'-absent.o'));args+=['-I'+str(O),'-I'+str(N),'-I'+str(P),'-I'+str(G),'-mgeneral-regs-only'];log=run(args,method+'-API-refused',rec['directory'],good=False);assert 'no member named' in log and method in log
 for p,h in pins.items():assert sha(Path(p))==h,p
 (O/'check-result.json').write_text(json.dumps(dict(commands=commands,inputs=inputs,objects=objects,new_actual_source_negatives=neg,reset_and_release_API_compile_refused=True,no_initializer_or_SIMD=True,remaining_component_imports=imports,host_uses_real_deliberately_unbacked_native_types=True,host_successful_allocator_mapping_address_handle_model=False,no_address_generation_or_output=True,native_methods_or_phone_calls=0,native_attempted=0,native_status_available=0,mapping_complete=0,runtime_complete=0,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('New rounded-tail/retained metadata checks +4 actual-source/2 missing-API refusals passed;4 independent current iOS17 objects;zero native methods/address outputs')
if __name__=='__main__':main()
