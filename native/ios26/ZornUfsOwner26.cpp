extern "C" void zorn26_native_known_image_observation(unsigned (&)[32]);
extern "C" void zorn26_native_kernel_client_observation(unsigned (&)[40]);

extern "C" void zorn26_native_runtime_observation(unsigned (&)[24]);
extern "C" void zorn26_native_bootstrap_observation(unsigned (&)[16]);
extern "C" void zorn26_native_zap_context(unsigned (&)[12]);
extern "C" void zorn26_native_zap_observation(unsigned (&)[14]);
extern "C" void zorn26_native_cp_observation(unsigned (&)[8]);
#include "ZornUsbCdcProbe26.h"
#include <stdint.h>
#include <kern/processor.h>
#include <mach/machine.h>
#include <machine/machine_routines.h>
#include <mach/processor_info.h>
extern uint32_t processor_avail_count;
extern "C" kern_return_t processor_info(processor_t, processor_flavor_t, host_t *,
    processor_info_t, mach_msg_type_number_t *);
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornSBOut26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornSBReason26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornOSFiles26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornOSAnalytics26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornOrdinaryLog26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornReporterFiles26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornCorpseNotify26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornCrashDelivery26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/include/ZornCrashReport26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/include/ZornCrashMessageFormat26.h"
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornSBLifecycle26.h"
// SPDX-License-Identifier: BSD-2-Clause-Patent
#include "ZornUfsOwner26.h"
#include "ZornPresenterStartup26.h"
#include "ZornFramebufferProgress26.h"
#include "ZornTouchTrialSnapshot26.h"
#include "ZornGen7PlatformBoardStart26.h"
#include "ZornGen7RegistryStartup26.h"
extern "C" bool zorn26_gpu_platform_startup_result26(ZornGen7RegistryStartupResult26 &);
static_assert(__is_trivially_copyable(ZornGen7RegistryStartupResult26),"Completed result snapshot must remain a plain CPU copy");
#include "ZornHfsImage26.h"

OSDefineMetaClassAndStructors(ZornUfsOwner26, OSObject);
namespace {
// Source-local exclusion only. Never cleared: uncertain partial controller
// state and every created owner/context/resource stay retained permanently.
ZornUfsOwner26 *volatile preparationOwner = nullptr;
ZornUfsOwner26 *volatile rootLookupOwner = nullptr;
}

IOReturn ZornUfsOwner26::create(OSObject &actualPlatformOwner,
                               OSObject &actualTraceOwner,
                               ZornUfsCore26::Trace actualTrace,
                               ZornUfsOwner26 *&output) {
    if (output || !actualTrace) return kIOReturnBadArgument;
    auto *owner = new ZornUfsOwner26;
    if (!owner) return kIOReturnNoMemory;
    if (!owner->init()) { owner->release(); return kIOReturnError; }
    owner->retain(); // pin before any partially constructed state escapes
    actualPlatformOwner.retain();
    actualTraceOwner.retain();
    owner->platformOwner_ = &actualPlatformOwner;
    owner->traceOwner_ = &actualTraceOwner;
    owner->trace_ = actualTrace;
    output = owner;
    owner->status_.phase = Phase::Retained;
    owner->gate_ = IOLockAlloc();
    return owner->gate_ ? kIOReturnSuccess : kIOReturnNoMemory;
}

bool ZornUfsOwner26::stageRoot(int index, uint64_t start, uint64_t bytes) {
    if (!gate_) return false;
    IOLockLock(gate_);
    if (stagingAttempted_ || status_.preparationAttempted || status_.rootAttempted) {
        IOLockUnlock(gate_); return false;
    }
    stagingAttempted_ = true;
    if (!ZornHfsImage26::window(index, start, bytes)) {
        IOLockUnlock(gate_); return false;
    }
    stagedIndex_ = index;
    stagedStart_ = start;
    stagedBytes_ = bytes;
    // Publication borrows the same already self-pinned owner. No new object,
    // callback lifetime, cleanup, device claim or hardware-ready state.
    if (!__sync_bool_compare_and_swap(&rootLookupOwner,
                                      static_cast<ZornUfsOwner26 *>(nullptr), this)) {
        IOLockUnlock(gate_); return false;
    }
    stagingPublished_ = true;
    IOLockUnlock(gate_);
    return true;
}

extern "C" void zorn_ufs_root_attach26(int index) {
    auto *owner = __atomic_load_n(&rootLookupOwner, __ATOMIC_ACQUIRE);
    if (!owner) return;
    IOLockLock(owner->gate_);
    if (!owner->stagingPublished_ || index != owner->stagedIndex_) {
        IOLockUnlock(owner->gate_); return;
    }
    const uint64_t start = owner->stagedStart_, bytes = owner->stagedBytes_;
    IOLockUnlock(owner->gate_);
    const auto preparation = owner->prepare();
    if (preparation.phase != ZornUfsOwner26::Phase::Prepared) return;
    // Repeated IOFindBSDRoot calls cannot repeat initialization or binding.
    // Every real partial/failure stays in the original owner's status.
    (void)owner->bindRoot(index, start, bytes);
}

ZornUfsOwner26::Status ZornUfsOwner26::prepare() {
    if (!gate_ || !platformOwner_ || !traceOwner_ || !trace_)
        return readStatus();
    IOLockLock(gate_);
    if (status_.preparationAttempted) {
        const Status result = status_; IOLockUnlock(gate_); return result;
    }
    status_.preparationAttempted = true;
    if (!__sync_bool_compare_and_swap(&preparationOwner,
                                      static_cast<ZornUfsOwner26 *>(nullptr), this)) {
        status_.phase = Phase::ReservationRefused;
        const Status result = status_; IOLockUnlock(gate_); return result;
    }
    const auto &host = ZornUfsCore26::gHost;
    if (host.hcMap || host.smmuMap || host.hc || host.dma || host.virt ||
        host.phys || host.lock || host.ready || host.poisoned || host.smmu || host.cb) {
        status_.phase = Phase::ExistingTransport;
        const Status result = status_; IOLockUnlock(gate_); return result;
    }
    status_.phase = Phase::Preparing;
    IOLockUnlock(gate_);
    // Owner/status gate is released over the real initializer and trace.
    // All public mutating methods reject a second attempt or nonready phase.
    const char *reason = nullptr;
    ZornUfsCore26::PreparationObservation observation;
    const bool completed = ZornUfsCore26::hostBringUp(
        &reason, *traceOwner_, trace_, observation);
    IOLockLock(gate_);
    status_.initializerReturned = true;
    status_.initializerSucceeded = completed;
    status_.originalFailureReason = reason;
    status_.preparation = observation;
    status_.phase = completed ? Phase::Prepared : Phase::PreparationFailed;
    const Status result = status_;
    IOLockUnlock(gate_);
    return result;
}

ZornUfsOwner26::Status ZornUfsOwner26::bindRoot(int index,
                                            uint64_t start, uint64_t bytes) {
    if (!gate_) return readStatus();
    IOLockLock(gate_);
    if (status_.phase != Phase::Prepared || status_.rootAttempted) {
        const Status result = status_; IOLockUnlock(gate_); return result;
    }
    status_.rootAttempted = true;
    status_.phase = Phase::RootConstruction;
    IOLockUnlock(gate_);
    ZornHfsRoot26 *actualRoot = nullptr;
    const IOReturn created = ZornHfsRoot26::create(*this, actualRoot);
    IOLockLock(gate_);
    root_ = actualRoot; // preserve even actual partial construction on failure
    status_.rootCreateReturned = true;
    status_.rootCreateResult = created;
    if (created != kIOReturnSuccess) {
        status_.phase = Phase::RootConstructionFailed;
        const Status result = status_; IOLockUnlock(gate_); return result;
    }
    status_.phase = Phase::RootBinding;
    IOLockUnlock(gate_);
    const auto actual = actualRoot->bind(index, start, bytes);
    IOLockLock(gate_);
    status_.root = actual;
    status_.rootBindReturned = true;
    status_.phase = actual.registrationReturned &&
        actual.phase == ZornHfsRoot26::Phase::Registered
        ? Phase::RootRegistered : Phase::RootRefused;
    const Status result = status_;
    IOLockUnlock(gate_);
    return result;
}

ZornUfsOwner26::Status ZornUfsOwner26::readStatus() {
    if (!gate_) return status_;
    IOLockLock(gate_);
    const Status result = status_;
    IOLockUnlock(gate_);
    return result;
}

void ZornUfsOwner26::free() {
    // Only pre-init failure can reach here. Initialized owners self-pin before
    // retaining caller resources; no release/reset/unmap/rollback is supplied.
    OSObject::free();
}

#include "ZornPlatformRecordIo26.h"
#include "ZornPlatformRecordIdentity26.h"
#include "HoujiTerminal26.h"
#include <pexpert/pexpert.h>
#include <machine/machine_routines.h>
#include <kern/sched_prim.h>
// Called only by bsd_init after its actual vfs_mountroot returned zero.
// Existing owner/core and locks are reused;no new transport or callback owner.
extern "C" void zorn_ufs_root_mount_record26(int actualMountedDevice)
{
    int selected=0,root=0,header=0;
    if(!PE_parse_boot_argn("zorn26_root_mount_record",&selected,sizeof(selected)) || selected!=1)return;
    if(!PE_parse_boot_argn("zorn26_root",&root,sizeof(root)) || root!=1 ||
       (PE_parse_boot_argn("zorn26_root_record",&header,sizeof(header)) && header))return;
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled())return;
    auto *owner=__atomic_load_n(&rootLookupOwner,__ATOMIC_ACQUIRE);
    if(!owner)return;
    const auto actual=owner->readStatus();
    if(actual.phase!=ZornUfsOwner26::Phase::RootRegistered || !actual.rootBindReturned ||
       !actual.root.registrationReturned || actual.root.device==static_cast<dev_t>(-1) ||
       actual.root.device!=static_cast<dev_t>(actualMountedDevice))return;
    Hjt26Reason milestone={};
    hjt26_capture(&milestone,"K80 IOS26 actual vfs_mountroot returned zero; mounted rootdev matches registered UFS mdev; GPU not started",kZornPlatformRecordTrial);
    ZornUfsCore26::PlatformRecordObservation observation;
    const IOReturn raw=ZornUfsCore26::persistPlatformRecordOnce(milestone.record,observation);
    IOLog("K80 actual root-mount record: raw=%08x write-returned=%u readback-returned=%u matched=%u\n",raw,
        observation.writeReturned,observation.readbackReturned,observation.readbackMatched);
    if(raw!=kIOReturnSuccess)panic("K80 root-mount observation storage failed;resources retained;no retry");
}

// Actual PID1 load_init_program return only;not user-mode execution proof.
extern "C" void zorn_ufs_root_init_record26(int actualMountedDevice)
{
    int selected=0,root=0,header=0,mount=0;
    if(!PE_parse_boot_argn("zorn26_root_init_record",&selected,sizeof(selected)) || selected!=1)return;
    if(!PE_parse_boot_argn("zorn26_root",&root,sizeof(root)) || root!=1 ||
       (PE_parse_boot_argn("zorn26_root_record",&header,sizeof(header)) && header) ||
       (PE_parse_boot_argn("zorn26_root_mount_record",&mount,sizeof(mount)) && mount))return;
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled())return;
    auto *owner=__atomic_load_n(&rootLookupOwner,__ATOMIC_ACQUIRE);
    if(!owner)return;
    const auto actual=owner->readStatus();
    if(actual.phase!=ZornUfsOwner26::Phase::RootRegistered || !actual.rootBindReturned ||
       !actual.root.registrationReturned || actual.root.device==static_cast<dev_t>(-1) ||
       actual.root.device!=static_cast<dev_t>(actualMountedDevice))return;
    Hjt26Reason milestone={};
    hjt26_capture(&milestone,"K80 IOS26 PID1 image activation returned successfully; UFS rootdev matches registered mdev; user instructions and GPU not proven",kZornPlatformRecordTrial);
    ZornUfsCore26::PlatformRecordObservation observation;
    const IOReturn raw=ZornUfsCore26::persistPlatformRecordOnce(milestone.record,observation);
    IOLog("K80 actual PID1-image record: raw=%08x write-returned=%u readback-returned=%u matched=%u\n",raw,
        observation.writeReturned,observation.readbackReturned,observation.readbackMatched);
    if(raw!=kIOReturnSuccess)panic("K80 PID1-image observation storage failed;resources retained;no retry");
}

// Existing UFS one-page envelope, now sampled once after userland has had time
// to run. No I/O occurs in the syscall progress/event hooks themselves.
#include "ZornUserlandProgress26.h"
#include "ZornPresenterStartup26.h"
#include <kern/thread.h>
#include <kern/sched_prim.h>
#include "/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/cpu-posterboard-passive-cc9fbb3b86364db19e8f2ec90256040b/native/ZornThreadCensus26.h"
extern "C" void zorn26_display_thread_census(ZornThreadCensus26 *);
extern "C" uint32_t houji26_process_presence(const char *const *,unsigned);
extern "C" uint32_t zorn26_backboard_surface_starts(void);
extern "C" uint64_t zorn26_backboard_surface_first_create(void);
extern "C" uint64_t zorn26_backboard_surface_init(uint64_t *sizes);
extern "C" uint64_t zorn26_backboard_framebuffer_unsupported(void);
extern "C" uint32_t zorn26_software_accelerator_status(void);
static constexpr uint32_t zorn26_base64_size(uint32_t length)
{
    return 4 * ((length + 2) / 3);
}

// The caller provides zorn26_base64_size(length) bytes plus the terminator.
static void zorn26_base64_encode(char *output, const uint8_t *input, uint32_t length)
{
    static constexpr char alphabet[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    uint32_t offset = 0;
    for (; length - offset >= 3; offset += 3) {
        const uint32_t bits = (uint32_t(input[offset]) << 16)
            | (uint32_t(input[offset + 1]) << 8) | input[offset + 2];
        *output++ = alphabet[bits >> 18];
        *output++ = alphabet[(bits >> 12) & 63];
        *output++ = alphabet[(bits >> 6) & 63];
        *output++ = alphabet[bits & 63];
    }
    const uint32_t remaining = length - offset;
    if (remaining) {
        const uint32_t first = input[offset];
        const uint32_t second = remaining == 2 ? input[offset + 1] : 0;
        *output++ = alphabet[first >> 2];
        *output++ = alphabet[((first & 3) << 4) | (second >> 4)];
        *output++ = remaining == 2 ? alphabet[(second & 15) << 2] : '=';
        *output++ = '=';
    }
    *output = 0;
}

static void zorn_userland_progress_worker26(void *context,wait_result_t)
{
    auto *owner=static_cast<ZornUfsOwner26 *>(context);
    IOSleep(45000);
    const auto firstFramebuffer = zorn26_framebuffer_progress();
    ZornSBLifecycle26 firstSpringBoard{};
    zorn26_sb_snapshot(&firstSpringBoard);
    ZornSBLifecycle26 firstPosterBoard{};
    zorn26_pb_snapshot(&firstPosterBoard);
    ZornThreadCensus26 earlyPosterBoard{};
    zorn26_posterboard_thread_census(firstPosterBoard.pid, &earlyPosterBoard);
    IOSleep(105000);
    ZornUserlandProgress26 p{};
    const auto actual=owner->readStatus();
    if(actual.phase==ZornUfsOwner26::Phase::RootRegistered && zorn26_userland_progress_snapshot(&p)){
        const auto fb=zorn26_framebuffer_progress();
        ZornSBLifecycle26 sb{};zorn26_sb_snapshot(&sb);
        ZornSBLifecycle26 posterBoard{};
        zorn26_pb_snapshot(&posterBoard);
        ZornThreadCensus26 latePosterBoard{};
        zorn26_posterboard_thread_census(posterBoard.pid, &latePosterBoard);
        const uint32_t sourceMarkers=zorn26_pb_source_markers();
        ZornSBOut26 out{};zorn26_sbout_snapshot(&out);
        // Separate padding for each stream can add at most four encoded bytes.
        // The existing attempted-once gate gives this worker sole use of the scratch buffer.
        static char historyBuffer[zorn26_base64_size(ZornSBOutHistoryBytes26) + 4 + 2];
        const uint32_t stderrOffset = zorn26_sbout_history_offset(&out, 1);
        char *historyText[2] = {historyBuffer, historyBuffer + zorn26_base64_size(stderrOffset) + 1};
        char messageText[2][zorn26_base64_size(sizeof(out.channel[0].message)) + 1];
        for (unsigned channel = 0; channel < 2; ++channel) {
            const uint32_t offset = zorn26_sbout_history_offset(&out, channel);
            zorn26_base64_encode(historyText[channel], out.history + offset,
                                 zorn26_sbout_history_count(&out, channel));
            zorn26_base64_encode(messageText[channel], out.channel[channel].message,
                                 out.channel[channel].length);
        }
        // The existing atomic attempted-once scheduler admits only one worker.
        // Keep these fixed CPU diagnostic buffers out of its16KiB kernel stack.
        static char payload[ZornLogContextBytes26]{};
        const int payloadLength=snprintf(payload,sizeof(payload),"{\"routing\":[%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u],\"o\":[%u,%u,%u,%u,%u,%u,%u,%u,%u,%llu,%u,%u,%u,%u,%u,%u],\"e\":[%u,%u,%u,%u,%u,%u,%u,%u,%u,%llu,%u,%u,%u,%u,%u,%u],\"oh\":\"%s\",\"eh\":\"%s\",\"om\":\"%s\",\"em\":\"%s\",\"mo\":[%u,%u,%u,%u,%d,%u,%u,%d,%d,%lld,%d],\"me\":[%u,%u,%u,%u,%d,%u,%u,%d,%d,%lld,%d]}",
            out.reservations,out.reservationDrops,out.nativeErrors[0],out.nativeErrors[1],out.zeroReturns[0],out.zeroReturns[1],out.vectorSkips[0],out.vectorSkips[1],out.invalidAccept[0],out.invalidAccept[1],out.gaps[0],out.gaps[1],out.multiIov[0],out.multiIov[1],
            out.channel[0].probes,out.channel[0].writes,out.channel[0].copyErrors,out.channel[0].contention,out.channel[0].busy,out.channel[0].skipped,out.channel[0].priority,out.channel[0].truncated,out.channel[0].length,out.channel[0].nativeBytes,out.channel[0].historyLength,out.channel[0].historyTruncated,out.channel[0].redactions,out.channel[0].deniedLines,out.channel[0].partialLine,out.channel[0].overflowLines,
            out.channel[1].probes,out.channel[1].writes,out.channel[1].copyErrors,out.channel[1].contention,out.channel[1].busy,out.channel[1].skipped,out.channel[1].priority,out.channel[1].truncated,out.channel[1].length,out.channel[1].nativeBytes,out.channel[1].historyLength,out.channel[1].historyTruncated,out.channel[1].redactions,out.channel[1].deniedLines,out.channel[1].partialLine,out.channel[1].overflowLines,historyText[0],historyText[1],messageText[0],messageText[1],
            out.metadata[0].skip[0],out.metadata[0].skip[1],out.metadata[0].skip[2],out.metadata[0].skip[3],out.metadata[0].lastIov,out.metadata[0].firstState,out.metadata[0].firstReason,out.metadata[0].firstIov,out.metadata[0].firstType,out.metadata[0].firstAccepted,out.metadata[0].firstError,out.metadata[1].skip[0],out.metadata[1].skip[1],out.metadata[1].skip[2],out.metadata[1].skip[3],out.metadata[1].lastIov,out.metadata[1].firstState,out.metadata[1].firstReason,out.metadata[1].firstIov,out.metadata[1].firstType,out.metadata[1].firstAccepted,out.metadata[1].firstError);
        char text[512]{};
        const int prefixLength=snprintf(text,sizeof(text),"K80 posterwait150: u=%llu/%llu/%u/%d sb=%d/%u/%d/%u/%llx frame=%u/%llu/%llu/%03x early=%d/%u/%u/%llu/%llu/%03x pb=%u/%d/%u/%d/%u/%d/%u/%d/%u/%llx/%x wait=%u/%u/%u/%u/%u/%u/%u/%u/%llx,%u/%u/%u/%u/%u/%u/%u/%u/%llx payload=%d; actual PID1 EL0; GPU off",p.entries,p.returns,p.stock_main,p.error,sb.pid,sb.exitState,sb.exitStatus,sb.exitNamespace,sb.exitCode,fb.backboardSwapEnds,fb.queued,fb.pixelCopies,fb.firstFrameStages,
            firstSpringBoard.pid, firstSpringBoard.exitState, firstFramebuffer.backboardSwapEnds,
            firstFramebuffer.queued, firstFramebuffer.pixelCopies, firstFramebuffer.firstFrameStages,
            posterBoard.attempts, posterBoard.pid, posterBoard.activationState, posterBoard.activationResult,
            posterBoard.spawnState, posterBoard.spawnResult, posterBoard.exitState, posterBoard.exitStatus,
            posterBoard.exitNamespace, posterBoard.exitCode, sourceMarkers,
            earlyPosterBoard.present, earlyPosterBoard.active, earlyPosterBoard.total,
            earlyPosterBoard.sampled, earlyPosterBoard.runnable, earlyPosterBoard.waiting,
            earlyPosterBoard.portReceive, earlyPosterBoard.truncated, earlyPosterBoard.waitHints,
            latePosterBoard.present, latePosterBoard.active, latePosterBoard.total,
            latePosterBoard.sampled, latePosterBoard.runnable, latePosterBoard.waiting,
            latePosterBoard.portReceive, latePosterBoard.truncated, latePosterBoard.waitHints,
            payloadLength);
        static ZornLogContextRecord26 contextRecord{};
        if(payloadLength<=0||payloadLength>=(int)sizeof(payload)||prefixLength<=0||prefixLength>=(int)sizeof(text)||!zorn26_log_context_init(&contextRecord,kZornPlatformRecordTrial,(const uint8_t*)payload,(uint32_t)payloadLength)) {
            owner->release();(void)thread_terminate(current_thread());panic("K80 invalid standard output context returned");
        }
        Hjt26Reason milestone={};hjt26_capture(&milestone,text,kZornPlatformRecordTrial);
        ZornUfsCore26::PlatformRecordObservation observed;
        const auto raw=ZornUfsCore26::persistPlatformRecordWithContextOnce(milestone.record,contextRecord,observed);
        IOLog("K80 userland standard output snapshot raw=%08x write=%u read=%u matched=%u\n",raw,observed.writeReturned,observed.readbackReturned,observed.readbackMatched);
        // Observation failure is reported once; it does not kill PID1.
        // The existing UFS core retains/quarantines uncertain hardware state.
    }
    owner->release();
    (void)thread_terminate(current_thread());panic("K80 userland progress worker returned");
}
// The RSC path can retain the composition gate while a native call is in
// flight. This one-shot diagnostic therefore reads only the atomic CPU stage,
// from the same real root-owner worker context as the retained progress path.
static bool zorn_cpu_load_sample26(processor_t processor, processor_cpu_load_info_data_t &load)
{
    host_t host = HOST_NULL;
    mach_msg_type_number_t count = PROCESSOR_CPU_LOAD_INFO_COUNT;
    const auto result = processor_info(processor, PROCESSOR_CPU_LOAD_INFO, &host,
        reinterpret_cast<processor_info_t>(&load), &count);
    return result == KERN_SUCCESS && count == PROCESSOR_CPU_LOAD_INFO_COUNT;
}

// Copy the completed startup result after the existing GPU worker publishes it.
extern "C" uint64_t zorn26_gmu_context_irq_snapshot();
extern "C" unsigned zorn26_gmu_context_irq_readback();
extern "C" unsigned zorn26_gmu_stream_activation_snapshot();

static int zorn_gpu_checkpoint26(char *text, size_t capacity)
{
    unsigned enabled = 0;
    if (!PE_parse_boot_argn("zorn26_gpu_guarded_smmu_reserve", &enabled, sizeof(enabled)) ||
        enabled != 1) return 0;
    auto *result = static_cast<ZornGen7RegistryStartupResult26 *>(
        IOMallocZero(sizeof(ZornGen7RegistryStartupResult26)));
    if (!result) return snprintf(text, capacity, "; gpu=alloc");
    int length;
    if (zorn26_gpu_platform_startup_result26(*result)) {
        const auto &reservation = result->endpointReservation;
        length = snprintf(text, capacity, "; gpu=%u/%x,%u/%x,%u/%u/%u/%llx",
            unsigned(result->registerMappingsReturned), unsigned(result->registerMappingsReturn),
            unsigned(result->domainProbeReturned), unsigned(result->domainProbeReturn),
            unsigned(result->endpointReservationReturned), unsigned(reservation.disposition),
            unsigned(reservation.domain), static_cast<unsigned long long>(reservation.raw_status));
        if (length > 0 && size_t(length) < capacity) {
            const int context = snprintf(text + length, capacity - length, ",%u/%x,%u/%x/%u/%x,%u/%x,%u/%x/%u/%x",
                unsigned(result->contextViewsReturned), unsigned(result->contextViewsReturn),
                unsigned(result->gmuColdClocksReturned), unsigned(result->gmuColdClocksReturn),
                unsigned(result->nativeGmuClockResult.source_return_available),
                unsigned(result->nativeGmuClockResult.source_return),
                unsigned(result->gmuAhbReturned), unsigned(result->gmuAhbReturn),
                unsigned(result->cxTimerReturned), unsigned(result->cxTimerReturn),
                unsigned(result->nativeCxTimerResult.samples), unsigned(result->nativeCxTimerResult.assessment));
            if (context <= 0 || size_t(context) >= capacity - length) length = int(capacity);
            else length += context;
            if (size_t(length) < capacity) {
                const auto &irq = result->nativeGlobalSmmuIrq;
                const unsigned state = unsigned(result->nativeGlobalSmmuIrqReturned) |
                    (unsigned(irq.io_bound) << 1) | (unsigned(irq.cfg_after_returned) << 2) |
                    (unsigned(irq.registered_masked) << 3);
                const int written = snprintf(text + length, capacity - length, ",i=%x/%x/%u",
                    state, result->nativeGlobalSmmuIrqReturned ? unsigned(result->nativeGlobalSmmuIrqReturn) : 0u,
                    irq.registered_masked ? unsigned(irq.intid) : 0u);
                length = written < 0 ? int(capacity) : length + written;
            }
            if (size_t(length) < capacity) {
                const auto &control = result->nativeGlobalSmmuIrq.control;
                const unsigned state = unsigned(control.attempted) |
                    (unsigned(control.cr0_before_returned) << 1) |
                    (unsigned(control.active_controller) << 2) |
                    (unsigned(control.gfsr_returned) << 3) |
                    (unsigned(control.sync_write_returned) << 4) |
                    (unsigned(control.cr0_write_returned) << 5) |
                    (unsigned(control.cr0_readback_returned) << 6) |
                    (unsigned(control.arm_returned) << 7) |
                    (unsigned(control.complete) << 8);
                const int written = snprintf(text + length, capacity - length,
                    ",a=%x/%x/%x/%x/%u/%x", state, control.cr0_before,
                    control.cr0_readback, control.gfsr, control.sync_reads, control.sync_status);
                length = written < 0 ? int(capacity) : length + written;
            }
            if (size_t(length) < capacity) {
                const uint64_t context = zorn26_gmu_context_irq_snapshot() |
                    (uint64_t(zorn26_gmu_context_irq_readback()) << 32);
                const int written = snprintf(text + length, capacity - length, ",g=%llx,l=%x",
                    static_cast<unsigned long long>(context),zorn26_gmu_stream_activation_snapshot());
                length = written < 0 ? int(capacity) : length + written;
            }
            if (size_t(length) < capacity) {
                const unsigned returned = unsigned(result->rootPagesReturned) |
                    (unsigned(result->sparseArenasReturned) << 1) |
                    (unsigned(result->gmuImageReturned) << 2) |
                    (unsigned(result->gmuFirmwareSeedReturned) << 3) |
                    (unsigned(result->gmuFirmwareHoldsReturned) << 4);
                const int written = snprintf(text + length, capacity - length, ",t=%u/%x/%x/%x/%x/%x",
                    returned, result->rootPagesReturned ? unsigned(result->rootPagesReturn) : 0u,
                    result->sparseArenasReturned ? unsigned(result->sparseArenasReturn) : 0u,
                    result->gmuImageReturned ? unsigned(result->gmuImageReturn) : 0u,
                    result->gmuFirmwareSeedReturned ? unsigned(result->gmuFirmwareSeedReturn) : 0u,
                    result->gmuFirmwareHoldsReturned ? unsigned(result->gmuFirmwareHoldsReturn) : 0u);
                length = written < 0 ? int(capacity) : length + written;
            }

        }
    } else {
        length = snprintf(text, capacity, "; gpu=pending");
    }
    IOFree(result, sizeof(*result));
    return length;
}

extern "C" vm_offset_t ml_io_map(vm_offset_t physical, vm_size_t size);

#include "ZornPanicPacket236.h"
extern "C" int zorn26_cdc_dma_allocate(vm_offset_t *va, uint64_t *pa, unsigned bytes, unsigned bits)
{
    static IOBufferMemoryDescriptor *owner;
    if (owner || bytes != ZornCdcDmaBytes236 || bits < 36 || bits > 64) return 0;
    auto memory = IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,
        IOOptionBits(kIODirectionInOut) | IOOptionBits(kIOMemoryPhysicallyContiguous) |
        IOOptionBits(kIOMemoryMapperNone), bytes, 0x4000);
    if (!memory) return 0;
    IOByteCount contiguous = 0;
    const auto physical = memory->getPhysicalSegment(0, &contiguous, kIOMemoryMapperNone);
    auto *buffer = memory->getBytesNoCopy();
    if (!physical || (physical & 0x3fff) || contiguous < bytes || !buffer ||
        physical > UINT64_MAX - (bytes - 1) ||
        (bits < 64 && physical + bytes - 1 >= (uint64_t(1) << bits))) {
        return 0;
    }
    bzero(buffer, bytes);
    owner = memory.detach();
    *pa = physical;
    *va = reinterpret_cast<vm_offset_t>(buffer);
    return 1;
}

extern "C" unsigned zorn26_cdc_run(vm_offset_t, const char *, unsigned);
extern "C" void zorn26_cdc_status(unsigned *, unsigned *, unsigned *, unsigned *, uint32_t *, uint32_t *);

extern "C" uint64_t zorn26_native_gmu_irq_observed();
extern "C" uint32_t zorn26_native_gmu_armed();
extern "C" uint32_t zorn26_native_cm3_observation();
extern "C" uint32_t zorn26_native_pdc_rsc_observation();
extern "C" uint32_t zorn26_native_hfi_control_observation();
extern "C" void zorn26_native_hfi_query_observation(uint32_t (&)[5]);
extern "C" void zorn26_native_hfi_perf_observation(uint32_t (&)[5]);
extern "C" void zorn26_native_hfi_bw_observation(uint32_t (&)[5]);
extern "C" void zorn26_native_hfi_core_observation(uint32_t (&)[4]);
extern "C" void zorn26_native_hfi_dcvs_observation(uint32_t (&)[5]);
extern "C" uint32_t zorn26_native_gpu_tables_observation();
extern "C" uint32_t zorn26_native_qos_observation();
extern "C" bool zorn26_cx_scm_read_status(uint64_t *);

extern "C" uint32_t zorn26_host_mmu_preflight_observation();
extern "C" uint32_t zorn26_host_actlr_observation(unsigned);
extern "C" uint32_t zorn26_host_context_observation(unsigned);
extern "C" uint32_t zorn26_host_stream_observation();
extern "C" uint32_t zorn26_host_stream_trace(unsigned);
extern "C" void zorn26_native_gpu_oob_observation(uint32_t (&)[5]);
extern "C" void zorn26_native_gpu_start_observation(uint32_t (&)[5]);
extern "C" void zorn26_native_code_bind_observation(uint32_t (&)[4]);
extern "C" void zorn26_native_gx_registers_observation(uint32_t (&)[6]);
extern "C" void zorn26_native_gpu_irq_observation(uint32_t (&)[4]);
#include "ZornApplicationObservation26.h"
#include "ZornMapGate222.h"
extern "C" uint64_t zorn26_native_application_publication();
static __attribute__((unused)) void zorn_gpu_cdc_checkpoint26(const char *body, unsigned smr)
{
    unsigned enabled = 0;
    if (!PE_parse_boot_argn("zorn26_gpu_cdc", &enabled, sizeof(enabled)) || enabled != 1) return;
    const char *gpu = body;
    while (*gpu && strncmp(gpu, "; gpu=", 6)) ++gpu;
    if (!*gpu) return;
    ZornApplicationObservation26 application{};
    if(smr==88){
        // Publication is after150s. Observe at most10s for intermediate progress;
        // do not postpone CDC for100s when the client has not reachedphase11.
        // The independent300s watchdog and GPU/client operations are unchanged.
        for(unsigned i=0;i<40;++i){
            if(zorn26_application_snapshot(&application) && application.reportTerminal){
                IOSleep(2000);(void)zorn26_application_snapshot(&application);break;
            }
            IOSleep(250);
        }
        (void)zorn26_application_snapshot(&application);
    }
    char line[4096];
    int length = snprintf(line, sizeof(line), "K80 GPU CDC 9a697dec3b024930bd83b9161c05e99d %s,m=%u\r\n", gpu + 2, smr);
    if (length <= 0 || size_t(length) >= sizeof(line)) return;
    uint64_t scmStatus=0;
    if(zorn26_cx_scm_read_status(&scmStatus)){
        const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),",s=%016llx\r\n",
            static_cast<unsigned long long>(scmStatus));
        if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
        length+=appended-2;
    }
        struct Registers {
            vm_offset_t dwc = 0;
            vm_offset_t map(vm_offset_t address, vm_size_t size) {
                auto mapping = ml_io_map(address, size);
                if (address == 0x0a600000) dwc = mapping;
                return mapping;
            }
            uint32_t read(vm_offset_t address, unsigned offset) { return ml_io_read32(address + offset); }
        } regs;
        ZornUsbCdcProbe26::Snapshot state{};
        const auto result = ZornUsbCdcProbe26::inspect(regs, state);
    if (result == ZornUsbCdcProbe26::Result::IdentityRoute) {
        if(smr>=21){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",j=%016llx\r\n",static_cast<unsigned long long>(zorn26_native_gmu_irq_observed()));
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=31){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",q=%08x\r\n",zorn26_native_qos_observation());
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=33){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",a=%x\r\n",zorn26_native_gmu_armed());
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=37){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",c=%08x\r\n",zorn26_native_cm3_observation());
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=39){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",p=%08x\r\n",zorn26_native_pdc_rsc_observation());
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=41){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",h=%08x\r\n",zorn26_native_hfi_control_observation());
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=43){
            uint32_t query[5]{};
            zorn26_native_hfi_query_observation(query);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",e=%08x/%08x/%08x/%08x/%08x\r\n",
                query[0],query[1],query[2],query[3],query[4]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=45){
            uint32_t perf[5]{};
            zorn26_native_hfi_perf_observation(perf);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",f=%08x/%08x/%08x/%08x/%08x\r\n",
                perf[0],perf[1],perf[2],perf[3],perf[4]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=47){
            uint32_t bw[5]{};
            zorn26_native_hfi_bw_observation(bw);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",b=%08x/%08x/%08x/%08x/%08x\r\n",
                bw[0],bw[1],bw[2],bw[3],bw[4]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=49){
            uint32_t core[4]{};
            zorn26_native_hfi_core_observation(core);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",k=%08x/%08x/%08x/%08x\r\n",core[0],core[1],core[2],core[3]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=51){
            uint32_t dcvs[5]{};
            zorn26_native_hfi_dcvs_observation(dcvs);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",d=%08x/%08x/%08x/%08x/%08x\r\n",
                dcvs[0],dcvs[1],dcvs[2],dcvs[3],dcvs[4]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=53){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",v=%08x\r\n",zorn26_native_gpu_tables_observation());
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=55){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",w=%08x\r\n",zorn26_host_mmu_preflight_observation());
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=63){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",x=%08x/%08x,y=%08x/%08x,z=%08x,u=%08x/%08x\r\n",zorn26_host_actlr_observation(0),
                zorn26_host_actlr_observation(1),zorn26_host_context_observation(0),
                zorn26_host_context_observation(1),zorn26_host_stream_observation(),
                zorn26_host_stream_trace(0),zorn26_host_stream_trace(1));
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=65){
            uint32_t oob[5]{};
            zorn26_native_gpu_oob_observation(oob);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",o=%08x/%08x/%08x/%08x/%08x\r\n",oob[0],oob[1],oob[2],oob[3],oob[4]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=67){
            uint32_t start[5]{};
            zorn26_native_gpu_start_observation(start);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",t=%08x/%08x/%08x/%08x/%08x\r\n",start[0],start[1],start[2],start[3],start[4]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=69){
            uint32_t code[4]{};
            zorn26_native_code_bind_observation(code);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",n=%08x/%08x/%08x/%08x\r\n",code[0],code[1],code[2],code[3]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=71){
            uint32_t gx[6]{};zorn26_native_gx_registers_observation(gx);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",r=%08x/%08x/%08x/%08x/%08x/%08x\r\n",gx[0],gx[1],gx[2],gx[3],gx[4],gx[5]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=73){
            uint32_t irq[4]{};zorn26_native_gpu_irq_observation(irq);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",i=%08x/%08x/%08x/%08x\r\n",irq[0],irq[1],irq[2],irq[3]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=75){
            uint32_t cp[8]{};zorn26_native_cp_observation(cp);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",cp=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x\r\n",cp[0],cp[1],cp[2],cp[3],cp[4],cp[5],cp[6],cp[7]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=77){
            uint32_t zp[14]{};zorn26_native_zap_observation(zp);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",zp=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x\r\n",
                zp[0],zp[1],zp[2],zp[3],zp[4],zp[5],zp[6],zp[7],zp[8],zp[9],zp[10],zp[11],zp[12],zp[13]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=77){
            uint32_t sc[12]{};zorn26_native_zap_context(sc);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",sc=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x\r\n",
                sc[0],sc[1],sc[2],sc[3],sc[4],sc[5],sc[6],sc[7],sc[8],sc[9],sc[10],sc[11]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=79){
            uint32_t bf[16]{};zorn26_native_bootstrap_observation(bf);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",bf=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x\r\n",
                bf[0],bf[1],bf[2],bf[3],bf[4],bf[5],bf[6],bf[7],bf[8],bf[9],bf[10],bf[11],bf[12],bf[13],bf[14],bf[15]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=81){
            uint32_t rt[24]{};zorn26_native_runtime_observation(rt);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",rt=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x\r\n",
                rt[0],rt[1],rt[2],rt[3],rt[4],rt[5],rt[6],rt[7],rt[8],rt[9],rt[10],rt[11],rt[12],rt[13],rt[14],rt[15],rt[16],rt[17],rt[18],rt[19],rt[20],rt[21],rt[22],rt[23]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr>=83){
            uint32_t ki[32]{};zorn26_native_known_image_observation(ki);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",ki=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x\r\n",
                ki[0],ki[1],ki[2],ki[3],ki[4],ki[5],ki[6],ki[7],ki[8],ki[9],ki[10],ki[11],ki[12],ki[13],ki[14],ki[15],ki[16],ki[17],ki[18],ki[19],ki[20],ki[21],ki[22],ki[23],ki[24],ki[25],ki[26],ki[27],ki[28],ki[29],ki[30],ki[31]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr==85 || smr==86){
            uint32_t kc[40]{};zorn26_native_kernel_client_observation(kc);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",kc=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x\r\n",
                kc[0],kc[1],kc[2],kc[3],kc[4],kc[5],kc[6],kc[7],kc[8],kc[9],kc[10],kc[11],kc[12],kc[13],kc[14],kc[15],kc[16],kc[17],kc[18],kc[19],kc[20],kc[21],kc[22],kc[23],kc[24],kc[25],kc[26],kc[27],kc[28],kc[29],kc[30],kc[31],kc[32],kc[33],kc[34],kc[35],kc[36],kc[37],kc[38],kc[39]);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr==87 || smr==88){
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",ap=%016llx\r\n",static_cast<unsigned long long>(zorn26_native_application_publication()));
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
        }
        if(smr==88){
            char encoded[zorn26_base64_size(sizeof(application.text))+1]{};
            if(application.bytes>=sizeof(application.text))return;
            zorn26_base64_encode(encoded,reinterpret_cast<const uint8_t *>(application.text),application.bytes);
            const int appended=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",au=%016llx/%u/%x/%u/%u/%x/%u/%x/%u/%u/%u/%u/%u,at=%s\r\n",
                static_cast<unsigned long long>(application.unique),application.pid,application.flags,
                application.calls,application.method,application.raw,application.closeReturned,application.closeRaw,
                application.attempts,application.copyErrors,application.lines,application.bytes,application.dropped,encoded);
            if(appended<0 || size_t(appended)>=sizeof(line)-size_t(length-2))return;
            length+=appended-2;
            const int traced=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",ax=%u/%x/%x/%u/%u/%016llx\r\n",application.prepareStage,application.prepareRaw,
                application.prepareDetail,application.prepareEvents,application.prepareFailed,
                static_cast<unsigned long long>(application.prepareMask));
            if(traced<0 || size_t(traced)>=sizeof(line)-size_t(length-2))return;
            length+=traced-2;
            const int sessions=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",ms=%u/%u/%u\r\n",application.sessions,application.sessionRejected,application.reportTerminal);
            if(sessions<0 || size_t(sessions)>=sizeof(line)-size_t(length-2))return;
            length+=sessions-2;
            char rawEncoded[zorn26_base64_size(sizeof(application.rawText))+1]{};
            if(application.rawBytes>=sizeof(application.rawText))return;
            zorn26_base64_encode(rawEncoded,reinterpret_cast<const uint8_t *>(application.rawText),application.rawBytes);
            const int program=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                ",mp=%016llx/%u/%u/%u,mt=%s\r\n",static_cast<unsigned long long>(application.reportUnique),
                application.reportPid,application.rawBytes,application.rawDropped,rawEncoded);
            if(program<0 || size_t(program)>=sizeof(line)-size_t(length-2))return;
            length+=program-2;
            for(unsigned i=0;i<application.sessions && i<4;++i){
                const auto &h=application.history[i];
                const int entry=snprintf(line+length-2,sizeof(line)-size_t(length-2),
                    ",mh%u=%x/%u/%u/%x/%u/%x/%u/%x/%x/%u/%u/%016llx\r\n",
                    i,h.flags,h.calls,h.method,h.raw,h.closeReturned,h.closeRaw,h.prepareStage,h.prepareRaw,
                    h.prepareDetail,h.prepareEvents,h.prepareFailed,static_cast<unsigned long long>(h.prepareMask));
                if(entry<0 || size_t(entry)>=sizeof(line)-size_t(length-2))return;
                length+=entry-2;
            }
        }
        const unsigned tx = zorn26_cdc_run(regs.dwc, line, unsigned(length));
        IOLog("K80 GPU CDC result=%u\n", tx);
    }
}

extern "C" unsigned zorn26_gmu_validate_smr_after_checkpoint();

#include "ZornCdcStream201.h"
#include "ZornProgressFormat202.h"
#include "ZornProgressGate203.h"
extern "C" unsigned zorn26_cdc_stream201(vm_offset_t,ZornCdcNext201,void *);
struct ZornGpuProgress201 {
    ZornUfsOwner26 *owner;
    unsigned state,result,spawnRaw;
    thread_t worker;
    ZornProgressGate203 gate;
    unsigned emittedPoint; // Sole CDC-consumer ownership.
};
static ZornGpuProgress201 zornProgress201{};
#include "ZornTerminalContext231.h"
// Two bounded atomic source censuses only. This is not a global hardware or
// thread-quiescence snapshot;unknown/inconsistent observations remain unknown.
extern "C" unsigned zorn26_gpu_terminal_progress231(void){
    const auto census=[](){
        const unsigned state=__atomic_load_n(&zornProgress201.state,__ATOMIC_ACQUIRE);
        const unsigned requested=__atomic_load_n(&zornProgress201.gate.requested,__ATOMIC_ACQUIRE);
        const unsigned acknowledged=__atomic_load_n(&zornProgress201.gate.acknowledged,__ATOMIC_ACQUIRE);
        const unsigned result=state==3?__atomic_load_n(&zornProgress201.result,__ATOMIC_ACQUIRE):255u;
        return ZornTerminalProgress231{state,requested,acknowledged,result};
    };
    const auto first=census(),second=census();return zorn_terminal_progress_pack231(first,second);
}

// First eligible mapClientMemory64 after completed BoCpuMap13 only.
// The diagnostic call-kind257 is never sent to the native GPU dispatcher.
static unsigned zornCallbackClaimed222,zornCallbackActive222,zornCallbackToken222;
static uintptr_t zornCallbackClient222;
static thread_t zornCallbackThread222;
static ZornProgressGate203 zornCallbackGate222{};
static uint64_t zornCallbackResult222,zornCallbackViewState222,zornCallbackMapState222;
static unsigned zornCallbackEmitted222; // Sole USB consumer owns this field.
extern "C" int zorn26_gpu_map_gate222(uintptr_t client,unsigned token,unsigned point,uint32_t actualRaw,unsigned resultKnown,unsigned descriptorPresent,unsigned mapState){
 if(!token || token>4096 || point<1 || point>4 || resultKnown>1 || descriptorPresent>1 ||
    (point==1?resultKnown!=0:resultKnown!=1) || (!resultKnown && actualRaw) ||
    (point==1 && descriptorPresent) ||
    (point<3 ? mapState!=0 : point==3 ? (mapState!=1 && mapState!=3) : (mapState!=5 && mapState!=7 && mapState!=15)) ||
    ((mapState&2u) && (actualRaw || !descriptorPresent)))return 0;
 if(point==1){
  if(!zorn26_application_observes_map222(client))return 1;
  unsigned zero=0;
  if(__atomic_compare_exchange_n(&zornCallbackClaimed222,&zero,1,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)){
   zornCallbackClient222=client;zornCallbackThread222=current_thread();
   __atomic_store_n(&zornCallbackToken222,token,__ATOMIC_RELEASE);
   __atomic_store_n(&zornCallbackActive222,1u,__ATOMIC_RELEASE);
  }else {
   if(!__atomic_load_n(&zornCallbackActive222,__ATOMIC_ACQUIRE))return 1;
   if(zornCallbackClient222!=client || zornCallbackThread222!=current_thread() ||
      __atomic_load_n(&zornCallbackToken222,__ATOMIC_ACQUIRE)!=token)return 1;
   return 0;
  }
 }else if(!__atomic_load_n(&zornCallbackActive222,__ATOMIC_ACQUIRE) ||
          zornCallbackClient222!=client || zornCallbackThread222!=current_thread() ||
          __atomic_load_n(&zornCallbackToken222,__ATOMIC_ACQUIRE)!=token)return 1;
 if(__atomic_load_n(&zornCallbackGate222.requested,__ATOMIC_ACQUIRE)+1!=point ||
    __atomic_load_n(&zornCallbackGate222.acknowledged,__ATOMIC_ACQUIRE)+1!=point ||
    __atomic_load_n(&zornCallbackGate222.failed,__ATOMIC_ACQUIRE))return 0;
 __atomic_store_n(&zornCallbackResult222,resultKnown?((uint64_t(point)<<32)|actualRaw):0,__ATOMIC_RELEASE);
 __atomic_store_n(&zornCallbackViewState222,(uint64_t(point)<<32)|descriptorPresent,__ATOMIC_RELEASE);
 __atomic_store_n(&zornCallbackMapState222,(uint64_t(point)<<32)|mapState,__ATOMIC_RELEASE);
 if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled()){
  if(zorn_gate_begin203(zornCallbackGate222,point))__atomic_store_n(&zornCallbackGate222.failed,point,__ATOMIC_RELEASE);return 0;
 }
 uint64_t deadline=0;clock_interval_to_deadline(10,NSEC_PER_SEC,&deadline);
 const bool passed=zorn_gate_wait203(zornCallbackGate222,point,deadline,
  [](){return mach_absolute_time();},[](){IOSleep(10);});
 if(passed && point==4)__atomic_store_n(&zornCallbackActive222,0u,__ATOMIC_RELEASE);
 return passed?1:0;
}

extern "C" bool zorn26_gpu_diagnostic_gate203(unsigned point){
    auto &p=zornProgress201;
    if(!preemption_enabled() || ml_at_interrupt_context() ||
       __atomic_load_n(&p.worker,__ATOMIC_ACQUIRE)!=current_thread() ||
       __atomic_load_n(&p.state,__ATOMIC_ACQUIRE)!=2)return false;
    uint64_t deadline=0;clock_interval_to_deadline(10,NSEC_PER_SEC,&deadline);
    return zorn_gate_wait203(p.gate,point,deadline,
        [](){return mach_absolute_time();},[](){IOSleep(10);});
}

static void zorn_gpu_deferred_worker201(void *cookie,wait_result_t){
    auto *p=static_cast<ZornGpuProgress201 *>(cookie);
    __atomic_store_n(&p->worker,current_thread(),__ATOMIC_RELEASE);
    __atomic_store_n(&p->state,2,__ATOMIC_RELEASE);
    if(zorn26_gpu_diagnostic_gate203(1)){
        const unsigned actual=zorn26_gmu_validate_smr_after_checkpoint();
        __atomic_store_n(&p->result,actual,__ATOMIC_RELAXED);
        __atomic_store_n(&p->state,3,__ATOMIC_RELEASE);
    }else __atomic_store_n(&p->state,5,__ATOMIC_RELEASE); // Explicit diagnostic abort; GPU not called.
    __atomic_store_n(&p->worker,THREAD_NULL,__ATOMIC_RELEASE);
    p->owner->release();
    (void)thread_terminate(current_thread());panic("K80 GPU progress worker returned");
}
static unsigned zorn_gpu_progress_next201(void *cookie,char *line,unsigned cap,unsigned completedFrames){
    auto *p=static_cast<ZornGpuProgress201 *>(cookie);
    // Callback receives only actual complete transfers. Never acknowledge a
    // newly sampled point until the frame carrying it has itself completed.
    if(completedFrames){
        (void)zorn_gate_ack203(p->gate,p->emittedPoint);
        (void)zorn_gate_ack203(zornCallbackGate222,zornCallbackEmitted222);
    }
    // Three actual pre-GPU frames prove repeated transport, including >3s idle.
    // The diagnostic gate supplies no native hardware/client authority.
    if(completedFrames>=3 && __atomic_load_n(&p->state,__ATOMIC_ACQUIRE)==0){
        __atomic_store_n(&p->state,1,__ATOMIC_RELEASE);p->owner->retain();
        thread_t worker=THREAD_NULL;
        const auto kr=kernel_thread_start(zorn_gpu_deferred_worker201,p,&worker);
        __atomic_store_n(&p->spawnRaw,unsigned(kr),__ATOMIC_RELEASE);
        if(kr==KERN_SUCCESS && worker!=THREAD_NULL)thread_deallocate(worker);
        else if(kr!=KERN_SUCCESS){p->owner->release();__atomic_store_n(&p->state,4,__ATOMIC_RELEASE);}
        // Success without a handle is unexpected: retain, never restart/release.
    }
    ZornApplicationObservation26 observation{};
    const unsigned got=zorn26_application_snapshot(&observation)?1u:0u;
    const unsigned state=__atomic_load_n(&p->state,__ATOMIC_ACQUIRE);
    const unsigned result=state==3?__atomic_load_n(&p->result,__ATOMIC_RELAXED):0;
    const unsigned point=__atomic_load_n(&p->gate.requested,__ATOMIC_ACQUIRE);
    const unsigned ack=__atomic_load_n(&p->gate.acknowledged,__ATOMIC_ACQUIRE);
    const unsigned failed=__atomic_load_n(&p->gate.failed,__ATOMIC_ACQUIRE);
    const unsigned callbackPoint=__atomic_load_n(&zornCallbackGate222.requested,__ATOMIC_ACQUIRE);
    const unsigned size=zorn_progress_format202(line,cap,"9a697dec3b024930bd83b9161c05e99d",completedFrames,state,result,
        __atomic_load_n(&p->spawnRaw,__ATOMIC_ACQUIRE),got,zorn26_native_application_publication(),observation,
        point,ack,failed,
        callbackPoint,
        __atomic_load_n(&zornCallbackGate222.acknowledged,__ATOMIC_ACQUIRE),
        __atomic_load_n(&zornCallbackGate222.failed,__ATOMIC_ACQUIRE),
        __atomic_load_n(&zornCallbackResult222,__ATOMIC_ACQUIRE),
        callbackPoint?257u:0u,
        callbackPoint?__atomic_load_n(&zornCallbackToken222,__ATOMIC_ACQUIRE):0u,
        __atomic_load_n(&zornCallbackViewState222,__ATOMIC_ACQUIRE),
        __atomic_load_n(&zornCallbackMapState222,__ATOMIC_ACQUIRE));
    if(size){p->emittedPoint=point;zornCallbackEmitted222=callbackPoint;}
    return size;
}
static void zorn_gpu_progress_cdc201(ZornUfsOwner26 *owner){
    unsigned enabled=0;
    if(!PE_parse_boot_argn("zorn26_gpu_cdc",&enabled,sizeof(enabled)) || enabled!=1)return;
    struct Registers {
        vm_offset_t dwc=0;
        vm_offset_t map(vm_offset_t address,vm_size_t size){
            const auto p=ml_io_map(address,size);if(address==0x0a600000)dwc=p;return p;
        }
        uint32_t read(vm_offset_t address,unsigned offset){return ml_io_read32(address+offset);}
    } regs;
    ZornUsbCdcProbe26::Snapshot snapshot{};
    if(ZornUsbCdcProbe26::inspect(regs,snapshot)!=ZornUsbCdcProbe26::Result::IdentityRoute)return;
    zornProgress201.owner=owner;
    const unsigned result=zorn26_cdc_stream201(regs.dwc,zorn_gpu_progress_next201,&zornProgress201);
    IOLog("K80 GPU progress CDC result=%u\n",result);
}


static void zorn_touch_checkpoint_worker26(void *context,wait_result_t)
{
    auto *owner=static_cast<ZornUfsOwner26 *>(context);
    constexpr unsigned kK80CPUCount = 8;
    processor_cpu_load_info_data_t first[kK80CPUCount]{};
    processor_t processors[kK80CPUCount]{};
    IOSleep(25000);
    const int maxCPU = ml_get_max_cpu_number();
    for (unsigned cpu = 0; cpu < kK80CPUCount && int(cpu) <= maxCPU; ++cpu) {
        const auto processor = cpu_to_processor(int(cpu));
        if (processor && zorn_cpu_load_sample26(processor, first[cpu])) processors[cpu] = processor;
    }

    IOSleep(20000);
    unsigned valid = 0;
    natural_t user[kK80CPUCount]{};
    natural_t system[kK80CPUCount]{};
    for (unsigned cpu = 0; cpu < kK80CPUCount; ++cpu) {
        const auto processor = processors[cpu];
        if (!processor || processor != cpu_to_processor(int(cpu))) continue;
        processor_cpu_load_info_data_t last{};
        if (!zorn_cpu_load_sample26(processor, last)) continue;
        if (last.cpu_ticks[CPU_STATE_USER] < first[cpu].cpu_ticks[CPU_STATE_USER] ||
            last.cpu_ticks[CPU_STATE_SYSTEM] < first[cpu].cpu_ticks[CPU_STATE_SYSTEM]) continue;
        valid |= 1u << cpu;
        user[cpu] = last.cpu_ticks[CPU_STATE_USER] - first[cpu].cpu_ticks[CPU_STATE_USER];
        system[cpu] = last.cpu_ticks[CPU_STATE_SYSTEM] - first[cpu].cpu_ticks[CPU_STATE_SYSTEM];
    }
    unsigned checkpoint45=0,cdc=0;
    // Dedicated GPU-only validation schedule. Original25s/45s CPU samples,
    // RootRegistered check,full persisted checkpoint and pre-GPU CDC gates stay.
    // The default retains the150s touch/UI observation schedule.
    const bool earlyGpu=PE_parse_boot_argn("-g45",&checkpoint45,sizeof(checkpoint45)) && checkpoint45==1 &&
        PE_parse_boot_argn("zorn26_gpu_cdc",&cdc,sizeof(cdc)) && cdc==1;
    if(!earlyGpu)IOSleep(105000);
    if(owner->readStatus().phase==ZornUfsOwner26::Phase::RootRegistered){
        const auto fb=zorn26_framebuffer_progress();
        ZornSBLifecycle26 sb{};
        zorn26_sb_snapshot(&sb);
        const auto count=[](uint64_t value) -> unsigned {
            return value>255 ? 255 : unsigned(value);
        };
        const unsigned ui=(unsigned(sb.pid>0)<<23) | (unsigned(sb.exitState!=0)<<22) |
            (unsigned(earlyGpu)<<16) | (count(fb.backboardSwapEnds)<<8) | count(fb.pixelCopies);
        Hjt26Reason milestone={};
        char text[sizeof(milestone.record.text)]{};
        const unsigned online = __atomic_load_n(&processor_avail_count, __ATOMIC_RELAXED);
        const int prefix = snprintf(text, sizeof(text),
            "cpu_online=%u; cpumask=%02x; ticks=%08x/%08x,%08x/%08x,%08x/%08x,%08x/%08x,"
            "%08x/%08x,%08x/%08x,%08x/%08x,%08x/%08x; ",
            online, valid, user[0], system[0], user[1], system[1], user[2], system[2], user[3], system[3],
            user[4], system[4], user[5], system[5], user[6], system[6], user[7], system[7]);
        int length = -1;
        if (prefix > 0 && size_t(prefix) < sizeof(text)) {
            int body = ZornTouchFormatTrialSnapshot26(text + prefix, sizeof(text) - prefix);
            if (body > 0 && size_t(body) < sizeof(text) - prefix) {
                constexpr char label[] = "K80 FT3683: ";
                if (!strncmp(text + prefix, label, sizeof(label) - 1)) {
                    body -= sizeof(label) - 1;
                    memmove(text + prefix, text + prefix + sizeof(label) - 1, body + 1);
                }
                length = prefix + body;
                const int extra=snprintf(text+length,sizeof(text)-size_t(length),"; u=%06x",ui);
                if(extra!=10 || size_t(extra)>=sizeof(text)-size_t(length)){
                    owner->release();
                    (void)thread_terminate(current_thread());
                    panic("K80 invalid UI census size");
                }
                length+=extra;
                const int gpu = zorn_gpu_checkpoint26(text + length, sizeof(text) - length);
                if (gpu >= 0 && size_t(gpu) < sizeof(text) - length) length += gpu;
                else text[length] = '\0';
            }
        }
        if(length>0 && size_t(length)<sizeof(text)){
            hjt26_capture(&milestone,text,kZornPlatformRecordTrial);
            ZornUfsCore26::PlatformRecordObservation observed;
            const auto raw=ZornUfsCore26::persistPlatformRecordOnce(milestone.record,observed);
            IOLog("K80 FT3683 snapshot raw=%08x write=%u read=%u matched=%u\n",raw,
                observed.writeReturned,observed.readbackReturned,observed.readbackMatched);
            if (raw == kIOReturnSuccess && observed.readbackMatched) {
                zorn_gpu_progress_cdc201(owner);
            }
        }
    }
    owner->release();
    (void)thread_terminate(current_thread());panic("K80 FT3683 checkpoint worker returned");
}
extern "C" unsigned zorn26_rsc_stage_snapshot(void);
static void zorn_rsc_checkpoint_worker26(void *context,wait_result_t)
{
    auto *owner=static_cast<ZornUfsOwner26 *>(context);
    IOSleep(25000);
    const auto actual=owner->readStatus();
    if(actual.phase==ZornUfsOwner26::Phase::RootRegistered){
        const unsigned word=zorn26_rsc_stage_snapshot();
        char text[160]{};
        snprintf(text,sizeof(text),"K80 RSC checkpoint25: word=%x; zero=unreached else stage=word-1; actual PID1 EL0; enable clocks GMU GPU off",word);
        Hjt26Reason milestone={};hjt26_capture(&milestone,text,kZornPlatformRecordTrial);
        ZornUfsCore26::PlatformRecordObservation observed;
        const auto raw=ZornUfsCore26::persistPlatformRecordOnce(milestone.record,observed);
        IOLog("K80 RSC checkpoint snapshot raw=%08x write=%u read=%u matched=%u\n",raw,observed.writeReturned,observed.readbackReturned,observed.readbackMatched);
    }
    owner->release();
    (void)thread_terminate(current_thread());panic("K80 RSC checkpoint worker returned");
}
// Actual PID1 EL0 BSD-system-call entry;no syscall result or user arguments logged.
extern "C" uint32_t ZornBootPresenterRefusal26(void);
extern "C" IOReturn ZornBootPresenterPatternResult26(uint32_t *,uint64_t *);
extern "C" void zorn_ufs_root_EL0_record26(int actualMountedDevice)
{
    static uint32_t attempted=0;
    if(__atomic_load_n(&attempted,__ATOMIC_ACQUIRE))return;
    int selected=0,root=0,header=0,mount=0,image=0;
    int presenter=0,cpu=0;
    const bool wantProgress=zorn26_userland_progress_enabled();
    unsigned checkpoint=0;
    const bool wantRscCheckpoint=PE_parse_boot_argn("zorn26_rsc_checkpoint_record",&checkpoint,sizeof(checkpoint)) && checkpoint==1;
    const bool wantEL0=PE_parse_boot_argn("zorn26_root_EL0_record",&selected,sizeof(selected)) && selected==1;
    const bool wantPresenter=PE_parse_boot_argn("zorn26_presenter_record",&presenter,sizeof(presenter)) && presenter==1;
    unsigned board=0;
    const bool wantBoard=PE_parse_boot_argn("zorn26_gpu_board_record",&board,sizeof(board)) && board==1;
    unsigned touch=0;
    const bool wantTouch=PE_parse_boot_argn("zorn26_touch_record",&touch,sizeof(touch)) && touch==1;
    if(unsigned(wantEL0)+unsigned(wantPresenter)+unsigned(wantBoard)+unsigned(wantProgress)+unsigned(wantTouch)!=1)return;
    if(wantTouch){
        unsigned selected=0,installed=0;
        if(!PE_parse_boot_argn("zorn26_touch",&selected,sizeof(selected)) || selected!=1 ||
           !PE_parse_boot_argn("zorn26_installed_root_trial",&installed,sizeof(installed)) || installed!=1)return;
    }
    if(wantRscCheckpoint && !wantBoard)return;
    if(wantPresenter && (!PE_parse_boot_argn("zorn26_cpu_presenter",&cpu,sizeof(cpu)) || cpu!=1))return;
    if(!PE_parse_boot_argn("zorn26_root",&root,sizeof(root)) || root!=1 ||
       (PE_parse_boot_argn("zorn26_root_record",&header,sizeof(header)) && header) ||
       (PE_parse_boot_argn("zorn26_root_mount_record",&mount,sizeof(mount)) && mount) ||
       (PE_parse_boot_argn("zorn26_root_init_record",&image,sizeof(image)) && image))return;
    if(!preemption_enabled() || ml_at_interrupt_context() || !ml_get_interrupts_enabled())return;
    auto *owner=__atomic_load_n(&rootLookupOwner,__ATOMIC_ACQUIRE);
    if(!owner)return;
    const auto actual=owner->readStatus();
    if(actual.phase!=ZornUfsOwner26::Phase::RootRegistered || !actual.rootBindReturned ||
       !actual.root.registrationReturned || actual.root.device==static_cast<dev_t>(-1) ||
       actual.root.device!=static_cast<dev_t>(actualMountedDevice))return;
    if(wantTouch){
        uint32_t empty=0;
        if(!__atomic_compare_exchange_n(&attempted,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
        owner->retain();thread_t worker=THREAD_NULL;
        const auto raw=kernel_thread_start(zorn_touch_checkpoint_worker26,owner,&worker);
        if(raw==KERN_SUCCESS && worker!=THREAD_NULL){thread_deallocate(worker);return;}
        // Keep the reference if scheduling returned success without a handle.
        if(raw!=KERN_SUCCESS)owner->release();
        IOLog("K80 FT3683 checkpoint worker scheduling: raw=%d handle=%u\n",raw,worker!=THREAD_NULL);
        return;
    }
    if(wantRscCheckpoint){
        uint32_t empty=0;
        if(!__atomic_compare_exchange_n(&attempted,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
        owner->retain();thread_t worker=THREAD_NULL;
        const auto raw=kernel_thread_start(zorn_rsc_checkpoint_worker26,owner,&worker);
        if(raw==KERN_SUCCESS){thread_deallocate(worker);return;}
        owner->release();IOLog("K80 RSC checkpoint worker scheduling failed: %d\n",raw);return;
    }
    if(wantProgress){
        uint32_t empty=0;
        if(!__atomic_compare_exchange_n(&attempted,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
        owner->retain();thread_t worker=THREAD_NULL;
        const auto raw=kernel_thread_start(zorn_userland_progress_worker26,owner,&worker);
        if(raw==KERN_SUCCESS){thread_deallocate(worker);return;}
        owner->release();IOLog("K80 userland progress worker scheduling failed: %d\n",raw);return;
    }
    ZornPresenterStartupSnapshot26 presenterResult;
    if(wantPresenter){
        if(!zorn26_cpu_presenter_snapshot26(presenterResult))return;
        if(presenterResult.scheduleRaw==kIOReturnSuccess &&
           (!presenterResult.statusReturned || !presenterResult.status.creationReturned))return;
    }
    ZornGen7PlatformBoardStatus26 boardResult;
    if(wantBoard){
        unsigned boardSelected=0;
        if(!PE_parse_boot_argn("zorn26_gpu_board_stage",&boardSelected,sizeof(boardSelected)) || boardSelected!=1 ||
           !zorn26_gpu_board_platform_status(boardResult))return;
    }
    unsigned sourceRead=0;
    const bool wantCommandDb=wantBoard && PE_parse_boot_argn("zorn26_commanddb_source_read",&sourceRead,sizeof(sourceRead)) && sourceRead==1;
    IOReturn commandDbSubmission=kIOReturnNotReady;ZornGen7CommandDbStatus26 commandDbResult;
    if(wantCommandDb){
        if(!zorn26_gpu_platform_commanddb_observation_submission(commandDbSubmission))return;
        if(commandDbSubmission==kIOReturnSuccess && !zorn26_gpu_platform_commanddb_observation_status(commandDbResult))return;
    }
    unsigned resources=0,resourcesOnly=0,rscRead=0,managed=0;
    const bool wantManaged=wantBoard && PE_parse_boot_argn("zorn26_rsc_managed",&managed,sizeof(managed)) && managed==1;
    const bool wantRsc=wantBoard &&
        PE_parse_boot_argn("zorn26_commanddb_resources",&resources,sizeof(resources)) && resources==1 &&
        PE_parse_boot_argn("zorn26_commanddb_resources_only",&resourcesOnly,sizeof(resourcesOnly)) && resourcesOnly==1 &&
        PE_parse_boot_argn("zorn26_rsc_layout_read",&rscRead,sizeof(rscRead)) && rscRead==1;
    if(wantRsc && wantCommandDb)return;
    bool resourceSubmissionReturned=false,rscReturned=false;IOReturn resourceSubmission=kIOReturnNotReady,rscRaw=kIOReturnNotReady;
    ZornGen7CommandDbCapturedStatus26 captured;ZornGen7RscControllerStatus26 rsc;
    if(wantRsc && boardResult.setupRaw==kIOReturnSuccess && boardResult.preparationReturned &&
       boardResult.preparationRaw==kIOReturnSuccess && boardResult.stage.phase==ZornGen7BoardPreparedPhase26){
        resourceSubmissionReturned=zorn26_gpu_platform_captured_commanddb_submission(resourceSubmission);
        if(!resourceSubmissionReturned)return;
        if(resourceSubmission==kIOReturnSuccess){
            if(!zorn26_gpu_platform_captured_commanddb_status(captured))return;
            if(captured.bindingReturned && captured.bindingRaw==kIOReturnSuccess){
                rscReturned=zorn26_gpu_platform_rsc_controller_read_status(rsc,rscRaw);
                if(!rscReturned)return;
            }
        }
    }
    uint32_t empty=0;
    if(!__atomic_compare_exchange_n(&attempted,&empty,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
    Hjt26Reason milestone={};
    if(wantManaged){
        ZornGen7RscManagedStatus26 actual;const bool copied=zorn26_gpu_platform_rsc_managed_status(actual);
        // Keep the actual completed aggregate off
        // the syscall stack;free only this plain CPU copy,never native owners.
        auto *snapshot=static_cast<ZornGen7RegistryStartupResult26 *>(IOMallocZero(sizeof(ZornGen7RegistryStartupResult26)));
        const bool details=snapshot && zorn26_gpu_platform_startup_result26(*snapshot);
        char text[512]{};
        if(details){
            const auto &o=*snapshot;
            snprintf(text,sizeof(text),"K80 domain: copied=1 gpucc=%u/%u graph=%u/%u/%u/%u/%u/%u list=%u/%u/%u/%d/%d hub=%u/%x ddr=%u/%x core=%u/%x cx=%u/%u/%u/%u/%u cc=%u/%x completion=%u/%u smmu=%u/%x maps=%u/%x cxon=%u/%u/%u/%d/%u/%u/%u/%llx power=%u/%u/%u/%u/%llx pm=%u/%x pstep=%u/%u bulk=%u/%u/%u/%d/%d probe=%u/%x/%u/%u/%x/%x/%x/%u/%u/%u/%u/%u/%u/%u gclk=%u/%x/%u/%u/%d/%u/%u/%u/%u/%u/%d/%u/%d/%u/%u/%u/%d/%d ahb=%u/%x timer=%u/%x/%u/%x/%u/%x/%u/%u/%u/%u girqm=%u/%x/%u/%u/%d/%u/%u/%u gobs=%x/%x/%x/%x/%u/%llx/%llx/%u/%u/%u acr=%u/%x/%x; PID1 EL0; GMU GPU off",
                o.gpuccPrefixReturned,o.gpuccPrefix.source_prefix_complete,
                o.clockGraphReturned,unsigned(o.clockGraph.assessment),o.clockGraph.hardware_constructed,o.clockGraph.namespace_records,o.clockGraph.cores_registered,o.clockGraph.cpu_graph_complete,
                o.clockListReturned,unsigned(o.clockList.assessment),o.clockList.source_return_available,o.clockList.source_return,o.clockList.entries_returned,
                o.hubMetadataReturned,unsigned(o.hubMetadataReturn),o.ddrMetadataReturned,unsigned(o.ddrMetadataReturn),o.coreInputsReturned,unsigned(o.coreInputsReturn),
                o.cxGdscProbeReturned,o.cxGdscProbe.attempted,o.cxGdscProbe.configuration_store_returned,o.cxGdscProbe.retain_update_returned,o.cxGdscProbe.native_prefix_returned,
                o.cxGdscCoreReturned,unsigned(o.cxGdscCoreReturn),o.cxCompletionReturned,o.cxCompletion.registered,o.smmuPowerReturned,unsigned(o.smmuPowerReturn),o.registerMappingsReturned,unsigned(o.registerMappingsReturn),
                o.probePrimaryReturned,unsigned(o.probePrimary.wait.assessment),o.probePrimary.wait.native_return_available,o.probePrimary.wait.native_return,
                unsigned(o.probePrimary.regulator.disposition),unsigned(o.probePrimary.regulator.domain),o.probePrimary.regulator.raw_status_available,static_cast<unsigned long long>(o.probePrimary.regulator.raw_status),
                o.nativeSmmuPowerReturned,unsigned(o.nativeSmmuPower.disposition),unsigned(o.nativeSmmuPower.domain),o.nativeSmmuPower.raw_status_available,static_cast<unsigned long long>(o.nativeSmmuPower.raw_status),o.smmuPmReturned,unsigned(o.smmuPmReturn),o.nativeSmmuPowerProgress.caller_phase,o.nativeSmmuPowerProgress.source_phase,
                o.nativeSmmuPowerProgress.bulk_assessment,o.nativeSmmuPowerProgress.prepare_assessment,o.nativeSmmuPowerProgress.enable_assessment,
                o.nativeSmmuPowerProgress.prepare_entries,o.nativeSmmuPowerProgress.enable_entries,
                o.domainProbeReturned,unsigned(o.domainProbeReturn),o.nativeSmmuProbe.ioBound,o.nativeSmmuProbe.identificationReads,
                o.nativeSmmuProbe.id0,o.nativeSmmuProbe.id1,o.nativeSmmuProbe.id2,o.nativeSmmuProbe.capabilitiesReady,
                o.nativeSmmuProbe.banks,o.nativeSmmuProbe.s2banks,o.nativeSmmuProbe.inputBits,o.nativeSmmuProbe.outputBits,o.nativeSmmuProbe.physicalBits,o.nativeSmmuProbe.registerShift,
                o.gmuColdClocksReturned,unsigned(o.gmuColdClocksReturn),unsigned(o.nativeGmuClockResult.assessment),o.nativeGmuClockResult.source_return_available,o.nativeGmuClockResult.source_return,o.nativeGmuClockResult.state_published,
                unsigned(o.nativeGmuClockResult.rdpm_assessment),o.nativeGmuClockResult.frequency_available,o.nativeGmuClockResult.frequency_hz,
                o.nativeGmuClockResult.gmu_return_available,o.nativeGmuClockResult.gmu_return,o.nativeGmuClockResult.hub_return_available,o.nativeGmuClockResult.hub_return,
                unsigned(o.nativeGmuClockResult.bulk_assessment),unsigned(o.nativeGmuClockResult.prepare_assessment),unsigned(o.nativeGmuClockResult.enable_assessment),o.nativeGmuClockResult.prepare_entries,o.nativeGmuClockResult.enable_entries,
                o.gmuAhbReturned,unsigned(o.gmuAhbReturn),o.cxTimerReturned,unsigned(o.cxTimerReturn),
                o.nativeCxTimerResult.reset_read_returned,o.nativeCxTimerResult.reset,o.nativeCxTimerResult.gx_read_returned,o.nativeCxTimerResult.gx,
                o.nativeCxTimerResult.operation_returned,o.nativeCxTimerResult.assessment,o.nativeCxTimerResult.samples,o.nativeCxTimerResult.seed_available,
                o.nativeGlobalSmmuIrqReturned,unsigned(o.nativeGlobalSmmuIrqReturn),o.nativeGlobalSmmuIrq.io_bound,o.nativeGlobalSmmuIrq.attach_returned,
                o.nativeGlobalSmmuIrq.attach_raw,o.nativeGlobalSmmuIrq.intid,o.nativeGlobalSmmuIrq.source,o.nativeGlobalSmmuIrq.registered_masked,
                o.nativeGlobalSmmuIrq.gic.readMask,o.nativeGlobalSmmuIrq.gic.control,o.nativeGlobalSmmuIrq.gic.priority,o.nativeGlobalSmmuIrq.gic.configuration,
                o.nativeGlobalSmmuIrq.gic.enabled,static_cast<unsigned long long>(o.nativeGlobalSmmuIrq.gic.requestedRoute),static_cast<unsigned long long>(o.nativeGlobalSmmuIrq.gic.route),
                o.nativeGlobalSmmuIrq.gic.group,o.nativeGlobalSmmuIrq.gic.modifier,o.nativeGlobalSmmuIrq.gic.requestedType,
                unsigned(o.nativeGlobalSmmuIrq.cfg_before_returned)|(unsigned(o.nativeGlobalSmmuIrq.cfg_write_returned)<<1)|(unsigned(o.nativeGlobalSmmuIrq.cfg_after_returned)<<2),
                o.nativeGlobalSmmuIrq.cfg_before,o.nativeGlobalSmmuIrq.cfg_after);
        }else{
            strlcpy(text,"K80 domain: unavailable; PID1 EL0; GMU GPU off",sizeof(text));
        }
        if(snapshot)IOFree(snapshot,sizeof(ZornGen7RegistryStartupResult26));
        hjt26_capture(&milestone,text,kZornPlatformRecordTrial);
    }else if(wantRsc){
        const auto &c=captured.source;const auto &b=boardResult;
        const unsigned bf=unsigned(b.setupReturned)|(unsigned(b.inputReturned)<<1)|(unsigned(b.preparationReturned)<<2);
        const unsigned cf=unsigned(c.intentReturned)|(unsigned(c.registryReturned)<<1)|(unsigned(c.constructionReturned)<<2)|
            (unsigned(c.captureReturned)<<3)|(unsigned(c.readIntentReturned)<<4)|(unsigned(c.mappingReturned)<<5)|
            (unsigned(c.mappingAccepted)<<6)|(unsigned(c.copyReturned)<<7)|(unsigned(c.decoderReturned)<<8)|
            (unsigned(c.headerObserved)<<9)|(unsigned(captured.readerReturned)<<10)|(unsigned(captured.bindingReturned)<<11)|
            (unsigned(captured.privateCaptureOrigin)<<12)|(unsigned(captured.dataReady)<<13);
        const unsigned rf=unsigned(rsc.operationReturned)|(unsigned(rsc.providerReturned)<<1)|(unsigned(rsc.providerOpened)<<2)|
            (unsigned(rsc.descriptorObserved)<<3)|(unsigned(rsc.mappingReturned)<<4)|(unsigned(rsc.mappingAccepted)<<5)|
            (unsigned(rsc.revisionRead)<<6)|(unsigned(rsc.configurationRead)<<7)|(unsigned(rsc.solverRead)<<8)|
            (unsigned(rsc.irqEnableRead)<<9)|(unsigned(rsc.irqStatusRead)<<10);
        char text[512]{};
        const int length=snprintf(text,sizeof(text),"K80 RSC: b=%x/%08x/%08x/%08x/%u sub=%u/%08x cf=%x in=%08x mk=%08x cp=%08x cl=%08x bd=%08x dc=%u v=%08x bytes=%llu dn=%llu r=%u/%08x rf=%x op=%08x p=%08x rev=%08x cfg=%08x sol=%08x ie=%08x is=%08x id=%u off=%x mt=%u nc=%u ch=%u n=%u am=%08x sr=%08x cr=%08x er=%08x busy=%08x; EL0 PID1; GPU not started",
            bf,unsigned(b.setupRaw),unsigned(b.inputRaw),unsigned(b.preparationRaw),unsigned(b.stage.phase),
            unsigned(resourceSubmissionReturned),unsigned(resourceSubmission),cf,unsigned(c.intentRaw),unsigned(c.constructionRaw),
            unsigned(c.captureRaw),unsigned(c.readIntentRaw),unsigned(captured.bindingRaw),c.decoderRaw,c.observedVersion,c.copiedBytes,c.entryCount,
            unsigned(rscReturned),unsigned(rscRaw),rf,unsigned(rsc.operationRaw),unsigned(rsc.providerRaw),rsc.revision,rsc.configuration,rsc.solver,
            rsc.irqEnable,rsc.irqStatus,rsc.drvId,rsc.tcsOffset,rsc.maximumTcs,rsc.commandsPerTcs,rsc.channelCount,rsc.tcsCount,
            rsc.activeMask,rsc.statusReadMask,rsc.controlReadMask,rsc.commandEnableReadMask,rsc.busyObservedMask);
        if(length<=0 || size_t(length)>=sizeof(text))return;
        hjt26_capture(&milestone,text,kZornPlatformRecordTrial);
    }else if(wantCommandDb){
        char text[384]{};const auto &c=commandDbResult;
        snprintf(text,sizeof(text),"K80 CommandDB observation: submit=%08x intent=%u/%08x reg=%u make=%u/%08x capture=%u/%08x claim=%u/%08x map=%u/%u copy=%u decoder=%u/%u hdr=%u ver=%08x bytes=%llu entries=%llu; EL0 PID1; GPU not started",
            unsigned(commandDbSubmission),c.intentReturned,unsigned(c.intentRaw),c.registryReturned,
            c.constructionReturned,unsigned(c.constructionRaw),c.captureReturned,unsigned(c.captureRaw),
            c.readIntentReturned,unsigned(c.readIntentRaw),c.mappingReturned,c.mappingAccepted,c.copyReturned,
            c.decoderReturned,c.decoderRaw,c.headerObserved,c.observedVersion,c.copiedBytes,c.entryCount);
        hjt26_capture(&milestone,text,kZornPlatformRecordTrial);
    }else if(wantBoard){
        char text[384]{};const auto &b=boardResult;const auto &s=b.stage;
        snprintf(text,sizeof(text),"K80 GPU board stage: setup=%08x tr=%u thread=%08x handle=%u ir=%u input=%08x pr=%u prep=%08x phase=%u br=%u board=%08x cr=%u clock=%08x xr=%u xo=%u; EL0 PID1; GPU not started",
            unsigned(b.setupRaw),b.threadReturned,unsigned(b.threadRaw),b.threadHandleReturned,
            b.inputReturned,unsigned(b.inputRaw),b.preparationReturned,unsigned(b.preparationRaw),unsigned(s.phase),
            s.boardConstructionReturned,unsigned(s.boardConstructionRaw),s.clocksReturned,unsigned(s.clocksRaw),s.xoReturned,s.xoCoreInitialized);
        hjt26_capture(&milestone,text,kZornPlatformRecordTrial);
    }else if(wantPresenter){
        char text[256]{};
        if(presenterResult.statusReturned){
            const auto &p=presenterResult.status;
            uint32_t patternFlags=0;uint64_t patternChecked=0;
            const auto patternRaw=ZornBootPresenterPatternResult26(&patternFlags,&patternChecked);
            snprintf(text,sizeof(text),"K80 CPU presenter actual returns: schedule=%08x statusReturned=1 submitted=%u handleReturned=%u creationReturned=%u creation=%08x refusal=%08x pattern=%08x flags=%x checked=%llu; EL0 PID1; physical display and GPU not proven",
                unsigned(presenterResult.scheduleRaw),p.submitted,p.threadHandleReturned,p.creationReturned,unsigned(p.creationRaw),unsigned(ZornBootPresenterRefusal26()),unsigned(patternRaw),patternFlags,patternChecked);
        } else {
            snprintf(text,sizeof(text),"K80 CPU presenter actual returns: schedule=%08x statusReturned=0; EL0 PID1; physical display and GPU not proven",unsigned(presenterResult.scheduleRaw));
        }
        hjt26_capture(&milestone,text,kZornPlatformRecordTrial);
    }else{
    hjt26_capture(&milestone,"K80 IOS26 PID1 entered BSD syscall from EL0; registered UFS rootdev matched; syscall completion and GPU not proven",kZornPlatformRecordTrial);
    }
    ZornUfsCore26::PlatformRecordObservation observation;
    const IOReturn raw=ZornUfsCore26::persistPlatformRecordOnce(milestone.record,observation);
    IOLog("K80 actual PID1-EL0 record: raw=%08x write-returned=%u readback-returned=%u matched=%u\n",raw,
        observation.writeReturned,observation.readbackReturned,observation.readbackMatched);
    if(raw!=kIOReturnSuccess)panic("K80 PID1-EL0 observation storage failed;resources retained;no retry");
}
