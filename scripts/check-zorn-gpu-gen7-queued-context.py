#!/usr/bin/env python3
"""Audit one callback-local NULL refusal,not a queue/refcount success model."""
from pathlib import Path
import argparse,json,re,shutil,subprocess


def body(s,t):
    a=s.index('{',s.index(t));d=0
    for i in range(a,len(s)):
        d+=(s[i]=='{')-(s[i]=='}')
        if not d:return s[a:i+1]
    raise AssertionError('unclosed source block')


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


def check(original,candidate,ident):
    assert candidate.count(ident['after'])==1 and candidate.replace(ident['after'],ident['before'],1)==original
    worker=tok(body(candidate,'static void gen7_defer_hw_fence_work('))
    assert worker.index('spin_unlock(&hfi->hw_fence.lock);')<worker.index('if(!drawctxt)return;')<worker.index('device=drawctxt->base.device;')<worker.index('mutex_lock(&adreno_dev->hwsched.mutex);')
    ack=body(original,'static void process_hw_fence_ack(')
    assert re.search(r'(?m)^\s*kthread_queue_work\(adreno_dev->hwsched.worker, &hfi->defer_hw_fence_work\);$',ack)
    ack=tok(ack)
    assert ack.index('drawctxt=hfi->hw_fence.defer_drawctxt;')<ack.index('del_timer_sync(')<ack.index('kthread_init_work(')<ack.index('kthread_queue_work(')
    stop=tok(body(original,'void gen7_hwsched_hfi_stop('))
    assert 'gen7_hwsched_process_msgq(adreno_dev);' in stop
    clear=tok(body(original,'static void _disable_hw_fence_throttle('))
    assert 'hfi->hw_fence.defer_drawctxt=NULL;' in clear


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    i=json.loads((o/'source-repair-identity.json').read_text());original=Path(i['original']).read_text();candidate=Path(i['candidate']).read_text();check(original,candidate,i);refused=[]
    for name,old,new in [
        ('missing-reloaded-null-guard',i['after'],i['before']),
        ('guard-after-first-dereference','if (!drawctxt)\n\t\treturn;\n\n\tdevice = drawctxt->base.device;','device = drawctxt->base.device;\n\tif (!drawctxt)\n\t\treturn;'),
        ('new-fault-policy-on-empty-context','if (!drawctxt)\n\t\treturn;','if (!drawctxt) {\n\t\tgen7_hwsched_fault(adreno_dev, ADRENO_GMU_FAULT);\n\t\treturn;\n\t}'),
    ]:
        assert candidate.count(old)==1;s=candidate.replace(old,new,1);(o/(name+'.source')).write_text(s)
        try:check(original,s,i)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('queued context source mutation accepted: '+name)
    review=o/'source-review';review.mkdir();dst=review/'adreno_gen7_hwsched_hfi.c';shutil.copyfile(i['original'],dst);patch=str((o/'queued-context-null.UNAPPLIED.patch').resolve())
    for args in [['--check',patch],[patch]]:
        r=subprocess.run(['git','apply',*args],cwd=review,capture_output=True,text=True);(o/('review-check.log' if '--check' in args else 'review-apply.log')).write_text(r.stdout+r.stderr);assert r.returncode==0
    assert dst.read_text()==candidate and dst.stat().st_ino!=Path(i['candidate']).stat().st_ino
    (o/'queued-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,independent_original_review_matches=True,all_nonnull_flow_and_other_source_inverse_byte_identical=True,no_queue_refcount_thread_callback_or_phone_execution=True,no_success_context_task_or_address_peer=True,no_full_Linux_or_native_target_build=True,no_old_suite_reexecution=True),indent=2)+'\n');print('3 new queued-context source mutations refused;review/inverse matched,no queue/ref/API execution')


if __name__=='__main__':main()
