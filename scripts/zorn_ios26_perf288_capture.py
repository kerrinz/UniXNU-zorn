"""Host-only postprocessing for288;no USB,ADB,boot or installation entry."""
import base64,hashlib,json
from pathlib import Path
from inspect_ios26_ui_perf278 import inspect_progress,save_shot278,save_panic
from inspect_ios26_gpu_early252_record import inspect_page
from inspect_ios26_scalar_timing287 import inspect as inspect_scalar_timing

def finish_capture(out,*,tag,program_tag,scope,runner_exit,transport_errors=(),port=None):
    out=Path(out);raw=out/'cdc.raw';errors=list(transport_errors);data=b'';raw_readable=False
    try:data=raw.read_bytes();raw_readable=True
    except OSError as error:errors.append('CDC raw unavailable: '+str(error))
    verdict=dict(transport_frames_valid=False,frames=[],frame_count=0,full_GPU_qualification=False,known_image_complete=False)
    envelope=False
    try:
        verdict.update(inspect_progress(data,tag,program_tag))
        verdict['raw_screenshot_file270']=save_shot278(data,tag,out)
        journal=verdict['journal248'];fragment=base64.b64decode(journal['stderr_base64'],validate=True)
        if hashlib.sha256(fragment).hexdigest()!=journal['sha256']:raise ValueError('journal248 actual saved bytes hash differs')
        p=out/'ordinary288-stderr.bin'
        with p.open('xb') as f:f.write(fragment)
        journal['raw_file']=str(p);verdict['scalar_timing287']=inspect_scalar_timing(fragment,tag);verdict['raw_panic_files']=save_panic(data,tag,out)
        record=inspect_page((out/'after-log.bin').read_bytes(),bytes.fromhex(tag),(out/'before-log.bin').read_bytes())
        run=json.loads((out/'run.json').read_text())
        envelope=bool(record and runner_exit==0 and run.get('scope')==scope and
            type(run.get('boot_attempts')) is int and run['boot_attempts']==1 and run.get('fastboot_returned_success') is True and
            run.get('recovery_identity_after',{}).get('family') in ('TWRP','OrangeFox'))
    except (OSError,ValueError,KeyError) as error:errors.append(str(error))
    verified=bool(verdict['transport_frames_valid'] and envelope and not errors and not verdict.get('terminal236',{}).get('partial_bytes'))
    verdict.update(verified=verified,envelope_valid=envelope,port=port,bytes=len(data),raw_wire_readable=raw_readable,runner_exit=runner_exit,errors=errors,wire_schema='288boot;278CPU-present-cost1248-nine-snapshots-no-synthetic-input;retained270ROI/268census/266initial-known-task;probe267disabled',full_GPU_qualification=False)
    for key,value in [('early252_with_recovery_observed',verdict.get('early_launch_observed252')),('serial_roi270_with_recovery_observed',verdict.get('serial_roi270',{}).get('complete')),('kernel_readback266_with_recovery_observed',verdict.get('kernel_known_task_complete266')),('manual_observation_completed278_with_recovery_observed',verdict.get('manual_observation_completed278'))]:
        verdict[key]=bool(verified and value)
    verdict['scalar_timing287_with_recovery_observed']=bool(verified and verdict.get('scalar_timing287',{}).get('complete'))
    verdict['native_RPC287_with_recovery_observed']=bool(verified and verdict.get('scalar_timing287',{}).get('native_RPC_complete'))
    verdict['ordinary_daemon_exit_required278']=False
    verdict['Liquid_Glass_menu_functionally_qualified']=False
    verdict['GPU_desktop_stability_qualified']=False
    verdict['menu_dismissal_functionally_qualified']=False
    verdict['Settings_navigation_functionally_qualified']=False
    # Serialize BEFORE opening the receipt:bad keys cannot leave another
    # partial JSON file. All separate grades above are explicit string keys.
    text=json.dumps(verdict,indent=2)+'\n'
    with (out/'cdc-capture.json').open('x') as f:f.write(text)
    return verdict
