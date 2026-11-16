#!/usr/bin/env python3
"""Audit new exact reference boot polling source edges;never execute driver code."""
from pathlib import Path
import argparse,json,re


def body(s,t):
    a=s.index('{',s.index(t));depth=0
    for i in range(a,len(s)):
        depth+=(s[i]=='{')-(s[i]=='}')
        if not depth:return s[a:i+1]
    raise AssertionError('unclosed source function')


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


def check(s):
    macro=tok(s['header'][s['header'].index('#define kgsl_regmap_read_poll_timeout'):]).replace('\\','')
    assert '__ret||' in macro and '__ret?:__tmp;' in macro
    assert macro.index('region->ops->preaccess(region);')<macro.index('__tmp=read_poll_timeout(')
    read=tok(body(s['regmap'],'int kgsl_regmap_poll_read('))
    assert read.index('return-ENODEV;')<read.index('*val=readl_relaxed(')<read.index('rmb();')<read.index('return0;')
    lower=tok(body(s['core'],'int gmu_core_timed_poll_check('))
    assert 'returnkgsl_regmap_read_poll_timeout(&device->regmap,offset,val,(val&mask)==expected_ret,100,timeout_ms*1000);' in lower
    boot=tok(body(s['gmu'],'int gen7_gmu_device_start('))
    assert 'gmu_core_timed_poll_check(device,GEN7_GMU_CM3_FW_INIT_RESULT,BIT(8),100,GENMASK(8,0))' in boot
    assert boot.index('gmu_core_regwrite(device,GEN7_GMU_CM3_SYSRESET,0);')<boot.index('wmb();')<boot.index('gmu_core_timed_poll_check(')
    assert boot.index('gmu_core_fault_snapshot(device);')<boot.index('return-ETIMEDOUT;')
    snapshot=tok(body(s['core'],'void gmu_core_fault_snapshot('))
    assert 'ops->send_nmi(device,false);' in snapshot
    for sig in ['static int gen7_hwsched_gmu_first_boot(','static int gen7_hwsched_gmu_boot(']:
        b=tok(body(s['hwsched'],sig))
        assert 'ret=gen7_gmu_device_start(adreno_dev);if(ret)gotoerr;' in b
        assert b.index('gen7_gmu_device_start(adreno_dev)')<b.index('gen7_hwsched_hfi_start(adreno_dev)')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    s={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(s);refused=[]
    for label,key,old,new in [
        ('lower-reader-error-erased','header','__ret ?: __tmp;','__tmp;'),
        ('missing-region-falsely-success','regmap','return -ENODEV;','return 0;'),
        ('fresh-ready-lower-bits-ignored','gmu','BIT(8), 100, GENMASK(8, 0)','BIT(8), 100, BIT(8)'),
        ('fault-snapshot-falsely-inert','core','ops->send_nmi(device, false);','/* deleted NMI */'),
    ]:
        mutant=dict(s)
        if label=='missing-region-falsely-success':
            a=mutant[key].index('int kgsl_regmap_poll_read(');assert old in mutant[key][a:];mutant[key]=mutant[key][:a]+mutant[key][a:].replace(old,new,1)
        else:assert mutant[key].count(old)==1;mutant[key]=mutant[key].replace(old,new,1)
        (o/(label+'.source')).write_text(mutant[key])
        try:check(mutant)
        except (AssertionError,ValueError):refused.append(label)
        else:raise AssertionError('new reference source mutation accepted: '+label)
    (o/'boot-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,no_reference_or_native_driver_execution=True,no_success_poll_clock_MMIO_peer=True,actual_Linux_read_poll_timeout_implementation_still_unbound=True,no_old_suite_reexecution=True),indent=2)+'\n');print('4 new boot polling source mutations refused;no driver/MMIO/clock execution')


if __name__=='__main__':main()
