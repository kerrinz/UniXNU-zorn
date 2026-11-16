#!/usr/bin/env python3
"""Bind exact deferred-work domains and borrowed-reader order,source only."""
from pathlib import Path
import argparse,json,re


def body(s,t):
    a=s.index('{',s.index(t));d=0
    for i in range(a,len(s)):
        d+=(s[i]=='{')-(s[i]=='}')
        if not d:return s[a:i+1]
    raise AssertionError('unclosed source block')


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


def check(s):
    assert tok(body(s['header'],'static inline void kgsl_schedule_work('))=='{queue_work(kgsl_driver.workqueue,work);}'
    timer=tok(body(s['hfi'],'static void gen7_hwsched_hw_fence_timer('))
    assert 'kgsl_schedule_work(&hfi->hw_fence_ws);' in timer
    work=tok(body(s['hfi'],'static void gen7_hwsched_hw_fence_timeout('))
    assert work.index('gen7_hwsched_process_msgq(adreno_dev);')<work.index('if(!fault)return;')
    close=tok(body(s['hwsched'],'static void adreno_hwsched_dispatcher_close('))
    assert 'kthread_destroy_worker(hwsched->worker);' in close
    assert 'hw_fence_ws' not in close and 'kgsl_driver.workqueue' not in close
    exit=tok(body(s['adreno'],'static void __exit kgsl_3d_exit('))
    assert exit.index('platform_driver_unregister(')<exit.index('kgsl_core_exit();')
    core=tok(body(s['kgsl'],'void kgsl_core_exit('))
    assert 'destroy_workqueue(kgsl_driver.workqueue);' in core


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    s={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(s);refused=[]
    for name,key,old,new in [
        ('timeout-work-falsely-lockless','header','queue_work(kgsl_driver.workqueue, work);','queue_work(kgsl_driver.lockless_workqueue, work);'),
        ('pre-fault-message-read-hidden','hfi','gen7_hwsched_process_msgq(adreno_dev);','/* deleted unconditional queue processing */'),
        ('global-drain-falsely-before-device-unregister','adreno','platform_driver_unregister(&adreno_platform_driver);','kgsl_core_exit();\n\tplatform_driver_unregister(&adreno_platform_driver);'),
    ]:
        b=dict(s)
        if name=='pre-fault-message-read-hidden':
            a=b[key].index('static void gen7_hwsched_hw_fence_timeout(');assert old in b[key][a:];b[key]=b[key][:a]+b[key][a:].replace(old,new,1)
        else:assert b[key].count(old)==1;b[key]=b[key].replace(old,new,1)
        (o/(name+'.source')).write_text(b[key])
        try:check(b)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('new deferred-work source mutation accepted: '+name)
    (o/'deferred-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,no_timer_workqueue_thread_provider_or_phone_execution=True,no_success_task_cancellation_or_buffer_peer=True,no_old_suite_reexecution=True,no_new_patch_or_native_target=True),indent=2)+'\n');print('3 new deferred-work source mutations refused;no timer/workqueue/native execution')


if __name__=='__main__':main()
