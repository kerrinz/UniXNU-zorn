#!/usr/bin/env python3
"""One unattended K80 round: recovery -> fastboot boot -> recovery -> saved log.

All device commands target 92988a43. The kernel image owns its checkpoint and
recovery reset; this host runner never flashes a partition or changes a slot.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SERIAL = "92988a43"
ROOT = Path(__file__).resolve().parents[2]


def command(args, timeout=20):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{' '.join(map(str, args))}: {result.stdout}{result.stderr}")
    return result.stdout + result.stderr


def adb_state():
    for line in command(["adb", "devices"]).splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] == SERIAL:
            return fields[1]
    return None


def fastboot_visible():
    return any(line.split()[:2] == [SERIAL, "fastboot"]
               for line in command(["fastboot", "devices"]).splitlines())


def verify_bootloader():
    product = command(["fastboot", "-s", SERIAL, "getvar", "product"])
    slot = command(["fastboot", "-s", SERIAL, "getvar", "current-slot"])
    if "product: zorn" not in product or "current-slot: b" not in slot:
        raise RuntimeError(f"unexpected bootloader identity/slot:\n{product}{slot}")


def wait_for_recovery(timeout, capture_after=0, capture=None):
    started = time.monotonic()
    deadline = started + timeout
    next_notice = started + 20
    captured = False
    while True:
        state = adb_state()
        if state == "recovery":
            return
        if state is not None:
            raise RuntimeError(f"unexpected adb state after boot: {state!r}")
        now = time.monotonic()
        if now >= deadline:
            raise RuntimeError(f"no recovery ADB after {timeout} seconds; no further reboot attempted")
        if capture_after and not captured and now - started >= capture_after and deadline - now >= 26:
            captured = True
            try:
                capture(now - started)
            except Exception as error:
                # Optional host-only observation must not defeat log recovery.
                print(f"screen observation failed: {error}", flush=True)
        if now >= next_notice:
            print("waiting for recovery ADB", flush=True)
            next_notice = now + 20
        time.sleep(2)


def capture_screen(out, elapsed):
    result = {"elapsed_after_boot_seconds": elapsed, "audio": False}
    try:
        shot = subprocess.run([sys.executable, str(Path(__file__).with_name("capture-zorn-screen.py")),
                               "--run", str(out)], capture_output=True, text=True, timeout=25)
        result.update(returncode=shot.returncode, stdout=shot.stdout, stderr=shot.stderr)
    except (OSError, subprocess.SubprocessError) as error:
        result.update(error=str(error))
    (out / "scheduled-screen-capture.json").write_text(json.dumps(result, indent=2) + "\n")
    print("scheduled host screen observation completed; recovery deadline unchanged", flush=True)


def prepare_recovery_bcb(out):
    if adb_state() != "recovery" or command(["adb", "-s", SERIAL, "get-serialno"]).strip() != SERIAL or \
            command(["adb", "-s", SERIAL, "shell", "getprop", "ro.product.device"]).strip() != "zorn":
        raise RuntimeError("BCB preparation requires the exact K80 recovery")

    def read_page():
        result = subprocess.run(["adb", "-s", SERIAL, "exec-out", "sh", "-c",
                                 "dd if=/dev/block/by-name/misc bs=4096 count=1 2>/dev/null"],
                                capture_output=True, check=True, timeout=20)
        if len(result.stdout) != 4096:
            raise RuntimeError("misc read did not return exactly one 4 KiB page")
        return result.stdout

    original = read_page()
    (out / "misc-before.bin").write_bytes(original)
    page = bytearray(original)
    page[:864] = bytes(864)
    page[:14] = b"boot-recovery\0"
    page[64:73] = b"recovery\n"
    assert page[864:] == original[864:] and len(page) == 4096
    source = out / "recovery-bcb.bin"
    source.write_bytes(page)
    remote = "/tmp/unixnu-recovery-bcb.bin"
    command(["adb", "-s", SERIAL, "push", str(source), remote])
    copied = subprocess.run(["adb", "-s", SERIAL, "exec-out", "cat", remote],
                            capture_output=True, check=True, timeout=20).stdout
    if copied != bytes(page):
        raise RuntimeError("temporary BCB copy differs; no device write attempted")
    command(["adb", "-s", SERIAL, "shell",
             "dd if=/tmp/unixnu-recovery-bcb.bin of=/dev/block/by-name/misc bs=4096 count=1 conv=notrunc"])
    if read_page() != bytes(page):
        raise RuntimeError("recovery BCB read-back differs; no boot attempted")
    (out / "bcb.json").write_text(json.dumps({"serial": SERIAL, "bytes": 4096,
        "changed_prefix_bytes": 864, "tail_preserved": True, "readback_verified": True,
        "before_sha256": hashlib.sha256(original).hexdigest(),
        "after_sha256": hashlib.sha256(page).hexdigest()}, indent=2) + "\n")
    print("verified recovery BCB; only first 864 bytes changed, 4 KiB page read back", flush=True)


def main():
    from zorn_session_guard import check_deadline
    check_deadline()
    if sys.platform == "darwin" and Path("/usr/bin/caffeinate").is_file():
        # The assertion ends with this exact trial process, including failures.
        subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=ROOT / "out/zorn/boot.img")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--capture-after", type=int, default=0,
                        help="optional single USB-camera frame this many seconds after fastboot boot; 0 disables")
    parser.add_argument("--arm-recovery-bcb", action="store_true", help="prepare the bounded recovery BCB before an early-watchdog image")
    parser.add_argument("--gpu-media-qualification-policy", type=Path, help="UNAPPLIED proposal; requires new specific approval and complete fresh candidate")
    args = parser.parse_args()
    if args.timeout < 10:
        parser.error("--timeout must be at least 10 seconds")
    if args.capture_after and not 30 <= args.capture_after <= args.timeout - 30:
        parser.error("--capture-after must be 0 or 30..timeout-30 seconds")
    image = args.image.resolve()
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    qualification = None
    if args.gpu_media_qualification_policy:
        from qualification_policy import validate, claim
        policy = json.loads(args.gpu_media_qualification_policy.read_text())
        qualification = validate(policy, image, args.timeout, args.capture_after, args.arm_recovery_bcb)
    out = ROOT / "out/zorn/debug" / (time.strftime("%Y%m%d-%H%M%S-") + digest[:8])
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"serial": SERIAL, "image": str(image), "sha256": digest,
                "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": "started",
                "recovery_timeout_seconds": args.timeout,
                "host_log_reader_sha256": hashlib.sha256(
                    Path(__file__).with_name("read-zorn-log.py").read_bytes()).hexdigest()}
    if args.capture_after:
        manifest["screen_capture_after_boot_seconds"] = args.capture_after
        manifest["screen_capture_script_sha256"] = hashlib.sha256(
            Path(__file__).with_name("capture-zorn-screen.py").read_bytes()).hexdigest()
        manifest["host_runner_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def record():
        (out / "run.json").write_text(json.dumps(manifest, indent=2) + "\n")

    record()
    try:
        inputs = (ROOT / "out/zorn/boot.inputs.json" if image == (ROOT / "out/zorn/boot.img").resolve()
                  else image.with_suffix(".inputs.json"))
        if image.name == "boot.img" and image.parent.parent == (ROOT / "out/zorn/builds").resolve():
            inputs = image.parent / "inputs.json"
        if not inputs.is_file():
            raise RuntimeError("missing ready build manifest; no USB action attempted")
        early_watchdog = args.arm_recovery_bcb
        build = None
        if inputs.exists():
            build = json.loads(inputs.read_text())
            if build.get("status") != "ready" or build.get("sha256") != digest:
                raise RuntimeError("build manifest is not ready or does not match boot.img; rebuild with build-zorn-debug.py")
            if build.get("single_media_qualification") is True or qualification:
                from qualification_policy import validate_build_manifest
                validate_build_manifest(build, qualification)
            (out / "build-inputs.json").write_bytes(inputs.read_bytes())
            early_watchdog = early_watchdog or build.get("early_watchdog_mode", 0) != 0
        if args.capture_after and (not build or not build.get("gui_watch") or not early_watchdog):
            raise RuntimeError("scheduled screen observation requires a ready GUI watchdog build")
        if build and build.get("gui_watch") and early_watchdog:
            from zorn_session_guard import minimum_gui_recovery_timeout
            if args.timeout < minimum_gui_recovery_timeout(build.get("gui_hold_seconds", 0)):
                raise RuntimeError("host timeout omits independent exec/GUI/watchdog/recovery budgets; no USB action attempted")
        print(f"image {digest}; artifacts {out}", flush=True)
        if qualification:
            claim(qualification)
            manifest["single_media_qualification"] = "consumed-no-repeat"
        state = adb_state()
        if qualification and state != "recovery":
            raise RuntimeError("media qualification starts in recovery; bootstrap/extra boot forbidden")
        if early_watchdog and state is None and fastboot_visible():
            bootstrap = ROOT / "out/zorn/boot-ignition-natural-ee6681fd.img"
            if not bootstrap.is_file() or hashlib.sha256(bootstrap.read_bytes()).hexdigest() != \
                    "ee6681fd77ba97a3756a32d82a5d6487ba19428d9cf3cbc6c4c8fc4e5ac88548":
                raise RuntimeError("early watchdog needs recovery first; missing the pinned known-good recovery bootstrap")
            verify_bootloader()
            print("K80 fastboot -> known-good RAM bootstrap -> recovery", flush=True)
            boot = command(["fastboot", "-s", SERIAL, "boot", str(bootstrap)], timeout=60)
            (out / "bootstrap-fastboot.txt").write_text(boot)
            wait_for_recovery(args.timeout)
            state = "recovery"
            manifest["recovery_bootstrap_sha256"] = hashlib.sha256(bootstrap.read_bytes()).hexdigest()
            record()
        if state == "recovery":
            if qualification:
                exact_serial = command(["adb", "-s", SERIAL, "get-serialno"]).strip()
                exact_slot = command(["adb", "-s", SERIAL, "shell", "getprop", "ro.boot.slot_suffix"]).strip()
                if exact_serial != SERIAL or exact_slot != "_b":
                    raise RuntimeError("exact serial/slot b required before any BCB write")
            product = command(["adb", "-s", SERIAL, "shell", "getprop", "ro.product.device"]).strip()
            if product != "zorn":
                raise RuntimeError(f"unexpected recovery device: {product!r}")
            reader_spec = importlib.util.spec_from_file_location("zorn_reader", Path(__file__).with_name("read-zorn-log.py"))
            reader_module = importlib.util.module_from_spec(reader_spec)
            reader_spec.loader.exec_module(reader_module)
            before_log = reader_module.from_recovery()
            (out / "preboot-checkpoints.bin").write_bytes(before_log)
            manifest["preboot_log_sha256"] = hashlib.sha256(before_log).hexdigest()
            if early_watchdog:
                prepare_recovery_bcb(out)
                manifest["host_recovery_bcb_verified"] = True
                record()
            print("K80 recovery -> bootloader", flush=True)
            command(["adb", "-s", SERIAL, "reboot", "bootloader"])
        elif state is not None:
            raise RuntimeError(f"unexpected adb state {state!r}; require recovery or fastboot")
        deadline = time.monotonic() + 30
        while not fastboot_visible():
            if time.monotonic() >= deadline:
                raise RuntimeError("K80 did not appear in fastboot within 30 seconds")
            time.sleep(1)
        verify_bootloader()
        manifest.update(product="zorn", slot="b")
        record()
        print("verified zorn slot b; fastboot boot", flush=True)
        boot = command(["fastboot", "-s", SERIAL, "boot", str(image)], timeout=60)
        (out / "fastboot.txt").write_text(boot)
        print(boot, end="", flush=True)
        wait_for_recovery(args.timeout, args.capture_after, lambda elapsed: capture_screen(out, elapsed))
        print("recovery ADB online; reading checkpoint block", flush=True)
        reader = Path(__file__).with_name("read-zorn-log.py")
        if qualification:
            # Recover bytes first. Invalid/missing/mismatched early record is
            # unavailable, not a fabricated native failure or storage success.
            reader_spec = importlib.util.spec_from_file_location("qualification_reader", reader)
            reader_module = importlib.util.module_from_spec(reader_spec)
            reader_spec.loader.exec_module(reader_module)
            block = reader_module.from_recovery()
            (out / "checkpoints.bin").write_bytes(block)
            from qualification_policy import recovered_record
            observed = recovered_record(block, qualification["expected_path"], before_log)
            (out / "qualification-record.json").write_text(json.dumps(observed, indent=2)+"\n")
            manifest["qualification_record_available"] = observed["available"]
            manifest["native_commit_status_available"] = False
            if observed["available"]:
                log = command([sys.executable, str(reader), "--block", str(out / "checkpoints.bin"),
                               "--early-expected", qualification["expected_path"], "--tail", "100"])
            else:
                log = "qualification record unavailable: " + observed["reason"] + "\n"
        else:
            log = command([sys.executable, str(reader), "--save", str(out / "checkpoints.bin"),
                           "--tail", "100"])
        (out / "checkpoints.txt").write_text(log)
        print(log, end="", flush=True)
        after_log = hashlib.sha256((out / "checkpoints.bin").read_bytes()).hexdigest()
        manifest["kernel_log_changed"] = (after_log != manifest["preboot_log_sha256"]
                                          if "preboot_log_sha256" in manifest else None)
        if manifest["kernel_log_changed"] is False:
            print("kernel log is unchanged from before this boot; do not attribute its stages to this image", flush=True)
        manifest["bootreason"] = command(["adb", "-s", SERIAL, "shell", "getprop", "ro.boot.bootreason"]).strip()
        manifest.update(status="recovered", completed=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    except Exception as error:
        manifest.update(status="failed", error=str(error))
        raise
    finally:
        record()


if __name__ == "__main__":
    try:
        if '--ios26-lockscreen-touch-cpu-trial' in sys.argv:
            from zorn_ios26_lockscreen_touch_cpu_trial import main as lockscreen_touch_cpu
            lockscreen_touch_cpu()
        elif '--ios26-ft3683-trial' in sys.argv:
            from zorn_ios26_ft3683_trial import main as ft3683
            ft3683()
        elif '--ios26-native-smmu-cfgprobe-trial' in sys.argv:
            from zorn_ios26_native_smmu_cfgprobe_trial import main as native_smmu_cfgprobe
            native_smmu_cfgprobe()
        elif '--ios26-native-smmu-bootcpu-irq-trial' in sys.argv:
            from zorn_ios26_native_smmu_bootcpu_irq_trial import main as native_smmu_bootcpu_irq
            native_smmu_bootcpu_irq()
        elif '--ios26-native-smmu-irq-observed-trial' in sys.argv:
            from zorn_ios26_native_smmu_irq_observed_trial import main as native_smmu_irq_observed
            native_smmu_irq_observed()
        elif '--ios26-native-smmu-global-irq-trial' in sys.argv:
            from zorn_ios26_native_smmu_global_irq_trial import main as native_smmu_global_irq
            native_smmu_global_irq()
        elif '--ios26-native-cx-timer-trial' in sys.argv:
            from zorn_ios26_native_cx_timer_trial import main as native_cx_timer
            native_cx_timer()
        elif '--ios26-cxo-parentless-poll-trial' in sys.argv:
            from zorn_ios26_cxo_parentless_poll_trial import main as cxo_parentless_poll
            cxo_parentless_poll()
        elif '--ios26-gmu-clock-owned-frames-trial' in sys.argv:
            from zorn_ios26_gmu_clock_owned_frames_trial import main as gmu_clock_owned_frames
            gmu_clock_owned_frames()
        elif '--ios26-native-gmu-clocks-trial' in sys.argv:
            from zorn_ios26_native_gmu_clocks_trial import main as native_smmu_power
            native_smmu_power()
        elif '--ios26-native-smmu-probe-trial' in sys.argv:
            from zorn_ios26_native_smmu_probe_trial import main as native_smmu_power
            native_smmu_power()
        elif '--ios26-parentless-smmu-clock-trial' in sys.argv:
            from zorn_ios26_parentless_smmu_clock_trial import main as native_smmu_power
            native_smmu_power()
        elif '--ios26-smmu-power-results-trial' in sys.argv:
            from zorn_ios26_smmu_power_results_trial import main as native_smmu_power
            native_smmu_power()
        elif '--ios26-native-smmu-power-trial' in sys.argv:
            from zorn_ios26_native_smmu_power_trial import main as native_smmu_power
            native_smmu_power()
        elif '--ios26-native-cx-primary-trial' in sys.argv:
            from zorn_ios26_native_cx_primary_trial import main as native_cx_primary
            native_cx_primary()
        elif '--ios26-guarded-gpu-maps-trial' in sys.argv:
            from zorn_ios26_guarded_gpu_maps_trial import main as guarded_gpu_maps
            guarded_gpu_maps()
        elif '--ios26-native-register-maps-trial' in sys.argv:
            from zorn_ios26_native_register_maps_trial import main as cx_location_fix
            cx_location_fix()
        elif '--ios26-cx-location-fix-trial' in sys.argv:
            from zorn_ios26_cx_location_fix_trial import main as cx_location_fix
            cx_location_fix()
        elif '--ios26-domain-live-trial' in sys.argv:
            from zorn_ios26_domain_live_trial import main as domain_live
            domain_live()
        elif '--ios26-gpucc-lock-fix-trial' in sys.argv:
            from zorn_ios26_gpucc_lock_fix_trial import main as gpucc_lock_fix
            gpucc_lock_fix()
        elif '--ios26-gpucc-detail-trial' in sys.argv:
            from zorn_ios26_gpucc_detail_trial import main as gpucc_detail
            gpucc_detail()
        elif '--ios26-clock-live-trial' in sys.argv:
            from zorn_ios26_clock_live_trial import main as clock_live
            clock_live()
        elif '--ios26-rsc-enable-trial' in sys.argv:
            from zorn_ios26_rsc_enable_trial import main as rsc_enable
            rsc_enable()
        elif '--ios26-rsc-workloop-fix-trial' in sys.argv:
            from zorn_ios26_rsc_workloop_fix_trial import main as rsc_workloop_fix
            rsc_workloop_fix()
        elif '--ios26-rsc-factory-boundary-trial' in sys.argv:
            from zorn_ios26_rsc_factory_boundary_trial import main as rsc_factory_boundary
            rsc_factory_boundary()
        elif '--ios26-rsc-prewrite-boundary-trial' in sys.argv:
            from zorn_ios26_rsc_prewrite_boundary_trial import main as rsc_prewrite_boundary
            rsc_prewrite_boundary()
        elif '--ios26-rsc-reserve-boundary-trial' in sys.argv:
            from zorn_ios26_rsc_reserve_boundary_trial import main as rsc_reserve_boundary
            rsc_reserve_boundary()
        elif '--ios26-rsc-ram-checkpoint-trial' in sys.argv:
            from zorn_ios26_rsc_ram_checkpoint_trial import main as rsc_ram_checkpoint
            rsc_ram_checkpoint()
        elif '--ios26-rsc-screen-stage-trial' in sys.argv:
            from zorn_ios26_rsc_screen_stage_trial import main as rsc_screen_stage
            rsc_screen_stage()
        elif '--ios26-rsc-masked-stage-trial' in sys.argv:
            from zorn_ios26_rsc_masked_stage_trial import main as rsc_masked_stage
            rsc_masked_stage()
        elif '--ios26-rsc-only-trial' in sys.argv:
            from zorn_ios26_rsc_only_trial import main as rsc_only
            rsc_only()
        elif '--ios26-rsc-bootcpu-trial' in sys.argv:
            from zorn_ios26_rsc_bootcpu_trial import main as rsc_bootcpu
            rsc_bootcpu()
        elif '--ios26-gic-route-order-trial' in sys.argv:
            from zorn_ios26_gic_route_order_trial import main as gic_route_order
            gic_route_order()
        elif '--ios26-gic-observation-trial' in sys.argv:
            from zorn_ios26_gic_observation_trial import main as gic_observation
            gic_observation()
        elif '--ios26-rsc-clock-trial' in sys.argv:
            from zorn_ios26_rsc_clock_trial import main as rsc_clock
            rsc_clock()
        elif '--ios26-rsc-runtime-trial' in sys.argv:
            from zorn_ios26_rsc_runtime_trial import main as rsc_runtime
            rsc_runtime()
        elif any(flag in sys.argv for flag in ('--ios26-metal-display-trial', '--ios26-metal-cpu-presenter-trial', '--ios26-metal-first-swap-trial', '--ios26-current-root-userland-control-trial', '--ios26-current-root-finite-touch-userland-trial', '--ios26-cpu-display-vsync-trial', '--ios26-cpu-display-first-frame-trial', '--ios26-cpu-display-wait-trial', '--ios26-cpu-software-accelerator-trial', '--ios26-cpu-iosurface-root-trial', '--ios26-cpu-iosurface-platform-trial', '--ios26-cpu-iosurface-client-trial', '--ios26-cpu-iosurface-record-lock-trial', '--ios26-cpu-iosurface-create-trial', '--ios26-cpu-iosurface-init-trial', '--ios26-cpu-framebuffer-unsupported-trial', '--ios26-cpu-thread-census-trial', '--ios26-cpu-no-sampling-trial', '--ios26-cpu-sb-lifecycle-trial', '--ios26-cpu-sb-stderr-trial', '--ios26-cpu-crash-report-trial', '--ios26-cpu-crash-delivery-trial', '--ios26-cpu-crash-delivery-first-trial', '--ios26-cpu-corpse-notify-trial', '--ios26-cpu-reporter-files-trial', '--ios26-cpu-two-directory-report-trial', '--ios26-cpu-reporter-path-trial', '--ios26-cpu-general-log-trial', '--ios26-cpu-log-context-trial', '--ios26-cpu-osanalytics-trial', '--ios26-cpu-osanalytics-files-trial', '--ios26-cpu-springboard-reason-trial', '--ios26-cpu-springboard-stdio-trial', '--ios26-cpu-service-policy-trial', '--ios26-cpu-platform-identity-trial', '--ios26-cpu-work-interval-trial', '--ios26-cpu-display-scale-trial', '--ios26-cpu-continuity-trial', '--ios26-cpu-posterboard-trial', '--ios26-cpu-posterboard-reply-trial', '--ios26-cpu-posterboard-output-trial', '--ios26-cpu-posterboard-tail-trial', '--ios26-cpu-posterboard-entry-trial', '--ios26-cpu-posterboard-bits-trial', '--ios26-cpu-posterboard-wide-trial', '--ios26-cpu-posterboard-return-trial', '--ios26-cpu-posterboard-wait-trial', '--ios26-cpu-posterboard-passive-trial', '--ios26-cpu-sb-wallpaper-control-trial', '--ios26-cpu-sb-bootargs-trial', '--ios26-cpu-ui-display-wait-trial', '--ios26-cpu-sb-ulock-trial', '--ios26-cpu-sb-owner-trial', '--ios26-cpu-sb-peer-trial', '--ios26-cpu-lsd-vfs-trial', '--ios26-cpu-lsd-vfs-copylen-trial', '--ios26-cpu-lsd-vfs-budget-trial', '--ios26-cpu-lsd-vfs-prefix-trial', '--ios26-cpu-lsd-vfs-suffix-trial', '--ios26-cpu-network-identity-trial', '--ios26-cpu-long-window-trial', '--ios26-cpu-reply-destination-trial', '--ios26-cpu-reply-holder-trial', '--ios26-cpu-holder-name-trial', '--ios26-cpu-service-name-trial', '--ios26-cpu-keystore-trial', '--ios26-cpu-keystore-rerun-trial', '--ios26-cpu-keystore-retag-trial')):
            from zorn_ios26_metal_display_trial import main as metal_display_trial
            metal_display_trial()
        elif '--ios26-logdirs-boot-trial' in sys.argv:
            from zorn_ios26_logdirs_boot_trial import main as logdirs_boot
            logdirs_boot()
        elif '--ios26-cpu-host-preflight-recovery' in sys.argv:
            from zorn_ios26_cpu_host_preflight_recovery import main as cpu_host_preflight_recovery
            cpu_host_preflight_recovery()
        elif '--ios26-gpu-v73-recovery-requalify' in sys.argv:
            from zorn_ios26_gpu_v73_recovery_requalify import main as gpu_v73_recovery_requalify
            gpu_v73_recovery_requalify()
        elif '--ios26-gpu-v73-offset-recovery-requalify' in sys.argv:
            from zorn_ios26_gpu_v73_offset_recovery_requalify import main as gpu_v73_offset_recovery_requalify
            gpu_v73_offset_recovery_requalify()
        elif '--ios26-gpu-v73-offset-log-recovery-requalify' in sys.argv:
            from zorn_ios26_gpu_v73_offset_log_recovery_requalify import main as gpu_v73_offset_log_recovery_requalify
            gpu_v73_offset_log_recovery_requalify()
        elif '--ios26-finish-recovery' in sys.argv:
            from zorn_ios26_logdirs_boot_trial import finish_recovery
            finish_recovery()
        elif any(flag in sys.argv for flag in ('--ios26-metal-root-delta', '--ios26-metal-handle-lifetime-delta', '--ios26-cpu-no-sampling-root-delta', '--ios26-cpu-crash-report-root-delta', '--ios26-cpu-two-directory-root-delta', '--ios26-cpu-osanalytics-root-delta', '--ios26-cpu-service-policy-root-delta', '--ios26-cpu-posterboard-reply-root-delta', '--ios26-cpu-posterboard-reply-archive-root-delta', '--ios26-cpu-posterboard-entry-root-delta', '--ios26-cpu-posterboard-entry-root-delta', '--ios26-cpu-posterboard-passive-root-delta', '--ios26-gpu-application186-root-delta', '--ios26-metal193-root-delta', '--ios26-metal195-root-delta', '--ios26-metal197-root-delta', '--ios26-metal198-root-delta', '--ios26-metal199-root-delta', '--ios26-metal204-root-delta', '--ios26-metal207-root-delta', '--ios26-metal208-root-delta', '--ios26-metal209-root-delta', '--ios26-metal211-root-delta', '--ios26-metal213-root-delta', '--ios26-metal214-root-delta', '--ios26-metal215-root-delta', '--ios26-metal224-root-delta', '--ios26-metal226-root-delta', '--ios26-metal228-root-delta', '--ios26-metal229-root-delta', '--ios26-metal247-root-delta')):
            from zorn_ios26_metal_root_delta import main as metal_root_delta
            metal_root_delta()
        elif '--ios26-root-delta' in sys.argv:
            from zorn_ios26_root_delta import main as root_delta
            root_delta()
        elif '--ios26-userland-progress-trial' in sys.argv:
            from zorn_ios26_userland_progress_trial import main as userland_progress
            userland_progress()
        elif '--ios26-rsc-readonly-trial' in sys.argv:
            from zorn_ios26_rsc_readonly_trial import main as rsc_readonly
            rsc_readonly()
        elif '--ios26-commanddb-observation-trial' in sys.argv:
            from zorn_ios26_commanddb_observation_trial import main as commanddb_observation
            commanddb_observation()
        elif '--ios26-current-platform-trial' in sys.argv:
            from zorn_ios26_current_platform_trial import main as current_platform
            current_platform()
        elif '--ios26-platform-board-stage-trial' in sys.argv:
            from zorn_ios26_platform_board_stage_trial import main as trial_platform_board_stage
            trial_platform_board_stage()
        elif '--ios26-gpu-provider-census-v73-trial' in sys.argv:
            from zorn_ios26_gpu_provider_census_trial import main as trial_gpu_provider_census_v73
            trial_gpu_provider_census_v73()
        elif '--ios26-gpu-provider-census-predevice-002-trial' in sys.argv:
            from zorn_ios26_gpu_provider_census_predevice_002_trial import main as trial_gpu_provider_census_predevice_002
            trial_gpu_provider_census_predevice_002()

        elif '--ios26-gpu-provider-census-predevice-003-trial' in sys.argv:
            from zorn_ios26_gpu_provider_census_predevice_003_trial import main as trial_gpu_provider_census_predevice_003
            trial_gpu_provider_census_predevice_003()

        elif '--ios26-gpu-provider-census-predevice-004-trial' in sys.argv:
            from zorn_ios26_gpu_provider_census_predevice_004_trial import main as trial_gpu_provider_census_predevice_004
            trial_gpu_provider_census_predevice_004()
        elif '--ios26-presenter-known-image-trial' in sys.argv:
            from zorn_ios26_presenter_known_image_trial import main as trial_presenter_known_image
            trial_presenter_known_image()
        elif '--ios26-presenter-console-mode-trial' in sys.argv:
            from zorn_ios26_presenter_console_mode_trial import main as trial_presenter_console_mode
            trial_presenter_console_mode()
        elif '--ios26-presenter-refusal-trial' in sys.argv:
            from zorn_ios26_presenter_refusal_trial import main as trial_presenter_refusal
            trial_presenter_refusal()
        elif '--ios26-presenter-result-trial' in sys.argv:
            from zorn_ios26_presenter_result_trial import main as trial_presenter_result
            trial_presenter_result()
        elif '--ios26-CPU-presenter-trial' in sys.argv:
            from zorn_ios26_CPU_presenter_trial import main as trial_CPU_presenter
            trial_CPU_presenter()
        elif '--ios26-EL0-root-trial' in sys.argv:
            from zorn_ios26_EL0_root_trial import main as trial_EL0_root
            trial_EL0_root()
        elif '--ios26-PID1-root-trial' in sys.argv:
            from zorn_ios26_PID1_root_trial import main as trial_PID1_root
            trial_PID1_root()
        elif '--ios26-mounted-root-trial' in sys.argv:
            from zorn_ios26_mounted_root_trial import main as trial_mounted_root
            trial_mounted_root()
        elif '--ios26-current-root-trial' in sys.argv:
            from zorn_ios26_current_root_trial import main as trial_current_root
            trial_current_root()
        elif '--ios26-loader-bound-root-trial' in sys.argv:
            from zorn_ios26_loader_bound_root_trial import entry as trial_loader_bound_root
            trial_loader_bound_root()
        elif '--ios26-installed-root-trial' in sys.argv:
            from zorn_ios26_installed_root_trial import main as trial_installed_ios26_root
            trial_installed_ios26_root()
        elif '--ios26-verify-existing-root' in sys.argv:
            from zorn_ios26_root_verify import main as verify_existing_ios26_root
            verify_existing_ios26_root()
        elif '--ios26-recovery-crash-read' in sys.argv:
            from zorn_recovery_crash_read import main as read_recovery_crash
            read_recovery_crash()
        elif '--ios26-enter-recovery' in sys.argv:
            from zorn_enter_recovery import main as enter_ios26_recovery
            enter_ios26_recovery()
        elif '--ios26-install-root' in sys.argv:
            from zorn_ios26_root_install import main as install_ios26_root
            install_ios26_root()
        elif '--ios26-install-preflight' in sys.argv:
            from zorn_ios26_install_preflight import main as run_ios26_install_preflight
            run_ios26_install_preflight()
        elif '--ios26-root-input-probe-trial' in sys.argv:
            from zorn_ios26_root_input_probe import main as run_root_input_probe
            run_root_input_probe('run')
        elif '--ios26-platform-record-trial' in sys.argv:
            from zorn_gpu_ios26_platform_record import main as run_ios26_platform_record
            run_ios26_platform_record('run')
        elif '--ios26-platform-trial' in sys.argv:
            from zorn_gpu_ios26_platform import main as run_ios26_platform
            run_ios26_platform('run')
        elif '--gpu-resource-observation-trial' in sys.argv:
            from zorn_gpu_resource_trial import main as run_gpu_resource
            run_gpu_resource()
        elif '--gpu-unixnu64-media-trial' in sys.argv:
            from zorn_gpu_unixnu64_trial import main as run_gpu_unixnu64
            run_gpu_unixnu64()
        elif '--unixnu64-install-trial' in sys.argv:
            from zorn_unixnu64_run import main as run_unixnu64
            run_unixnu64()
        else:
            main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
