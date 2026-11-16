/* SPDX-License-Identifier: GPL-2.0-only */
#pragma once
#include <IOKit/IOLocks.h>
#include <libkern/c++/OSObject.h>
#include "ZornGen7RpmhXoClock.h"
class ZornGen7DirectHfi26;class ZornGen7DarwinBoardOwner;class ZornGen7HwschedHfi26;class IOService;class ZornGen7IccInputs26;
// Actual stable K80 FDT identity plus independently selected power-node suffix.
// Source owner retains the real node/fuse-selection provenance. No unknown-to0
// conversion,default bin or performance-policy choice is provided here.
struct ZornGen7HostTableSelection26 {
    const uint8_t (&actualStockFdtDigest)[32];
    const uint32_t actualSelectedSuffix;
    OSObject &actualSelectionOwner;
};
class ZornGen7HostTables26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7HostTables26);
public:
    void free() override;
private:
    friend class ZornGen7DarwinBoardOwner;
    friend class ZornGen7CommandDbResources26;
    static IOReturn createAndPrepareResources(IORecursiveLock &,OSObject &,
        ZornGen7Rpmh::NativeCommandDbResourceReader &,OSObject &,const ZornGen7HostTableSelection26 &,
        ZornGen7HostTables26 *&);
    static IOReturn createAndPrepareInput(IORecursiveLock &,OSObject &,
        const ZornGen7Rpmh::ActualXoCommandDbSnapshot *,ZornGen7Rpmh::NativeCommandDbResourceReader *,
        OSObject &,const ZornGen7HostTableSelection26 &,ZornGen7HostTables26 *&);
    static IOReturn createAndPrepare(IORecursiveLock &actualBoardGate,
        OSObject &actualBoardOwner,const ZornGen7Rpmh::ActualXoCommandDbSnapshot &,
        OSObject &actualSnapshotOwner,const ZornGen7HostTableSelection26 &,
        ZornGen7HostTables26 *&actualPartialOutput);
    IOReturn sendDirectPerformance(ZornGen7DirectHfi26 &,uint32_t,uint32_t (&)[4]);
    IOReturn sendDirectBandwidth(ZornGen7DirectHfi26 &,uint32_t (&)[4]);
    IOReturn runHostProfile(ZornGen7HwschedHfi26 &);
    IOReturn requestDefaultClock(ZornGen7HwschedHfi26 &,IOService &actualSameBoardGpu);
    IOReturn requestDefaultBandwidth(ZornGen7HwschedHfi26 &,ZornGen7IccInputs26 &actualSameBoardIcc);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};
