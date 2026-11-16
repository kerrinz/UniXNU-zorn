#!/usr/bin/env python3
"""Bind exact SHMEM release ownership source;no file/page/refcount or unmap model."""
from pathlib import Path
import argparse,json,re


def mask(s):return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:' '*len(m.group(0)),s,flags=re.S)

def span(s,sig):
    m=mask(s);a=m.index('{',m.index(sig));d=0
    for j in range(a,len(s)):
        d+=(m[j]=='{')-(m[j]=='}')
        if not d:return a,j+1
    raise AssertionError('unclosed source block')

def body(s,sig):a,b=span(s,sig);return s[a:b]

def tok(s):return re.sub(r'\s+','',mask(s))


def check(src):
    s=src['sharedmem'];kgsl=src['kgsl']
    init=tok(body(s,'static int kgsl_memdesc_file_setup('));assert 'shmem_file_setup(' in init
    assert init.index('memdesc->shmem_filp=NULL;returnret;')<init.index('android_vendor_data1=(u64)memdesc;')<init.index('mapping_set_unevictable(')
    cb=tok(body(s,'static void kgsl_shmem_fill_page('))
    assert 'structkgsl_memdesc*memdesc=(structkgsl_memdesc*)inode->android_vendor_data1;' in cb
    assert 'if(IS_ERR_OR_NULL(memdesc))return;' in cb and 'kref_get' not in cb and 'get_file' not in cb
    assert '*folio=list_first_entry(&memdesc->shmem_page_list,structfolio,lru);list_del(&(*folio)->lru);' in cb
    small=tok(body(s,'static void _kgsl_free_pages('))
    assert small.index('if(memdesc->pages[i])put_page(memdesc->pages[i]);')<small.index('android_vendor_data1=0;')<small.index('fput(memdesc->shmem_filp);')
    large=tok(body(s,'static void kgsl_free_pages('))
    assert large.index('if(memdesc->priv&KGSL_MEMDESC_MAPPED)return;')<large.index('_kgsl_free_pages(memdesc);')<large.index('memdesc->page_count=0;')<large.index('kvfree(memdesc->pages);')<large.index('memdesc->pages=NULL;')
    shared=tok(body(s,'void kgsl_sharedmem_free('))
    assert 'if(memdesc->ops->put_gpuaddr)memdesc->ops->put_gpuaddr(memdesc);if(memdesc->ops->free)memdesc->ops->free(memdesc);' in shared
    release=tok(body(kgsl,'kgsl_mem_entry_destroy(struct kref *kref)'))
    assert 'kgsl_sharedmem_free(&entry->memdesc);kfree(entry);' in release
    assert 'KGSL_MEMDESC_MAPPED' not in release
    core=tok(body(kgsl,'int __init kgsl_core_init('));assert 'kgsl_register_shmem_callback();' in core
    reg=tok(body(s,'void kgsl_register_shmem_callback('));assert 'register_trace_android_rvh_shmem_get_folio(kgsl_shmem_fill_page,NULL);' in reg
    exit=tok(body(kgsl,'void kgsl_core_exit('));assert 'unregister_trace_android_rvh_shmem_get_folio' not in exit
    assert 'staticinlinevoidkgsl_sharedmem_put_gpuaddr(' in tok(src['header'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule
    src={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(src);refused=[]
    for name,key,sig,before,after in [
        ('inode-cookie-clear-removed','sharedmem','static void _kgsl_free_pages(','SHMEM_I(memdesc->shmem_filp->f_mapping->host)->android_vendor_data1 = 0;',';'),
        ('file-put-before-cookie-clear','sharedmem','static void _kgsl_free_pages(','SHMEM_I(memdesc->shmem_filp->f_mapping->host)->android_vendor_data1 = 0;\n\tfput(memdesc->shmem_filp);','fput(memdesc->shmem_filp);\n\tSHMEM_I(memdesc->shmem_filp->f_mapping->host)->android_vendor_data1 = 0;'),
        ('MAPPED-release-exclusion-removed','sharedmem','static void kgsl_free_pages(','if (memdesc->priv & KGSL_MEMDESC_MAPPED)\n\t\treturn;','if (false)\n\t\treturn;'),
        ('owner-retention-falsely-assumed','kgsl','kgsl_mem_entry_destroy(struct kref *kref)','kgsl_sharedmem_free(&entry->memdesc);\n\n\tkfree(entry);','kgsl_sharedmem_free(&entry->memdesc);\n\tif (entry->memdesc.priv & KGSL_MEMDESC_MAPPED) return;\n\tkfree(entry);'),
    ]:
        d=dict(src);a,b=span(d[key],sig);part=d[key][a:b];assert part.count(before)==1;part=part.replace(before,after,1);d[key]=d[key][:a]+part+d[key][b:];(o/(name+'.source')).write_text(d[key])
        try:check(d)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('SHMEM release source mutation accepted:'+name)
    (o/'shmem-release-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,raw_inode_cookie_not_a_memdesc_reference=True,voidfree_owner_retention_gap_recorded_not_repaired=True,actual_trace_hook_synchronization_core_unbound=True,no_new_driver_patch_or_target=True,no_native_file_page_map_success_model_or_API_execution=True,no_old_suite_reexecution=True),indent=2)+'\n')
    print('4new SHMEM release source mutations refused;cookie/voidfree ownership gap bound,no API/model')


if __name__=='__main__':main()
