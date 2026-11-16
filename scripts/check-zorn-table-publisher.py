#!/usr/bin/env python3
"""Source-only callback validation-order check;never executes native methods."""
from pathlib import Path
import argparse,json
GUARD='''    auto *pages=static_cast<NativeAdrenoTablePages *>(cookie);
    if(!pages || !page || bytes!=4096 || ((uintptr_t)page&4095) || !pages->contains(page))return 1;
'''
MARK='''static int publishTable(void *cookie,volatile uint64_t *page,size_t bytes)
{
'''
def check(source,old):
    assert source.count(MARK+GUARD)==1,'real page validation must precede fastpath'
    assert source.index(MARK+GUARD)<source.index('    if(native_adreno_walk_coherent[0])',source.index(MARK))
    assert source.replace(GUARD,'',1)==old.replace(GUARD,'',1),'only existing guard moves;all other source unchanged'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule;s=(o/'NativeAdrenoSmmuMemory.cpp').read_text();old=(o/'NativeAdrenoSmmuMemory.cpp.preimage').read_text();check(s,old);bad=[]
    for label,b in [('coherent-validation-bypass-restored',old),('actual-membership-erased',s.replace(' || !pages->contains(page)','',1)),('page-size-check-erased',s.replace('bytes!=4096 || ','',1))]:
        (o/(label+'.cpp')).write_text(b)
        try:check(b,old)
        except AssertionError:bad.append(label)
        else:raise RuntimeError('new provider source mutation accepted')
    (o/'source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=bad,only_existing_guard_moved=True,no_native_callback_or_hardware_success_peer=True),indent=2)+'\n');print('3 new provider-source mutations refused;no callback invocation')
if __name__=='__main__':main()
