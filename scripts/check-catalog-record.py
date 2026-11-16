#!/usr/bin/env python3
"""Keep the catalog TOML bounded,complete and distinct from its historical ledger."""
import argparse,copy,hashlib,importlib.machinery,importlib.util,json,tempfile,tomllib
from pathlib import Path

MAX_BYTES=48*1024

def read_entry(raw):
    if len(raw)>MAX_BYTES:
        raise ValueError('catalog entry exceeds48KiB;archive history and summarize current evidence')
    return tomllib.loads(raw.decode('utf-8'))

def module(path,name):
    loader=importlib.machinery.SourceFileLoader(name,str(path))
    spec=importlib.util.spec_from_loader(name,loader)
    obj=importlib.util.module_from_spec(spec);loader.exec_module(obj);return obj

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--upstream',type=Path)
    parser.add_argument('--sync-script',type=Path)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args();root=args.device.resolve();raw=(root/'porting.toml').read_bytes();record=read_entry(raw)
    meta=json.loads((root/'docs/history/porting-archive-2026-11-17.json').read_text())
    archive=(root/meta['archive']).resolve();assert archive.is_relative_to(root)
    history=archive.read_bytes();assert len(history)==meta['bytes'] and hashlib.sha256(history).hexdigest()==meta['sha256']
    old=tomllib.loads(history.decode());assert sum(len(a.get('evidence',[])) for a in old['area'])==meta['historical_evidence_entries']
    assert [a['id'] for a in old['area']]==meta['areas']==[a['id'] for a in record['area']]
    # Compaction must not change board inputs,components,configuration or required procedures.
    for before,after in zip(old['area'],record['area']):
        for key in ['id','components','inputs','configuration','procedure','completion']:
            assert before[key]==after[key],(before['id'],key)
        assert set(before['paths'])<=set(after['paths'])
    board=tomllib.loads((root/'board.toml').read_text());assert record['device']['name']==board['board']['name']=='zorn'
    for a in record['area']:
        for e in a.get('evidence',[]):
            ref=e['reference']
            if '://' not in ref:assert (root/ref.split('#')[0]).is_file(),ref
    refused=[]
    for name,data in [('oversized-valid-TOML',raw+b'\n#'+b'x'*MAX_BYTES),('unterminated-string',b'schema_version = 1\nsummary = "open')]:
        try:read_entry(data)
        except ValueError:refused.append(name)
        else:raise AssertionError(name)
    regression=None
    if args.upstream:
        tools=module(args.upstream.resolve()/'scripts/porting-record.py','zorn_catalog_record_tools')
        tools.validate(record,board,'kerrinz/UniXNU-zorn',allow_custom_components=True)
        sync=module(args.sync_script.resolve() if args.sync_script else args.upstream.resolve()/'scripts/sync-devices.py','zorn_catalog_sync')
        with tempfile.TemporaryDirectory() as tmp:
            sync.SNAPSHOTS=Path(tmp);results={}
            for name,data in [('complete-history',history),('truncated-history',history[:524288]),('concise-current',raw)]:
                entry=dict(name='zorn',repository='kerrinz/UniXNU-zorn',format=2,legacy_page='preserve',title='Redmi K80',title_zh='Redmi K80')
                fixture=dict(nameWithOwner='kerrinz/UniXNU-zorn',databaseId=1432118290,defaultBranchRef=dict(target=dict(oid='HOST-FIXTURE-NOT-A-PUBLISHED-REVISION')),board=dict(text=(root/'board.toml').read_text()),record=dict(text=data.decode('utf-8',errors='ignore') if name=='truncated-history' else data.decode()))
                sync.update_entry(entry,fixture,tools);results[name]={k:entry.get(k) for k in ['record_state','record_error']}
            assert results['complete-history']['record_state']=='available',results
            assert results['truncated-history']==dict(record_state='invalid',record_error='Unterminated string (at end of document)'),results
            assert results['concise-current']['record_state']=='available',results
            regression=dict(results=results,scope='Actual official ingestion function,synthetic metadata and explicit524288-byte prefix rounded to complete UTF8;not an authenticated GitHub GraphQL response',sync_source_sha256=hashlib.sha256(Path(sync.__file__).read_bytes()).hexdigest(),validator_source_sha256=hashlib.sha256(Path(tools.__file__).read_bytes()).hexdigest())
    result=dict(passed=True,entry_bytes=len(raw),entry_max_bytes=MAX_BYTES,history_bytes=len(history),history_sha256=meta['sha256'],history_evidence_entries=meta['historical_evidence_entries'],controls=refused,official_ingestion_regression=regression,phone_access=False,remote_modified=False)
    if args.out:args.out.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS catalog entry',len(raw),'bytes;complete history',meta['historical_evidence_entries'],'evidence entries preserved;ingestion regression',bool(regression))

if __name__=='__main__':main()
