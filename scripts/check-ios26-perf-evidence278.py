#!/usr/bin/env python3
"""Manual277 decoder/postprocessor regression;retagged275 transport is synthetic."""
import argparse,hashlib,json,struct,tempfile,zlib
from pathlib import Path
from inspect_ios26_ui_menu275 import split_menu
from inspect_ios26_ui_roi270 import split_roi
from inspect_ios26_ui_perf278 import inspect_progress,decode_cost,cost_windows
from zorn_ios26_perf278_capture import finish_capture

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['wire','packet','page','out']:p.add_argument('--'+k,type=Path,required=True)
 for k in ['parent-tag','tag','program-tag']:p.add_argument('--'+k,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);raw=a.wire.read_bytes();stripped,old,_=split_menu(raw,a.parent_tag);assert len(old)==1;normal,_,roi=split_roi(stripped,a.parent_tag);assert roi['complete'];normal=normal.replace(a.parent_tag.encode(),a.tag.encode());at=0;images=[]
 while at<len(raw):
  tail=raw[at:]
  if tail.startswith(b'K80SH270'):
   n=struct.unpack_from('<I',tail,28)[0];q=bytearray(tail[:68+n]);q[8:24]=bytes.fromhex(a.tag);struct.pack_into('<I',q,64,zlib.crc32(q[:64]));images.append(bytes(q));at+=68+n
  elif tail.startswith(b'K80UI275'):at+=416
  else:at=raw.index(b'\r\n',at)+2
 packet=bytearray(a.packet.read_bytes());assert len(packet)==1248 and packet[:8]==b'K80PF278';packet[8:24]=bytes.fromhex(a.tag);struct.pack_into('<I',packet,1240,zlib.crc32(packet[:1240]));packet=bytes(packet);image=b''.join(images);fixture=normal+packet+image;f=a.out/'SYNTHETIC-retagged275-wire-plus-manual278.bin';f.write_bytes(fixture);r=inspect_progress(fixture,a.tag,a.program_tag);assert r['transport_frames_valid'] and r['manual_observation_completed278'] and r['serial_roi270']['complete'] and r['kernel_known_task_complete266'] and r['wire_nonterminal_frames278']==38 and not r['synthetic_input_enabled'] and not r['full_GPU_qualification'];checks=[]
 def rejected(name,data):
  try:inspect_progress(data,a.tag,a.program_tag)
  except ValueError:checks.append(name)
  else:raise AssertionError(name)
 rejected('old synthetic scene',raw);rejected('repeated performance packet',fixture+packet)
 for name,offset,value,fix in [('boot',8,1,False),('CRC',24,1,False),('schema',1244,1,False),('phase',24,3,True),('flags',32,64,True),('count',36,16,True),('interval',40,1,True),('availability',56,8,True),('start time',44,1,True)]:
  q=bytearray(packet);q[offset]^=value
  if fix:struct.pack_into('<I',q,1240,zlib.crc32(q[:1240]))
  rejected(name,normal+q+image)
 for n in [1,7,8,24,1239,1240,1247]:assert not inspect_progress(normal+packet[:n],a.tag,a.program_tag)['transport_frames_valid']
 checks.append('7 partial prefixes refuse complete transport')
 # Actual observer-host packet carries nine structurally valid CPU cost records.
 assert all(s['present_cost'] for s in inspect_progress(fixture,a.tag,a.program_tag)['manual278']['samples'])
 base=[278,2,1000,17,2,10,5,30,10,4,20,3,1,0,0,9]
 assert decode_cost(base)['lease_call_us']==10
 for name,i,value in [('cost schema',0,17),('cost stage',4,0),('cost flags',14,8),('cost counts',1,99),('call exceeds wall',8,31)]:
  q=base.copy();q[i]=value
  try:decode_cost(q)
  except ValueError:checks.append(name+' refused')
  else:raise AssertionError(name)
 def win(a,b):return cost_windows([dict(uptime_ms=1000,present_cost=a),dict(uptime_ms=2000,present_cost=b)])[0]
 aCost=decode_cost(base);bCost=dict(aCost,published_uptime_ms=2000,completed_pixel_copies=3,attempts=4,show_us=30)
 assert win(aCost,bCost)['valid'] and win(aCost,bCost)['completed_copy_rate_per_second']==1
 assert not win(None,bCost)['valid'] and not win(aCost,dict(bCost,faults=1))['valid'] and not win(aCost,dict(bCost,queue_us=0))['valid'] and not win(aCost,aCost)['valid'];checks.append('missing/fault/regression/repeated publication cannot produce performance rate')

 def altered(fields):
  q=bytearray(packet)
  for i,x in fields.items():struct.pack_into('<I',q,24+4*i,x)
  struct.pack_into('<I',q,1240,zlib.crc32(q[:1240]));return normal+q+image
 # Completion of a CPU observer never promises GPU progress or correct input.
 fields={}
 for n in range(9):
  for i in range(16):fields[8+33*n+i]=0
 flat=altered(fields);r=inspect_progress(flat,a.tag,a.program_tag);assert r['manual_observation_completed278'] and not r['physical_FT3683_functionally_qualified'] and not r['full_GPU_qualification'];checks.append('missing/flat snapshots remain observations,not qualification')
 r=inspect_progress(altered({15:1,16:170,17:0xe00002bd}),a.tag,a.program_tag);assert r['manual278']['backend_failure_observed'];checks.append('backend error preserved')
 r=inspect_progress(altered({14:1,20:1}),a.tag,a.program_tag);assert r['manual278']['CF_diagnostic_loss_observed'] and r['manual278']['compact_loss_observed'];checks.append('CF/compact loss preserved')
 scope='HOST-ONLY-perf278'
 def capture(data,code=0,errors=(),change=None):
  with tempfile.TemporaryDirectory() as temp:
   out=Path(temp)
   if data is not None:(out/'cdc.raw').write_bytes(data)
   (out/'before-log.bin').write_bytes(bytes(4096));(out/'after-log.bin').write_bytes(a.page.read_bytes());run=dict(scope=scope,boot_attempts=1,fastboot_returned_success=True,recovery_identity_after=dict(family='TWRP'));run.update(change or {});(out/'run.json').write_text(json.dumps(run));r=finish_capture(out,tag=a.tag,program_tag=a.program_tag,scope=scope,runner_exit=code,transport_errors=errors);assert json.loads((out/'cdc-capture.json').read_text())==r;assert (out/'cdc.raw').exists()==(data is not None);return r
 r=capture(fixture);assert r['verified'] and r['manual_observation_completed278_with_recovery_observed'] and r['serial_roi270_with_recovery_observed'] and not r['full_GPU_qualification'];checks.append('actual postprocessor saves final JSON/image/journal independently of human response')
 for name,kw in [('runner',dict(code=1)),('transport',dict(errors=['fixture'])),('scope',dict(change=dict(scope='foreign'))),('two boots',dict(change=dict(boot_attempts=2))),('no boot',dict(change=dict(fastboot_returned_success=False))),('unknown recovery',dict(change=dict(recovery_identity_after=dict(family='unknown'))))]:
  r=capture(fixture,**kw);assert not r['verified'] and not r['manual_observation_completed278_with_recovery_observed'];checks.append(name+' refuses Recovery-associated grade')
 r=capture(None);assert not r['verified'] and not r['raw_wire_readable'] and r['bytes']==0;checks.append('missing raw explicit failed JSON')
 r=capture(b'');assert not r['verified'] and r['raw_wire_readable'];checks.append('empty raw distinct from missing')
 r=capture(normal+packet[:1247]);assert not r['verified'];checks.append('partial observer packet refuses verified')
 pin=lambda q:dict(path=str(q.resolve()),sha256=hashlib.sha256(q.read_bytes()).hexdigest());(a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,decoder=pin(Path(__file__).with_name('inspect_ios26_ui_perf278.py')),source=pin(Path(__file__).with_name('zorn_ios26_perf278_capture.py')),test_tool=pin(Path(__file__)),fixture=pin(f),packet_from_actual_observer_host_body=pin(a.packet),explicit_synthetic_retagged_parent_transport_and_image=True,phone_access=False,hardware_qualified=False),indent=2)+'\n');print('PASS278 decoder/postprocessor',len(checks),'controls;no UI success from CPU-only observation')
if __name__=='__main__':main()
