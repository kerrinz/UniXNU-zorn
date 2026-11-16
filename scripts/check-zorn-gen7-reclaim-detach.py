#!/usr/bin/env python3
"""Audit remaining-unpinned detach accounting source;no page/map/refcount success model."""
from pathlib import Path
import argparse,json,re,shutil,subprocess


def mask(s):return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:' '*len(m.group(0)),s,flags=re.S)

def span(s,sig):
    m=mask(s);a=m.index('{',m.index(sig));d=0
    for j in range(a,len(s)):
        d+=(m[j]=='{')-(m[j]=='}')
        if not d:return a,j+1
    raise AssertionError('unclosed source block')

def body(s,sig):a,b=span(s,sig);return s[a:b]

def tok(s):return re.sub(r'\s+','',mask(s))


def contract(src):
    c=src['kgsl'];shared=src['sharedmem'];reclaim=src['reclaim']
    mmap=tok(body(c,'static int kgsl_mmap('));assert 'vma->vm_private_data=entry;' in mmap and 'vma->vm_ops=&kgsl_gpumem_vm_ops;' in mmap
    close=tok(body(c,'kgsl_gpumem_vm_close(struct vm_area_struct *vma)'));assert 'kgsl_mem_entry_put(entry);' in close
    free=tok(body(c,'long gpumem_free_entry('));assert 'if(!kgsl_mem_entry_set_pend(entry))return-EBUSY;' in free and 'kgsl_mem_entry_put(entry);return0;' in free
    release=tok(body(c,'kgsl_mem_entry_destroy(struct kref *kref)'))
    assert release.index('kgsl_mem_entry_detach_process(entry);')<release.index('kgsl_sharedmem_free(&entry->memdesc);')<release.index('kfree(entry);')
    fault=tok(body(shared,'static vm_fault_t kgsl_paged_vmfault('));assert 'memdesc->pages[pgoff]=page;atomic_dec(&priv->unpinned_page_count);' in fault and 'KGSL_MEMDESC_RECLAIMED' not in fault
    recover=tok(body(reclaim,'static int kgsl_memdesc_get_reclaimed_pages('));assert 'memdesc->pages[i]=page;atomic_dec(&entry->priv->unpinned_page_count);' in recover
    assert recover.index('if(IS_ERR(page))returnPTR_ERR(page);')<recover.index('ret=kgsl_mmu_map(memdesc->pagetable,memdesc);if(ret)returnret;')<recover.index('memdesc->priv&=~KGSL_MEMDESC_RECLAIMED;')
    gpu=tok(body(shared,'void kgsl_unmap_and_put_gpuaddr('));assert 'memdesc->pages=' not in gpu and 'memdesc->page_count=' not in gpu
    ops=tok(shared[shared.index('static const struct kgsl_memdesc_ops kgsl_page_ops ='):shared.index('static const struct kgsl_memdesc_ops kgsl_system_ops =')]);assert '.put_gpuaddr=kgsl_unmap_and_put_gpuaddr,' in ops
    mmu=tok(body(src['mmu'],'kgsl_mmu_map(struct kgsl_pagetable *pagetable,'));assert 'ret=pagetable->pt_ops->mmu_map(pagetable,memdesc);if(ret)returnret;' in mmu
    assert 'intkgsl_mmu_map(structkgsl_pagetable*pagetable,structkgsl_memdesc*memdesc);' in tok(src['mmuh'])


def check(original,candidate,i):
    assert candidate.count(i['after'])==1 and candidate.replace(i['after'],i['before'],1)==original
    f=tok(body(candidate,'static void kgsl_mem_entry_detach_process(struct kgsl_mem_entry *entry)\n{'))
    part='if(entry->memdesc.priv&KGSL_MEMDESC_RECLAIMED){unsignedinti,unpinned=0;for(i=0;i<entry->memdesc.page_count;i++)if(!entry->memdesc.pages[i])unpinned++;atomic_sub(unpinned,&entry->priv->unpinned_page_count);}'
    assert part in f
    assert f.index('kgsl_sharedmem_put_gpuaddr(&entry->memdesc);')<f.index(part)<f.index('kgsl_process_private_put(entry->priv);')<f.index('entry->priv=NULL;')
    assert 'atomic_set(' not in f and 'entry->memdesc.pages[i]=' not in f


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule
    src={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};contract(src)
    identity=json.loads((o/'source-repair-identity.json').read_text());original=Path(identity['original']).read_text();candidate=Path(identity['candidate']).read_text();check(original,candidate,identity);refused=[]
    for name,before,after in [
        ('full-page-count-debit-restored','atomic_sub(unpinned, &entry->priv->unpinned_page_count);','atomic_sub(entry->memdesc.page_count, &entry->priv->unpinned_page_count);'),
        ('restored-nonNULL-pages-counted','if (!entry->memdesc.pages[i])','if (entry->memdesc.pages[i])'),
        ('last-slot-not-counted','i < entry->memdesc.page_count; i++','i + 1 < entry->memdesc.page_count; i++'),
        ('page-count-reset-policy-added','atomic_sub(unpinned, &entry->priv->unpinned_page_count);','entry->memdesc.page_count = 0;\n\t\tatomic_sub(unpinned, &entry->priv->unpinned_page_count);'),
    ]:
        assert candidate.count(before)==1;s=candidate.replace(before,after,1);(o/(name+'.source')).write_text(s)
        try:check(original,s,identity)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('remaining-unpinned source mutation accepted:'+name)
    review=o/'source-review';review.mkdir();dst=review/'kgsl.c';shutil.copyfile(identity['original'],dst);patch=str((o/'remaining-unpinned-accounting.UNAPPLIED.patch').resolve())
    for args in [['--check',patch],[patch]]:
        r=subprocess.run(['git','apply',*args],cwd=review,capture_output=True,text=True);(o/('review-check.log' if '--check' in args else 'review-apply.log')).write_text(r.stdout+r.stderr);assert r.returncode==0
    assert dst.read_text()==candidate and dst.stat().st_ino!=Path(identity['candidate']).stat().st_ino
    (o/'detach-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,public_VMA_free_partial_restore_source_contract_bound=True,inverse_all_other_source_byte_identical=True,independent_original_review_matches=True,no_new_free_reset_retry_map_or_page_pointer_policy=True,no_native_target_or_Linux_fullbuild=True,no_page_map_counter_refcount_success_model_or_API_execution=True,no_old_suite_reexecution=True),indent=2)+'\n')
    print('4new detach-accounting source mutations refused;independent review/inverse exact,no page/map/refcount APIs/model')


if __name__=='__main__':main()
