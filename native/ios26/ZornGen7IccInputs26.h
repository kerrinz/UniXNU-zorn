// SPDX-License-Identifier: GPL-2.0-only
#pragma once
#include <IOKit/IOService.h>
#include <IOKit/IOLocks.h>
#include "ZornGen7RpmhXoClock.h"
#include "ZornGen7OperationGuard26.h"
#include "ZornGen7IccQosAuthority26.h"
class ZornGen7RscRuntime26;
class ZornGen7DarwinBoardOwner;
namespace ZornGen7Clock {class NativeClockRoot;struct NativeClockFirmwareNode;}
// Real retained native registry/resource owner for the K80 GPU ICC path.
// Input construction is not ICC registration, clock/QoS initialization or an
// applied bandwidth vote. No nullable path/provider success is manufactured.
class ZornGen7IccInputs26 final : public OSObject {
    OSDeclareDefaultStructors(ZornGen7IccInputs26);
public:
    void free() override;
private:
    friend class ZornGen7DarwinBoardOwner;
    friend class ZornGen7SmmuDomain26;
    friend class ZornGen7QtbFence26;
    IOReturn acquireTbuPower(IOService &actualQtb,IOService &actualSmmu);
    bool tbuPowerHeldFor(IOService &actualQtb) const;
    IOReturn releaseTbuPower(IOService &actualQtb);
    friend class ZornGen7CommandDbResources26;
    IOReturn bindVoterFromResources(ZornGen7RscRuntime26 &,ZornGen7Rpmh::NativeCommandCache &,
        ZornGen7Rpmh::NativeReservation &,ZornGen7Rpmh::NativeCommandDbResourceReader &,OSObject &);
    IOReturn bindVoterInput(ZornGen7RscRuntime26 &,ZornGen7Rpmh::NativeCommandCache &,
        ZornGen7Rpmh::NativeReservation &,const ZornGen7Rpmh::ActualXoCommandDbSnapshot *,
        ZornGen7Rpmh::NativeCommandDbResourceReader *,OSObject &);
    friend class ZornGen7HostTables26;
    static IOReturn create(IOService &actualPlatform,IORegistryEntry &actualRoot,
        IOService &actualGpu,OSObject &actualStableTreeOwner,uint32_t actualSourceDdrType,
        ZornGen7IccInputs26 *&actualPartialOutput);
    IOReturn bindClock(ZornGen7Clock::NativeClockRoot &,
        const ZornGen7Clock::NativeClockFirmwareNode &actualGcc,IORecursiveLock *actualStartupGate);
    bool clockReady() const;
    IOReturn bindVoter(ZornGen7RscRuntime26 &,ZornGen7Rpmh::NativeCommandCache &,
        ZornGen7Rpmh::NativeReservation &,const ZornGen7Rpmh::ActualXoCommandDbSnapshot &,OSObject &);
    bool voterReady() const;
    IOReturn initializeInitialVotes();
    IOReturn applyBootstrapBandwidth();
    IOReturn finishHostBootstrap();
    IOReturn applyHostAverageMbps(uint32_t actualSourceAverage);
    IOReturn configureQos(OSObject &actualAuthorityCodeOwner,const ZornGen7OperationGuard26 &,const ZornGen7IccQosAuthority26 &);
    IOReturn configureNativeQos(OSObject &,const ZornGen7IccQosAuthority26 &);
    IOReturn prepareNativeQos(OSObject &,bool program);
    IOReturn configureQosImpl(OSObject &,const ZornGen7OperationGuard26 *,const ZornGen7IccQosAuthority26 &,unsigned nativeProbe=0);
    bool claimNativeQosProvider();
    bool nativeQosProviderHeld() const;
    bool qosUpdateBits(uint32_t actualSourceOffset,uint32_t mask,uint32_t value);
    bool qosAccess(uint32_t actualSourceOffset,bool write,uint32_t &actualValue);
    bool resolve();
    bool sourceReady() const;
    struct Storage;Storage *storage_=nullptr;bool pinned_=false;
};
