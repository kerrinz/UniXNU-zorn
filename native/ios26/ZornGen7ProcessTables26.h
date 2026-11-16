// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <libkern/c++/OSObject.h>
#include <mach/mach_types.h>
#include "sparse/ArmSmmu4KLive.h"
#include "sparse/ArmSmmu4KContext.h"
#include "sparse/ArmSmmu4KProgram.h"
#include "direct-runtime/ZornGen7DirectVm26.h"
#include "direct-runtime/ZornGen7DirectClient26.h"
class IOUserClient;class ZornGen7HostRing26;
class ZornGen7SmmuTablePages26;
// Private driver command,never part of IOUserClient or Metal wire ABI.
enum class ZornGen7ProcessTableOperation26 : unsigned {
    Prepare,Select,RestoreKernel,RetireDetached,DiscardNeverInstalled,AttachVm,DetachVm
};
// Private retained backing for one process table,not an active VM or lease.
// Parent owns/holds the actual shared kernel BOs. Only the existing table
// owner may construct this state;there is no address/object getter or public
// activation API. Failed partials retain every actual allocation.
class ZornGen7ProcessTables26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7ProcessTables26);
public:
    void free() override;
private:
    friend class ZornGen7HostGpuTables26;friend class ZornGen7SmmuDomain26;friend class ZornGen7HostRing26;
    OSObject *parent_=nullptr; // actual retained kernel-BO owner,for eventual normal retirement
    ZornGen7SmmuTablePages26 *pages_=nullptr;
    ZornSmmuSparse4KLiveArena arena_{};
    ZornSmmuSparse4KLiveState state_{};
    ZornSmmuSparse4KLiveVisibility visibility_{};
    ZornSmmuSparse4KLiveResult seed_{},audit_{};
    ZornSmmuSparse4KRange *ranges_=nullptr;
    size_t count_=0;
    // Software client aperture only:derived from this actual audited seed
    // ledger,not a hardware address or permission returned to a caller.
    uint64_t clientVaStart_=0,clientVaBytes_=0;
    ZornSmmuSparse4KContextConfig context_{};
    ZornSmmuSparse4KContextImage image_{};
    uint16_t asid_=0;bool asidHeld_=false,everExposed_=false;
    bool bankGrantAttempted_=false,bankGrantReturned_=false;int bankGrantRaw_=0;
    ZornSmmuSparse4KProgramResult switchWrite_{},switchSync_{},switchRead_{};
    ZornSmmuSparse4KProgramResult restoreWrite_{},restoreSync_{},restoreRead_{},retirementSync_{};
    // Actual mapper and callback context live with their page/ASID owner.
    ZornGen7DirectVm26 vm_;ZornGen7DirectVm26Routes routes_{};
    ZornGen7SmmuDomain26 *domain_=nullptr; // parent's retained original domain
    bool vmAttachAttempted_=false,vmAttached_=false,vmDetached_=false;
    // Native submit workspace exceeds the OSObject typed-allocation limit.
    // Own it as real separately allocated storage,as the other driver owners.
    struct ClientStorage {
        ZornGen7DirectSubmit26 submit;ZornGen7DirectClient26 client;NativeAdrenoAbiDeviceInfo info{};
        NativeAdrenoTimer timer;
        static void *operator new(size_t,void *p)noexcept{return p;}
    };
    ClientStorage *clientState_=nullptr;
    ZornGen7HostRing26 *ringOwner_=nullptr;ZornGen7ProcessTables26 *ringNext_=nullptr;
    IOUserClient *clientOwner_=nullptr;task_t clientTask_=TASK_NULL;
    bool clientOpenAttempted_=false,clientOpen_=false,clientClosed_=false,submitAttached_=false;
    bool pinned_=false,prepared_=false;
};
