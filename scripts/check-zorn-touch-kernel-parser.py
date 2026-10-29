#!/usr/bin/env python3
"""Refuse catalogue selectors broader than the owned FT3683 touchscreen."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import plistlib
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "UniXNU-zorn/native/display/ZornTouchKernelMatch.h"
xml = re.search(r'R"plist\((.*?)\)plist"', HEADER.read_text(), re.S).group(1)
policy = plistlib.loads(('<plist version="1.0">' + xml + '</plist>').encode())

def validate(p):
    assert set(p) == {"CFBundleIdentifier", "IOClass", "IOProviderClass", "IOProbeScore",
        "IOMatchDefer", "HIDDefaultBehavior", "Product", "Transport", "IOPropertyMatch", "DeviceUsagePairs"}
    assert p["CFBundleIdentifier"] == "com.apple.iokit.IOHIDFamily"
    assert p["IOClass"] == "IOHIDEventDriver" and p["IOProviderClass"] == "IOHIDInterface"
    assert p["IOProbeScore"] == 100000 and p["IOMatchDefer"] is False
    assert p["HIDDefaultBehavior"] == ""
    assert p["Product"] == "Redmi K80 FT3683 Touchscreen" and p["Transport"] == "SPI"
    assert p["IOPropertyMatch"] == {"Product": p["Product"], "Transport": p["Transport"]}
    assert p["DeviceUsagePairs"] == [{"DeviceUsagePage": 13, "DeviceUsage": 4}]

validate(policy)
controls = []
for key in ("Product", "Transport", "IOPropertyMatch", "DeviceUsagePairs"):
    p = deepcopy(policy)
    del p[key]
    controls.append(p)
for key, value in (("IOClass", "AppleUserHIDEventService"),
                   ("IOProviderClass", "IOService"), ("Product", ""),
                   ("IOPropertyMatch", {}), ("DeviceUsagePairs", [])):
    p = deepcopy(policy)
    p[key] = value
    controls.append(p)
for p in controls:
    try:
        validate(p)
    except AssertionError:
        pass
    else:
        raise AssertionError("broadened input personality accepted")
# This argument refusal occurs before build-state or USB operations.
r = subprocess.run([sys.executable, str(ROOT / "UniXNU-zorn/scripts/build-zorn-debug.py"),
                    "--touch-kernel-parser"], capture_output=True, text=True)
assert r.returncode == 2 and "--touch-kernel-parser requires --touch-runtime" in r.stderr
result = dict(passed=True, header_sha256=hashlib.sha256(HEADER.read_bytes()).hexdigest(),
    exact_owned_product_transport_and_touch_usage=True, unknown_or_broadened_policies_rejected=len(controls),
    default_off_cli_guard=True, runtime_catalogue_registration_qualified=False)
out = ROOT / "out/zorn/touch/kernel-parser-host-check.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
