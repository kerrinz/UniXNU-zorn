#!/usr/bin/env python3
"""Audit acquisition-scoped recurring rollback source,no vote/power model."""
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


def check(original,candidate,i):
    inv=candidate
    assert inv.count(i['rollback_after'])==2
    inv=inv.replace(i['rollback_after'],i['rollback_before'])
    for stem in ['mark','declaration']:
        assert inv.count(i[stem+'_after'])==1;inv=inv.replace(i[stem+'_after'],i[stem+'_before'],1)
    assert inv==original and i['unchanged_STOP_success'] in candidate
    f=tok(body(candidate,'int gen7_hwsched_send_recurring_cmdobj('))
    assert 'boolacquired_here=false;' in f
    assert 'ret=adreno_active_count_get(adreno_dev);if(ret){kfree(cmd);returnret;}active=true;acquired_here=true;' in f
    assert f.count('if(acquired_here){adreno_active_count_put(adreno_dev);active=false;}')==2
    assert 'if(active)adreno_active_count_put(adreno_dev);active=false;returnret;' in f


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    i=json.loads((o/'source-repair-identity.json').read_text());original=Path(i['original']).read_text();candidate=Path(i['candidate']).read_text();check(original,candidate,i);refused=[]
    for name,old,new in [
        ('unacquired-call-falsely-marked','bool acquired_here = false;','bool acquired_here = true;'),
        ('acquisition-mark-before-return-check','\t\t\tactive = true;\n\t\t\tacquired_here = true;','\t\t\tactive = true;'),
        ('preexisting-vote-error-put-restored',i['rollback_after'],i['rollback_before']),
        ('STOP-success-release-wrongly-scoped','\t\tif (active)\n\t\t\tadreno_active_count_put(adreno_dev);','\t\tif (acquired_here)\n\t\t\tadreno_active_count_put(adreno_dev);'),
    ]:
        s=candidate
        if name=='acquisition-mark-before-return-check':
            assert s.count(old)==1;s=s.replace(old,new,1);a=s.index('int gen7_hwsched_send_recurring_cmdobj(');part=s[a:];token='ret = adreno_active_count_get(adreno_dev);';assert token in part;s=s[:a]+part.replace(token,'acquired_here = true;\n\t\t\t'+token,1)
        else:assert s.count(old)==(2 if name=='preexisting-vote-error-put-restored' else 1);s=s.replace(old,new,1)
        (o/(name+'.source')).write_text(s)
        try:check(original,s,i)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('recurring acquisition rollback source mutation accepted: '+name)
    review=o/'source-review';review.mkdir();dst=review/'adreno_gen7_hwsched_hfi.c';shutil.copyfile(i['original'],dst);patch=str((o/'recurring-acquired-here.UNAPPLIED.patch').resolve())
    for args in [['--check',patch],[patch]]:
        r=subprocess.run(['git','apply',*args],cwd=review,capture_output=True,text=True);(o/('review-check.log' if '--check' in args else 'review-apply.log')).write_text(r.stdout+r.stderr);assert r.returncode==0
    assert dst.read_text()==candidate and dst.stat().st_ino!=Path(i['candidate']).stat().st_ino
    (o/'rollback-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,original_review_matches_candidate_and_inverse_exact=True,STOP_success_and_primary_return_unchanged=True,no_activecount_callback_refcount_or_phone_execution=True,no_success_vote_power_or_task_peer=True,no_full_Linux_or_native_target_build=True,no_old_suite_reexecution=True),indent=2)+'\n');print('4 new acquisition-rollback source mutations refused;review/inverse/STOP-success matched,no vote API execution')


if __name__=='__main__':main()
