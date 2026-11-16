#!/usr/bin/env python3
"""Source-only check of catalog149 WPTR diagnostic retention;no callback runs."""
from pathlib import Path
import argparse,json

HELPER='''int NativeAdrenoRing::retainWptrCallback(int status,WptrCallbackStage stage)
{
    if(status && !first_wptr_callback_error_available_) {
        first_wptr_callback_error_=status;
        first_wptr_callback_stage_=stage;
        first_wptr_callback_error_available_=true;
    }
    return status;
}
'''

def check(source,old):
    assert source.count(HELPER)==1,'first signed-int capture/guard/unchanged return'
    restored=source.replace(HELPER,'',1)
    for original,stage,count in [
      ('io_.write32(io_.cookie,RingWptr,value)','WptrWrite',2),
      ('io_.barrier(io_.cookie)','WptrBarrier',1),
      ('io_.fence_status(io_.fence_cookie,0,&status)','WptrRead',1),
      ('io_.fence_status(io_.fence_cookie,1,&status)','WptrClear',2)]:
        wrapped=f'retainWptrCallback({original},{stage})'
        assert restored.count(wrapped)==count,(stage,'actual sites')
        restored=restored.replace(wrapped,original)
    assert restored==old,'all original public flow/order/poison/non-WPTR methods unchanged'

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capsule',type=Path);a=parser.parse_args();o=a.capsule
    s=(o/'NativeAdrenoRing.cpp').read_text();old=(o/'NativeAdrenoRing.cpp.preimage').read_text();check(s,old)
    bad=[]
    for name,before,after in [
        ('first-available-guard-erased','status && !first_wptr_callback_error_available_','status'),
        ('raw32-collapsed','first_wptr_callback_error_=status;','first_wptr_callback_error_=!!status;'),
        ('clear-call-result-lost','(void)retainWptrCallback(io_.fence_status(io_.fence_cookie,1,&status),WptrClear);','(void)io_.fence_status(io_.fence_cookie,1,&status);'),
        ('return-status-folded','    return status;\n}\nIOReturn NativeAdrenoRing::writeWptr','    return !!status;\n}\nIOReturn NativeAdrenoRing::writeWptr')]:
        assert before in s,name
        mutant=s.replace(before,after,1);(o/(name+'.cpp')).write_text(mutant)
        try:check(mutant,old)
        except AssertionError:bad.append(name)
        else:raise RuntimeError('new source mutation accepted: '+name)
    (o/'source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=bad,all_original_flow_and_other_methods_byte_identical_after_inverse=True,no_callbacks_or_native_execution=True),indent=2)+'\n')
    print('4 new catalog WPTR source mutations refused;original flow restored byte-identically')

if __name__=='__main__':main()
