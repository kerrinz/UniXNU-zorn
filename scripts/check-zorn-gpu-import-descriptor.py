#!/usr/bin/env python3
"""Source-only exact catalog import/selected XNU descriptor contract checks."""
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
    raise AssertionError('unclosed pinned function')


def tok(s):
    return re.sub(r'\s+', '', re.sub(r'/\*.*?\*/|//[^\n]*', '', s, flags=re.S))


def check(s):
    assert re.search(r'#define\s+KERN_PROTECTION_FAILURE\s+2\b', s['kern_return'])
    assert 'enum:IOReturn{kNativeAdrenoProtectionFailure=2};' in tok(s['memory'])
    factory = tok(body(s['memory'], 'static IOMemoryDescriptor *importRange('))
    assert factory.index('options|kIOMemoryPersistent') < factory.index('if(range)')
    assert 'range=IOMemoryDescriptor::withAddressRange(address,bytes,options,static_cast<task_t>(task));' in factory
    native = tok(body(s['memory'], 'IOReturn NativeAdrenoMemory::importTask('))
    assert 'if(!imported_)returnkIOReturnNoMemory;' in native
    assert 'if(status==kNativeAdrenoProtectionFailure)' in native
    assert 'imported_=importRange(address,bytes,kIODirectionOut,task);' in native
    assert 'if(status==kIOReturnSuccess)read_only_=true;' in native
    assert native.index('if(status!=kIOReturnSuccess)') < native.index('prepared_=true;bytes_=bytes;')
    assert 'failed:(void)release();returnstatus;' in native
    selected = tok(body(s['general'], 'IOMemoryDescriptor::withAddressRanges('))
    assert 'if(task){options|=kIOMemoryTypeVirtual64;}' in selected
    assert 'initWithOptions(ranges,rangeCount,0,task,options,' in selected
    init = tok(body(s['general'], 'IOGeneralMemoryDescriptor::initWithOptions('))
    assert 'if((kIOMemoryPersistent&_flags)&&!_memRef)' in init
    assert 'err=memoryReferenceCreate(0,&_memRef);if(kIOReturnSuccess!=err){returnfalse;}' in init
    wire = tok(body(s['general'], 'IOGeneralMemoryDescriptor::wireVirtual('))
    assert 'error=memory_object_iopl_request(' in wire and 'error=vm_map_create_upl(' in wire
    assert 'if(error==KERN_FAILURE){error=kIOReturnCannotWire;}elseif(error==KERN_MEMORY_ERROR){error=kIOReturnNoResources;}' in wire
    assert wire.endswith('returnerror;}')
    release = tok(body(s['memory'], 'IOReturn NativeAdrenoMemory::release('))
    assert 'if(device_references_||quarantined_)returnkIOReturnBusy;' in release
    assert 'IOReturnstatus=imported_->complete();if(status!=kIOReturnSuccess){quarantined_=true;returnstatus;}prepared_=false;' in release
    assert release.index('imported_->complete()') < release.index('imported_->release();imported_=nullptr;')
    client = tok(body(s['client'], 'IOReturn NativeAdrenoUserClient::importBo('))
    assert 'if(entry->memory.release()!=kIOReturnSuccess){entry->used=true;entry->unreleasable=true;++live_;}' in client
    assert client.index('if(status)') < client.index('publish(*entry);')
    clear = tok(body(s['client'], 'void NativeAdrenoUserClient::clear('))
    assert 'entry.memory' not in clear
    mapped = tok(body(s['client'], 'IOReturn NativeAdrenoUserClient::mapBo('))
    assert 'permissions=entry->memory.readOnly()?(request->permissions&~2u):request->permissions;' in mapped


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capsule', type=Path)
    o = p.parse_args().capsule
    s = {k: Path(v).read_text() for k, v in json.loads((o / 'audit-inputs.json').read_text()).items()}
    check(s)
    changes = [
        ('persistent-attempt-erased', 'memory', 'options|kIOMemoryPersistent', 'options'),
        ('wrong-protection-domain-value', 'memory', 'kNativeAdrenoProtectionFailure=2', 'kNativeAdrenoProtectionFailure=3'),
        ('readonly-mapping-write-restored', 'client', '(request->permissions&~2u)', '(request->permissions)'),
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
            raise AssertionError('new descriptor contract mutation accepted')
    (o / 'source-audit.json').write_text(json.dumps({
        'new_source_mutations_refused': refused,
        'only_source_read_no_constructor_descriptor_ref_cache_or_phone_execution': True,
        'no_driver_patch_new_native_target_or_old_suite_reexecution': True,
    }, indent=2) + '\n')
    print('3 new exact import descriptor source mutations refused; no native methods')


if __name__ == '__main__':
    main()
