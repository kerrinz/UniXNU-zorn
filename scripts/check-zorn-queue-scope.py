#!/usr/bin/env python3
"""Source-only queue admission/owner audit;never constructs queues or calls driver APIs."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-queue-scope-contract';N=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740'
assert not (O/'queue-source-audit.json').exists()
def body(text,name):
 start=text.index(name);opened=text.index('{',start);depth=0
 for i in range(opened,len(text)):
  if text[i]=='{':depth+=1
  if text[i]=='}':
   depth-=1
   if depth==0:return text[start:i+1]
 raise AssertionError(name)
client=(N/'NativeAdrenoUserClient.cpp').read_text();publish=(N/'NativeAdrenoPublish.cpp').read_text();submit=(N/'NativeAdrenoSubmit.cpp').read_text()
def check(c,p):
 grow=body(c,'NativeAdrenoUserClient::growQueues()')
 limit='if(queue_capacity_>=UINT32_MAX/2)return false;';allocate='Queue *made=IONewData(Queue,size);';refuse='if(!made)return false;';copy='for(uint32_t i=0;i<size;++i)made[i]=i<queue_capacity_?queues_[i]:Queue{};';free='if(queues_)IODeleteData(queues_,Queue,queue_capacity_);';assign='queues_=made;queue_capacity_=size;'
 assert grow.index(limit)<grow.index('const uint32_t size=queue_capacity_?queue_capacity_*2:8;')<grow.index(allocate)<grow.index(refuse)<grow.index(copy)<grow.index(free)<grow.index(assign)
 create=body(c,'NativeAdrenoUserClient::createQueue(');assert 'for(uint32_t i=1;i<queue_capacity_;++i)if(!queues_[i].active)' in create and 'queues_[i]={i,true};' in create and 'if(!growQueues())return kIOReturnNoMemory;' in create
 close=body(c,'NativeAdrenoUserClient::closeQueue(');assert close.index('if(!request->queue || request->queue>=queue_capacity_)return kIOReturnBadArgument;')<close.index('Queue &queue=queues_[request->queue];')<close.index('if(!queue.active)return kIOReturnBadArgument;')<close.index('submit_->queueOutstanding(queue_base_+request->queue)')<close.index('queue={};')
 scope=body(c,'NativeAdrenoUserClient::setScope(');assert 'queue_base%NativeAdrenoQueueRange' in scope and scope.index('ownRangeOutstanding()')<scope.index('queue_base_=queue_base;scoped_=true;')
 mount=body(p,'AGXDeviceUserClient::mount(');assert mount.index('IOLockLock(g.lock);')<mount.index('base=(uint64_t)g.next_client*NativeAdrenoQueueRange;')<mount.index('scoped=!g.next_client || !window?kIOReturnNoResources:core->setScope(')<mount.index('if(scoped==kIOReturnSuccess) {')<mount.index('if(!kernel)++g.next_client;')<mount.index('core_=core;')<mount.index('IOLockUnlock(g.lock);')
 assert p.count('++g.next_client')==1 and p.count('next_client=')==1
check(client,publish)
range_body=body(submit,'NativeAdrenoSubmit::rangeOutstanding(');assert 'job.active && job.queue-first<count' in range_body
assert 'enum : uint64_t {NativeAdrenoQueueRange=UINT64_C(1)<<32};' in (N/'NativeAdrenoSubmit.h').read_text()
abi=(N/'NativeAdrenoAbi.h').read_text();assert 'uint64_t queue;' in abi[abi.index('struct NativeAdrenoAbiQueue {'):abi.index('struct NativeAdrenoAbiQueueReply {')]
mutants=[('capacity-limit-erased',client.replace('if(queue_capacity_>=UINT32_MAX/2)return false;','',1),publish),('nullable-allocation-refusal-erased',client.replace('    if(!made)return false;\n    for(uint32_t i=0;i<size;++i)made[i]=i<queue_capacity_?queues_[i]:Queue{};','    for(uint32_t i=0;i<size;++i)made[i]=i<queue_capacity_?queues_[i]:Queue{};',1),publish),('scope-zero-terminal-refusal-erased',client,publish.replace('scoped=!g.next_client || !window?','scoped=!window?',1)),('queue-clear-before-outstanding',client.replace('    /* A queue must be drained by the caller before it disappears. */','    queue={};\n    /* A queue must be drained by the caller before it disappears. */',1),publish)]
refused=[]
for name,c,p in mutants:
 assert c!=client or p!=publish;(O/(name+'.source')).write_text(c if c!=client else p)
 try:check(c,p)
 except (AssertionError,ValueError):refused.append(name)
 else:raise AssertionError('queue source mutation accepted '+name)
result=dict(new_source_mutations_refused=refused,actual_nullable_allocation_failure_precedes_publication=True,actual_capacity_and_scope_zero_guards_bound=True,queue_clear_after_active_job_check=True,no_queue_allocator_counter_or_success_peer_model=True,no_old_suite_target_or_native_API_execution=True)
(O/'queue-source-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('4 new queue source mutations refused;no target/API/queue or allocation model')
