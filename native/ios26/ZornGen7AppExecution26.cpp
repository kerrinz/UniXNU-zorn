// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornGen7AppExecution26.h"
#include "ZornGen7RegisterMaps26.h"
#include "ZornGen7HostRing26.h"
#include <IOKit/IOLib.h>
#include <kern/task.h>
#include <kern/task_ref.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
OSDefineMetaClassAndStructors(ZornGen7AppExecution26,OSObject)
namespace {bool normal(){return preemption_enabled() && !ml_at_interrupt_context() && ml_get_interrupts_enabled();}}
IOReturn ZornGen7AppExecution26::create(ZornGen7RegisterMaps26 &maps,ZornGen7HostRing26 &ring,
    IORecursiveLock &driverGate,IOUserClient &client,task_t task,OSObject &codeOwner,
    const ZornGen7AppAuthority26 &authority,IOService &gpu,IOMemoryDescriptor &gpuRegisters,
    IOService &gmu,IOMemoryDescriptor &gmuRegisters,ZornGen7AppExecution26 *&out)
{
    if(out || !normal() || IORecursiveLockHaveLock(&driverGate) || !task || task==kernel_task ||
       task!=current_task() || !authority.acquire || !authority.check || !authority.release)
        return kIOReturnBadArgument;
    if(!maps.providerClaimsHeld())return kIOReturnNotOpen;
    auto *p=new ZornGen7AppExecution26;if(!p)return kIOReturnNoMemory;
    if(!p->init()){p->release();return kIOReturnNoMemory;}
    p->retain();p->pinned_=true;out=p;
    // Capture every genuine reference before any foreign authority call.
    maps.retain();ring.retain();codeOwner.retain();client.retain();task_reference(task);
    gpu.retain();gpuRegisters.retain();gmu.retain();gmuRegisters.retain();
    p->maps_=&maps;p->ring_=&ring;p->driverGate_=&driverGate;p->codeOwner_=&codeOwner;
    p->client_=&client;p->task_=task;p->gpu_=&gpu;p->gpuRegisters_=&gpuRegisters;
    p->gmu_=&gmu;p->gmuRegisters_=&gmuRegisters;p->authority_=authority;
    p->gate_=IOLockAlloc();if(!p->gate_){p->phase_=Phase::Failed;return kIOReturnNoMemory;}
    p->phase_=Phase::Acquiring;
    auto raw=p->authority_.acquire(p->authority_.cookie,client,task,ring,gpu,gpuRegisters,gmu,gmuRegisters);
    if(!raw && !maps.providerClaimsHeld())raw=kIOReturnNotOpen;
    IOLockLock(p->gate_);p->last_=raw;p->phase_=raw?Phase::Failed:Phase::Held;IOLockUnlock(p->gate_);
    return raw; // Failure retains all inputs;there is no acquire retry.
}
IOReturn ZornGen7AppExecution26::checkCurrent(IOUserClient &client,ZornGen7AppOperation26 operation)
{
    if(!normal() || !gate_ || unsigned(operation)>unsigned(ZornGen7AppOperation26::Timestamp))return kIOReturnBadArgument;
    task_t caller=current_task();if(!caller)return kIOReturnBadArgument;task_reference(caller);
    IOLockLock(gate_);
    if(phase_!=Phase::Held || client_!=&client || !driverGate_ || IORecursiveLockHaveLock(driverGate_)){
        IOLockUnlock(gate_);task_deallocate(caller);return kIOReturnNotReady;}
    phase_=Phase::Checking;IOLockUnlock(gate_);
    // No owner/driver lock crosses the foreign check. Reentry sees Checking.
    auto raw=maps_->providerClaimsHeld() ? authority_.check(authority_.cookie,client,task_,caller,operation) : kIOReturnNotOpen;
    if(!raw && !maps_->providerClaimsHeld())raw=kIOReturnNotOpen;
    IOLockLock(gate_);last_=raw;phase_=raw?Phase::Failed:Phase::Held;IOLockUnlock(gate_);
    task_deallocate(caller);return raw;
}
IOReturn ZornGen7AppExecution26::closeAcquiredSession(IOUserClient &client)
{
    if(!normal() || !gate_)return kIOReturnNotReady;
    IOLockLock(gate_);
    if(phase_!=Phase::Held || client_!=&client || !driverGate_ || IORecursiveLockHaveLock(driverGate_) ||
       (oob_.attempted && !oob_.releaseWriteReturned)){
        IOLockUnlock(gate_);return kIOReturnNotReady;}
    phase_=Phase::Closing;IOLockUnlock(gate_);
    const auto raw=authority_.release(authority_.cookie,client,task_);
    IOLockLock(gate_);last_=raw;
    if(raw){phase_=Phase::Failed;IOLockUnlock(gate_);return raw;}
    phase_=Phase::Released;driverGate_=nullptr;IOLockUnlock(gate_);
    // Only actual release success returns real reference ownership. No
    // implicit register store,OOB release,reset,retry or failure cleanup.
    task_deallocate(task_);task_=TASK_NULL;client_->release();client_=nullptr;
    gpuRegisters_->release();gpuRegisters_=nullptr;gmuRegisters_->release();gmuRegisters_=nullptr;
    gpu_->release();gpu_=nullptr;gmu_->release();gmu_=nullptr;
    codeOwner_->release();codeOwner_=nullptr;maps_->release();maps_=nullptr;ring_->release();ring_=nullptr;
    pinned_=false;release();return kIOReturnSuccess; // caller reference remains
}
void ZornGen7AppExecution26::free()
{
    if(pinned_)return;
    if(gate_)IOLockFree(gate_);gate_=nullptr;OSObject::free();
}
