#!/usr/bin/env python3
"""Source-only context identifier/scalar producer audit;no atomics or driver calls executed."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-context-scalar-contract';N=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740'
assert not (O/'context-source-audit.json').exists()
def body(text,name):
 start=text.index(name);opened=text.index('{',start);depth=0
 for i in range(opened,len(text)):
  if text[i]=='{':depth+=1
  if text[i]=='}':
   depth-=1
   if depth==0:return text[start:i+1]
 raise AssertionError(name)
c=(N/'NativeAdrenoUserClient.cpp').read_text();h=(N/'NativeAdrenoRing.h').read_text()
def check(client,header):
 opened=body(client,'NativeAdrenoUserClient::open(')
 assert 'static uint32_t contexts;' in opened
 atomic='do context_=__atomic_add_fetch(&contexts,1,__ATOMIC_RELAXED); while(!context_);'
 assert opened.index('if(!growQueues())')<opened.index('open_=true;')<opened.index(atomic)<opened.index('return kIOReturnSuccess;')
 submitted=body(client,'NativeAdrenoUserClient::submit(')
 assert submitted.index('ring_->useContext(context_);')<submitted.index('submit_->nextPriority(')<submitted.index('submit_->submit(vm_,')
 scalar=body(header,'void useContext(uint32_t context)')
 assert scalar=='void useContext(uint32_t context) {if(context!=context_) {context_=context;reset_pending_=true;}}'
 assert 'uint32_t context() const {return context_;}' in header
check(c,h)
mutants=[('counter-atomic-lost',c.replace('__atomic_add_fetch(&contexts,1,__ATOMIC_RELAXED)','++contexts',1),h),('zero-skip-lost',c.replace('while(!context_);','while(false);',1),h),('user-context-carrier-lost',c.replace('    ring_->useContext(context_);\n','',1),h),('changed-context-reset-intent-lost',c,h.replace('context_=context;reset_pending_=true;','context_=context;reset_pending_=false;',1))];refused=[]
for name,client,header in mutants:
 assert client!=c or header!=h;(O/(name+'.source')).write_text(client if client!=c else header)
 try:check(client,header)
 except (AssertionError,ValueError):refused.append(name)
 else:raise AssertionError('context source mutation accepted '+name)
(O/'context-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,actual_relaxed_atomic_zero_skip_and_carrier_order_bound=True,scalar_change_only_sets_pending_intent=True,no_counter_context_ring_success_model=True,no_old_packet_HFI_Submit_CPU_VM_suite_or_target_reexecution=True,no_native_driver_atomic_callback_or_phone_execution=True),indent=2)+'\n')
print('4 new context source mutations refused;no counter/driver API or success peer executed')
