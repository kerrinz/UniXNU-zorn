#!/usr/bin/env python3
"""Prepare original iPadOS 21H461 GUI symbols from a readonly local SystemOS.

Requires Apple's dyld-1125.5 format reference, already checked out locally.
Only metadata and file hashes belong in Git; cache/symbol binaries stay in out.
"""
import argparse,hashlib,json,plistlib,shutil,struct,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'out/zorn/gui-symbols')
parser.add_argument('--reference',type=Path,default=ROOT/'out/zorn/refer/dyld-1125.5')
parser.add_argument('--check-only',action='store_true',help='verify existing UUID/hash metadata without mounting an image')
args=parser.parse_args()
OUT=args.output.expanduser().resolve()
REF=args.reference.expanduser().resolve()
OUT.mkdir(parents=True,exist_ok=True)
if args.check_only:
    proof=json.loads((OUT/'inputs.json').read_text())
    assert proof['os']=='ipados-17.7.11-21H461' and proof['symbols_uuid_matches']
    for name in ('dyld_shared_cache_arm64','dyld_shared_cache_arm64.symbols'):
        h=hashlib.sha256()
        with (OUT/name).open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
        assert h.hexdigest()==proof['sha256'][name]
    print('Original GUI symbol inputs match their recorded hashes')
    raise SystemExit(0)
if any((OUT/name).exists() for name in ('inputs.json','dyld_shared_cache_arm64','dyld_shared_cache_arm64.symbols')):
    parser.error('Refuse to replace existing symbol inputs; use --check-only or a fresh --output')
MOUNT=OUT/'systemos-readonly'
MOUNT.mkdir(exist_ok=True)

def run(*args):
    return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE,timeout=120)

assert run('git','-C',REF,'rev-parse','HEAD').decode().strip()=='d1a0f6869ece370913a3f749617e457f3b4cd7c4'
fields=('imagesTextOffset','localSymbolsOffset','sharedRegionStart','symbolFileUUID','uuid')
cpp='#include <cstddef>\n#include <cstdio>\n#include "dyld_cache_format.h"\nint main(){\n'
for f in fields: cpp+=f'printf("{f} %zu\\n",offsetof(dyld_cache_header,{f}));\n'
cpp+='printf("image_size %zu\\n",sizeof(dyld_cache_image_text_info));\n'
cpp+='printf("local_info_size %zu\\n",sizeof(dyld_cache_local_symbols_info));\n'
cpp+='printf("local_entry_size %zu\\n",sizeof(dyld_cache_local_symbols_entry_64));}\n'
(OUT/'offsets.cpp').write_text(cpp)
run('xcrun','clang++','-std=c++17','-I',REF/'cache-builder',OUT/'offsets.cpp','-o',OUT/'offsets')
offsets={k:int(v) for k,v in (line.split() for line in run(OUT/'offsets').decode().splitlines())}
assert (offsets['image_size'],offsets['local_info_size'],offsets['local_entry_size'])==(32,24,16)
raw=None
try:
    info=plistlib.loads(run('hdiutil','attach','-readonly','-nobrowse','-noautoopen','-noautofsck','-owners','off',
        '-imagekey','diskimage-class=CRawDiskImage','-section','11874304,6451200','-mountpoint',MOUNT,'-plist',
        ROOT/'UniXNU/out/zorn/userdata/userdata-root.img'))
    raw=info['system-entities'][0]['dev-entry']
    volume=next(e for e in info['system-entities'] if e.get('mount-point')==str(MOUNT))
    disk=plistlib.loads(run('diskutil','info','-plist',volume['dev-entry']))
    assert not disk.get('Writable') and disk['VolumeUUID'].upper()=='8846FE78-2910-4297-AF97-D59BB6F8FC16'
    cache=MOUNT/'System/Library/Caches/com.apple.dyld'
    for name in ('dyld_shared_cache_arm64','dyld_shared_cache_arm64.symbols'):
        shutil.copyfile(cache/name,OUT/name)
finally:
    if raw:run('hdiutil','detach',raw)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

with (OUT/'dyld_shared_cache_arm64').open('rb') as f: main=f.read(1024)
with (OUT/'dyld_shared_cache_arm64.symbols').open('rb') as f: symbols=f.read(1024)
assert main[:16].rstrip(b'\0')==b'dyld_v1   arm64'
assert symbols[offsets['uuid']:offsets['uuid']+16]==main[offsets['symbolFileUUID']:offsets['symbolFileUUID']+16]
record={'os':'ipados-17.7.11-21H461','source_volume_uuid':disk['VolumeUUID'],'source_readonly':True,
        'original_inputs_modified':False,'offsets':offsets,'symbols_uuid_matches':True,
        'format_reference':'dyld-1125.5@d1a0f6869ece370913a3f749617e457f3b4cd7c4','sha256':{}}
for name in ('dyld_shared_cache_arm64','dyld_shared_cache_arm64.symbols'):
    record['sha256'][name]=digest(OUT/name)
(OUT/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
