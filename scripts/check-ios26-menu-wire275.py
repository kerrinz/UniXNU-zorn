#!/usr/bin/env python3
"""Retain actual270 sampler/late-stream controls with the new416-byte UI frame."""
import hashlib,importlib.util,json,sys
from pathlib import Path
def main():
    f=Path(__file__).with_name('check-ios26-roi270.py');spec=importlib.util.spec_from_file_location('retained_roi270_controls',f);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    base.TEST=base.TEST.replace('#include "ZornSerialShot270.h"','#include "ZornSerialShot270.h"\n#include "ZornUiMenuWire275.h"').replace('uint32_t status[16]{}','uint32_t status[96]{}').replace('ZornUiSceneWire269::packet(p,cap,status,tag)','ZornUiMenuWire275::packet(p,cap,status,tag)')
    assert 'ZornUiSceneWire269::packet' not in base.TEST and 'ZornUiMenuWire275::packet' in base.TEST
    base.main();out=Path(sys.argv[sys.argv.index('--out')+1]);source=Path(sys.argv[sys.argv.index('--source')+1]);r=json.loads((out/'result.json').read_text());pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());r.update(new_UI_packet_bytes=416,actual_UI275_wire_header=pin(source/'ZornUiMenuWire275.h'),retained_test_base=pin(f),test_tool=pin(Path(__file__)),no_old_UI_readiness_interpretation=True);(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS275 actual416byte UI with unchanged30normal/7ROI/38frame/late Pending controls')
if __name__=='__main__':main()
