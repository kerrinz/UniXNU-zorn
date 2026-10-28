#!/usr/bin/env python3
"""Check three pinned OS-profile UI-startup compatibility fixups, read-only.

These target AttentionAwareness and PosterBoardServices; they do not provide
a CPU renderer or disable accelerator discovery.

No system image bytes are changed. The kernel's existing signed-text mechanism
applies only matching bytes in RAM, after original page-signature validation.
"""
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import tomllib

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/zorn/cpu-profile'
OUT.mkdir(parents=True,exist_ok=True)
MOUNT=OUT/'systemos-readonly';MOUNT.mkdir(exist_ok=True)
PROFILE=ROOT/'UniXNU/profiles/os/ipados-17.7.11-21H461/profile.toml'
p=tomllib.loads(PROFILE.read_text())
assert p['kernel']['prelink']['kernelcache_sha256']=='f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7'
fixups=p['payload']['text_fixups'][:3]
assert fixups==['dyld_shared_cache_arm64.15,421e8bc,28ad1bb0008544f9,c0035fd6008544f9',
                'dyld_shared_cache_arm64.13,1b05bec,44008052,24008052',
                'dyld_shared_cache_arm64.13,1b05b08,44008052,24008052']
def run(*args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE,timeout=120)
raw=None;checks=[]
try:
 info=plistlib.loads(run('hdiutil','attach','-readonly','-nobrowse','-noautoopen','-noautofsck','-owners','off',
   '-imagekey','diskimage-class=CRawDiskImage','-section','11874304,6451200','-mountpoint',MOUNT,'-plist',
   ROOT/'UniXNU/out/zorn/userdata/userdata-root.img'))
 raw=info['system-entities'][0]['dev-entry']
 volume=next(e for e in info['system-entities'] if e.get('mount-point')==str(MOUNT))
 disk=plistlib.loads(run('diskutil','info','-plist',volume['dev-entry']))
 assert not disk.get('Writable') and disk['VolumeUUID'].upper()=='8846FE78-2910-4297-AF97-D59BB6F8FC16'
 for spec in fixups:
  name,offset,before,after=spec.split(',');matches=list(MOUNT.rglob(name));assert len(matches)==1,(name,matches)
  with matches[0].open('rb') as f:f.seek(int(offset,16));observed=f.read(len(bytes.fromhex(before)))
  assert observed==bytes.fromhex(before),(name,offset,observed.hex())
  checks.append(dict(entry=spec,file=str(matches[0].relative_to(MOUNT)),original_bytes_match=True))
finally:
 if raw:run('hdiutil','detach',raw)
report=dict(os='ipados-17.7.11-21H461',profile_sha256=hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
            source_systemos_uuid='8846FE78-2910-4297-AF97-D59BB6F8FC16',checks=checks,
            original_input_modified=False,applies_after_original_signature_validation=True,
            gpu_driver_enabled=False,gui_qualified=False)
(OUT/'profile.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
