"""One exact260 ordinary backboardd regression of shared context and bounded close.

Same installed252 root and typed wire;no independent cross-task policy workload.
All260 native inputs and current lifecycle tests are bound before one boot.
"""
import argparse,json,struct,tomllib,plistlib
from pathlib import Path
from zorn_ios26_logdirs_boot_trial import CURRENT,STAGE,load,sha,probe_existing_adb_listener,run
BASE = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-system-trial-81683386ba0d423d817a2b7d0e1c60f0')
TRIAL = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-system-trial-81683386ba0d423d817a2b7d0e1c60f0/root-trial')
SCOPE = 'single-K80-ios26-gpu-v260-platform-identity-300s-81683386'
TAG = '81683386ba0d423d817a2b7d0e1c60f0'
PROBE_TAG = 'f80eb1403d7e4f958b5eddacb49d98d0'
BOOT = 'a4f282c67941ce334df0df4ef220498418e271f52745f9c33e87d447db32ebef'
KERNEL = '0760266217b3d721f1799c859958310ced40b3f74c802266926b841f8b918f43'
ROOT_SHA = '859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02'
ADT_SHA = '98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936'
FD_SHA = '1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab'
ARGS = 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_cpu_presenter=1 zorn26_software_accelerator=2 sample=0 sb_wallpaper=0 zorn26_touch=1 zorn26_touch_pacing=1 zorn26_touch_continuous=1 zorn26_touch_record=1 zorn26_gpu_board_stage=1 zorn26_owned_clocks=1 zorn26_gpu_provider_claim=1 zorn26_commanddb_resources=1 zorn26_commanddb_resources_only=1 zorn26_rsc_managed=1 zorn26_clock_prefix=1 zorn26_domain_prefix=1 zorn26_register_maps=1 zorn26_gpu_guarded_maps=1 zorn26_gpu_guarded_smmu_id=1 zorn26_gpu_guarded_smmu_reserve=1 zorn26_gpu_smmu_context_read=1 zorn26_gpu_guarded_gmu_clocks=1 zorn26_gpu_guarded_cx_timer=1 zorn26_gpu_cdc=1 zorn26_gpu_cpu_memory_prep=1 zorn26_gpu_gmu_context_image=1 zorn26_gpu_gmu_direct_seed=1 zorn26_gpu_masked_global_irq=1 zorn26_smmu_active_faults=1 zorn26_gmu_context_irq=1 zorn26_gmu_blocked_stream=1 zorn26_gmu_program_bank=1 zorn26_gmu_observe_reset=1 zorn26_gmu_deferred_valid=21 -g0'
PACKAGE = Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/boot-package/verified.json')
SOURCES = {
    'early_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/early-host-wire/result.json'),
    'early_tsan':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/early-tsan-wire/result.json'),
    'callback_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/progress-success-frame-host/result.json'),
    'terminal_host':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/terminal-host/result.json'),
    'late_gate':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/late-gate-host/result.json'),
    'close_reset':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/close-reset-host/result.json'),
    'transport_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/transport-source-closure260.json'),
    'operation_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/close-source-closure260.json'),
    'current_validation':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/final-offline-check260.json'),
    'full_build':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/full-build-review.json'),
    'native_config':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/native-platform-config.json'),
    'segment_layout':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/segment-layout-check.json'),
    'patch_replay':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/patch-replay/result.json'),
    'root_reuse':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/root-reuse260.json'),
    'firmware_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/firmware-input-closure260.json'),
    'retirement_closure':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/additional-retirement-final260.json'),
    'root_layout':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-candidate/layout-and-replay-result.json'),
    'root_composition':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-candidate/root-result.json'),
    'root_delta':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-candidate/delta.json'),
    'policy_clients':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-policy/NativeAdrenoMetal.clients'),
    'policy_job':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v252-early-system-f5bb017ece0045d3a06ec1711a1c8b88/root-policy/org.unixnu.zorn.metal-probe193.plist'),
    'record_decoder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_early252_record.py'),
    'record_envelope':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_lockscreen_touch_cpu_record.py'),
    'progress_decoder':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_early252.py'),
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
    'link_inputs':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/full-link/exact-inputs.json'),
    'source_manifest':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/patches/gpu/ios26-platform-identity260/source-manifest.json'),
    'entry':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_gpu_v260_system_trial.py'),
    'cdc_capture':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/read-zorn-gpu-system260-cdc.py'),
    'camera_entry':Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/capture-zorn-video260.py'),
    'root_window':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/ZornRootWindow26.h'),
    'ufs_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/ZornUfsOwner26.cpp'),
    'cdc_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/ZornUsbCdc26.c'),
    'framebuffer_source':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/MiniIOMobileFramebuffer.cpp'),
    'native_io':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/direct-runtime/ZornGen7AppIo26.cpp'),
    'native_io_header':Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v260-platform-identity-81683386ba0d423d817a2b7d0e1c60f0/direct-runtime/ZornGen7AppIo26.h'),
}
SOURCES['identity_host'] = PACKAGE.parent.parent/'native-identity-host/result.json'
SOURCES['unchanged_driver_bodies'] = PACKAGE.parent.parent/'unchanged-driver-bodies260.json'
CHECKS = ['identity_host','unchanged_driver_bodies','early_host', 'early_tsan', 'callback_host', 'terminal_host', 'late_gate', 'close_reset', 'transport_closure', 'operation_closure', 'current_validation', 'full_build', 'native_config', 'segment_layout', 'patch_replay', 'root_reuse', 'firmware_closure', 'retirement_closure']
ARTIFACTS={'boot','kernel','FAT','fd','ADT','loader','manager','menu','package','record_identity','installed_cohort'}
PROTECTIONS={'primary_GPT','backup_GPT','root_manifest','Data_header','Data_metadata','root_first_page','root_before','root_after'}
TOOLS={'installed_result','adb_binary','fastboot_binary','host_adb_proof'}
EXPECTED=dict(scope=SCOPE,serial='92988a43',product='zorn',slot='a',trial_seconds=300,timeout_seconds=600,retries=0,watchdog_mode=1,accepted_recovery='twrp-or-orangefox',existing_server_only=True,native_log_absolute_lba=49563392,native_log_blocks=1,root_read_only=True,data_read_only=True,transient_boot=True,bootstrap_allowed=False,gpu_firmware_start=True,allow_boot=False)

def require(condition,message):
    if not condition:raise ValueError(message)

def pinned(row):
    p=Path(row['path']);require(p.is_absolute() and not p.is_symlink() and p.is_file() and sha(p)==row['sha256'],'source/check bytes changed: '+str(p))

def validate_package(proof=None):
    proof=load(PACKAGE) if proof is None else proof
    require(proof['version']==260 and proof['run_id']==TAG and proof['identity260_selected'] is True,'260 package identity differs')
    require(proof['boot']['sha256']==BOOT and proof['link']['sha256']==KERNEL and proof['root']['sha256']==ROOT_SHA and proof['pins']['ADT']['sha256']==ADT_SHA and proof['pins']['FD']['sha256']==FD_SHA,'exact260 tuple differs')
    require(proof['root_installed'] is True and proof['root_installation_required'] is False and proof['root_payload_changed'] is False and proof['new_root_or_delta_created'] is False,'reuse installed252 root only')
    require(proof['ordinary_client']=='backboardd' and proof['probe_job_disabled'] is True and proof['physical_native_session_still_exclusive'] is True and proof['multi_context_native_dispatch_implemented'] is True and proof['multiple_logical_member_admission_implemented'] is True and proof['bounded_same_thread_pending_close_continuation_implemented'] is True,'actual shared-context/close scope differs')
    for key in ['Ring_owned_physical_OOB_storage_and_resource_references_implemented','client_independent_physical_authority_implemented','whole_operation_context_lifecycle_implemented']:
        require(proof[key] is True,'current260 operation/physical path missing: '+key)
    require(proof['watchdog_seconds']==300 and proof['recovery_timeout_seconds']==600 and proof['retries']==0 and proof['boot_args']==ARGS,'bounded260 configuration differs')
    for row in [proof['boot'],proof['FAT']]:pinned(row)
    for key in ['kernel','ADT','FD']:
        row=proof['pins'][key];pinned(dict(path=row['archive'],sha256=row['sha256']))
    for key in CHECKS:require(load(SOURCES[key]).get('passed') is True,'current check failed: '+key)
    native=load(SOURCES['native_config']);require(native['CPU_page_bytes']==16384 and native['macros']['ARM_PGSHIFT']=='14','actual CPU16KiB input required')
    closure=load(SOURCES['operation_closure'])
    require(closure['kernel_sha256']==KERNEL and closure['root_sha256']==ROOT_SHA and proof['identity260_closure']['sha256']==sha(SOURCES['operation_closure']),'260 native/source closure differs')
    for key in ['exact_Root_pending_status_before_backend_cleanup','real_pending_fence_scope_exit_revalidated','release_checks_selected_foreign_context_before_outstanding_refusal','bounded_same_close_thread_continuation','no_completed_cleanup_stage_replay','nonpending_Busy_and_release_timeout_never_retried','timeout_or_unknown_resources_remain_pinned','no_async_worker_or_extra_kernel_thread']:
        require(closure[key] is True,'current pending-close source path differs: '+key)
    require(closure['pending_observation_budget_ms']==1000 and closure['maximum_observations_per_pending_stage']==1000,'bounded observation differs')
    for row in closure['checks']:pinned(row)
    evidence=load(SOURCES['current_validation'])
    require(evidence['current_native_objects']==32 and evidence['current_native_source_header_and1398_inputs_match'] is True,'current native closure differs')
    for row in load(PACKAGE.parent.parent/'offline260.json')['checks']:
        pinned(row);require(load(row['path']).get('passed') is True,'current lifecycle test failed')
    transport=load(SOURCES['transport_closure'])
    require(transport['boot_tag']==TAG and transport['kernel_sha256']==KERNEL and transport['wire252_compatible'] is True,'current source transport identity differs')
    for row in transport['sources']+transport['checks']:pinned(row)
    validation=load(SOURCES['current_validation']);require(validation['kernel']['sha256']==KERNEL and validation['boot']['sha256']==BOOT and validation['current_sanitizer_tools_and_sources_match'] is True,'current final offline proof differs')
    pinned(validation['source_manifest']);pinned(validation['evidence'])
    for role,sanitizer in [('early_host','address,undefined'),('early_tsan','thread')]:
        receipt=load(SOURCES[role]);require(receipt['sanitizer']==sanitizer,'early sanitizer not selected')
        for row in receipt['source']:pinned(row)
    for row in load(SOURCES['callback_host'])['actual_sources']:pinned(row)
    for key in ['terminal_host','late_gate']:
        require(load(SOURCES[key])['source_sha256']==sha(SOURCES['cdc_source']),'current terminal/gate source differs: '+key)
    terminal=load(SOURCES['terminal_host']);require(terminal['ASan_UBSan'] and terminal['actual_source_sender_transfer_epcmd_extracted'] and terminal['one_START'] and terminal['unknown_or_inflight_DMA_retained'],'terminal ownership control differs')
    close=load(SOURCES['close_reset']);require(close['ASan_UBSan'] and close['TSan'] and close['actual_recorder_reset_and_getter_used'] and close['reset_before_real_Close_callouts'],'actual close control differs')
    for name,digest in close['sources'].items():require(digest==sha(SOURCES['root_window'].parent/name),'current close source differs: '+name)
    require(load(SOURCES['early_parser_host'])['parser']['sha256']==sha(SOURCES['progress_decoder']) and load(SOURCES['early_record_host'])['parser']['sha256']==sha(SOURCES['record_decoder']),'typed decoder source differs')
    reuse=load(SOURCES['root_reuse']);require(reuse['root']['sha256']==ROOT_SHA and reuse['root_payload_changed'] is False and reuse['new_image_or_delta_created'] is False and reuse['normal_runtime_read_only'] is True,'installed root reuse differs')
    for key in ['actual_parent_result','actual_installation_receipt','parent_composition']:pinned(reuse[key])
    root=load(SOURCES['root_composition']);require(root['sha256']==ROOT_SHA and root['bytes']==34359738368 and root['signature_verified'] and root['filesystem_verified'] and root['monitored_attributes_preserved'] and root['Metal_bundle_files_unchanged'] and root['application_probe_unchanged'],'retained root composition differs')
    allowed={'System/Library/Extensions/NativeAdrenoMetal.clients','System/Library/LaunchDaemons/org.unixnu.zorn.metal-probe193.plist'}
    before,after=root['monitored_before_sha256'],root['monitored_after_sha256'];require(set(before)==set(after) and {k for k in before if before[k]!=after[k]}==allowed,'unrelated root payload differs')
    require(SOURCES['policy_clients'].read_text()=='backboardd'+chr(10) and after['System/Library/Extensions/NativeAdrenoMetal.clients']==sha(SOURCES['policy_clients']),'ordinary client policy differs')
    job=plistlib.loads(SOURCES['policy_job'].read_bytes());require(job==root['launch_job']==dict(root['prior_launch_job'],RunAtLoad=False,Disabled=True) and job['KeepAlive'] is False and after['System/Library/LaunchDaemons/org.unixnu.zorn.metal-probe193.plist']==sha(SOURCES['policy_job']),'competing probe job differs')
    layout=load(SOURCES['root_layout']);require(layout['layout_change'] is False and layout['placement_recomputed_from_Data_end'] and layout['candidate_image']['sha256']==layout['replay_image']['sha256']==ROOT_SHA and layout['proposed_relative_first_lba']==6291712 and layout['proposed_blocks']==8388608 and layout['Data_gap_bytes']==782336 and layout['reserve_after_root_bytes']==8588886016,'retained storage layout differs')
    require(load(SOURCES['full_build'])['kernel_sha256']==KERNEL and proof['link']['inputs']==1398 and proof['link']['undefined_symbols']==0,'complete current native link differs')
    require(proof['link']['exact_inputs']['sha256']==sha(SOURCES['link_inputs']),'exact link manifest differs')
    inputs=load(SOURCES['link_inputs'])
    for row in inputs:pinned(row)
    firmware=load(SOURCES['firmware_closure'])
    require(firmware['kernel_sha256']==KERNEL and firmware['retained_selected_object'] in inputs,'selected K80 firmware object differs')
    for row in firmware['generated_K80_firmware_headers']+firmware['current_sources']+[firmware['recipe'],firmware['parent_closure']]:pinned(row)
    return proof

def validate(path):
    require(not path.is_symlink() and path.resolve()==TRIAL/'bundle.json','canonical260 bundle required')
    bundle=load(path);require(all(type(bundle.get(k)) is type(v) and bundle[k]==v for k,v in EXPECTED.items()),'exact260 trial scope differs')
    pins=bundle['pins'];require(set(pins)==ARTIFACTS|PROTECTIONS|TOOLS|SOURCES.keys(),'complete260 input/protection roles required')
    for role,row in pins.items():
        source,archive=Path(row['path']),Path(row['archive']);pinned(row)
        require(not archive.is_symlink() and archive.is_file() and archive.parent==TRIAL/'archive' and not source.samefile(archive) and sha(archive)==row['sha256'],'independent260 archive differs: '+role)
    require(all(Path(pins[k]['path']).resolve()==v.resolve() for k,v in SOURCES.items()),'260 fixed source path differs')
    proof=validate_package(load(pins['package']['path']))
    require(Path(pins['package']['path'])==PACKAGE and pins['boot']['sha256']==BOOT and pins['kernel']['sha256']==KERNEL and pins['ADT']['sha256']==ADT_SHA and pins['fd']['sha256']==FD_SHA,'260 packaged tuple differs')
    for role,value in {'FAT':proof['FAT']['sha256'],'fd':proof['pins']['FD']['sha256'],'ADT':proof['pins']['ADT']['sha256']}.items():require(pins[role]['sha256']==value,'carrier input differs: '+role)
    for row in proof['FAT_members']:
        role={'BOOTAA64.EFI':'manager','DarwinBoot26.efi':'loader','kernel.macho':'kernel','kernel.macho.adt':'ADT','unixnu.toml':'menu'}[Path(row['FAT_path']).name]
        require(pins[role]['sha256']==row['sha256'],'FAT member differs: '+role)
    menu=tomllib.loads(Path(pins['menu']['path']).read_text());require(len(menu['entry'])==1 and menu['entry'][0]['args']==ARGS and not menu['boot']['connect_all'] and not menu['kits']['autoload'],'single exact260 menu required')
    with Path(pins['FAT']['path']).open('rb') as stream:
        for sector in (0,6):
            stream.seek(sector*512+0x180);mode=struct.pack('<II',1,0xfffffffe)
            require(stream.read(32)==b'ZORNGHWD'+mode+b'ZORNTPWR'+mode,'watchdog/power marker differs')
    installed=load(pins['installed_result']['path']);require(installed['expected_image_sha256']==ROOT_SHA and installed['installed'] is True and installed['protected_metadata_and_fences_unchanged'] is True and installed['phase']=='root-delta-installed-written-blocks-readback-verified' and installed['readback']==dict(scope='written4KiB-root-pages-only',blocks=16,bytes=65536,sha256='d429efd1c52316066e02a4c9800e84a317c2cfda01fb5b03a421a3d438fbea32'),'actual252 installation receipt differs')
    cohort=load(pins['installed_cohort']['path']);require(cohort['package']['sha256']==pins['package']['sha256'] and cohort['root_install_receipt']['sha256']==pins['installed_result']['sha256'] and cohort['boot']['sha256']==BOOT and cohort['root']['sha256']==ROOT_SHA and cohort['system_booted'] is False and cohort['reused_root_from_actual252'] is True and cohort['parent_hardware_result']['sha256']==load(SOURCES['root_reuse'])['actual_parent_result']['sha256'],'260 root reuse cohort differs')
    state=load(CURRENT);require(state['gpu_discovery'].get('current_phone_root_expected_sha256')==ROOT_SHA,'current root identity differs')
    require(load(pins['host_adb_proof']['path'])['adb_sha256']==pins['adb_binary']['sha256'],'existing ADB tool identity differs')
    require(load(pins['record_identity']['path'])['run_id']==TAG,'record artifact identity differs')
    return bundle

def record_result(decoded):
    require(decoded['CPU_samples_pending'] is True and decoded['deferred_CPU_owner_published'] is True,'exact early252 record required')
    return dict(status='recovered-fresh-root-EL0-early-GPU-checkpoint',root_mount_proven=True,PID1_image_activation_proven=True,cpu_online=decoded['cpu_online'],eight_cpus_available=decoded['cpu_online']==8,CPU_samples_in_record_pending=True,early_deferred_CPU_owner_published=True,GPU_started=False,desktop_proven=False,touch_input_delivery_proven=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios26-platform-identity260-trial', action='store_true')
    parser.add_argument('--bundle',
                        type=Path, required=True, dest='bundle')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    bundle = validate(args.bundle)
    if args.check_only:
        print('260 operation-context host inputs verified; no USB or claim')
        return
    if args.admission is None or args.admission.resolve() != TRIAL / 'admission.json':
        parser.error('exact local admission required')
    admission = load(args.admission)
    binding = dict(scope=SCOPE, nonce=TAG, bundle_sha256=sha(args.bundle), boot_sha256=BOOT, allow_boot=True)
    for name in ('owner', 'ready', 'admission'):
        row = admission if name == 'admission' else load(TRIAL / (name + '.json'))
        if any(row.get(k) != v for k, v in binding.items()):
            raise ValueError(f'{name} does not bind the exact 260 operation-context scope')
        if name != 'admission' and sha(TRIAL / (name + '.json')) != admission[name + '_sha256']:
            raise ValueError(f'{name} changed after admission')
    ready=load(TRIAL/'ready.json')
    if (ready.get('host_checks_passed') is not True or ready.get('one_boot') is not True or
            ready.get('timeout_seconds')!=600 or ready.get('watchdog_seconds')!=300 or
            not isinstance(ready.get('hardware_only_pending'),list) or not ready['hardware_only_pending']):
        raise ValueError('260 ready must retain bounded watchdog/return and unresolved hardware conditions')
    for row in ready.get('host_checks',[]):
        if sha(row['path'])!=row['sha256'] or load(row['path']).get('passed') is not True:
            raise ValueError('260 ready host test changed/failed')
    if not ready.get('host_checks'):
        raise ValueError('260 ready requires actual current host receipts')
    state = load(CURRENT)
    if state.get('gpu_discovery', {}).get('current_mode') != 'unattended-phone-connected':
        raise ValueError('unattended phone mode required')
    claim = TRIAL / 'trial/one-shot.claim.json'
    if claim.exists() or claim.is_symlink():
        raise ValueError('260 operation-context trial already consumed')
    probe_existing_adb_listener()
    run(bundle, claim, record_result=record_result)


if __name__ == '__main__':
    main()
