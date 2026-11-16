#!/usr/bin/env python3
"""Check only new source diagnostic capture;never executes a recovery method."""
from pathlib import Path
import argparse,json
HELPER='''IOReturn NativeAdrenoSubmit::retainRecoveryError(IOReturn status,RecoveryOperation operation)
{
    if(status) {
        const unsigned index=unsigned(operation)-1;
        const uint32_t bit=1u<<index;
        if(!(recovery_error_mask_&bit)) {
            first_recovery_error_[index]=status;
            recovery_error_mask_|=bit;
        }
        if(!first_recovery_operation_) {
            first_recovery_error_any_=status;
            first_recovery_operation_=operation;
        }
    }
    return status;
}
'''
def check(source,old):
    assert source.count(HELPER)==1,'raw32 first-failure mask/global preservation and same return'
    restored=source.replace(HELPER,'',1)
    for call,stage in [('now->restoreWptr()','RestorePending'),('now->restoreWptr()','RestoreOther'),('vm_->invalidateTlb()','StallInvalidate'),('stalled->kick()','StallKick')]:
        wrapped=f'retainRecoveryError({call},{stage})';assert restored.count(wrapped)==1
        restored=restored.replace(wrapped,call,1)
    assert restored==old,'original return,poison,reference and all other methods must be unchanged'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    s=(o/'candidate/NativeAdrenoSubmit.cpp').read_text();old=(o/'original/NativeAdrenoSubmit.cpp').read_text();check(s,old);refused=[]
    for name,before,after in [
        ('per-operation-first-guard-erased','if(!(recovery_error_mask_&bit))','if(true)'),
        ('global-first-guard-erased','if(!first_recovery_operation_)','if(true)'),
        ('full-API-status-folded','first_recovery_error_[index]=status;','first_recovery_error_[index]=!!status;'),
        ('kick-error-lost','(void)retainRecoveryError(stalled->kick(),StallKick);','(void)stalled->kick();')]:
        assert before in s;b=s.replace(before,after,1);(o/(name+'.cpp')).write_text(b)
        try:check(b,old)
        except AssertionError:refused.append(name)
        else:raise RuntimeError('source mutation accepted')
    (o/'source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,original_flow_restores_byte_identically=True,no_native_or_host_hardware_peer=True),indent=2)+'\n')
    print('4 new source negatives refused;original recovery flow byte-identical after inverse')
if __name__=='__main__':main()
