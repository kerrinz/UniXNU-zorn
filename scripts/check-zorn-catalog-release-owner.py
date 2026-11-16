#!/usr/bin/env python3
"""Audit new catalog system-release handoff source,without native or object execution."""
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


def check(src):
    release=tok(body(src['memory'],'IOReturn NativeAdrenoMemory::releaseSystemInto('))
    assert 'if(!out||out->descriptor||!system_||!descriptor_||!prepared_||imported_||device_references_||quarantined_)returnrelease();' in release
    assert 'out->descriptor=descriptor_;out->bytes=bytes_;out->write_combined=write_combined_;out->cleaned=false;descriptor_=nullptr;prepared_=false;returnrelease();' in release
    assert 'descriptor_->release(' not in release and 'complete(' not in release
    assert '~NativeAdrenoMemory()=default;' in tok(src['memoryh'])
    free=tok(body(src['client'],'IOReturn NativeAdrenoUserClient::freeBo('))
    call='constIOReturnrelease=freed_pages_?entry->memory.releaseSystemInto(freed_pages_):entry->memory.release();'
    assert call in free and free.index(call)<free.index('if(release){noteFreeRefused(entry->imported,entry->handle,release);returnrelease;}')<free.index('clear(*entry);')
    assert 'voidcollectFreedPages(NativeAdrenoSystemPages*pages){freed_pages_=pages;}' in tok(src['clienth'])
    p=tok(src['publish']);at=p.index('NativeAdrenoSystemPagesfreed{};');p=p[at:]
    bind='connection->core_->collectFreedPages(&freed);';unbind='connection->core_->collectFreedPages(nullptr);'
    assert p.index(bind)<p.index('status=connection->live_?connection->core_->dispatch(')<p.index(unbind)<p.index('unlockTimed(lockWait);')<p.index('NativeAdrenoMemory::discardSystem(&freed);')
    discard=tok(body(src['memory'],'void NativeAdrenoMemory::discardSystem('))
    assert 'pages->descriptor->complete();pages->descriptor->release();*pages=NativeAdrenoSystemPages{};' in discard
    assert 'IOReturn' not in discard


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule
    src={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(src);refused=[]
    for name,key,before,after in [
        ('source-descriptor-not-withdrawn','memory','descriptor_=nullptr;prepared_=false;\n    return release();','prepared_=false;\n    return release();'),
        ('occupied-output-guard-removed','memory','if(!out || out->descriptor || !system_','if(!out || !system_'),
        ('stack-collector-not-unbound','publish','connection->core_->collectFreedPages(nullptr);',';'),
        ('Entry-clear-before-returned-release-error','client','if(release) {noteFreeRefused(entry->imported,entry->handle,release);return release;}','clear(*entry);\n    if(release) {noteFreeRefused(entry->imported,entry->handle,release);return release;}'),
    ]:
        d=dict(src);assert d[key].count(before)==1;d[key]=d[key].replace(before,after,1);(o/(name+'.source')).write_text(d[key])
        try:check(d)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('catalog release-owner source mutation accepted:'+name)
    (o/'release-owner-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,only_new_catalog_handoff_source_checked=True,unchanged_hold_retire_get_provenance_only=True,no_driver_patch_or_target=True,no_native_descriptor_page_map_refcount_success_model_or_API_execution=True,no_old_suite_reexecution=True),indent=2)+'\n')
    print('4new catalog release handoff source mutations refused;unchanged methods provenance only,no API/model')


if __name__=='__main__':main()
