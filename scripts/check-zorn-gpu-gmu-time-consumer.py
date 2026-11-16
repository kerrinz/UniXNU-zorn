#!/usr/bin/env python3
"""Audit exact source timing consumers without calling a clock, wait or device."""
from pathlib import Path
import argparse,json,re


def body(s, signature):
    begin=s.index('{',s.index(signature));depth=0
    for i in range(begin,len(s)):
        depth+=(s[i]=='{')-(s[i]=='}')
        if not depth:return s[begin:i+1]
    raise AssertionError('unclosed function')


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


def check(source):
    p=tok(body(source,'static ShengGmuStatus poll('))
    start='if(d->services.now_us(d->services.cookie,&start))returnShengGmuClockError;last=start;'
    clock='if(d->services.now_us(d->services.cookie,&now)||now<last)returnShengGmuClockError;'
    elapsed='if(now-start>=10000)returnShengGmuTimeout;'
    assert start in p and 'for(unsignedi=0;i<budget;++i)' in p
    assert clock in p and elapsed in p
    assert p.index(clock)<p.index(elapsed)<p.index('last=now;++r->poll_reads;')<p.index('check_faults(d,r)')<p.index('core_read(d,reg,observed,r)')
    assert 'if(i+1<budget&&d->services.wait_us(d->services.cookie,100))returnShengGmuClockError;' in p
    assert p.endswith('returnShengGmuTimeout;}')
    for sig,call in [('static int startup_now(','d->services.now_us(d->services.cookie,value)'),('static int startup_wait(','d->services.wait_us(d->services.cookie,us)')]:
        b=tok(body(source,sig));assert 'return'+call+';' in b
        assert b.count('return')==1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    source=Path(json.loads((o/'audit-inputs.json').read_text())['gmu']).read_text();check(source)
    refused=[]
    for name,old,new in [
        ('clock-output-before-return-check','d->services.now_us(d->services.cookie,&now) || now<last','now<last || d->services.now_us(d->services.cookie,&now)'),
        ('backward-time-accepted',' || now<last',''),
        ('extra-last-iteration-wait','i+1<budget && d->services.wait_us','d->services.wait_us'),
        ('forwarded-callback-value-folded','return d->services.now_us(d->services.cookie,value);','return d->services.now_us(d->services.cookie,value)!=0;'),
    ]:
        assert source.count(old)==1
        mutant=source.replace(old,new,1);(o/(name+'.source')).write_text(mutant)
        try:check(mutant)
        except (AssertionError,ValueError):refused.append(name)
        else:raise AssertionError('accepted timing consumer source mutation: '+name)
    (o/'time-consumer-source-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,no_native_callback_clock_wait_or_hardware_execution=True,no_success_clock_provider_peer=True,no_old_startup_or_HFI_suite_reexecution=True),indent=2)+'\n')
    print('4 new timing consumer source mutations refused;source only/no callback or clock peer')


if __name__=='__main__':main()
