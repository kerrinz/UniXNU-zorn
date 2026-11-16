#!/usr/bin/env python3
"""Pinned changed catalog VM/kit contract checks, without executing their code."""
from pathlib import Path
import argparse
import json
import re


def body(source, signature):
    start = source.index('{', source.index(signature))
    depth = 0
    for i in range(start, len(source)):
        depth += (source[i] == '{') - (source[i] == '}')
        if depth == 0:
            return source[start:i + 1]
    raise AssertionError('unclosed function')


def tok(s):
    return re.sub(r'\s+', '', re.sub(r'/\*.*?\*/|//[^\n]*', '', s, flags=re.S))


def check(s):
    vm = tok(body(s['vm'], 'IOReturn NativeAdrenoVm::map('))
    assert 'mapImported' not in s['vm']
    assert vm.index('memory->holdForDevice()') < vm.index('*record={memory,0,')
    assert vm.index('*record={memory,0,') < vm.index('ArmSmmu4KLiveMapContextBatchExclusive(')
    cap = tok(body(s['vm'], 'if(status==ArmSmmu4KCapacity)'))
    assert cap.index('*record={};--objects_;') < cap.index('memory->retireAfterQuiescence()')
    assert 'result_.operation=status;returnkIOReturnNoMemory;' in cap
    transaction = vm.index('ArmSmmu4KLiveMapContextBatchExclusive(')
    after_transaction_fail = vm.index('if(status)returnfail(status);', transaction)
    assert vm.index('if(status==ArmSmmu4KCapacity)') < after_transaction_fail
    assert after_transaction_fail < vm.index('insert(record);')
    assert vm.index('insert(record);') < vm.index('*handle=record->handle;')
    fail = tok(body(s['vm'], 'IOReturn NativeAdrenoVm::fail('))
    assert 'mappings_[i].memory->quarantine();' in fail
    assert 'r.tables->quarantine();r.state->poisoned=1;' in fail
    hold = tok(body(s['memory'], 'IOReturn NativeAdrenoMemory::holdForDevice('))
    retire = tok(body(s['memory'], 'IOReturn NativeAdrenoMemory::retireAfterQuiescence('))
    assert 'if(device_references_==UINT32_MAX)returnkIOReturnNoResources;' in hold
    assert '++device_references_;returnkIOReturnSuccess;' in hold
    assert retire == '{if(!device_references_)returnkIOReturnBadArgument;if(quarantined_)returnkIOReturnNotReady;--device_references_;returnkIOReturnSuccess;}'
    leaf = tok(body(s['live'], 'static ArmSmmu4KStatus leaf_entry('))
    order = ['pages->allocate(', '++state->tables.table_pages;', 'publish_table_page(visibility->cookie,page,4096)', 'table[slot]=value;', 'publish_table_page(visibility->cookie,table,4096)']
    assert [leaf.index(v) for v in order] == sorted(leaf.index(v) for v in order)
    assert 'if(a->pages->allocate(a->pages->cookie,&physical,&page))returnArmSmmu4KCapacity;' in leaf
    update = tok(body(s['live'], 'static ArmSmmu4KStatus update('))
    assert update.index('if(status==ArmSmmu4KCapacity)returnstatus;') < update.index('*entry=map?descriptor(')
    assert 'poisoned:state->poisoned=1;if(peer)peer->state->poisoned=1;returnstatus;' in update
    assert 'r->must_retain_resources=1;' in update
    mapped = tok(body(s['client'], 'IOReturn NativeAdrenoUserClient::mapBo('))
    assert 'vm_->map(&entry->memory,' in mapped
    assert mapped.index('if(status)returnstatus;') < mapped.index('entry->mapped=handle;')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capsule', type=Path)
    o = p.parse_args().capsule
    paths = json.loads((o / 'audit-inputs.json').read_text())
    s = {k: Path(v).read_text() for k, v in paths.items()}
    check(s)
    changes = [
        ('capacity-to-poison', 'live', 'if(status==ArmSmmu4KCapacity)return status;', 'if(status==ArmSmmu4KCapacity)goto poisoned;'),
        ('leaf-store-before-capacity', 'live', 'if(status==ArmSmmu4KCapacity)return status;', '*entry=map?descriptor(0,0):0;if(status==ArmSmmu4KCapacity)return status;'),
        ('mapping-published-on-failure', 'client', 'if(status)return status;\n    entry->mapped=handle;', 'entry->mapped=handle;\n    if(status)return status;'),
        ('retire-fabricated-success', 'memory', 'if(quarantined_)return kIOReturnNotReady;\n    --device_references_;return kIOReturnSuccess;', 'if(quarantined_)return kIOReturnSuccess;\n    --device_references_;return kIOReturnSuccess;'),
    ]
    refused = []
    for label, key, before, after in changes:
        assert s[key].count(before) == 1, label
        b = dict(s)
        b[key] = b[key].replace(before, after, 1)
        (o / (label + '.source')).write_text(b[key])
        try:
            check(b)
        except (AssertionError, ValueError):
            refused.append(label)
        else:
            raise AssertionError('new contract mutation accepted: ' + label)
    (o / 'source-audit.json').write_text(json.dumps({
        'new_source_mutations_refused': refused,
        'source_only_no_native_method_callback_or_success_model': True,
        'capacity_retire_failure_shape_not_a_proven_stable_serial_failure': True,
    }, indent=2) + '\n')
    print('4 new changed-VM/kit source contract mutations refused; no native execution')


if __name__ == '__main__':
    main()
