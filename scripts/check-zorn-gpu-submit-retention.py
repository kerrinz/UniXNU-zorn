#!/usr/bin/env python3
"""Real current iOS17 compile/static retention audit; no native or host provider call."""
from pathlib import Path
import hashlib,importlib.util,json,re,shlex,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-native-submit-retention';N=R/'UniXNU/drivers/NativeAdreno'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('extent_util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
norm=lambda s:' '.join(re.sub(r'/\*.*?\*/','',s,flags=re.S).split())
def source_check(header,source):
 rollback=norm(util.body(source,'NativeAdrenoSubmit::rollbackBeforeCommit'))
 assert rollback.index('job.count=count;job.queue=queue;job.active=true;')<rollback.index('vm_->retireJobAfterCompletion('),'metadata before native retirement'
 assert 'if(retired) { rememberCleanupFailure(retired);++stats_.poisoned_jobs; return poisonFailure(primary); }' in rollback,'retain pending refs on first failed cleanup'
 assert rollback.index('if(retired)')<rollback.index('job.retired_mask|=')<rollback.index('++stats_.references_retired;'),'count only real success'
 assert rollback.index('return poisonFailure(primary);')<rollback.rindex('job=Job{};'),'no failed metadata clear'
 release=norm(util.body(source,'NativeAdrenoSubmit::release'))
 assert 'if(retired) { rememberCleanupFailure(retired); return poisonFailure(retired); }' in release
 assert release.index('if(retired)')<release.index('job.retired_mask|=')<release.index('++stats_.references_retired;')
 assert 'const IOReturn acquired=vm_->acquireImported(); if(acquired)return poisonFailure(acquired);' in release,'raw completion-cache API error preserved'
 assert release.index('if(acquired)')<release.index('job=Job{};')
 assert 'if(status && !first_failure_available_)' in source and 'if(status && !first_cleanup_available_)' in source
 assert 'first_failure_status_=status;first_failure_available_=true;' in source
 assert 'first_cleanup_status_=status;first_cleanup_available_=true;' in source
 assert 'IOReturn first_failure_status_=' in header and 'IOReturn first_cleanup_status_=' in header
 submit=util.body(source,'NativeAdrenoSubmit::submit')
 assert submit.count('rollbackBeforeCommit(')==3
 assert 'vm_->retireJobAfterCompletion(' not in submit,'no unchecked rollback in submission'
 assert 'return poisonFailure(status);' in submit,'actual ring API error not generic poison'
 assert 'job->retired_mask' not in submit,'uncertain ring path does not claim any retirement'

def main():
 if (O/'compile-result.json').exists():raise SystemExit('completed;do not repeat')
 pins=json.loads((O/'source-pins.json').read_text())
 for p,h in pins.items():assert sha(Path(p))==h,p
 header=(O/'NativeAdrenoSubmit.h').read_text();source=(O/'NativeAdrenoSubmit.cpp').read_text();source_check(header,source)
 vm=(N/'NativeAdrenoVm.cpp').read_text();memory=(N/'NativeAdrenoMemory.cpp').read_text();ring=(N/'NativeAdrenoRing.cpp').read_text()
 hold=util.body(vm,'NativeAdrenoVm::holdJob');retire=util.body(vm,'NativeAdrenoVm::retireJobAfterCompletion')
 assert hold.index('holdForDevice()')<hold.index('++record->jobs') and 'if(status)return status;' in hold
 assert retire.index('retireAfterQuiescence()')<retire.index('--record->jobs') and 'if(status)return status;' in retire
 assert 'if(quarantined_)return kIOReturnNotReady;' in util.body(memory,'NativeAdrenoMemory::retireAfterQuiescence')
 assert 'return fail(ArmSmmu4KIoError)' in util.body(vm,'NativeAdrenoVm::acquireImported'),'lower cache error remains already folded'
 assert 'if(cache_.publish(' in ring and 'if(io_.write32(io_.cookie,RingWptr,end))return poison();' in ring
 assert 'const uint32_t value=fence_[1]' in util.body(ring,'NativeAdrenoRing::observeFence')
 controls=[]
 for name,which,a,b in [('cleanup-counted-before-success','source','if(retired) {\n            rememberCleanupFailure(retired);++stats_.poisoned_jobs;','if(retired) {\n            ++stats_.references_retired; rememberCleanupFailure(retired);++stats_.poisoned_jobs;'),('primary-error-folded','source','return poisonFailure(primary);','return poison();'),('first-error-overwritten','source','if(status && !first_failure_available_)','if(status)'),('raw-status-truncated','header','IOReturn first_cleanup_status_=','uint16_t first_cleanup_status_=')]:
  h,s=header,source
  if which=='source':assert a in s;s=s.replace(a,b)
  else:assert a in h;h=h.replace(a,b)
  try:source_check(h,s)
  except (AssertionError,ValueError) as e:controls.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('source corruption survived '+name)
 commands=[]
 def run(a,name,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,directory=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0,name
  return p.stdout+p.stderr
 abi=O/'submit-retention-ABI.cpp';abi.write_text('''/* SPDX-License-Identifier: MIT */
#include "NativeAdrenoSubmit.h"
#include <stddef.h>
using SubmitMethod=IOReturn(NativeAdrenoSubmit::*)(const NativeAdrenoSubmitBuffer*,size_t,uint32_t,uint32_t*);
using RetireMethod=IOReturn(NativeAdrenoVm::*)(uint64_t);
static_assert(__is_same(decltype(&NativeAdrenoSubmit::submit),SubmitMethod));
static_assert(__is_same(decltype(&NativeAdrenoVm::retireJobAfterCompletion),RetireMethod));
static_assert(sizeof(IOReturn)==4 && sizeof(uint64_t)==8);
static_assert(sizeof(NativeAdrenoSubmitStats)==40);
static_assert(offsetof(NativeAdrenoSubmitStats,references_retired)==24);
extern "C" const unsigned submit_retention_sizes[]={sizeof(NativeAdrenoSubmit),sizeof(NativeAdrenoSubmitStats),sizeof(IOReturn)};
''')
 B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';recipes={};inputs=dict(pins);objects={};builds={}
 for kind,rel in [('cxx','iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'),('c','bsd/DEVELOPMENT/bsd_init.o.json')]:
  p=B/rel;inputs[str(p)]=sha(p);recipes[kind]=json.JSONDecoder().raw_decode(p.read_text())[0];assert '--target=arm64-apple-ios17.0.0' in recipes[kind]['arguments']
 includes=['-I'+str(O),'-I'+str(N),'-I'+str(R/'UniXNU/kits/ArmSmmu4K'),'-I'+str(R/'UniXNU/kits/AdrenoPM4')]
 targets=[('original-submit',N/'NativeAdrenoSubmit.cpp','cxx'),('retained-submit',O/'NativeAdrenoSubmit.cpp','cxx'),('current-vm',N/'NativeAdrenoVm.cpp','cxx'),('current-ring',N/'NativeAdrenoRing.cpp','cxx'),('current-memory',N/'NativeAdrenoMemory.cpp','cxx'),('current-cpu',N/'NativeAdrenoCpu.cpp','cxx'),('current-smmu-memory',N/'NativeAdrenoSmmuMemory.cpp','cxx'),('current-PM4',R/'UniXNU/kits/AdrenoPM4/AdrenoPM4.c','c'),('retention-ABI',abi,'cxx')]
 for name,src,kind in targets:
  rec=recipes[kind];a=list(rec['arguments']);a[a.index(rec['file'])]=str(src);obj=O/(name+'.o');a[a.index('-o')+1]=str(obj);a+=includes+['-mgeneral-regs-only']
  if name=='retention-ABI':a+=['-Xclang','-fdump-record-layouts']
  run(a,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(a,name+'-independent',rec['directory']);assert sha(first)==sha(obj);objects[name]=dict(source=str(src),source_sha256=sha(src),object_sha256=sha(obj),independent_raw_SHA_equal=True);builds[name]=(a,rec['directory']);inputs[str(src)]=sha(src)
  imports=run(['nm','-u',obj],name+'-imports');assert '__mod_init_func' not in run(['otool','-l',obj],name+'-sections');run(['otool','-tvV',obj],name+'-disassembly')
  if name=='retention-ABI':assert not imports.strip()
  pp=[];i=0
  while i<len(a):
   if a[i] in ['-o','-MF','-MT','-MJ']:i+=2
   elif a[i]=='-c':i+=1
   elif a[i]=='-Xclang' and a[i+1]=='-fdump-record-layouts':i+=2
   else:pp.append(a[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',dep,'-MT','input'],name+'-deps',rec['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(rec['directory'])/p
   inputs[str(p)]=sha(p)
 bad=O/'wrong-retire-width.cpp';bad.write_text(abi.read_text().replace(')(uint64_t);',')(uint32_t);'));a,cwd=builds['retention-ABI'];a=list(a);a[a.index(str(abi))]=str(bad);a[a.index('-o')+1]=str(O/'wrong-retire-width.o');run(a,'wrong-retire-width-refused',cwd,good=False)
 selected=[name for name,_,_ in targets if name not in ['original-submit','retention-ABI']]
 linked=O/'retained-submit-component.o';run(['xcrun','ld','-r','-arch','arm64','-platform_version','ios','17.0','27.0',*[O/(name+'.o') for name in selected],'-o',linked],'component-link')
 imports=run(['nm','-u',linked],'component-imports').split();assert not any('NativeAdreno' in n for n in imports),'native class component imports not closed'
 assert '__mod_init_func' not in run(['otool','-l',linked],'component-sections')
 assert not any(n in imports for n in ['___cxa_atexit','__GLOBAL__sub_I'])
 for p,h in pins.items():assert sha(Path(p))==h,p
 (O/'compile-result.json').write_text(json.dumps(dict(objects=objects,inputs=inputs,commands=commands,new_source_corruptions_refused=controls,wrong_retire_width_compile_refused=True,selected_component_imports=imports,selected_component_sha256=sha(linked),native_class_component_imports_closed=True,kernel_and_SMMU_kit_imports_still_external=True,no_initializer_or_runtime_invocation=True,no_host_provider_or_success_address_fence_model=True,patch_unapplied=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n')
 print('9 current iOS17 independent object pairs;4 source/1 width refusals;native class imports close in7-object component;no methods/providers executed')
if __name__=='__main__':main()
