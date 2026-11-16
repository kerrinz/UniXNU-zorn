#!/usr/bin/env python3
"""Source-only selected kernel time callback semantics;never read a clock or wait."""
from pathlib import Path
import argparse,json,re


def body(s, signature):
    start=s.index('{',s.index(signature));depth=0
    for i in range(start,len(s)):
        depth+=(s[i]=='{')-(s[i]=='}')
        if depth==0:return s[start:i+1]
    raise AssertionError('unclosed pinned function')


def tok(s):
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))


def check(s):
    now=tok(body(s['time'],'int NativeAdrenoKernelTime::now_us('))
    assert 'if(cookie||!value)return1;' in now
    assert 'absolutetime_to_nanoseconds(mach_absolute_time(),&nanoseconds);' in now
    assert '*value=nanoseconds/1000;return0;' in now
    wait=tok(body(s['time'],'int NativeAdrenoKernelTime::wait_us('))
    assert wait=='{if(cookie)return1;IODelay(microseconds);return0;}'
    assert tok(body(s['iolib'],'\nIODelay('))=='{delay_for_interval(microseconds,kMicrosecondScale);}'
    delay=tok(body(s['clock'],'\ndelay_for_interval('))
    assert '_clock_delay_until_deadline(abstime,mach_absolute_time()+abstime);' in delay
    deep=tok(body(s['clock'],'\n_clock_delay_until_deadline_with_leeway('))
    assert 'ml_delay_should_spin(interval)||get_preemption_level()!=0||ml_get_interrupts_enabled()==FALSE' in deep
    assert 'machine_delay_until(interval,deadline);' in deep
    assert 'thread_block(THREAD_CONTINUE_NULL);' in deep


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capsule',type=Path);o=p.parse_args().capsule
    s={k:Path(v).read_text() for k,v in json.loads((o/'audit-inputs.json').read_text()).items()};check(s);refused=[]
    for label,key,before,after in [
        ('wait-falsely-returned-before-delay','time','    IODelay(microseconds);\n    return 0;','    return 0;\n    IODelay(microseconds);'),
        ('sleep-path-falsely-deleted','clock','thread_block(THREAD_CONTINUE_NULL);','/* deleted */'),
        ('time-unit-falsely-nanoseconds','time','*value=nanoseconds/1000;','*value=nanoseconds;'),
    ]:
        assert before in s[key];b=dict(s)
        if label=='sleep-path-falsely-deleted':
            a=b[key].index('\n_clock_delay_until_deadline_with_leeway(');b[key]=b[key][:a]+b[key][a:].replace(before,after,1)
        else:b[key]=b[key].replace(before,after,1)
        (o/(label+'.source')).write_text(b[key])
        try:check(b)
        except (AssertionError,ValueError):refused.append(label)
        else:raise AssertionError('new kernel time source mutation accepted')
    (o/'time-source-audit.json').write_text(json.dumps(dict(new_time_source_mutations_refused=refused,unchanged_native_functions_not_host_or_target_reexecuted=True,no_clock_delay_scheduler_or_hardware_API_executed=True,no_wall_time_bound_or_IOKit_status_inferred=True),indent=2)+'\n');print('3 new selected SDK timing source mutations refused;no clock read/wait/native execution')


if __name__=='__main__':main()
