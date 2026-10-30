#!/usr/bin/env python3
"""Prepare the pinned diagnostic input view; never build or access a device."""
from pathlib import Path
from zorn_legacy_device import prepare

device = Path(__file__).resolve().parents[1]
print(prepare(device, device.parent / 'out/zorn/legacy-device'))
