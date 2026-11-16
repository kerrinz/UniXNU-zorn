#!/usr/bin/env python3
"""Source-only region producer/lifetime checks;no mapping or hardware peers."""
from pathlib import Path
import argparse,json,re


def body(s,t):
    a=s.index('{',s.index(t));d=0
    for i in range(a,len(s)):
        d+=(s[i]=='{')-(s[i]=='}')
        if not d:return s[a:i+1]
    raise AssertionError('unclosed function')


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


def check(s):
    reg=tok(body(s['regmap'],'int kgsl_regmap_add_region('))
    assert 'if(!res)return-ENODEV;' in reg
    assert 'if(!ret)regmap->count++;returnret;' in reg
    get=tok(body(s['regmap'],'struct kgsl_regmap_region *kgsl_regmap_get_region('))
    assert 'for(i=0;i<regmap->count;i++)' in get
    assert 'if(in_range(offset,region->offset,region->size))returnregion;' in get
    gmu=tok(body(s['gmu'],'static int gen7_gmu_reg_probe('))
    assert 'ret=kgsl_regmap_add_region(&device->regmap,gmu->pdev,"gmu",NULL,NULL);' in gmu
    assert 'kgsl_regmap_add_region(&device->regmap,gmu->pdev,"gmu_ao_blk_dec0",NULL,NULL);returnret;' in gmu
    assert gmu.count('ret=')==1
    pre=tok(body(s['adreno'],'static void adreno_regmap_op_preaccess('))
    assert 'if(!device->snapshot_atomic&&!in_interrupt())kgsl_pre_hwaccess(device);' in pre
    lower=tok(body(s['power'],'void kgsl_pre_hwaccess('))
    assert lower=='{WARN_ON(!mutex_is_locked(&device->mutex));if(!gmu_core_gpmu_isenabled(device))WARN_ON(!kgsl_pwrctrl_isenabled(device));}'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);p.add_argument('--resume-after-failure',action='store_true');args=p.parse_args();o=args.capsule
    s={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(s);refused=[]
    if args.resume_after_failure:
        import hashlib
        saved=json.loads((o/'checker-first-failure.json').read_text())
        assert {k:hashlib.sha256(v.encode()).hexdigest() for k,v in s.items()}==saved['source_SHA']
        refused=list(saved['completed_before_failure'])
    for name,key,old,new in [
        ('failed-add-publishes-count','regmap','if (!ret)\n\t\tregmap->count++;','if (ret)\n\t\tregmap->count++;'),
        ('GMU-falsely-inherits-GPU-preaccess','gmu','"gmu", NULL, NULL);','"gmu", &adreno_regmap_ops, device);'),
        ('preaccess-falsely-powers-on','power','WARN_ON(!mutex_is_locked(&device->mutex));','kgsl_pwrctrl_enable(device);'),
        ('optional-missing-falsely-primary-error','gmu','\tkgsl_regmap_add_region(&device->regmap, gmu->pdev, "gmu_ao_blk_dec0", NULL, NULL);','\tret = kgsl_regmap_add_region(&device->regmap, gmu->pdev, "gmu_ao_blk_dec0", NULL, NULL);'),
    ]:
        if name in refused:continue
        assert s[key].count(old)==1;mut=dict(s);mut[key]=s[key].replace(old,new,1);(o/(name+'.source')).write_text(mut[key])
        try:check(mut)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('new region source mutation accepted: '+name)
    (o/'region-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,no_provider_map_preaccess_power_or_phone_execution=True,no_success_mapping_address_peer=True,no_driver_patch_or_old_suite_reexecution=True),indent=2)+'\n');print('4 new region/preaccess source mutations refused;no native/provider execution')


if __name__=='__main__':main()
