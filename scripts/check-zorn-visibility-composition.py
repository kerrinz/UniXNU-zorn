#!/usr/bin/env python3
"""New default-OFF composition tests; forbidden native entry only has a trap."""
from pathlib import Path
import json,hashlib,subprocess,shlex,shutil,re
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-visibility-composition/corrected';N=R/'UniXNU/drivers/NativeAdreno';K=R/'UniXNU/kits/ArmSmmu4K'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def inspect(s):
 tokens=['if(!report_.publisher_mode_selected)','report_.native_attempted=1;','report_.native_return=native;report_.native_status_available=1;','int bound=publisher_.bind(memory,&fresh);','*out=fresh;report_.callback_exported=1;','s->poisoned=1;m->quarantine();','!separate(this,sizeof(*this),pool,poolbytes)']
 for t in tokens:
  if t not in s:raise ValueError('lost composition condition '+t)
 assert s.index('publisher_.selectedMode()')<s.index('NativeAdrenoPrepareSmmuMemory(')<s.index('publisher_.bind(memory,&fresh)')<s.index('*out=fresh;')
def main():
 if (O/'check-result.json').exists():raise SystemExit('Completed; do not repeat')
 commands=[]
 def run(a,n,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,cwd=str(cwd),returncode=p.returncode));(O/(n+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p
 pins=json.loads((O/'source-preimages.json').read_text());assert all(sha(Path(p))==h for p,h in pins.items())
 shutil.copytree(R/'out/zorn/gpu-runtime-backing-registry/host-include',O/'host-include',dirs_exist_ok=True)
 inc=['-I'+str(O),'-I'+str(O/'host-include'),'-I'+str(N),'-I'+str(K)];flags=['-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined']
 pub=O/'ZornGpuTableVisibility.cpp';bridge=O/'ZornGpuTablePreparation.cpp';s=bridge.read_text();inspect(s)
 run(['clang++',*flags,*inc,'-c',pub,'-o',O/'publisher-off-host.o'],'host-publisher-OFF')
 def host(source,name,select,good=True):
  exe=O/name;run(['clang++',*flags,*inc,'-DZORN_TABLE_PREPARE_COMPILE_ONLY='+str(select),*(['-DTEST_MIXED'] if select else []),source,O/'publisher-off-host.o',O/'test-config.cpp','-o',exe],name+'-build');return run([exe],name+'-run',good=good)
 host(bridge,'host-OFF',0);host(bridge,'host-mixed',1)
 run(['clang++',*flags,*inc,'-DZORN_NATIVE_VISIBILITY_COMPILE_ONLY=1','-c',pub,'-o',O/'publisher-ON-host.o'],'host-publisher-ON-config-only')
 for name,select in [('reverse-mixed',0),('selected-invalid',1)]:
  exe=O/('host-'+name)
  run(['clang++',*flags,*inc,'-DZORN_TABLE_PREPARE_COMPILE_ONLY='+str(select),*(['-DEXTRA_SELECTED'] if select else []),bridge,O/'publisher-ON-host.o',O/'test-config-extra.cpp','-o',exe],name+'-host-build')
  run([exe],name+'-host-run')
 neg=[]
 for name,old,new,select in [('mode-gate-removed','if(!report_.publisher_mode_selected)','if(false)',1),('OFF-success-forged','report_.adapter_error=Disabled;leave();return Disabled;','report_.adapter_error=Disabled;leave();return Ok;',0)]:
  assert s.count(old)==1;bad=O/(name+'.cpp');bad.write_text(s.replace(old,new));p=host(bad,name,select,False);neg.append(dict(name=name,returncode=p.returncode))
 static=[]
 for name,old,new in [('prepare-result-lost','report_.native_return=native;report_.native_status_available=1;','/* result lost */'),('legacy-callback-leaked','*out=fresh;report_.callback_exported=1;','*out=legacy_;report_.callback_exported=1;'),('failed-pool-not-retained','s->poisoned=1;m->quarantine();','/* retention missing */'),('owner-pool-alias-allowed','||!separate(this,sizeof(*this),pool,poolbytes)','')]:
  assert s.count(old)==1;bad=s.replace(old,new);(O/(name+'.cpp')).write_text(bad)
  try:inspect(bad)
  except (ValueError,AssertionError) as e:static.append(dict(name=name,refused=str(e)))
  else:raise ValueError('source corruption survived '+name)
 recipe=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';d=json.JSONDecoder().raw_decode(recipe.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in d['arguments'];inputs={str(recipe):sha(recipe),**pins};objects={}
 for who,source,macro in [('bridge',bridge,'ZORN_TABLE_PREPARE_COMPILE_ONLY'),('publisher',pub,'ZORN_NATIVE_VISIBILITY_COMPILE_ONLY')]:
  for select in [0,1]:
   name=who+'-'+str(select);obj=O/(name+'.o');a=list(d['arguments']);a[a.index(d['file'])]=str(source);a[a.index('-o')+1]=str(obj);a+=['-I'+str(O),'-I'+str(N),'-I'+str(K),'-mgeneral-regs-only','-D'+macro+'='+str(select)]
   run(a,name+'-first',d['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(a,name+'-independent',d['directory']);assert sha(obj)==sha(first)
   imports=run(['nm','-u',obj],name+'-imports').stdout.split()
   if who=='bridge':assert len([x for x in imports if 'NativeAdrenoPrepareSmmuMemory' in x])==select
   else:assert len([x for x in imports if 'publishForDevice' in x])==select
   assert not any(t in n for n in imports for t in ['allocate','holdForDevice','release','SetPages','mapInto','unmap'])
   dis=run(['otool','-tvV',obj],name+'-disassembly').stdout;ins='\n'.join(l.split('\t',1)[-1] for l in dis.splitlines() if re.match(r'^[0-9a-f]{16}\s',l));assert not re.search(r'\b(?:v\d+\.|[qdsbh]\d+)\b',ins)
   objects[name]=dict(sha256=sha(obj),independent_raw_SHA_equal=True,imports=imports)
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
 for mode,b,p in [('OFF',0,0),('mixed',1,0),('reverse-mixed',0,1),('selected',1,1)]:
  out=O/('composition-'+mode+'.o');run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',O/('bridge-'+str(b)+'.o'),O/('publisher-'+str(p)+'.o'),'-o',out],mode+'-link');imports=run(['nm','-u',out],mode+'-imports').stdout.split()
  assert not any('ZornGpu' in n for n in imports)
  if mode=='OFF':assert not any('NativeAdreno' in n for n in imports)
 storage=O/'storage.cpp';storage.write_text('#include "ZornGpuTablePreparation.h"\nconstinit ZornGpuTablePreparation zorn_table_preparation;\n');a=list(d['arguments']);a[a.index(d['file'])]=str(storage);a[a.index('-o')+1]=str(O/'storage.o');a+=['-I'+str(O),'-I'+str(N),'-I'+str(K),'-mgeneral-regs-only'];run(a,'constinit-storage',d['directory']);assert '__mod_init_func' not in run(['otool','-l',O/'storage.o'],'storage-sections').stdout
 for p in [N/'NativeAdrenoSmmuMemory.cpp',N/'NativeAdrenoMemory.cpp']:inputs[str(p)]=sha(p)
 (O/'check-result.json').write_text(json.dumps(dict(commands=commands,inputs=inputs,objects=objects,host_OFF_and_mixed_guard_passed=True,forbidden_entry_trap_never_entered_in_passing_tests=True,no_successful_native_prepare_publisher_address_model=True,new_host_negatives=neg,new_static_corruptions=static,constinit_storage_no_initializer=True,native_API_callback_cache_or_phone_invocation=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('New OFF/mixed-mode guards +2 host negatives/4 static corruptions passed;4 independent iOS17 objects and4 relocatable modes checked;zero native calls')
if __name__=='__main__':main()
