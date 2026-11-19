"""One exact275 menu/outside-tap scenario;actual271 root reused read-only."""
import argparse,json,struct,tomllib,plistlib
from pathlib import Path
from zorn_ios26_logdirs_boot_trial import CURRENT,STAGE,load,sha,probe_existing_adb_listener,run
BASE = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-system-trial-3bdbf713eb0f47c28de0e5f0539836d9')
TRIAL = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-system-trial-3bdbf713eb0f47c28de0e5f0539836d9/root-trial')
SCOPE = 'single-K80-ios26-gpu-v275-menu-dismiss-300s-3bdbf713'
TAG = '3bdbf713eb0f47c28de0e5f0539836d9'
PROBE_TAG = 'ddb9c8640ab544cd85cae684e0fb8f66'
BOOT = '716f24c17f6a6cb69ef4817ba5a855ab5395825bbdf997b79fb6ff7f69663e1c'
KERNEL = '5b7668c30fba30e2f444a15153b4c4389e9c8243adfa87ec70ee838e0c9ac93b'
ROOT_SHA = 'c60b198ded30a982cf96ee9cb66211a8f74c7d8fa80f5b6dd8e0839e121304fc'
ADT_SHA = 'c089535db85a5998f1da010663b7384a921c7417c48af224fa0dc6d94113d1f3'
FD_SHA = '1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab'
ARGS = 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_cpu_presenter=1 zorn26_software_accelerator=2 sample=0 sb_wallpaper=0 zorn26_touch=1 zorn26_touch_pacing=1 zorn26_touch_continuous=1 zorn26_touch_record=1 zorn26_gpu_board_stage=1 zorn26_owned_clocks=1 zorn26_gpu_provider_claim=1 zorn26_commanddb_resources=1 zorn26_commanddb_resources_only=1 zorn26_rsc_managed=1 zorn26_clock_prefix=1 zorn26_domain_prefix=1 zorn26_register_maps=1 zorn26_gpu_guarded_maps=1 zorn26_gpu_guarded_smmu_id=1 zorn26_gpu_guarded_smmu_reserve=1 zorn26_gpu_smmu_context_read=1 zorn26_gpu_guarded_gmu_clocks=1 zorn26_gpu_guarded_cx_timer=1 zorn26_gpu_cdc=1 zorn26_gpu_cpu_memory_prep=1 zorn26_gpu_gmu_context_image=1 zorn26_gpu_gmu_direct_seed=1 zorn26_gpu_masked_global_irq=1 zorn26_smmu_active_faults=1 zorn26_gmu_context_irq=1 zorn26_gmu_blocked_stream=1 zorn26_gmu_program_bank=1 zorn26_gmu_observe_reset=1 zorn26_gmu_deferred_valid=21 -g0'
PACKAGE = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/boot-package/verified.json')
SOURCES = {
    'early_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/early-backboardd-host/result.json'),
    'early_tsan':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/early-backboardd-tsan/result.json'),
    'callback_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/progress-success-frame-host/result.json'),
    'terminal_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/terminal-host/result.json'),
    'late_gate':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/late-gate-host/result.json'),
    'close_reset':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/close-reset-host/result.json'),
    'current_validation':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/offline-validation275.json'),
    'full_build':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/full-build-review.json'),
    'native_config':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/native-platform-config.json'),
    'segment_layout':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/segment-layout-check.json'),
    'identity_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/native-identity-current-host/result.json'),
    'patch_replay':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/patch-replay/result.json'),
    'operation_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/close-source-closure275.json'),
    'firmware_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/firmware-input-closure275.json'),
    'native_source_projection':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/unchanged-backend-tests275.json'),
    'root_composition':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v271-desktop-scene-2073ff1494c64d61a0f63ce88573ceab/root-candidate/root-result.json'),
    'root_layout':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v271-desktop-scene-2073ff1494c64d61a0f63ce88573ceab/root-candidate/layout-and-replay-result.json'),
    'policy_clients':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v271-desktop-scene-2073ff1494c64d61a0f63ce88573ceab/root-policy/NativeAdrenoMetal.clients'),
    'policy_job':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v271-desktop-scene-2073ff1494c64d61a0f63ce88573ceab/root-policy/org.unixnu.zorn.metal-probe193.plist'),
    'root_install_review':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-desktop271-root-delta-review-2073ff14/review-inputs.json'),
    'root_install_receipt':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-desktop271-root-delta-review-2073ff14/admission/run/result.json'),
    'root_install_admission':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-desktop271-root-delta-review-2073ff14/admission/admission.json'),
    'root_first_page_proof':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v271-desktop-scene-2073ff1494c64d61a0f63ce88573ceab/installed-root-first-page271.json'),
    'root_install_approval':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-desktop271-root-delta-review-2073ff14/admission/explicit-user-approval271.json'),
    'link_inputs':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/full-link/exact-inputs.json'),
    'source_manifest':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/patches/gpu/ios26-menu-dismiss275/source-manifest.json'),
    'root_window':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/ZornRootWindow26.h'),
    'ufs_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/ZornUfsOwner26.cpp'),
    'cdc_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/ZornUsbCdc26.c'),
    'framebuffer_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/MiniIOMobileFramebuffer.cpp'),
    'native_io':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/direct-runtime/ZornGen7AppIo26.cpp'),
    'native_io_header':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/direct-runtime/ZornGen7AppIo26.h'),
    'progress_decoder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_ui_menu275.py'),
    'capture_postprocessor':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_menu275_capture.py'),
    'entry':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_gpu_v275_system_trial.py'),
    'cdc_capture':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/read-zorn-gpu-menu275-cdc.py'),
    'camera_entry':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/capture-zorn-video275.py'),
    'record_decoder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_early252_record.py'),
    'record_envelope':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_lockscreen_touch_cpu_record.py'),
    'early_base_decoder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_early252.py'),
    'transport_core':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_logdirs_boot_trial.py'),
    'record_helpers':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_gpu_ios26_platform_record.py'),
    'device_helpers':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_gpu_resource_trial.py'),
    'recovery_identity':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_recovery_identity.py'),
    'fixed_builder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/build-zorn-debug.py'),
    'fixed_runner':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/run-zorn-debug.py'),
    'camera_binary':Path('/opt/homebrew/bin/ffmpeg'),
    'desktop_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/dismiss-address-undefined-host/result.json'),
    'desktop_tsan':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/dismiss-thread-host/result.json'),
    'wire_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/dismiss-wire-address-undefined-host/result.json'),
    'wire_tsan':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/dismiss-wire-thread-host/result.json'),
    'desktop_parser_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/dismiss-evidence-final-host/result.json'),
    'journal_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v271-desktop-scene-2073ff1494c64d61a0f63ce88573ceab/desktop-journal-host/result.json'),
    'desktop_capture_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/dismiss-capture-host/result.json'),
    'early_parser_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/early-parser-host/result.json'),
    'early_record_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/early-record-host/result.json'),
    'menu_gate_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/menu-gate-current-host/result.json'),
    'tap_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v275-menu-dismiss-3bdbf713eb0f47c28de0e5f0539836d9/tap-host/result.json'),
}
CHECKS = ['early_host', 'early_tsan', 'callback_host', 'terminal_host', 'late_gate', 'close_reset', 'current_validation', 'full_build', 'native_config', 'segment_layout', 'identity_host', 'patch_replay', 'operation_closure', 'firmware_closure', 'native_source_projection', 'desktop_host', 'desktop_tsan', 'wire_host', 'wire_tsan', 'desktop_parser_host', 'journal_host', 'desktop_capture_host', 'early_parser_host', 'early_record_host', 'menu_gate_host', 'tap_host']
import sys
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
    require(proof['version']==275 and proof['run_id']==TAG and proof['application_probe_run_id']==PROBE_TAG and proof['menu275_selected'],'exact270 probe identity differs')
    require(proof['boot']['sha256']==BOOT and proof['link']['sha256']==KERNEL and proof['root']['sha256']==ROOT_SHA and proof['pins']['ADT']['sha256']==ADT_SHA and proof['pins']['FD']['sha256']==FD_SHA,'exact270 tuple differs')
    require(proof['root_installed'] and not proof['root_installation_required'] and not proof['root_payload_changed'] and not proof['new_root_or_delta_created'],'only actual267root reuse is selected')
    require(proof['ordinary_client']=='backboardd' and proof['probe_job_disabled'] and proof['multi_context_native_dispatch_implemented'] and proof['multiple_logical_member_admission_implemented'] and proof['bounded_same_thread_pending_close_continuation_implemented'],'real shared-member probe path differs')
    require(proof['watchdog_seconds']==300 and proof['recovery_timeout_seconds']==600 and proof['retries']==0 and proof['boot_args']==ARGS,'bounded270 configuration differs')
    for row in [proof['boot'],proof['FAT']]:pinned(row)
    for role in ['kernel','ADT','FD']:pinned(dict(path=proof['pins'][role]['archive'],sha256=proof['pins'][role]['sha256']))
    for key in CHECKS:require(load(SOURCES[key]).get('passed') is True,'current check failed:'+key)
    native=load(SOURCES['native_config']);require(native['CPU_page_bytes']==16384 and native['macros']['ARM_PGSHIFT']=='14','CPU16KiB input required')
    closure=load(SOURCES['operation_closure']);require(closure['kernel_sha256']==KERNEL and closure['root_sha256']==ROOT_SHA and closure['boot_tag']==TAG and closure['program_tag']==PROBE_TAG and proof['menu275_closure']['sha256']==sha(SOURCES['operation_closure']),'actual267 source/test/kernel/root differs')
    for row in closure['checks']:pinned(row)
    validation=load(SOURCES['current_validation']);require(validation['kernel']['sha256']==KERNEL and validation['root']['sha256']==ROOT_SHA and validation['boot']['sha256']==BOOT,'270 validation tuple differs')
    for row in validation['current_checks']+validation['current_check_tools']:pinned(row)
    full=load(SOURCES['full_build']);require(full['kernel_sha256']==KERNEL and full['root_sha256']==ROOT_SHA and full['inputs_verified']==1399 and len(full['header_checks'])==145 and proof['link']['inputs']==1399 and proof['link']['undefined_symbols']==0,'complete current native closure differs')
    require(proof['link']['exact_inputs']['sha256']==sha(SOURCES['link_inputs']),'link manifest changed')
    inputs=load(SOURCES['link_inputs'])
    for row in inputs:pinned(row)
    for role,san in [('early_host','address,undefined'),('early_tsan','thread')]:
        receipt=load(SOURCES[role]);require(receipt['sanitizer']==san and receipt['observer_process']=='backboardd','actual early/process controls differ')
        for row in receipt['source']:
            resolved=(Path(__file__).resolve().parents[2]/row['path']).resolve()
            require(resolved.is_relative_to(SOURCES['root_window'].parent),'early source escaped selected tree')
            pinned(dict(row,path=str(resolved)))
    for row in load(SOURCES['callback_host'])['actual_sources']:pinned(row)
    for key in ['terminal_host','late_gate']:require(load(SOURCES[key])['source_sha256']==sha(SOURCES['cdc_source']),'actual CDC source differs')
    terminal=load(SOURCES['terminal_host']);require(terminal['ASan_UBSan'] and terminal['one_START'] and terminal['unknown_or_inflight_DMA_retained'],'DMA retention differs')
    require(load(SOURCES['close_reset'])['ASan_UBSan'] and load(SOURCES['close_reset'])['TSan'],'actual close controls missing')
    for name,digest in load(SOURCES['close_reset'])['sources'].items():require(sha(SOURCES['root_window'].parent/name)==digest,'current close source differs')
    root=load(SOURCES['root_composition']);require(root['sha256']==ROOT_SHA and root['bytes']==34359738368 and root['signature_verified'] and root['filesystem_verified'] and root['monitored_attributes_preserved'] and root['Metal_bundle_files_unchanged'] and root['application_probe_unchanged'] and not root['application_probe_recompiled'],'actual current root composition differs')
    allowed={'System/Library/Extensions/NativeAdrenoMetal.clients','System/Library/LaunchDaemons/org.unixnu.zorn.metal-probe193.plist'}
    before,after=root['monitored_before_sha256'],root['monitored_after_sha256'];require(set(before)==set(after) and {n for n in before if before[n]!=after[n]}==allowed,'unexpected root payload differs')
    require(SOURCES['policy_clients'].read_text()=='backboardd'+chr(10) and after['System/Library/Extensions/NativeAdrenoMetal.clients']==sha(SOURCES['policy_clients']),'probe-only policy differs')
    job=plistlib.loads(SOURCES['policy_job'].read_bytes());require(job==root['launch_job']==dict(root['prior_launch_job'],RunAtLoad=False,Disabled=True) and not job['KeepAlive'] and job['ProgramArguments']==['/redwood/sbin/zorn-metal-probe193'],'exact existing probe job differs')
    layout=load(SOURCES['root_layout']);require(layout['placement_recomputed_from_Data_end'] and not layout['layout_change'] and layout['candidate_image']['sha256']==layout['replay_image']['sha256']==ROOT_SHA and layout['proposed_relative_first_lba']==6291712 and layout['proposed_blocks']==8388608 and layout['Data_gap_bytes']==782336 and layout['reserve_after_root_bytes']==8588886016 and layout['changed_pages']==25 and layout['write_groups']==9,'current267 root placement/replay differs')
    installed=load(SOURCES['root_install_receipt']);require(installed['installed'] and not installed['booted'] and installed['protected_metadata_and_fences_unchanged'] and installed['expected_image_sha256']==ROOT_SHA and installed['phase']=='root-delta-installed-written-blocks-readback-verified' and installed['readback']==dict(scope='written4KiB-root-pages-only',blocks=25,bytes=102400,sha256='638016a4683ae9adabca4bc84e3f5c4d68a4a61d1a86c51d6f0397cb3e55e4ca'),'actual267 installation/readback differs')
    require(sha(SOURCES['root_install_review'])=='f76f0756dd294dfde0d94209fe3931784d28ce7ca2eaee6be5d1bba2be94f87d' and load(SOURCES['root_install_admission'])['review_sha256']==sha(SOURCES['root_install_review']),'exact root installation review/admission differs')
    adt=load(proof['root_adt_binding']['path']);require(sha(proof['root_adt_binding']['path'])==proof['root_adt_binding']['sha256'] and adt['root_sha256']==ROOT_SHA and adt['only_property'] is None and adt['all_ADT_bytes_equal_to_actual271'] and adt['unrelated_bytes_preserved'],'actual changed ADT differs')
    firmware=load(SOURCES['firmware_closure']);require(firmware['kernel_sha256']==KERNEL and firmware['retained_selected_object'] in inputs,'retained firmware object differs')
    for row in firmware['generated_K80_firmware_headers']+firmware['current_sources']+[firmware['recipe'],firmware['parent_closure']]:pinned(row)
    require(load(SOURCES['desktop_parser_host'])['decoder']['sha256']==sha(SOURCES['progress_decoder']),'actual271 decoder source differs')
    require(load(SOURCES['desktop_capture_host'])['source']['sha256']==sha(SOURCES['capture_postprocessor']),'actual271 JSON postprocessor differs')
    for row in full['header_checks']:require(sha(row['resolved'])==row['sha256'],'actual current native header differs')
    for role in ['desktop_host','desktop_tsan','wire_host','wire_tsan']:
        for row in load(SOURCES[role])['sources']:pinned(row)
    require(load(SOURCES['root_install_approval'])['approved'] is True,'explicit271 installation approval missing')
    for row in load(SOURCES['menu_gate_host'])['sources']:pinned(row)
    projection=load(SOURCES['native_source_projection'])
    for row in projection['byte_identical_to_actual274']:
        require(sha(SOURCES['root_window'].parent/row['file'])==row['sha256'],'retained backend source projection changed')
    for row in projection['retained_backend_tests']:pinned(row)
    for row in load(SOURCES['tap_host'])['sources']:pinned(row)
    return proof

def validate(path):
    require(not path.is_symlink() and path.resolve()==TRIAL/'bundle.json','canonical275 bundle required')
    b=load(path);require(all(type(b.get(k)) is type(v) and b[k]==v for k,v in EXPECTED.items()),'exact275 scope differs')
    pins=b['pins'];require(set(pins)==ARTIFACTS|PROTECTIONS|TOOLS|SOURCES.keys(),'complete275 role set required')
    for role,row in pins.items():
        pinned(row);src,archive=Path(row['path']),Path(row['archive']);require(archive.is_file() and not archive.is_symlink() and archive.parent==TRIAL/'archive' and not src.samefile(archive) and sha(archive)==row['sha256'],'independent275 archive differs:'+role)
    require(all(Path(pins[k]['path']).resolve()==v.resolve() for k,v in SOURCES.items()),'275 fixed source paths differ')
    proof=validate_package(load(pins['package']['path']))
    require(Path(pins['package']['path'])==PACKAGE and pins['boot']['sha256']==BOOT and pins['kernel']['sha256']==KERNEL and pins['ADT']['sha256']==ADT_SHA and pins['fd']['sha256']==FD_SHA,'packaged tuple differs')
    require(pins['installed_result']['sha256']==sha(SOURCES['root_install_receipt']),'actual installation role differs')
    for row in proof['FAT_members']:
        role={'BOOTAA64.EFI':'manager','DarwinBoot26.efi':'loader','kernel.macho':'kernel','kernel.macho.adt':'ADT','unixnu.toml':'menu'}[Path(row['FAT_path']).name];require(pins[role]['sha256']==row['sha256'],'FAT member differs:'+role)
    menu=tomllib.loads(Path(pins['menu']['path']).read_text());require(len(menu['entry'])==1 and menu['entry'][0]['args']==ARGS and not menu['boot']['connect_all'] and not menu['kits']['autoload'],'single bounded menu differs')
    with Path(pins['FAT']['path']).open('rb') as f:
        for sector in [0,6]:f.seek(sector*512+0x180);mode=struct.pack('<II',1,0xfffffffe);require(f.read(32)==b'ZORNGHWD'+mode+b'ZORNTPWR'+mode,'WDT/power markers differ')
    cohort=load(pins['installed_cohort']['path']);require(cohort['package']['sha256']==pins['package']['sha256'] and cohort['root_install_receipt']['sha256']==pins['installed_result']['sha256'] and cohort['root']['sha256']==ROOT_SHA and cohort['boot']['sha256']==BOOT and not cohort['system_booted'] and not cohort['new_root_installation'] and cohort['reused_root_from_actual271'] and not cohort['full_phone_root_hash_performed'],'actual root cohort differs')
    state=load(CURRENT);require(state['gpu_discovery'].get('current_phone_root_expected_sha256')==ROOT_SHA,'current installed root differs')
    require(load(pins['host_adb_proof']['path'])['adb_sha256']==pins['adb_binary']['sha256'] and load(pins['record_identity']['path'])['run_id']==TAG,'native tool/record identity differs')
    return b

def record_result(decoded):
    require(decoded['CPU_samples_pending'] is True and decoded['deferred_CPU_owner_published'] is True,'exact early252 record required')
    return dict(status='recovered-fresh-root-EL0-early-GPU-checkpoint',root_mount_proven=True,PID1_image_activation_proven=True,cpu_online=decoded['cpu_online'],eight_cpus_available=decoded['cpu_online']==8,CPU_samples_in_record_pending=True,early_deferred_CPU_owner_published=True,GPU_started=False,desktop_proven=False,touch_input_delivery_proven=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios26-menu-dismiss275-trial', action='store_true')
    parser.add_argument('--bundle',
                        type=Path, required=True, dest='bundle')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    bundle = validate(args.bundle)
    if args.check_only:
        print('275 menu/outside-tap host inputs verified; no USB or claim')
        return
    if args.admission is None or args.admission.resolve() != TRIAL / 'admission.json':
        parser.error('exact local admission required')
    admission = load(args.admission)
    binding = dict(scope=SCOPE, nonce=TAG, bundle_sha256=sha(args.bundle), boot_sha256=BOOT, allow_boot=True)
    for name in ('owner', 'ready', 'admission'):
        row = admission if name == 'admission' else load(TRIAL / (name + '.json'))
        if any(row.get(k) != v for k, v in binding.items()):
            raise ValueError(f'{name} does not bind the exact 275 menu/outside-tap scope')
        if name != 'admission' and sha(TRIAL / (name + '.json')) != admission[name + '_sha256']:
            raise ValueError(f'{name} changed after admission')
    ready=load(TRIAL/'ready.json')
    if (ready.get('host_checks_passed') is not True or ready.get('one_boot') is not True or
            ready.get('timeout_seconds')!=600 or ready.get('watchdog_seconds')!=300 or
            not isinstance(ready.get('hardware_only_pending'),list) or not ready['hardware_only_pending']):
        raise ValueError('275 ready must retain bounded watchdog/return and unresolved hardware conditions')
    for row in ready.get('host_checks',[]):
        if sha(row['path'])!=row['sha256'] or load(row['path']).get('passed') is not True:
            raise ValueError('275 ready host test changed/failed')
    if not ready.get('host_checks'):
        raise ValueError('275 ready requires actual current host receipts')
    state = load(CURRENT)
    if state.get('gpu_discovery', {}).get('current_mode') != 'unattended-phone-connected':
        raise ValueError('unattended phone mode required')
    if any(state.get(k) for k in ['active_run','active_admission','active_build','runner_session','stop_device_operations']) or state.get('gpu_discovery',{}).get('active_admission'):
        raise ValueError('device busy/stopped or independent storage admission active;no probe/claim')
    claim = TRIAL / 'trial/one-shot.claim.json'
    if claim.exists() or claim.is_symlink():
        raise ValueError('275 menu/outside-tap trial already consumed')
    require(Path(sys.argv[0]).resolve()==Path(__file__).with_name("run-zorn-debug.py"),"maintained fixed runner required")
    probe_existing_adb_listener()
    run(bundle, claim, record_result=record_result)


if __name__ == '__main__':
    main()
