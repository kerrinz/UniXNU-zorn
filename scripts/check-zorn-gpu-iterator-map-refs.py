#!/usr/bin/env python3
"""Pinned iterator/map-reference source contracts; never invoke IOKit objects."""
from pathlib import Path
import argparse,json,re


def body(s, signature):
    start=s.index('{',s.index(signature));depth=0
    for i in range(start,len(s)):
        depth+=(s[i]=='{')-(s[i]=='}')
        if depth==0:return s[start:i+1]
    raise AssertionError('unclosed pinned function')


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


def check(s):
    assert 'uint8_tinlineStorage[4];' in tok(s['iterator_h'])
    init=tok(body(s['iterator'],'\nOSCollectionIterator::initWithCollection('))
    assert 'if(!super::init()||!inColl){returnfalse;}' in init
    storage=tok(body(s['iterator'],'\nOSCollectionIterator::initializeIteratorStorage('))
    assert 'if(collection->iteratorSize()>sizeof(inlineStorage)||isSubclassed())' in storage
    assert 'collection->initIterator(&inlineStorage[0])' in storage
    assert tok(body(s['set'],'\nOSSet::iteratorSize('))=='{returnsizeof(unsignedint);}'
    assert tok(body(s['set'],'\nOSSet::initIterator('))=='{unsignedint*iteratorP=(unsignedint*)inIterator;*iteratorP=0;returntrue;}'
    obj=tok(body(s['object'],'\nOSObject_typed_operator_new('))
    assert 'kalloc_type_impl_external(ktv,Z_WAITOK_ZERO)' in obj and 'assert(mem);' in obj
    mapping=tok(body(s['uc'],'\nis_io_connect_map_memory_into_task\n'))
    assert mapping.index('if(client->sharedInstance||(into_task!=current_task()))') < mapping.index('client->mappings->setObject(map);')
    assert 'IOMachPort::makeSendRightForTask(into_task,map,IKOT_IOKIT_OBJECT);map->release();' in mapping
    remove=tok(body(s['uc'],'\nIOUserClient::removeMappingForDescriptor('))
    assert 'map->retain();mappings->removeObject(map);break;' in remove
    port=tok(body(s['uc'],'\nIOMachPort::withObjectAndType('))
    assert 'obj->taggedRetain(OSTypeID(OSCollection));' in port
    initmap=tok(body(s['md'],'\nIOMemoryMap::init('))
    assert 'vm_map_reference(fAddressMap);' in initmap
    tagged=tok(body(s['md'],'\nIOMemoryMap::taggedRelease('))
    assert 'super::taggedRelease(tag,2);' in tagged
    unmap=tok(body(s['md'],'\nIOMemoryMap::unmap('))
    assert unmap.index('err=fMemory->doUnmap(') < unmap.index('fAddress=0;')
    assert 'vm_map_deallocate(fAddressMap);fAddressMap=NULL;' in unmap and unmap.endswith('returnerr;}')
    assert 'fAddressMap=NULL;}fAddress=0;UNLOCK;returnerr;}' in unmap
    free=tok(body(s['md'],'\nIOMemoryMap::free('))
    assert free.startswith('{unmap();') and 'fMemory.reset();' in free
    cpumap=tok(body(s['client'],'IOReturn NativeAdrenoUserClient::cpuMap('))
    assert 'if(entry->memory.imported())returnkIOReturnUnsupported;' in cpumap


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    s={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(s)
    mutations=[
        ('inline-set-iterator-falsely-heap-sized','set','return sizeof(unsigned int);','return 32;'),
        ('set-init-failure-invented','set','*iteratorP = 0;\n\treturn true;','*iteratorP = 0;\n\treturn false;'),
        ('mach-port-object-reference-erased','uc','obj->taggedRetain(OSTypeID(OSCollection));','/* reference erased */'),
        ('unmap-status-falsely-preserves-address','md','fAddress = 0;\n\n\tUNLOCK;\n\n\treturn err;','if(!err)fAddress = 0;\n\n\tUNLOCK;\n\n\treturn err;'),
    ];refused=[]
    progress=o/'source-progress.json'
    if progress.exists():
        import hashlib
        saved=json.loads(progress.read_text())
        for label in saved['already_refused']:
            assert hashlib.sha256((o/(label+'.source')).read_bytes()).hexdigest()==saved['source_SHA256'][label]
        refused=list(saved['already_refused'])
    for label,key,before,after in mutations:
        if label in refused:continue
        assert s[key].count(before)==1,label
        b=dict(s);b[key]=b[key].replace(before,after,1);(o/(label+'.source')).write_text(b[key])
        try:check(b)
        except (AssertionError,ValueError):refused.append(label)
        else:raise AssertionError('new iterator/ref contract mutation accepted')
    (o/'source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,no_native_iterator_map_reference_or_success_peer_executed=True,no_new_driver_patch_target_or_old_suite_reexecution=True),indent=2)+'\n')
    print('4 new iterator/map-reference source mutations refused;no IOKit/native execution')


if __name__=='__main__':main()
