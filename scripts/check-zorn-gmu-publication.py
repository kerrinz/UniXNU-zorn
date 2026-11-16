#!/usr/bin/env python3
"""Source-only returned-bool publication guard check;no native calls."""
from pathlib import Path
import argparse,json
BEFORE='''    setProperty("gmu-window-bases",bases);
    bases->release();
'''
AFTER='''    const bool published=setProperty("gmu-window-bases",bases);
    bases->release();
    if(!published) {stop(provider);return false;}
'''
def check(source,old):
    assert source.count(AFTER)==1,'exact bool branch/release once/existing stop on failure'
    assert source.replace(AFTER,BEFORE,1)==old,'all other flow,append,stop and source unchanged'
    assert source.index(AFTER)<source.index('    registerService();')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule;s=(o/'NativeAdrenoGmuService.cpp').read_text();old=(o/'NativeAdrenoGmuService.cpp.preimage').read_text();check(s,old);bad=[]
    for label,before,after in [('publication-false-guard-erased','    if(!published) {stop(provider);return false;}\n',''),('wrong-success-cleanup','if(!published)','if(published)'),('temporary-release-lost','    bases->release();\n    if(!published)','    if(!published)')]:
        assert before in s;b=s.replace(before,after,1);(o/(label+'.cpp')).write_text(b)
        try:check(b,old)
        except AssertionError:bad.append(label)
        else:raise RuntimeError('publication mutation accepted')
    (o/'source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=bad,all_other_source_byte_identical_after_inverse=True,no_native_property_or_success_peer=True),indent=2)+'\n');print('3 new source negatives refused;no append guard or cleanup policy expansion')
if __name__=='__main__':main()
