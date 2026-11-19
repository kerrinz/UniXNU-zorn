#!/usr/bin/env python3
"""Execute the real288 late-run decoder on explicitly retagged host fixtures."""
import argparse, copy, hashlib, json, struct, zlib
from pathlib import Path
import zorn_ios26_gpu_v288_system_trial as t
from zorn_gpu_ios26_platform_record import artifact_tag, record_inspector

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir()
    state=t.CURRENT.read_bytes();bundle=t.validate(t.TRIAL/'bundle.json')
    before=(t.BASE.parent/'k80-gpu-v281-upstream-known-image-36e4614944b04a64bee5499cb2e8338f/root-trial/trial/before-log.bin').read_bytes()
    original=(t.BASE.parent/'k80-gpu-v281-upstream-known-image-36e4614944b04a64bee5499cb2e8338f/root-trial/trial/after-log.bin').read_bytes()
    fixture=bytearray(original);fixture[8:24]=bytes.fromhex(t.TAG);fixture[28:32]=bytes(4);struct.pack_into('<I',fixture,28,zlib.crc32(fixture[:544]))
    decoder=record_inspector(bundle);tag=artifact_tag(bundle);assert tag==bytes.fromhex(t.TAG)
    decoded=decoder(fixture,tag,before);result=t.record_result(decoded)
    assert decoded['cpu_online']==8 and result['root_mount_proven']
    checks=['actual shared decoder factory and actual record_result callback complete on explicit host-only fixture']
    for name,change in [('missing semantic role',lambda x:x['pins'].pop('record_decoder')),
                        ('changed pinned decoder',lambda x:x['pins']['record_decoder'].update(sha256='0'*64))]:
        bad=copy.deepcopy(bundle);change(bad)
        try:record_inspector(bad)
        except (ValueError,KeyError):checks.append(name+' refused')
        else:raise AssertionError(name)
    try:decoder(fixture,tag,fixture)
    except ValueError:checks.append('stale record refused')
    else:raise AssertionError('stale record')
    assert t.CURRENT.read_bytes()==state and not (t.TRIAL/'trial/one-shot.claim.json').exists()
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=t.sha(p))
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,source=pin(t.__file__),test_tool=pin(__file__),helper=pin(Path(__file__).with_name('zorn_gpu_ios26_platform_record.py')),bundle=pin(t.TRIAL/'bundle.json'),explicit_synthetic_retagged_fixture=True,phone_access=False,hardware_qualified=False),indent=2)+'\n')
    print('PASS288 actual late-run record consumer and callback;no device access')
if __name__=='__main__':main()
