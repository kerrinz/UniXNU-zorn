"""Decode exact per-client CPU diagnostic tokens;never claim a GPU/exit oracle."""
import re
from inspect_ios26_gpu_early252 import inspect_progress as inspect_previous
from inspect_ios26_gpu_progress236 import MAGIC,WIRE_LIMIT

STAGES={10,11,12,13,14,15,16,40,41,42,43,44,45,80,81,100,101,102,103,104,105,106,107,108,109,120,121,122,160,161}
EVENT=('sequence','stage','reason','raw','method','detail0','detail1')

def decode_failure(raw):
 fields=raw.split(b'/')
 if len(fields)!=25 or fields[0] not in (b'0',b'1'):
  raise ValueError('failure261 envelope differs')
 for text,width in zip(fields[1:],(16,16)+(8,)*22):
  if not re.fullmatch(rb'[0-9a-f]{%d}'%width,text):raise ValueError('failure261 syntax differs')
 v=[int(x,16) for x in fields[1:]]
 r=dict(available=int(fields[0]),id=v[0],unique=v[1],pid=v[2],flags=v[3],calls=v[4],records=v[5],recycled=v[6],dropped=v[7],reject=dict(zip(EVENT,v[8:15])),failure=dict(zip(EVENT,v[15:22])),close_stage=v[22],close_raw=v[23])
 if not r['available']:
  if any(v):raise ValueError('failure261 unavailable contains state')
  return r
 if r['records']>64 or r['flags']&~31:raise ValueError('failure261 bounds differ')
 if not r['id']:
  if any(v[:5]+v[8:]) or r['records'] or r['recycled']:raise ValueError('failure261 empty identity differs')
  return r
 if r['id']<64 or not r['unique'] or not r['pid'] or not r['records'] or not r['flags']&1:
  raise ValueError('failure261 missing actual client identity')
 if (r['flags']&16 and not r['flags']&8) or (r['flags']&8 and r['flags']&2) or (r['flags']&8 and bool(r['close_raw'])!=bool(r['flags']&16)):
  raise ValueError('failure261 close flags differ')
 for event in (r['reject'],r['failure']):
  if not event['sequence']:
   if any(event.values()):raise ValueError('failure261 empty event contains state')
  elif not event['raw'] or event['stage'] not in STAGES or event['reason']>23 or event['method']>18:
   raise ValueError('failure261 event bounds differ')
 if r['close_stage'] and r['close_stage'] not in STAGES:raise ValueError('failure261 close stage differs')
 return r

def inspect_progress(data,tag,program_tag):
 if len(data)>WIRE_LIMIT:raise ValueError('failure261 wire budget exceeded')
 at=data.find(MAGIC);normal,terminal=(data,b'') if at<0 else (data[:at],data[at:]);output=[];records=[];clients={}
 for line in normal.splitlines(keepends=True):
  if not line.endswith(b'\r\n'):output.append(line);continue
  if len(line)>3072 or line.count(b',cf=')!=1:raise ValueError('failure261 frame envelope differs')
  head,_,rest=line.partition(b',cf=');raw,sep,tail=rest.partition(b',jl=')
  if not sep:raise ValueError('failure261 journal separator missing')
  r=decode_failure(raw);records.append(r)
  if r['id']:
   key=r['id'];old=clients.get(key)
   if old:
    if (r['unique'],r['pid'])!=(old['unique'],old['pid']) or r['calls']<old['calls']:
     raise ValueError('failure261 client identity/calls regressed')
    for channel in ['reject','failure']:
     if old[channel]['sequence'] and r[channel]!=old[channel]:raise ValueError('failure261 first event changed')
    if old['flags']&8 and (not r['flags']&8 or (r['close_raw'],r['close_stage'])!=(old['close_raw'],old['close_stage'])):raise ValueError('failure261 completed row regressed')
   clients[key]=r
  output.append(head+b',jl='+tail)
 result=inspect_previous(b''.join(output)+terminal,tag,program_tag)
 if len(records)!=result['frame_count']:raise ValueError('failure261 frame count differs')
 for row in records:
  for channel in ['reject','failure']:
   event=row[channel];event['raw_kind']=('ZornSmmuSparse4KStatus' if event['stage']==160 else 'IOReturn') if event['sequence'] else None
   event['physical_owner_cleanup']=event['method']==18 # Internal diagnostic tag;external ABI remains1..17
 result['client_failure261']=records;result['clients261']=list(clients.values())
 result['source_reject_observed261']=any(r['reject']['sequence'] for r in clients.values())
 result['source_backend_error_observed261']=any(r['failure']['sequence'] for r in clients.values())
 result['client_diagnostic_loss261']=any(r['dropped'] or r['recycled'] or not r['available'] for r in records)
 result['all_clients_observed261']=False # bounded sampled rows do not prove exhaustive coverage
 result['full_GPU_qualification']=False
 result['scope261']='Source-defined per-client CPU first reject/backend error and close metadata;diagnostic tokens are not addresses,authority,fences or hardware completion'
 return result
