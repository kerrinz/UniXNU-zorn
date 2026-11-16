#!/usr/bin/env python3
"""Bind exact recurring drawobj source ownership and feature-gated reachability.
No native/refcount/object/queue execution or simulated successful peer.
"""
from pathlib import Path
import argparse,hashlib,json,re


def clean(s):
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:'""' if m.group(0).startswith('"') else '',s,flags=re.S)


def body(s,signature):
    s=clean(s);a=s.index('{',s.index(signature));depth=0
    for i in range(a,len(s)):
        depth+=(s[i]=='{')-(s[i]=='}')
        if depth==0:return s[a:i+1]
    raise AssertionError('unclosed block')


def tok(s):return re.sub(r'\s+','',s)


def check(src):
    init=tok(body(src['drawc'],'static int drawobj_init('))
    assert 'if(!_kgsl_context_get(context))return-ENOENT;kref_init(&drawobj->refcount);' in init
    destroy=tok(body(src['drawc'],'void kgsl_drawobj_destroy('))
    assert 'drawobj->destroy(drawobj);kgsl_drawobj_put(drawobj);' in destroy
    free=tok(body(src['drawc'],'void kgsl_drawobj_destroy_object('))
    assert 'kgsl_context_put(drawobj->context);drawobj->destroy_object(drawobj);' in free
    ioctl=tok(body(src['kgsl'],'long kgsl_ioctl_recurring_command('))
    assert 'if(drawobj->flags&KGSL_DRAWOBJ_STOP_RECURRING){result=device->ftbl->dequeue_recurring_cmd(device,context);if(!result)kgsl_drawobj_destroy(drawobj);}else{result=device->ftbl->queue_recurring_cmd(dev_priv,context,drawobj);}' in ioctl
    assert 'if(result&&result!=-EPROTO)kgsl_drawobj_destroy(drawobj);kgsl_context_put(context);returnresult;' in ioctl
    callback=tok(body(src['hfi'],'int gen7_hwsched_send_recurring_cmdobj('))
    assert 'adreno_hwsched_retire_cmdobj(hwsched,hwsched->recurring_cmdobj);del_timer_sync(&hwsched->lsr_timer);hwsched->recurring_cmdobj=NULL;' in callback
    assert callback.count('hwsched->recurring_cmdobj=cmdobj;')==1
    assert 'kref_get(' not in callback and 'kgsl_drawobj_destroy(' not in callback
    # This exact source configuration does not admit recurring through public APIs.
    core=body(src['gpulist'],'static const struct adreno_gen7_core adreno_gpu_core_gen7_9_1 =')
    features=core[core.index('.features'):core.index('.gpudev')]
    assert 'ADRENO_LSR' not in features
    assert '.gpudev=&adreno_gen7_9_0_hwsched_gpudev.base' in tok(core)
    assert '((_dev)->gpucore->features&(_bit))' in tok(clean(src['adrenoh']))
    for signature in ['static int adreno_queue_recurring_cmd(','static int adreno_dequeue_recurring_cmd(']:
        f=tok(body(src['adreno'],signature));gate='if(!ADRENO_FEATURE(adreno_dev,ADRENO_LSR))return-EOPNOTSUPP;'
        assert gate in f and f.index(gate)<f.index('mutex_lock(&device->mutex);')
    profile=tok(body(src['drawc'],'static void add_profiling_buffer('))
    assert profile.index('if(!(drawobj->flags&KGSL_DRAWOBJ_PROFILING))return;')<profile.index('cmdobj->profiling_buf_entry=entry;')
    assert ioctl.index('drawobj->flags&=~(unsignedlong)KGSL_DRAWOBJ_PROFILING;')<ioctl.index('kgsl_drawobj_cmd_add_memlist(')
    retire=tok(body(src['sched'],'void adreno_hwsched_retire_cmdobj('))
    assert 'if(profile_buffer==NULL)return;' in retire
    assert retire.endswith('kgsl_drawobj_destroy(drawobj);}')
    node=tok(body(src['drawc'],'static int kgsl_drawobj_add_memobject('))
    assert 'kgsl_mem_entry_get' not in node and 'list_add_tail(&mem->node,head);return0;' in node
    replay=tok(body(src['sched'],'void adreno_hwsched_replay('))
    assert 'kgsl_context_invalid(hwsched->recurring_cmdobj->base.context)' in replay
    assert 'gpudev->send_recurring_cmdobj(adreno_dev,hwsched->recurring_cmdobj);' in replay


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule
    inputs=json.loads((o/'audit-inputs.json').read_text());src={k:Path(v).read_text() for k,v in inputs.items()};check(src);refused=[]
    mutations=[
        ('constructor-context-reference-removed','drawc','if (!_kgsl_context_get(context))','if (!context)'),
        ('STOP-temporary-object-destroy-removed','kgsl','if (!result)\n\t\t\tkgsl_drawobj_destroy(drawobj);','if (!result)\n\t\t\tkgsl_context_put(context);'),
        ('selected-core-LSR-falsely-enabled','gpulist','.features = ADRENO_APRIV | ADRENO_IOCOHERENT | ADRENO_AQE |','.features = ADRENO_APRIV | ADRENO_IOCOHERENT | ADRENO_AQE | ADRENO_LSR |'),
        ('profile-entry-gate-removed','drawc','if (!(drawobj->flags & KGSL_DRAWOBJ_PROFILING))\n\t\treturn;','if (!drawobj)\n\t\treturn;'),
    ]
    for name,key,before,after in mutations:
        s=dict(src)
        if key=='gpulist' or name=='constructor-context-reference-removed':
            marker='static const struct adreno_gen7_core adreno_gpu_core_gen7_9_1 =' if key=='gpulist' else 'static int drawobj_init('
            at=s[key].index(marker);prefix=s[key][:at];suffix=s[key][at:];assert before in suffix;s[key]=prefix+suffix.replace(before,after,1)
        else:assert s[key].count(before)==1;s[key]=s[key].replace(before,after,1)
        (o/(name+'.source')).write_text(s[key])
        try:check(s)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('source mutation accepted:'+name)
    (o/'drawobj-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,exact_source_only=True,no_driver_patch_or_target=True,no_API_refcount_object_or_phone_execution=True,no_successpeer_or_packet_model=True,no_old_suite_reexecution=True),indent=2)+'\n')
    print('4 new drawobj ownership/selection/profile source mutations refused;no API or model execution')


if __name__=='__main__':main()
