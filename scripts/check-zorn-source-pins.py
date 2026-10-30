#!/usr/bin/env python3
"""Verify the selected local component versions and bytes without fetching."""
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace

device = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, default=device.parent / 'UniXNU')
parser.add_argument('--pins', type=Path, default=device / 'source-pins.json')
args = parser.parse_args()
sys.path.insert(0, str(args.core.resolve() / 'scripts'))
from unixnu.feeds import verify_frozen_submodules

verify_frozen_submodules(
    SimpleNamespace(root=args.core.resolve(), device=device), args.pins.resolve(),
)
