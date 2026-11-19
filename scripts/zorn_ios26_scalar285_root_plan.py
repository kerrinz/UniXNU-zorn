"""Pure source template for the fixed285 policy delta; no device execution.

Preparation copies this into the independent reviewed archive and binds its
actual input-manifest hash. Importing this unprepared template must fail.
The existing reviewed transport owns every live read/write and timeout.
"""
from pathlib import Path
import hashlib,json,plistlib,re,sys,types

HERE=Path(__file__).resolve().parent
INPUTS_SHA='PREPARE_INPUTS_SHA'
PAGE=4096;FIRST=6291712;BLOCKS=8388608;BYTES=BLOCKS*PAGE;PAGES=7454;GROUPS=130
RETAINED_PAGES=0
BASE_SHA='d9856b4342a307d915f43d8cd7d9540b8a2d3933f07dfd46750cfe5a32c0c622'
RESULT_SHA='03bb39293ecfcd7b89bde24c61edff430a891ea77e3024e37ef9c244c7f80a92'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def require(v,m):
    if not v:raise ValueError(m)

def bound():
    p=HERE/'plan-inputs.json';require(sha(p)==INPUTS_SHA,'285 plan manifest differs');rows=json.loads(p.read_text())
    for role,row in rows.items():
        f=Path(row['path']);require(not f.is_symlink() and f.is_file() and sha(f)==row['sha256'],'285 plan source differs:'+role)
    return {k:Path(v['path']) for k,v in rows.items()}

paths=bound();R=next(p for p in HERE.parents if (p/'UniXNU-zorn/scripts').is_dir());sys.path.insert(0,str(R/'UniXNU-zorn/scripts'))
from zorn_ios26_root_delta import groups
m=types.ModuleType('retained_apply_delta285');m.__file__=str(paths['apply_delta_reference']);exec(compile(paths['apply_delta_reference'].read_bytes(),m.__file__,'exec'),m.__dict__);apply_delta=m.apply_delta

def load_plan():
    paths=bound();load=lambda k:json.loads(paths[k].read_text());root=load('composed_root');base=load('offline_composition_parent');delta=load('delta');boot=load('boot_manifest');layout=load('layout');bundle=load('plugin_result')
    require(root['passed'] and root['sha256']==delta['sha256']==boot['root']['sha256']==layout['candidate_image']['sha256']==layout['replay_image']['sha256']==RESULT_SHA,'285 target root lineage differs')
    require(base['passed'] and base['sha256']==load('install_base')['sha256']==delta['source_sha256']==layout['source_image']['sha256']==BASE_SHA,'285 actual installed base differs')
    require(root['bytes']==base['bytes']==delta['bytes']==boot['root']['bytes']==BYTES and not boot['root_installed'] and boot['root_installation_required'] and not boot['device_ready'],'285 offline root state differs')
    for key in ['signature_verified','filesystem_verified','CPU_rendering_and_input_files_unchanged','monitored_attributes_preserved','source_image_hash_and_metadata_preserved','rc_unchanged']:
        require(root[key] and base[key],'285 root validation differs:'+key)
    before,after=base['monitored_after_sha256'],root['monitored_after_sha256']
    allowed={'System/Library/Extensions/NativeAdrenoMetal.bundle/NativeAdrenoMetal','System/Library/LaunchDaemons/com.apple.backboardd.plist'}
    require(set(before)==set(after) and {n for n in before if before[n]!=after[n]}==allowed,'285 unrelated root file differs')
    require(bundle['passed'] and bundle['ABI']==1 and bundle['all_OS_targets']=='arm64e iOS26','285 actual plugin ABI/OS differs')
    prefix='System/Library/Extensions/NativeAdrenoMetal.bundle/'
    for name,digest in bundle['files'].items():
        require(after[prefix+name]==digest and sha(Path(bundle['bundle'])/name)==digest and (name=='NativeAdrenoMetal' or before[prefix+name]==digest),'285 actual signed bundle differs:'+name)
    require(paths['policy_clients'].read_text()=='backboardd\n' and sha(paths['policy_clients'])==after['System/Library/Extensions/NativeAdrenoMetal.clients'] and root['client_policy']==boot['ordinary_client']=='backboardd' and root['probe_job_disabled'] and boot['probe_job_disabled'],'285 ordinary-client policy differs')
    job=plistlib.loads(paths['policy_job'].read_bytes())
    require(job['ProgramArguments']==['/redwood/sbin/zorn-metal-probe193'] and job['Disabled'] and not job['RunAtLoad'] and not job['KeepAlive'] and sha(paths['policy_job'])==after['System/Library/LaunchDaemons/org.unixnu.zorn.metal-probe193.plist'],'285 probe-disable policy differs')
    env=plistlib.loads(paths['backboardd_policy'].read_bytes())['EnvironmentVariables']
    require(env['NATIVE_METAL_TIMING']=='1' and env['NATIVE_METAL_BOOT_SESSION']==boot['run_id'] and sha(paths['backboardd_policy'])==after['System/Library/LaunchDaemons/com.apple.backboardd.plist'],'285 scalar timing environment differs')
    require(load('frontend_closure')['passed'] and load('scalar_host')['passed'] and load('scalar_tsan')['passed'] and load('scalar_decoder')['passed'],'285 scalar source controls failed')
    require(bundle['native_PAC_archive_unchanged'] and not bundle['postlink_instruction_rewrite'] and sha(bundle['retained_Rust_archive']['path'])==bundle['retained_Rust_archive']['sha256'],'285 retained native Rust differs')
    require(boot['version']==285 and not boot['human_input_required'] and not boot['synthetic_input_enabled'] and boot['watchdog_seconds']==300 and boot['recovery_timeout_seconds']==600 and boot['retries']==0 and boot['runtime_roots_read_only'] and not boot['storage_layout_changed'],'285 bounded boot configuration differs')
    closure=load('operation_closure')
    require(closure['passed'] and closure['kernel_sha256']==boot['link']['sha256'] and closure['root_sha256']==RESULT_SHA and closure['boot_tag']==boot['run_id'] and not closure['new_root_installed'] and not closure['synthetic_input'],'285 native closure differs')
    for row in closure['checks']:require(sha(row['path'])==row['sha256'],'285 current check changed')
    for key in ['wire_retire_host','ABI_dependencies','native_identity','firmware_closure','presenter_host','presenter_tsan','observer_host','observer_tsan']:
        require(load(key)['passed'],'285 required control failed:'+key)
    require(load('native_identity')['expected_boot_tag']==boot['run_id'] and load('ABI_dependencies')['ABI']==1,'285 current native identity/ABI differs')
    values={k:int(v) for k,v in re.findall(r'static constexpr uint64_t (\w+)=(\d+)ULL;',paths['root_window_header'].read_text())}
    storage=load('source_storage_descriptor');start=((storage['Data']['relative_first_lba']+storage['Data']['window_blocks'])*PAGE+1048575)&~1048575
    require(values['RelativeByteStart']==FIRST*PAGE==start and values['Bytes']==BYTES and values['PartitionBytes']==storage['partition']['bytes'] and values['AbsoluteByteStart']==storage['partition']['first_lba']*PAGE+start,'285 exact storage placement differs')
    require(values['DataStart']==storage['Data']['relative_first_lba']*PAGE and values['DataEnd']==(storage['Data']['relative_first_lba']+storage['Data']['window_blocks'])*PAGE and values['DataEnd']<=start and values['LogStart']+PAGE<=start and start+BYTES<=values['PartitionBytes'],'285 root overlaps protections')
    require(layout['placement_recomputed_from_Data_end'] and layout['placement_alignment']==1048576 and not layout['layout_change'] and layout['proposed_relative_first_lba']==FIRST and layout['proposed_blocks']==BLOCKS and layout['reserve_after_root_bytes']>=4*1024**3 and layout['source_metadata_preserved'],'285 layout/replay differs')
    require(','.join(hex(x) for x in bytes.fromhex(RESULT_SHA)) in paths['root_window_header'].read_text(),'285 native header digest differs')
    rows=delta['pages'];patch=paths['patch'].read_bytes();require(len(rows)==PAGES and len(patch)==PAGES*PAGE*2 and [r['image_block'] for r in rows]==sorted({r['image_block'] for r in rows}),'285 delta coverage differs')
    for i,row in enumerate(rows):
        a,z=patch[i*8192:i*8192+4096],patch[i*8192+4096:(i+1)*8192]
        require(type(row['image_block']) is int and 0<=row['image_block']<BLOCKS and hashlib.sha256(a).hexdigest()==row['old_sha256'] and hashlib.sha256(z).hexdigest()==row['new_sha256'] and a!=z,'285 page bounds/hash differs')
    parts=groups(rows,patch);require(len(parts)==GROUPS and all(1<=len(z)//PAGE<=65 for _,_,z in parts),'285 write groups differ')
    require(load('local_replay')['replay']['changed_page_readback_sha256']==layout['local_readback_sha256'],'285 local replay readback differs')
    previous,claim,admission=load('previous_result'),load('previous_claim'),load('previous_admission')
    require(previous['scope']=='K80-persistent-iOS26-desktop283-45267e58' and previous['installed'] and previous['expected_image_sha256']==BASE_SHA and previous['pages_written']==22 and previous['protected_metadata_and_fences_unchanged'] and claim['consumed_before_first_USB'] and not claim['reusable'],'285 actual parent install differs')
    require(claim['admission_sha256']==sha(paths['previous_admission']) and admission['review_sha256']==sha(paths['previous_review']) and admission['runner_sha256']==sha(paths['previous_installer_runner']) and admission['entry_sha256']==sha(paths['previous_installer_entry']),'285 previous install source/claim binding differs')
    actual,capture=load('latest_actual_boot'),load('latest_actual_capture')
    require(actual['boot_attempts']==1 and actual['recovery_identity_after']['family'] in ['TWRP','OrangeFox'] and capture['verified'] and capture['manual_observation_completed278_with_recovery_observed'],'285 latest actual284 readback cohort incomplete')
    index=load('prior_readback_layout');raw=paths['prior_readback'].read_bytes()
    require(hashlib.sha256(raw).hexdigest()==index['sha256'] and index['previous_install_receipt']['sha256']==sha(paths['previous_result']) and index['latest_readback_sha256']==previous['readback']['sha256'] and index['merged_previous_retained_and_all_actual283_written_pages'],'285 merged prior readback lineage differs')
    retained=[];at=0;last=-1
    for row in index['groups']:
        n=row['block'];count=row['pages'];z=raw[at:at+count*PAGE];at+=len(z)
        require(type(n) is int and last<n and 0<=n<BLOCKS and 1<=count<=65 and n+count<=BLOCKS and len(z)==count*PAGE and hashlib.sha256(z).hexdigest()==row['sha256'],'285 prior readback group differs');last=n+count-1;retained.append((n,z))
    require(at==len(raw) and sum(len(z)//PAGE for _,z in retained)==index['pages']==RETAINED_PAGES,'285 retained coverage differs')
    source=Path(delta['source']);require(source.is_file() and not source.is_symlink() and source.stat().st_size==BYTES and not source.stat().st_mode&0o222,'285 immutable local base differs')
    with source.open('rb') as f:
        for n,z in retained:f.seek(n*PAGE);require(f.read(len(z))==z,'285 recorded current pages disagree with local source')
    return source,parts,retained
