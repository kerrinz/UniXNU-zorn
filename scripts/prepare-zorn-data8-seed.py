#!/usr/bin/env python3
"""Verify the already grown8GiB minimal seed and unchanged template paths."""
from pathlib import Path
import hashlib,json,plistlib,stat,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/data-grow8'
sys.path.insert(0,str(ROOT/'UniXNU/drivers/DarwinBoot/Test'));import packed_ramdisk
base=json.loads((ROOT/'out/zorn/ram-data/desktop/seed.json').read_text())
seed=OUT/'base-8g.dbr';actual,header=packed_ramdisk.inspect(seed);grow=json.loads((OUT/'base-grow.log').read_text())
assert actual['bytes']==8*1024**3 and actual['sha256']==grow['sha256'] and actual['encoded_sha256']==grow['encoded_sha256']
assert header[32:36]==b'NXSB' and int.from_bytes(header[40:48],'little')*4096==actual['bytes']
assert hashlib.sha256((ROOT/base['seed']).read_bytes()).hexdigest()==base['encoded_sha256']
policy=json.loads((ROOT/'UniXNU-zorn/native/startup-policy/data-permissions.json').read_text())
assert policy['seed_encoded_sha256']==base['encoded_sha256']
run=lambda *args:subprocess.check_output(list(map(str,args)),stderr=subprocess.PIPE,timeout=60)
with tempfile.TemporaryDirectory(prefix='inspect8-',dir=OUT) as directory:
    d=Path(directory);raw=d/'data.raw';mount=d/'mounted';mount.mkdir();logical,extents=packed_ramdisk.regions(seed.read_bytes())
    with raw.open('wb') as f:
        f.truncate(logical)
        for offset,data in extents:f.seek(offset);f.write(data)
    info=plistlib.loads(run('hdiutil','attach','-readonly','-nobrowse','-owners','off','-imagekey','diskimage-class=CRawDiskImage','-mountpoint',mount,'-plist',raw))
    device=info['system-entities'][0]['dev-entry']
    try:
        volume=next(e for e in info['system-entities'] if e.get('mount-point')==str(mount))
        disk=plistlib.loads(run('diskutil','info','-plist',volume['dev-entry']))
        assert not disk['Writable'] and disk['VolumeUUID'].upper()==base['volume_uuid']
        for row in policy['entries']:
            assert stat.S_IFMT((mount/row['relative']).lstat().st_mode)==row['type'],row['relative']
        assert not (mount/'db/.unixnu-data-retained').exists()
    finally:run('hdiutil','detach',device)
report={**base,**actual,'seed':str(seed.relative_to(ROOT)),'guest_volatile':False,'persistent_backing':True,
        'storage_mode':'ufs-direct','grown_from_encoded_sha256':base['encoded_sha256'],
        'numeric_policy_paths_verified':len(policy['entries']),'grown_seed_readonly_verified':True,
        'fresh_initialization':True,'hardware_qualified':False,'phone_writes':False}
path=OUT/'seed.json'
if path.exists() and json.loads(path.read_text())!=report:raise ValueError('existing seed report differs')
path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
