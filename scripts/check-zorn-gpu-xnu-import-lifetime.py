#!/usr/bin/env python3
"""Check selected XNU import lifetime source, without invoking any VM/native API."""
from pathlib import Path
import argparse
import json
import re


def body(s, signature):
    start = s.index('{', s.index(signature))
    depth = 0
    for i in range(start, len(s)):
        depth += (s[i] == '{') - (s[i] == '}')
        if depth == 0:
            return s[start:i + 1]
    raise AssertionError('unclosed pinned function')


def tok(s):
    return re.sub(r'\s+', '', re.sub(r'/\*.*?\*/|//[^\n]*', '', s, flags=re.S))


def check(s):
    entry = tok(body(s['entry'], '\nmach_make_memory_entry_internal('))
    assert 'vmk_flags.vmkf_copy_single_object=TRUE;' in entry
    assert 'vm_map_copy_extract(target_map,map_start,map_size,FALSE,&copy,&cur_prot,&max_prot,VM_INHERIT_SHARE,vmk_flags)' in entry
    assert 'user_entry->backing.copy=copy;' in entry
    assert 'user_entry->is_object=TRUE;' in entry
    no_senders = tok(body(s['entry'], '\nmach_memory_entry_no_senders('))
    assert no_senders.count('vm_map_copy_discard(named_entry->backing.copy);') == 2
    remap = tok(body(s['map'], '\nvm_map_remap_extract('))
    assert 'vm_object_reference_locked(object);' in remap
    assert 'result=KERN_PROTECTION_FAILURE;' in remap
    discard = tok(body(s['map'], '\nvm_map_copy_discard('))
    assert 'vm_object_deallocate(VME_OBJECT(entry));' in discard
    request = tok(body(s['named_upl'], '\nmemory_object_iopl_request('))
    assert 'if(named_entry->is_sub_map||named_entry->is_copy){returnKERN_INVALID_ARGUMENT;}' in request
    assert 'vm_object_reference(object);named_entry_unlock(named_entry);' in request
    assert '!=VM_PROT_READ){returnKERN_INVALID_RIGHT;}' in request
    assert request.index('vm_object_reference(object);') < request.index('ret=vm_object_iopl_request(')
    assert request.index('ret=vm_object_iopl_request(') < request.index('vm_object_deallocate(object);returnret;')
    create = tok(body(s['upl'], '\nvm_map_create_upl('))
    assert 'ret=KERN_PROTECTION_FAILURE;gotodone;' in create
    assert 'vm_map_reference(submap);' in create
    assert 'done:if(release_map){vm_map_deallocate(map);}returnret;' in create
    assert 'ret=copyinmap(map,offset,(void*)kaddr,*upl_size);' in create
    assert 'ret=vm_map_create_upl(kernel_map,' in create and 'kmem_free(kernel_map,kaddr,ksize);' in create
    iopl = tok(body(s['upl'], '\nvm_object_iopl_request('))
    assert 'upl->map_object=object;' in iopl
    assert 'vm_object_activity_begin(object);' in iopl
    assert 'vm_object_activity_end(object);' in iopl
    assert 'upl_destroy(upl);' in iopl
    for fn in ['upl_commit_range', 'upl_abort_range']:
        assert 'vm_object_activity_end(shadow_object);' in tok(body(s['upl'], '\n' + fn + '('))
    terminate = tok(body(s['object'], '\nvm_object_terminate('))
    assert 'if(object->paging_in_progress!=0||object->activity_in_progress!=0)' in terminate
    assert 'vm_object_reap_async(object);vm_object_unlock(object);returnKERN_FAILURE;' in terminate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capsule', type=Path)
    o = p.parse_args().capsule
    s = {k: Path(v).read_text() for k, v in json.loads((o / 'audit-inputs.json').read_text()).items()}
    check(s)
    changes = [
        ('named-UPL-temporary-reference-erased', 'named_upl', 'vm_object_reference(object);', '/* reference erased */'),
        ('named-right-mismatch-mislabelled', 'named_upl', 'return KERN_INVALID_RIGHT;', 'return KERN_PROTECTION_FAILURE;'),
        ('async-termination-mislabelled-synchronous', 'object', 'vm_object_reap_async(object);', 'vm_object_reap(object);'),
        ('ordinary-readonly-exec-copy-erased', 'upl', 'ret = copyinmap(map, offset, (void *)kaddr, *upl_size);', 'ret = KERN_SUCCESS;'),
    ]
    refused = []
    for label, key, before, after in changes:
        if label == 'named-right-mismatch-mislabelled':
            # All permission-mismatch returns of this exact lower function change together.
            changed = s[key].replace(before, after)
        elif label == 'async-termination-mislabelled-synchronous':
            begin = s[key].index('\nvm_object_terminate(')
            at = s[key].index(before, begin)
            changed = s[key][:at] + s[key][at:].replace(before, after, 1)
        else:
            assert s[key].count(before) >= 1, label
            changed = s[key].replace(before, after, 1)
        b = dict(s)
        b[key] = changed
        (o / (label + '.source')).write_text(changed)
        try:
            check(b)
        except (AssertionError, ValueError):
            refused.append(label)
        else:
            raise AssertionError('new lower lifetime mutation accepted: ' + label)
    (o / 'source-audit.json').write_text(json.dumps({
        'new_source_mutations_refused': refused,
        'source_only_no_native_VM_UPL_page_callback_or_success_peer': True,
        'no_driver_patch_or_unnecessary_native_target': True,
    }, indent=2) + '\n')
    print('4 new lower VM source mutations refused; no VM/UPL/native code executed')


if __name__ == '__main__':
    main()
