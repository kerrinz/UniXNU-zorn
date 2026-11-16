#!/usr/bin/env python3
"""Offline tests of the actual bounded journal, syscall adapter and CDC decoder."""
import argparse, base64, hashlib, json, re, subprocess, sys, zlib
from pathlib import Path
from inspect_ios26_gpu_journal248 import inspect_progress, inspect_journal, decode_journal, KEYS
from inspect_ios26_gpu_known247 import inspect_progress as inspect247


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--build',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir();repo=Path(__file__).resolve().parents[1];native=repo/'native/ios26-journal248'
    checks=[];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    def run(name,args):
        p=subprocess.run(args,capture_output=True,timeout=120);(a.out/(name+'.stdout')).write_bytes(p.stdout);(a.out/(name+'.stderr')).write_bytes(p.stderr);(a.out/(name+'.command.json')).write_text(json.dumps(dict(arguments=args,exit=p.returncode),indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace')[-3000:];return p.stdout
    for f in native.glob('*'):
        if f.suffix in ('.h','.inc'):assert f.read_bytes()==(a.source_root/f.name).read_bytes()
    run('store-build',['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-g','-pthread',str(native/'hostcheck.cpp'),'-o',str(a.out/'store')]);run('store',[str(a.out/'store')]);checks.append('actual resident store/capture ASan UBSan including concurrent publication')
    # Reuse the existing producer base64 implementation byte-for-byte.
    ufs=(a.source_root/'ZornUfsOwner26.cpp').read_text();start=ufs.index('static void zorn26_base64_encode(');end=ufs.index('\n#include "ZornJournalWire248.h"',start);encode=ufs[start:end]
    wire='''#include <cassert>
#include <cstdio>
#include <cstring>
#include "ZornJournalWire248.h"
'''+encode+'''
int main(){
 char line[3072];uint32_t cursor=0;
 auto sample=[](uint32_t at,void *out,uint32_t cap,ZornJournalSnapshot248 *s){
  uint32_t n=2000-at;if(n>cap)n=cap;
  for(uint32_t i=0;i<n;++i)static_cast<unsigned char *>(out)[i]=static_cast<unsigned char>((at+i)%251);
  *s={42,2000,7,2000,2000,1,0,0,1,0,0,at,n};return 1;
 };
 while(cursor<2000){strcpy(line,"frame\\r\\n");auto n=zorn_journal_append248(line,sizeof(line),7,cursor,sample,zorn26_base64_encode);
  assert(n && n<sizeof(line) && n==strlen(line));fwrite(line,1,n,stdout);}
 assert(cursor==2000);
 char small[512];strcpy(small,"frame\\r\\n");uint32_t zero=0;
 assert(!zorn_journal_append248(small,64,7,zero,sample,zorn26_base64_encode));assert(!zero);
 auto busy=[](uint32_t,void *,uint32_t,ZornJournalSnapshot248 *){return 0;};
 strcpy(small,"frame\\r\\n");assert(zorn_journal_append248(small,sizeof(small),7,zero,busy,zorn26_base64_encode));assert(!zero);
 for(unsigned cap=160;cap<=512;++cap){strcpy(small,"frame\\r\\n");zero=0;auto n=zorn_journal_append248(small,cap,7,zero,sample,zorn26_base64_encode);if(n){assert(n<cap && n==strlen(small) && zero>0 && zero<=768);}}
}
'''
    (a.out/'wire.cpp').write_text(wire);run('wire-build',['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(native),str(a.out/'wire.cpp'),'-o',str(a.out/'wire')]);wiredata=run('wire',[str(a.out/'wire')]);joined=bytearray()
    for line in wiredata.splitlines():
        _,_,rest=line.partition(b',jl=');raw,_,blob=rest.partition(b',jb=');r,data=decode_journal(raw,blob);assert r['offset']==len(joined);joined.extend(data)
    assert joined==bytes(i%251 for i in range(2000));checks.append('actual producer encoder/header, dynamic bounded capacity, all fragment byte ranges')
    c=json.loads((a.build/'candidate.json').read_text());parent=Path(c['parent']);pc=json.loads((parent/'candidate.json').read_text());ps=Path(pc['source'])
    # Real source hook location, original exit byte proof and native call preservation.
    exitmeta=json.loads((a.build/'exit-source.json').read_text());original=Path(exitmeta['original']).read_text();current=(a.source_root/'kern_exit.c').read_text()
    hook='''#if defined(ARM64_BOARD_CONFIG_ZORN)
    /* Task detached after file/AIO cleanup;no resource ownership changed. */
    zorn26_journal_exit248(proc_uniqueid(p),(uint32_t)proc_getpid(p),(uint32_t)p->p_xstat);
#endif
'''
    assert current.replace('#include "ZornApplicationJournal248.h"\n','',1).replace(hook,'',1)==original
    at=current.index('zorn26_journal_exit248(');assert current.rfind('clear_thread_ro_proc(get_machthread(uth));',0,at)>current.index('proc_exit(proc_t p)')
    assert (a.source_root/'ZornApplicationStderr26.inc').read_text()==(ps/'ZornApplicationStderr26.inc').read_text()+'\n#include "ZornJournalCapture248.inc"\n'
    checks.append('actual task-detached exit hook, unchanged original legacy observer and exit body')
    # Actual247 capture is retained as a legacy regression. Appended journal is
    # SYNTHETIC fixture data, not reconstructed missing hardware diagnostics.
    rawpath=parent.parent/('k80-gpu-v247-metal-trial-'+pc['tag'])/'root-trial/trial/cdc.raw';raw=rawpath.read_bytes();legacy=inspect247(raw,pc['tag'],c['program_tag']);assert legacy['last_application']['raw_stderr_dropped']==36 and not legacy['last_application']['complete']
    lines=raw.replace(pc['tag'].encode(),c['tag'].encode()).split(b'\r\n')[:-1];app=legacy['last_application'];report=app['report'];identity=app['program_identity']
    message=('ZORN193MTL run='+c['program_tag']+' phase={phase} flags={flags:x} status={status} code={code} service={service:x} device={device:x} crc={crc:08x} bad={first_bad:08x} ticks={ticks}\n').format(**report).encode()
    data=b'SYNTHETIC journal regression fixture\n'+message
    r=dict(zip(KEYS,[identity['unique'],len(data),identity['pid'],len(data),len(data),1,0,0,1,0,zlib.crc32(data),0,len(data)]),available=1)
    def wire_record(r,data):return b',jl='+str(r['available']).encode()+b'/'+b'/'.join(f'{r[k]:0{16 if i<2 else 8}x}'.encode() for i,k in enumerate(KEYS))+b',jb='+base64.b64encode(data)
    zero=dict.fromkeys(KEYS,0)|dict(available=0)
    def compose(r,data):return b'\r\n'.join(line+wire_record(zero,b'') if i<len(lines)-1 else line+wire_record(r,data) for i,line in enumerate(lines))+b'\r\n'
    good=compose(r,data);result=inspect_progress(good,c['tag'],c['program_tag']);assert result['lossless_application_complete248'] and not result['last_application']['complete'] and result['last_application']['raw_stderr_dropped']==36
    (a.out/'synthetic-positive.raw').write_bytes(good);checks.append('actual247 legacy regression; synthetic lossless journal does not erase legacy loss36')
    cases={
      'busy':(r|dict(gaps=1),data),'copy-fault':(r|dict(gaps=8),data),
      'pending':(r|dict(pending=1),data),'not-exited':(r|dict(exited=0),data),
      'failed-exit':(r|dict(exit_status=256),data),
      'crc':(r|dict(crc32=r['crc32']^1),data),'offset':(r|dict(offset=1),data),
      'foreign-pid':(r|dict(pid=r['pid']+1),data),
      'missing-report':(r|dict(crc32=zlib.crc32(b'x'*len(data))),b'x'*len(data)),
      'unseen-tail':(r|dict(seen_bytes=len(data)+1),data),
      'reserved-tail':(r|dict(seen_bytes=len(data)+1,reserved=len(data)+1),data),
      'missing-publication':(zero,b''),
    }
    for name,(rec,blob) in cases.items():
        try:bad=inspect_progress(compose(rec,blob),c['tag'],c['program_tag'])
        except ValueError:pass
        else:assert not bad['lossless_application_complete248'],name
        checks.append(name+' rejects or remains incomplete')
    for count in range(1,8):
        try:p=inspect_progress(good+b'K80PAN26'[:count],c['tag'],c['program_tag'])
        except ValueError:pass
        else:assert not p['lossless_application_complete248']
    checks.append('partial panic prefixes never qualify lossless application')
    # Sequential fragments with growing CRC coverage and unchanged terminal
    # totals may be assembled; gaps, duplicate offsets, monotonic regressions fail.
    one=r|dict(bytes=3);two=r|dict(offset=3,bytes=len(data)-3)
    summary,got=inspect_journal([(one,data[:3]),(two,data[3:])]);assert summary['complete'] and got==data
    for bad in [two|dict(offset=4),two|dict(gaps=128),two|dict(unique=two['unique']+1),two|dict(seen_bytes=two['seen_bytes']-1),two|dict(exit_status=256)]:
        try:summary,_=inspect_journal([(one,data[:3]),(bad,data[3:])])
        except ValueError:pass
        else:assert not summary['complete']
    checks.append('sequential assembly, CRC prefixes, identity and exit monotonicity')
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,legacy_capture_sha256=sha(rawpath),native_sources={f.name:sha(f) for f in native.glob('*') if f.is_file()},source_root=str(a.source_root),hardware_qualification=False,phone_access=False),indent=2)+'\n');print('PASS journal248 offline store/capture/wire/strict decoder controls')

if __name__=='__main__':main()
