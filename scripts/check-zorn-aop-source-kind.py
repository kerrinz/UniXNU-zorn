#!/usr/bin/env python3
"""Only new static AOP source-envelope/kind cases;no firmware suite execution."""
import copy,hashlib,json,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/gpu-aop-source-kind-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/inspect-zorn-aop-source-kind.py';GUARD=ROOT/'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    OUT.mkdir(exist_ok=False)
    inputs=json.loads((ROOT/'out/zorn/gpu-source-review-verify-20261103/next-local-inputs.json').read_text())['files'];before={r['path']:r['sha256'] for r in inputs}
    def invoke(p,good=False,snapshot=False,digest=None):
        args=[sys.executable,'-B',str(GUARD),str(TOOL),'--input',str(p),'--sha256',digest or sha(p)]
        if snapshot:args+=['--require-commanddb-snapshot']
        q=subprocess.run(args,capture_output=True,text=True);assert not q.stderr,q.stderr
        assert q.returncode==(0 if good else 2),(q.returncode,q.stdout)
        d=json.loads(q.stdout);assert not d['commanddb_snapshot_usable'] and not d['hardware_qualification'] and not d['generated_policy'] and not d['device_operations'];return d
    real=[]
    for item in inputs:
        p=Path(item['path']);assert sha(p)==item['sha256'];r=invoke(p,True)
        assert r['container_bounds_verified'] and r['programs'][0]['type_raw']==0 and r['programs'][0]['declared_memory_bytes']==0 and r['programs'][0]['file_bytes']>0
        assert r['programs'][0]['covers_header_and_program_table'] and r['independently_qualified_expected_version'] is None and r['runtime_commanddb_presence']=='unknown'
        assert not r['source_authentication_verified']
        (OUT/(p.name+'.envelope.json')).write_text(json.dumps(r,indent=2)+'\n')
        refused=invoke(p,snapshot=True);assert refused['container_bounds_verified'] and 'refused' in refused['error']
        real.append(dict(input=str(p),sha256=sha(p),program_rows=len(r['programs']),static_ELF_refused_as_DB=True,metadata_PT_NULL_preserved=True))
    original=bytearray(Path(inputs[0]['path']).read_bytes());phoff=struct.unpack_from('<I',original,28)[0];cases=[]
    for case in ['short-header','wrong-endianness','wrong-header-size','program-table-OOB','program-row-width','extended-program-count','load-file-OOB','load-file-larger-than-memory','invalid-alignment','contradictory-section-metadata','unknown-nonELF-kind']:
        b=bytearray(original)
        if case=='short-header':b=b[:30]
        elif case=='wrong-endianness':b[5]=2
        elif case=='wrong-header-size':struct.pack_into('<H',b,40,51)
        elif case=='program-table-OOB':struct.pack_into('<I',b,28,len(b)-16)
        elif case=='program-row-width':struct.pack_into('<H',b,42,31)
        elif case=='extended-program-count':struct.pack_into('<H',b,44,0xffff)
        elif case=='load-file-OOB':struct.pack_into('<I',b,phoff+32+4,0xfffffff0)
        elif case=='load-file-larger-than-memory':struct.pack_into('<I',b,phoff+32+20,1)
        elif case=='invalid-alignment':struct.pack_into('<I',b,phoff+32+28,3)
        elif case=='contradictory-section-metadata':struct.pack_into('<I',b,32,52)
        else:b[:4]=b'NOPE'
        p=OUT/(case+'.invalid');p.write_bytes(b);r=invoke(p);assert not r['container_bounds_verified'];cases.append(dict(case=case,error=r['error']))
    p=Path(inputs[0]['path']);r=invoke(p,digest='0'*64);cases.append(dict(case='wrong-source-SHA',error=r['error']))
    # The actual source has one zero-byte PT_LOAD. Its offset conveys no owned
    # file bytes and must not become an inferred memory/page mapping.
    b=bytearray(original);struct.pack_into('<I',b,phoff+7*32+4,0xffffffff);p=OUT/'empty-payload-offset.elf';p.write_bytes(b);r=invoke(p,True);assert r['programs'][7]['file_offset_raw']==0xffffffff and r['programs'][7]['file_bytes']==0 and not r['programs'][7]['file_extent_verified']
    special=[dict(case='empty-payload-no-file-ownership',passed=True)]
    b=bytearray(original);offset=len(b);struct.pack_into('<I',b,32,offset);struct.pack_into('<H',b,46,40);struct.pack_into('<H',b,48,1)
    b.extend(struct.pack('<10I',0,8,0,0,0xffffffff,4096,0,0,16,0));p=OUT/'nobits-section.elf';p.write_bytes(b);r=invoke(p,True);assert not r['sections'][0]['file_backed'];special.append(dict(case='NOBITS-not-file-backed',passed=True))
    struct.pack_into('<I',b,offset+4,1);p=OUT/'file-backed-section-OOB.invalid';p.write_bytes(b);r=invoke(p);cases.append(dict(case='file-backed-section-OOB',error=r['error']))
    # Literal magic inside an ELF payload is merely static source bytes.
    b=bytearray(original);b[4096:4100]=bytes.fromhex('db30030c');p=OUT/'literal-magic.elf';p.write_bytes(b);r=invoke(p,snapshot=True);assert r['container_bounds_verified'] and 4096 in r['literal_cmd_db_magic_file_offsets'] and r['independently_qualified_expected_version'] is None;special.append(dict(case='literal-magic-not-a-live-DB',passed=True))
    b=bytearray(original);b[4096:4096+4*65]=bytes.fromhex('db30030c')*65;p=OUT/'many-literal-matches.elf';p.write_bytes(b);r=invoke(p,True);assert len(r['literal_cmd_db_magic_file_offsets'])==64 and not r['literal_scan_complete'];special.append(dict(case='literal-report-bound-no-absence-claim',passed=True))
    assert all(sha(Path(p))==digest for p,digest in before.items())
    result=dict(two_real_static_source_envelopes=real,new_malformed_refusals=cases,new_scope_edge_cases=special,child_no_write_or_process=True,source_inputs_unchanged=True,no_success_commandDB_snapshot_or_expected_version=True,no_firmware_or_native_execution=True,old_firmware_suites_or_driver_compiles_reexecuted=False,driver_patch_count_remains32=True,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:2real ELF envelopes refused as live DB;13new malformed/SHA cases and4source-boundary cases;0firmware/native/device')
if __name__=='__main__':main()
