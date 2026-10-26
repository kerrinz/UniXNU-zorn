#!/usr/bin/env python3
"""One unattended K80 round: recovery -> fastboot boot -> recovery -> saved log.

All device commands target 92988a43. The kernel image owns its checkpoint and
recovery reset; this host runner never flashes a partition or changes a slot.
"""
import argparse
import hashlib
import json
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=ROOT / "out/zorn/boot.img")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    if args.timeout < 10:
        parser.error("--timeout must be at least 10 seconds")
    image = args.image.resolve()
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    out = ROOT / "out/zorn/debug" / (time.strftime("%Y%m%d-%H%M%S-") + digest[:8])
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"serial": SERIAL, "image": str(image), "sha256": digest,
                "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": "started"}

    def record():
        (out / "run.json").write_text(json.dumps(manifest, indent=2) + "\n")

    record()
    try:
        inputs = ROOT / "out/zorn/boot.inputs.json"
        if image == (ROOT / "out/zorn/boot.img").resolve() and inputs.exists():
            build = json.loads(inputs.read_text())
            if build.get("status") != "ready" or build.get("sha256") != digest:
                raise RuntimeError("build manifest is not ready or does not match boot.img; rebuild with build-zorn-debug.py")
            (out / "build-inputs.json").write_bytes(inputs.read_bytes())
        print(f"image {digest}; artifacts {out}", flush=True)
        state = adb_state()
        if state == "recovery":
            product = command(["adb", "-s", SERIAL, "shell", "getprop", "ro.product.device"]).strip()
            if product != "zorn":
                raise RuntimeError(f"unexpected recovery device: {product!r}")
            print("K80 recovery -> bootloader", flush=True)
            command(["adb", "-s", SERIAL, "reboot", "bootloader"])
        elif state is not None:
            raise RuntimeError(f"unexpected adb state {state!r}; require recovery or fastboot")
        deadline = time.monotonic() + 30
        while not fastboot_visible():
            if time.monotonic() >= deadline:
                raise RuntimeError("K80 did not appear in fastboot within 30 seconds")
            time.sleep(1)
        product = command(["fastboot", "-s", SERIAL, "getvar", "product"])
        slot = command(["fastboot", "-s", SERIAL, "getvar", "current-slot"])
        if "product: zorn" not in product or "current-slot: b" not in slot:
            raise RuntimeError(f"unexpected bootloader identity/slot:\n{product}{slot}")
        manifest.update(product="zorn", slot="b")
        record()
        print("verified zorn slot b; fastboot boot", flush=True)
        boot = command(["fastboot", "-s", SERIAL, "boot", str(image)], timeout=60)
        (out / "fastboot.txt").write_text(boot)
        print(boot, end="", flush=True)
        deadline = time.monotonic() + args.timeout
        next_notice = time.monotonic() + 20
        while True:
            state = adb_state()
            if state == "recovery":
                break
            if state is not None:
                raise RuntimeError(f"unexpected adb state after boot: {state!r}")
            now = time.monotonic()
            if now >= deadline:
                raise RuntimeError(f"no recovery ADB after {args.timeout} seconds; no further reboot attempted")
            if now >= next_notice:
                print("waiting for recovery ADB", flush=True)
                next_notice = now + 20
            time.sleep(2)
        print("recovery ADB online; reading checkpoint block", flush=True)
        reader = Path(__file__).with_name("read-zorn-log.py")
        log = command([sys.executable, str(reader), "--save", str(out / "checkpoints.bin"),
                       "--tail", "100"])
        (out / "checkpoints.txt").write_text(log)
        print(log, end="", flush=True)
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
