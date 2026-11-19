#!/usr/bin/env python3
"""One bounded host USB-camera clip for the exact claimed262 boot;no audio/phone IO."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

CAMERA='USB  Camera'
SECONDS=340


def inspect_binding(bundle, claim, run, *, scope, boot_sha, age):
    if (bundle.get('scope')!=scope or bundle.get('serial')!='92988a43' or
            bundle.get('product')!='zorn' or bundle.get('slot')!='a' or
            bundle.get('pins',{}).get('boot',{}).get('sha256')!=boot_sha or
            claim.get('scope')!=scope or claim.get('boot_sha256')!=boot_sha or
            claim.get('status')!='consumed-no-repeat' or claim.get('before_first_USB') is not True or
            run.get('scope')!=scope or run.get('status')!='single-boot-attempt' or
            run.get('boot_attempts')!=1 or not 0<=age<=120):
        raise ValueError('fresh identified262 claimed live boot required for camera')
    return dict(scope=scope,boot_sha256=boot_sha,seconds_since_fastboot_return=age,
                camera=CAMERA,audio=False,seconds=SECONDS,phone_commands=0,
                physical_known_image_proven=False,interpretation_required=True)


def capture_clip(report, out, ffmpeg, run=subprocess.run):
    out=Path(out);out.mkdir(exist_ok=True)
    video=out/'v262-window.mp4';record=out/'v262-window.json'
    if video.exists() or record.exists():
        raise ValueError('single fresh262 camera clip required')
    report=dict(report,started=datetime.now(timezone.utc).isoformat(),
                ffmpeg_path=str(ffmpeg),ffmpeg_sha256=hashlib.sha256(Path(ffmpeg).read_bytes()).hexdigest())
    args=[str(ffmpeg),'-nostdin','-hide_banner','-loglevel','warning','-n',
          '-f','avfoundation','-pixel_format','uyvy422','-framerate','30','-i',CAMERA+':none',
          '-an','-t',str(SECONDS),'-vf','scale=640:-2','-c:v','libx264','-preset','veryfast',
          '-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    report['arguments']=args
    try:
        p=run(args,capture_output=True,text=True,timeout=SECONDS+18)
        report.update(returncode=p.returncode,stderr=p.stderr[-1600:])
    except subprocess.TimeoutExpired:
        report.update(returncode=124,error='358s host capture bound;child terminated by subprocess')
    if video.is_file():
        report.update(video=str(video),bytes=video.stat().st_size,
                      sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    if report.get('returncode')==0 and not report.get('bytes'):
        report.update(returncode=1,error='no video bytes returned')
    record.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    import zorn_ios26_gpu_v262_system_trial as t
    bundle=t.validate(t.TRIAL/'bundle.json')
    # File observation only: no USB lookup,ADB request or boot command here.
    deadline=time.monotonic()+90
    while True:
        try:
            claim=t.load(t.TRIAL/'trial/one-shot.claim.json')
            run=t.load(t.TRIAL/'trial/run.json')
            fastboot=t.TRIAL/'trial/fastboot.txt'
            if fastboot.is_file():
                binding=inspect_binding(bundle,claim,run,scope=t.SCOPE,boot_sha=t.BOOT,
                                        age=time.time()-fastboot.stat().st_mtime)
                state=t.load(t.CURRENT)
                if (state.get('active_run')!=str(t.TRIAL/'trial') or
                        state.get('stop_device_operations') or
                        state['gpu_discovery'].get('current_mode')!='unattended-phone-connected'):
                    raise ValueError('262 camera current mode/run differs')
                break
        except (FileNotFoundError,json.JSONDecodeError):
            pass
        if time.monotonic()>=deadline:
            raise TimeoutError('no fresh262 live boot within90s;camera not opened')
        time.sleep(0.25)
    report=capture_clip(binding,t.TRIAL/'camera',t.SOURCES['camera_binary'].resolve())
    print(json.dumps(report))
    return report['returncode']


if __name__=='__main__':
    raise SystemExit(main())
