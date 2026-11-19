"""One exact268 CPU client-census scheduling regression on unchanged actual267root/Metal probe while retaining131072CPU span-capacity and successful VM totals and bounded late CDC observation.

Actual267 installation/readback checked separately from its unchanged offline package;no cross-task or physical-touch qualification.
All266 native inputs and current lifecycle tests are bound before one boot.
"""
import argparse,json,struct,tomllib,plistlib
from pathlib import Path
from zorn_ios26_logdirs_boot_trial import CURRENT,STAGE,load,sha,probe_existing_adb_listener,run
BASE = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-system-trial-68353193691144bd9bae517b08d3770a')
TRIAL = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-system-trial-68353193691144bd9bae517b08d3770a/root-trial')
SCOPE = 'single-K80-ios26-gpu-v268-client-census-300s-68353193'
TAG = '68353193691144bd9bae517b08d3770a'
PROBE_TAG = 'ddb9c8640ab544cd85cae684e0fb8f66'
BOOT = '4c88db3be7884b031ca5a9673bb7bdcdb3561dfd4d7d0583beed60a70b649c88'
KERNEL = 'bf0bbb455c8c9948045927c4fab0e169a033e34a4af000a48af8bd953654e195'
ROOT_SHA = 'f3ad6b7b6bae2ffd8aaa835427e0b4ace823f52bd614a298d2b7d191da33dd26'
ADT_SHA = '421760d43d4ce113166181db5d57fb6bca3aa9a8634c6718db7075d23d186d1b'
FD_SHA = '1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab'
ARGS = 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_cpu_presenter=1 zorn26_software_accelerator=2 sample=0 sb_wallpaper=0 zorn26_touch=1 zorn26_touch_pacing=1 zorn26_touch_continuous=1 zorn26_touch_record=1 zorn26_gpu_board_stage=1 zorn26_owned_clocks=1 zorn26_gpu_provider_claim=1 zorn26_commanddb_resources=1 zorn26_commanddb_resources_only=1 zorn26_rsc_managed=1 zorn26_clock_prefix=1 zorn26_domain_prefix=1 zorn26_register_maps=1 zorn26_gpu_guarded_maps=1 zorn26_gpu_guarded_smmu_id=1 zorn26_gpu_guarded_smmu_reserve=1 zorn26_gpu_smmu_context_read=1 zorn26_gpu_guarded_gmu_clocks=1 zorn26_gpu_guarded_cx_timer=1 zorn26_gpu_cdc=1 zorn26_gpu_cpu_memory_prep=1 zorn26_gpu_gmu_context_image=1 zorn26_gpu_gmu_direct_seed=1 zorn26_gpu_masked_global_irq=1 zorn26_smmu_active_faults=1 zorn26_gmu_context_irq=1 zorn26_gmu_blocked_stream=1 zorn26_gmu_program_bank=1 zorn26_gmu_observe_reset=1 zorn26_gmu_deferred_valid=21 -g0'
PACKAGE = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/boot-package/verified.json')
SOURCES = {
    'early_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/early-host-wire/result.json'),
    'early_tsan':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/early-tsan-wire/result.json'),
    'callback_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/progress-success-frame-host/result.json'),
    'terminal_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/terminal-host/result.json'),
    'late_gate':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/late-gate-host/result.json'),
    'close_reset':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/close-reset-host/result.json'),
    'transport_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/transport-source-closure268.json'),
    'operation_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/close-source-closure268.json'),
    'current_validation':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/final-offline-check266.json'),
    'full_build':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/full-build-review.json'),
    'native_config':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/native-platform-config.json'),
    'segment_layout':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/segment-layout-check.json'),
    'patch_replay':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/patch-replay/result.json'),
    'root_reuse':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/root-reuse266.json'),
    'firmware_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/firmware-input-closure268.json'),
    'retirement_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/additional-retirement-final268.json'),
    'root_layout':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-candidate/layout-and-replay-result.json'),
    'root_composition':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-candidate/root-result.json'),
    'root_delta':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-candidate/delta.json'),
    'policy_clients':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-policy/NativeAdrenoMetal.clients'),
    'policy_job':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-policy/org.unixnu.zorn.metal-probe193.plist'),
    'record_decoder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_early252_record.py'),
    'record_envelope':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_lockscreen_touch_cpu_record.py'),
    'progress_decoder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_metal_probe267.py'),
    'early_base_decoder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_early252.py'),
    'early_test_tool':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/check-ios26-early-system.py'),
    'transport_core':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_logdirs_boot_trial.py'),
    'record_helpers':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_gpu_ios26_platform_record.py'),
    'device_helpers':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_gpu_resource_trial.py'),
    'recovery_identity':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_recovery_identity.py'),
    'fixed_builder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/build-zorn-debug.py'),
    'fixed_runner':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/run-zorn-debug.py'),
    'camera_binary':Path('/opt/homebrew/bin/ffmpeg'),
    'journal_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/journal-compositor-host/result.json'),
    'early_parser_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/early-parser-host/result.json'),
    'early_record_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/early-record-host/result.json'),
    'observer_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/observer-program-host/result.json'),
    'link_inputs':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v268-client-census-68353193691144bd9bae517b08d3770a/full-link/exact-inputs.json'),
    'source_manifest':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/patches/gpu/ios26-known-readback266/source-manifest.json'),
    'entry':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_gpu_v268_system_trial.py'),
    'cdc_capture':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/read-zorn-gpu-census268-cdc.py'),
    'camera_entry':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/capture-zorn-video268.py'),
    'root_window':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v268-client-census-68353193691144bd9bae517b08d3770a/ZornRootWindow26.h'),
    'ufs_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v268-client-census-68353193691144bd9bae517b08d3770a/ZornUfsOwner26.cpp'),
    'cdc_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v268-client-census-68353193691144bd9bae517b08d3770a/ZornUsbCdc26.c'),
    'framebuffer_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v268-client-census-68353193691144bd9bae517b08d3770a/MiniIOMobileFramebuffer.cpp'),
    'native_io':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v268-client-census-68353193691144bd9bae517b08d3770a/direct-runtime/ZornGen7AppIo26.cpp'),
    'native_io_header':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v268-client-census-68353193691144bd9bae517b08d3770a/direct-runtime/ZornGen7AppIo26.h'),
}
SOURCES['identity_host'] = PACKAGE.parent.parent/'native-identity-current-host/result.json'
SOURCES['native_source_projection'] = PACKAGE.parent.parent/'unchanged-backend-tests268.json'
SOURCES['failure_parser'] = PACKAGE.parent.parent/'known-task-public-host/result.json'
SOURCES['failure_store_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v262-mapping-capacity-3df21cbd4e974475befb85cebe382928/failure-store-host/result.json')
SOURCES['failure_store_tsan'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v262-mapping-capacity-3df21cbd4e974475befb85cebe382928/failure-store-tsan/result.json')
CHECKS = ['identity_host','native_source_projection','early_host', 'early_tsan', 'callback_host', 'terminal_host', 'late_gate', 'close_reset', 'transport_closure', 'operation_closure', 'current_validation', 'full_build', 'native_config', 'segment_layout', 'patch_replay', 'root_reuse', 'firmware_closure', 'retirement_closure']
CHECKS += ['failure_parser','failure_store_host','failure_store_tsan']
SOURCES['mapping_capacity_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v264-pool-capacity-a1d69e45450e4415aa5b23c975a011bc/pool-capacity-host/result.json')
SOURCES['late_cadence_host'] = PACKAGE.parent.parent/'shot-cadence-public-host/result.json'
CHECKS += ['mapping_capacity_host','late_cadence_host']
SOURCES['vm_totals_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v264-pool-capacity-a1d69e45450e4415aa5b23c975a011bc/vm-totals-public-host/result.json')
SOURCES['vm_totals_tsan'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v264-pool-capacity-a1d69e45450e4415aa5b23c975a011bc/vm-totals-public-tsan/result.json')
SOURCES['capacity_reference'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v264-pool-capacity-a1d69e45450e4415aa5b23c975a011bc/pool-capacity-reference264.json')
CHECKS += ['vm_totals_host','vm_totals_tsan','capacity_reference']
SOURCES['serial_common_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v265-serial-shot-dc48e662130d4dc28186229f33c6aa7e/serial-shot-public-host/result.json')
SOURCES['serial_common_tsan'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v265-serial-shot-dc48e662130d4dc28186229f33c6aa7e/serial-shot-public-tsan/result.json')
SOURCES['serial_source_projection'] = PACKAGE.parent.parent/'unchanged-backend-tests268.json'
CHECKS += ['serial_common_host','serial_common_tsan','serial_source_projection']
SOURCES['known_task_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v266-known-readback-df2c09e8c23f42cba9b0a3e6e2e78ae9')/'known-task-public-host/result.json'
SOURCES['known_task_header'] = SOURCES['ufs_source'].parent/'ZornKnownTask266.h'
SOURCES['shot_decoder265'] = Path(__file__).with_name('inspect_ios26_gpu_shot265.py')
SOURCES['kernel_decoder266'] = Path(__file__).with_name('inspect_ios26_gpu_kernel266.py')
SOURCES['pool_decoder264'] = Path(__file__).with_name('inspect_ios26_gpu_pool264.py')
SOURCES['metal_parser_host'] = PACKAGE.parent.parent/'probe-evidence-public-host/result.json'
SOURCES['shared_probe_host'] = PACKAGE.parent.parent/'shared-query-public-host/result.json'
SOURCES['root_composition'] = PACKAGE.parent.parent/'root-candidate/root-result.json'
SOURCES['root_layout'] = PACKAGE.parent.parent/'root-candidate/layout-and-replay-result.json'
SOURCES['policy_clients'] = PACKAGE.parent.parent/'root-policy/NativeAdrenoMetal.clients'
SOURCES['policy_job'] = PACKAGE.parent.parent/'root-policy/org.unixnu.zorn.metal-probe193.plist'
SOURCES['current_validation'] = PACKAGE.parent.parent/'offline-validation268.json'
SOURCES['observer_host'] = PACKAGE.parent.parent/'observer-program-host/result.json'
SOURCES['early_parser_host'] = PACKAGE.parent.parent/'early-parser-host/result.json'
SOURCES['early_record_host'] = PACKAGE.parent.parent/'early-record-host/result.json'
SOURCES['journal_host'] = PACKAGE.parent.parent/'journal-probe-host/result.json'
SOURCES['serial_source_projection'] = PACKAGE.parent.parent/'unchanged-backend-tests268.json'
SOURCES['failure_parser'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v266-known-readback-df2c09e8c23f42cba9b0a3e6e2e78ae9')/'known-task-public-host/result.json'
SOURCES['source_manifest'] = Path(__file__).resolve().parents[1]/'patches/gpu/ios26-metal-probe267/source-manifest.json'
SOURCES['root_install_review'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal267-root-delta-review-ddb9c864/review-inputs.json')
SOURCES['root_install_receipt'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal267-root-delta-review-ddb9c864/review-inputs.json').parent/'admission/run/result.json'
SOURCES['root_install_admission'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal267-root-delta-review-ddb9c864/review-inputs.json').parent/'admission/admission.json'
SOURCES['root_first_page_proof'] = PACKAGE.parent.parent/'installed-root-first-page267.json'
SOURCES.pop('root_reuse')
CHECKS = [k for k in CHECKS if k!='root_reuse']+['known_task_host','metal_parser_host','shared_probe_host','observer_host','journal_host','root_first_page_proof']
# Actual267 root/probe and unchanged early/journal helpers are reused only
# under the explicit268 source projection and current native identity checks.
SOURCES['early_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'early-host-wire/result.json'
SOURCES['early_tsan'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'early-tsan-wire/result.json'
SOURCES['observer_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'observer-program-host/result.json'
SOURCES['journal_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'journal-probe-host/result.json'
SOURCES['late_cadence_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'shot-cadence-public-host/result.json'
SOURCES['metal_parser_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'probe-evidence-public-host/result.json'
SOURCES['shared_probe_host'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'shared-query-public-host/result.json'
SOURCES['root_composition'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'root-candidate/root-result.json'
SOURCES['root_layout'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'root-candidate/layout-and-replay-result.json'
SOURCES['policy_clients'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'root-policy/NativeAdrenoMetal.clients'
SOURCES['policy_job'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'root-policy/org.unixnu.zorn.metal-probe193.plist'
SOURCES['root_first_page_proof'] = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-metal-v267-shared-probe-ddb9c8640ab544cd85cae684e0fb8f66')/'installed-root-first-page267.json'
SOURCES['progress_decoder'] = Path(__file__).with_name('inspect_ios26_client_census268.py')
SOURCES['metal_decoder267'] = Path(__file__).with_name('inspect_ios26_metal_probe267.py')
SOURCES['census_parser_host'] = PACKAGE.parent.parent/'census-evidence-public-host/result.json'
SOURCES['census_store_host'] = PACKAGE.parent.parent/'census-address-undefined-host/result.json'
SOURCES['census_store_tsan'] = PACKAGE.parent.parent/'census-thread-host/result.json'
SOURCES['source_manifest'] = Path(__file__).resolve().parents[1]/'patches/gpu/ios26-client-census268/source-manifest.json'
CHECKS += ['census_parser_host','census_store_host','census_store_tsan']
ARTIFACTS={'boot','kernel','FAT','fd','ADT','loader','manager','menu','package','record_identity','installed_cohort'}
PROTECTIONS={'primary_GPT','backup_GPT','root_manifest','Data_header','Data_metadata','root_first_page','root_before','root_after'}
TOOLS={'installed_result','adb_binary','fastboot_binary','host_adb_proof'}
EXPECTED=dict(scope=SCOPE,serial='92988a43',product='zorn',slot='a',trial_seconds=300,timeout_seconds=600,retries=0,watchdog_mode=1,accepted_recovery='twrp-or-orangefox',existing_server_only=True,native_log_absolute_lba=49563392,native_log_blocks=1,root_read_only=True,data_read_only=True,transient_boot=True,bootstrap_allowed=False,gpu_firmware_start=True,allow_boot=False)

def require(condition,message):
    if not condition:raise ValueError(message)

def pinned(row):
    p=Path(row['path']);require(p.is_absolute() and not p.is_symlink() and p.is_file() and sha(p)==row['sha256'],'source/check bytes changed: '+str(p))

def validate_package(proof=None):
    proof=load(PACKAGE) if proof is None else proof;B=PACKAGE.parent.parent
    require(proof['version']==268 and proof['run_id']==TAG and proof['application_probe_run_id']==PROBE_TAG and proof['client_census268_selected'],'exact267 probe identity differs')
    require(proof['boot']['sha256']==BOOT and proof['link']['sha256']==KERNEL and proof['root']['sha256']==ROOT_SHA and proof['pins']['ADT']['sha256']==ADT_SHA and proof['pins']['FD']['sha256']==FD_SHA,'exact267 tuple differs')
    require(proof['root_installed'] and not proof['root_installation_required'] and not proof['root_payload_changed'] and not proof['new_root_or_delta_created'],'only actual267root reuse is selected')
    require(proof['ordinary_client']=='zorn-metal-probe193' and not proof['probe_job_disabled'] and proof['multi_context_native_dispatch_implemented'] and proof['multiple_logical_member_admission_implemented'] and proof['bounded_same_thread_pending_close_continuation_implemented'],'real shared-member probe path differs')
    require(proof['watchdog_seconds']==300 and proof['recovery_timeout_seconds']==600 and proof['retries']==0 and proof['boot_args']==ARGS,'bounded267 configuration differs')
    for row in [proof['boot'],proof['FAT']]:pinned(row)
    for role in ['kernel','ADT','FD']:pinned(dict(path=proof['pins'][role]['archive'],sha256=proof['pins'][role]['sha256']))
    for key in CHECKS:require(load(SOURCES[key]).get('passed') is True,'current check failed:'+key)
    require(load(SOURCES['metal_parser_host'])['decoder']['sha256']==sha(SOURCES['metal_decoder267']),'retained267 Metal parser source differs')
    require(load(SOURCES['census_parser_host'])['decoder']['sha256']==sha(SOURCES['progress_decoder']),'current268 census parser differs')
    require(load(SOURCES['shared_probe_host'])['actual_function_extracted_from']['sha256']==sha(SOURCES['ufs_source'].parent/'userland/ZornMetalProbe193.mm'),'current actual shared probe differs')
    native=load(SOURCES['native_config']);require(native['CPU_page_bytes']==16384 and native['macros']['ARM_PGSHIFT']=='14','CPU16KiB input required')
    closure=load(SOURCES['operation_closure']);require(closure['kernel_sha256']==KERNEL and closure['root_sha256']==ROOT_SHA and closure['boot_tag']==TAG and closure['program_tag']==PROBE_TAG and proof['client_census268_closure']['sha256']==sha(SOURCES['operation_closure']),'actual267 source/test/kernel/root differs')
    for row in closure['checks']:pinned(row)
    validation=load(SOURCES['current_validation']);require(validation['kernel']['sha256']==KERNEL and validation['root']['sha256']==ROOT_SHA and validation['boot']['sha256']==BOOT,'267 validation tuple differs')
    for row in validation['current_checks']+validation['current_check_tools']:pinned(row)
    full=load(SOURCES['full_build']);require(full['kernel_sha256']==KERNEL and full['root_sha256']==ROOT_SHA and full['inputs_verified']==1398 and len(full['header_checks'])==126 and proof['link']['inputs']==1398 and proof['link']['undefined_symbols']==0,'complete current native closure differs')
    require(proof['link']['exact_inputs']['sha256']==sha(SOURCES['link_inputs']),'link manifest changed')
    inputs=load(SOURCES['link_inputs'])
    for row in inputs:pinned(row)
    for role,san in [('early_host','address,undefined'),('early_tsan','thread')]:
        receipt=load(SOURCES[role]);require(receipt['sanitizer']==san and receipt['observer_process']=='zorn-metal-probe193','actual early/process controls differ')
        for row in receipt['source']:pinned(row)
    for row in load(SOURCES['callback_host'])['actual_sources']:pinned(row)
    for key in ['terminal_host','late_gate']:require(load(SOURCES[key])['source_sha256']==sha(SOURCES['cdc_source']),'actual CDC source differs')
    terminal=load(SOURCES['terminal_host']);require(terminal['ASan_UBSan'] and terminal['one_START'] and terminal['unknown_or_inflight_DMA_retained'],'DMA retention differs')
    require(load(SOURCES['close_reset'])['ASan_UBSan'] and load(SOURCES['close_reset'])['TSan'],'actual close controls missing')
    for name,digest in load(SOURCES['close_reset'])['sources'].items():require(sha(SOURCES['root_window'].parent/name)==digest,'current close source differs')
    root=load(SOURCES['root_composition']);require(root['sha256']==ROOT_SHA and root['bytes']==34359738368 and root['signature_verified'] and root['filesystem_verified'] and root['monitored_attributes_preserved'] and root['Metal_bundle_files_unchanged'] and root['application_probe_recompiled'],'actual current root composition differs')
    allowed={'redwood/sbin/zorn-metal-probe193','System/Library/Extensions/NativeAdrenoMetal.clients','System/Library/LaunchDaemons/org.unixnu.zorn.metal-probe193.plist'}
    before,after=root['monitored_before_sha256'],root['monitored_after_sha256'];require(set(before)==set(after) and {n for n in before if before[n]!=after[n]}==allowed,'unexpected root payload differs')
    require(SOURCES['policy_clients'].read_text()=='zorn-metal-probe193'+chr(10) and after['System/Library/Extensions/NativeAdrenoMetal.clients']==sha(SOURCES['policy_clients']),'probe-only policy differs')
    job=plistlib.loads(SOURCES['policy_job'].read_bytes());require(job==root['launch_job']==dict(root['prior_launch_job'],RunAtLoad=True,Disabled=False) and not job['KeepAlive'] and job['ProgramArguments']==['/redwood/sbin/zorn-metal-probe193'],'exact existing probe job differs')
    layout=load(SOURCES['root_layout']);require(layout['placement_recomputed_from_Data_end'] and not layout['layout_change'] and layout['candidate_image']['sha256']==layout['replay_image']['sha256']==ROOT_SHA and layout['proposed_relative_first_lba']==6291712 and layout['proposed_blocks']==8388608 and layout['Data_gap_bytes']==782336 and layout['reserve_after_root_bytes']==8588886016 and layout['changed_pages']==46 and layout['write_groups']==18,'current267 root placement/replay differs')
    installed=load(SOURCES['root_install_receipt']);require(installed['installed'] and not installed['booted'] and installed['protected_metadata_and_fences_unchanged'] and installed['expected_image_sha256']==ROOT_SHA and installed['phase']=='root-delta-installed-written-blocks-readback-verified' and installed['readback']==dict(scope='written4KiB-root-pages-only',blocks=46,bytes=188416,sha256='322963faeeb2bc599194deb507b915a808dfb4415c550eb70f65921ebb047b33'),'actual267 installation/readback differs')
    require(sha(SOURCES['root_install_review'])=='57064ffa047be7dc648f66c95b0496be5f5a8d6f36c9e02c5386d0ee873c62a1' and load(SOURCES['root_install_admission'])['review_sha256']==sha(SOURCES['root_install_review']),'exact root installation review/admission differs')
    adt=load(proof['root_adt_binding']['path']);require(sha(proof['root_adt_binding']['path'])==proof['root_adt_binding']['sha256'] and adt['root_sha256']==ROOT_SHA and adt['only_property'] is None and adt['unrelated_bytes_preserved'],'actual changed ADT differs')
    firmware=load(SOURCES['firmware_closure']);require(firmware['kernel_sha256']==KERNEL and firmware['retained_selected_object'] in inputs,'retained firmware object differs')
    for row in firmware['generated_K80_firmware_headers']+firmware['current_sources']+[firmware['recipe'],firmware['parent_closure']]:pinned(row)
    return proof

def validate(path):
    require(not path.is_symlink() and path.resolve()==TRIAL/'bundle.json','canonical267 bundle required')
    b=load(path);require(all(type(b.get(k)) is type(v) and b[k]==v for k,v in EXPECTED.items()),'exact267 scope differs')
    pins=b['pins'];require(set(pins)==ARTIFACTS|PROTECTIONS|TOOLS|SOURCES.keys(),'complete267 role set required')
    for role,row in pins.items():
        pinned(row);src,archive=Path(row['path']),Path(row['archive']);require(archive.is_file() and not archive.is_symlink() and archive.parent==TRIAL/'archive' and not src.samefile(archive) and sha(archive)==row['sha256'],'independent267 archive differs:'+role)
    require(all(Path(pins[k]['path']).resolve()==v.resolve() for k,v in SOURCES.items()),'267 fixed source paths differ')
    proof=validate_package(load(pins['package']['path']))
    require(Path(pins['package']['path'])==PACKAGE and pins['boot']['sha256']==BOOT and pins['kernel']['sha256']==KERNEL and pins['ADT']['sha256']==ADT_SHA and pins['fd']['sha256']==FD_SHA,'packaged tuple differs')
    require(pins['installed_result']['sha256']==sha(SOURCES['root_install_receipt']),'actual installation role differs')
    for row in proof['FAT_members']:
        role={'BOOTAA64.EFI':'manager','DarwinBoot26.efi':'loader','kernel.macho':'kernel','kernel.macho.adt':'ADT','unixnu.toml':'menu'}[Path(row['FAT_path']).name];require(pins[role]['sha256']==row['sha256'],'FAT member differs:'+role)
    menu=tomllib.loads(Path(pins['menu']['path']).read_text());require(len(menu['entry'])==1 and menu['entry'][0]['args']==ARGS and not menu['boot']['connect_all'] and not menu['kits']['autoload'],'single bounded menu differs')
    with Path(pins['FAT']['path']).open('rb') as f:
        for sector in [0,6]:f.seek(sector*512+0x180);mode=struct.pack('<II',1,0xfffffffe);require(f.read(32)==b'ZORNGHWD'+mode+b'ZORNTPWR'+mode,'WDT/power markers differ')
    cohort=load(pins['installed_cohort']['path']);require(cohort['package']['sha256']==pins['package']['sha256'] and cohort['root_install_receipt']['sha256']==pins['installed_result']['sha256'] and cohort['root']['sha256']==ROOT_SHA and cohort['boot']['sha256']==BOOT and not cohort['system_booted'] and not cohort['new_root_installation'] and cohort['reused_root_from_actual267'] and not cohort['full_phone_root_hash_performed'],'actual root cohort differs')
    state=load(CURRENT);require(state['gpu_discovery'].get('current_phone_root_expected_sha256')==ROOT_SHA,'current installed root differs')
    require(load(pins['host_adb_proof']['path'])['adb_sha256']==pins['adb_binary']['sha256'] and load(pins['record_identity']['path'])['run_id']==TAG,'native tool/record identity differs')
    return b

def record_result(decoded):
    require(decoded['CPU_samples_pending'] is True and decoded['deferred_CPU_owner_published'] is True,'exact early252 record required')
    return dict(status='recovered-fresh-root-EL0-early-GPU-checkpoint',root_mount_proven=True,PID1_image_activation_proven=True,cpu_online=decoded['cpu_online'],eight_cpus_available=decoded['cpu_online']==8,CPU_samples_in_record_pending=True,early_deferred_CPU_owner_published=True,GPU_started=False,desktop_proven=False,touch_input_delivery_proven=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios26-client-census268-trial', action='store_true')
    parser.add_argument('--bundle',
                        type=Path, required=True, dest='bundle')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    bundle = validate(args.bundle)
    if args.check_only:
        print('268 client-census host inputs verified; no USB or claim')
        return
    if args.admission is None or args.admission.resolve() != TRIAL / 'admission.json':
        parser.error('exact local admission required')
    admission = load(args.admission)
    binding = dict(scope=SCOPE, nonce=TAG, bundle_sha256=sha(args.bundle), boot_sha256=BOOT, allow_boot=True)
    for name in ('owner', 'ready', 'admission'):
        row = admission if name == 'admission' else load(TRIAL / (name + '.json'))
        if any(row.get(k) != v for k, v in binding.items()):
            raise ValueError(f'{name} does not bind the exact 268 client-census scope')
        if name != 'admission' and sha(TRIAL / (name + '.json')) != admission[name + '_sha256']:
            raise ValueError(f'{name} changed after admission')
    ready=load(TRIAL/'ready.json')
    if (ready.get('host_checks_passed') is not True or ready.get('one_boot') is not True or
            ready.get('timeout_seconds')!=600 or ready.get('watchdog_seconds')!=300 or
            not isinstance(ready.get('hardware_only_pending'),list) or not ready['hardware_only_pending']):
        raise ValueError('268 ready must retain bounded watchdog/return and unresolved hardware conditions')
    for row in ready.get('host_checks',[]):
        if sha(row['path'])!=row['sha256'] or load(row['path']).get('passed') is not True:
            raise ValueError('268 ready host test changed/failed')
    if not ready.get('host_checks'):
        raise ValueError('268 ready requires actual current host receipts')
    state = load(CURRENT)
    if state.get('gpu_discovery', {}).get('current_mode') != 'unattended-phone-connected':
        raise ValueError('unattended phone mode required')
    if any(state.get(k) for k in ['active_run','active_admission','active_build','runner_session','stop_device_operations']) or state.get('gpu_discovery',{}).get('active_admission'):
        raise ValueError('device busy/stopped or independent storage admission active;no probe/claim')
    claim = TRIAL / 'trial/one-shot.claim.json'
    if claim.exists() or claim.is_symlink():
        raise ValueError('268 client-census trial already consumed')
    probe_existing_adb_listener()
    run(bundle, claim, record_result=record_result)


if __name__ == '__main__':
    main()
