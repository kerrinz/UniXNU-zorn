#!/usr/bin/env python3
"""Exact reference stop errors and UNAPPLIED repair; no hardware function executes."""
from pathlib import Path
import hashlib,importlib.util,json,re,shlex,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-gen7-stop-error-retention'
P=R/'out/zorn/gpu-discovery-20261030/profile-reference';L=R/'out/zorn/gpu-discovery-20261030/layout'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('extent_util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
norm=lambda s:' '.join(s.split())
def calls(s):
 return [n for n in re.findall(r'\b((?:gen7|kgsl|clk|adreno)_[a-zA-Z0-9_]+)\s*\(',s) if n!='gen7_stop_capture']
def candidate_check(hw,gmu,header,original_hw,original_gmu):
 b=norm(util.body(hw,'gen7_hwsched_gmu_power_off'));h=norm(util.body(gmu,'gen7_halt_gbif'))
 assert 'if (!ret) ret = gbif_ret;' in b,'RSCC first return preserved'
 assert 'return ret ? ret : arb_ret;' in h,'GBIF client first return preserved'
 assert 'fault_entry_adapter_status = -EIO; ret = -EIO; goto error;' in b,'fault adapter rejection'
 assert 'gen7_stop_capture(&gmu->stop_errors, GEN7_STOP_RSCC, ret);' in b
 assert 'GEN7_STOP_GBIF_CLIENT, ret' in h and 'GEN7_STOP_GBIF_ARB, arb_ret' in h
 assert b.count('void_cleanup_unknown = 1;')==2
 assert 'memset(' not in b+h and 'stop_errors = ' not in b+h,'persistent error history not reset'
 assert 'if (!capture->first_failure_stage_plus1)' in header,'first failure guarded'
 assert 'if (!(capture->failed_mask & bit))' in header,'per-stage first failure guarded'
 assert 'if (!raw)\n\t\treturn;' in header,'zero cannot create available native success'
 assert calls(util.body(hw,'gen7_hwsched_gmu_power_off'))==calls(util.body(original_hw,'gen7_hwsched_gmu_power_off')),'existing hardware call order unchanged'
 assert calls(util.body(gmu,'gen7_halt_gbif'))==calls(util.body(original_gmu,'gen7_halt_gbif')),'existing GBIF call order unchanged'
 for name in ['gen7_gmu_suspend','gen7_gmu_pwrctrl_suspend','_do_gbif_halt','gen7_complete_rpmh_votes','gen7_rscc_sleep_sequence']:
  assert util.body(gmu,name)==util.body(original_gmu,name),name+' changed outside repair'

def main():
 if (O/'check-result.json').exists():raise SystemExit('completed;do not repeat')
 inputs=json.loads((O/'source-pins.json').read_text())
 for p,h in inputs.items():assert sha(Path(p))==h
 fetch=json.loads((O/'adreno.h.escalated-fetch.json').read_text());assert fetch['status']==200 and sha(O/'adreno.h')==fetch['sha256'];inputs[str(O/'adreno.h')]=fetch['sha256']
 for manifest,names,folder in [(P/'manifest.json',['adreno_gen7.h'],P),(L/'source-manifest.json',['adreno_gen7_hwsched.h'],L)]:
  data=json.loads(manifest.read_text());entries=data['files'] if isinstance(data,dict) else data
  for name in names:
   e=next(e for e in entries if e.get('name',e.get('file'))==name and e.get('ok'));p=folder/name;assert sha(p)==e['sha256'];inputs[str(p)]=e['sha256']
 original_hw=(L/'adreno_gen7_hwsched.c').read_text();original_gmu=(P/'adreno_gen7_gmu.c').read_text();header=(O/'adreno_gen7_gmu.h').read_text();hw=(O/'adreno_gen7_hwsched.c').read_text();gmu=(O/'adreno_gen7_gmu.c').read_text();assert (O/'stop-error-capture.exact.inc').read_text() in header;candidate_check(hw,gmu,header,original_hw,original_gmu)
 # Bind actual lower behavior. No function below is executed or replaced by a peer.
 lower=json.loads((O/'exact-lower-functions.json').read_text())
 assert 'ret = gen7_timed_poll_check_rscc' in lower['gen7_rscc_sleep_sequence'] and 'return -ETIMEDOUT;' in lower['gen7_rscc_sleep_sequence']
 assert 'return 0;' in lower['gen7_rscc_sleep_sequence'] and 'GMU_PRIV_FIRST_BOOT_DONE' in lower['gen7_rscc_sleep_sequence'] and 'GMU_PRIV_RSCC_SLEEP_DONE' in lower['gen7_rscc_sleep_sequence']
 assert 'gen7_complete_rpmh_votes(gmu, 1);' in lower['gen7_gmu_pwrctrl_suspend']
 assert 'ret |= gen7_timed_poll_check_rscc' in lower['gen7_complete_rpmh_votes']
 assert 'kgsl_mmu_pagefault_resume(&device->mmu, false)' in lower['_do_gbif_halt'] and 'return -' not in lower['_do_gbif_halt']
 assert 'regulator_enable(pwr->gx_gdsc)' in lower['gen7_gmu_pwrctrl_suspend'] and 'regulator_disable(pwr->gx_gdsc)' in lower['gen7_gmu_pwrctrl_suspend']
 assert 'kgsl_regmap_read_poll_timeout(' in lower['adreno_wait_for_halt_ack'] and 'return ret;' in lower['adreno_wait_for_halt_ack']
 assert 'gen7_hfi_send_cmd_async' in lower['gen7_hwsched_notify_slumber']
 assert 'devm_kzalloc(&pdev->dev, sizeof(*gen7_hwsched_dev)' in lower['gen7_hwsched_probe']
 assert 'struct gen7_gmu_device gmu;' in (P/'adreno_gen7.h').read_text() and 'struct gen7_device gen7_dev;' in (L/'adreno_gen7_hwsched.h').read_text()
 native={}
 for name in ['NativeAdrenoGmuPlatform.h','NativeAdrenoGmuContext.h','NativeAdrenoGmuService.cpp']:
  p=R/'UniXNU/drivers/NativeAdreno'/name;inputs[str(p)]=sha(p);native[name]=p.read_text()
 assert 'already mapped' in native['NativeAdrenoGmuPlatform.h']
 assert 'there is no teardown' in native['NativeAdrenoGmuContext.h']
 stop=util.body(native['NativeAdrenoGmuService.cpp'],'NativeAdrenoGmuService::stop');assert 'map.reset()' in stop and 'IOService::stop(provider)' in stop
 source_neg=[]
 for name,which,a,b in [('RSCC-overwritten','hw','if (!ret)\n\t\tret = gbif_ret;','ret = gbif_ret;'),('client-overwritten','gmu','return ret ? ret : arb_ret;','return arb_ret;'),('fault-success','hw','fault_entry_adapter_status = -EIO;','fault_entry_adapter_status = 0;'),('first-error-erased','header','if (!capture->first_failure_stage_plus1)','if (1)')]:
  v=dict(hw=hw,gmu=gmu,header=header);assert a in v[which];v[which]=v[which].replace(a,b)
  try:candidate_check(v['hw'],v['gmu'],v['header'],original_hw,original_gmu)
  except AssertionError as e:source_neg.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('source corruption survived '+name)
 commands=[]
 def run(a,name,cwd=R,good=True):
  a=list(map(str,a));p=subprocess.run(a,cwd=cwd,capture_output=True,text=True,timeout=55);commands.append(dict(arguments=a,directory=str(cwd),returncode=p.returncode));(O/(name+'.log')).write_text(p.stdout+p.stderr)
  if good:p.check_returncode()
  else:assert p.returncode!=0,name
  return p.stdout+p.stderr
 wrapper=O/'capture-compile-only.c';wrapper.write_text('/* SPDX-License-Identifier: GPL-2.0-only */\n#include <stdint.h>\ntypedef uint32_t u32;\n#include "stop-error-capture.exact.inc"\nvoid ZornGen7StopCaptureCompileOnly(struct gen7_stop_error_capture *p,unsigned stage,int raw){gen7_stop_capture(p,stage,raw);}\n')
 flags=['-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(O)]
 test=O/'test-stop-error-capture.c';test.write_text('''/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdint.h>
#include <assert.h>
#include <string.h>
typedef uint32_t u32;
#include "stop-error-capture.exact.inc"
int main(void){
 struct gen7_stop_error_capture r={0};
 assert(sizeof(r.first_failure_raw)==4 && sizeof(r)==56);
 gen7_stop_capture(&r,GEN7_STOP_RSCC,-110);
 assert(r.first_failure_raw==-110 && r.first_failure_stage_plus1==4);
 gen7_stop_capture(&r,GEN7_STOP_GBIF_CLIENT,-22);
 gen7_stop_capture(&r,GEN7_STOP_GBIF_ARB,INT32_MIN);
 gen7_stop_capture(&r,GEN7_STOP_RSCC,-7);
 gen7_stop_capture(&r,GEN7_STOP_RSCC,0);
 assert(r.first_failure_raw==-110 && r.error[GEN7_STOP_RSCC]==-110);
 assert(r.error[GEN7_STOP_GBIF_CLIENT]==-22 && r.error[GEN7_STOP_GBIF_ARB]==INT32_MIN);
 assert(r.failed_mask==0x38 && r.attempted_mask==0x38);
 assert(r.fault_entry_seen==0 && r.fault_entry_adapter_status==0 && r.void_cleanup_unknown==0);
 struct gen7_stop_error_capture before=r;
 gen7_stop_capture(&r,GEN7_STOP_STAGE_COUNT,-1);gen7_stop_capture(0,0,-1);
 assert(!memcmp(&r,&before,sizeof(r)));
 for(unsigned i=0;i<GEN7_STOP_STAGE_COUNT;++i){
  struct gen7_stop_error_capture x={0};
  gen7_stop_capture(&x,i,-123456789);gen7_stop_capture(&x,i,-8);
  assert(x.first_failure_raw==-123456789 && x.error[i]==-123456789);
  assert(x.first_failure_stage_plus1==i+1 && x.failed_mask==(1u<<i));
 }
 return 0;
}
''')
 run(['clang',*flags,test,'-o',O/'test-stop-error-capture'],'capture-host-build');run([O/'test-stop-error-capture'],'capture-host-run');host_neg=[]
 for name,a,b in [('first-error-clobbered','if (!capture->first_failure_stage_plus1)','if (1)'),('raw32-truncated','capture->error[stage] = raw;','capture->error[stage] = (short)raw;')]:
  d=O/name;d.mkdir();inc=(O/'stop-error-capture.exact.inc').read_text();assert a in inc;(d/'stop-error-capture.exact.inc').write_text(inc.replace(a,b));local=d/'test.c';local.write_bytes(test.read_bytes());run(['clang',*flags,local,'-o',d/'test'],name+'-build');run([d/'test'],name+'-refused',good=False);host_neg.append(name)
 abi=O/'capture-ABI.cpp';abi.write_text('''/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdint.h>
#include <stddef.h>
#include <IOKit/IOTypes.h>
typedef uint32_t u32;
#include "stop-error-capture.exact.inc"
static_assert(sizeof(int)==4 && sizeof(IOReturn)==4);
static_assert(sizeof(gen7_stop_error_capture)==56);
static_assert(offsetof(gen7_stop_error_capture,error)==16);
static_assert(offsetof(gen7_stop_error_capture,fault_entry_adapter_status)==44);
static_assert(offsetof(gen7_stop_error_capture,void_cleanup_unknown)==52);
extern "C" const unsigned stop_capture_sizes[]={56,16,44,52,4};
''')
 objects={};B=R/'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
 for name,src,recipe in [('capture',wrapper,B/'bsd/DEVELOPMENT/bsd_init.o.json'),('capture-ABI',abi,B/'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json')]:
  inputs[str(recipe)]=sha(recipe);rec=json.JSONDecoder().raw_decode(recipe.read_text())[0];args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args;args[args.index(rec['file'])]=str(src);obj=O/(name+'.o');args[args.index('-o')+1]=str(obj);args+=['-I'+str(O),'-mgeneral-regs-only'];run(args,name+'-first',rec['directory']);first=O/(name+'-first.o');first.write_bytes(obj.read_bytes());run(args,name+'-independent',rec['directory']);assert sha(first)==sha(obj);objects[name]=sha(obj)
  assert not run(['nm','-u',obj],name+'-imports').strip();assert '__mod_init_func' not in run(['otool','-l',obj],name+'-sections');run(['otool','-tvV',obj],name+'-disassembly')
  pp=[];i=0
  while i<len(args):
   if args[i] in ['-o','-MF','-MT','-MJ']:i+=2
   elif args[i]=='-c':i+=1
   else:pp.append(args[i]);i+=1
  dep=O/(name+'.d');run(pp+['-M','-MF',dep,'-MT','input'],name+'-deps',rec['directory'])
  for n in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
   p=Path(n)
   if not p.is_absolute():p=Path(rec['directory'])/p
   inputs[str(p)]=sha(p)
 for p in [wrapper,test,abi,O/'stop-error-retention.UNAPPLIED.patch',O/'adreno_gen7_gmu.c',O/'adreno_gen7_gmu.h',O/'adreno_gen7_hwsched.c']:inputs[str(p)]=sha(p)
 (O/'check-result.json').write_text(json.dumps(dict(inputs=inputs,commands=commands,objects=objects,source_corruptions_refused=source_neg,pure_negative_scalar_capture_corruptions_refused=host_neg,
  full_Linux_driver_candidate_not_compiled=True,only_actual_extracted_CPU_error_capture_and_data_ABI_compiled=True,no_hardware_callable_wrapper_or_fake_provider=True,no_native_IRQ_MMIO_allocator_provider_callback_phone_calls=True,no_runtime_caller_FD_kernel_device_candidate=True,repair_unapplied=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0),indent=2)+'\n')
 print('Exact stop contract +UNAPPLIED3file repair;4source/2negative-scalar refusals;2independent current iOS17 extracted CPU/data objects;',len(inputs),'inputs;no Linux/native/hardware execution')
if __name__=='__main__':main()
