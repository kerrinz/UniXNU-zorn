#!/usr/bin/env python3
"""Exact service-cookie source repair and real-header static ABI;never calls a provider."""
from pathlib import Path
import hashlib,importlib.util,json,re,shlex,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-service-cookie-lifetime';N=R/'UniXNU/drivers/NativeAdreno'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
WINDOW='struct NativeAdrenoGpuWindow {\n    volatile uint8_t *base;\n    size_t bytes;\n};\n'
MEMBERS='''
    /* Storage follows this service,not the automatic start() frame.
     * This does not retain the mapped base or prove hardware quiescence.
     * All consumers must remain inside the real service/map lifetime. */
    NativeAdrenoGpuWindow gpu_window_{},cp_window_{};'''
def check(s,old):
 assert s.count(WINDOW)==1 and s.index(WINDOW)<s.index('class NativeAdrenoGpuService : public IOService {')
 assert s.count(MEMBERS)==1,'real service members'
 restored=s.replace(MEMBERS,'').replace(WINDOW+'\nclass NativeAdrenoGpuService','class NativeAdrenoGpuService')
 restored=restored.replace('int NativeAdrenoGpuService::gpu_read32',WINDOW+'int NativeAdrenoGpuService::gpu_read32',1)
 for stem in ['gpu','cp']:
  assert f'NativeAdrenoGpuWindow {stem}_window=' not in s,'automatic cookie escaped'
  assert s.count(f'{stem}_window_={{')==1,'one assigned descriptor'
  restored=restored.replace(f'{stem}_window_={{',f'NativeAdrenoGpuWindow {stem}_window={{').replace('&'+stem+'_window_,','&'+stem+'_window,')
 assert restored==old,'only scoped storage relocation permitted'
 for fn in ['gpu_read32','gpu_write32','gpu_barrier','ring_publish','fence_acquire','ring_now','probe','stop','newUserClient']:
  assert util.body(s,'NativeAdrenoGpuService::'+fn)==util.body(old,'NativeAdrenoGpuService::'+fn),fn
 assert 'NativeAdrenoRingIo ring_io{&gpu_window_,gpu_write32,gpu_read32,gpu_barrier};' in s
 assert 'NativeAdrenoRingIo cp_io{&cp_window_,gpu_write32,gpu_read32,gpu_barrier};' in s
 assert 'gpu_read32,&cp_window_,' in s

def main():
 if (O/'check-result.json').exists():raise SystemExit('completed;do not repeat')
 pins=json.loads((O/'source-pins.json').read_text())
 for n,h in pins.items():assert sha(Path(n))==h,n
 s=(O/'NativeAdrenoService.cpp').read_text();old=(O/'NativeAdrenoService.cpp.preimage').read_text();check(s,old)
 negatives=[]
 for name,a,b in [('ring-local-cookie','&gpu_window_,gpu_write32','&gpu_window,gpu_write32'),('irq-local-cookie','&cp_window_,gpu_write32','&cp_window,gpu_write32'),('cache-return-changed','publishForDevice(0,bytes,false)==kIOReturnSuccess?0:1','publishForDevice(0,bytes,false)==kIOReturnSuccess?0:0'),('teardown-changed','for(auto &map:maps_)map.reset();','/* invented cleanup */')]:
  assert a in s
  try:check(s.replace(a,b),old)
  except AssertionError as e:negatives.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('source mutation accepted '+name)
 commands=[]
 def run(args,name,cwd=R,good=True):
  args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=args,directory=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  return p
 d=O/'source-review/drivers/NativeAdreno';d.mkdir(parents=True);(d/'NativeAdrenoService.cpp').write_bytes((N/'NativeAdrenoService.cpp').read_bytes())
 for args,name in [(['git','apply','--no-index','--check',O/'persistent-service-cookie.UNAPPLIED.patch'],'patch-check'),(['git','apply','--no-index',O/'persistent-service-cookie.UNAPPLIED.patch'],'patch-review')]:run(args,name,d.parents[1])
 assert (d/'NativeAdrenoService.cpp').read_bytes()==(O/'NativeAdrenoService.cpp').read_bytes()
 B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';recipe=B/'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json';rec=json.JSONDecoder().raw_decode(recipe.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in rec['arguments']
 includes=['-I'+str(O),'-I'+str(N),'-I'+str(R/'UniXNU/kits/ArmSmmu4K'),'-I'+str(R/'UniXNU/kits/AdrenoPM4')]
 def build(src,obj):
  a=list(rec['arguments']);a[a.index(rec['file'])]=str(src);a[a.index('-o')+1]=str(obj);return a+includes+['-mgeneral-regs-only']
 full=run(build(O/'NativeAdrenoService.cpp',O/'service.o'),'full-service-current-recipe',rec['directory'],False)
 # Missing board-provider source is not repaired by stubs,foreign headers or defines.
 if full.returncode:
  missing=re.findall(r"fatal error: '([^']+)' file not found",full.stderr)
  assert missing,'unexpected full-service compiler failure;inspect log'
 else:missing=[]
 abi=O/'cookie-types.cpp';abi.write_text('''/* SPDX-License-Identifier: MIT;data-only extraction,not service layout qualification. */
#include "NativeAdrenoRing.h"
#include "NativeAdrenoIrq.h"
#include <stddef.h>
'''+WINDOW+'''
using Read=int(*)(void*,uint32_t,uint32_t*);
using Write=int(*)(void*,uint32_t,uint32_t);
using Barrier=int(*)(void*);
static_assert(__is_same(decltype(NativeAdrenoRingIo::read32),Read));
static_assert(__is_same(decltype(NativeAdrenoRingIo::write32),Write));
static_assert(__is_same(decltype(NativeAdrenoRingIo::barrier),Barrier));
static_assert(__is_same(decltype(NativeAdrenoGpuWindow::base),volatile uint8_t*));
static_assert(__is_same(decltype(NativeAdrenoGpuWindow::bytes),size_t));
static_assert(sizeof(NativeAdrenoGpuWindow)==16 && alignof(NativeAdrenoGpuWindow)==8);
static_assert(offsetof(NativeAdrenoGpuWindow,base)==0 && offsetof(NativeAdrenoGpuWindow,bytes)==8);
static_assert(sizeof(NativeAdrenoRingIo)==32 && sizeof(int)==4 && sizeof(size_t)==8);
static_assert(__is_same(decltype(&NativeAdrenoIrq::attach),IOReturn(NativeAdrenoIrq::*)(const NativeAdrenoRingIo*)));
extern "C" const unsigned native_service_cookie_type_sizes[]={sizeof(NativeAdrenoGpuWindow),alignof(NativeAdrenoGpuWindow),sizeof(NativeAdrenoRingIo),sizeof(int)};
''')
 obj=O/'cookie-types.o';a=build(abi,obj);run(a,'cookie-types-first',rec['directory']);first=O/'cookie-types-first.o';first.write_bytes(obj.read_bytes());run(a,'cookie-types-independent',rec['directory']);assert sha(first)==sha(obj)
 assert not run(['nm','-u',obj],'cookie-types-imports').stdout.strip()
 sections=run(['otool','-l',obj],'cookie-types-sections').stdout;assert '__mod_init_func' not in sections
 assert not run(['otool','-tvV',obj],'cookie-types-code').stdout.split('(__TEXT,__text) section')[-1].strip() if '(__TEXT,__text) section' in run(['otool','-tvV',obj],'cookie-types-code-check').stdout else True
 pp=[];i=0
 while i<len(a):
  if a[i] in ['-o','-MF','-MJ','-MT']:i+=2
  elif a[i]=='-c':i+=1
  else:pp.append(a[i]);i+=1
 dep=O/'cookie-types.d';run(pp+['-M','-MF',dep,'-MT','input'],'cookie-types-deps',rec['directory']);inputs={str(recipe):sha(recipe)}
 for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
  p=Path(n)
  if not p.is_absolute():p=Path(rec['directory'])/p
  inputs[str(p)]=sha(p)
 bad=O/'wrong-cookie-width.cpp';bad.write_text(abi.read_text().replace('size_t bytes;','uint32_t bytes;'));status=run(build(bad,O/'wrong-cookie-width.o'),'wrong-cookie-width-refused',rec['directory'],False);assert status.returncode!=0
 for n,h in pins.items():assert sha(Path(n))==h,n
 result=dict(source_patch_unapplied=True,source_review_exact=True,new_source_mutations_refused=negatives,actual_current_iOS17_recipe=str(recipe),full_service_compile_returncode=full.returncode,missing_provider_headers=missing,full_service_layout_or_selected_start_not_qualified=bool(missing),missing_headers_not_filled_with_stubs_reference_device_headers_or_defines=True,data_only_exact_window_and_real_Ring_Irq_types=True,cookie16_align8_base0_bytes8=True,independent_raw_SHA_equal=sha(first)==sha(obj),object_sha256=sha(obj),actual_recursive_inputs=inputs,new_cookie_width_compile_refused=True,commands=commands,native_or_callback_or_service_or_phone_execution=False,no_runtime_caller_FD_kernel_device_candidate=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'check-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['commands','actual_recursive_inputs']},indent=2))
if __name__=='__main__':main()
