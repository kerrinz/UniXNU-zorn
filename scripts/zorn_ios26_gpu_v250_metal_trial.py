"""Fixed K80 iOS26 journal and Metal trial with protected Recovery return."""
import argparse
from pathlib import Path
import struct
import tomllib

from zorn_ios26_logdirs_boot_trial import (
    CURRENT, STAGE, load, sha, probe_existing_adb_listener, run,
)

HERE = Path(__file__).resolve().parent
BASE = STAGE / 'k80-gpu-v250-metal-trial-9735df98f85745cd9f43a43290398656'
TRIAL = BASE / 'root-trial'
SCOPE = 'single-K80-ios26-gpu-v250-present-window-300s-9735df98'
BOOT = '6ba14e9d32ff6b75fab3548489f610cd0d8a145f68ad64f694b9a546ff1a7ed2'
KERNEL = '52a7b61c88c7b850ec58f37914c6cc39f57c22706991bc276c3b1083d5aff0be'
ADT_SHA = '2d3503001dcb277ba700439285c7766516f86e11dbc9de77cb6c0d30b001554d'
TAG = '9735df98f85745cd9f43a43290398656'
PROBE_TAG = '9735df98f85745cd9f43a43290398656'
ROOT_SHA = '40338c39e91e4932c63271cea073c1eba208080d3356de20a6a7c3593629bb0d'
SOURCES = {
    'camera_entry': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/capture-zorn-video250.py'),
    'camera_binary': Path('/opt/homebrew/bin/ffmpeg'),
    'known_header': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornKnownPresent247.h'),
    'known_parser': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_known247.py'),
    'known_observer_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornApplicationObservation26.inc'),
    'known_window_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornRootWindow26.h'),
    'known_probe_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/userland/ZornMetalProbe193.mm'),
    'known_closure': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/known-source-closure250.json'),
    'known_api_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/known-present-host/result.json'),
    'known_probe_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/present-window-repo-host/result.json'),
    'known_observer_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/observer-program-host/result.json'),
    'known_signed_probe': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/user-probe-launch/build-result.json'),
    'known_root_layout': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/root-candidate/layout-and-replay-result.json'),
    'known_header_rebuild': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/probe-header-closure250.json'),
    'known_profile_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/profile-mode-host/result.json'),
    'surface_header': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornSurfaceBacking246.h'),
    'surface_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/MiniIOSurface.cpp'),
    'surface_vm_header': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/direct-runtime/ZornGen7DirectVm26.h'),
    'surface_vm_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/direct-runtime/ZornGen7DirectVm26.cpp'),
    'surface_submit_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/direct-runtime/ZornGen7DirectSubmit26.cpp'),
    'surface_backing_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/surface-backing-host/result.json'),
    'surface_drop_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/surface-actual-drop-host/result.json'),
    'surface_lifetime_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/surface-lifetime-host/result.json'),
    'surface_layout_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/mapping-layout-host/result.json'),
    'surface_baseline_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/surface-source-provenance/result.json'),
    'surface_composition_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/known-terminal-composition.json'),
    'surface_success_callback_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/progress-success-frame-host/result.json'),
    'surface_full_build_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/full-build-review.json'),
    'surface_link_inputs': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/full-link/exact-inputs.json'),
    'capture_verdict_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/progress-capture-check250.json'),
    'present_sources_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/surface-source-closure250.json'),
    'present_framebuffer_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/MiniIOMobileFramebuffer.cpp'),
    'present_host_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornGen7HostRing26.cpp'),
    'present_cdc_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornUfsOwner26.cpp'),
    'present_header': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornPresentTrace245.h'),
    'present_parser': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_surface246.py'),
    'present_trace_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/present-trace-host/result.json'),
    'present_ledger_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/present-ledger-host/result.json'),
    'present_frame_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/known-frame-body-host/result.json'),
    'present_parser_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/known-stream-host/result.json'),
    'present_callback_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/progress-frame-host/result.json'),
    'present_patch_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/patch-replay/result.json'),
    'present_PTY_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/large-PTY-capture-check250.json'),
    'clock_client': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/direct-runtime/ZornGen7DirectClient26.cpp'),
    'clock_vm': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/direct-runtime/ZornGen7DirectVm26.cpp'),
    'clock_submit': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/direct-runtime/ZornGen7DirectSubmit26.cpp'),
    'clock_test': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/clock-lifetime-regression/result.json'),
    'clock_provenance': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/clock-provenance/result.json'),
    'close_source_owner': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornGen7HostRing26.cpp'),
    'close_source_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/close-source-check/result.json'),
    'close_reset_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/direct-runtime/ZornGen7AppIo26.cpp'),
    'close_reset_host': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/close-reset-host/result.json'),
    'terminal_session_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/houji_recovery26.c'),
    'terminal_session_host': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/terminal-session-host/result.json'),
    'terminal_session_parsercheck': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/terminal-session-parser/result.json'),
    'terminal_session_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_application241.py'),
    'client_source_header': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornClientTrace240.h'),
    'client_source_host': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/client-source-host/result.json'),
    'client_source_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_source242.py'),
    'late_panic_gate': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/late-gate-host/result.json'),
    'panic_ram_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/pe_init.c'),
    'panic_ram_host': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/panic-init-host/result.json'),
    'panic_ram_startup': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v247-known-present-c0bed9d9c79d4aeca33d0ad509f2984d/startup-source-audit/result.json'),
    'panic_ram_segments': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/segment-layout-check.json'),
    'panic_identity_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/identity-dependency-check.json'),
    'panic_wire_header': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornPanicPacket236.h'),
    'panic_format_catalog': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/data/k80-panic-formats232-f9fd63efaf9448ad923c58b1cfb477f5.json'),
    'progress_format_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress232.py'),
    'progress_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress236.py'),
    'progress_device_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress229.py'),
    'progress_previous_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress226.py'),
    'progress_request_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress225.py'),
    'progress_control_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress223.py'),
    'progress_mapping_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress222.py'),
    'progress_return_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress217.py'),
    'progress_callback_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress216.py'),
    'progress_base_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_progress211.py'),
    'entry': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_gpu_v250_metal_trial.py'),
    'preparation_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_prepare191.py'),
    'application_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_metal194.py'),
    'fixed_builder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/build-zorn-debug.py'),
    'fixed_runner': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/run-zorn-debug.py'),
    'transport_core': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_ios26_logdirs_boot_trial.py'),
    'device_helpers': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_gpu_resource_trial.py'),
    'recovery_identity': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_recovery_identity.py'),
    'record_helpers': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/zorn_gpu_ios26_platform_record.py'),
    'record_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_ui_census227_record.py'),
    'record_legacy_census_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_ui_census_record.py'),
    'percore_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_lockscreen_percore_record.py'),
    'cdc_capture': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/read-zorn-gpu-metal250-cdc.py'),
    'gpu_base_decoder': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_s2cr_cdc_record.py'),
    'record_envelope': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_lockscreen_touch_cpu_record.py'),
    'journal_closure': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/journal-source-closure250.json'),
    'journal_parser': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_journal248.py'),
    'journal_header': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornApplicationJournal248.h'),
    'journal_store': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornJournalStore248.h'),
    'journal_wire': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornJournalWire248.h'),
    'journal_capture_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornJournalCapture248.inc'),
    'journal_stderr_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornApplicationStderr26.inc'),
    'journal_syscall_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/sys_generic.c'),
    'journal_exit_source': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/kern_exit.c'),
    'journal_host': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v248-log-journal-0b6e1744c27f410a9a7fc1030cf45206/journal-host-r3/result.json'),
    'journal_tsan': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v248-log-journal-0b6e1744c27f410a9a7fc1030cf45206/journal-tsan/result.json'),
    'journal_callback': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/progress-success-frame-host/result.json'),
    'journal_capture_verdict': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/progress-capture-check250.json'),
    'journal_PTY': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/large-PTY-capture-check250.json'),
    'journal_source_delta': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/source-delta-review.json'),
    'journal_exit_provenance': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/exit-source-provenance/result.json'),
    'journal_native_config': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/native-platform-config.json'),
    'journal_raw_sender': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/terminal-host/result.json'),
    'journal_patch_replay': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/patch-replay/result.json'),
    'journal_manifest': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/patches/diagnostics/ios26-present-window250/source-manifest.json'),
    'burst_closure': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/burst-source-closure.json'),
    'burst_parser': Path('/Volumes/macData/projects/ios-zorn/UniXNU-zorn/scripts/inspect_ios26_gpu_burst249.py'),
    'burst_function_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/present-window-repo-host/result.json'),
    'burst_parser_check': Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-gpu-v250-present-window-9735df98f85745cd9f43a43290398656/burst-parser-host/result.json'),
}

ARTIFACTS = {'boot', 'kernel', 'FAT', 'fd', 'ADT', 'loader', 'manager', 'menu', 'package', 'record_identity', 'installed_cohort'}
PROTECTIONS = {'primary_GPT', 'backup_GPT', 'root_manifest', 'Data_header', 'Data_metadata',
               'root_first_page', 'root_before', 'root_after'}
TOOLS = {'installed_result', 'adb_binary', 'fastboot_binary', 'host_adb_proof'}
EXPECTED = dict(scope=SCOPE, serial='92988a43', product='zorn', slot='a',
                trial_seconds=300, timeout_seconds=600, retries=0, watchdog_mode=1,
                accepted_recovery='twrp-or-orangefox', existing_server_only=True,
                native_log_absolute_lba=49563392, native_log_blocks=1, root_read_only=True,
                data_read_only=True, transient_boot=True, bootstrap_allowed=False,
                gpu_firmware_start=True, allow_boot=False)


def validate(path):
    if path.is_symlink() or path.resolve() != TRIAL / 'bundle.json':
        raise ValueError('canonical CPU touch scope required')
    bundle = load(path)
    if any(type(bundle.get(k)) is not type(v) or bundle[k] != v for k, v in EXPECTED.items()):
        raise ValueError('CPU touch trial settings differ')
    pins = bundle['pins']
    if set(pins) != ARTIFACTS | PROTECTIONS | TOOLS | SOURCES.keys():
        raise ValueError('CPU touch trial inputs incomplete')
    for role, row in pins.items():
        source, archive = Path(row['path']), Path(row['archive'])
        if (not source.is_absolute() or source.is_symlink() or archive.is_symlink()
                or archive.parent != TRIAL / 'archive' or source.samefile(archive)
                or sha(source) != row['sha256'] or sha(archive) != row['sha256']):
            raise ValueError(f'CPU touch input differs: {role}')
    if any(Path(pins[k]['path']).resolve() != p.resolve() for k, p in SOURCES.items()):
        raise ValueError('fixed runner source differs')
    if pins['boot']['sha256'] != BOOT or pins['kernel']['sha256'] != KERNEL:
        raise ValueError('exact CPU touch boot and kernel required')
    proof = load(pins['package']['path'])
    journal=load(pins['journal_closure']['path'])
    journal_roles=['journal_header','journal_store','journal_wire','journal_capture_source',
                   'known_observer_source','journal_stderr_source','journal_syscall_source',
                   'journal_exit_source','present_cdc_source']
    # The stderr adapter has its own actual source path in the closure; verify
    # every file SHA before applying the explicit expected ordered bindings.
    for row in journal['sources']+journal['checks']:
        if sha(row['path']) != row['sha256']:
            raise ValueError('journal248 source or test bytes changed')
    expected_sources=[pins[k]['sha256'] for k in journal_roles]
    if (proof.get('journal248_selected') is not True or
            proof['journal248_closure']['sha256']!=pins['journal_closure']['sha256'] or
            proof['journal248_parser']['sha256']!=pins['journal_parser']['sha256'] or
            journal.get('passed') is not True or journal['kernel_sha256']!=KERNEL or
            journal['root_sha256']!=ROOT_SHA or journal['program_tag']!=PROBE_TAG or
            journal.get('root_payload_changed') is not True or
            journal.get('legacy_loss_rule_unchanged') is not True or
            journal['parser']['sha256']!=pins['journal_parser']['sha256'] or
            [x['sha256'] for x in journal['sources']]!=expected_sources):
        raise ValueError('journal248 exact sources/kernel/root/parser binding differs')
    for role in ['journal_host','journal_tsan','journal_callback','journal_capture_verdict',
                 'journal_PTY','journal_source_delta','journal_exit_provenance',
                 'journal_native_config','journal_raw_sender','journal_patch_replay']:
        if load(pins[role]['path']).get('passed') is not True:
            raise ValueError('journal248 current check failed: '+role)
    config=load(pins['journal_native_config']['path'])
    if (config.get('CPU_page_bytes')!=16384 or
            config.get('generic_format2_profile_used') is not False or
            config.get('macros',{}).get('ARM_PGSHIFT')!='14'):
        raise ValueError('journal248 actual native page configuration differs')
    exit_proof=load(pins['journal_exit_provenance']['path'])
    if exit_proof.get('actual_recipe_rebuild_byte_equal') is not True:
        raise ValueError('journal248 original selected exit recipe was not reproduced')
    if (proof['current_offline_package']['sha256']!=sha(SOURCES['journal_closure'].parent/'boot-package/verified.json') or
            proof.get('admission_only_refresh') is not True or
            sorted(proof['changed_FAT_members'])!=['EFI/UniXNU/Payloads/kernel.macho','EFI/UniXNU/Payloads/kernel.macho.adt']):
        raise ValueError('journal248 frozen complete package or changed-member scope differs')

    burst=load(pins['burst_closure']['path'])
    if (proof.get('burst249_selected') is not True or
            proof['burst249_closure']['sha256']!=pins['burst_closure']['sha256'] or
            proof['burst249_parser']['sha256']!=pins['burst_parser']['sha256'] or
            burst.get('passed') is not True or burst['kernel_sha256']!=KERNEL or
            burst['root_sha256']!=ROOT_SHA or burst['program_tag']!=PROBE_TAG or
            burst['source']['sha256']!=pins['known_probe_source']['sha256'] or
            burst['signed_probe']['sha256']!=pins['known_signed_probe']['sha256'] or
            burst.get('new_loop_frames')!=120 or burst.get('deadline_between_calls_seconds')!=20 or
            burst['parser']['sha256']!=pins['burst_parser']['sha256'] or
            load(pins['burst_function_check']['path']).get('passed') is not True or
            load(pins['burst_parser_check']['path']).get('passed') is not True):
        raise ValueError('burst249 exact loop/source/parser/kernel/root scope differs')

    source_roles=['present_framebuffer_source','present_host_source','present_cdc_source','present_header',
                  'surface_source','surface_header','surface_vm_header','surface_vm_source','surface_submit_source']
    check_roles=['surface_backing_check','surface_drop_check','surface_lifetime_check','surface_layout_check',
                 'surface_baseline_check','present_frame_check','present_parser_check','surface_composition_check',
                 'present_callback_check','surface_success_callback_check','present_patch_check','present_PTY_check']
    closure=load(pins['present_sources_check']['path'])
    if (closure.get('passed') is not True or closure.get('kernel_sha256') != KERNEL or
            [x['sha256'] for x in closure['sources']] != [pins[k]['sha256'] for k in source_roles] or
            [x['sha256'] for x in closure['checks']] != [pins[k]['sha256'] for k in check_roles] or
            closure['effective_header_review']['sha256'] != pins['surface_full_build_check']['sha256']):
        raise ValueError('surface246 actual source/object/header/test closure differs')
    selected={x['sha256'] for x in load(pins['surface_link_inputs']['path'])}
    for row in closure['objects']:
        for key in ['object','recipe','dependencies']:
            if sha(row[key]['path']) != row[key]['sha256']:
                raise ValueError('surface246 current compiled input differs: '+key)
        if row['object']['sha256'] not in selected:
            raise ValueError('surface246 compiled object not in actual full link')
    review=load(pins['surface_full_build_check']['path'])
    if review.get('passed') is not True or review.get('kernel_sha256') != KERNEL:
        raise ValueError('surface246 full build review differs')
    if (proof.get('surface246_selected') is not True or proof.get('presentation245_selected') is not False or
            proof['surface246_header']['sha256'] != pins['surface_header']['sha256'] or
            proof['surface246_parser']['sha256'] != pins['present_parser']['sha256'] or
            proof['surface246_closure']['sha256'] != pins['present_sources_check']['sha256']):
        raise ValueError('surface246 source and schema2 parser selection differs')
    for role in check_roles+['present_trace_check','present_ledger_check']:
        if load(pins[role]['path']).get('passed') is not True:
            raise ValueError('surface246 host check differs: '+role)
    if [x['sha256'] for x in proof['surface246_checks']] != [pins[k]['sha256'] for k in check_roles]:
        raise ValueError('surface246 host receipt binding differs')

    known=load(pins['known_closure']['path'])
    check_roles=['known_api_check','known_probe_check','known_observer_check','present_frame_check',
                 'present_parser_check','surface_composition_check','capture_verdict_check','present_PTY_check']
    # Capture verdict uses the original envelope and raw panic checks,not GPU success.
    if (proof.get('known247_selected') is not True or
            proof['known247_header']['sha256'] != pins['known_header']['sha256'] or
            proof['known247_parser']['sha256'] != pins['known_parser']['sha256'] or
            proof['known247_closure']['sha256'] != pins['known_closure']['sha256'] or
            known.get('passed') is not True or known['kernel_sha256'] != KERNEL or known['root_sha256'] != ROOT_SHA or
            known['source_closure']['sha256'] != pins['present_sources_check']['sha256'] or
            known['required_boot_arg'] != 'zorn26_software_accelerator=2' or
            [x['sha256'] for x in known['sources']] != [pins[k]['sha256'] for k in
                ['known_header','known_observer_source','known_window_source','known_probe_source']] or
            known['signed_probe']['sha256'] != pins['known_signed_probe']['sha256'] or
            known['layout']['sha256'] != pins['known_root_layout']['sha256']):
        raise ValueError('known247 actual source/root/probe/selected mode differs')
    if ([x['sha256'] for x in known['checks']] != [pins[k]['sha256'] for k in check_roles] or
            [x['sha256'] for x in proof['known247_checks']] != [pins[k]['sha256'] for k in check_roles]):
        raise ValueError('known247 check receipt binding differs')
    for role in check_roles+['known_header_rebuild','known_profile_check']:
        if load(pins[role]['path']).get('passed') is not True:
            raise ValueError('known247 host check differs: '+role)
    probe=load(pins['known_signed_probe']['path'])
    if (probe.get('signed') is not True or probe.get('signature_verified') is not True or
            probe.get('program_tag') != PROBE_TAG or probe.get('frames') != 120 or
            probe.get('no_SwapWait') is not True or probe.get('queries_per_frame') != 200 or
            probe.get('application_deadline_seconds') != 20 or
            probe.get('no_native_GPU_backend_change') is not True or
            probe.get('entitlements_unchanged_from_247') is not True or
            load(pins['known_header_rebuild']['path']).get('actual_selected_headers_verified') is not True or
            load(pins['known_header_rebuild']['path']).get('signed_binary_equals_root') is not True):
        raise ValueError('known247 actual signed probe/header/lifetime differs')
    # Creation-time offline package never claimed this new root installed.
    # The independently verified actual250 installation receipt follows below.
    if (proof.get('root_installation_required') is not True or
            proof.get('root_installation_pending') is not True or
            proof.get('root_installed_delta_receipt') is not None or
            proof.get('preexisting_root_verified_by_written_page_receipt') is not False):
        raise ValueError('new250 offline root/independent installation scope differs')

    if (proof.get('clock_lifetime244_selected') is not True or
            proof['clock_lifetime244_test']['sha256'] != pins['clock_test']['sha256'] or
            load(pins['clock_test']['path']).get('passed') is not True or
            load(pins['clock_provenance']['path']).get('passed') is not True or
            [x['sha256'] for x in proof['clock_lifetime244_sources']] !=
            [pins[x]['sha256'] for x in ['clock_client','clock_vm','clock_submit']]):
        raise ValueError('clock source lifetime repair binding differs')

    if (proof['boot']['sha256'] != BOOT or proof['root']['sha256'] != ROOT_SHA
            or proof['touch_continuous'] is not True or proof['touch_checkpoint_seconds_after_pid1'] != 45 or proof.get('gpu_checkpoint45_selected') is not True or proof.get('touch150_qualification_transferred') is not False
            or proof.get('pre_Metal_delay_seconds') != 0 or proof.get('diagnostic_wait_unselected') is not True
            or proof.get('terminal_source_macro233_selected') is not True
            or proof.get('terminal_source_format232_selected') is not True
            or proof.get('terminal_source_context231_selected') is not True
            or proof.get('terminal_CDC_source_selected') is not True or proof.get('terminal_wire_bytes') is not None
            or proof.get('terminal_one_packet_max_bytes') != 409600 or proof.get('terminal_within_39frame529408B_budget') is not True
            or proof.get('ram_panic238_selected') is not True
            or proof.get('terminal_identity237_selected') is not True
            or proof.get('terminal_raw_panic236_selected') is not True or proof.get('terminal_wire_limit_bytes') != 529408
            or proof.get('terminal_DMA_bytes') != 540672
            or proof['cpu_accounting_samples_after_pid1_seconds'] != [25, 45]
            or proof['no_home_button_adt'] is not True
            or proof['pins']['ADT']['sha256'] != ADT_SHA
            or not proof['WDT1_markers_both_present'] or not proof['actual_file_loader_parser_pass']):
        raise ValueError('carrier proof differs')
    source_check=proof['terminal_source_check']
    if (sha(source_check['path'])!=source_check['sha256'] or
            load(source_check['path'])['catalog']['sha256']!=pins['panic_format_catalog']['sha256']):
        raise ValueError('kernel source format catalog differs from decoder catalog')
    if load(source_check['path'])['new_packet_header']['sha256'] != pins['panic_wire_header']['sha256']:
        raise ValueError('kernel raw panic wire header differs from bound source')
    if proof['terminal_identity_check']['sha256'] != pins['panic_identity_check']['sha256']:
        raise ValueError('actual identity dependency check differs')
    if (load(source_check['path'])['added_source']['sha256'] != pins['panic_ram_source']['sha256']
            or proof['ram_panic238_source_check']['sha256'] != source_check['sha256']
            or proof['ram_panic238_host_check']['sha256'] != pins['panic_ram_host']['sha256']):
        raise ValueError('RAM panic source or validation binding differs')
    if not all(load(pins[k]['path']).get('passed') is True for k in
               ('panic_ram_host','panic_ram_startup','panic_ram_segments')):
        raise ValueError('RAM panic offline checks incomplete')
    if (proof.get('late_panic239_selected') is not True or
            proof['late_panic239_gate_check']['sha256'] != pins['late_panic_gate']['sha256'] or
            load(pins['late_panic_gate']['path']).get('passed') is not True or
            load(pins['late_panic_gate']['path']).get('source_sha256') != sha(Path('/Volumes/macData/projects/ios-zorn/out/zorn/ios26-feasibility-20261107/source/os/ios26/gpu-v250-present-window-9735df98f85745cd9f43a43290398656/ZornUsbCdc26.c'))):
        raise ValueError('late panic initialization gate differs')
    if (proof.get('source_client240_selected') is not True or
            proof['source_client240_host']['sha256'] != pins['client_source_host']['sha256'] or
            proof['source_client240_header']['sha256'] != pins['client_source_header']['sha256'] or
            load(pins['client_source_host']['path']).get('passed') is not True):
        raise ValueError('source client milestone binding differs')
    if (proof.get('terminal_session241_selected') is not True or
            proof['terminal_session241_source']['sha256'] != pins['terminal_session_source']['sha256'] or
            proof['terminal_session241_host']['sha256'] != pins['terminal_session_host']['sha256'] or
            proof['terminal_session241_parser']['sha256'] != pins['terminal_session_parsercheck']['sha256'] or
            load(pins['terminal_session_host']['path']).get('passed') is not True or
            load(pins['terminal_session_parsercheck']['path']).get('passed') is not True):
        raise ValueError('terminal application snapshot binding differs')
    if (proof.get('close_source242_selected') is not True or
            proof['close_source242_owner']['sha256'] != pins['close_source_owner']['sha256'] or
            proof['close_source242_check']['sha256'] != pins['close_source_check']['sha256'] or
            proof['close_source242_reset_source']['sha256'] != pins['close_reset_source']['sha256'] or
            proof['close_source242_reset_host']['sha256'] != pins['close_reset_host']['sha256'] or
            load(pins['close_source_check']['path']).get('passed') is not True or
            load(pins['close_reset_host']['path']).get('passed') is not True):
        raise ValueError('latest-close source milestone binding differs')
    reset = load(pins['close_reset_host']['path'])
    if any(reset['sources'][name] != pins[role]['sha256'] for name, role in
           [('ZornGen7HostRing26.cpp','close_source_owner'),
            ('direct-runtime/ZornGen7AppIo26.cpp','close_reset_source'),
            ('ZornClientTrace240.h','client_source_header')]):
        raise ValueError('latest-close reset source test differs')





    for role, value in {'FAT': proof['FAT']['sha256'], 'fd': proof['pins']['FD']['sha256'],
                        'ADT': proof['pins']['ADT']['sha256']}.items():
        if pins[role]['sha256'] != value:
            raise ValueError(f'carrier input differs: {role}')
    for row in proof['FAT_members']:
        role = {'BOOTAA64.EFI': 'manager', 'DarwinBoot26.efi': 'loader',
                'kernel.macho': 'kernel', 'kernel.macho.adt': 'ADT',
                'unixnu.toml': 'menu'}[Path(row['FAT_path']).name]
        if pins[role]['sha256'] != row['sha256']:
            raise ValueError(f'FAT member differs: {role}')
    menu = tomllib.loads(Path(pins['menu']['path']).read_text())
    if len(menu['entry']) != 1 or menu['entry'][0]['args'] != proof['boot_args']:
        raise ValueError('single CPU touch menu entry required')
    tokens = menu['entry'][0]['args'].split()
    required = {'zorn26_touch=1', 'zorn26_touch_pacing=1', 'zorn26_touch_continuous=1',
                'zorn26_touch_record=1', 'zorn26_cpu_presenter=1', 'zorn_wdt=1',
                'zorn26_prearmed_recovery=1', 'zorn26_trial_seconds=300'}
    if tokens != ['rd=md0', '-v', 'keepsyms=1', 'houji_native_root=1', 'zorn26_root=1', 'zorn26_installed_root_trial=1', 'zorn_wdt=1', 'zorn26_prearmed_recovery=1', 'zorn26_trial_seconds=300', 'zorn26_cpu_presenter=1', 'zorn26_software_accelerator=2', 'sample=0', 'sb_wallpaper=0', 'zorn26_touch=1', 'zorn26_touch_pacing=1', 'zorn26_touch_continuous=1', 'zorn26_touch_record=1', 'zorn26_gpu_board_stage=1', 'zorn26_owned_clocks=1', 'zorn26_gpu_provider_claim=1', 'zorn26_commanddb_resources=1', 'zorn26_commanddb_resources_only=1', 'zorn26_rsc_managed=1', 'zorn26_clock_prefix=1', 'zorn26_domain_prefix=1', 'zorn26_register_maps=1', 'zorn26_gpu_guarded_maps=1', 'zorn26_gpu_guarded_smmu_id=1', 'zorn26_gpu_guarded_smmu_reserve=1', 'zorn26_gpu_smmu_context_read=1', 'zorn26_gpu_guarded_gmu_clocks=1', 'zorn26_gpu_guarded_cx_timer=1', 'zorn26_gpu_cdc=1', 'zorn26_gpu_cpu_memory_prep=1', 'zorn26_gpu_gmu_context_image=1', 'zorn26_gpu_gmu_direct_seed=1', 'zorn26_gpu_masked_global_irq=1', 'zorn26_smmu_active_faults=1', 'zorn26_gmu_context_irq=1', 'zorn26_gmu_blocked_stream=1', 'zorn26_gmu_program_bank=1', 'zorn26_gmu_observe_reset=1', 'zorn26_gmu_deferred_valid=21', '-g45'] or not required.issubset(tokens) or any(arg.startswith(('zorn26_userland_progress',
                                                            'zorn26_touch_limit')) for arg in tokens):
        raise ValueError('exact continuous touch and CPU presenter selection required')
    with Path(pins['FAT']['path']).open('rb') as stream:
        for sector in (0, 6):
            stream.seek(sector * 512 + 0x180)
            mode = struct.pack('<II', 1, 0xfffffffe)
            if stream.read(32) != b'ZORNGHWD' + mode + b'ZORNTPWR' + mode:
                raise ValueError('watchdog or FT3683 power marker differs')
    installed = load(pins['installed_result']['path'])
    if (installed['expected_image_sha256'] != ROOT_SHA or installed['installed'] is not True
            or installed['protected_metadata_and_fences_unchanged'] is not True
            or installed['phase'] != 'root-delta-installed-written-blocks-readback-verified'
            or installed['readback'] != dict(scope='written4KiB-root-pages-only', blocks=58,
                bytes=237568, sha256='dc58e53affc16cfa25b370a3f34b8e67ff0d9db5bc83ea72d5fd943f19767a23')):
        raise ValueError('CPU baseline root delta receipt differs')
    cohort=load(pins['installed_cohort']['path'])
    if (cohort['package']['sha256']!=pins['package']['sha256'] or
            cohort['root_install_receipt']['sha256']!=pins['installed_result']['sha256'] or
            cohort['boot']['sha256']!=BOOT or cohort['root']['sha256']!=ROOT_SHA or
            cohort['system_booted'] is not False):
        raise ValueError('exact installed root/package cohort differs')
    if proof['application_probe_run_id'] != PROBE_TAG:
        raise ValueError('exact signed IOSurface application program identity differs')
    current=load(CURRENT)
    if current['gpu_discovery'].get('current_phone_root_expected_sha256')!=ROOT_SHA:
        raise ValueError('current root identity differs')
    if load(pins['host_adb_proof']['path'])['adb_sha256'] != pins['adb_binary']['sha256']:
        raise ValueError('ADB identity differs')
    if load(pins['record_identity']['path'])['run_id'] != TAG:
        raise ValueError('artifact ID differs')
    return bundle


def record_result(decoded):
    if decoded['late_ui'].get('checkpoint45_selected') is not True or decoded['late_ui']['sample_seconds_after_pid1'] != 45:
        raise ValueError('recorded GPU checkpoint45 selection required')
    return dict(status='recovered-fresh-FT3683-percore-snapshot', root_mount_proven=True,
                PID1_image_activation_proven=True, cpu_online=decoded['cpu_online'],
                eight_cpus_available=decoded['cpu_online'] == 8,
                continuous_polling_observed=decoded['continuous_polling_observed'],
                all_eight_executed_work=decoded['all_eight_executed_work'],
                gpu_snapshot=decoded['gpu_snapshot'], context_reads_complete=decoded['context_reads_complete'], gmu_clock_complete=decoded['gmu_clock_complete'], endpoint_reservation_complete=decoded['endpoint_reservation_complete'],
                cx_timer_complete=decoded.get('cx_timer_complete',False), cx_timer_raw=decoded.get('cx_timer_raw'), cx_timer_samples=decoded.get('cx_timer_samples'), cx_timer_assessment=decoded.get('cx_timer_assessment'), gmu_ahb_raw=decoded.get('gmu_ahb_raw'),
                inactive_context=decoded.get('inactive_context'), global_irq=decoded.get('global_irq'), global_fault_control=decoded.get('global_fault_control'), context_fault_irq=decoded.get('context_fault_irq'), blocked_stream=decoded.get('blocked_stream'), bank_programming=decoded.get('bank_programming'), reset_observation=decoded.get('reset_observation'), late_ui=decoded['late_ui'], touch_input_delivery_proven=False, lockscreen_proven=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',
                        type=Path, required=True, dest='bundle')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--admission', type=Path)
    args = parser.parse_args()
    bundle = validate(args.bundle)
    if args.check_only:
        print('CPU touch host inputs verified; no USB or claim')
        return
    if args.admission is None or args.admission.resolve() != TRIAL / 'admission.json':
        parser.error('exact local admission required')
    admission = load(args.admission)
    binding = dict(scope=SCOPE, nonce=TAG, bundle_sha256=sha(args.bundle), boot_sha256=BOOT, allow_boot=True)
    for name in ('owner', 'ready', 'admission'):
        row = admission if name == 'admission' else load(TRIAL / (name + '.json'))
        if any(row.get(k) != v for k, v in binding.items()):
            raise ValueError(f'{name} does not bind the exact CPU touch scope')
        if name != 'admission' and sha(TRIAL / (name + '.json')) != admission[name + '_sha256']:
            raise ValueError(f'{name} changed after admission')
    ready=load(TRIAL/'ready.json')
    if (ready.get('host_checks_passed') is not True or ready.get('one_boot') is not True or
            ready.get('timeout_seconds')!=600 or ready.get('watchdog_seconds')!=300 or
            not isinstance(ready.get('hardware_only_pending'),list) or not ready['hardware_only_pending']):
        raise ValueError('248 ready must retain bounded watchdog/return and unresolved hardware conditions')
    for row in ready.get('host_checks',[]):
        if sha(row['path'])!=row['sha256'] or load(row['path']).get('passed') is not True:
            raise ValueError('248 ready host test changed/failed')
    if not ready.get('host_checks'):
        raise ValueError('248 ready requires actual current host receipts')
    state = load(CURRENT)
    if state.get('gpu_discovery', {}).get('current_mode') != 'unattended-phone-connected':
        raise ValueError('unattended phone mode required')
    claim = TRIAL / 'trial/one-shot.claim.json'
    if claim.exists() or claim.is_symlink():
        raise ValueError('CPU touch trial already consumed')
    probe_existing_adb_listener()
    run(bundle, claim, record_result=record_result)


if __name__ == '__main__':
    main()
