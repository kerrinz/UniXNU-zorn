#!/usr/bin/env python3
"""Audit exact normal dispatcher POWER/inflight source,without running a counter model."""
from pathlib import Path
import argparse,json,re


def mask(s):
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:' '*len(m.group(0)),s,flags=re.S)


def span(s,signature):
    m=mask(s);a=m.index('{',m.index(signature));depth=0
    for i in range(a,len(s)):
        depth+=(m[i]=='{')-(m[i]=='}')
        if depth==0:return a,i+1
    raise AssertionError('unclosed source block')


def body(s,signature):
    a,b=span(s,signature);return s[a:b]


def tok(s):return re.sub(r'\s+','',mask(s))


def check(src):
    s=src['dispatcher'];f=tok(body(s,'static int hwsched_sendcmd('))
    assert 'hwsched->inflight++;if(hwsched->inflight==1&&!test_bit(ADRENO_HWSCHED_POWER,&hwsched->flags)){ret=adreno_active_count_get(adreno_dev);if(ret){hwsched->inflight--;gotodone;}set_bit(ADRENO_HWSCHED_POWER,&hwsched->flags);}' in f
    assert 'ret=hwsched->hwsched_ops->submit_drawobj(adreno_dev,drawobj);if(ret){if(hwsched->inflight==1){adreno_active_count_put(adreno_dev);clear_bit(ADRENO_HWSCHED_POWER,&hwsched->flags);}hwsched->inflight--;gotodone;}' in f
    assert f.count('hwsched->inflight--;')==2
    assert f.index('mutex_lock(&device->mutex);')<f.index('hwsched->inflight++;')<f.index('mutex_unlock(&device->mutex);')
    power=tok(body(s,'static void hwsched_power_down('))
    assert power.count('adreno_active_count_put(adreno_dev);')==1
    assert 'if(test_bit(ADRENO_HWSCHED_POWER,&hwsched->flags)){adreno_active_count_put(adreno_dev);clear_bit(ADRENO_HWSCHED_POWER,&hwsched->flags);}' in power
    assert power.index('mutex_lock(&device->mutex);')<power.index('adreno_active_count_put(')<power.index('mutex_unlock(&device->mutex);')
    retire=tok(body(s,'static void retire_drawobj_list('))
    assert 'if(!drawobj_retired(adreno_dev,drawobj))continue;list_del_init(&obj->node);kmem_cache_free(obj_cache,obj);hwsched->inflight--;' in retire
    assert 'ADRENO_HWSCHED_POWER' not in retire
    work=tok(body(s,'static void adreno_hwsched_work('))
    assert work.index('mutex_lock(&hwsched->mutex);')<work.index('retire_drawobj_list(adreno_dev);')<work.index('hwsched_issuecmds(adreno_dev);')<work.index('if(hwsched->inflight==0){hwsched_power_down(adreno_dev);}')
    assert s.count('hwsched_power_down(adreno_dev);')==1
    fault=tok(body(s,'static bool adreno_hwsched_do_fault('))
    assert fault.index('mutex_lock(&device->mutex);')<fault.index('adreno_hwsched_reset_and_snapshot(')<fault.index('mutex_unlock(&device->mutex);')
    replay=tok(body(s,'void adreno_hwsched_replay('))
    assert 'hwsched->inflight--;' in replay and 'ADRENO_HWSCHED_POWER' not in replay
    idle=tok(body(src['gen7'],'static void hwsched_idle_check('))
    assert 'atomic_read(&device->active_cnt)||time_is_after_jiffies(device->idle_jiffies)' in idle
    assert 'ADRENO_HWSCHED_POWER' not in idle and 'gen7_hwsched_power_off(adreno_dev);' in idle
    reset=tok(body(src['gen7'],'int gen7_hwsched_reset_replay('))
    assert 'adreno_hwsched_replay(adreno_dev);' in reset
    assert '.submit_drawobj=gen7_hwsched_submit_drawobj,' in tok(src['gen7'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule
    inputs=json.loads((o/'audit-inputs.json').read_text());src={k:Path(v).read_text() for k,v in inputs.items()};check(src);refused=[]
    for name,sig,before,after in [
        ('failed-get-inflight-rollback-removed','static int hwsched_sendcmd(','if (ret) {\n\t\t\thwsched->inflight--;\n\t\t\tgoto done;','if (ret) {\n\t\t\tgoto done;'),
        ('multi-inflight-error-releases-owner','static int hwsched_sendcmd(','if (hwsched->inflight == 1) {','if (hwsched->inflight >= 1) {'),
        ('powerdown-duplicate-put','static void hwsched_power_down(','adreno_active_count_put(adreno_dev);','adreno_active_count_put(adreno_dev);\n\t\tadreno_active_count_put(adreno_dev);'),
        ('worker-powerdown-before-issue','static void adreno_hwsched_work(','hwsched_issuecmds(adreno_dev);','hwsched_power_down(adreno_dev);\n\thwsched_issuecmds(adreno_dev);'),
    ]:
        d=dict(src);a,b=span(d['dispatcher'],sig);part=d['dispatcher'][a:b];assert part.count(before)==1;part=part.replace(before,after,1);d['dispatcher']=d['dispatcher'][:a]+part+d['dispatcher'][b:];(o/(name+'.source')).write_text(d['dispatcher'])
        try:check(d)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('normal POWER source mutation accepted:'+name)
    (o/'normal-power-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,normal_first_inflight_may_reuse_prior_dispatcher_POWER=True,no_mechanical_recurring_patch_composition=True,no_driver_patch_or_target=True,no_counter_model_or_native_API_phone_execution=True,no_old_suite_reexecution=True),indent=2)+'\n')
    print('4new normal POWER source mutations refused;no counter model or API execution')


if __name__=='__main__':main()
