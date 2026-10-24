#!/usr/bin/env python3
"""Define symbols the development kernel references before zorn has those drivers.

native_legacy_display_probe is called from bsd_init only when the boot argument
offline-legacy-register is set. The real archive is qualified against another
board's kernelcache, so this empty definition is enough to finish the link.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/zorn-stubs"
OUT.mkdir(parents=True, exist_ok=True)
source = OUT / "link-stubs.c"
source.write_text("void native_legacy_display_probe(void) {}\n")
obj = OUT / "link-stubs.o"
sdk = subprocess.check_output(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], text=True).strip()
subprocess.run(
    ["xcrun", "--sdk", "iphoneos", "clang", "-target", "arm64-apple-ios17.0",
     "-isysroot", sdk, "-mkernel", "-ffreestanding", "-fno-builtin", "-c",
     str(source), "-o", str(obj)],
    check=True,
)
archive = OUT / "libZornLinkStubs.a"
archive.unlink(missing_ok=True)
subprocess.run(["xcrun", "ar", "rcs", str(archive), str(obj)], check=True)
print(archive)
