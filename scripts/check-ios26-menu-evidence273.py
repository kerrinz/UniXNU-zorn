#!/usr/bin/env python3
"""Source273 packet over explicitly retagged real271wire;never a real menu image."""
import argparse,hashlib,json,struct,subprocess,zlib
from pathlib import Path
from inspect_ios26_ui_desktop271 import split_desktop
from inspect_ios26_ui_menu273 import inspect_progress
from inspect_ios26_ui_roi270 import split_roi
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wire',type=Path,required=True);p.add_argument('--parent-tag',required=True);p.add_argument('--tag',required=True);p.add_argument('--program-tag',required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    v=[6,0,1023,2,1,17,17,0,0,1020,16384,32112,8192,16,1,0,0,2,2,0,1,0,800,28330,3938,2,400,30000,70000,1,151020,153820]+[7,259,262,262,262,292,0,0,0,0,129,3,1,4338,10,10]+[7,265,268,268,268,299,0,0,0,0,129,3,1,4400,10,10];assert len(v)==64
    cpp=a.out/'actual-packet.cpp';exe=a.out/'packet';cpp.write_text('#include "ZornUiMenuWire273.h"\n#include <cassert>\n#include <cstdio>\nint main(){const uint32_t v[64]={'+','.join(map(str,v))+'};const uint8_t tag[16]={'+','.join(map(str,bytes.fromhex(a.tag)))+'};char p[288];assert(ZornUiMenuWire273::packet(p,sizeof(p),v,tag)==288);assert(fwrite(p,1,288,stdout)==288);}\n');args=['xcrun','clang++','-std=c++17','-I'+str(a.source),str(cpp),'-o',str(exe)];r=subprocess.run(args,capture_output=True);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe)],capture_output=True);assert not r.returncode and len(r.stdout)==288;packet=r.stdout;(a.out/'SYNTHETIC-source273-packet.bin').write_bytes(packet)
    raw=a.wire.read_bytes();stripped,old,_=split_desktop(raw,a.parent_tag);assert len(old)==1;normal,_,roi=split_roi(stripped,a.parent_tag);assert roi['complete'];normal=normal.replace(a.parent_tag.encode(),a.tag.encode());at=0;images=[]
    while at<len(raw):
        tail=raw[at:]
        if tail.startswith(b'K80SH270'):
            n=struct.unpack_from('<I',tail,28)[0];q=bytearray(tail[:68+n]);q[8:24]=bytes.fromhex(a.tag);struct.pack_into('<I',q,64,zlib.crc32(q[:64]));images.append(bytes(q));at+=68+n
        elif tail.startswith(b'K80UI271'):at+=160
        else:at=raw.index(b'\r\n',at)+2
    image=b''.join(images);fixture=normal+packet+image;r=inspect_progress(fixture,a.tag,a.program_tag);assert r['transport_frames_valid'] and r['kernel_known_task_complete266'] and r['synthetic_menu_dispatch_returned273'] and r['serial_roi270']['complete'] and r['wire_nonterminal_frames273']==38 and not r['full_GPU_qualification'];ui=r['synthetic_menu273'];assert ui['compact_loss_observed'] and ui['source_surface_fence_advanced'] and not ui['backend_failure_observed']
    refused=[]
    def reject(label,data):
        try:inspect_progress(data,a.tag,a.program_tag)
        except ValueError:refused.append(label)
        else:raise AssertionError(label)
    reject('oldUI271',raw);reject('repeatedUI273',fixture+packet)
    for label,offset,value,fix in [('boot',8,1,False),('CRC',24,1,False),('schema',284,1,False),('old-long-hold-count',24+25*4,4,True),('snapshot-availability',24+32*4,8,True),('coordinates',24+23*4,1,True)]:
        q=bytearray(packet);q[offset]^=value
        if fix:struct.pack_into('<I',q,280,zlib.crc32(q[:280]))
        reject(label,normal+q+image)
    for n in [1,7,8,24,279,280,287]:assert not inspect_progress(normal+packet[:n],a.tag,a.program_tag)['transport_frames_valid']
    def changed(fields):
        q=bytearray(packet)
        for i,n in fields.items():struct.pack_into('<I',q,24+i*4,n)
        struct.pack_into('<I',q,280,zlib.crc32(q[:280]));return inspect_progress(normal+q+image,a.tag,a.program_tag)
    lost=changed({54:1});assert lost['transport_frames_valid'] and lost['synthetic_menu273']['CF_diagnostic_loss_observed'] and lost['serial_roi270']['complete']
    error=changed({55:1,56:170,57:0xe00002bd});assert error['synthetic_menu273']['backend_failure_observed'] and error['transport_frames_valid']
    stalled=changed({49:259,50:262,51:262,52:262});assert not stalled['synthetic_menu273']['source_surface_fence_advanced'] and not stalled['synthetic_menu273']['backend_failure_observed'];assert not stalled['GPU_desktop_stability_qualified']
    failure=changed({0:7,16:3});assert failure['transport_frames_valid'] and not failure['synthetic_menu_dispatch_returned273'] and failure['serial_roi270']['complete']
    f=a.out/'SYNTHETIC-retagged271-wire-plus-menu273.bin';f.write_bytes(fixture);pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());result=dict(passed=True,fixture=pin(f),parent_actual_wire=pin(a.wire),actual_wire_header=pin(a.source/'ZornUiMenuWire273.h'),decoder=pin(Path(__file__).with_name('inspect_ios26_ui_menu273.py')),source_packet_code=pin(cpp),explicit_synthetic_timing_progress_and_parent_edit_ROI_not_real_menu=True,old_scene_removed_not_reinterpreted=True,refused=refused,partial_prefixes=7,CF_loss_backend_error_and_no_progress_independent=True,stalled_snapshot_not_automatically_hang=True,phone_access=False,hardware_qualified=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS273 source-produced288byte scene/2snapshots,explicit retagged271data,',len(refused),'refusals/7partials;CF loss/error/no progress independent,not menu proof')
if __name__=='__main__':main()
