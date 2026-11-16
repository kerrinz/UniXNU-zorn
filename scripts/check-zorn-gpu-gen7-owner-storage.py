#!/usr/bin/env python3
"""Audit exact owner-bound callback storage,no allocator/buffer/task doubles."""
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


def check(original,header,candidate,ch,i):
    inv=candidate
    for before,after in [(i['recurring_before'],i['recurring_after']),(i['publish_before'],i['publish_after']),(i['local_before'],i['local_after'])]:
        assert inv.count(after)==1;inv=inv.replace(after,before,1)
    assert inv==original
    assert ch.count(i['header_after'])==1 and ch.replace(i['header_after'],i['header_before'],1)==header
    submit=tok(body(candidate,'int gen7_hwsched_submit_drawobj('))
    assert 'void*cmdbuf=adreno_dev->hwsched.submit_cmdbuf;' in submit and 'staticvoid*cmdbuf' not in submit
    assert 'cmdbuf=devm_kzalloc(&device->pdev->dev,HFI_MAX_MSG_SIZE,GFP_KERNEL);' in submit
    assert submit.index('if(!cmdbuf)return-ENOMEM;')<submit.index('adreno_dev->hwsched.submit_cmdbuf=cmdbuf;')<submit.index('hfi_context_register(')
    recurring=tok(body(candidate,'int gen7_hwsched_send_recurring_cmdobj('))
    assert 'staticboolactive' not in recurring and 'if(!hwsched->recurring_active)' in recurring
    assert 'hwsched->recurring_active=true;' in recurring and 'hwsched->recurring_active=false;' in recurring


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    i=json.loads((o/'source-repair-identity.json').read_text());a=Path(i['original_c']).read_text();h=Path(i['original_h']).read_text();c=(o/'candidate/adreno_gen7_hwsched_hfi.c').read_text();ch=(o/'candidate/adreno_hwsched.h').read_text();check(a,h,c,ch,i);refused=[]
    for name,old,new in [
        ('scratch-pointer-global-static-again',i['local_after'],i['local_before']),
        ('owner-publication-before-failure-check',i['publish_after'],'\t\tadreno_dev->hwsched.submit_cmdbuf = cmdbuf;\n'+i['publish_before']),
        ('recurring-state-global-static-again',i['recurring_after'],i['recurring_before']),
        ('scratch-allocation-size-changed','cmdbuf = devm_kzalloc(&device->pdev->dev, HFI_MAX_MSG_SIZE,','cmdbuf = devm_kzalloc(&device->pdev->dev, sizeof(void *),'),
    ]:
        assert c.count(old)==1;s=c.replace(old,new,1);(o/(name+'.source')).write_text(s)
        try:check(a,h,s,ch,i)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('owner callback storage source mutation accepted: '+name)
    review=o/'source-review';review.mkdir();shutil.copyfile(i['original_c'],review/'adreno_gen7_hwsched_hfi.c');shutil.copyfile(i['original_h'],review/'adreno_hwsched.h');patch=str((o/'owner-callback-storage.UNAPPLIED.patch').resolve())
    for args in [['--check',patch],[patch]]:
        r=subprocess.run(['git','apply',*args],cwd=review,capture_output=True,text=True);(o/('review-check.log' if '--check' in args else 'review-apply.log')).write_text(r.stdout+r.stderr);assert r.returncode==0
    assert (review/'adreno_gen7_hwsched_hfi.c').read_text()==c and (review/'adreno_hwsched.h').read_text()==ch
    (o/'owner-storage-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,both_review_sources_match_candidate_and_inverse_exact=True,no_allocator_buffer_refcount_or_phone_execution=True,no_success_owner_buffer_address_or_task_peer=True,no_full_Linux_or_native_target_build=True,no_old_suite_reexecution=True),indent=2)+'\n');print('4 new owner-storage source mutations refused;twofile review/inverse matched,no allocator/native execution')


if __name__=='__main__':main()
