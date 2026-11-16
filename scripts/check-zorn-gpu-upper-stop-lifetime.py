#!/usr/bin/env python3
"""Pinned upper stop/fence source contract and minimal UNAPPLIED propagation guard.

No stop/fence/provider peer is constructed or executed. No new native component,
object/kernel/candidate or wire format is produced by this reference-only repair.
"""
from pathlib import Path
import difflib,hashlib,importlib.util,json,re,subprocess
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-gen7-upper-stop-lifetime'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
spec=importlib.util.spec_from_file_location('extent_util',R/'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py');util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
norm=lambda s:' '.join(re.sub(r'/\*.*?\*/','',s,flags=re.S).split())
def check_guard(src,original):
 b=norm(util.body(src,'gen7_hwsched_power_off'))
 assert 'fence_ret = check_inflight_hw_fences(adreno_dev);' in b
 assert 'stop_ret = gen7_hwsched_gmu_power_off(adreno_dev);' in b
 gate='if (ret || stop_ret)'
 assert gate in b,'known OOB/stop error gate'
 at=b.index(gate)
 assert at<b.index('drain_hw_fences_cpu(adreno_dev)')<b.index('adreno_hwsched_unregister_contexts(adreno_dev)'), 'gate before drain/unregister'
 assert at<b.index('clear_bit(GMU_PRIV_GPU_STARTED'), 'gate before started flag clear'
 assert 'return ret ? ret : (fence_ret ? fence_ret : stop_ret);' in b,'first chronological nonzero before failed stop'
 pm=norm(util.body(src,'gen7_hwsched_pm_suspend'))
 assert 'ret = gen7_hwsched_power_off(adreno_dev); if (ret) return ret;' in pm, 'failed poweroff returns before common start-on-error'
 assert pm.index('if (ret) return ret;')<pm.index('adreno_get_gpu_halt(adreno_dev)')<pm.index('set_bit(GMU_PRIV_PM_SUSPEND')
 boot=norm(util.body(src,'gen7_hwsched_gpu_boot'))
 assert 'int stop_ret = gen7_hwsched_gmu_power_off(adreno_dev);' in boot
 assert 'boot:%d stop:%d' in boot and boot.endswith('return ret; }'), 'original boot error preserved'
 idle=norm(util.body(src,'hwsched_idle_check'))
 assert 'ret = gen7_hwsched_power_off(adreno_dev);' in idle and 'upper stop failed:%d' in idle
 # Exact earlier lower helper is untouched; the new patch is separate.
 assert util.body(src,'gen7_hwsched_gmu_power_off')==util.body(original,'gen7_hwsched_gmu_power_off')
 for fn in ['check_inflight_hw_fences','drain_hw_fences_cpu','drain_ctx_hw_fences_cpu','gen7_hwsched_reset_replay']:
  assert util.body(src,fn)==util.body(original,fn),fn+' outside minimal guard scope'

def main():
 if (O/'check-result.json').exists():raise SystemExit('completed;do not repeat')
 pins=json.loads((O/'source-pins.json').read_text())
 for p,h in pins.items():assert sha(Path(p))==h,p
 L=R/'out/zorn/gpu-discovery-20261030/layout';P=R/'out/zorn/gpu-discovery-20261030/profile-reference';G=R/'out/zorn/gpu-gen7-preallocated-providers'
 original=(L/'adreno_gen7_hwsched.c').read_text();hfi=(L/'adreno_gen7_hwsched_hfi.c').read_text();sched=(G/'adreno_hwsched.c').read_text();adreno=(P/'adreno.c').read_text();kgsl=(G/'kgsl.c').read_text()
 # Static functions have only these direct callers in the selected TU; table
 # use is mapped through exact common wrappers, not all hypothetical kernels.
 assert len(re.findall(r'\bgen7_hwsched_gmu_power_off\(',original))==3
 assert len(re.findall(r'\bgen7_hwsched_power_off\(',original))==3
 assert '.last_close = gen7_hwsched_power_off,' in original
 assert 'mutex_lock(&device->mutex);' in util.body(original,'hwsched_idle_check')
 for name in ['adreno_pm_suspend','adreno_power_cycle','adreno_hibernation_suspend']:
  b=util.body(adreno,name);assert 'mutex_lock(&device->mutex)' in b and 'ops->pm_suspend(adreno_dev)' in b
 b=norm(util.body(kgsl,'kgsl_close_device'));assert b.index('mutex_lock(&device->mutex)')<b.index('device->ftbl->last_close(device)')<b.index('device->open_count--')
 assert 'return ops->last_close(adreno_dev);' in util.body(adreno,'adreno_last_close')
 # Read->context lock then context spinlock. Removal drops a dma_fence ref
 # and frees metadata; it is not proof of DMA completion.
 b=util.body(original,'drain_hw_fences_cpu');assert 'read_lock(&device->context_lock)' in b and 'context->gmu_registered' in b
 b=norm(util.body(original,'drain_ctx_hw_fences_cpu'));assert b.index('spin_lock(&drawctxt->lock)')<b.index('gen7_trigger_hw_fence_cpu')<b.index('gen7_remove_hw_fence_entry')
 b=util.body(hfi,'gen7_hwsched_check_context_inflight_hw_fences');assert 'hdr->out_fence_ts' in b and 'return ret;' in b and 'gen7_remove_hw_fence_entry' in b
 trigger=util.body(hfi,'gen7_trigger_hw_fence_cpu');assert 'int ret = msm_hw_fence_update_txq(' in trigger and 'return;' in trigger and 'msm_hw_fence_trigger_signal(' in trigger
 remove=util.body(hfi,'gen7_remove_hw_fence_entry');assert 'dma_fence_put(' in remove and 'list_del_init(' in remove and 'kmem_cache_free(' in remove
 unregister=util.body(sched,'unregister_context');assert 'header->read_index = header->write_index' in unregister and 'context->gmu_registered = false' in unregister and 'drawctxt->internal_timestamp = 0' in unregister
 work=util.body(sched,'hwsched_idle');assert work.index('mutex_unlock(&device->mutex)')<work.index('adreno_hwsched_flush')<work.index('mutex_lock(&device->mutex)')
 assert 'kthread_flush_worker(hwsched->worker)' in util.body(sched,'adreno_hwsched_flush')
 # Build one independent candidate from original source, not the previously
 # repaired lower capsule. No live upstream/source profile is modified.
 candidate=original
 old=util.body(candidate,'gen7_hwsched_gpu_boot');new=old.replace('if (ret)\n\t\tgen7_hwsched_gmu_power_off(adreno_dev);','if (ret) {\n\t\tint stop_ret = gen7_hwsched_gmu_power_off(adreno_dev);\n\n\t\tif (stop_ret)\n\t\t\tdev_err_ratelimited(device->dev,\n\t\t\t\t"boot cleanup failed:boot:%d stop:%d\\n", ret, stop_ret);\n\t}')
 assert new!=old;candidate=candidate.replace(old,new,1)
 old=util.body(candidate,'gen7_hwsched_power_off');new=old.replace('int ret = 0;','int ret = 0, fence_ret, stop_ret;')
 new=new.replace('if (check_inflight_hw_fences(adreno_dev))','fence_ret = check_inflight_hw_fences(adreno_dev);\n\tif (fence_ret)')
 marker='\tgen7_hwsched_gmu_power_off(adreno_dev);';assert new.count(marker)==1
 new=new.replace(marker,'''\tstop_ret = gen7_hwsched_gmu_power_off(adreno_dev);

\t/* A known error cannot justify the following CPU drain or state reset.
\t * The check may already have removed entries; this is not rollback.
\t * A zero stop return still is not an independent DMA/stop proof.
\t */
\tif (ret || stop_ret) {
\t\tdev_err_ratelimited(device->dev,
\t\t\t"upper stop failed:oob:%d pending:%d stop:%d\\n",
\t\t\tret, fence_ret, stop_ret);
\t\treturn ret ? ret : (fence_ret ? fence_ret : stop_ret);
\t}''')
 candidate=candidate.replace(old,new,1)
 old=util.body(candidate,'hwsched_idle_check');new=old.replace('struct adreno_device *adreno_dev = ADRENO_DEVICE(device);','struct adreno_device *adreno_dev = ADRENO_DEVICE(device);\n\tint ret;')
 new=new.replace('gen7_hwsched_power_off(adreno_dev);','ret = gen7_hwsched_power_off(adreno_dev);\n\tif (ret)\n\t\tdev_err_ratelimited(device->dev, "idle upper stop failed:%d\\n", ret);');candidate=candidate.replace(old,new,1)
 old=util.body(candidate,'gen7_hwsched_pm_suspend');new=old.replace('gen7_hwsched_power_off(adreno_dev);','ret = gen7_hwsched_power_off(adreno_dev);\n\t/* Keep the halt gate closed; common err restarts the dispatcher. */\n\tif (ret)\n\t\treturn ret;');candidate=candidate.replace(old,new,1)
 check_guard(candidate,original)
 (O/'adreno_gen7_hwsched.c').write_text(candidate)
 patch=''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/vendor/qcom/opensource/graphics-kernel/adreno_gen7_hwsched.c',tofile='b/vendor/qcom/opensource/graphics-kernel/adreno_gen7_hwsched.c'))
 patchfile=O/'upper-stop-propagation.UNAPPLIED.patch';patchfile.write_text(patch)
 negatives=[]
 for name,a,b in [('known-error-guard-erased','if (ret || stop_ret)','if (0)'),('stop-status-not-propagated','return ret ? ret : (fence_ret ? fence_ret : stop_ret);','return ret;'),('PM-restarts-after-failed-stop','if (ret)\n\t\treturn ret;\n\n\tadreno_get_gpu_halt(adreno_dev);','if (ret)\n\t\tgoto err;\n\n\tadreno_get_gpu_halt(adreno_dev);'),('boot-error-overwritten','int stop_ret = gen7_hwsched_gmu_power_off(adreno_dev);','int stop_ret = (ret = gen7_hwsched_gmu_power_off(adreno_dev));')]:
  assert a in candidate;bad=candidate.replace(a,b)
  try:check_guard(bad,original)
  except AssertionError as e:negatives.append(dict(name=name,refused=str(e)))
  else:raise RuntimeError('source negative survived '+name)
 # Patch check is performed only in a new local source-review directory.
 # An optional composed copy verifies the earlier lower body is unchanged.
 commands=[]
 for name,base in [('original-base',original),('lower-repair-composition',(R/'out/zorn/gpu-gen7-stop-error-retention/adreno_gen7_hwsched.c').read_text())]:
  d=O/name;p=d/'vendor/qcom/opensource/graphics-kernel/adreno_gen7_hwsched.c';p.parent.mkdir(parents=True);p.write_text(base)
  for mode in ['--check','--apply']:
   a=['git','apply','--no-index',str(patchfile)]
   if mode=='--check':a.insert(2,'--check')
   # --apply is git-apply's default; never use any live source directory.
   proc=subprocess.run(a,cwd=d,capture_output=True,text=True,timeout=30);commands.append(dict(arguments=a,directory=str(d),returncode=proc.returncode));(O/(name+mode+'.log')).write_text(proc.stdout+proc.stderr);proc.check_returncode()
  patched=p.read_text();check_guard(patched,base)
  assert util.body(patched,'gen7_hwsched_gmu_power_off')==util.body(base,'gen7_hwsched_gmu_power_off')
  if name=='original-base':assert patched==candidate
 extracted={}
 for name in ['gen7_hwsched_gpu_boot','gen7_hwsched_power_off','hwsched_idle_check','gen7_hwsched_pm_suspend','check_inflight_hw_fences','drain_hw_fences_cpu','drain_ctx_hw_fences_cpu','gen7_hwsched_reset_replay']:
  extracted[name]=util.body(original,name)
 for name in ['gen7_hwsched_check_context_inflight_hw_fences','gen7_trigger_hw_fence_cpu','gen7_remove_hw_fence_entry','_retire_inflight_hw_fences']:
  extracted[name]=util.body(hfi,name)
 for name in ['unregister_context','adreno_hwsched_unregister_contexts','hwsched_idle','adreno_hwsched_idle','adreno_hwsched_work','adreno_hwsched_flush']:
  extracted[name]=util.body(sched,name)
 for name in ['adreno_last_close','adreno_pm_suspend','adreno_power_cycle','adreno_hibernation_suspend']:extracted[name]=util.body(adreno,name)
 extracted['kgsl_close_device']=util.body(kgsl,'kgsl_close_device')
 (O/'exact-lifetime-functions.json').write_text(json.dumps(extracted,indent=2)+'\n')
 for p,h in pins.items():assert sha(Path(p))==h
 result=dict(source_pins=pins,source_corruptions_refused=negatives,patch_sha256=sha(patchfile),new_patch_unapplied=True,source_review_copy_apply_checks=commands,
  old_lower_capsule_and_implementation_not_modified=True,known_error_gate_before_post_stop_drain_unregister_state_reset=True,
  lower_internal_actions_and_precheck_removal_not_rolled_back=True,PM_error_does_not_restart_dispatcher=True,
  no_new_native_component_or_target_needed_for_reference_only_repair=True,full_Linux_driver_not_compiled=True,
  no_CPU_hardware_peer_or_fake_stop_fence_provider=True,no_runtime_caller_FD_kernel_device_candidate=True,no_native_IRQ_MMIO_provider_phone_calls=True,
  limitations=['Zero lower return still not stop/DMA proof. Lower reference patch separately required for its own lost-error holes.','Void CPU fence-trigger can lose manager errors then caller removes entries; external native manager contract remains unbound.','Metadata flags can disagree with already-changed lower hardware state; broader recovery/retry/last-close policy unresolved.','New dev_err logging is diagnostic source only, not durable typed capture or a readable-failure transport.'],
  allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (O/'check-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('Upper source/locks/fence lifetime bound;4 source refusals;new reference guard checks on2 isolated bases;no Linux/native/hardware execution')
if __name__=='__main__':main()
