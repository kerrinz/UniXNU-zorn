#!/usr/bin/env python3
"""Audit exact module component lifetime edges without invoking any driver API."""
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
    probe=tok(body(s['hwsched'],'int gen7_hwsched_probe('))
    assert 'gen7_hwsched_dev=devm_kzalloc(&pdev->dev,sizeof(*gen7_hwsched_dev),GFP_KERNEL);' in probe
    assert 'if(!gen7_hwsched_dev)return-ENOMEM;' in probe
    assert probe.index('devm_kzalloc(')<probe.index('gen7_probe_common(')
    table=tok(body(s['gen7'],'const struct gen7_gpudev adreno_gen7_9_0_hwsched_gpudev ='))
    assert '.probe=gen7_hwsched_probe,' in table and '.remove=' not in table
    assert '.hfi_remove=gen7_hwsched_hfi_remove,' in table
    unbind=tok(body(s['adreno'],'\nstatic void adreno_unbind(struct device *dev)\n'))
    assert 'if(!device->pdev)return;' in unbind
    assert unbind.index('kgsl_device_platform_remove(device);')<unbind.index('component_unbind_all(dev,NULL);')<unbind.index('device->pdev=NULL;')
    remove=tok(body(s['gmu'],'void gen7_gmu_remove('))
    assert 'gen7_free_gmu_globals(gmu);' in remove and 'vfree(gmu->itcm_shadow);' in remove
    assert 'regmap' not in remove and 'iounmap' not in remove
    child=tok(body(s['gmu'],'static void gen7_gmu_unbind('))
    assert child.index('gen7_gpudev->hfi_remove(adreno_dev);')<child.index('gen7_gmu_remove(device);')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    s={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(s);refused=[]
    for name,key,old,new in [
        ('selected-probe-falsely-reuses-master','hwsched','gen7_hwsched_dev = devm_kzalloc(&pdev->dev, sizeof(*gen7_hwsched_dev),\n\t\t\t\tGFP_KERNEL);','gen7_hwsched_dev = dev_get_drvdata(&pdev->dev);'),
        ('selected-falsely-inherits-legacy-remove','gen7','const struct gen7_gpudev adreno_gen7_9_0_hwsched_gpudev = {\n\t.base = {','const struct gen7_gpudev adreno_gen7_9_0_hwsched_gpudev = {\n\t.base = {\n\t\t.remove = gen7_remove,'),
        ('probe-cleanup-guard-deleted','adreno','if (!device->pdev)\n\t\treturn;','/* deleted cleanup guard */'),
        ('GMU-remove-falsely-retires-regmap','gmu','gen7_free_gmu_globals(gmu);','gen7_free_gmu_globals(gmu);\n\tdevice->regmap.count = 0;'),
    ]:
        # Restrict to the exact newly audited function for repeated source calls.
        b=dict(s)
        if name=='GMU-remove-falsely-retires-regmap':
            a=b[key].index('void gen7_gmu_remove(');assert old in b[key][a:];b[key]=b[key][:a]+b[key][a:].replace(old,new,1)
        else:assert b[key].count(old)==1;b[key]=b[key].replace(old,new,1)
        (o/(name+'.source')).write_text(b[key])
        try:check(b)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('accepted new component lifetime source mutation: '+name)
    (o/'component-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,no_native_component_map_remove_or_phone_execution=True,no_success_allocator_mapping_or_lifetime_peer=True,no_old_suite_reexecution=True,actual_Linux_component_devres_implementation_unbound=True),indent=2)+'\n');print('4 new component lifetime source mutations refused;no driver/component execution')


if __name__=='__main__':main()
