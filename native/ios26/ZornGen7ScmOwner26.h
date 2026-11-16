// SPDX-License-Identifier: GPL-2.0-only
#pragma once
#include "ZornGen7CxScmOperation.h"
#include <IOKit/IOService.h>
// Independent actual epoch/conduit/power/security and exclusion of ALL foreign
// SCM callers (including legacy direct callers) through probe/init/failure.
// The owner below adds native serialization, not permission from a DT node or
// a local lock. Real code/context/resources stay retained across uncertainty.
struct ZornGen7ScmAuthority26 {
    void *cookie=nullptr;
    ZornGen7ColdBoot::OperationResult (*acquireExclusiveCxEpoch)(void *,IOService &actualGpu,
        IORegistryEntry &actualScmNode,uint32_t actualSourceRequest,uint32_t explicitEntryBudget)=nullptr;
};
class ZornGen7ScmOwner26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7ScmOwner26);
public:
    static IOReturn create(IORegistryEntry &actualRoot,IOService &actualGpu,OSObject &actualAuthorityOwner,
        const ZornGen7ScmAuthority26 &,ZornGen7ScmOwner26 *&actualPartialOutput);
    ZornGen7ColdBoot::OperationResult initializeCxRegisters(IORecursiveLock &actualStartupGate,
        uint32_t actualSourceRequest,uint32_t explicitEntryBudget);
    void free() override;
private:
    friend class ZornGen7ZapOwner26;
    IOReturn authenticateZap(class ZornGen7ZapOwner26 &);
    int invokeHeldZapFrame(struct ggs_regs &);
    class Session;
    struct Storage;Storage *storage_=nullptr;
    IORecursiveLock *gate_=nullptr;bool pinned_=false;
    ZornGen7ColdBoot::OperationResult checkHeld(const IORecursiveLock &,
        ZornGen7ScmRegisters::Convention,uint32_t,uint32_t) const;
};
