// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <IOKit/IOReturn.h>
#include "ZornGen7CommandDbStatus26.h"
#include "ZornGen7RscControllerStatus26.h"
#include <mach/kern_return.h>
#include <stdint.h>
#include <IOKit/IOLocks.h>
class IOService;class IORegistryEntry;class OSObject;class ZornGen7NativeBoardStage26;
inline constexpr uint32_t ZornGen7BoardPreparedPhase26=3;
struct ZornGen7PlatformBoardStatus26 {
    bool setupReturned=false;IOReturn setupRaw=kIOReturnNotReady;
    bool threadReturned=false,threadHandleReturned=false;kern_return_t threadRaw=KERN_FAILURE;
    bool workerReturned=false,inputReturned=false;IOReturn inputRaw=kIOReturnNotReady;
    bool preparationReturned=false;IOReturn preparationRaw=kIOReturnNotReady;
    struct ProviderObservation {
        bool entryFound=false,serviceFound=false,parentFound=false;
        bool isOpen=false,isInactive=false,parentIsOpen=false,parentIsInactive=false;
        uint64_t entryId=0,parentId=0;
        char className[40]{};
        char parentClassName[40]{};
    };
    struct Stage {
        uint32_t phase=0;
        bool boardConstructionReturned=false,boardPreparationReturned=false;
        IOReturn boardConstructionRaw=kIOReturnNotReady;
        bool clocksReturned=false,xoReturned=false,xoCoreInitialized=false;
        IOReturn clocksRaw=kIOReturnNotReady;
        ProviderObservation gpuProvider{},gmuProvider{};
        bool gpuGmuShareParentObserved=false;
        bool providerClaimRequested=false,providerClaimAttempted=false,providerClaimHeld=false;
        IOReturn providerClaimRaw=kIOReturnNotReady;
    } stage;
    // Optional CPU-only backing/firmware preparation for the later GPU owner
    // graph. It grants no GPU access and reports the real partial owner state.
    struct CpuMemoryPreparation {
        bool optionPresent=false;uint32_t optionValue=0;
        bool requested=false,attempted=false;
        IOReturn admissionRaw=kIOReturnNotReady;
        bool ownerCreateReturned=false;IOReturn ownerCreateRaw=kIOReturnNotReady;
        bool prepareReturned=false;uint32_t phase=0;
        bool cpuQueryReturned=false;IOReturn cpuQueryRaw=kIOReturnNotReady;uint64_t cpuPageBytes=0;
        bool graphStatusReturned=false;int graphStatus=0;
        bool firmwarePrepareReturned=false;uint32_t firmwarePrepareCode=0;
        bool zeroAllocationReturned=false;IOReturn zeroAllocationRaw=kIOReturnNotReady;
        bool zeroCacheReturned=false;IOReturn zeroCacheRaw=kIOReturnNotReady;
        bool zeroPreparedCpuOnly=false;
    } cpuMemory;
    // Optional continuation that resolves the retained native K80 GPU/GMU
    // nodes and captures their genuine memory descriptors. It grants no MMIO,
    // DMA, SMMU, IRQ, power or GPU-start authority.
    struct ProviderResourcesPreparation {
        bool optionPresent=false;uint32_t optionValue=0;
        bool requested=false,attempted=false,inputNodesPresent=false;
        IOReturn admissionRaw=kIOReturnNotReady;
        bool prepareReturned=false;uint32_t phase=0;
        bool registryLookupAttempted=false;
        bool registryLookupReturned[2]{},registryNodeFound[2]{};
        bool resourceCaptureAttempted=false;
        bool resourceCountReturned[2]{};uint32_t resourceCount[2]{};
        uint32_t retainedResourceMask=0;
        bool providerReused[2]{};
        bool nubAllocated[2]{};
        bool nubInitReturned[2]{},nubInitialized[2]{};
        bool nubAttachReturned[2]{},nubAttached[2]{};
        bool nubResourceReturned[2]{};
        IOReturn nubResourceStatus[2]={kIOReturnNotReady,kIOReturnNotReady};
    } providerResources;
    // Optional software-only IOService exclusion on the exact retained pair.
    // It is not an all-master quiescence proof or a hardware-access grant.
    struct ProviderClaimsPreparation {
        bool optionPresent=false;uint32_t optionValue=0;
        bool requested=false,attempted=false;
        IOReturn admissionRaw=kIOReturnNotReady;
        bool callReturned=false;IOReturn claimRaw=kIOReturnNotReady;
        bool claimsHeld=false;
    } providerClaims;
};
// Optional preparation-only entry after the actual expert is registered.
// No authority,hardware startup,foreign backing or successful provider is synthesized.
bool zorn26_gpu_board_platform_start(IOService *);
bool zorn26_gpu_board_platform_status(ZornGen7PlatformBoardStatus26 &);

// Raw-IOKit implementation is isolated from the root's shared-pointer view.
// The preparation-only mode accepts no imported GPU BOs;it is not a full
// physical-memory inventory or a hardware authority producer.
void ZornGen7PreparePlatformBoardStage26(IOService &,IORegistryEntry &,OSObject &,
    IORecursiveLock &,ZornGen7NativeBoardStage26 *&,IORegistryEntry *(&)[4],ZornGen7PlatformBoardStatus26 &);
bool ZornGen7PlatformBoardStageGpuProviderClaimsHeld26(ZornGen7NativeBoardStage26 &);

class ZornGen7StartupOwner26;struct ZornGen7StartupGpuInputs26;
enum class ZornGen7PlatformDirectStage26 : uint8_t { GpuPrefix,KernelImage,KernelIo,ConsoleImage };
// The actual code/storage owner owns every supplied immutable callback/cookie
// and nested input lifetime. The platform retains it before any scheduling
// attempt,including partial failure. No callbacks are defaulted or synthesized.
IOReturn zorn26_gpu_platform_schedule_direct(OSObject &actualInputCodeAndStorageOwner,
    const ZornGen7StartupGpuInputs26 &,ZornGen7PlatformDirectStage26);
IOReturn ZornGen7SchedulePlatformDirect26(IOService &,IORegistryEntry &,OSObject &,
    IORecursiveLock &,ZornGen7NativeBoardStage26 &,const ZornGen7StartupGpuInputs26 &,
    ZornGen7PlatformDirectStage26,ZornGen7StartupOwner26 *&actualPartialOutput);

// Authenticated bootstrap milestone. This shares the platform's one attempt
// and stops before client VM creation. The actual input owner is retained.
struct ZornGen7StartupAuthenticatedPrefixInputs26;
IOReturn zorn26_gpu_platform_schedule_authenticated_prefix(OSObject &actualInputCodeAndStorageOwner,
    const ZornGen7StartupAuthenticatedPrefixInputs26 &);
IOReturn ZornGen7SchedulePlatformAuthenticatedPrefix26(IOService &,IORegistryEntry &,OSObject &,
    IORecursiveLock &,ZornGen7NativeBoardStage26 &,const ZornGen7StartupAuthenticatedPrefixInputs26 &,
    ZornGen7StartupOwner26 *&actualPartialOutput);

struct ZornGen7StartupInputs26;
IOReturn ZornGen7SchedulePlatformCommandDb26(IOService &,IORegistryEntry &,OSObject &,IORecursiveLock &,
    ZornGen7NativeBoardStage26 &,const ZornGen7StartupInputs26 &,ZornGen7StartupOwner26 *&);
IOReturn zorn26_gpu_platform_schedule_commanddb(OSObject &,const ZornGen7StartupInputs26 &);

struct ZornGen7CommandDbWorkerObservation26;
IOReturn ZornGen7SchedulePlatformCommandDbObservation26(IOService &,IORegistryEntry &,OSObject &,IORecursiveLock &,
    ZornGen7NativeBoardStage26 &,const ZornGen7StartupInputs26 &,ZornGen7StartupOwner26 *&);
IOReturn zorn26_gpu_platform_schedule_commanddb_observation(OSObject &,const ZornGen7StartupInputs26 &);
bool ZornGen7CopyCompletedPlatformCommandDbObservation26(ZornGen7StartupOwner26 &,ZornGen7CommandDbWorkerObservation26 &);
bool zorn26_gpu_platform_copy_commanddb_observation(ZornGen7CommandDbWorkerObservation26 &);

// Internal stage-specific boot bridge. Actual root/prepared ownership only.
IOReturn ZornGen7SchedulePlatformCommandDbObservationOnly26(IOService &,IORegistryEntry &,OSObject &,
    IORecursiveLock &,ZornGen7NativeBoardStage26 &,ZornGen7StartupOwner26 *&);
// Submission result only;completed mapping/decoder outputs use the distinct
// terminal observation API. Absent selector leaves this entry unattempted.
bool zorn26_gpu_platform_commanddb_observation_submission(IOReturn &actualRaw);

bool ZornGen7CopyCompletedPlatformCommandDbStatus26(ZornGen7StartupOwner26 &,ZornGen7CommandDbStatus26 &);
bool zorn26_gpu_platform_commanddb_observation_status(ZornGen7CommandDbStatus26 &);

IOReturn ZornGen7SchedulePlatformCapturedCommandDb26(IOService &,IORegistryEntry &,OSObject &,
    IORecursiveLock &,ZornGen7NativeBoardStage26 &,ZornGen7StartupOwner26 *&);
bool ZornGen7CopyCompletedPlatformCapturedCommandDb26(ZornGen7StartupOwner26 &,ZornGen7CommandDbCapturedStatus26 &);
bool zorn26_gpu_platform_captured_commanddb_submission(IOReturn &);
bool zorn26_gpu_platform_captured_commanddb_status(ZornGen7CommandDbCapturedStatus26 &);

bool ZornGen7CopyCompletedPlatformRscControllerRead26(ZornGen7StartupOwner26 &,ZornGen7RscControllerStatus26 &,IOReturn &);
bool zorn26_gpu_platform_rsc_controller_read_status(ZornGen7RscControllerStatus26 &,IOReturn &actualCreationRaw);

bool ZornGen7CopyCompletedPlatformRscManaged26(ZornGen7StartupOwner26 &,ZornGen7RscManagedStatus26 &);
bool zorn26_gpu_platform_rsc_managed_status(ZornGen7RscManagedStatus26 &);
