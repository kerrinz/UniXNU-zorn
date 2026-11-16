#!/usr/bin/env python3
"""Check one isolated reference guard;never instantiate or call a task/provider."""
from pathlib import Path
import argparse,json,re,shutil,subprocess


def body(s,t):
    a=s.index('{',s.index(t));d=0
    for i in range(a,len(s)):
        d+=(s[i]=='{')-(s[i]=='}')
        if not d:return s[a:i+1]
    raise AssertionError('unclosed source block')


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


OLD='\tif (hw_hfi->f2h_task)\n\t\tkthread_stop(hw_hfi->f2h_task);'
NEW='\tif (!IS_ERR_OR_NULL(hw_hfi->f2h_task))\n\t\tkthread_stop(hw_hfi->f2h_task);'


def check(original,candidate):
    assert candidate.count(NEW)==1 and candidate.replace(NEW,OLD,1)==original
    init=tok(body(original,'int gen7_hwsched_hfi_init('))
    assert 'hw_hfi->f2h_task=kthread_run(hfi_f2h_main,adreno_dev,"gmu_f2h");' in init
    assert 'if(!IS_ERR(hw_hfi->f2h_task))sched_set_fifo(hw_hfi->f2h_task);' in init
    assert init.endswith('returnPTR_ERR_OR_ZERO(hw_hfi->f2h_task);}')
    remove=tok(body(candidate,'void gen7_hwsched_hfi_remove('))
    assert 'if(!IS_ERR_OR_NULL(hw_hfi->f2h_task))kthread_stop(hw_hfi->f2h_task);' in remove
    assert remove.count('kthread_stop(')==1 and 'f2h_task=' not in remove


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    ident=json.loads((o/'source-repair-identity.json').read_text());original=Path(ident['original']).read_text();candidate=Path(ident['candidate']).read_text();check(original,candidate);refused=[]
    for name,old,new in [
        ('encoded-error-still-stopped',NEW,OLD),
        ('valid-task-stop-deleted','kthread_stop(hw_hfi->f2h_task);','(void)hw_hfi->f2h_task;'),
        ('failure-pointer-silently-cleared','return PTR_ERR_OR_ZERO(hw_hfi->f2h_task);','hw_hfi->f2h_task = NULL;\n\treturn 0;'),
    ]:
        assert candidate.count(old)==1;s=candidate.replace(old,new,1);(o/(name+'.source')).write_text(s)
        try:check(original,s)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('worker guard source mutation accepted: '+name)
    review=o/'source-review';review.mkdir();dst=review/'adreno_gen7_hwsched_hfi.c';shutil.copyfile(ident['original'],dst)
    patch=str((o/'worker-error-pointer.UNAPPLIED.patch').resolve())
    for args in [['--check',patch],[patch]]:
        r=subprocess.run(['git','apply',*args],cwd=review,capture_output=True,text=True)
        (o/('review-check.log' if '--check' in args else 'review-apply.log')).write_text(r.stdout+r.stderr);assert r.returncode==0
    assert dst.read_text()==candidate and dst.stat().st_ino!=Path(ident['candidate']).stat().st_ino
    (o/'worker-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,source_review_check_apply_matches_candidate=True,all_other_source_inverse_byte_identical=True,no_live_application=True,no_native_thread_provider_IRQ_or_phone_execution=True,no_success_task_address_or_allocator_peer=True,no_full_Linux_or_target_ABI_build=True,no_old_suite_reexecution=True),indent=2)+'\n');print('3 new source mutations refused;independent reference review check/apply matched;no task/native execution')


if __name__=='__main__':main()
