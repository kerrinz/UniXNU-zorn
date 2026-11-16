#!/usr/bin/env python3
"""Check exact public batch shape and timestamp prevalidation source. No queue/object model."""
from pathlib import Path
import argparse,json,re


def mask(s):return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:' '*len(m.group(0)),s,flags=re.S)


def span(s,sig):
    m=mask(s);a=m.index('{',m.index(sig));d=0
    for i in range(a,len(s)):
        d+=(m[i]=='{')-(m[i]=='}')
        if not d:return a,i+1
    raise AssertionError('unclosed source block')


def body(s,sig):a,b=span(s,sig);return s[a:b]

def tok(s):return re.sub(r'\s+','',mask(s))


def check(src):
    kgsl=src['kgsl'];s=src['dispatcher']
    kinds=tok(body(kgsl,'static unsigned int _process_command_input('))
    assert 'if(flags&KGSL_DRAWOBJ_MARKER)returnMARKEROBJ_TYPE;elseif(flags&KGSL_DRAWOBJ_SYNC)returnSYNCOBJ_TYPE;' in kinds
    assert 'if(numsyncs&&numcmds)returnSYNCOBJ_TYPE|CMDOBJ_TYPE;' in kinds
    assert 'CMDOBJ_TYPE|MARKEROBJ_TYPE' not in kinds
    for sig in ['long kgsl_ioctl_gpu_command(','long kgsl_ioctl_submit_commands(']:
        f=tok(body(kgsl,sig));assert 'structkgsl_drawobj*drawobj[2];' in f
        assert f.index('if(type&SYNCOBJ_TYPE)')<f.index('if(type&(CMDOBJ_TYPE|MARKEROBJ_TYPE))')
        assert f.count('kgsl_drawobj_cmd_create(')==1
        assert 'if(result&&result!=-EPROTO)while(i--)kgsl_drawobj_destroy(drawobj[i]);' in f
    aux=tok(body(kgsl,'long kgsl_ioctl_gpu_aux_command('))
    assert 'if(param->numcmds!=1)return-EINVAL;' in aux
    assert aux.index('drawobjs[index++]=DRAWOBJ(tsobj);')<aux.index('drawobjs[index++]=DRAWOBJ(bindobj);')
    assert aux.index('drawobjs[index++]=DRAWOBJ(timelineobj);')<aux.index('drawobjs[index++]=DRAWOBJ(markerobj);')
    assert 'for(i=0;i<count;i++)kgsl_drawobj_destroy(drawobjs[i]);' in aux
    q=tok(body(s,'static int adreno_hwsched_queue_cmds('))
    saved=q.index('user_ts=*timestamp;');pre=q.index('if(timestamp_cmp(drawctxt->timestamp,user_ts)>=0)');loop=q.index('for(i=0;i<count;i++){switch(drawobj[i]->type)')
    assert q.index('spin_lock(&drawctxt->lock);')<saved<pre<loop
    assert q.index('ret=_check_context_state_to_queue_cmds(drawctxt,count);')<saved
    sync=tok(body(s,'static void _queue_syncobj('));timeline=tok(body(s,'static void _queue_timelineobj('))
    assert '*timestamp=0;drawobj->timestamp=0;_queue_drawobj(drawctxt,drawobj);' in sync
    assert 'drawobj->timestamp=0;_queue_drawobj(drawctxt,drawobj);' in timeline
    assert 'drawctxt->timestamp' not in sync+timeline
    ts=tok(body(s,'static int get_timestamp('))
    assert 'if(timestamp_cmp(drawctxt->timestamp,user_ts)>=0)return-ERANGE;drawctxt->timestamp=user_ts;' in ts
    marker=tok(body(s,'static int _queue_markerobj('))
    assert marker.index('ret=get_timestamp(drawctxt,drawobj,timestamp,user_ts);')<marker.index('if(!drawctxt->queued&&kgsl_check_timestamp(')
    assert '_retire_timestamp(drawobj);return1;' in marker
    assert q.index('spin_unlock(&drawctxt->lock);',loop)<q.index('if(_kgsl_context_get(&drawctxt->base))')
    assert 'llist_add(&job->node,&hwsched->jobs[drawctxt->base.priority]);adreno_hwsched_trigger(adreno_dev);' in q
    ctor=tok(body(src['drawc'],'struct kgsl_drawobj_cmd *kgsl_drawobj_cmd_create('))
    assert 'drawobj_init(device,context,&cmdobj->base,(type&(CMDOBJ_TYPE|MARKEROBJ_TYPE)))' in ctor


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule
    files=json.loads((o/'audit-inputs.json').read_text());src={k:Path(v).read_text() for k,v in files.items()};check(src);refused=[]
    changes=[
        ('user-timestamp-precheck-removed','dispatcher','static int adreno_hwsched_queue_cmds(','if (timestamp_cmp(drawctxt->timestamp, user_ts) >= 0) {','if (false) {'),
        ('sync-prefix-changes-context-timestamp','dispatcher','static void _queue_syncobj(','*timestamp = 0;','*timestamp = 0;\n\tdrawctxt->timestamp++;'),
        ('combined-CMD-MARKER-type-created','kgsl','static unsigned int _process_command_input(','return MARKEROBJ_TYPE;','return CMDOBJ_TYPE | MARKEROBJ_TYPE;'),
        ('aux-marker-precedes-timeline','kgsl','long kgsl_ioctl_gpu_aux_command(','drawobjs[index++] = DRAWOBJ(timelineobj);','drawobjs[index++] = DRAWOBJ(markerobj);'),
    ]
    for name,key,sig,before,after in changes:
        d=dict(src);a,b=span(d[key],sig);part=d[key][a:b];assert before in part;part=part.replace(before,after,1);d[key]=d[key][:a]+part+d[key][b:];(o/(name+'.source')).write_text(d[key])
        try:check(d)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('batch-owner source mutation accepted:'+name)
    (o/'batch-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,public_batch_has_at_most_one_timestamp_allocator=True,generic_partial_batch_shape_not_proven_publicly_reachable=True,no_driver_patch_or_target=True,no_queue_refcount_successpeer_or_API_execution=True,no_old_suite_reexecution=True),indent=2)+'\n')
    print('4new batch-owner source mutations refused;no batch success model/API/phone execution')


if __name__=='__main__':main()
