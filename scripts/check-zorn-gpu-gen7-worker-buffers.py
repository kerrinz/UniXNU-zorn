#!/usr/bin/env python3
"""Audit new buffer publication/collection ownership edges;no memory/task model."""
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
    init=tok(body(s['hwsched'],'static int gen7_hwsched_gmu_init('))
    assert 'ret=gen7_hwsched_gmu_memory_init(adreno_dev);if(ret)returnret;returngen7_hwsched_hfi_init(adreno_dev);' in init
    mem=tok(body(s['hwsched'],'static int gen7_hwsched_gmu_memory_init('))
    assert mem.index('if(IS_ERR(gmu->trace.md))returnPTR_ERR(gmu->trace.md);')<mem.index('gmu_core_trace_header_init(&gmu->trace);')
    hfi=tok(body(s['hfi'],'int gen7_hwsched_hfi_init('))
    assert hfi.index('init_queues(hfi);')<hfi.index('kthread_run(hfi_f2h_main,adreno_dev,"gmu_f2h")')
    reserve=tok(body(s['gmu'],'struct kgsl_memdesc *gen7_reserve_gmu_kernel_block('))
    assert 'md=&gmu->gmu_globals[gmu->global_entries];' in reserve
    assert 'kgsl_allocate_kernel(device,md,size,0,KGSL_MEMDESC_SYSMEM)' in reserve
    kernel=tok(body(s['sharedmem'],'int kgsl_allocate_kernel('))
    assert 'list_add' not in kernel and 'device->globals' not in kernel
    globalalloc=tok(body(s['sharedmem'],'struct kgsl_memdesc *kgsl_allocate_global('))
    assert 'list_add_tail(&md->node,&device->globals);' in globalalloc
    free=tok(body(s['sharedmem'],'void kgsl_free_globals('))
    assert 'list_for_each_entry_safe(md,tmp,&device->globals,node)' in free
    private=tok(body(s['gmu'],'static void gen7_free_gmu_globals('))
    assert 'structkgsl_memdesc*md=&gmu->gmu_globals[i];' in private


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    s={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(s);refused=[]
    mutations=[
        ('trace-header-never-initialized','hwsched','gmu_core_trace_header_init(&gmu->trace);','/* omitted trace header init */'),
        ('worker-start-before-HFI-queues','hfi','\t\tinit_queues(hfi);','\t\thw_hfi->f2h_task = kthread_run(hfi_f2h_main, adreno_dev, "gmu_f2h");\n\t\tinit_queues(hfi);'),
        ('private-backing-falsely-enlisted','sharedmem','int kgsl_allocate_kernel(','int kgsl_allocate_kernel('),
        ('master-global-free-collection-changed','sharedmem','list_for_each_entry_safe(md, tmp, &device->globals, node)','list_for_each_entry_safe(md, tmp, &device->other_globals, node)'),
    ]
    for name,key,old,new in mutations:
        b=dict(s)
        if name=='private-backing-falsely-enlisted':
            a=b[key].index('{',b[key].index(old));b[key]=b[key][:a+1]+'\nlist_add_tail(NULL, &device->globals);'+b[key][a+1:]
        else:assert b[key].count(old)==1;b[key]=b[key].replace(old,new,1)
        (o/(name+'.source')).write_text(b[key])
        try:check(b)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('worker buffer source mutation accepted: '+name)
    (o/'buffer-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,no_native_allocation_thread_shared_memory_read_or_phone_execution=True,no_success_pointer_buffer_address_or_task_peer=True,no_old_allocator_geometry_HFI_or_stop_suite_reexecution=True,no_new_driver_patch_or_native_target=True),indent=2)+'\n');print('4 new buffer publication/collection source mutations refused;no allocator/thread/reader execution')


if __name__=='__main__':main()
