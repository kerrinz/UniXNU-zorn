#!/usr/bin/env python3
"""Bind exact reclaim preflight publication/error/reference source;no pin or map model."""
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
    s=src['reclaim'];f=tok(body(s,'int kgsl_reclaim_to_pinned_state('))
    assert 'mutex_lock(&process->reclaim_lock);if(test_bit(KGSL_PROC_PINNED_STATE,&process->state))gotodone;' in f
    assert 'if(entry->memdesc.priv&KGSL_MEMDESC_RECLAIMED)valid_entry=kgsl_mem_entry_get(entry);spin_unlock(&process->mem_lock);if(valid_entry){ret=kgsl_memdesc_get_reclaimed_pages(entry);kgsl_mem_entry_put(entry);if(ret)gotodone;}next++;' in f
    assert f.index('next++;')<f.index('set_bit(KGSL_PROC_PINNED_STATE,&process->state);')<f.index('done:mutex_unlock(&process->reclaim_lock);returnret;')
    assert f.count('set_bit(KGSL_PROC_PINNED_STATE,&process->state);')==1
    restore=tok(body(s,'static int kgsl_memdesc_get_reclaimed_pages('))
    assert 'if(IS_ERR(page))returnPTR_ERR(page);' in restore
    assert 'memdesc->pages[i]=page;atomic_dec(&entry->priv->unpinned_page_count);' in restore
    assert restore.index('atomic_dec(&entry->priv->unpinned_page_count);')<restore.index('ret=kgsl_mmu_map(memdesc->pagetable,memdesc);if(ret)returnret;')<restore.index('memdesc->priv&=~KGSL_MEMDESC_RECLAIMED;')
    reclaim=tok(body(s,'static u32 kgsl_reclaim_process('))
    assert 'if(!mutex_trylock(&process->reclaim_lock))return0;' in reclaim
    assert 'if(atomic_read(&process->cmd_count))break;' in reclaim
    assert 'if(!entry->pending_free&&' in reclaim
    assert 'valid_entry=kgsl_mem_entry_get(entry);' in reclaim
    assert reclaim.index('if(!kgsl_mmu_unmap(')<reclaim.index('memdesc->pages[i]=NULL;')<reclaim.index('atomic_inc(&process->unpinned_page_count);')<reclaim.index('memdesc->priv|=KGSL_MEMDESC_RECLAIMED;')
    assert 'if(next)clear_bit(KGSL_PROC_PINNED_STATE,&process->state);' in reclaim
    assert reclaim.endswith('mutex_unlock(&process->reclaim_lock);return(pages_to_reclaim-remaining);}')
    h=src['header'];assert '#ifdef CONFIG_QCOM_KGSL_PROCESS_RECLAIM' in h
    disabled=h.split('#else',1)[1]
    assert tok(body(disabled,'static inline int kgsl_reclaim_to_pinned_state('))=='{return0;}'
    detach=tok(body(src['kgsl'],'static void kgsl_mem_entry_detach_process(struct kgsl_mem_entry *entry)\n{'))
    assert 'if(entry->memdesc.priv&KGSL_MEMDESC_RECLAIMED)atomic_sub(entry->memdesc.page_count,&entry->priv->unpinned_page_count);' in detach
    fault=tok(body(src['sharedmem'],'static vm_fault_t kgsl_paged_vmfault('))
    assert 'memdesc->pages[pgoff]=page;atomic_dec(&priv->unpinned_page_count);' in fault
    assert 'KGSL_MEMDESC_RECLAIMED' not in fault
    assert 'kref_get_unless_zero(&entry->refcount)' in tok(src['kgslh'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule
    paths=json.loads((o/'audit-inputs.json').read_text());src={k:Path(v).read_text() for k,v in paths.items()};check(src);refused=[]
    for name,sig,before,after in [
        ('PINNED-published-before-entry-walk','int kgsl_reclaim_to_pinned_state(','count = atomic_read(&process->unpinned_page_count);','set_bit(KGSL_PROC_PINNED_STATE, &process->state);\n\tcount = atomic_read(&process->unpinned_page_count);'),
        ('restore-error-ignored','static int kgsl_memdesc_get_reclaimed_pages(','if (ret)\n\t\treturn ret;','if (false)\n\t\treturn ret;'),
        ('entry-reference-put-before-restore','int kgsl_reclaim_to_pinned_state(','ret = kgsl_memdesc_get_reclaimed_pages(entry);\n\t\t\tkgsl_mem_entry_put(entry);','kgsl_mem_entry_put(entry);\n\t\t\tret = kgsl_memdesc_get_reclaimed_pages(entry);'),
        ('background-reclaim-lock-removed','static u32 kgsl_reclaim_process(','if (!mutex_trylock(&process->reclaim_lock))','if (false)'),
    ]:
        d=dict(src);a,b=span(d['reclaim'],sig);p=d['reclaim'][a:b];assert p.count(before)==1;p=p.replace(before,after,1);d['reclaim']=d['reclaim'][:a]+p+d['reclaim'][b:];(o/(name+'.source')).write_text(d['reclaim'])
        try:check(d)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('reclaim source mutation accepted:'+name)
    (o/'reclaim-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,disabled_zero_return_and_enabled_PINNED_skip_distinct=True,partial_restoration_retains_pages_before_returned_map_error=True,no_new_driver_patch_or_target=True,no_pin_map_refcount_success_model_or_API_execution=True,no_old_suite_reexecution=True),indent=2)+'\n')
    print('4new reclaim source mutations refused;OFF0/PINNEDskip/partialrestore source bound,no API/model')


if __name__=='__main__':main()
