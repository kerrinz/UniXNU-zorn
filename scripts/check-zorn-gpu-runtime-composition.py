#!/usr/bin/env python3
"""Private backing/Gen7 reservation composition; executes no native methods."""
from pathlib import Path
import json,hashlib,subprocess,importlib.util,re,shlex
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-gmu-runtime-composition';P=R/'UniXNU-zorn/native/gpu-owned/runtime';G=P/'gmu';N=R/'UniXNU/drivers/NativeAdreno'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('extent_util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
def audit(s):
 b=util.body(s,'ZornGpuGmuRuntime::rememberGmu')
 assert b.index('if(!compiledCpuPrepareSelected())return GmuModeMismatch;')<b.index('memory_[index].bytes()'),'compiled CPU mode before native getters'
 assert '!cpu.native_status_available||cpu.native_status!=kIOReturnSuccess' in b and '!cpu.backed||!cpu.cpu_prepared||cpu.quarantined' in b,'actual CPU success/prepared evidence required'
 assert b.index('cpu.cpu_prepared')<b.index('memory_[index].bytes()'),'prepared before native getter'
 assert 'uint64_t bytes=memory_[index].bytes();' in b,'real native backing count'
 assert 'report.local_index=local;report.local_index_available=1;' in b,'successful local index recorded for retention'
 retain=util.body(s,'ZornGpuGmuRuntime::retainGmuLocked')
 assert 'ledger_.retainFailure(report.local_index,error)' in retain,'failure retains rounded interval'
 assert 'report.retention_result=result;report.retention_result_available=1;' in retain,'preserve original ledger retention result'
 assert '.native_map_status_available=' not in s and '.mapping_complete=' not in s,'no manufactured mapping result'
def main():
 if (O/'check-result.json').exists():raise SystemExit('completed; do not repeat')
 pins=json.loads((O/'source-preimages.json').read_text())
 for p,h in pins.items():assert sha(Path(p))==h,p
 # Existing CPU allocator policy/return/error logic is unchanged, not re-tested
 # by replaying the old CPU suite. A new type avoids duplicate old symbols.
 old=(O/'preimages/ZornGpuRuntimeBackings.cpp').read_text().replace('ZornGpuRuntimeBackings','ZornGpuGmuRuntime');s=(O/'ZornGpuGmuRuntime.cpp').read_text()
 for method in ['reserve','snapshot','copyFailure','checkCpuPolicy','prepareCpu','copyCpuReport']:
  assert util.body(old,'ZornGpuGmuRuntime::'+method)==util.body(s,'ZornGpuGmuRuntime::'+method),method
 audit(s);controls=[]
 for name,a,b in [('CPU-prepared-gate-erased','||!cpu.cpu_prepared',''),('bytes-supplied-from-plan','uint64_t bytes=memory_[index].bytes();','uint64_t bytes=slot.requirement.rounded_size;'),('local-index-availability-lost','report.local_index=local;report.local_index_available=1;','report.local_index=local;report.local_index_available=0;'),('retention-result-zeroed','report.retention_result=result;report.retention_result_available=1;','report.retention_result=0;report.retention_result_available=1;')]:
  assert s.count(a)==1
  try:audit(s.replace(a,b))
  except (AssertionError,ValueError) as e:controls.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('source corruption survived '+name)
 commands=[]
 def run(args,name,cwd=R,good=True):
  args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=args,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p.stdout+p.stderr
 inc=O/'host-include/IOKit';inc.mkdir(parents=True,exist_ok=True);(inc/'IOTypes.h').write_bytes((R/'out/zorn/gpu-runtime-backing-registry/host-include/IOKit/IOTypes.h').read_bytes())
 flags=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined'];includes=['-I'+str(O),'-I'+str(P),'-I'+str(G),'-I'+str(N),'-I'+str(O/'host-include')]
 for name,path in [('extent',G/'ZornGpuGmuExtent.c'),('planner',P/'ZornGpuStartupPlan.c')]:run(['clang','-std=c11',*flags,*includes,'-c',path,'-o',O/(name+'-host.o')],name+'-host-dependency')
 def host(source,name,mixed=False,cpu=False,good=True):
  args=['clang++','-std=c++17',*flags,*includes,source,O/'ZornGpuGmuReservations.cpp',O/'test-composition.cpp',O/'extent-host.o',O/'planner-host.o','-o',O/name]
  if mixed:args+=['-DZGGMU_RECORD_COMPILE_ONLY=1','-DTEST_MIXED=1']
  if cpu:args+=['-DZGBR_CPU_PREPARE_COMPILE_ONLY=1']
  log=run(args,name+'-build',good=good);return O/name,log
 for name,mixed in [('default-OFF',False),('mixed-CPU-OFF',True)]:exe,_=host(O/'ZornGpuGmuRuntime.cpp',name,mixed);run([exe],name+'-run')
 hostneg=[]
 for name,a,b,mixed in [('mode-check-erased','if(!compiledCpuPrepareSelected())return GmuModeMismatch;','if(false)return GmuModeMismatch;',True),('OFF-forged-success','(void)index;(void)request;return Disabled;','(void)index;(void)request;return Ok;',False)]:
  assert s.count(a)==1;p=O/(name+'.cpp');p.write_text(s.replace(a,b));exe,_=host(p,name,mixed);run([exe],name+'-refused',good=False);hostneg.append(name)
 _,log=host(O/'ZornGpuGmuRuntime.cpp','selected-host-link-refused',True,True,good=False);assert 'allocate' in log
 B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';recipes={};inputs=dict(pins)
 for kind,rel in [('cxx','iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'),('c','bsd/DEVELOPMENT/bsd_init.o.json')]:
  p=B/rel;inputs[str(p)]=sha(p);recipes[kind]=json.JSONDecoder().raw_decode(p.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in recipes[kind]['arguments']
 storage=O/'storage-ABI.cpp';storage.write_text('#include "ZornGpuGmuRuntime.h"\n#include "ZornGpuRuntimeBackings.h"\nstatic_assert(sizeof(ZornGpuGmuRuntime::CpuReport)==sizeof(ZornGpuRuntimeBackings::CpuReport));\nstatic_assert(__is_same(decltype(ZornGpuGmuRuntime::CpuReport::native_status),IOReturn));\nstatic_assert(sizeof(ZornGpuGmuRuntime::GmuReport::adapter_error)==8);\nconstinit ZornGpuGmuRuntime zorn_gmu_runtime;\n')
 objects={};sources=[(f'owner-{cpu}{gmu}',O/'ZornGpuGmuRuntime.cpp','cxx',cpu,gmu) for cpu,gmu in [(0,0),(0,1),(1,0),(1,1)]]+[(name,path,kind,0,0) for name,path,kind in [('ledger',O/'ZornGpuGmuReservations.cpp','cxx'),('extent',G/'ZornGpuGmuExtent.c','c'),('planner',P/'ZornGpuStartupPlan.c','c'),('storage-ABI',storage,'cxx')]]
 for name,path,kind,cpu,gmu in sources:
  rec=recipes[kind];args=list(rec['arguments']);args[args.index(rec['file'])]=str(path);obj=O/(name+'.o');args[args.index('-o')+1]=str(obj);args+=['-I'+str(O),'-I'+str(P),'-I'+str(G),'-I'+str(N),'-mgeneral-regs-only']
  if name.startswith('owner-'):args+=['-DZGBR_CPU_PREPARE_COMPILE_ONLY='+str(cpu),'-DZGGMU_RECORD_COMPILE_ONLY='+str(gmu)]
  run(args,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(args,name+'-independent',rec['directory']);assert sha(first)==sha(obj)
  sections=run(['otool','-l',obj],name+'-sections');assert '__mod_init_func' not in sections
  imports=run(['nm','-u',obj],name+'-imports').split()
  if name.startswith('owner-'):
   native=[n for n in imports if 'NativeAdreno' in n and not n.startswith('__ZN22ZornGpuGmuReservations')];assert len(native)==cpu and all('allocate' in n for n in native)
  else:assert not any('NativeAdreno' in n for n in imports)
  dis=run(['otool','-tvV',obj],name+'-disassembly');instructions='\n'.join(l.split('\t',1)[-1] for l in dis.splitlines() if re.match(r'^[0-9a-f]{16}\s',l));assert not re.search(r'\b(?:v\d+\.|[qdsbh]\d+)\b',instructions)
  objects[name]=dict(sha256=sha(obj),imports=imports,same_path_independent_raw_SHA=True)
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
 graphs={}
 for mode in ['00','01','10','11']:
  out=O/('composition-'+mode+'.o');run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',O/('owner-'+mode+'.o'),O/'ledger.o',O/'extent.o',O/'planner.o','-o',out],mode+'-link');imports=run(['nm','-u',out],mode+'-imports').split();allowed={'_memcmp','_memcpy','___stack_chk_guard','___stack_chk_fail'};native=[n for n in imports if 'NativeAdreno' in n and not n.startswith('__ZN22ZornGpuGmuReservations')];assert len(native)==int(mode[0]) and all('allocate' in n for n in native);assert set(imports)-set(native)<=allowed;graphs[mode]=imports
 for p,h in pins.items():assert sha(Path(p))==h,p
 (O/'check-result.json').write_text(json.dumps(dict(commands=commands,inputs=inputs,objects=objects,graphs=graphs,new_static_source_corruptions_refused=controls,new_host_negatives=hostneg,selected_host_link_without_native_allocator_stubs_refused=True,unchanged_original_CPU_methods_source_verified=True,no_initializer_or_SIMD=True,no_native_getter_allocator_provider_phone_calls=True,no_successful_backing_address_handle_model=True,no_public_object_pointer_range_accessor=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('Private owner OFF/mixed guards +2 host/4 source refusals/ON link refusal;8 independent iOS17 objects and4 closed helper graphs;zero native methods')
if __name__=='__main__':main()
