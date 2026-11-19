#!/usr/bin/env python3
"""Actual269 ordinary Metal/UI reports plus explicit source-produced synthetic ROI."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
from inspect_ios26_ui_roi270 import inspect_progress,split_roi,ROI_MAGIC
from inspect_ios26_gpu_shot265 import SHOT_MAGIC
from inspect_ios26_ui_scene269 import UI_MAGIC

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wire',type=Path,required=True);p.add_argument('--roi-wire',type=Path,required=True);p.add_argument('--parent-tag',required=True);p.add_argument('--tag',required=True);p.add_argument('--program-tag',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    raw=a.wire.read_bytes();at=0;rows=[];removed=[]
    while at<len(raw):
        tail=raw[at:]
        if tail.startswith(SHOT_MAGIC):
            n=struct.unpack_from('<I',tail,28)[0];removed.append(dict(bytes=48+n,sha256=hashlib.sha256(tail[:48+n]).hexdigest()));at+=48+n
        elif tail.startswith(UI_MAGIC):
            packet=bytearray(tail[:96]);assert zlib.crc32(packet[:88])==struct.unpack_from('<I',packet,88)[0];packet[8:24]=bytes.fromhex(a.tag);struct.pack_into('<I',packet,88,zlib.crc32(packet[:88]));rows.append(bytes(packet));at+=96
        else:
            end=raw.index(b'\r\n',at)+2;rows.append(raw[at:end].replace(a.parent_tag.encode(),a.tag.encode()));at=end
    assert len(removed)==7
    old=b''.join(rows);roi=a.roi_wire.read_bytes();fixture=old+roi;r=inspect_progress(fixture,a.tag,a.program_tag)
    assert r['transport_frames_valid'] and r['kernel_known_task_complete266'] and r['complete_client_lifecycle268'] and r['synthetic_scene_dispatch_returned269']
    assert r['serial_roi270']['complete'] and not r['serial_roi270']['full_screen_image'] and not r['legacy_full_frame_SHOT265_selected']
    assert r['wire_nonterminal_frames270']==38 and not r['synthetic_unlock_proven269'] and not r['ROI_image_is_final_UI_acceptance'] and not r['full_GPU_qualification']
    refused=[]
    def reject(name,data):
        try:inspect_progress(data,a.tag,a.program_tag)
        except ValueError:refused.append(name)
        else:raise AssertionError(name)
    reject('duplicate-ROI',fixture+roi)
    reject('old-full-frame-packet',old+raw[raw.index(SHOT_MAGIC):])
    bad=bytearray(roi);bad[8]^=1;reject('foreign-ROI-boot',old+bad)
    bad=bytearray(roi);bad[48]^=1;reject('ROI-geometry-not-covered-by-pixels-CRC',old+bad)
    bad=bytearray(roi);bad[68]^=1;reject('ROI-pixel-CRC',old+bad)
    partial=[]
    for n in [1,7,8,20,67,68,100,len(roi)-1]:
        report=inspect_progress(old+roi[:n],a.tag,a.program_tag);assert not report['transport_frames_valid'] and not report['serial_roi270']['complete'];partial.append(n)
    without=inspect_progress(old,a.tag,a.program_tag);assert without['transport_frames_valid'] and not without['serial_roi270']['complete'] and without['complete_client_lifecycle268']
    f=a.out/'SYNTHETIC-retagged269-reports-plus-host-ROI270.bin';f.write_bytes(fixture);pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());result=dict(passed=True,fixture=pin(f),parent_actual_wire=pin(a.wire),host_synthetic_ROI_wire=pin(a.roi_wire),removed_original_SHOT_packets=removed,explicit_boot_retag=dict(parent=a.parent_tag,candidate=a.tag,ordinary_text_and_UI_header_CRC_only=True),program_tag_unchanged=a.program_tag,refused=refused,partial_prefixes=partial,decoder=pin(Path(__file__).with_name('inspect_ios26_ui_roi270.py')),actual_parent_probe_reports_preserved=r['Metal_probe267'],actual_parent_census_preserved=r['client_census268'],raw_parent_UI_payload_preserved_except_boot_header_and_CRC=True,source_produced_ROI_geometry=r['serial_roi270']['source_roi'],fixture_is_not_hardware_or_settled_UI_evidence=True,phone_access=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS270 actual prior report + explicit host ROI framing,',len(refused),'refusals,',len(partial),'partial prefixes;no fabricated UI/physical image acceptance')
if __name__=='__main__':main()
