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
for path in includes:
    command += ["-I", str(path)]
print(" ".join(command), flush=True)
subprocess.run(command, check=True)
archive = out / "libZornUfs.a"
archive.unlink(missing_ok=True)
subprocess.run(["xcrun", "ar", "rcs", str(archive), str(obj)], check=True)
print(archive)
