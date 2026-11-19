"""Host-only postprocessing for273;no USB,ADB,boot or installation entry."""
import base64,hashlib,json
from pathlib import Path
from inspect_ios26_ui_menu273 import inspect_progress,save_shot273,save_panic
from inspect_ios26_gpu_early252_record import inspect_page

def finish_capture(out,*,tag,program_tag,scope,runner_exit,transport_errors=(),port=None):
    out=Path(out);raw=out/'cdc.raw';data=raw.read_bytes();errors=list(transport_errors)
    verdict=dict(transport_frames_valid=False,frames=[],frame_count=0,full_GPU_qualification=False,known_image_complete=False)
    envelope=False
    try:
        run=json.loads((out/'run.json').read_text())
        verdict.update(inspect_progress(data,tag,program_tag))
        verdict['raw_screenshot_file270']=save_shot273(data,tag,out)
        journal=verdict['journal248'];fragment=base64.b64decode(journal['stderr_base64'],validate=True)
        if hashlib.sha256(fragment).hexdigest()!=journal['sha256']:raise ValueError('journal248 actual saved bytes hash differs')
        p=out/'ordinary273-stderr.bin'
        with p.open('xb') as f:f.write(fragment)
        journal['raw_file']=str(p);verdict['raw_panic_files']=save_panic(data,tag,out)
        record=inspect_page((out/'after-log.bin').read_bytes(),bytes.fromhex(tag),(out/'before-log.bin').read_bytes())
        envelope=bool(record and runner_exit==0 and run.get('scope')==scope and
            run.get('boot_attempts')==1 and run.get('fastboot_returned_success') is True and
            run.get('recovery_identity_after',{}).get('family') in ('TWRP','OrangeFox'))
    except (OSError,ValueError,KeyError) as error:errors.append(str(error))
    verified=bool(verdict['transport_frames_valid'] and envelope and not errors and not verdict.get('terminal236',{}).get('partial_bytes'))
    verdict.update(verified=verified,envelope_valid=envelope,port=port,bytes=len(data),runner_exit=runner_exit,errors=errors,wire_schema='273live-backboardd-menu288-before-after-CPU-snapshots;retained270ROI/268census/266initial-known-task;probe267disabled',full_GPU_qualification=False)
    for key,value in [('early252_with_recovery_observed',verdict.get('early_launch_observed252')),
        ('serial_roi270_with_recovery_observed',verdict.get('serial_roi270',{}).get('complete')),
        ('kernel_readback266_with_recovery_observed',verdict.get('kernel_known_task_complete266')),
        ('synthetic_menu_dispatch_returned273_with_recovery_observed',verdict.get('synthetic_menu_dispatch_returned273'))]:
        verdict[key]=bool(verified and value)
    verdict['ordinary_daemon_exit_required273']=False
    verdict['Liquid_Glass_menu_functionally_qualified']=False
    verdict['GPU_desktop_stability_qualified']=False
    # Serialize BEFORE opening the receipt:bad keys cannot leave another
    # partial JSON file. All separate grades above are explicit string keys.
    text=json.dumps(verdict,indent=2)+'\n'
    with (out/'cdc-capture.json').open('x') as f:f.write(text)
    return verdict
