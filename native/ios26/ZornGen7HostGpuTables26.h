/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <IOKit/IOLocks.h>
#include <IOKit/IOReturn.h>
#include <libkern/c++/OSObject.h>
#include "sparse/ArmSmmu4KProgram.h"
enum class ZornGen7ProcessTableOperation26 : unsigned;
struct FhgStorage;class HoujiFullHostNativeMemory;class ZornGen7SmmuDomain26;
// Actual native BOs and NEW sparse page owners for the retained direct host
// software VA layout. No old FHG root or OEM TTBR1 root is installed/replayed.
// Prepared is CPU-only:bank programming,PRR,fault policy/IRQ,stream authority,
// synchronization and actual GPU-MMU start still need their real predecessor.
class ZornGen7HostGpuTables26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7HostGpuTables26);
public:
    void free() override;
private:
    friend class ZornGen7SmmuDomain26;
    static IOReturn create(IORecursiveLock &actualGate,OSObject &actualDomainOwner,
        FhgStorage &actualFrozenGraph,HoujiFullHostNativeMemory &actualOwnedMemory,
        OSObject &actualAllocatingParent,unsigned actualProbedInputBits,
        unsigned actualProbedStage1OutputBits,unsigned actualProbedPhysicalBits,
        ZornGen7HostGpuTables26 *&actualPartialOutput);
    // CPU-only private lower-table preparation from this owner's held kernel
    // ranges. Explicit requested IAS must fit the original real probe. Does
    // reserves a private software ASID and encodes a context,but does not
    // install it or publish an application client.
    IOReturn prepareProcessTables(unsigned requestedInputBits,
        class ZornGen7ProcessTables26 *&actualPartialOutput);
    IOReturn discardProcessTables(class ZornGen7ProcessTables26 *&actualCallerReference);
    // Domain-only primitives. Caller MUST hold its real execution/all-master
    // exclusion AND drain actual jobs/fences under the issuer before gate.
    // These functions neither acquire that permission nor fabricate idle.
    // Derive exact values from this owner's actual ASID bitmap and encoded
    // child context. This is not an execution grant; the domain must also
    // hold its native controller, actual client/OOB and drained issuer.
    bool nativeProcessWindow(class ZornGen7ProcessTables26 &,ZornGen7ProcessTableOperation26,
        unsigned actualBank,size_t actualOffset,uint64_t &ttbr0,uint16_t &asid,
        bool &writeRoot,bool &invalidate) const;
    IOReturn selectProcessTables(class ZornGen7ProcessTables26 &,const ZornSmmuSparse4KIo &,
        unsigned actualBank,size_t actualOffset,unsigned explicitPollBudget);
    IOReturn restoreKernelTables(const ZornSmmuSparse4KIo &,unsigned actualBank,size_t actualOffset,unsigned explicitPollBudget);
    IOReturn retireDetachedProcessTables(class ZornGen7ProcessTables26 *&,
        const ZornSmmuSparse4KIo &,unsigned actualBank,size_t actualOffset,unsigned explicitPollBudget);
    IOReturn attachProcessVm(class ZornGen7ProcessTables26 &,const ZornSmmuSparse4KIo &,
        size_t explicitSpanBudget,unsigned explicitPollBudget);
    IOReturn detachProcessVm(class ZornGen7ProcessTables26 &);
    IOReturn observeProcessTables(class ZornGen7ProcessTables26 &,const ZornSmmuSparse4KIo &,
        unsigned actualBank,size_t actualOffset);
    IOReturn prepare();
    bool prepared() const;
    IOReturn inspectPostCpContext(const ZornSmmuSparse4KIo &,unsigned actualBank,size_t actualOffset,
        bool &actualRestoreNeeded,uint32_t &actualExpectedTcr,uint32_t &actualObservedTcr);
    IOReturn restorePostCpContext(const ZornSmmuSparse4KIo &,unsigned actualBank,size_t actualOffset,unsigned explicitPollBudget);
    IOReturn attachDirectVm(class ZornGen7DirectVm26 &,const ZornSmmuSparse4KIo &,
        struct ZornGen7DirectVm26Routes &,size_t explicitSpanBudget,unsigned explicitPollBudget);
    IOReturn observeRuntimeUser(const ZornSmmuSparse4KIo &,unsigned actualBank,size_t actualOffset);
    IOReturn buildFirstContextWords(uint32_t (&actualWords)[25]);
    IOReturn prepareContexts(uint32_t actualId0,uint32_t actualId2,const uint16_t (&actualAsids)[2],
        bool actualCoherentWalk,const uint32_t (&actualBypassAttributes)[2],unsigned actualBankCount);
    IOReturn programContext(unsigned,const ZornSmmuSparse4KIo &,unsigned actualBank,
        size_t actualContextOffset,unsigned explicitPollBudget);
    IOReturn verifyContext(unsigned,const ZornSmmuSparse4KIo &,unsigned actualBank,size_t actualContextOffset);
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};
