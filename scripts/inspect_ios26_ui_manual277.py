"""Decode277 CPU-only timeline. Human/camera observations establish UI behavior."""
import struct,zlib
from inspect_ios26_ui_desktop271 import inspect_progress as previous,save_shot271,save_panic as previous_panic
from inspect_ios26_ui_roi270 import ROI_MAGIC
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT
from inspect_ios26_ui_menu275 import PROGRESS_FIELDS
UI_MAGIC=b'K80MN277'
def split_manual(data,tag):
 if len(data)>WIRE_LIMIT:raise ValueError('manual277 wire bound exceeded')
 boot=bytes.fromhex(tag)
 if len(boot)!=16:raise ValueError('manual277 tag width differs')
 rest=bytearray();rows=[];partial=0;at=0
 while at<len(data):
  tail=data[at:]
  if tail.startswith(UI_MAGIC):
   if len(tail)<672:partial=len(tail);break
   p=tail[:672];crc,schema=struct.unpack_from('<2I',p,664)
   if p[8:24]!=boot or schema!=277 or zlib.crc32(p[:664])!=crc:raise ValueError('manual277 boot/schema/CRC differs')
   v=struct.unpack_from('<160I',p,24);phase,raw,flags,count,interval,start,end=v[:7]
   if phase not in (6,7) or flags&~63 or count>9 or (interval not in (0,10000)) or (phase==6 and (raw or flags not in (61,63) or count!=9 or interval!=10000)):raise ValueError('manual277 observer state differs')
   samples=[]
   for n in range(9):
    q=v[7+17*n:24+17*n]
    if n>=count:
     if any(q):raise ValueError('manual277 unused sample has values')
     continue
    uptime=q[0];s=q[1:]
    if s[0]&~7:raise ValueError('manual277 availability differs')
    for bit,a,b in [(1,1,6),(2,6,12),(4,12,16)]:
     if not s[0]&bit and any(s[a:b]):raise ValueError('manual277 absent CPU source has values')
    if uptime<start or (n and uptime<samples[-1]['uptime_ms']):raise ValueError('manual277 sample time reversed')
    samples.append(dict(uptime_ms=uptime,**dict(zip(PROGRESS_FIELDS,s))))
   if samples and (end<samples[-1]['uptime_ms'] or start!=samples[0]['uptime_ms']):raise ValueError('manual277 endpoint time differs')
   rows.append(dict(phase=phase,thread_raw=raw,flags=flags,count=count,interval_ms=interval,start_uptime_ms=start,end_uptime_ms=end,samples=samples,observation_completed=phase==6,synthetic_contacts=0,physical_touch_delivery_proven=False,backend_failure_observed=any(s['available']&2 and s['backend_sequence'] for s in samples),CF_diagnostic_loss_observed=any(s['available']&2 and s['CF_dropped'] for s in samples),compact_loss_observed=any(s['available']&4 and s['compact_dropped'] for s in samples)))
   if len(rows)>1:raise ValueError('manual277 repeated observer packet')
   at+=672;continue
  if UI_MAGIC.startswith(tail):partial=len(tail);break
  if tail.startswith(b'K80UI'):raise ValueError('manual277 received synthetic scene schema')
  if tail.startswith(ROI_MAGIC):
   if len(tail)<68:rest.extend(tail);break
   n=struct.unpack_from('<I',tail,28)[0]
   if not 0<n<=3004:raise ValueError('manual277 ROI bound differs')
   if len(tail)<68+n:rest.extend(tail);break
   rest.extend(tail[:68+n]);at+=68+n;continue
  if tail.startswith(MAGIC):rest.extend(tail);break
  end=data.find(b'\r\n',at)
  if end<0:rest.extend(tail);break
  rest.extend(data[at:end+2]);at=end+2
 return bytes(rest),rows,partial
def inspect_progress(data,tag,program_tag):
 rest,rows,partial=split_manual(data,tag);r=previous(rest,tag,program_tag);total=r['wire_nonterminal_frames271']+len(rows)
 if total>38:raise ValueError('manual277 frame budget exceeded')
 if partial:r['transport_frames_valid']=False
 r.update(manual277=rows[0] if rows else None,manual_observation_completed277=bool(rows and rows[0]['observation_completed']),partial_manual_packet277=partial,wire_nonterminal_frames277=total,synthetic_input_enabled=False,ordinary_probe267_selected=False,Liquid_Glass_menu_functionally_qualified=False,Settings_navigation_functionally_qualified=False,physical_FT3683_functionally_qualified=False,GPU_desktop_stability_qualified=False,full_GPU_qualification=False)
 r['client_census268']['scope']='Actual live backboardd clients;manual observation does not require daemon exit.'
 return r
def save_shot277(data,tag,out):
 rest,_,_=split_manual(data,tag);return save_shot271(rest,tag,out)
def save_panic(data,tag,out):
 rest,_,_=split_manual(data,tag);return previous_panic(rest,tag,out)
