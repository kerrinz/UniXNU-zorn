#!/usr/bin/env python3
"""Only the new offline raw-file decoder is tested;synthetic bytes are not a device snapshot."""
from pathlib import Path
import argparse,importlib.util,hashlib,json,struct,subprocess,sys
R=Path(__file__).resolve().parents[2];p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();O=a.out.resolve();O.mkdir(exist_ok=False)
S=R/'UniXNU-zorn/scripts/decode-zorn-commanddb-file.py';spec=importlib.util.spec_from_file_location('raw_decoder',S);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sha(b):return hashlib.sha256(b).hexdigest()
def fixture():
 b=bytearray(256);b[:4]=b'\x78\x56\x34\x12';b[4:8]=m.MAGIC;struct.pack_into('<4H',b,8,9,0,48,2)
 b[144:152]=b'\xffa\0\0raw!';b[168:176]=b'\xffa\0\0raw!'
 b[160:164]=bytes.fromhex('01020304');struct.pack_into('<2H',b,164,3,0);struct.pack_into('<2H',b,188,0,64);b[192:195]=b'\xff\0A';return b
b=fixture();(O/'synthetic.bin').write_bytes(b);d=m.decode(b,len(b),sha(b));assert d['entry_count']==2 and len(d['duplicate_resource_ids'])==1 and d['rows'][0]['entries'][0]['aux_raw_hex']=='ff0041' and not d['snapshot_qualified'] and not d['expected_version_qualified']
valid=[dict(case='all-raw-fields-unknown-version-and-duplicate-IDs',passed=True)]
b2=fixture();struct.pack_into('<4H',b2,40,5,65535,65535,65535);d2=m.decode(b2,len(b2),sha(b2));assert not d2['rows'][2]['in_linux_search_prefix'] and 'entry_count' not in d2['rows'][2];valid.append(dict(case='post-terminator-rows-retained-not-searched',passed=True))
b3=fixture();struct.pack_into('<2H',b3,164,4,0);struct.pack_into('<H',b3,12,0);d3=m.decode(b3,len(b3),sha(b3));assert d3['rows'][0]['entries'][0]['aux_overlaps_record_table'];valid.append(dict(case='aux-alias-reported-without-eligibility',passed=True))
failures=[]
def reject(name,raw,n=None,digest=None):
 try:m.decode(raw,len(raw) if n is None else n,sha(raw) if digest is None else digest)
 except ValueError as e:failures.append(dict(case=name,error=str(e)))
 else:raise AssertionError(name)
reject('truncated-header',b[:143]);reject('declared-truncation',b,257);reject('extra-byte',b+b'x',256);reject('wrong-SHA',b,digest='0'*64);x=fixture();x[4]=0;reject('wrong-magic',x)
for name,prefix in [('ELF',b'\x7fELF'),('DTB',bytes.fromhex('d00dfeed'))]:
 x=fixture();x[:4]=prefix;reject(name+'-container',x)
x=fixture();struct.pack_into('<H',x,10,65535);reject('entry-table-OOB',x)
x=fixture();struct.pack_into('<H',x,12,65535);reject('aux-base-OOB',x)
x=fixture();struct.pack_into('<2H',x,164,65,0);reject('aux-length-OOB',x)
x=fixture();struct.pack_into('<H',x,14,4097);reject('entry-budget',x)
x=bytearray(72200);x[4:8]=m.MAGIC;struct.pack_into('<4H',x,8,9,0,0,3000);struct.pack_into('<4H',x,24,10,0,0,3000);reject('aggregate-entry-budget',x)
reject('oversized-declared-input',b,m.MAX_FILE_BYTES+1)
# Verify actual CLI file reading with no write/process audit guard.
guard=R/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
cmd=[sys.executable,'-B',str(guard),str(S),'--raw-reservation-file',str(O/'synthetic.bin'),'--expected-bytes','256','--source-sha256',sha(b)]
r=subprocess.run(cmd,capture_output=True);(O/'cli.stdout.raw').write_bytes(r.stdout);(O/'cli.stderr.raw').write_bytes(r.stderr);assert r.returncode==0 and json.loads(r.stdout)['decoded']
result=dict(scope='new raw file decoder only;synthetic layout cases,not actual captured memory',preservation_cases=valid,new_refusals=failures,guarded_cli_no_write_process=True,decoder_sha256=sha(S.read_bytes()),actual_snapshot_available=False,snapshot_qualified=False,expected_version_qualified=False,old_suites_or_target_builds_rerun=False,device_operations=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:3 preservation cases/13 refusal cases/guarded read-only CLI;no snapshot or GPU qualification')
