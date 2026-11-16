#!/usr/bin/env python3
"""Capture one authorized USB-camera frame bound to an actual slotA trial.

Host camera only: no audio,no phone command,no alternate-camera fallback.
A frame is evidence to inspect,never automatic desktop/GPU qualification.
"""
import argparse
from datetime import datetime,timezone
import hashlib,json,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90'
CAMERA='USB  Camera'
def capture(trial,label):
    trial=Path(trial).resolve()
    if not trial.is_relative_to(STAGE.resolve()) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',label):raise ValueError('exact local trial and bounded label required')
    bundle_path=trial/'bundle.json'
    if not bundle_path.is_file() and trial.name=='trial-review':
        bundle_path=trial/'reviewed-inputs.json'
    raw_bundle=bundle_path.read_bytes()
    bundle=json.loads(raw_bundle);run=json.loads((trial/'trial/run.json').read_text());claim=json.loads((trial/'trial/one-shot.claim.json').read_text())
    if bundle_path.name=='reviewed-inputs.json' and (
        claim.get('nonce')!=bundle.get('record_id') or
        claim.get('bundle_sha256')!=hashlib.sha256(raw_bundle).hexdigest()):
        raise ValueError('exact FT3683 review and claim required')
    if (bundle.get('serial')!='92988a43' or bundle.get('product')!='zorn' or bundle.get('slot')!='a' or
        claim.get('status')!='consumed-no-repeat' or claim.get('scope')!=bundle.get('scope') or
        claim.get('boot_sha256')!=bundle['pins']['boot']['sha256'] or run.get('scope')!=bundle.get('scope') or run.get('boot_attempts')!=1):raise ValueError('actual identified consumed slotA boot trial required')
    if not (run.get('status')=='single-boot-attempt' or str(run.get('status','')).startswith('recovered-')):raise ValueError('trial not an actual live/recovered boot')
    fastboot=trial/'trial/fastboot.txt';age=time.time()-fastboot.stat().st_mtime
    if not 0<=age<=720:raise ValueError('trial camera attribution expired')
    out=trial/'camera';out.mkdir(exist_ok=True);frame=out/(label+'.jpg');report_path=out/(label+'.json')
    if frame.exists() or report_path.exists():raise ValueError('fresh camera capture label required')
    report=dict(trial=str(trial),scope=bundle['scope'],boot_sha256=bundle['pins']['boot']['sha256'],run_status=run['status'],camera=CAMERA,audio=False,seconds_since_fastboot_return=age,started=datetime.now(timezone.utc).isoformat(),phone_commands=0,desktop_or_GPU_qualified=False)
    args=['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','warning','-f','avfoundation','-pixel_format','uyvy422','-framerate','30','-i',CAMERA+':none','-an','-ss','2','-frames:v','1','-update','1',str(frame)]
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=18);report.update(returncode=p.returncode,stderr=p.stderr[-1600:])
    except subprocess.TimeoutExpired:report.update(returncode=124,error='18s host capture limit')
    if frame.is_file():report.update(image=str(frame),bytes=frame.stat().st_size,sha256=hashlib.sha256(frame.read_bytes()).hexdigest())
    elif report.get('returncode')==0:report.update(returncode=1,error='no actual frame returned')
    report_path.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trial',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args();print(json.dumps(capture(a.trial,a.label)))
