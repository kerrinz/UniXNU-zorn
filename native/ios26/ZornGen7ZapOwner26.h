// SPDX-License-Identifier: GPL-2.0-only
#pragma once
#include "ZornGen7ZapAuthority26.h"
#include <IOKit/IOLocks.h>
#include <libkern/c++/OSObject.h>
struct ggs_state;struct ggs_regs;
class ZornGen7InactiveOwner26;class ZornGen7HostRing26;class ZornGen7ScmOwner26;
class ZornGen7ZapOwner26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7ZapOwner26);
public:
    void free() override;
private:
    friend class ZornGen7DarwinBoardOwner;friend class ZornGen7ScmOwner26;friend class ZornGen7HostRing26;
    bool authenticatedForRing(const ZornGen7HostRing26 &) const;
    static IOReturn create(IORecursiveLock &,IORegistryEntry &,IOService &,ZornGen7InactiveOwner26 &,
        ZornGen7HostRing26 &,ZornGen7ScmOwner26 &,OSObject &,const ZornGen7ZapAuthority26 &,
        ZornGen7ZapOwner26 *&actualPartialOutput);
    IOReturn prepare();IOReturn loadWithHeldScm(const ggs_state &actualCxQualification);
    bool forwardAllowed(unsigned);static int queryGuard(void *);static int loadGuard(void *,unsigned);
    static int call(void *,ggs_regs *);static int delay(void *,unsigned);
    static int publishMetadata(void *,void *,uint64_t,unsigned);
    static int copySegment(void *,uint64_t,const uint8_t *,unsigned);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};
