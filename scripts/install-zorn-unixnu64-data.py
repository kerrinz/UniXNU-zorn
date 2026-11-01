#!/usr/bin/env python3
"""Initialize a fresh 8GiB COW Data store only inside the new unixnu64 partition.

This is the owner's new installation, not a migration or reset of the historical
userdata-backed store. Only 65 metadata blocks are written; an empty bitmap
keeps all uninitialized backing pages inaccessible to the filesystem.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import struct
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'out/zorn/dual-system-reinstall-20261101'
ADB = os.environ.get('UNIXNU_ADB', 'adb')
BASE = [ADB,'-s','92988a43']
PARTITION = '/dev/block/by-name/unixnu'
FIRST = 4194304
PAGES = 2097152
WINDOW = 2097217
META = 65


def adb(*args):
    return subprocess.check_output([*BASE,*map(str,args)],timeout=30)


def read(device, first, count):
    if device not in (PARTITION, '/dev/block/sda') or first < 0 or not 0 < count <= 65:
        raise ValueError('invalid bounded read')
    data = adb('exec-out',f'dd if={device} bs=4096 skip={first} count={count} 2>/dev/null')
    if len(data) != count*4096: raise ValueError('short bounded read')
    return data


def boundaries():
    for args, expected in [
        (('get-serialno',),'92988a43'),
        (('shell','getprop','ro.product.device'),'zorn'),
        (('shell','getprop','ro.boot.slot_suffix'),'_a'),
        (('shell','getprop','ro.orangefox.boot'),'1'),
        (('shell','readlink','-f',PARTITION),'/dev/block/sda35'),
        (('shell','blockdev','--getsize64',PARTITION),'68719476736'),
        (('shell','blockdev','--getss','/dev/block/sda'),'4096')]:
        if adb(*args).decode().strip() != expected: raise ValueError('Recovery identity/geometry changed')
    mounted = adb('shell','cat','/proc/mounts').decode()
    if any(line.split()[0] in (PARTITION,'/dev/block/sda35') for line in mounted.splitlines()):
        raise ValueError('unixnu unexpectedly mounted')
    primary = read('/dev/block/sda',0,6)
    if primary != (OUT/'plan64-applied-tty/gpt-primary.after').read_bytes():
        raise ValueError('primary GPT changed')
    backup_lba = struct.unpack_from('<Q',primary,4096+32)[0]
    backup = read('/dev/block/sda',backup_lba-4,5)
    if backup != (OUT/'plan64-applied-tty/gpt-backup.after').read_bytes():
        raise ValueError('backup GPT changed')
    manifest = read(PARTITION,0,1)
    with (ROOT/'UniXNU/out/zorn/userdata/userdata-root.img').open('rb') as stream:
        if manifest != stream.read(4096): raise ValueError('iOS root manifest changed')
    return dict(primary=primary,backup=backup,manifest=manifest,
                before=read(PARTITION,FIRST-1,1),after=read(PARTITION,FIRST+WINDOW,1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialize',action='store_true',required=True)
    parser.parse_args()
    verify = json.loads((OUT/'ios-install-verification.json').read_text())
    if verify.get('full_image_readback') is not True: raise ValueError('complete iOS readback required')
    out = OUT/'data-store'; out.mkdir(exist_ok=True)
    if (out/'install-attempt.json').exists(): raise ValueError('installation already attempted; inspect before retry')
    original = boundaries()
    seed = json.loads((ROOT/'out/zorn/data-grow8/seed.json').read_text())
    if seed['bytes'] != PAGES*4096 or seed['volume_uuid'] != 'C7D77FF3-6437-4C4A-8E05-E8E239AC1641':
        raise ValueError('wrong Data seed')
    metadata = bytearray(META*4096); metadata[:8] = b'SHNGDATA'
    struct.pack_into('<IIQ',metadata,8,1,64,PAGES)
    metadata[24:56] = bytes.fromhex(seed['sha256'])
    cookie = secrets.randbelow(0xffffffff)+1
    struct.pack_into('<I',metadata,56,cookie)
    struct.pack_into('<I',metadata,60,zlib.crc32(metadata[:60]))
    for name, data in original.items(): (out/(name+'.before.bin')).write_bytes(data)
    (out/'metadata.preimage.bin').write_bytes(read(PARTITION,FIRST,META))
    local = out/'fresh-overlay-metadata.bin'; local.write_bytes(metadata)
    remote = '/tmp/unixnu64-data-metadata.bin'
    adb('push',local,remote)
    if adb('exec-out','cat',remote) != metadata: raise ValueError('tmpfs metadata differs')
    if original != boundaries(): raise ValueError('storage changed before metadata write')
    attempt = dict(serial='92988a43',slot='a',target=PARTITION,relative_first=FIRST,
        blocks=META,window_blocks=WINDOW,logical_Data_bytes=PAGES*4096,
        cookie=cookie,seed_sha256=seed['sha256'],volume_uuid=seed['volume_uuid'],
        metadata_sha256=hashlib.sha256(metadata).hexdigest(),status='write-attempting',
        new_installation=True,historical_Data_reset=False,Android_userdata_written=False)
    record = out/'install-attempt.json'; record.write_text(json.dumps(attempt,indent=2)+'\n')
    adb('shell','dd','if='+remote,'of='+PARTITION,'bs=4096','seek='+str(FIRST),
        'count='+str(META),'conv=notrunc')
    adb('shell','sync')
    if read(PARTITION,FIRST,META) != metadata: raise ValueError('metadata readback differs')
    if original != boundaries(): raise ValueError('GPT/root/fences changed')
    attempt.update(status='installed-readback-verified',GPT_root_fences_unchanged=True,
                   ios_boot_qualified=False,Android_boot_verified=False)
    record.write_text(json.dumps(attempt,indent=2)+'\n')
    (out/'plan.json').write_text(json.dumps(dict(attempt,installed=True,data_profile='8g',
        storage_profile='unixnu64',relative_first_lba=FIRST,absolute_first_lba=47271680+FIRST,
        pages=PAGES,bitmap_blocks=64,blocks=WINDOW),indent=2)+'\n')
    print(json.dumps(attempt,indent=2))


if __name__ == '__main__': main()
