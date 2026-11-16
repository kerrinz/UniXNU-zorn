#!/usr/bin/env python3
"""Source-only exact native metadata validation before CPU-view side effects."""
from pathlib import Path
import argparse,json


def check(o, sources, r):
    for n,before,after in [
        ('NativeAdrenoPublish.cpp',r['publish_before'],r['publish_after']),
        ('NativeAdrenoUserClient.cpp',r['core_before'],r['core_after']),
        ('NativeAdrenoUserClient.h',r['header_before'],r['header_after']),
    ]:
        s=sources[n];assert s.count(after)==1
        assert s.replace(after,before,1)==(o/(n+'.unmap-preimage')).read_text(),'all unrelated source unchanged'
    pure=r['core_after'].split('IOReturn NativeAdrenoUserClient::cpuUnmap(')[0]
    assert '--entry->mapping_leases' not in pure and 'return kIOReturnSuccess;' in pure
    original=r['core_before'].replace('NativeAdrenoUserClient::cpuUnmap(', 'NativeAdrenoUserClient::checkCpuUnmap(',1).replace('    --entry->mapping_leases;\n','',1)
    assert pure.rstrip()==original
    p=r['publish_after']
    assert '&& !output_size' in p
    assert p.index('checkCpuUnmap(&request)') < p.index('if(checked)return checked;') < p.index('dropViews(request.token)') < p.index('return runCore(')
    assert p.index('IOLockLock(g.lock)') < p.index('checkCpuUnmap') < p.index('IOLockUnlock(g.lock)')
    assert 'const IOReturn checked=checkCpuUnmap(request);if(checked)return checked;' in r['core_after']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule;C=o/'cpu-unmap-candidate';r=json.loads((o/'unmap-replacements.json').read_text());sources={n:(C/n).read_text() for n in ['NativeAdrenoPublish.cpp','NativeAdrenoUserClient.cpp','NativeAdrenoUserClient.h']};check(o,sources,r)
    refused=[]
    for label,n,before,after in [
        ('validation-error-ignored','NativeAdrenoPublish.cpp','        if(checked)return checked;\n',''),
        ('lease-decrement-before-view-restored','NativeAdrenoUserClient.cpp','    if(!entry->mapping_leases)return kIOReturnBusy;\n','    if(!entry->mapping_leases)return kIOReturnBusy;\n    --entry->mapping_leases;\n'),
        ('invalid-output-schema-view-side-effect','NativeAdrenoPublish.cpp',' && !output_size',''),
    ]:
        s=dict(sources);assert before in s[n];s[n]=s[n].replace(before,after,1);(o/(label+'.cpp')).write_text(s[n])
        try:check(o,s,r)
        except AssertionError:refused.append(label)
        else:raise AssertionError('new CPU validation source mutation accepted')
    (o/'unmap-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,exact_original_CPU_validation_shared_without_state_mutation=True,only_correctly_validated_request_reaches_view_side_effects=True,original_lease_decrement_after_view_handling_preserved=True,no_native_object_method_or_success_peer_executed=True),indent=2)+'\n');print('3 new CPU-unmap validation source mutations refused;no native methods')


if __name__=='__main__':main()
