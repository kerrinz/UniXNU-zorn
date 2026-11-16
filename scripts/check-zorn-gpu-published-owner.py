#!/usr/bin/env python3
"""Source-only balancing of one actual returned IOMemoryMap reference."""
from pathlib import Path
import argparse,json


def check(source, original, replacement):
    before, after = replacement['before'], replacement['after']
    assert source.count(after) == 1
    assert source.replace(after, before, 1) == original, 'all other source/flow/counters unchanged'
    assert after.count('mapping->release();') == 1
    assert 'while(IOMemoryMap *mapping=removeMappingForDescriptor(view))' in after
    assert after.index('mapping->release();') < after.index('forced_unmaps=')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    source=(o/'NativeAdrenoPublish.cpp').read_text();original=(o/'NativeAdrenoPublish.cpp.preimage').read_text();replacement=json.loads((o/'replacement.json').read_text());check(source,original,replacement)
    refused=[]
    for label,changed in [
        ('returned-reference-discard-restored',original),
        ('wrong-descriptor-reference-released',source.replace('mapping->release();','view->release();',1)),
        ('returned-reference-double-released',source.replace('mapping->release();','mapping->release();mapping->release();',1)),
    ]:
        (o/(label+'.cpp')).write_text(changed)
        try:check(changed,original,replacement)
        except AssertionError:refused.append(label)
        else:raise AssertionError('new reference-balance source mutation accepted')
    (o/'source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,only_returned_reference_balanced=True,no_host_mapping_reference_or_success_peer_executed=True),indent=2)+'\n')
    print('3 new returned-reference source mutations refused;other producer source byte-identical')


if __name__=='__main__':main()
