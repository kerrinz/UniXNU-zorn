"""Host-only storage migration through the fixed device build entry.

The new policy retains the old native source/recipe pins and separately records
the reviewed device-source delta. It never edits an old qualification receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--unixnu64-native-build', action='store_true', required=True)
    parser.add_argument('--os', choices=('17',), required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--policy-sha256', required=True)
    args = parser.parse_args()
    if sha(args.policy) != args.policy_sha256:
        raise RuntimeError('storage migration policy changed')
    policy = json.loads(args.policy.read_text())
    root = Path(policy['root'])
    out = root/'out/zorn/dual-system-reinstall-20261101/native-build'
    if args.policy.resolve() != out/'policy.json':
        raise RuntimeError('wrong storage migration policy context')
    if policy['storage_profile'] != 'unixnu64' or policy['allow_boot'] is not False:
        raise RuntimeError('offline unixnu64 policy required')
    current_path = root/'out/zorn/unattended-active/current.json'
    current = json.loads(current_path.read_text())
    if current.get('active_run') or current.get('active_build') or current.get('runner_session'):
        raise RuntimeError('another build/run is active')
    for name, expected in policy['inputs'].items():
        if sha(name) != expected:
            raise RuntimeError('native migration input changed: '+name)
    if (out/'result.json').exists():
        raise RuntimeError('native result exists; inspect it before any retry')
    tree = Path(policy['tree']); device = Path(policy['device'])
    env = dict(os.environ, **policy['environment'])
    sys.path.insert(0,str(Path(policy['core'])/'scripts'))
    from unixnu.kernel import toolchain_path
    env['PATH'] = toolchain_path(env.get('PATH'))
    if (env['UNIXNU_ZORN_STORAGE_PROFILE'] != 'unixnu64' or
        env['UNIXNU_ZORN_DATA_PROFILE'] != '8g' or env['UNIXNU_ZORN_SMP'] != '8' or
        env['UNIXNU_ZORN_GPU_MEMORY'] != '0' or env['UNIXNU_IOS_VERSION'] != '17.0'):
        raise RuntimeError('storage/CPU/OS selection differs')
    # Preserve mutable archives, link outputs and records before compiler/Make.
    saved = {}
    for base in (tree/'build/zorn-ufs', tree/'build/zorn-storage',
                 tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837',
                 tree.parent/'kernel'):
        for src in base.rglob('*'):
            if not src.is_file() or src.is_symlink(): continue
            dest = out/'preimages'/src.relative_to(tree.parent)
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['cp','-c',str(src),str(dest)],check=True)
            if src.stat().st_ino == dest.stat().st_ino or sha(src) != sha(dest):
                raise RuntimeError('mutable preimage is not independent')
            saved[str(src)] = dict(path=str(dest), sha256=sha(dest))
    (out/'mutable-preimages.json').write_text(json.dumps(saved,indent=2)+'\n')
    current['active_build'] = str(out); current['active_phase'] = 'unixnu64-native-build'
    current_path.write_text(json.dumps(current,indent=2,ensure_ascii=False)+'\n')
    result = dict(status='running', phone_operations=False, allow_boot=False,
                  GPU_executed=False, policy_sha256=args.policy_sha256)
    try:
        if policy.get('reuse_ufs'):
            for name, expected in policy['reuse_ufs'].items():
                if sha(name) != expected: raise RuntimeError('completed UFS result changed')
            steps = []
        else:
            steps = [('ufs', [sys.executable,str(device/'scripts/build-zorn-ufs.py')])]
        for name, command in steps:
            with (out/(name+'.log')).open('w') as log:
                subprocess.run(command,cwd=tree,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        # Force a genuine relink: Make does not track external archive contents
        # in XNU_EXTRA_LD_ARCHIVES on every supported XNU revision.
        linked = tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/mach.development.bcm2837.unstripped'
        for target in (linked, linked.with_name(linked.name+'.noctf')):
            if target.exists():
                before = out/'preimages/link-targets'/target.name
                before.parent.mkdir(parents=True,exist_ok=True)
                target.rename(before)
        with (out/'native-link.log').open('w') as log:
            subprocess.run(['bash',str(tree/'scripts/build-xnu-4k-baseline.sh')],
                cwd=tree,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        native = linked.with_name(linked.name+'.noctf')
        unresolved = subprocess.check_output(['xcrun','nm','-u',str(native)],text=True)
        if unresolved.strip(): raise RuntimeError('new native kernel has undefined imports')
        shutil.copy2(native,out/'kernel.native.macho')
        result['native_sha256'] = sha(native)
        if result['native_sha256'] == policy['old_native_sha256']:
            raise RuntimeError('storage migration did not change the actual native kernel')
        sys.path.insert(0,str(Path(policy['core'])/'scripts'))
        from unixnu.cli import parser as core_parser
        from unixnu.config import Context
        from unixnu import kernel
        ctx = Context(core_parser().parse_args(['status','--os','17','-D',policy['legacy'],
            '--out',str(Path(policy['core'])/'out'),'--kernelcache',policy['original_kernelcache']]))
        if str(ctx.tree) != str(tree): raise RuntimeError('prelink tree differs')
        ctx.logs.mkdir(parents=True,exist_ok=True)
        candidate = kernel.prelink(ctx)
        shutil.copy2(candidate,out/'kernel.prelinked.macho')
        shutil.copy2(candidate.with_suffix('.json'),out/'kernel.postlink-plan.json')
        result.update(status='completed',candidate=str(candidate),candidate_sha256=sha(candidate),
            ufs_archive_sha256=sha(tree/'build/zorn-ufs/libZornUfs.a'))
    except Exception as error:
        result.update(status='failed',error=str(error)); raise
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        current = json.loads(current_path.read_text()); current['active_build'] = None
        current['active_phase'] = 'unixnu64-native-'+result['status']
        current_path.write_text(json.dumps(current,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(result,indent=2))
