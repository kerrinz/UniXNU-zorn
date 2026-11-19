#!/usr/bin/env python3
"""Regress the real preceding CDC wire plus explicitly synthetic UI packets."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
from inspect_ios26_ui_scene269 import inspect_progress,split_scene,UI_MAGIC
from inspect_ios26_gpu_shot265 import SHOT_MAGIC
from inspect_ios26_gpu_progress236 import MAGIC

def packet(tag,values):
    raw=UI_MAGIC+bytes.fromhex(tag)+struct.pack('<16I',*values)
    return raw+struct.pack('<2I',zlib.crc32(raw),269)

def normal_prefix(data):
    """Retain30 complete normal frames and every exact SHOT packet,in order."""
    out=bytearray();at=0;normal=0;removed=[]
    while at<len(data):
        tail=data[at:]
        if tail.startswith(SHOT_MAGIC):
            assert len(tail)>=48;n=struct.unpack_from('<I',tail,28)[0];assert len(tail)>=48+n
            out.extend(tail[:48+n]);at+=48+n;continue
        assert not tail.startswith(MAGIC),'fixture has no terminal panic packet'
        end=data.index(b'\r\n',at)+2;line=data[at:end]
        if normal<30:out.extend(line)
        else:removed.append(dict(sequence=normal,bytes=len(line),sha256=hashlib.sha256(line).hexdigest()))
        normal+=1;at=end
    assert normal==31 and len(removed)==1
    return bytes(out),removed

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wire',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--program-tag',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    real=a.wire.read_bytes();prefix,removed=normal_prefix(real)
    good=[6,0,1023,1,1,17,17,0,0,1020,16384,32112,8192,16,1,0]
    ui=packet(a.tag,good);fixture=prefix+ui
    r=inspect_progress(fixture,a.tag,a.program_tag)
    assert r['transport_frames_valid'] and r['kernel_known_task_complete266'] and r['complete_client_lifecycle268']
    assert r['synthetic_scene_dispatch_returned269'] and r['wire_nonterminal_frames269']==38
    assert r['serial_shot265']['complete'] and not r['synthetic_unlock_proven269'] and not r['physical_FT3683_gestures_qualified269'] and not r['full_GPU_qualification']
    refused=[];incomplete=[]
    def reject(name,data):
        try:inspect_progress(data,a.tag,a.program_tag)
        except ValueError:refused.append(name)
        else:raise AssertionError(name)
    reject('untrimmed31normal-would-exceed-original-budget',real+ui)
    bad=bytearray(ui);bad[8]^=1;reject('foreign-boot',prefix+bad)
    bad=bytearray(ui);bad[88]^=1;reject('CRC',prefix+bad)
    bad=bytearray(ui);struct.pack_into('<I',bad,92,270);reject('schema',prefix+bad)
    reject('duplicate',fixture+ui)
    for field,value,name in [(0,5,'nonterminal-scene'),(2,2047,'unknown-flags'),(3,121,'poll-bound'),(4,2,'subscriber-boolean'),(5,18,'contact-bound'),(6,18,'return-bound'),(10,0,'geometry'),(15,4,'outcome')]:
        values=good.copy();values[field]=value;reject(name,prefix+packet(a.tag,values))
    for field,value,name in [(0,7,'failed-phase'),(1,5,'thread-failed'),(2,895,'no-successful-lift'),(2,511,'probe-readiness-unproven'),(5,16,'missing-contact'),(6,16,'missing-return'),(7,0xe00002c0,'contact-error'),(8,0xe00002c0,'lift-error'),(9,32001,'late-return'),(15,3,'dispatch-failure')]:
        values=good.copy();values[field]=value
        if name=='missing-contact':values[6]=value
        result=inspect_progress(prefix+packet(a.tag,values),a.tag,a.program_tag);assert not result['synthetic_scene_dispatch_returned269'],name;incomplete.append(name)
    for n in range(96):
        result=inspect_progress(prefix+ui[:n],a.tag,a.program_tag)
        assert not result['synthetic_scene_dispatch_returned269']
        if n:assert not result['transport_frames_valid']
    # Magic inside a real SHOT pixel payload cannot be treated as a UI packet;
    # a corrupted chunk must instead fail the retained original chunk CRC.
    bad=bytearray(prefix);at=bad.index(SHOT_MAGIC);bad[at+48:at+56]=UI_MAGIC
    reject('UI-magic-in-corrupt-pixels-not-a-terminal-record',bytes(bad)+ui)
    path=a.out/'synthetic-ui-on-bounded-real268-wire.bin';path.write_bytes(fixture)
    result=dict(passed=True,actual_parent_wire=dict(path=str(a.wire.resolve()),sha256=hashlib.sha256(real).hexdigest()),fixture=str(path),fixture_SHA256=hashlib.sha256(fixture).hexdigest(),fixture_scope='Explicit host fixture:exact268 bytes with one complete last ordinary frame removed to preserve30normal+7SHOT+1syntheticUI=38;actual boot/probe IDs retained. No269 hardware event or unlock claimed.',removed_normal_frames=removed,refused=refused,incomplete=incomplete,partial_UI_prefixes=96,raw_parent_Metal_result_preserved=r['Metal_probe267'],raw_parent_census_preserved=r['client_census268'],synthetic_unlock_proven=False,physical_FT3683_gestures_qualified=False,phone_access=False)
    decoder=Path(__file__).with_name('inspect_ios26_ui_scene269.py')
    result['decoder']=dict(path=str(decoder.resolve()),sha256=hashlib.sha256(decoder.read_bytes()).hexdigest())
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS UI269 evidence',len(refused),'refusals,',len(incomplete),'incomplete controls,96partial prefixes;no fabricated event delivery')
if __name__=='__main__':main()
