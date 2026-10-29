"""Explicit Data geometry; the legacy512MiB profile remains the default."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parents[2]
NAME=os.environ.get('UNIXNU_ZORN_DATA_PROFILE','512m')
if NAME not in ('512m','8g'):raise ValueError('unqualified Data profile')
LARGE=NAME=='8g'
DIRECTORY=ROOT/('out/zorn/data-store8-192' if LARGE else 'out/zorn/data-store')
SEED_REPORT=ROOT/('out/zorn/data-grow8/seed.json' if LARGE else 'out/zorn/ram-data/desktop/seed.json')
RELATIVE_FIRST=(192 if LARGE else 10)*1024**3//4096
PAGES=(8*1024**3 if LARGE else 512*1024**2)//4096
BITMAP_BLOCKS=(PAGES+32767)//32768
WINDOW_BLOCKS=1+BITMAP_BLOCKS+PAGES
