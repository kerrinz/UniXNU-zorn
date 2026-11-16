#!/usr/bin/env python3
"""Audit private returned replay API values;never execute callbacks or models."""
from pathlib import Path
import argparse,json,re,shutil,subprocess


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


def check(original_c,original_h,candidate_c,candidate_h,i,adreno):
    inverse=candidate_c.replace(i['helper'],'',1)
    for e in reversed(i['c_substitutions']):
        assert inverse.count(e['after'])==1;inverse=inverse.replace(e['after'],e['before'],1)
    assert inverse==original_c
    assert candidate_h.count(i['header_after'])==1 and candidate_h.replace(i['header_after'],i['header_before'],1)==original_h
    c=tok(candidate_c);h=tok(original_h)
    assert 'int(*submit_drawobj)(structadreno_device*adreno_dev,' in h
    assert 'int(*send_recurring_cmdobj)(structadreno_device*adreno_dev,' in tok(adreno)
    assert 'if(error&&!hwsched->replay_first_error_available){hwsched->replay_first_error=error;hwsched->replay_first_error_operation=operation;hwsched->replay_first_error_available=true;}' in c
    assert 'memset(hwsched,0,sizeof(*hwsched));' in c
    assert 'note_replay_failure(hwsched,replay_ret,1);' in c and 'note_replay_failure(hwsched,replay_ret,2);' in c


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    i=json.loads((o/'source-repair-identity.json').read_text());a=Path(i['original_c']).read_text();h=Path(i['original_h']).read_text();c=(o/'candidate/adreno_hwsched.c').read_text();ch=(o/'candidate/adreno_hwsched.h').read_text();adreno=Path(json.loads((o/'audit-inputs.json').read_text())['adreno_header']).read_text();check(a,h,c,ch,i,adreno);refused=[]
    for name,old,new in [
        ('zero-falsely-recorded-as-failure','if (error && !hwsched->replay_first_error_available)','if (!hwsched->replay_first_error_available)'),
        ('first-failure-overwritten','if (error && !hwsched->replay_first_error_available)','if (error)'),
        ('returned-int-folded-to-bool','hwsched->replay_first_error = error;','hwsched->replay_first_error = error != 0;'),
        ('draw-callback-operation-mislabelled','note_replay_failure(hwsched, replay_ret, 1);','note_replay_failure(hwsched, replay_ret, 2);'),
    ]:
        assert c.count(old)==1;s=c.replace(old,new,1);(o/(name+'.source')).write_text(s)
        try:check(a,h,s,ch,i,adreno)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('replay returned-error source mutation accepted: '+name)
    review=o/'source-review';review.mkdir();shutil.copyfile(i['original_c'],review/'adreno_hwsched.c');shutil.copyfile(i['original_h'],review/'adreno_hwsched.h');patch=str((o/'replay-callback-errors.UNAPPLIED.patch').resolve())
    for args in [['--check',patch],[patch]]:
        r=subprocess.run(['git','apply',*args],cwd=review,capture_output=True,text=True);(o/('review-check.log' if '--check' in args else 'review-apply.log')).write_text(r.stdout+r.stderr);assert r.returncode==0
    assert (review/'adreno_hwsched.c').read_text()==c and (review/'adreno_hwsched.h').read_text()==ch
    (o/'replay-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,both_callback_return_declarations_are_actual_C_int=True,both_review_sources_match_candidate_and_inverse_exact=True,no_replay_callback_refcount_provider_or_phone_execution=True,no_success_submission_task_or_address_peer=True,no_full_Linux_or_native_target_build=True,no_old_suite_reexecution=True),indent=2)+'\n');print('4 new replay API-error source mutations refused;typed declarations/review/inverse matched,no callback execution')


if __name__=='__main__':main()
