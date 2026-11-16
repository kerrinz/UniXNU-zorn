#!/usr/bin/env python3
"""Audit a narrow exact-source diagnostic reference repair,no context/ref model."""
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


def check(original,candidate,identity,header):
    g=tok(body(header,'static inline int _kgsl_context_get('))
    assert 'kref_get_unless_zero(&context->refcount)' in g
    p=tok(body(header,'kgsl_context_put(struct kgsl_context *context)'))
    assert 'kref_put(&context->refcount,kgsl_context_destroy);' in p
    inv=candidate
    for e in reversed(identity['owner_release_substitutions']):
        assert inv.count(e['after'])==1;inv=inv.replace(e['after'],e['before'],1)
    for stem in ['timeout_get','timeout_put']:
        assert inv.count(identity[stem+'_after'])==1;inv=inv.replace(identity[stem+'_after'],identity[stem+'_before'],1)
    assert inv==original
    for sig in ['static void gen7_defer_hw_fence_work(','int gen7_hwsched_disable_hw_fence_throttle(']:
        b=tok(body(candidate,sig))
        assert b.index('hfi->hw_fence.defer_drawctxt=NULL;')<b.index('kgsl_context_put(&drawctxt->base);')
    b=tok(body(candidate,'static void gen7_hwsched_hw_fence_timeout('))
    get='if(fault&&drawctxt&&!_kgsl_context_get(&drawctxt->base))drawctxt=NULL;'
    assert get in b and b.index(get)<b.index('spin_unlock(&hfi->hw_fence.lock);')
    assert b.index('if(!fault)return;')<b.index('structkgsl_process_private*proc_priv=drawctxt->base.proc_priv;')<b.index('kgsl_context_put(&drawctxt->base);')<b.index('gen7_hwsched_fault(adreno_dev,ADRENO_GMU_FAULT);')
    assert b.count('_kgsl_context_get(')==b.count('kgsl_context_put(')==1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    i=json.loads((o/'source-repair-identity.json').read_text());original=Path(i['original']).read_text();candidate=Path(i['candidate']).read_text();header=Path(json.loads((o/'audit-inputs.json').read_text())['context_header']).read_text();check(original,candidate,i,header);refused=[]
    for name,old,new in [
        ('first-owner-drops-before-withdrawal',i['owner_release_substitutions'][0]['after'],i['owner_release_substitutions'][0]['before']),
        ('diagnostic-get-removed','if (fault && drawctxt && !_kgsl_context_get(&drawctxt->base))','if (fault && drawctxt)'),
        ('diagnostic-temporary-ref-leaked',i['timeout_put_after'],i['timeout_put_before']),
        ('nonfault-path-grabs-ref-without-put','if (fault && drawctxt && !_kgsl_context_get(&drawctxt->base))','if (drawctxt && !_kgsl_context_get(&drawctxt->base))'),
    ]:
        assert candidate.count(old)==1;s=candidate.replace(old,new,1);(o/(name+'.source')).write_text(s)
        try:check(original,s,i,header)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('deferred context mutation accepted: '+name)
    review=o/'source-review';review.mkdir();dst=review/'adreno_gen7_hwsched_hfi.c';shutil.copyfile(i['original'],dst);patch=str((o/'deferred-diagnostic-reference.UNAPPLIED.patch').resolve())
    for args in [['--check',patch],[patch]]:
        r=subprocess.run(['git','apply',*args],cwd=review,capture_output=True,text=True);(o/('review-check.log' if '--check' in args else 'review-apply.log')).write_text(r.stdout+r.stderr);assert r.returncode==0
    assert dst.read_text()==candidate and dst.stat().st_ino!=Path(i['candidate']).stat().st_ino
    (o/'context-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,source_review_check_apply_matches_candidate=True,all_other_source_inverse_byte_identical=True,no_context_refcount_callback_or_phone_execution=True,no_success_context_task_or_address_peer=True,no_full_Linux_or_native_target_build=True,no_old_suite_reexecution=True),indent=2)+'\n');print('4 new context source mutations refused;independent reference review matched,no refcount/API execution')


if __name__=='__main__':main()
