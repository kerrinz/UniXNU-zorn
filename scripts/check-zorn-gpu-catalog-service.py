#!/usr/bin/env python3
"""Exact main-pinned Service dependency/type audit;no runtime or provider call."""
from pathlib import Path
import hashlib,importlib.util,json,re,shlex,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-service-dependencies';A=O/'Adreno740';S=O/'catalog-candidate/NativeAdrenoService.cpp'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
MEMBER='\n    NativeAdrenoGpuWindow cp_window_{};   /* retained by IRQ;map/stop lifetime remains external */'
def check(candidate,base):
 assert candidate.count(MEMBER)==1
 restored=candidate.replace(MEMBER,'').replace('cp_window_={','NativeAdrenoGpuWindow cp_window={').replace('&cp_window_,','&cp_window,')
 assert restored==base,'only the remaining CP cookie lifetime changes'
 assert 'NativeAdrenoRingIo cp_io{&cp_window_,gpu_write32,gpu_read32,gpu_barrier,nullptr,nullptr};' in candidate
 for f in ['gpu_read32','gpu_write32','gpu_barrier','gmu_fence_status','ring_publish','fence_acquire','stop','probe','newUserClient']:
  assert util.body(candidate,'NativeAdrenoGpuService::'+f)==util.body(base,'NativeAdrenoGpuService::'+f),f
 assert 'NativeAdrenoGpuWindow ring_window_{};' in candidate
 assert 'gmu_io_bound_?&gmu_io_:nullptr,gmu_io_bound_?gmu_fence_status:nullptr' in candidate

def main():
 if (O/'compile-result.json').exists():raise SystemExit('complete;do not repeat')
 b=(A/'NativeAdrenoService.cpp').read_text();s=S.read_text();check(s,b);neg=[]
 for name,a,c in [('CP-automatic-pointer-restored','&cp_window_,gpu_write32','&cp_window,gpu_write32'),('existing-catalog-fence-hook-removed','gmu_io_bound_?gmu_fence_status:nullptr','nullptr'),('existing-map-teardown-changed','for(auto &map:maps_)map.reset();','/* guessed stop */')]:
  assert a in s
  try:check(s.replace(a,c),b)
  except AssertionError as e:neg.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('new catalog source mutation accepted '+name)
 exported=json.loads((O/'export-manifest.json').read_text())
 for n,e in exported['files'].items():assert sha(A/n)==e['sha256'],n
 for name,data in json.loads((O/'header-export-manifest.json').read_text()).items():
  for n,e in data['files'].items():assert sha(O/'catalog-headers'/name/n)==e['sha256']
 for name,e in json.loads((O/'sm8550-primary-manifest.json').read_text())['files'].items():assert sha(Path(e['local']))==e['sha256']
 cmds=[]
 def run(a,name,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);cmds.append(dict(arguments=a,directory=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  return p
 d=O/'catalog-source-review';d.mkdir();(d/'NativeAdrenoService.cpp').write_bytes((A/'NativeAdrenoService.cpp').read_bytes());run(['git','apply','--no-index','--check',O/'catalog-cp-cookie.UNAPPLIED.patch'],'catalog-patch-check',d);run(['git','apply','--no-index',O/'catalog-cp-cookie.UNAPPLIED.patch'],'catalog-patch-replay',d);assert (d/'NativeAdrenoService.cpp').read_bytes()==S.read_bytes()
 recpath=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';rec=json.JSONDecoder().raw_decode(recpath.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in rec['arguments']
 first=json.loads((O/'first-service-command.json').read_text());assert first['directory']==rec['directory']
 baseargs=first['arguments'];assert str(S) in baseargs and '-mgeneral-regs-only' in baseargs
 inputs={str(recpath):sha(recpath)};objects={};layouts={};imports={}
 def deps(a,name):
  pp=[];i=0
  while i<len(a):
   if a[i] in ['-o','-MF','-MT','-MJ']:i+=2
   elif a[i]=='-c':i+=1
   elif a[i]=='-Xclang' and a[i+1]=='-fdump-record-layouts':i+=2
   else:pp.append(a[i]);i+=1
  p=O/(name+'.d');run(pp+['-M','-MF',p,'-MT','input'],name+'-deps',rec['directory'])
  for n in shlex.split(p.read_text().replace('\\\n',' ').split(':',1)[1]):
   f=Path(n)
   if not f.is_absolute():f=Path(rec['directory'])/f
   inputs[str(f)]=sha(f)
  return pp
 for name,src in [('catalog-service-original',A/'NativeAdrenoService.cpp'),('catalog-service-candidate',S)]:
  a=list(baseargs);a[a.index(str(S))]=str(src);obj=O/(name+'.o');a[a.index('-o')+1]=str(obj)
  if name.endswith('candidate'):
   # The earlier successful compile is the first build,not repeated as a suite.
   oldobj=O/'catalog-service.o';assert oldobj.exists();obj.write_bytes(oldobj.read_bytes());firstlog=(O/'first-service-compile.log').read_text()
  else:firstlog=run(a,name+'-first',rec['directory']).stdout
  copy=O/(name+'-first.o');copy.write_bytes(obj.read_bytes());run(a,name+'-independent',rec['directory']);assert sha(copy)==sha(obj)
  objects[name]=dict(source=str(src),source_sha256=sha(src),object_sha256=sha(obj),independent_raw_SHA_equal=True)
  text=(O/(name+'-independent.log')).read_text();start=text.index('class NativeAdrenoGpuService\n');end=text.find('*** Dumping',start);block=text[start:end if end>=0 else None];m=re.search(r'\[sizeof=(\d+), dsize=(\d+), align=(\d+)',block);assert m;fields={}
  for field in ['ring_window_','cp_window_']:
   q=re.search(r'^\s*(\d+) \|   struct NativeAdrenoGpuWindow '+field+r'\s*$',block,re.M)
   if q:fields[field]=int(q[1])
  layouts[name]=dict(bytes=int(m[1]),dsize=int(m[2]),alignment=int(m[3]),fields=fields)
  imports[name]=run(['nm','-u',obj],name+'-imports').stdout.split();run(['otool','-l',obj],name+'-sections');run(['otool','-tvV',obj],name+'-disassembly');run(['otool','-rv',obj],name+'-relocations');pp=deps(a,name)
  macro=run(pp+['-dM','-E'],name+'-macros',rec['directory']).stdout
  assert not any(re.search(r'^#define '+x+r'\b',macro,re.M) for x in ['NATIVE_ADRENO_HAVE_GMU_RULES','NATIVE_ADRENO_HAVE_GMU_VOTES','NATIVE_ADRENO_HAVE_COMMAND_DB'])
 assert layouts['catalog-service-original']==dict(bytes=3192,dsize=3192,alignment=8,fields={'ring_window_':3176})
 assert layouts['catalog-service-candidate']==dict(bytes=3208,dsize=3208,alignment=8,fields={'ring_window_':3176,'cp_window_':3192})
 assert imports['catalog-service-original']==imports['catalog-service-candidate'],'cookie storage must not add imports'
 abi=O/'catalog-cookie-ABI.cpp';abi.write_text('''/* SPDX-License-Identifier: MIT;static exact catalog type annotation only. */
#include "NativeAdrenoRing.h"
#include "NativeAdrenoIrq.h"
#include <stddef.h>
'''+b[b.index('struct NativeAdrenoGpuWindow {'):b.index('class NativeAdrenoGpuService :')]+'''
using FenceStatus=int(*)(void*,int,uint32_t*);
static_assert(__is_same(decltype(NativeAdrenoRingIo::fence_status),FenceStatus));
static_assert(sizeof(NativeAdrenoRingIo)==48);
static_assert(offsetof(NativeAdrenoRingIo,fence_cookie)==32);
static_assert(offsetof(NativeAdrenoRingIo,fence_status)==40);
static_assert(sizeof(NativeAdrenoGpuWindow)==16 && alignof(NativeAdrenoGpuWindow)==8);
static_assert(offsetof(NativeAdrenoGpuWindow,bytes)==8);
extern "C" const unsigned catalog_cookie_sizes[]={48,32,40,16,8};
''')
 a=list(baseargs);a[a.index(str(S))]=str(abi);a[a.index('-o')+1]=str(O/'catalog-cookie-ABI.o');run(a,'catalog-cookie-ABI-first',rec['directory']);f=O/'catalog-cookie-ABI-first.o';f.write_bytes((O/'catalog-cookie-ABI.o').read_bytes());run(a,'catalog-cookie-ABI-independent',rec['directory']);assert sha(f)==sha(O/'catalog-cookie-ABI.o');deps(a,'catalog-cookie-ABI');assert not run(['nm','-u',O/'catalog-cookie-ABI.o'],'catalog-cookie-ABI-imports').stdout.strip();sections=run(['otool','-l',O/'catalog-cookie-ABI.o'],'catalog-cookie-ABI-sections').stdout;assert '__mod_init_func' not in sections
 objects['catalog-cookie-ABI']=dict(source=str(abi),object_sha256=sha(O/'catalog-cookie-ABI.o'),independent_raw_SHA_equal=True,data_only=True)
 bad=O/'wrong-new-fence-width.cpp';bad.write_text(abi.read_text().replace('using FenceStatus=int(*)','using FenceStatus=int64_t(*)'));a[a.index(str(abi))]=str(bad);a[a.index('-o')+1]=str(O/'wrong-new-fence-width.o');assert run(a,'wrong-new-fence-width-refused',rec['directory'],False).returncode!=0
 result=dict(exact_catalog_service_and_dependencies=True,objects=objects,actual_recursive_inputs=inputs,layouts=layouts,source_review_exact=True,new_source_mutations_refused=neg,new_fence_callback_width_compile_refused=True,
 only_remaining_CP_cookie_repaired_existing_ring_member_and_AHB_fence_hook_preserved=True,service_imports_unchanged=imports['catalog-service-candidate'],
 optional_board_rules_votes_CommandDB_macros_absent=True,guarded_startup_and_CP_IRQ_call_path_target_not_qualified=True,
 full_Service_declaration_and_nonoptional_code_compiled=True,not_final_kernel_or_link_or_Apple_ABI_qualification=True,Service_metaclass_initializer_is_existing_unexecuted_code=True,
 old_nine_capsules_not_rewritten_or_relabelled=True,patch_unapplied=True,no_native_service_start_stop_provider_cache_MMIO_or_phone_calls=True,no_runtime_caller_selection_FD_kernel_device_candidate=True,
 commands=cmds,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'compile-result.json').write_text(json.dumps(result,indent=2)+'\n');print('3 exact-catalog independent iOS17 object pairs;',len(inputs),'inputs;Service3192->3208,Io48;startup optional branches unavailable;no invocation')
if __name__=='__main__':main()
