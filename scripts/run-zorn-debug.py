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
    args = parser.parse_args()
    if args.timeout < 10:
        parser.error("--timeout must be at least 10 seconds")
    if args.capture_after and not 30 <= args.capture_after <= args.timeout - 30:
        parser.error("--capture-after must be 0 or 30..timeout-30 seconds")
    image = args.image.resolve()
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
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
            (out / "build-inputs.json").write_bytes(inputs.read_bytes())
            early_watchdog = early_watchdog or build.get("early_watchdog_mode", 0) != 0
        if args.capture_after and (not build or not build.get("gui_watch") or not early_watchdog):
            raise RuntimeError("scheduled screen observation requires a ready GUI watchdog build")
        if build and build.get("gui_watch") and early_watchdog:
            from zorn_session_guard import minimum_gui_recovery_timeout
            if args.timeout < minimum_gui_recovery_timeout(build.get("gui_hold_seconds", 0)):
                raise RuntimeError("host timeout omits independent exec/GUI/watchdog/recovery budgets; no USB action attempted")
        print(f"image {digest}; artifacts {out}", flush=True)
        state = adb_state()
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
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
