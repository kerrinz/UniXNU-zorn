#!/usr/bin/env python3
"""Default-OFF/native compile-only visibility publisher inspection; no callback run."""
from pathlib import Path
import hashlib,json,subprocess,shlex,shutil,re
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-native-visibility-publisher';N=R/'UniXNU/drivers/NativeAdreno';K=R/'UniXNU/kits/ArmSmmu4K'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def inspect(s):
 for token in ['report_.last_native_status=native;report_.native_status_available=1;','if(!report_.first_native_error_available){report_.first_native_error=native;report_.first_native_error_available=1;}','bytes!=4096','memory_->deviceReferences()','!memory_->imported()&&!memory_->writeCombined()','report_.native_status_attempt=report_.callback_attempts;']:
  if token not in s:raise ValueError('lost native visibility protection '+token)
 if s.index('report_.last_native_status=native;')>s.index('if(native!=kIOReturnSuccess)'):raise ValueError('native result saved too late')
def main():
 if (O/'check-result.json').exists():raise SystemExit('Completed; do not repeat')
 commands=[]
 def run(a,name,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,cwd=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0
  return p
 shutil.copytree(R/'out/zorn/gpu-runtime-backing-registry/host-include',O/'host-include',dirs_exist_ok=True)
 flags=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined'];inc=['-I'+str(O),'-I'+str(O/'host-include'),'-I'+str(N),'-I'+str(K)]
 def host(source,name,extra=(),good=True):
  exe=O/name;p=run(['clang++','-std=c++17',*flags,*inc,*extra,source,O/'test-off.cpp','-o',exe],name+'-build',good=good);return exe,p
 source=O/'ZornGpuTableVisibility.cpp';s=source.read_text();inspect(s);exe,_=host(source,'test-off');hostresult=run([exe],'off-run').stdout
 bad=O/'OFF-success-forged.cpp';assert s.count('leave();return Disabled;')==1;bad.write_text(s.replace('leave();return Disabled;','leave();return Ok;'));exe,_=host(bad,'OFF-success-forged');run([exe],'OFF-success-refused',good=False)
 _,p=host(source,'ON-host-link',['-DZORN_NATIVE_VISIBILITY_COMPILE_ONLY=1'],False);assert 'publishForDevice' in p.stderr
 static=[]
 for name,a,b in [('native-result-lost','report_.last_native_status=native;report_.native_status_available=1;','/* native status lost */'),('first-error-overwritten','if(!report_.first_native_error_available){report_.first_native_error=native;report_.first_native_error_available=1;}','{report_.first_native_error=native;report_.first_native_error_available=1;}'),('page-length-guard-removed','bytes!=4096','false')]:
  assert s.count(a)==1;mut=s.replace(a,b);(O/(name+'.cpp')).write_text(mut)
  try:inspect(mut)
  except ValueError as e:static.append(dict(name=name,refused=str(e)))
  else:raise ValueError('surviving source corruption '+name)
 recipe=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';d=json.JSONDecoder().raw_decode(recipe.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in d['arguments'];inputs={str(recipe):sha(recipe)};objects={}
 def args(src,obj,select):
  a=list(d['arguments']);a[a.index(d['file'])]=str(src);a[a.index('-o')+1]=str(obj);return a+['-I'+str(O),'-I'+str(N),'-I'+str(K),'-mgeneral-regs-only','-DZORN_NATIVE_VISIBILITY_COMPILE_ONLY='+str(select)]
 for select in [0,1]:
  obj=O/('visibility-'+str(select)+'.o');a=args(source,obj,select);run(a,'native-'+str(select)+'-first',d['directory']);first=O/('visibility-'+str(select)+'-first.o');first.write_bytes(obj.read_bytes());run(a,'native-'+str(select)+'-independent',d['directory']);assert sha(obj)==sha(first)
  imports=run(['nm','-u',obj],'imports-'+str(select)).stdout.split();assert len([x for x in imports if 'publishForDevice' in x])==select
  assert not any(t in n for n in imports for t in ['allocate','holdForDevice','release','map','SetPages','quarantine'])
  dis=run(['otool','-tvV',obj],'disassembly-'+str(select)).stdout;ins='\n'.join(l.split('\t',1)[-1] for l in dis.splitlines() if re.match(r'^[0-9a-f]{16}\s',l));assert not re.search(r'\b(?:v\d+\.|[qdsbh]\d+)\b',ins)
  objects[str(select)]={'sha256':sha(obj),'imports':imports,'independent_raw_SHA_equal':True}
  pp=[];i=0
  while i<len(a):
   if a[i] in ['-o','-MF','-MJ','-MT']:i+=2
   elif a[i]=='-c':i+=1
   else:pp.append(a[i]);i+=1
  dep=O/('visibility-'+str(select)+'.d');run(pp+['-M','-MF',str(dep),'-MT','input'],'dependencies-'+str(select),d['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(d['directory'])/p
   inputs[str(p)]=sha(p)
 storage=O/'storage.cpp';storage.write_text('#include "ZornGpuTableVisibility.h"\nconstinit ZornGpuTableVisibility zorn_table_visibility;\n');run(args(storage,O/'storage.o',0),'storage-build',d['directory']);sections=run(['otool','-l',O/'storage.o'],'storage-sections').stdout;assert '__mod_init_func' not in sections
 for p in [N/'NativeAdrenoMemory.cpp',N/'NativeAdrenoSmmuMemory.cpp',K/'ArmSmmu4KLive.h']:inputs[str(p)]=sha(p)
 (O/'check-result.json').write_text(json.dumps(dict(host=hostresult.strip(),new_OFF_forged_success_refused=True,new_ON_host_link_refused_without_publisher_stub=True,new_source_corruptions_refused=static,objects=objects,inputs=inputs,commands=commands,constinit_storage_no_initializer=True,callback_or_native_backend_executed=False,no_host_success_publication_address_or_handle_model=True,default_OFF_no_callback_export=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n');print('New OFF-only host checks +2 negatives/3 static corruptions;independent OFF/selected native objects;no callbacks or success models executed')
if __name__=='__main__':main()
