#!/usr/bin/env python3
"""Define symbols the development kernel references before zorn has those drivers.

Without the display profile, native_legacy_display_probe has an empty
development-only definition. With GopFramebuffer selected, this archive has
no display symbol: the qualified real archive supplies both lifecycle hooks.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/zorn-stubs"
OUT.mkdir(parents=True, exist_ok=True)
source = OUT / "link-stubs.c"
display_enabled = "CONFIG_XNU_NATIVE_LEGACY_DISPLAY=y" in (ROOT.parent / ".config").read_text().splitlines()
source.write_text("/* Real display archive supplies its initialization hooks. */\n" if display_enabled
                  else "void native_legacy_display_probe(void) {}\n")
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
