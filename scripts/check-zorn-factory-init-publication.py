#!/usr/bin/env python3
"""Audit two factory initialization publications;no allocation/backoff concurrency model."""
from pathlib import Path
import argparse,json,re,struct,subprocess,shutil


def mask(s):return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',lambda m:' '*len(m.group(0)),s,flags=re.S)

def body(s,sig):
 m=mask(s);a=m.index('{',m.index(sig));d=0
 for j in range(a,len(s)):
  d+=(m[j]=='{')-(m[j]=='}')
  if not d:return s[a:j+1]
 raise AssertionError('unclosed')

def tok(s):return re.sub(r'\s+','',mask(s))


def sourcecheck(original,candidate,i):
 inv=candidate
 for a,b in reversed(i['changes']):assert inv.count(b)==1;inv=inv.replace(b,a,1)
 assert inv==original
 f=tok(body(candidate,'static IOBufferMemoryDescriptor *systemDescriptor('))
 assert f.count('__atomic_load_n(&contigKiB,__ATOMIC_ACQUIRE)')==2 and f.count('__atomic_load_n(&backoff,__ATOMIC_ACQUIRE)')==2
 assert 'uint32_tparsed=0;PE_parse_boot_argn(' in f and '&parsed,sizeofparsed);' in f
 assert '__atomic_compare_exchange_n(&contigKiB,&expected,parsed,false,__ATOMIC_RELEASE,__ATOMIC_RELAXED);' in f
 assert 'uint64_tconverted=0;nanoseconds_to_absolutetime(UINT64_C(5000000000),&converted);' in f
 assert '__atomic_compare_exchange_n(&backoff,&expected,converted,false,__ATOMIC_RELEASE,__ATOMIC_RELAXED);' in f
 assert 'if(failedBytes&&now-failedAt>=backoffTicks)failedBytes=0;' in f
 assert 'if(!failedBytes||bytes<failedBytes)failedBytes=bytes;failedAt=now;' in f


def factory_asm(obj):
 r=subprocess.run(['xcrun','llvm-objdump','--macho','--disassemble','--symbolize-operands',str(obj)],capture_output=True,text=True);assert r.returncode==0
 text=r.stdout;sig='__ZL16systemDescriptormbPyS_:';start=text.index(sig);rest=text[start+len(sig):];end=re.search(r'\n__Z[^\s:]+:\n',rest);return rest[:end.start()] if end else rest


def objectcheck(obj):
 s=factory_asm(obj)
 assert len(re.findall(r'\bldar\s+w\d+',s))==2
 assert len(re.findall(r'\bldar\s+x\d+',s))==2
 assert re.search(r'\bstlxr\s+w\d+,\s*w\d+',s)
 assert re.search(r'\bstlxr\s+w\d+,\s*x\d+',s)
 assert '_PE_parse_boot_argn' in s and '_nanoseconds_to_absolutetime' in s
 return s


def textsection(data):
 assert struct.unpack_from('<I',data)[0]==0xfeedfacf
 off=32
 for _ in range(struct.unpack_from('<I',data,16)[0]):
  cmd,size=struct.unpack_from('<II',data,off)
  if cmd==0x19:
   for j in range(struct.unpack_from('<I',data,off+64)[0]):
    p=off+72+80*j
    if data[p:p+16].split(b'\0')[0]==b'__text':return struct.unpack_from('<Q',data,p+32)[0],struct.unpack_from('<I',data,p+48)[0]
  off+=size
 raise AssertionError('text section absent')


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capsule',type=Path);o=ap.parse_args().capsule;i=json.loads((o/'source-repair-identity.json').read_text());original=Path(i['original']).read_text();candidate=Path(i['candidate']).read_text();sourcecheck(original,candidate,i);refused=[]
 for name,a,b in [
  ('boot-parse-writes-static','&parsed,sizeof parsed','&contigKiB,sizeof contigKiB'),
  ('conversion-writes-static','UINT64_C(5000000000),&converted','UINT64_C(5000000000),&backoff'),
  ('plain-hint-load-restored','uint32_t contigHint=__atomic_load_n(&contigKiB,__ATOMIC_ACQUIRE);','uint32_t contigHint=contigKiB;'),
  ('unpublished-loser-ticks-used','backoffTicks=__atomic_load_n(&backoff,__ATOMIC_ACQUIRE);\n    }','backoffTicks=converted;\n    }'),
 ]:
  assert candidate.count(a)==1;s=candidate.replace(a,b,1);(o/(name+'.source')).write_text(s)
  try:sourcecheck(original,s,i)
  except (AssertionError,ValueError):refused.append(name)
  else:raise AssertionError('initialization source mutation accepted:'+name)
 review=o/'source-review';review.mkdir();shutil.copyfile(i['original'],review/'NativeAdrenoMemory.cpp');patch=str((o/'factory-hint-initialization.UNAPPLIED.patch').resolve())
 for args in [['--check',patch],[patch]]:
  r=subprocess.run(['git','apply',*args],cwd=review,capture_output=True,text=True);(o/('review-check.log' if '--check' in args else 'review-apply.log')).write_text(r.stdout+r.stderr);assert r.returncode==0
 assert (review/'NativeAdrenoMemory.cpp').read_text()==candidate
 obj=o/'NativeMemory.o';asm=objectcheck(obj);raw=obj.read_bytes();addr,offset=textsection(raw);object_refused=[]
 for width in ['w','x']:
  m=re.search(r'^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2}\s+){3}[0-9a-f]{2})\s+ldar\s+'+width+r'\d+',asm,re.M);assert m,width
  pos=offset+int(m.group(1),16)-addr;ins=bytes.fromhex(m.group(2));assert raw[pos:pos+4]==ins;changed=bytearray(raw);changed[pos:pos+4]=bytes.fromhex('1f2003d5');p=o/('missing-'+width+'-acquire.o');p.write_bytes(changed)
  try:objectcheck(p)
  except (AssertionError,ValueError):object_refused.append(width+' acquire removed')
  else:raise AssertionError('actual object acquire mutation accepted')
 sections=(o/'sections.log').read_text();imports=(o/'imports.log').read_text();assert '__mod_init_func' not in sections and '__cxa_guard' not in imports and '__atomic_' not in imports
 (o/'init-publication-audit.json').write_text(json.dumps(dict(new_source_mutations_refused=refused,new_actual_object_mutations_refused=object_refused,independent_original_review_inverse_equal=True,actual32_and64_acquire_release_CAS_emitted=True,no_initializer_or_new_atomic_runtime_import=True,failedBytes_failedAt_pair_unchanged_and_not_concurrency_qualified=True,no_factory_allocator_refcount_API_or_success_model_execution=True,no_old_suite_or_target_rerun=True),indent=2)+'\n')
 print('4new source/2actual object acquire refusals;review/inverse exact,32+64 CAS/acquire emitted,no API/model')


if __name__=='__main__':main()
