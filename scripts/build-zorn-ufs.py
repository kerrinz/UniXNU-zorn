#!/usr/bin/env python3
"""Build the read-only zorn UFS probe and leave libZornUfs.a in the tree."""
import subprocess
import sys
import json
import os
from pathlib import Path

TREE = Path.cwd()
STATE = TREE.parents[1] / "state.json"
try:
    DEVICE = Path(os.environ["UNIXNU_DEVICE"] if "UNIXNU_DEVICE" in os.environ
                  else json.loads(STATE.read_text())["device"]).expanduser().resolve()
except (OSError, KeyError, ValueError) as error:
    sys.exit(f"cannot locate UniXNU device repository: {error}")
SOURCE = DEVICE / "native/ufs-read"
HEADERS = TREE / "build/xnu/ios-obj/EXPORT_HDRS"
OBJDIR = TREE / "build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT"
if not (SOURCE / "ZornUfsRead.cpp").is_file():
    sys.exit(f"missing {SOURCE / 'ZornUfsRead.cpp'}")
if not (HEADERS / "iokit").is_dir():
    sys.exit(f"missing kernel headers under {HEADERS}; build the kernel once first")

clang = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++"
out = TREE / "build/zorn-ufs"
out.mkdir(parents=True, exist_ok=True)
obj = out / "ZornUfsRead.o"
includes = [
    OBJDIR,
    SOURCE,
    HEADERS / "iokit",
    HEADERS / "osfmk",
    HEADERS / "bsd",
    HEADERS / "libkern",
    HEADERS / "pexpert",
    HEADERS / "libsa",
    HEADERS / "security",
    HEADERS / "san",
    TREE / ".cache/xnu-work/EXTERNAL_HEADERS",
    TREE / ".cache/xnu-work/iokit",
    TREE / ".cache/fakeroot/usr/local/include/kernel",
    TREE / ".cache/fakeroot/usr/local/include",
]
command = [
    clang, "-std=gnu++17", "-c", str(SOURCE / "ZornUfsRead.cpp"), "-o", str(obj),
    "-nostdlibinc", "-fno-builtin", "-fno-common", "-ftrivial-auto-var-init=zero",
    "-fsigned-bitfields", "-fc++-static-destructors=none", "-fno-exceptions",
    "-mkernel", "-O2", "-mios-version-min=17.0", "-arch", "arm64",
    "--target=arm64-apple-ios17.0.0",
    "-include", str(OBJDIR / "meta_features.h"),
    "-D", "KERNEL", "-D", "KERNEL_PRIVATE", "-D", "XNU_KERNEL_PRIVATE",
    "-D", "PRIVATE", "-D", "IOKIT", "-D", "LIBKERNCPP", "-D", "MACH",
    "-D", "APPLE", "-D", "__MACHO__=1", "-D", "LP64", "-D", "arm64",
    "-D", "ARM64", "-D", "__ARM64__", "-D", "XNU_TARGET_OS_IOS",
    "-D", "ARM64_BOARD_CONFIG_BCM2837",
    "-D", "CONFIG_EMBEDDED", "-D", "DRIVER_PRIVATE", "-D", "IOKIT_KERNEL_PRIVATE",
    "-Wno-unused-function", "-Wno-unused-variable", "-Wno-unused-parameter",
    "-Wno-c++98-compat", "-Wno-c++17-extensions", "-Wno-c99-extensions",
]
config = (TREE.parent / ".config").read_text().splitlines()
verified = "CONFIG_XNU_ZORN_VERIFIED_ROOT=y" in config
if verified:
    command += ["-DZORN_VERIFIED_ROOT=1"]
if "CONFIG_XNU_NATIVE_RAM_BLOCK=y" in config:
    command += ["-DZORN_RAM_DATA=1"]
if "CONFIG_XNU_NATIVE_LEGACY_DISPLAY=y" in config:
    command += ["-DZORN_DISPLAY=1"]
if os.environ.get('UNIXNU_ZORN_SMP','0')=='8':
    command += ["-DZORN_SMP_PREFLIGHT=1"]
if os.environ.get('UNIXNU_ZORN_DATA_PROFILE','512m')=='8g':
    command += ["-DZORN_DATA_8G=1"]
if os.environ.get('UNIXNU_ZORN_TOUCH_RUNTIME','0')=='1':
    command += ["-DZORN_TOUCH_RUNTIME_ENABLED=1"]
for path in includes:
    command += ["-I", str(path)]
print(" ".join(command), flush=True)
subprocess.run(command, check=True)
if verified:
    subprocess.run([sys.executable, TREE / "scripts/build-zorn-storage.py"], check=True)
archive = out / "libZornUfs.a"
archive.unlink(missing_ok=True)
storage = TREE / "build/zorn-storage"
objects = [obj]
if verified:
    # Keep the syscall ABI of the actual BSD compile record. Policy runs only
    # after the independent writable RAM Data mount, before original launchd.
    record_path = TREE / "build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/kern_exec.o.json"
    record = json.loads(record_path.read_text().strip().rstrip(","))
    policy_source = DEVICE / "native/startup-policy/BootWatchdogPolicy.c"
    policy_object = out / "BootWatchdogPolicy.o"
    policy_command = []
    arguments = record["arguments"]
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value == record["file"]:
            policy_command.append(str(policy_source))
        elif value == "-o":
            policy_command += ["-o", str(policy_object)]
            index += 1
        elif value in ("-MF", "-MJ", "-MT"):
            index += 1
        elif value not in ("-MD", "-MP"):
            policy_command.append(value)
        index += 1
    policy_command.append("-mgeneral-regs-only")
    subprocess.run(policy_command, cwd=record["directory"], check=True)
    objects.append(policy_object)
    permissions_source = DEVICE / "native/startup-policy/DataPermissions.c"
    permissions_object = out / "DataPermissions.o"
    permissions_command = [str(permissions_source) if value == str(policy_source) else
                           str(permissions_object) if value == str(policy_object) else value
                           for value in policy_command]
    subprocess.run(permissions_command, cwd=record["directory"], check=True)
    objects.append(permissions_object)
    marker_source = DEVICE / ("native/startup-policy/DataMarker.c" if
        "CONFIG_XNU_NATIVE_RAM_BLOCK=y" in config else "native/startup-policy/DataUnavailable.c")
    marker_object = out / "DataMarker.o"
    marker_command = [str(marker_source) if value == str(policy_source) else
                      str(marker_object) if value == str(policy_object) else value
                      for value in policy_command]
    subprocess.run(marker_command, cwd=record["directory"], check=True)
    objects.append(marker_object)
if verified:
    objects += [storage / "ZornUfsBlock.late.o", storage / "original-bindings.o"]
subprocess.run(["xcrun", "ar", "rcs", str(archive), *objects], check=True)
print(archive)
