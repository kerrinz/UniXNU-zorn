#!/usr/bin/env python3
"""Audit new actual catalog factory inputs/prepare/output;SDK methods provenance only."""
from pathlib import Path
import argparse,json,re


def mask(s):return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:' '*len(m.group(0)),s,flags=re.S)

def span(s,sig):
    m=mask(s);a=m.index('{',m.index(sig));d=0
    for j in range(a,len(s)):
        d+=(m[j]=='{')-(m[j]=='}')
        if not d:return a,j+1
    raise AssertionError('unclosed source block')

def body(s,sig):a,b=span(s,sig);return s[a:b]

def tok(s):return re.sub(r'\s+','',mask(s))


def check(s):
    f=tok(body(s,'static IOBufferMemoryDescriptor *systemDescriptor('))
    options=f[:f.index('if(write_combined)')]
    assert 'kIODirectionInOut' in options and 'kIOMemoryMapperNone' in options and 'kIOMemoryPageable' in options
    assert 'kIOMemoryRemote' not in f
    assert 'IOBufferMemoryDescriptor::inTaskWithPhysicalMask(nullptr,(options&~static_cast<IOOptionBits>(kIOMemoryPageable))|static_cast<IOOptionBits>(kIOMemoryPhysicallyContiguous)' in f
    assert 'IOBufferMemoryDescriptor::inTaskWithOptions(nullptr,options,bytes,4096);' in f
    assert 'if(descriptor&&descriptor->prepare()!=kIOReturnSuccess){descriptor->release();descriptor=nullptr;}' in f
    prep=tok(body(s,'IOReturn NativeAdrenoMemory::prepareSystem('))
    assert 'if(!out||out->descriptor||!bytes||(bytes&4095))returnkIOReturnBadArgument;' in prep
    assert prep.index('if(!descriptor)returnkIOReturnNoMemory;')<prep.index('if(descriptor->getLength()!=bytes){descriptor->complete();descriptor->release();returnkIOReturnUnsupported;}')<prep.index('out->descriptor=descriptor;')
    assert prep.count('out->descriptor=descriptor;')==1
    assert 'out->cleaned=cleaned;' in prep and 'if(cleaned)NativeAdrenoNotePhase(' in prep
    discard=tok(body(s,'void NativeAdrenoMemory::discardSystem('))
    assert 'pages->descriptor->complete();pages->descriptor->release();*pages=NativeAdrenoSystemPages{};' in discard


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule
    p=Path(json.loads((o/'audit-inputs.json').read_text())['memory']);s=p.read_text();check(s);refused=[]
    for name,sig,before,after in [
        ('Remote-option-falsely-selected','static IOBufferMemoryDescriptor *systemDescriptor(','if(write_combined)options|=kIOMapWriteCombineCache;','options|=kIOMemoryRemote;\n    if(write_combined)options|=kIOMapWriteCombineCache;'),
        ('contiguous-task-policy-silently-changed','static IOBufferMemoryDescriptor *systemDescriptor(','inTaskWithPhysicalMask(nullptr,','inTaskWithPhysicalMask(kernel_task,'),
        ('unprepared-descriptor-handed-out','static IOBufferMemoryDescriptor *systemDescriptor(','if(descriptor && descriptor->prepare()!=kIOReturnSuccess)','if(false)'),
        ('output-published-before-length-rejection','IOReturn NativeAdrenoMemory::prepareSystem(','if(descriptor->getLength()!=bytes)','out->descriptor=descriptor;\n    if(descriptor->getLength()!=bytes)'),
    ]:
        a,b=span(s,sig);part=s[a:b];assert part.count(before)==1;part=part.replace(before,after,1);d=s[:a]+part+s[b:];(o/(name+'.source')).write_text(d)
        try:check(d)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('system factory source mutation accepted:'+name)
    (o/'factory-source-audit.json').write_text(json.dumps(dict(new_catalog_factory_source_mutations_refused=refused,SDK_functions_provenance_only_not_retested=True,no_new_driver_patch_or_target=True,no_native_factory_prepare_complete_descriptor_success_model_or_API_execution=True,no_old_suite_reexecution=True),indent=2)+'\n')
    print('4new catalog factory source mutations refused;SDK provenance only,no allocator/descriptor model or APIs')


if __name__=='__main__':main()
