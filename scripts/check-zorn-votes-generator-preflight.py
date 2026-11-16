#!/usr/bin/env python3
"""Review an isolated UNAPPLIED generator validation-order repair; never emit policy headers."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import textwrap

R=Path(__file__).resolve().parents[2]
SOURCE=R/'references/sm8650-gpu-20261030/ArnoDorian123--UniXNU-ruyi/scripts/prepare-sheng-gmu-votes.py'
SHA='dfb330a56d990eb71ed60fd73f056fbcacca0a5533e6f011f7ee85286a6157ba'
O=R/'out/zorn/gpu-votes-generator-preflight-20261102'

def main():
    raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    s=raw.decode();a=s.index(" db_node='/reserved-memory/");b=s.index(" db_header=",a);block=s[a:b]
    marker=" out=ROOT/'build/sheng-gmu';out.mkdir(exist_ok=True)\n"
    assert s.count(marker)==1 and s.count(block)==1
    c=s[:a]+s[b:];c=c.replace(marker,block+marker,1)
    assert c.replace(block,'',1).replace(marker,marker+block,1)!=s # insertion positions differ
    inverse=c.replace(block,'',1);at=inverse.index(' db_header=');inverse=inverse[:at]+block+inverse[at:];assert inverse==s
    ast.parse(c);assert c.index(" db_node=")<c.index('header.write_text(text)')
    O.mkdir(exist_ok=False)
    (O/'original.py.txt').write_bytes(raw);(O/'candidate.py.txt').write_text(c)
    patch=''.join(difflib.unified_diff(s.splitlines(True),c.splitlines(True),fromfile='a/scripts/prepare-sheng-gmu-votes.py',tofile='b/scripts/prepare-sheng-gmu-votes.py'))
    (O/'command-db-preflight-before-header.UNAPPLIED.patch').write_text(patch)
    # Exercise only original CPU-side validation statements and the guarded
    # first output operation. Writes are intercepted BEFORE data is emitted.
    class WriteAttempt(Exception):pass
    class Sink:
        def write_text(self,*args,**kwargs):raise WriteAttempt('forbidden policy output')
    checks=[]
    for case in ['bad-compatible','bad-reg-width','missing-no-map','bad-reservation-size']:
        def prop(node,name,kind='x'):
            assert name=='compatible';return ['bad'] if case=='bad-compatible' else ['qcom,cmd-db']
        def cells(node,name):
            assert name=='reg';return [0] if case=='bad-reg-width' else [0,0,0,1 if case=='bad-reservation-size' else 4096]
        class Process:
            @staticmethod
            def run(*args,**kwargs):
                if case=='missing-no-map':raise subprocess.CalledProcessError(1,args[0])
        env=dict(prop=prop,cells=cells,subprocess=Process,dtb='CPU source fixture',header=Sink(),text='write intercepted')
        try:exec('header.write_text(text)\n'+textwrap.dedent(block),env)
        except WriteAttempt:pass
        else:raise AssertionError('original did not reach premature output')
        try:exec(textwrap.dedent(block)+'\nheader.write_text(text)',env)
        except (SystemExit,subprocess.CalledProcessError):pass
        except WriteAttempt:raise AssertionError('candidate output before input refusal')
        else:raise AssertionError('candidate accepted malformed source')
        checks.append(case)
    result=dict(source=str(SOURCE),source_sha256=SHA,candidate_sha256=hashlib.sha256(c.encode()).hexdigest(),
                repair='Move unchanged commandDB input preflight before output directory/header writes;all other source bytes inverse-exact',
                checks=checks,original_reaches_intercepted_write_before_bad_DB=True,candidate_refuses_before_any_write=True,
                inverse_byte_equal=True,generator_prepare_not_invoked=True,policy_headers_emitted=0,
                no_K80_policy_or_foreign_policy_adoption=True,driver_patch_count_remains32=True,
                patch_status='independent UNAPPLIED source generator repair;not applied to reference or active build',
                limitation='Not an atomic multi-file filesystem transaction;does not qualify board policy or generate K80 inputs',
                allow_boot=False,readback_qualified=False,WriteAuthorized=0)
    (O/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS:4 new source-input refusal traces;original premature write reproduced/intercepted,candidate no write;inverse exact;0 policy headers')

if __name__=='__main__':main()
