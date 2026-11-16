#!/usr/bin/env python3
"""Check pinned source lifetime facts; never invoke a native allocator/provider."""
import argparse
import json
import re
from pathlib import Path


def body(source, signature):
    start = source.index(signature)
    start = source.index('{', start)
    depth = 0
    for i in range(start, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError('unclosed pinned function')


def tokens(source):
    return re.sub(r'\s+', '', re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S))


def check(sources):
    bmd = sources['buffer']
    gmd = sources['general']
    native = sources['native']
    init = tokens(body(bmd, 'IOBufferMemoryDescriptor::initWithPhysicalMask('))
    assert 'else{iomdOptions|=kIOMemoryAutoPrepare;' in init
    assert 'iomdOptions=kIOMemoryTypeVirtual64|kIOMemoryAsReference;' in init
    assert 'iomdOptions|=(options&kIOBufferDescriptorMemoryFlags);' in init
    construct = tokens(body(bmd, 'IOBufferMemoryDescriptor::inTaskWithPhysicalMask('))
    assert 'if(me&&!me->initWithPhysicalMask(inTask,options,capacity,1,physicalMask)){me.reset();}' in construct
    general_init = tokens(body(gmd, 'IOGeneralMemoryDescriptor::initWithOptions('))
    assert 'if((_flags&kIOMemoryAutoPrepare)&&prepare()!=kIOReturnSuccess){returnfalse;}' in general_init
    wire = tokens(body(gmd, 'IOGeneralMemoryDescriptor::wireVirtual('))
    assert 'if(_wireCount){if((kIOMemoryPreparedReadOnly&_flags)&&!(UPL_COPYOUT_FROM&uplFlags))' in wire
    complete = tokens(body(gmd, 'IOGeneralMemoryDescriptor::complete('))
    assert re.findall(r'return([^;]+);', complete) == [
        'kIOReturnSuccess', 'kIOReturnNotAttached', 'kIOReturnSuccess']
    assert 'if(kIOMemoryRemote&_flags)' in complete
    assert '_wireCount--;' in complete and 'panic("complete()whiledmaactive")' in complete
    free = tokens(body(gmd, 'IOGeneralMemoryDescriptor::free('))
    assert 'while(_wireCount){complete();}' in free
    alloc = tokens(body(native, 'int NativeAdrenoTablePages::allocatePage('))
    assert 'kIOMemoryPageable' not in alloc and 'kIODirectionInOut' in alloc
    assert 'if(!page){native_adreno_table_pages[3]=native_adreno_table_pages[3]+1;return1;}' in alloc
    release = tokens(body(native, 'IOReturn NativeAdrenoTablePages::release('))
    assert 'if(page->complete()!=kIOReturnSuccess){quarantined_=true;returnkIOReturnIOError;}' in release
    assert 'page->release();pages_[i].descriptor=nullptr;' in release
    assert 'pages_[i].mapping=nullptr' not in release
    prepare = tokens(body(native, 'IOReturn NativeAdrenoPrepareSmmuMemory('))
    assert 'if(provider->allocate(provider->cookie,&root,&mapping))returnkIOReturnNoMemory;' in prepare
    assert 'if(status!=ArmSmmu4KSuccess)returnstatus==ArmSmmu4KCapacity?kIOReturnNoResources:kIOReturnBadArgument;' in prepare
    assert prepare.index('provider->allocate') < prepare.index('ArmSmmu4KLivePrepare')
    live = tokens(body(sources['live'], 'ArmSmmu4KStatus ArmSmmu4KLivePrepare('))
    assert 'if(status!=ArmSmmu4KSuccess)returnstatus;' in live
    assert 'state->poisoned=' not in live
    assert live.index('if(status!=ArmSmmu4KSuccess)returnstatus;') < live.index('state->prepared=1;')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capsule', type=Path)
    o = parser.parse_args().capsule
    paths = json.loads((o / 'audit-inputs.json').read_text())
    sources = {k: Path(v).read_text() for k, v in paths.items()}
    check(sources)
    mutations = [
        ('no-auto-prepare', 'buffer', 'iomdOptions |= kIOMemoryAutoPrepare;', 'iomdOptions |= 0;'),
        ('invented-complete-error', 'general', 'traceInterval.setEndArg1(kIOReturnSuccess);\n\treturn kIOReturnSuccess;\n}\n\nIOOptionBits', 'traceInterval.setEndArg1(kIOReturnSuccess);\n\treturn kIOReturnIOError;\n}\n\nIOOptionBits'),
        ('fabricated-null-success', 'native', 'if(!page) {native_adreno_table_pages[3]=native_adreno_table_pages[3]+1;return 1;}', 'if(!page)return 0;'),
        ('assumed-early-poison', 'live', 'if(status!=ArmSmmu4KSuccess)return status;\n    const volatile uint64_t *root=', 'if(status!=ArmSmmu4KSuccess) {state->poisoned=1;return status;}\n    const volatile uint64_t *root='),
    ]
    refused = []
    for label, key, before, after in mutations:
        assert sources[key].count(before) == 1, label
        changed = dict(sources)
        changed[key] = changed[key].replace(before, after, 1)
        (o / (label + '.source')).write_text(changed[key])
        try:
            check(changed)
        except (AssertionError, ValueError):
            refused.append(label)
        else:
            raise AssertionError('source contract mutation accepted: ' + label)
    (o / 'source-audit.json').write_text(json.dumps({
        'new_source_mutations_refused': refused,
        'source_conditions_only_not_observed_native_status': True,
        'no_provider_callback_allocator_or_hardware_peer_invoked': True,
        'no_driver_patch_or_new_target_required': True,
    }, indent=2) + '\n')
    print('4 new pinned-source contract mutations refused; no native method executed')


if __name__ == '__main__':
    main()
