#!/usr/bin/env python3
"""Offline source/actual-object audit only; never invokes a native request."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
R=Path(__file__).resolve().parents[2];O=R/'out/zorn/gpu-catalog-preallocation-offer'
ident=json.loads((O/'source-repair-identity.json').read_text());src=Path(ident['candidate']).read_text();orig=Path(ident['original']).read_text()
assert not (O/'preallocation-offer-audit.json').exists()
def check(text):
 assert text.count(ident['new'])==1
 assert text.replace(ident['new'],ident['old'],1)==orig
 gate=text[text.index('        if(alloc) {'):text.index('        /* i e38a0b1eb:')]
 assert gate.index('output && output_size==sizeof(NativeAdrenoAbiBoAllocReply)')<gate.index('NativeAdrenoMemory::prepareSystem')
 assert 'request.align_log2>=12 && request.align_log2<=24' in gate
 assert 'if(connection->live_)connection->core_->offerSystemPages(nullptr);' in text
check(src);passed=[]
for label,old,new in [('missing-schema','output && output_size==sizeof(NativeAdrenoAbiBoAllocReply) &&','true &&'),('missing-align-lower','request.align_log2>=12 && ',' '),('missing-align-upper',' && request.align_log2<=24','')]:
 assert src.count(old)==1;bad=src.replace(old,new,1);(O/(label+'.source')).write_text(bad)
 try:check(bad)
 except AssertionError:passed.append(label)
 else:raise AssertionError('accepted '+label)
review=O/'source-review';review.mkdir();shutil.copyfile(Path(ident['original']),review/'NativeAdrenoPublish.cpp')
for label,args in [('check',['git','apply','--check',str(O/'preallocation-request-validation.UNAPPLIED.patch')]),('apply',['git','apply',str(O/'preallocation-request-validation.UNAPPLIED.patch')])]:
 p=subprocess.run(args,cwd=review,capture_output=True,text=True);(O/('review-'+label+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0
assert (review/'NativeAdrenoPublish.cpp').read_bytes()==Path(ident['candidate']).read_bytes()
asm=(O/'disassembly.log').read_text();call=re.search(r'^\s*([0-9a-f]+):\s+bl\s+__ZN18NativeAdrenoMemory13prepareSystemEmbP23NativeAdrenoSystemPages\s*$',asm,re.M);assert call
prefix=asm[max(0,call.start()-1600):call.start()]
# Unsigned [12,24] compiled as (align-25)+13 carry test;schema8/null and size guards precede native preparation.
for pattern in [r'cbz\s+x8,',r'cmp\s+x8, #0x8',r'sub\s+w8, w25, #0x19',r'cmn\s+w8, #0xd',r'b.lo\s+0x',r'cbnz\s+w24,',r'cbz\s+x26,',r'and\s+x8, x26, #0xfff',r'cmp\s+x26, x20',r'b.hi\s+0x']:
 assert re.search(pattern,prefix),pattern
layout=(O/'candidate-first.log').read_text();a=layout.index('0 | class AGXDeviceUserClient\n');b=layout.index('*** Dumping',a+1);assert '[sizeof=280,' in layout[a:b]
v=dict(new_source_mutations_refused=passed,independent_original_review_apply_inverse_equal=True,actual_output_null_size_and_unsigned_align_range_guards_before_prepare=True,actual_existing_size_contiguous_budget_guards_preserved=True,AGXDeviceUserClient_size=280,no_changed_class_header_or_new_wire=True,original_dispatch_returns_offer_withdrawal_and_cleanup_source_unchanged=True,no_runtime_API_successpeer_or_old_suite_execution=True)
(O/'preallocation-offer-audit.json').write_text(json.dumps(v,indent=2)+'\n');print('3new source refusals;actual schema/alignment guards before prepare;review inverse equal/class280')
