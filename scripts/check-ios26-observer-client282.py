#!/usr/bin/env python3
"""Exercise the actual observer: unrelated contention is not lost telemetry.

The legacy source must reproduce the false loss. Relevant contention, capacity
loss and real errors must remain visible. No GPU or phone access occurs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HOST = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <thread>
#include "ZornApplicationObservation26.h"
#include "OBSERVER"
int main(){
 constexpr uintptr_t a=64,b=129,foreign=194;
 appObservationBind(a,10,10);
 assert(appObservationLock());
 appObservationEvent(foreign,2,3,0);
 zorn26_application_prepare_event(foreign,1,0,0);
 zorn26_application_native_return225(foreign,1,3,1,0);
 appObservationUnlock();
 ZornApplicationObservation26 s{};assert(zorn26_application_snapshot(&s));
 if(s.dropped){printf("unrelated_contention_false_loss=%u\n",s.dropped);return 42;}
 assert(appObservationLock());
 appObservationEvent(a,2,3,0);
 zorn26_application_prepare_event(a,1,0,0);
 zorn26_application_native_return225(a,1,3,1,0);
 appObservationUnlock();
 assert(zorn26_application_snapshot(&s) && s.dropped==3);
 appObservationBind(b,10,10); // cannot replace a live observed session
 assert(zorn26_application_snapshot(&s) && s.sessions==1 && s.sessionRejected==1);
 appObservationEvent(a,14,13,0);
 assert(zorn26_application_observes_map222(a));
 zorn26_application_prepare_event(a,2,7,99);
 zorn26_application_prepare_event(a,3,0,12);
 zorn26_application_native_return225(a,123,13,1,0);
 zorn26_application_native_return225(a,123,13,2,9);
 zorn26_application_native_return225(a,123,13,3,9);
 assert(zorn26_application_snapshot(&s) && s.prepareFailed && s.prepareRaw==7 &&
        s.prepareDetail==99 && s.nativeReturn225.runRaw==9 && s.nativeReturn225.externalRaw==9);
 appObservationEvent(a,128,0,0,true);
 assert(appObservationLock());
 appObservationEvent(a,0,13,0);
 zorn26_application_prepare_event(a,1,0,0);
 zorn26_application_native_return225(a,1,3,1,0);
 appObservationUnlock();
 assert(zorn26_application_snapshot(&s) && s.dropped==3 && s.closeReturned);
 appObservationBind(b,10,10);
 // Foreign callbacks run concurrently with real observed callbacks. They must
 // neither take the shared lock nor change its lost-event counter.
 auto noise=[&]{for(unsigned i=0;i<20000;++i){
  appObservationEvent(foreign,2,3,0);
  zorn26_application_prepare_event(foreign,1,0,0);
  zorn26_application_native_return225(foreign,1,3,1,0);
 }};
 std::thread t1(noise),t2(noise);
 for(unsigned i=0;i<20000;++i)appObservationEvent(b,2,13,0);
 t1.join();t2.join();
 assert(zorn26_application_snapshot(&s) && s.dropped==3 && s.sessions==2 && s.calls==20000);
 for(unsigned i=0;i<129;++i)zorn26_application_prepare_event(b,1,0,i);
 assert(zorn26_application_snapshot(&s) && s.prepareEvents==128 && s.dropped==4);
 assert(zorn26_application_stderr_reserve(10,10));
 assert(appObservationLock());
 zorn26_application_stderr_commit(10,"x",1,0);
 appObservationUnlock();
 assert(zorn26_application_snapshot(&s) && s.dropped==5);
 zorn26_application_stderr_commit(10,nullptr,0,14);
 assert(zorn26_application_snapshot(&s) && s.copyErrors==1);
 appObservationEvent(b,128,0,7,true);
 appObservationBind(259,10,10); // a failed close still prevents rebinding
 assert(zorn26_application_snapshot(&s) && s.sessions==2 && s.sessionRejected==2 &&
        s.history[0].closeReturned && !s.history[0].closeRaw && s.history[1].closeRaw==7);
 puts("PASS actual observer: foreign/post-close filtered;real loss/error/rejection retained");
}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--legacy-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sanitizer', default='address,undefined', choices=['address,undefined', 'thread'])
    a = ap.parse_args()
    a.out.mkdir()
    runs = []
    for name, root, expected in [('legacy', a.legacy_root, 42), ('current', a.source_root, 0)]:
        root = root.resolve()
        source = root / 'ZornApplicationObservation26.inc'
        program = a.out / (name + '.cpp')
        program.write_text(HOST.replace('OBSERVER', str(source)))
        binary = a.out / name
        args = ['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                '-g', '-pthread', '-fsanitize=' + a.sanitizer, '-I' + str(root), str(program), '-o', str(binary)]
        build = subprocess.run(args, capture_output=True, timeout=120)
        (a.out / (name + '.build.stderr')).write_bytes(build.stderr)
        assert build.returncode == 0, build.stderr.decode(errors='replace')
        run = subprocess.run([str(binary)], capture_output=True, timeout=60)
        (a.out / (name + '.stdout')).write_bytes(run.stdout)
        (a.out / (name + '.stderr')).write_bytes(run.stderr)
        assert run.returncode == expected, run.stderr.decode(errors='replace')
        if name == 'legacy':
            assert run.stdout == b'unrelated_contention_false_loss=3\n'
        runs.append(dict(name=name, arguments=args, exit=run.returncode,
                         observer=dict(path=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest())))
    (a.out / 'result.json').write_text(json.dumps(dict(passed=True, runs=runs, sanitizer=a.sanitizer,
        actual281_two_drops_cause_proven=False, device_access=False), indent=2) + '\n')
    print('PASS actual legacy false-loss reproduction and corrected observer regression: ' + a.sanitizer)


if __name__ == '__main__':
    main()
