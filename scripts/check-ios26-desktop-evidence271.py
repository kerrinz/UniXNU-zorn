#!/usr/bin/env python3
"""Source-produced271 packet plus explicitly retagged historical wire fixtures."""
import argparse,hashlib,json,struct,subprocess,zlib
from pathlib import Path
from inspect_ios26_ui_desktop271 import inspect_progress,split_desktop,UI_MAGIC
from inspect_ios26_ui_roi270 import split_roi
from inspect_ios26_ui_scene269 import split_scene
from inspect_ios26_gpu_shot265 import split_stream
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wire270',type=Path,required=True);p.add_argument('--tag270',required=True);p.add_argument('--wire266',type=Path,required=True);p.add_argument('--tag266',required=True);p.add_argument('--tag',required=True);p.add_argument('--program-tag',required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    cpp=a.out/'actual-packet.cpp';exe=a.out/'actual-packet';packet=a.out/'SYNTHETIC-source271-ui.bin'
    cpp.write_text('#include "ZornUiDesktopWire271.h"\n#include <cstdio>\n#include <cassert>\nint main(){const uint32_t v[32]={6,0,1023,2,1,17,17,0,0,1020,16384,32112,8192,16,1,0,0,6,6,0,1,0,2400,28330,3938,6,400,30000,70000,0,0,0};const uint8_t tag[16]={'+','.join(str(x) for x in bytes.fromhex(a.tag))+'};char out[160];assert(ZornUiDesktopWire271::packet(out,160,v,tag)==160);assert(fwrite(out,1,160,stdout)==160);}\n')
    args=['xcrun','clang++','-std=c++17','-I'+str(a.source),str(cpp),'-o',str(exe)];r=subprocess.run(args,capture_output=True);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe)],capture_output=True);assert not r.returncode;rdata=r.stdout;assert len(rdata)==160;packet.write_bytes(rdata)
    raw=a.wire270.read_bytes();roi_free,_,_=split_roi(raw,a.tag270);normal,old_ui,_=split_scene(roi_free,a.tag270);assert len(old_ui)==1
    # Preserve actual ROI bytes but retag each binary header with a newCRC.
    at=0;roi=[]
    while at<len(raw):
        tail=raw[at:]
        if tail.startswith(b'K80SH270'):
            n=struct.unpack_from('<I',tail,28)[0];q=bytearray(tail[:68+n]);q[8:24]=bytes.fromhex(a.tag);struct.pack_into('<I',q,64,zlib.crc32(q[:64]));roi.append(bytes(q));at+=68+n
        elif tail.startswith(b'K80UI269'):at+=96
        else:at=raw.index(b'\r\n',at)+2
    normal=normal.replace(a.tag270.encode(),a.tag.encode());fixture=normal+rdata+b''.join(roi);r=inspect_progress(fixture,a.tag,a.program_tag)
    assert r['transport_frames_valid'] and r['kernel_known_task_complete266'] and r['complete_client_lifecycle268'] and r['Metal_probe267']['bounded_probe_and_required_lifecycle_complete'] and r['synthetic_desktop_dispatch_returned271'] and r['wire_nonterminal_frames271']==38 and r['serial_roi270']['complete']
    assert not r['probe_exit_gate269_selected'] and not r['Settings_long_press_functionally_qualified'] and not r['full_GPU_qualification']
    ordinary=b'\r\n'.join(split_stream(a.wire266.read_bytes(),a.tag266)[0].split(b'\r\n')[:30])+b'\r\n';ordinary=ordinary.replace(a.tag266.encode(),a.tag.encode());daemon=inspect_progress(ordinary+rdata,a.tag,a.program_tag)
    assert daemon['transport_frames_valid'] and daemon['synthetic_desktop_dispatch_returned271'] and not daemon['Metal_probe267']['bounded_probe_and_required_lifecycle_complete'] and not daemon['full_GPU_qualification']
    refused=[]
    def reject(label,data):
        try:inspect_progress(data,a.tag,a.program_tag)
        except ValueError:refused.append(label)
        else:raise AssertionError(label)
    reject('duplicate-UI271',fixture+rdata);reject('old-probe-only-UI269',a.wire270.read_bytes())
    for label,offset,value,crc in [('foreign-boot',8,1,False),('CRC',24,1,False),('schema',156,1,False),('press-coordinate',116,1,True),('reserved',140,1,True),('press-over-bound',92,7,True)]:
        q=bytearray(rdata);q[offset]^=value
        if crc:struct.pack_into('<I',q,152,zlib.crc32(q[:152]))
        reject(label,normal+q+b''.join(roi))
    for n in [1,7,8,24,151,152,159]:assert not inspect_progress(normal+rdata[:n],a.tag,a.program_tag)['transport_frames_valid']
    q=bytearray(rdata);struct.pack_into('<I',q,24,7);struct.pack_into('<I',q,88,3);struct.pack_into('<I',q,152,zlib.crc32(q[:152]));failure=inspect_progress(normal+q+b''.join(roi),a.tag,a.program_tag);assert failure['transport_frames_valid'] and not failure['synthetic_desktop_dispatch_returned271'] and failure['serial_roi270']['complete']
    (a.out/'SYNTHETIC-retagged-probe-reports-ROI-plus-UI271.bin').write_bytes(fixture);(a.out/'SYNTHETIC-retagged-live-backboardd-prefix-plus-UI271.bin').write_bytes(ordinary+rdata)
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());result=dict(passed=True,packet_source=pin(cpp),actual_wire_header=pin(a.source/'ZornUiDesktopWire271.h'),decoder=pin(Path(__file__).with_name('inspect_ios26_ui_desktop271.py')),source_packet=pin(packet),parent_actual270=pin(a.wire270),parent_actual266=pin(a.wire266),explicitly_synthetic_retagged_fixtures_not_hardware=True,no_old_probe269_readiness_semantics_reused=True,daemon_does_not_require_or_claim_probe_exit_or_four_closed_clients=True,failed_scene_keeps_valid_ROI_independent=True,refused=refused,partial_prefixes=7,phone_access=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS271 source-producedUI,explicitly retagged actual probe/live-daemon prefixes,ROI independence,',len(refused),'refusals/7partials;no hardware/menu proof')
if __name__=='__main__':main()
