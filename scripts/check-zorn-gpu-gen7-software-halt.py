#!/usr/bin/env python3
"""Bind exact software admission source;never run a halt/refcount/provider model."""
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
    assert tok(body(s['header'],'static inline void adreno_get_gpu_halt('))=='{atomic_inc(&adreno_dev->halt);}'
    put=tok(body(s['header'],'static inline void adreno_put_gpu_halt('))
    assert 'atomic_dec_if_positive(&adreno_dev->halt)' in put and 'WARN(ret<0,' in put
    abort=tok(body(s['hwsched'],'static bool _abort_submission('))
    assert 'atomic_read(&adreno_dev->halt)||atomic_read(&hwsched->fault)' in abort
    submit=tok(body(s['hwsched'],'static int hwsched_sendcmd('))
    assert submit.index('_abort_submission(adreno_dev)')<submit.index('hwsched->inflight++;')<submit.index('hwsched->hwsched_ops->submit_drawobj(')
    replay=body(s['hwsched'],'void adreno_hwsched_replay(')
    assert '_abort_submission' not in replay and 'adreno_gpu_halt(' not in replay
    assert re.search(r'(?m)^\s*hwsched->hwsched_ops->submit_drawobj\(adreno_dev, drawobj\);$',replay)
    setup=tok(body(s['hfi'],'static void setup_hw_fence_deferred_ctxt('))
    assert setup.index('_kgsl_context_get(')<setup.index('hfi->hw_fence.defer_drawctxt=drawctxt;')<setup.index('gen7_hwsched_active_count_get(')
    assert 'kgsl_context_put(' not in setup and 'if(hfi->hw_fence.defer_drawctxt)' not in setup


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    s={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(s);refused=[]
    for name,key,old,new in [
        ('software-halt-increment-omitted','header','atomic_inc(&adreno_dev->halt);','/* omitted counter increment */'),
        ('normal-submit-admission-omitted','hwsched','if (_abort_submission(adreno_dev)) {','if (false) {'),
        ('replay-falsely-uses-normal-gate','hwsched','void adreno_hwsched_replay(struct adreno_device *adreno_dev)\n{','void adreno_hwsched_replay(struct adreno_device *adreno_dev)\n{\n\tif (_abort_submission(adreno_dev)) return;'),
        ('setup-falsely-proves-single-owner','hfi','static void setup_hw_fence_deferred_ctxt(','static void setup_hw_fence_deferred_ctxt('),
    ]:
        b=dict(s)
        if name=='setup-falsely-proves-single-owner':
            a=b[key].index('hfi->hw_fence.defer_drawctxt = drawctxt;',b[key].index(old));b[key]=b[key][:a]+'if (hfi->hw_fence.defer_drawctxt) return;\n\t'+b[key][a:]
        else:assert b[key].count(old)==1;b[key]=b[key].replace(old,new,1)
        (o/(name+'.source')).write_text(b[key])
        try:check(b)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('software halt source mutation accepted: '+name)
    (o/'software-halt-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,no_software_halt_refcount_submit_or_phone_execution=True,no_success_admission_or_task_address_peer=True,no_old_suite_reexecution=True,no_new_patch_or_native_target=True),indent=2)+'\n');print('4 new software admission source mutations refused;no halt/refcount/submit execution')


if __name__=='__main__':main()
