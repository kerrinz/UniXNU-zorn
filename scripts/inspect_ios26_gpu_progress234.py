"""Source-event enums in the existing bounded terminal wire;no machine-state analysis."""
import re,json,hashlib
from pathlib import Path
from inspect_ios26_gpu_progress233 import inspect_progress as inspect_previous,FORMATS
CLASS_PATH=Path(__file__).parent/'data'/'k80-source-fault234-0008a13dd390479ebdb62c1d1b943531.json'
CLASS_SHA='6991a02621fd3d92de36d1d66accb3298e8ac393570200d4f14e1900a1f87bf2'
raw=CLASS_PATH.read_bytes()
if hashlib.sha256(raw).hexdigest()!=CLASS_SHA:raise ValueError('source fault class table differs')
manifest=json.loads(raw)
CLASSES={int(k):v for k,v in manifest['classes'].items() if int(k) in manifest['compiled_classes']}

def inspect_progress(data,run_id,probe_run_id):
    if len(data)>119808:raise ValueError('CDC total exceeds source budget')
    normalized=data;event=None
    # Translate only this newly introduced enum range for the old syntax parser.
    # Byte length,identity,ordering,onepacket and totalbudget checks stay intact.
    for m in re.finditer(rb'(?m)^K80 TERM ([0-9a-f]{32}) r([123]) f=([0-9a-f]{4}) p[0-7]{3} v=[0-9a-f]{2}\r\n',data):
        wire=int(m[3],16)
        if 0x8000<=wire<0x8100:
            if event is not None or wire-0x8000 not in CLASSES or m[2]!=b'2':raise ValueError('source fault enum differs')
            event=wire
            normalized=data[:m.start(3)]+b'fffe'+data[m.end(3):]
    result=inspect_previous(normalized,run_id,probe_run_id)
    terminal=result.pop('terminal233');terminal['wire_identifier']=event if event is not None else terminal['format_id']
    terminal['first_source_fault_event']=None
    if event is not None:
        if not terminal['packet_complete'] or terminal['reason']!=2:raise ValueError('source event has no complete terminal')
        terminal['format_id']=None
        terminal['first_source_fault_event']=dict(source_class=event-0x8000,label=CLASSES[event-0x8000],scope='First successful global source logger event. Existing source branches choose the class;no exception parameter,PC,address,register or stack data read. Under concurrent faults it need not belong to the terminal formatter winner. Not a rootcause or exact callsite claim.')
        terminal['format_capture_state']='unmatched-template-with-first-source-fault-event'
    terminal['cause_known']=False
    result['terminal234']=terminal
    return result
