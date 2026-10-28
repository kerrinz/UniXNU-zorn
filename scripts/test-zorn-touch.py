#!/usr/bin/env python3
"""Run the pinned K80 touch candidate and zip this exact round's returned log.

No flashing, Android boot, slot change or alternate serial is supported.
Use --check-only for a completely offline image/archive check.
"""
import argparse,hashlib,json,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def digest(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    candidate=json.loads((ROOT/'out/zorn/touch/next-test.json').read_text())
    sha=candidate['boot_sha256'];archive=ROOT/'out/zorn/builds'/sha[:8]
    image=archive/'boot.img';manifest=json.loads((archive/'inputs.json').read_text())
    if not (candidate['serial']=='92988a43' and candidate['product']=='zorn' and candidate['slot']=='b' and
            candidate['timeout_seconds']==360 and manifest['status']=='ready' and manifest['sha256']==sha and
            digest(image)==sha and digest(archive/'kernel.macho')==candidate['kernel_sha256'] and
            manifest.get('touch_identify') and manifest.get('touch_handoff') and manifest.get('touch_probe') and
            manifest['early_watchdog_mode']==1 and manifest['checkpoint_override']=='TOUCHRO'):
        raise RuntimeError('touch candidate identity/profile differs; no USB action attempted')
    print('Verified K80 FT3683 identity probe '+sha,flush=True)
    if args.check_only:
        print('Offline check passed; no device access.');return
    debug=ROOT/'out/zorn/debug';before=set(debug.glob('*'))
    result=subprocess.run([sys.executable,str(Path(__file__).with_name('run-zorn-debug.py')),
                           '--image',str(image),'--timeout','360'],cwd=ROOT)
    after=[d for d in debug.glob('*') if d not in before and d.name.endswith('-'+sha[:8])]
    if len(after)!=1:raise RuntimeError('cannot uniquely bind the returned run; inspect out/zorn/debug')
    run=after[0];state=json.loads((run/'run.json').read_text())
    if state.get('sha256')!=sha:raise RuntimeError('run image identity differs')
    dest=ROOT/'out/zorn/touch-return';dest.mkdir(parents=True,exist_ok=True)
    bundle=dest/(run.name+'.zip')
    with zipfile.ZipFile(bundle,'x',zipfile.ZIP_DEFLATED) as z:
        for name in ('run.json','build-inputs.json','checkpoints.bin','checkpoints.txt','preboot-checkpoints.bin','fastboot.txt','bootstrap-fastboot.txt','bcb.json'):
            file=run/name
            if file.is_file():z.write(file,run.name+'/'+name)
        z.write(ROOT/'out/zorn/touch/next-test.json',run.name+'/candidate.json')
    print('\nReturn this log bundle: '+str(bundle),flush=True)
    if result.returncode or state.get('status')!='recovered' or state.get('kernel_log_changed') is not True:
        print('This round is incomplete or has no fresh kernel log; do not retry repeatedly. Return the bundle as-is.',file=sys.stderr)
        raise SystemExit(1)
    print('K80 returned to recovery with a fresh log. This probe does not boot the GUI or provide touch input.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,RuntimeError) as error:sys.exit(str(error))
