#!/usr/bin/env python3
"""Build/package a zorn diagnostic image; boot only after every step succeeds."""
import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "UniXNU"
OUT = ROOT / "out/zorn"
MANIFEST = OUT / "boot.inputs.json"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main():
    from zorn_session_guard import check_deadline, minimum_gui_recovery_timeout
    check_deadline()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boot", action="store_true", help="run the serial-pinned recovery loop after packaging")
    parser.add_argument('--data-profile',choices=('512m','8g'),default='512m',help='select exact seed/store geometry; no implicit reset')
    parser.add_argument('--fresh-data',action='store_true',help='explicit first initialization of installed8GiBData; no oldData migration')
    parser.add_argument("--smp-preflight", type=int, choices=(0, 8), default=0,
                        help="bounded eight-core hardware qualification before root/Data publication")
    parser.add_argument("--smp-continue",action="store_true",help="continue into retained dim CPU GUI only after all eight-core checks pass")
    parser.add_argument("--defconfig", choices=("zorn_defconfig", "zorn_ramdata_defconfig", "zorn_display_defconfig", "zorn_union_defconfig", "zorn_library_defconfig"),
                        default="zorn_defconfig", help="select the qualified UFS baseline or volatile Data experiment")
    parser.add_argument("--display-mode", type=int, choices=(1, 2, 3), default=1,
                        help="display profile: initialize/release (1), publish (2), CPU presentation (3)")
    parser.add_argument("--memory-mib", type=int, help="request a derived UEFI-owned memory window (256..8192 MiB)")
    parser.add_argument("--gui-watch", action="store_true", help="bounded passive launchd/SpringBoard/backboardd thread observations")
    parser.add_argument("--gui-user-stacks", action="store_true", help="bounded original-VM reads of the first GUI thread's frame chain; requires GUI watch/watchdog")
    parser.add_argument("--gui-kernel-stacks", action="store_true", help="prefer bounded CPU0 retained kernel stacks; otherwise keep original user frame reads")
    parser.add_argument("--gui-runnable-kernel-stacks", action="store_true", help="also inspect referenced, non-current runnable kernel contexts; explicit CPU0 diagnostic")
    parser.add_argument("--gui-launchservices", action="store_true", help="observe lsd in place of launchd; requires --gui-user-stacks")
    parser.add_argument("--gui-service-thread", type=int, default=0, help="first lsd thread ordinal to sample (0..63); requires --gui-launchservices")
    parser.add_argument("--gui-backboard-thread", type=int, default=0, help="first backboardd thread ordinal to sample (0..63); requires --gui-user-stacks")
    parser.add_argument("--development-wifi-identity", action="store_true", help="local development MAC in ADT for MobileGestalt queries; no networking driver")
    parser.add_argument("--reuse-kernel-control", type=Path, help="reuse an archived identical GUI control kernel for the development Wi-Fi ADT-only trial")
    parser.add_argument("--data-permissions", action="store_true", help="restore verified template uid/gid/mode on existing RAM Data paths before launchd")
    parser.add_argument("--keystore-state", action="store_true", help="upstream AppleKeyStoreState for volatile unprotected RAM Data only")
    parser.add_argument("--shared-data-volume", action="store_true", help="tell original APFS/user management to use the one RAM Data volume")
    parser.add_argument("--data-store-mode", type=int, choices=(0, 1, 2), default=0,
                        help="Data overlay: off (0), readonly probe (1), reserved write-through window (2)")
    parser.add_argument("--retained-data", action="store_true", help="require and read existing initialization marker; preserve OS-managed Data metadata")
    parser.add_argument("--quiet-gui", action="store_true", help="keep fixed GUI diagnostics while omitting syscall-write and verbose exec capture")
    parser.add_argument("--brightness-mode", type=int, choices=(0, 1, 2, 3, 4), default=0,
                        help="K80 brightness: off (0), registers (1), DCS read (2), low limit/readback (3), short dim test (4)")
    parser.add_argument("--touch-probe", action="store_true", help="short read-only K80 touch/display handoff inventory; no touch events")
    parser.add_argument("--touch-handoff", action="store_true", help="opt in to K80 native UEFI L14/L12 and SE clock votes; requires touch probe")
    parser.add_argument("--touch-identify", action="store_true", help="bounded GPIO SPI FT3683 ID/firmware reads; requires touch probe and handoff")
    parser.add_argument("--touch-frames", action="store_true", help="bounded 20-second raw FT3683 frame reads after ID; no HID")
    parser.add_argument("--touch-full", action="store_true", help="complete 3120-byte raw touch frame and visible cue; requires --touch-frames")
    parser.add_argument("--touch-calibrate", action="store_true", help="same-boot untouched baseline plus active matrix; requires --touch-full")
    parser.add_argument("--touch-runtime", action="store_true", help="experimental long-lived calibrated FT3683 digitizer for the CPU GUI")
    parser.add_argument("--touch-fast-poll", action="store_true", help="explicit32-byte cooperation/20ms poll; requires trace and qualified eight-core runtime")
    parser.add_argument("--touch-trace", action="store_true", help="bounded coordinate/phase trace in unused GUI stack slots; excludes stack samplers")
    parser.add_argument("--touch-edges", action="store_true", help="opt in to this digitizer's qualified original-event edge dispatch adapter")
    parser.add_argument("--touch-kernel-parser", action="store_true", help="device-only personality for the qualified original kernel HID parser")
    parser.add_argument("--hid-family", action="store_true", help="explicitly load original HID OS services without a touch/input device")
    parser.add_argument("--minimal-services", action="store_true", help="temporary upstream launchd policy for unavailable radio/location services on RAM Data")
    parser.add_argument("--skip-setup", action="store_true", help="use the verified official skip-Setup/no-auto-dim RAM Data copy")
    parser.add_argument("--lite-services", action="store_true", help="select the upstream sheng-lite service preset; requires --minimal-services")
    parser.add_argument("--disable-jobs", default="", help="additional comma-separated launchd labels to disable on this boot's volatile Data; requires --minimal-services")
    parser.add_argument("--gui-hold-seconds", type=int, default=0, help="explicit 30..1800 second startup observation window; requires GUI watcher/watchdog")
    parser.add_argument("--disable-dyld-compact-info", action="store_true", help="request Apple's dyld bit 19; dyld-1165.3 does not consume the resulting process option")
    parser.add_argument("--checkpoint", help="override the derived menu recovery checkpoint")
    parser.add_argument("--recovery-timeout", type=int, default=300,
                        help="bounded recovery wait, including recovery boot time (10..2400 seconds)")
    parser.add_argument("--early-watchdog", type=int, choices=(0, 1, 2), default=0,
                        help="opt-in UEFI watchdog; 2 deliberately stops before filesystem/kernel startup")
    parser.add_argument("--ipsw", type=Path, help="local iPad7,1 / 21H461 IPSW; also accepts UNIXNU_IPSW")
    parser.add_argument("--incremental-patched-tree", action="store_true",
                        help="reuse the existing patched XNU tree; clean patch replay is not yet qualified")
    parser.add_argument("--fd", type=Path, default=ROOT.parent /
                        "Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd")
    args = parser.parse_args()
    os.environ['UNIXNU_ZORN_DATA_PROFILE']=args.data_profile
    data_directory=OUT/('data-store8-192' if args.data_profile=='8g' else 'data-store')
    if args.data_profile=='8g' and (not args.skip_setup or not args.data_store_mode):
        parser.error('8GiBData requires the verified desktop seed and explicit store mode')
    if args.fresh_data and (args.data_profile!='8g' or args.data_store_mode!=2 or args.retained_data or args.touch_runtime):
        parser.error('fresh Data requires8GiB/mode2 and excludes retainedData/touch for first initialization')
    if args.smp_continue and (args.smp_preflight!=8 or args.defconfig!='zorn_union_defconfig' or
        not (args.retained_data or args.fresh_data) or args.data_store_mode!=2 or not args.data_permissions or
        not args.gui_watch or args.brightness_mode!=3 or args.display_mode!=3 or
        args.gui_user_stacks or args.gui_kernel_stacks or args.gui_runnable_kernel_stacks or
        args.touch_probe):
        parser.error("eight-core GUI requires retained/dim union GUI and excludes CPU0 stack samplers and short touch probes")
    if args.smp_preflight:
        if ((args.defconfig != "zorn_defconfig" and not args.smp_continue) or args.early_watchdog != 1 or
            not args.incremental_patched_tree or args.reuse_kernel_control or args.checkpoint or
            (not args.smp_continue and (args.gui_watch or args.brightness_mode or args.touch_probe or args.touch_runtime or
            args.data_store_mode or args.retained_data))):
            parser.error("eight-core preflight requires new incremental zorn_defconfig/watchdog1 and excludes GUI/Data/touch/checkpoint")
    if args.touch_fast_poll and not (args.touch_runtime and args.touch_trace and args.smp_continue):
        parser.error("--touch-fast-poll requires runtime touch, trace and eight-core GUI")
    if args.touch_trace and (not args.touch_runtime or args.gui_user_stacks or args.gui_kernel_stacks or args.gui_runnable_kernel_stacks):
        parser.error("--touch-trace requires runtime touch and excludes GUI stack samplers")
    if args.touch_edges and not args.touch_runtime:
        parser.error("--touch-edges requires --touch-runtime")
    if args.touch_kernel_parser and not args.touch_runtime:
        parser.error("--touch-kernel-parser requires --touch-runtime")
    if args.touch_handoff and not (args.touch_probe or args.touch_runtime):
        parser.error("--touch-handoff requires the bounded touch probe")
    if args.touch_calibrate and not args.touch_full:
        parser.error("--touch-calibrate requires --touch-full")
    if args.touch_full and not args.touch_frames:
        parser.error("--touch-full requires --touch-frames")
    if args.touch_frames and not args.touch_identify:
        parser.error("--touch-frames requires --touch-identify")
    if args.touch_identify and not (args.touch_probe and args.touch_handoff):
        parser.error("--touch-identify requires probe and native power handoff")
    display_config = args.defconfig in ("zorn_display_defconfig", "zorn_union_defconfig", "zorn_library_defconfig")
    if args.retained_data and (args.data_store_mode!=2 or not args.data_permissions):
        parser.error("--retained-data requires mode2 and guarded Data metadata policy")
    if args.touch_runtime:
        if not (args.touch_handoff and args.hid_family and args.retained_data and args.gui_watch and args.early_watchdog==1 and display_config and args.display_mode==3 and args.brightness_mode==3) or args.touch_probe or args.touch_identify or args.touch_frames or args.touch_full or args.touch_calibrate:
            parser.error("runtime touch needs handoff/HID/retained Data/dim CPU GUI/watchdog and excludes short probes")
    if args.touch_probe:
        if not display_config or args.display_mode!=3 or args.early_watchdog!=1 or args.reuse_kernel_control or args.brightness_mode:
            parser.error("touch probe requires a new CPU display/watchdog kernel, and excludes brightness transactions")
        if args.checkpoint and args.checkpoint!="TOUCHRO":
            parser.error("touch probe requires TOUCHRO checkpoint")
        args.checkpoint="TOUCHRO"
    if args.brightness_mode and (not display_config or args.display_mode != 3 or args.early_watchdog != 1 or args.reuse_kernel_control):
        parser.error("brightness requires CPU display, independent watchdog and newly built kernel")
    if args.brightness_mode:
        expected_checkpoint = "BLFAIL" if args.brightness_mode == 3 else "BLSNAP"
        if args.checkpoint and args.checkpoint != expected_checkpoint:
            parser.error("brightness profile requires checkpoint " + expected_checkpoint)
        args.checkpoint = expected_checkpoint
    if args.gui_watch and (not display_config or args.display_mode != 3):
        parser.error("--gui-watch requires a display defconfig with --display-mode 3")
    if args.gui_user_stacks and (not args.gui_watch or args.early_watchdog != 1):
        parser.error("--gui-user-stacks requires --gui-watch and --early-watchdog 1")
    if args.gui_launchservices and not args.gui_user_stacks:
        parser.error("--gui-launchservices requires --gui-user-stacks")
    if args.gui_kernel_stacks and (not args.gui_user_stacks or args.reuse_kernel_control):
        parser.error("--gui-kernel-stacks requires --gui-user-stacks and a newly built kernel")
    if args.gui_runnable_kernel_stacks and not args.gui_kernel_stacks:
        parser.error("--gui-runnable-kernel-stacks requires --gui-kernel-stacks")
    if not 0 <= args.gui_service_thread <= 63 or (args.gui_service_thread and not args.gui_launchservices):
        parser.error("--gui-service-thread requires --gui-launchservices and an ordinal 0..63")
    if not 0 <= args.gui_backboard_thread <= 63 or (args.gui_backboard_thread and not args.gui_user_stacks):
        parser.error("--gui-backboard-thread requires --gui-user-stacks and an ordinal 0..63")
    if args.development_wifi_identity and (not display_config or args.display_mode != 3):
        parser.error("--development-wifi-identity requires the CPU GUI profile")
    if args.reuse_kernel_control and not args.development_wifi_identity:
        parser.error("--reuse-kernel-control is limited to the development Wi-Fi identity trial")
    if args.data_permissions and (not args.minimal_services or (not args.gui_launchservices and not args.smp_continue) or not args.skip_setup or args.reuse_kernel_control):
        parser.error("--data-permissions requires --minimal-services, --gui-launchservices, --skip-setup and a newly built kernel")
    if args.keystore_state and (not display_config or args.display_mode != 3):
        parser.error("--keystore-state requires a display defconfig with --display-mode 3")
    if args.shared_data_volume and args.defconfig == "zorn_defconfig":
        parser.error("--shared-data-volume requires a RAM Data defconfig")
    if args.data_store_mode:
        if not args.gui_watch or args.early_watchdog != 1 or args.defconfig == "zorn_defconfig" or args.reuse_kernel_control:
            parser.error("--data-store-mode requires RAM Data, GUI watchdog and a newly built kernel")
        plan = json.loads((data_directory / "plan.json").read_text())
        if plan.get("serial") != "92988a43" or not plan.get("backup_roundtrip_verified") or \
                (args.data_store_mode == 2 and not plan.get("installed")):
            parser.error("Data reservation/preimage must be verified; write mode additionally requires installed metadata")
    if args.quiet_gui and not args.gui_watch:
        parser.error("--quiet-gui requires --gui-watch")
    if args.hid_family and (not display_config or args.display_mode != 3):
        parser.error("--hid-family requires a display defconfig with --display-mode 3")
    if args.minimal_services and (not args.gui_watch or args.early_watchdog != 1):
        parser.error("--minimal-services requires --gui-watch and --early-watchdog 1")
    if args.skip_setup and not args.gui_watch:
        parser.error("--skip-setup requires --gui-watch and a RAM Data GUI profile")
    if args.lite_services and not args.minimal_services:
        parser.error("--lite-services requires --minimal-services")
    extra_jobs = args.disable_jobs.split(",") if args.disable_jobs else []
    if extra_jobs and (not args.minimal_services or len(args.disable_jobs) > 199 or len(extra_jobs) > 32 or
                       any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", name) for name in extra_jobs)):
        parser.error("--disable-jobs requires --minimal-services, at most 32 labels and 199 ASCII label characters")
    if args.gui_hold_seconds and (not args.gui_watch or not 30 <= args.gui_hold_seconds <= 1800 or args.early_watchdog != 1):
        parser.error("--gui-hold-seconds requires --gui-watch, --early-watchdog 1 and 30..1800 seconds")
    if args.disable_dyld_compact_info and (not display_config or args.display_mode != 3):
        parser.error("--disable-dyld-compact-info requires a display defconfig with --display-mode 3")
    if args.memory_mib is not None and (not 256 <= args.memory_mib <= 8192 or args.memory_mib % 2):
        parser.error("--memory-mib must be 256..8192, aligned to 2 MiB")
    if not 10 <= args.recovery_timeout <= 2400:
        parser.error("--recovery-timeout must be between 10 and 2400 seconds")
    if args.boot and args.gui_hold_seconds and args.recovery_timeout < args.gui_hold_seconds + 120:
        parser.error("--recovery-timeout must include the observation window plus 120 seconds for boot/recovery")
    if args.gui_watch and args.early_watchdog == 1 and args.recovery_timeout < minimum_gui_recovery_timeout(args.gui_hold_seconds):
        parser.error("recovery timeout must cover independent exec/GUI budgets, watchdog bite and recovery enumeration")
    args.fd = args.fd.expanduser().resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(OUT).free < 1024**3:
        parser.error("need at least 1 GiB of local build headroom; compact generated archives before building")
    disabled_jobs = ["com.apple.identityservicesd", "com.apple.locationd", "com.apple.CommCenter", "com.apple.bluetoothd", "com.apple.watchdogd"] if args.minimal_services else []
    if args.lite_services:
        policy_source = (ROOT / "UniXNU-zorn/native/startup-policy/BootWatchdogPolicy.c").read_text()
        clean_source = re.sub(r"//[^\n]*", "", policy_source)
        strings = re.search(r"static const char lite_jobs\[\]=(.*?);", clean_source, re.S).group(1)
        disabled_jobs = ["com.apple.watchdogd", *"".join(re.findall(r'"([^"]*)"', strings)).split(",")]
        if not all(re.fullmatch(r"[A-Za-z0-9.-]+", name) for name in disabled_jobs):
            parser.error("invalid upstream lite job list")
    disabled_jobs += extra_jobs
    record = {"status": "building", "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "serial": "92988a43", "incremental_patched_tree": args.incremental_patched_tree,
              "defconfig": args.defconfig,
              "data_profile":args.data_profile,"fresh_data":args.fresh_data,
              "smp_preflight": args.smp_preflight,
              "smp_continue": args.smp_continue,
              "display_mode": args.display_mode if display_config else 0,
              "brightness_mode": args.brightness_mode,
              "touch_probe": args.touch_probe,
              "touch_handoff": args.touch_handoff,
              "touch_identify": args.touch_identify,
              "touch_frames": args.touch_frames,
              "touch_full": args.touch_full,
              "touch_calibrate": args.touch_calibrate,
              "touch_runtime": args.touch_runtime,
              "touch_edges": args.touch_edges, "touch_trace": args.touch_trace, "touch_fast_poll": args.touch_fast_poll,
              "touch_kernel_parser": args.touch_kernel_parser,
              "root_composition": "native_union" if args.defconfig == "zorn_union_defconfig" else "carrier",
              "library_path_fallback": args.defconfig == "zorn_library_defconfig",
              "dyld_compact_info_disable_requested": args.disable_dyld_compact_info,
              "gui_watch": args.gui_watch,
              "gui_user_stacks": args.gui_user_stacks,
              "gui_kernel_stacks": args.gui_kernel_stacks,
              "gui_runnable_kernel_stacks": args.gui_runnable_kernel_stacks,
              "gui_launchservices": args.gui_launchservices,
              "gui_service_thread": args.gui_service_thread,
              "gui_backboard_thread": args.gui_backboard_thread,
              "development_wifi_identity": args.development_wifi_identity,
              "data_permissions": args.data_permissions,
              "keystore_state": args.keystore_state,
              "shared_data_volume": args.shared_data_volume,
              "data_store_mode": args.data_store_mode,
              "retained_data": args.retained_data,
              "quiet_gui": args.quiet_gui,
              "hid_family": args.hid_family,
              "minimal_services": args.minimal_services,
              "skip_setup": args.skip_setup,
              "disabled_jobs": disabled_jobs,
              "service_policy_preset": ("upstream-lite" if args.lite_services else "minimal" if args.minimal_services else "none") + ("+custom" if extra_jobs else ""),
              "gui_hold_seconds": args.gui_hold_seconds,
              "checkpoint_override": args.checkpoint,
              "memory_mib": args.memory_mib or 384,
              "early_watchdog_mode": args.early_watchdog,
              "recovery_timeout_seconds": args.recovery_timeout}

    def save():
        pending = MANIFEST.with_suffix(".json.tmp")
        pending.write_text(json.dumps(record, indent=2) + "\n")
        pending.replace(MANIFEST)

    def run(phase, command, cwd=ROOT, env=None):
        record.update(status="building", phase=phase)
        save()
        print(f"[{phase}]", flush=True)
        subprocess.run([str(value) for value in command], cwd=cwd, env=env, check=True)

    save()
    try:
        if args.brightness_mode:
            run("brightness-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-brightness.py"])
        if args.touch_probe:
            run("touch-handoff-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-probe.py"])
        if args.touch_runtime:
            run("touch-contacts-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-contacts.py"])
            run("touch-runtime-frame-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-frames.py"])
            run("touch-runtime-wire-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-wire.py"])
        if args.touch_trace:
            run("touch-trace-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-trace.py"])
        if args.touch_edges:
            run("touch-edges-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-edges.py"])
            run("touch-dispatch-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-dispatch.py"])
        if args.touch_kernel_parser:
            run("touch-kernel-parser-policy", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-kernel-parser.py"])
        if args.gui_watch:
            run("gui-footer-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-gui-stacks.py"])
        if args.touch_calibrate:
            run("touch-matrix-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-matrix.py"])
        if args.touch_full:
            run("touch-raw-log-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-raw-log.py"])
        if args.touch_frames:
            run("touch-frame-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-frames.py"])
        if args.touch_identify:
            run("touch-wire-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-touch-wire.py"])
        if not args.fd.is_file():
            raise RuntimeError(f"missing firmware: {args.fd}")
        if args.early_watchdog:
            firmware = json.loads((OUT / "firmware.inputs.json").read_text())
            if not firmware.get("early_watchdog_supported") or firmware.get("sha256") != digest(args.fd):
                raise RuntimeError("early watchdog requires a matching build-zorn-firmware.py capability record")
            if args.touch_handoff:
                if not firmware.get("touch_power_supported"):
                    raise RuntimeError("touch handoff needs matching firmware capability")
                run("touch-power-host-check", [sys.executable, ROOT / "uefi-zorn/scripts/check-zorn-touch-power.py"])
                if json.loads((OUT / "touch/power-host-check.json").read_text()) != firmware["touch_power_audit"]:
                    raise RuntimeError("touch power provider audit changed")
            for source, sha in firmware["source_sha256"].items():
                if digest(Path(source)) != sha:
                    raise RuntimeError("firmware source changed since its capability record; rebuild first")
        env = dict(os.environ)
        env["UNIXNU_ZORN_SMP"] = str(args.smp_preflight)
        env["UNIXNU_ZORN_TOUCH_RUNTIME"]="1" if args.touch_runtime else "0"
        local_ipsw = args.ipsw
        if local_ipsw is None and not env.get("UNIXNU_IPSW"):
            candidate = ROOT / "iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw"
            if candidate.is_file():
                local_ipsw = candidate
        if local_ipsw is not None:
            local_ipsw = local_ipsw.expanduser().resolve()
            if not local_ipsw.is_file():
                raise RuntimeError(f"missing local IPSW: {local_ipsw}")
            env["UNIXNU_IPSW"] = str(local_ipsw)
        env.pop("UNIXNU_PATCH_LIST", None)
        if args.incremental_patched_tree:
            if not (CORE / "out/zorn/tree/.cache/xnu-work/bsd/kern/bsd_init.c").is_file():
                raise RuntimeError("--incremental-patched-tree requires the existing patched XNU tree")
            env["UNIXNU_PATCH_LIST"] = "1"
        run("defconfig", [CORE / "unixnu", "defconfig", args.defconfig, "-D", ROOT / "UniXNU-zorn"], CORE)
        run("cpu-source-profile", [sys.executable, ROOT / "UniXNU-zorn/scripts/prepare-zorn-smp-runtime.py",
                                  "--mode", "preflight8" if args.smp_preflight else "normal"])
        if args.smp_preflight:
            if args.smp_continue:
                run("smp-qualified-remap-proof",[sys.executable,ROOT/"UniXNU-zorn/scripts/check-zorn-smp-proof.py"])
            run("smp-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-smp-runtime.py"])
            run("log-ownership-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-log-ownership.py"])
        ram_data = "CONFIG_XNU_NATIVE_RAM_BLOCK=y" in (CORE / "out/zorn/.config").read_text().splitlines()
        data_report = None
        if ram_data:
            data_report_path = OUT / ("data-grow8/seed.json" if args.data_profile=='8g' else "ram-data/desktop/seed.json" if args.skip_setup else "ram-data/seed.json")
            if args.skip_setup:
                run("desktop-data-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/prepare-zorn-desktop-seed.py", "--check-only"])
            data_report = json.loads(data_report_path.read_text())
            if args.data_permissions:
                run("numeric-data-policy-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/prepare-zorn-data-permissions.py", "--check-only"])
                permissions = json.loads((ROOT / "UniXNU-zorn/native/startup-policy/data-permissions.json").read_text())
                expected_origin=data_report.get('grown_from_encoded_sha256') if args.data_profile=='8g' else data_report['encoded_sha256']
                if permissions["seed_encoded_sha256"] != expected_origin or (args.data_profile=='8g' and data_report.get('numeric_policy_paths_verified')!=len(permissions['entries'])):
                    raise RuntimeError("numeric metadata policy does not describe the selected Data seed")
            env["UNIXNU_ZORN_DATA_REPORT"] = str(data_report_path)
            import uuid
            data_uuid = str(uuid.UUID(data_report["volume_uuid"])).upper()
            config = CORE / "out/zorn/.config"
            lines = [s for s in config.read_text().splitlines() if not s.startswith("CONFIG_XNU_OWNER_DATA_VOLUME_UUID=")]
            lines.append('CONFIG_XNU_OWNER_DATA_VOLUME_UUID="' + data_uuid + '"')
            config.write_text("\n".join(lines) + "\n")
        if args.reuse_kernel_control:
            control_dir = args.reuse_kernel_control.resolve()
            control = json.loads((control_dir / "inputs.json").read_text())
            control_kernel = control_dir / "kernel.macho"
            kernel = CORE / "out/zorn/kernel/kernel.macho"
            if (control.get("status") != "ready" or control.get("serial") != "92988a43" or
                    digest(control_dir / "boot.img") != control["sha256"] or
                    digest(control_kernel) != control["inputs"].get(str(kernel))):
                raise RuntimeError("control kernel/archive identity differs")
            comparable = ("defconfig", "display_mode", "root_composition", "library_path_fallback",
                          "gui_watch", "gui_user_stacks", "gui_launchservices", "gui_service_thread", "gui_backboard_thread", "keystore_state",
                          "shared_data_volume", "quiet_gui", "hid_family", "minimal_services", "skip_setup",
                          "disabled_jobs", "service_policy_preset", "gui_hold_seconds", "checkpoint_override",
                          "memory_mib", "early_watchdog_mode", "dyld_compact_info_disable_requested")
            if control.get("development_wifi_identity") or control.get("gui_kernel_stacks", False) != record["gui_kernel_stacks"] or control.get("gui_runnable_kernel_stacks", False) != record["gui_runnable_kernel_stacks"] or any(control.get(key, 0 if key in ("gui_service_thread", "gui_backboard_thread") else None) != record.get(key) for key in comparable):
                raise RuntimeError("ADT trial must preserve every control profile option")
            plan_path = control_dir / "kernel-plan.json"
            if not plan_path.is_file():
                plan_path = control_dir / "kernel-audit-plan.json"
            plan_bytes = plan_path.read_bytes()
            plan = json.loads(plan_bytes)
            plan_pin = control["inputs"].get(str(kernel.with_suffix(".json")))
            if plan_pin:
                if digest(plan_path) != plan_pin:
                    raise RuntimeError("control prelink plan differs")
            elif not (plan.get("audit_plan_kind") == "reconstructed-layout-for-archived-control" and
                      plan.get("candidate_sha256") == digest(control_kernel) and
                      plan.get("control_boot_sha256") == control["sha256"] and
                      plan.get("all_original_component_extents_match") is True):
                raise RuntimeError("legacy archive needs a verified layout plan for its exact kernel")
            kernel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(control_kernel, kernel)
            reuse = {"kind": "reused-qualified-control", "control_boot_sha256": control["sha256"],
                     "control_manifest_sha256": digest(control_dir / "inputs.json"),
                     "kernel_sha256": digest(kernel), "source_archive": str(control_dir)}
            kernel.with_suffix(".json").write_bytes(plan_bytes)
            record["kernel_reuse"] = reuse
            save()
            print("[kernel] reused exact archived control " + reuse["kernel_sha256"], flush=True)
        else:
            run("kernel", [CORE / "unixnu", "build", "kernel"], CORE, env)
        if args.smp_preflight:
            run("smp-linked-call-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-smp.py"]+(["--continue-gui"] if args.smp_continue else []))
        if display_config and json.loads((CORE / "out/zorn/tree/build/native-legacy-display/build-report.json").read_text()).get("touch_runtime_compiled") is not args.touch_runtime:
            raise RuntimeError("touch runtime compile gate does not match requested profile")
        if args.touch_runtime:
            run("touch-runtime-linked-calls", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-touch-runtime.py"])
        if args.gui_watch:
            run("gui-ipc-hook-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-gui-hook.py"])
            run("gui-final-snapshot-host-checks", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-final-snapshot.py"])
            run("gui-window-host-checks", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-gui-window.py"])
            run("trace-stage-host-checks", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-trace-stages.py"])
        if args.gui_user_stacks:
            run("gui-stack-call-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-gui-stacks.py"])
        if args.gui_kernel_stacks:
            run("gui-kernel-stack-host-checks", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-kernel-stacks.py"])
            run("vm-map-lock-init-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-vm-map-lock.py",
                                          "--kernel", CORE / "out/zorn/kernel/kernel.macho"])
        if args.data_store_mode:
            run("data-store-host-checks", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-data-store.py"])
            run("data-store-linked-call-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-data-store.py"])
        if args.data_permissions:
            run("data-permissions-call-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-data-permissions.py"])
        if args.retained_data:
            run("retained-marker-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-retained-marker.py"])
            run("data-probe-host-check", [sys.executable, ROOT / "UniXNU-zorn/scripts/check-zorn-data-probe.py"])
        if args.minimal_services:
            run("startup-policy-hook-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-service-policy.py"])
        if ram_data:
            run("data-seed-constant-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-data-seed.py", "--report", data_report_path])
        if "CONFIG_XNU_NATIVE_AES=y" in (CORE / "out/zorn/.config").read_text().splitlines():
            tree = CORE / "out/zorn/tree"
            run("aes-post-prelink-audit", [sys.executable, tree / "scripts/build-zorn-aes.py",
                                           "--audit-only"], tree)
        if "CONFIG_XNU_ZORN_VERIFIED_ROOT=y" in (CORE / "out/zorn/.config").read_text().splitlines():
            tree = CORE / "out/zorn/tree"
            run("storage-post-prelink-audit", [sys.executable, tree / "scripts/build-zorn-storage.py",
                                               "--audit-only"], tree)
            if ram_data:
                run("ram-storage-post-prelink-audit", [sys.executable, tree / "scripts/build-zorn-storage.py",
                                                       "--component", "RamBlock", "--audit-only"], tree)
        if "CONFIG_XNU_NATIVE_LEGACY_DISPLAY=y" in (CORE / "out/zorn/.config").read_text().splitlines():
            tree = CORE / "out/zorn/tree"
            run("display-post-prelink-audit", [sys.executable, tree / "scripts/build-zorn-display.py",
                                               "--audit-only"], tree)
        trust = OUT / "original-trustcache/original-static-system.bundle"
        verified_ufs = "CONFIG_XNU_ZORN_VERIFIED_ROOT=y" in (CORE / "out/zorn/.config").read_text().splitlines()
        payload_command = [sys.executable, ROOT / "uefi-zorn/scripts/make-zorn-payload.py", "--trust-cache", trust]
        payload_command += ['--data-profile',args.data_profile]
        if args.fresh_data:payload_command.append('--fresh-data')
        if args.smp_preflight:
            payload_command += ["--smp-preflight", str(args.smp_preflight)]
        if args.smp_continue:
            payload_command.append("--smp-continue")
        if ram_data:
            payload_command += ["--data-seed", ROOT / data_report["seed"]]
        elif verified_ufs:
            payload_command.append("--no-initrd")
        if display_config:
            payload_command += ["--display-mode", str(args.display_mode)]
        if args.memory_mib:
            payload_command += ["--memory-mib", str(args.memory_mib)]
        if args.gui_watch:
            payload_command.append("--gui-watch")
        if args.gui_user_stacks:
            payload_command.append("--gui-user-stacks")
        if args.gui_kernel_stacks:
            payload_command.append("--gui-kernel-stacks")
        if args.gui_runnable_kernel_stacks:
            payload_command.append("--gui-runnable-kernel-stacks")
        if args.data_store_mode:
            payload_command += ["--data-store-mode", str(args.data_store_mode)]
        if args.brightness_mode:
            payload_command += ["--brightness-mode", str(args.brightness_mode)]
        if args.touch_probe:
            payload_command.append("--touch-probe")
        if args.touch_handoff:
            payload_command.append("--touch-handoff")
        if args.touch_identify:
            payload_command.append("--touch-identify")
        if args.touch_frames:
            payload_command.append("--touch-frames")
        if args.touch_full:
            payload_command.append("--touch-full")
        if args.touch_calibrate:
            payload_command.append("--touch-calibrate")
        if args.touch_runtime:
            payload_command.append("--touch-runtime")
        if args.touch_fast_poll:
            payload_command.append("--touch-fast-poll")
        if args.touch_trace:
            payload_command.append("--touch-trace")
        if args.touch_edges:
            payload_command.append("--touch-edges")
        if args.touch_kernel_parser:
            payload_command.append("--touch-kernel-parser")
        if args.retained_data:
            payload_command += ["--retained-data"]
        if args.gui_launchservices:
            payload_command.append("--gui-launchservices")
        if args.gui_service_thread:
            payload_command += ["--gui-service-thread", str(args.gui_service_thread)]
        if args.gui_backboard_thread:
            payload_command += ["--gui-backboard-thread", str(args.gui_backboard_thread)]
        if args.development_wifi_identity:
            payload_command.append("--development-wifi-identity")
        if args.data_permissions:
            payload_command.append("--data-permissions")
        if args.keystore_state:
            payload_command.append("--keystore-state")
        if args.shared_data_volume:
            payload_command.append("--shared-data-volume")
        if args.quiet_gui:
            payload_command.append("--quiet-gui")
        if args.hid_family:
            payload_command.append("--hid-family")
        if args.minimal_services:
            payload_command.append("--minimal-services")
        if args.lite_services:
            payload_command.append("--lite-services")
        if extra_jobs:
            payload_command += ["--disable-jobs", args.disable_jobs]
        if args.gui_hold_seconds:
            payload_command += ["--gui-hold-seconds", str(args.gui_hold_seconds)]
        if args.disable_dyld_compact_info:
            payload_command.append("--disable-dyld-compact-info")
        if args.checkpoint:
            payload_command += ["--checkpoint", args.checkpoint]
        if args.early_watchdog:
            payload_command += ["--early-watchdog", str(args.early_watchdog)]
        run("payload", payload_command)
        if args.smp_preflight:
            run("smp-payload-audit", [sys.executable, ROOT / "UniXNU-zorn/scripts/audit-zorn-smp.py", "--payload"]+(["--continue-gui"] if args.smp_continue else [])+(['--fresh-data'] if args.fresh_data else []))
        image = OUT / "boot.img"
        run("boot-image", [sys.executable, ROOT / "uefi-zorn/scripts/package-zorn-boot.py",
                           "--fd", args.fd, "--ramdisk", OUT / "payload.img", "-o", image])
        inputs = [CORE / "out/zorn/kernel/kernel.macho", CORE / "out/zorn/kernel/kernel.json", CORE / "out/zorn/.config",
                  ROOT / "UniXNU-zorn/board.toml", ROOT / "UniXNU-zorn/configs" / args.defconfig,
                  ROOT / "uefi-zorn/payload/EFI/UniXNU/unixnu.toml", OUT / "kernel.macho.adt",
                  OUT / "payload-with-trustcache.adt",
                  trust, args.fd]
        if args.smp_preflight:
            inputs += [OUT / "smp/runtime/profile.json", OUT / "smp/runtime/ArmCpu.cpp",
                       OUT / "smp/runtime/ZornSmpPolicy.h", OUT / "smp/runtime/ZornSmpRuntime.inc",
                       OUT / "smp/runtime-host-check.json", OUT / "smp/log-ownership-host-check.json",
                       OUT / "smp/linked-call-audit.json", OUT / ("payload-ramdata.toml" if args.smp_continue else "payload-debug.toml"),
                       CORE / "out/zorn/tree/build/armcpu/zorn-smp-build.json",
                       ROOT / "UniXNU-zorn/native/ufs-read/ZornUfsRead.cpp",
                       ROOT / "UniXNU-zorn/native/ufs-read/ZornWatchdog.h",
                       ROOT / "UniXNU-zorn/native/startup-policy/DataUnavailable.c",
                       ROOT / "UniXNU-zorn/scripts/build-zorn-cpu.py",
                       ROOT / "UniXNU-zorn/scripts/build-zorn-ufs.py",
                       ROOT / "UniXNU-zorn/scripts/build-zorn-debug.py",
                       ROOT / "uefi-zorn/scripts/make-zorn-payload.py",
                       ROOT / "UniXNU-zorn/scripts/prepare-zorn-smp-runtime.py",
                       ROOT / "UniXNU-zorn/scripts/audit-zorn-smp.py",
                       ROOT / "UniXNU-zorn/scripts/check-zorn-smp-runtime.py",
                       ROOT / "UniXNU-zorn/scripts/check-zorn-log-ownership.py"]
            inputs += list((ROOT / "UniXNU-zorn/native/smp").glob("*.patch"))
            inputs.append(ROOT / "UniXNU-zorn/native/smp/runtime-source-pins.json")
            if args.smp_continue:
                inputs += [OUT / "smp/eight-remap-qualified.json",OUT/"smp/qualified-proof-check.json",ROOT/"UniXNU-zorn/scripts/check-zorn-smp-proof.py"]
            runtime = json.loads((OUT / "smp/runtime/profile.json").read_text())
            inputs += [CORE / "out/zorn/tree/.cache/xnu-work" / name for name in runtime["files"]]
        if not verified_ufs:
            inputs.append(OUT / "root.img")
        if ram_data:
            inputs += [ROOT / data_report["seed"], data_report_path, OUT / "payload-ramdata.toml", OUT / "data-seed-audit.json"]
        if args.data_store_mode:
            inputs += [data_directory / "plan.json", OUT / "data-store-host-checks.json",
                       OUT / "data-store-link-audit.json", ROOT / "UniXNU-zorn/scripts/audit-zorn-data-store.py",
                       ROOT / "UniXNU-zorn/scripts/check-zorn-data-store.py",
                       ROOT / "UniXNU-zorn/native/startup-policy/DataMarker.c",
                       ROOT / "UniXNU-zorn/native/startup-policy/BootWatchdogPolicy.c",
                       ROOT / "UniXNU-zorn/scripts/build-zorn-ufs.py",
                       ROOT / "UniXNU-zorn/scripts/zorn_session_guard.py",
                       ROOT / "UniXNU-zorn/native/ufs-read/ZornDataStore.h",
                       ROOT / "UniXNU-zorn/native/ufs-read/ZornDataStorePolicy.h",
                       ROOT / "UniXNU-zorn/native/ufs-read/ZornVolatileData.c",
                       ROOT / "UniXNU-zorn/native/ufs-read/RootCommands.h"]
            inputs += [ROOT/'UniXNU-zorn/scripts/zorn_data_profile.py',ROOT/'UniXNU-zorn/scripts/prepare-zorn-data-store.py',ROOT/'UniXNU-zorn/scripts/build-zorn-data.py']
            inputs += [ROOT/'UniXNU-zorn/native/ufs-read/ZornUfsRead.cpp',ROOT/'UniXNU-zorn/scripts/verify-zorn-data-store.py']
            if args.data_profile=='8g':inputs.append(ROOT/'UniXNU-zorn/scripts/prepare-zorn-data8-seed.py')
        if display_config and args.display_mode == 3:
            inputs += [OUT / "cpu-profile/profile.json", CORE / "profiles/os/ipados-17.7.11-21H461/profile.toml"]
        if args.retained_data:
            inputs += [ROOT / "UniXNU-zorn/scripts/check-zorn-retained-marker.py",
                       ROOT / "UniXNU-zorn/scripts/check-zorn-data-probe.py",
                       OUT / "data-store/retained-marker-host-check.json",
                       OUT / "data-store/data-probe-host-check.json"]
        if args.gui_watch:
            inputs.append(OUT / "gui-hook-audit.json")
            inputs += [ROOT / "UniXNU-zorn/native/ufs-read/ZornGuiLog.h",
                       ROOT / "UniXNU-zorn/scripts/read-zorn-log.py",
                       ROOT / "UniXNU-zorn/scripts/check-zorn-gui-stacks.py",
                       ROOT / "UniXNU-zorn/scripts/build-zorn-ufs.py",
                       OUT / "gui-stack-checks.json"]
        if args.gui_user_stacks:
            inputs.append(OUT / "gui-stack-audit.json")
            inputs += [ROOT / "UniXNU-zorn/native/ufs-read/ZornGuiLog.h",
                       ROOT / "UniXNU-zorn/native/ufs-read/ZornUfsRead.cpp",
                       CORE / "out/zorn/tree/.cache/xnu-work/osfmk/kern/exception.c",
                       CORE / "out/zorn/tree/.cache/xnu-work/bsd/kern/bsd_init.c"]
        if args.gui_kernel_stacks:
            inputs += [OUT / "kernel-stack-host-checks.json", ROOT / "UniXNU-zorn/scripts/check-zorn-kernel-stacks.py"]
            inputs += [OUT / "vm-map-lock-audit.json", ROOT / "UniXNU-zorn/scripts/audit-zorn-vm-map-lock.py",
                       CORE / "out/zorn/tree/.cache/xnu-work/osfmk/vm/vm_map.h"]
        if args.gui_watch:
            inputs += [OUT / "gui-final-snapshot-host-checks.json", ROOT / "UniXNU-zorn/scripts/check-zorn-final-snapshot.py"]
            inputs += [OUT / "gui-window-host-checks.json", ROOT / "UniXNU-zorn/scripts/check-zorn-gui-window.py"]
            inputs += [OUT / "trace-stage-host-checks.json", ROOT / "UniXNU-zorn/scripts/check-zorn-trace-stages.py",
                       ROOT / "UniXNU-zorn/native/ufs-read/ZornTraceStages.h", ROOT / "UniXNU-zorn/native/ufs-read/trace-stages.json"]
        if display_config:
            inputs += [CORE / "out/zorn/tree/build/native-legacy-display/build-report.json",
                       ROOT / "UniXNU-zorn/native/display/ZornPanelBrightness.h",
                       ROOT / "UniXNU-zorn/native/display/ZornDsiBrightness.h",
                       ROOT / "UniXNU-zorn/native/display/ZornTouchProbe.h",
                       ROOT / "UniXNU-zorn/native/display/ZornTouchHandoff.h",
                       ROOT / "UniXNU-zorn/scripts/make-zorn-adt.py",
                       ROOT / "uefi-zorn/scripts/make-zorn-payload.py"]
        if args.brightness_mode:
            inputs += [OUT / "brightness/host-check.json", ROOT / "UniXNU-zorn/scripts/check-zorn-brightness.py"]
        if args.touch_probe:
            inputs += [OUT / "touch/handoff-host-check.json", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-probe.py"]
        if args.touch_handoff:
            inputs += [OUT / "firmware.inputs.json", OUT / "touch/power-host-check.json", ROOT / "uefi-zorn/scripts/check-zorn-touch-power.py"]
        if args.touch_runtime:
            inputs += [ROOT / "UniXNU-zorn/native/display/ZornTouchPacing.h", ROOT / "UniXNU-zorn/native/display/ZornTouchRuntime.h", ROOT / "UniXNU-zorn/native/display/ZornTouchHid.cpp", ROOT / "UniXNU-zorn/native/display/ZornTouchContacts.h", ROOT / "UniXNU-zorn/scripts/zorn_touch_hid_build.py", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-contacts.py", OUT / "touch/contacts-host-check.json", CORE / "out/zorn/tree/build/native-legacy-display/touch-hid-abi-audit.json"]
            inputs.append(ROOT / "UniXNU-zorn/native/display/ZornTouchKernelMatch.h")
            inputs += [ROOT / "UniXNU-zorn/scripts/audit-zorn-touch-runtime.py", OUT / "touch/runtime-linked-calls.json"]
            inputs += [ROOT / "UniXNU-zorn/native/display/ZornFt3683Wire.h", ROOT / "UniXNU-zorn/native/display/ZornTouchMatrix.h", ROOT / "UniXNU-zorn/native/display/ZornTouchIdentify.h", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-frames.py", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-wire.py", OUT / "touch/frame-host-check.json", OUT / "touch/wire-host-check.json"]
            inputs += [ROOT / "UniXNU-zorn/native/display/ZornTouchEdges.h", ROOT / "UniXNU-zorn/native/display/ZornTouchEdgeDispatch.h"]
        if args.touch_trace:
            inputs += [ROOT / "UniXNU-zorn/native/display/ZornTouchTrace.h", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-trace.py", OUT / "touch/trace-host-check.json"]
        if args.touch_edges:
            inputs += [ROOT / "UniXNU-zorn/scripts/check-zorn-touch-edges.py", OUT / "touch/edges-host-check.json"]
            inputs += [ROOT / "UniXNU-zorn/scripts/check-zorn-touch-dispatch.py", OUT / "touch/dispatch-host-check.json"]
        if args.touch_kernel_parser:
            inputs += [ROOT / "UniXNU-zorn/scripts/check-zorn-touch-kernel-parser.py", OUT / "touch/kernel-parser-host-check.json"]
        if args.touch_calibrate:
            inputs += [ROOT / "UniXNU-zorn/native/display/ZornTouchMatrix.h", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-matrix.py", OUT / "touch/matrix-host-check.json"]
        if args.touch_full:
            inputs += [ROOT / "UniXNU-zorn/native/display/ZornTouchPrompt.h", ROOT / "UniXNU-zorn/native/ufs-read/ZornTouchRawLog.h", ROOT / "UniXNU-zorn/scripts/read-zorn-log.py", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-raw-log.py", OUT / "touch/raw-log-host-check.json"]
        if args.touch_frames:
            inputs += [ROOT / "UniXNU-zorn/native/display/ZornTouchFrames.h", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-frames.py", OUT / "touch/frame-host-check.json"]
        if args.touch_identify:
            inputs += [ROOT / "UniXNU-zorn/native/display/ZornFt3683Wire.h", ROOT / "UniXNU-zorn/native/display/ZornTouchIdentify.h", ROOT / "UniXNU-zorn/native/display/zorn-touch-board.json", ROOT / "UniXNU-zorn/scripts/check-zorn-touch-wire.py", OUT / "touch/wire-host-check.json"]
        if args.minimal_services:
            inputs += [ROOT / "UniXNU-zorn/native/startup-policy/BootWatchdogPolicy.c", OUT / "startup-policy-audit.json"]
        if args.data_permissions:
            inputs += [ROOT / "UniXNU-zorn/native/startup-policy/DataPermissions.c",
                       ROOT / "UniXNU-zorn/native/startup-policy/DataPermissions.h",
                       ROOT / "UniXNU-zorn/native/startup-policy/data-permissions.json", OUT / "data-permissions-audit.json"]
        if args.checkpoint and not ram_data:
            inputs.append(OUT / "payload-debug.toml")
        record.update(status="ready", phase="packaged", image=str(image), sha256=digest(image),
                      inputs={str(path): digest(path) for path in inputs},
                      completed=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        save()
        archive = OUT / "builds" / record["sha256"][:8]
        archive.mkdir(parents=True, exist_ok=True)
        saved = [(image, archive / "boot.img"),
                 (CORE / "out/zorn/kernel/kernel.macho", archive / "kernel.macho"),
                 (CORE / "out/zorn/kernel/kernel.json", archive / "kernel-plan.json")]
        if args.smp_preflight:
            saved += [(OUT / "smp/runtime/profile.json", archive / "smp-profile.json"),
                      (OUT / "smp/runtime-host-check.json", archive / "smp-host-check.json"),
                      (OUT / "smp/log-ownership-host-check.json", archive / "log-ownership-host-check.json"),
                      (OUT / "smp/linked-call-audit.json", archive / "smp-linked-call-audit.json"),
                      (CORE / "out/zorn/tree/build/armcpu/zorn-smp-build.json", archive / "smp-driver-build.json"),
                      (OUT / ("payload-ramdata.toml" if args.smp_continue else "payload-debug.toml"), archive / "unixnu.toml"),
                      (OUT / "payload-with-trustcache.adt", archive / "kernel.macho.adt"),
                      (OUT / "smp/runtime/ArmCpu.cpp", archive / "ArmCpu.cpp"),
                      (OUT / "smp/runtime/ZornSmpRuntime.inc", archive / "ZornSmpRuntime.inc"),
                      (OUT / "smp/runtime/ZornSmpPolicy.h", archive / "ZornSmpPolicy.h")]
            if args.smp_continue:
                saved += [(OUT/"smp/eight-remap-qualified.json",archive/"smp-qualified-baseline.json"),
                          (OUT/"smp/qualified-proof-check.json",archive/"smp-qualified-proof-check.json")]
        if args.gui_watch:
            saved += [(OUT / "gui-hook-audit.json", archive / "gui-hook-audit.json"),
                      (OUT / "gui-stack-checks.json", archive / "gui-footer-host-checks.json"),
                      (CORE / "out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/osfmk/DEVELOPMENT/ipc_kmsg.o.json",
                       archive / "ipc_kmsg.o.json"),
                      (CORE / "out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOUserClient.cpo.json",
                       archive / "IOUserClient.cpo.json")]
        if args.brightness_mode:
            saved.append((OUT / "brightness/host-check.json", archive / "brightness-host-check.json"))
        if args.touch_probe:
            saved.append((OUT / "touch/handoff-host-check.json", archive / "touch-handoff-host-check.json"))
        if args.touch_handoff:
            saved += [(OUT / "firmware.inputs.json", archive / "firmware-inputs.json"), (OUT / "touch/power-host-check.json", archive / "touch-power-host-check.json")]
        if args.touch_runtime:
            saved += [(OUT / "touch/contacts-host-check.json", archive / "touch-contacts-host-check.json"), (CORE / "out/zorn/tree/build/native-legacy-display/touch-hid-abi-audit.json", archive / "touch-hid-abi-audit.json")]
            saved.append((OUT / "touch/runtime-linked-calls.json", archive / "touch-runtime-linked-calls.json"))
        if args.touch_trace:
            saved.append((OUT / "touch/trace-host-check.json", archive / "touch-trace-host-check.json"))
        if args.touch_edges:
            saved.append((OUT / "touch/edges-host-check.json", archive / "touch-edges-host-check.json"))
            saved.append((OUT / "touch/dispatch-host-check.json", archive / "touch-dispatch-host-check.json"))
        if args.touch_kernel_parser:
            saved.append((OUT / "touch/kernel-parser-host-check.json", archive / "touch-kernel-parser-host-check.json"))
        if args.touch_calibrate:
            saved += [(OUT / "touch/matrix-host-check.json", archive / "touch-matrix-host-check.json")]
        if args.touch_full:
            saved += [(OUT / "touch/raw-log-host-check.json", archive / "touch-raw-log-host-check.json")]
        if args.touch_frames:
            saved += [(OUT / "touch/frame-host-check.json", archive / "touch-frame-host-check.json")]
        if args.touch_identify:
            saved += [(OUT / "touch/wire-host-check.json", archive / "touch-wire-host-check.json"), (ROOT / "UniXNU-zorn/native/display/zorn-touch-board.json", archive / "touch-board.json")]
        if args.gui_user_stacks:
            saved.append((OUT / "gui-stack-audit.json", archive / "gui-stack-audit.json"))
        if args.gui_watch:
            saved.append((OUT / "gui-final-snapshot-host-checks.json", archive / "gui-final-snapshot-host-checks.json"))
            saved.append((OUT / "gui-window-host-checks.json", archive / "gui-window-host-checks.json"))
            saved.append((OUT / "trace-stage-host-checks.json", archive / "trace-stage-host-checks.json"))
        if args.gui_kernel_stacks:
            saved.append((OUT / "kernel-stack-host-checks.json", archive / "kernel-stack-host-checks.json"))
            saved.append((OUT / "vm-map-lock-audit.json", archive / "vm-map-lock-audit.json"))
        if args.data_store_mode:
            saved += [(data_directory / "plan.json", archive / "data-store-plan.json"),
                      (OUT / "data-store-host-checks.json", archive / "data-store-host-checks.json"),
                      (OUT / "data-store-link-audit.json", archive / "data-store-link-audit.json")]
        if args.data_permissions:
            saved.append((OUT / "data-permissions-audit.json", archive / "data-permissions-audit.json"))
        if args.retained_data:
            saved += [(OUT / "data-store/retained-marker-host-check.json", archive / "retained-marker-host-check.json"),
                      (OUT / "data-store/data-probe-host-check.json", archive / "data-probe-host-check.json")]
        if display_config:
            saved += [(CORE / "out/zorn/tree/build/native-legacy-display/build-report.json", archive / "display-build-report.json"),
                      (OUT / "payload-with-trustcache.adt", archive / "kernel.macho.adt"),
                      (OUT / "payload-ramdata.toml", archive / "unixnu.toml")]
        if args.minimal_services:
            saved += [(OUT / "startup-policy-audit.json", archive / "startup-policy-audit.json"),
                      (CORE / "out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/kern_exec.o.json", archive / "kern_exec.o.json")]
        if ram_data:
            saved.append((OUT / "data-seed-audit.json", archive / "data-seed-audit.json"))
        # Publish a ready archive manifest only after every artifact is whole.
        saved.append((MANIFEST, archive / "inputs.json"))
        for source, destination in saved:
            if destination.exists():
                if digest(destination) != digest(source):
                    raise RuntimeError("archive artifact differs: " + str(destination))
                continue
            temporary = destination.with_name("." + destination.name + "." + str(os.getpid()) + ".partial")
            if temporary.exists():
                raise RuntimeError("archive staging file already exists: " + str(temporary))
            try:
                # APFS copy-on-write keeps a separate inode. Future rebuilds
                # cannot mutate an archived snapshot, unlike a source hard link.
                if sys.platform == "darwin":
                    subprocess.run(["/bin/cp", "-c", str(source), str(temporary)], check=True)
                    if source.stat().st_dev == temporary.stat().st_dev and source.stat().st_ino == temporary.stat().st_ino:
                        raise RuntimeError("archive must not alias the source inode")
                else:
                    shutil.copyfile(source, temporary)
                if digest(temporary) != digest(source):
                    raise RuntimeError("archive copy differs: " + str(destination))
                os.link(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        record.update(status="failed", error=str(error))
        save()
        raise
    if args.boot:
        # This runner validates the ready manifest and image digest before USB actions.
        subprocess.run([sys.executable, Path(__file__).with_name("run-zorn-debug.py"),
                        "--timeout", str(args.recovery_timeout)], check=True)
    print(f"ready {image}: {record['sha256']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
