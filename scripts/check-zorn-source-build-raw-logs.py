#!/usr/bin/env python3
"""Only new raw-stream preservation paths and one changed-entry compile smoke check."""
import hashlib,json,runpy,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/gpu-source-data-build-entry-20261103'
TOOL=ROOT/'UniXNU-zorn/scripts/build-zorn-source-data-review.py'
def main():
    out=OUT/'raw-mode-real-build'
    q=subprocess.run([sys.executable,'-B',str(TOOL),'--source-review-only','--execute','--out-dir',str(out)],capture_output=True,text=True)
    assert q.returncode==0 and not q.stderr,(q.returncode,q.stderr,q.stdout)
    actual=json.loads(q.stdout);assert actual['completed'] and len(actual['commands'])==2
    for command in actual['commands']:
        assert command['returncode']==0
        for stream in command['raw_streams'].values():
            raw=Path(stream['path']).read_bytes();assert len(raw)==stream['bytes'] and hashlib.sha256(raw).hexdigest()==stream['sha256']
    env=runpy.run_path(str(TOOL));failures=[]
    for mode in ['nonutf8-return-error','nonutf8-timeout']:
        directory=OUT/mode;plan,content,model=env['preflight'](directory)
        stdout=b'fixture stdout\xff\x00\n';stderr=b'fixture stderr\xfe\x00\n'
        def failure(command,**kwargs):
            assert kwargs['text'] is False
            if mode=='nonutf8-timeout':raise subprocess.TimeoutExpired(command,30,output=stdout,stderr=stderr)
            return subprocess.CompletedProcess(command,7,stdout,stderr)
        r=env['execute_build'](plan,content,model,runner=failure)
        assert not r['completed'] and len(r['commands'])==1 and not (directory/'isolated-source-data.o').exists()
        streams=r['commands'][0]['raw_streams'];assert Path(streams['stdout']['path']).read_bytes()==stdout and Path(streams['stderr']['path']).read_bytes()==stderr and Path(streams['log']['path']).read_bytes()==stdout+stderr
        assert all((directory/name).exists() for name in ['result.json','build-events.jsonl','UnselectedSourceTables.h'])
        failures.append(dict(case=mode,synthetic_failure_only=True,raw_streams=streams,returncode=r['commands'][0]['returncode'],timeout=r['commands'][0].get('timeout',False)))
    (OUT/'raw-log-result.json').write_text(json.dumps(dict(one_actual_changed_entry_build=actual,focused_raw_failure_cases=failures,non_UTF8_and_NUL_bytes_preserved=True,no_old_suite_reexecution=True,no_native_or_device_execution=True),indent=2)+'\n')
    print('PASS:changed entry actual data-only build;2explicit raw failure fixtures retain exact stdout/stderr/NUL/nonUTF8 bytes;0native/device')
if __name__=='__main__':main()
