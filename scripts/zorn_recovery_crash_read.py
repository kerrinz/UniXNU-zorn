"""Single bounded existing-Recovery crash-log read;no reboot,mount or writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from zorn_recovery_identity import PROPERTIES, inspect_recovery
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/k80-persistent-install26'
CURRENT=ROOT/'out/zorn/unattended-active/current.json'
SCOPE='K80-existing-recovery-readonly-crash-capture-v1'
SERIAL='92988a43'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):
    with Path(p).open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def validate(path):
    if path.is_symlink() or not path.resolve().is_relative_to(BASE):raise ValueError('independent local scope required')
    d=load(path)
    for k,v in dict(scope=SCOPE,serial=SERIAL,product='zorn',slot='a',timeout_seconds=120,existing_server_only=True,adb_server_port=5039,device_writes=False,boots=False,retries=0,accepted_recovery='twrp-or-orangefox').items():
        if type(d.get(k)) is not type(v) or d[k]!=v:raise ValueError('exact bounded read scope differs')
    if set(d.get('pins',{}))!={'entry','runner','identity','adb','owner'}:raise ValueError('exact pins required')
    for role,row in d['pins'].items():
        p,a=Path(row['path']),Path(row['archive'])
        if not p.is_absolute() or not a.is_absolute() or p.is_symlink() or a.is_symlink() or not p.is_file() or not a.is_file() or p.stat().st_ino==a.stat().st_ino or sha(p)!=row['sha256'] or sha(a)!=row['sha256']:raise ValueError('changed/shared input:'+role)
    for role,name in [('entry',Path(__file__).name),('runner','run-zorn-debug.py'),('identity','zorn_recovery_identity.py')]:
        if Path(d['pins'][role]['path'])!=Path(__file__).with_name(name):raise ValueError('maintained entry required')
    owner=load(d['pins']['owner']['path'])
    if owner.get('serial')!=SERIAL or owner.get('readonly_existing_crash_capture') is not True:raise ValueError('actual read authority required')
    c=load(CURRENT)
    if any(c.get(k) for k in ['active_run','active_build','runner_session','stop_device_operations']) or c.get('gpu_discovery',{}).get('current_mode')=='unattended-offline-no-phone':raise ValueError('device operation not available')
    return d

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ios26-recovery-crash-read',type=Path,required=True);parser.add_argument('--check',action='store_true');args=parser.parse_args();d=validate(args.ios26_recovery_crash_read)
    if args.check:print(json.dumps(dict(valid=True,device_calls=0)));return
    out=args.ios26_recovery_crash_read.parent/'run';out.mkdir();save(out/'one-shot.claim.json',dict(scope=SCOPE,serial=SERIAL,consumed_before_first_USB=True,reusable=False,admission_sha256=sha(args.ios26_recovery_crash_read)))
    current=load(CURRENT)
    if any(current.get(k) for k in ['active_run','active_build','runner_session','stop_device_operations']):raise RuntimeError('state changed after claim;no USB')
    current['active_run']=str(out);CURRENT.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
    deadline=time.monotonic()+120;commands=[];result=dict(scope=SCOPE,status='started',device_writes=False,boots=False)
    def call(argv,optional=False):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise RuntimeError('bounded read deadline expired')
        cmd=[d['pins']['adb']['path'],'-H','127.0.0.1','-P','5039','-s',SERIAL,*argv];index=len(commands)+1;env=os.environ.copy()
        for key in ['ADB_SERVER_SOCKET','ANDROID_ADB_SERVER_PORT','ANDROID_SERIAL','ADB_TRACE']:env.pop(key,None)
        env.update(ADB_LIBUSB='0',ADB_MDNS_AUTO_CONNECT='0');commands.append(dict(arguments=cmd,optional_existing_file=optional));save(out/f'command-{index:03}.json',commands[-1]);q=subprocess.run(cmd,capture_output=True,env=env,timeout=min(10,remaining));(out/f'command-{index:03}.stdout').write_bytes(q.stdout);(out/f'command-{index:03}.stderr').write_bytes(q.stderr)
        if q.returncode and not optional:raise RuntimeError('identity/read transport failed;no retry')
        return q
    def identity():
        for argv,wanted in [(['get-serialno'],SERIAL),(['shell','getprop','ro.product.device'],'zorn'),(['shell','getprop','ro.boot.slot_suffix'],'_a')]:
            if call(argv).stdout.decode().strip()!=wanted:raise RuntimeError('exact target identity differs')
        return inspect_recovery({key:call(['shell','getprop',key]).stdout.decode().strip() for key in PROPERTIES})
    try:
        result['recovery_before']=identity();inventory=call(['exec-out','ls','-l','/sys/fs/pstore'],optional=True);result['pstore_inventory_exit']=inventory.returncode;captures=[]
        # Fixed literal paths only,no arbitrary device path or host-selected shell.
        for path in ['/sys/fs/pstore/console-ramoops','/sys/fs/pstore/console-ramoops-0','/sys/fs/pstore/dmesg-ramoops-0','/sys/fs/pstore/dmesg-ramoops-1','/sys/fs/pstore/pmsg-ramoops-0','/proc/last_kmsg']:
            q=call(['exec-out','head','-c','1048576',path],optional=True)
            if len(q.stdout)>1048576:raise RuntimeError('bounded capture exceeded')
            captures.append(dict(device_path=path,exit=q.returncode,bytes=len(q.stdout),sha256=hashlib.sha256(q.stdout).hexdigest(),capture_command=len(commands),content_attribution='unknown;not assumed current XNU'))
        result['captures']=captures;result['recovery_after']=identity();result['status']='bounded-existing-crash-paths-captured'
    except BaseException as e:result.update(status='failed-stop-device-operations',error=str(e));raise
    finally:
        result['device_commands']=len(commands);save(out/'result.json',result);current=load(CURRENT)
        if current.get('active_run')==str(out):
            current['active_run']=None
            if result['status'].startswith('failed'):current['stop_device_operations']=True;current['stop_device_reason']=result.get('error')
            CURRENT.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result))
