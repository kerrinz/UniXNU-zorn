"""Bounded existing-error-reason wording classes;no raw reason/PC/register output."""
import re,json,hashlib
from pathlib import Path
from inspect_ios26_gpu_progress233 import inspect_progress as inspect_previous,FORMATS
CLASS_PATH=Path(__file__).parent/'data'/'k80-reason-classes235-78ed67e0c4b04a169dd54d04972aa671.json'
CLASS_SHA='71ff334ff0be75dc40cd598502ba9cf82da8e5629643b4235a1322cc6d1bdb8d'
raw=CLASS_PATH.read_bytes()
if hashlib.sha256(raw).hexdigest()!=CLASS_SHA:raise ValueError('reason class table differs')
CLASSES={int(k):v for k,v in json.loads(raw)['classes'].items()}

def inspect_progress(data,run_id,probe_run_id):
    if len(data)>119808:raise ValueError('CDC total exceeds source budget')
    normalized=data;event=None
    for m in re.finditer(rb'(?m)^K80 TERM ([0-9a-f]{32}) r([123]) f=([0-9a-f]{4}) p[0-7]{3} v=[0-9a-f]{2}\r\n',data):
        wire=int(m[3],16)
        if 0x9000<=wire<0x9100:
            if event is not None or wire-0x9000 not in CLASSES or m[2]!=b'2':raise ValueError('reason class enum differs')
            event=wire;normalized=data[:m.start(3)]+b'fffe'+data[m.end(3):]
    result=inspect_previous(normalized,run_id,probe_run_id)
    terminal=result.pop('terminal233');terminal['wire_identifier']=event if event is not None else terminal['format_id'];terminal['first_reason_class']=None
    if event is not None:
        if not terminal['packet_complete'] or terminal['reason']!=2:raise ValueError('reason class has no complete terminal')
        terminal['format_id']=None
        terminal['first_reason_class']=dict(source_class=event-0x9000,label=CLASSES[event-0x9000],scope='Fixed wording in the first published Hjt26Reason only. No raw message/numeric value/PC/register/backtrace exported. BRK numeric positions skipped;source filename/line syntax used only for assertion wording. This is error-text classification,not exact faulting PC/callsite or proof of a PAC rootcause.')
        terminal['format_capture_state']='unmatched-template-with-existing-first-reason-class'
    terminal['cause_known']=False;result['terminal235']=terminal;return result
