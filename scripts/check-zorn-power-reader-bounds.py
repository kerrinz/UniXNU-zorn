#!/usr/bin/env python3
"""Reproduce and isolate power-source CLI file-read bounds without runtime selection."""
from pathlib import Path
import argparse, difflib, hashlib, json, shutil, subprocess, sys

R = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--out', type=Path, required=True)
O = ap.parse_args().out.resolve()
O.mkdir(exist_ok=False)
P = R / 'out/zorn/gpu-provenance-bounded-read-20261103'
S = R / 'UniXNU-zorn/scripts/read-zorn-gpu-power-source.py'
PIN = '8e15bbef1f754f2808f5ffeeff76bdd0a707f5d8f77a136cec621f3d7929361b'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
assert sha(S) == PIN
old = S.read_text()
(O / 'original.py.txt').write_text(old)
M = O / 'mirror'
for f in (P / 'mirror').rglob('*'):
    if f.is_file():
        dest = M / f.relative_to(P / 'mirror')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dest)
T = M / 'UniXNU-zorn/scripts'
graph = T / 'verify-zorn-gpu-reference-source.py'
provenance = T / 'verify-zorn-gpu-source-provenance.py'
assert sha(graph) == json.loads((P / 'reference-reader/result.json').read_text())['candidate_SHA']
assert sha(provenance) == json.loads((P / 'result.json').read_text())['candidate_SHA']
overlay = R / 'UniXNU-zorn/scripts/inspect-zorn-gpu-overlay-inputs.py'
shutil.copyfile(overlay, T / overlay.name)
loader = '''def input_reader():
    """Use the strictly pinned candidate helper before any input read/hash."""
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    if sha(GRAPH.read_bytes())!=GRAPH_SHA:
        raise ValueError('pinned graph verifier changed')
    graph=runpy.run_path(str(GRAPH))
    if sha(graph['PROVENANCE'].read_bytes())!=graph['PROVENANCE_SHA']:
        raise ValueError('pinned provenance verifier changed')
    impl=runpy.run_path(str(graph['PROVENANCE']))
    if sha(impl['PARSER'].read_bytes())!=impl['PARSER_SHA']:
        raise ValueError('pinned raw parser changed')
    return impl


'''
new = old.replace('05973a22c22e8b40d83ae37d67890ab4af7d96b5c91a1f73de4992d6f9caa19b', sha(graph))
new = new.replace('def main():', loader + 'def main():')
new = new.replace("    blob=a.dtb.read_bytes();digest=hashlib.sha256(blob).hexdigest()", """    try:
        impl=input_reader()
        blob=impl['read_bounded'](a.dtb,impl['MAX_RAW_DTB_BYTES'],'raw DTB')
        digest=hashlib.sha256(blob).hexdigest()
    except (ValueError,TypeError,OSError) as exc:
        p.error(str(exc))""")
new = new.replace("            provenance,rows=verified_graph(root,digest,a.graph_json.read_bytes(),a.graph_sha256)",
                  "            source=impl['read_bounded'](a.graph_json,impl['MAX_SOURCE_JSON_BYTES'],'source JSON')\n            provenance,rows=verified_graph(root,digest,source,a.graph_sha256)")
assert new != old
C = T / S.name
C.write_text(new)
(O / 'power-reader.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(
    old.splitlines(True), new.splitlines(True), fromfile='a/scripts/' + S.name, tofile='b/scripts/' + S.name)))
wrapper = '''from pathlib import Path
import runpy,sys,json
script=Path(sys.argv[1]);args=sys.argv[2:];watched={str(Path(args[args.index(k)+1]).resolve()) for k in ['--dtb','--graph-json'] if k in args};events=[];real_open=Path.open
class Observed:
 def __init__(self,stream,path):self.stream=stream;self.path=path
 def __enter__(self):return self
 def __exit__(self,*a):return self.stream.__exit__(*a)
 def read(self,n=-1):
  data=self.stream.read(n);events.append(dict(path=self.path,requested=n,returned=len(data)));return data
def opened(path,*a,**k):
 stream=real_open(path,*a,**k);resolved=str(path.resolve());return Observed(stream,resolved) if resolved in watched else stream
Path.open=opened;sys.argv=[str(script),*args];code=0
try:runpy.run_path(str(script),run_name='__main__')
except SystemExit as e:code=e.code
finally:Path.open=real_open;print('READ_TRACE='+json.dumps(events),file=sys.stderr)
raise SystemExit(code)
'''
(O / 'trace-cli.py').write_text(wrapper)
limit = 16 * 1024 * 1024
for name, size in [('oversized-dtb.bin',limit+8192),('oversized-graph.json',limit+8192),('exact-dtb.bin',limit),('plus-one-dtb.bin',limit+1)]:
    with (O / name).open('wb') as f:
        f.truncate(size)
manifest = json.loads((R / 'out/zorn/gpu-power-source-compare-20261103/inputs.json').read_text())
row = manifest['sources'][0]
raw, source = Path(row['dtb']), Path(row['graph_json'])
guard = R / 'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
events = []
def cli(script, dtb, graph_input, name, legacy=False, guarded=True):
    cmd = [sys.executable, '-B']
    if guarded:
        cmd += [str(guard)]
    cmd += [str(O / 'trace-cli.py'), str(script), '--dtb', str(dtb), '--sha256', sha(dtb)]
    if legacy:
        cmd += ['--out', str(O / (name + '.output.json'))]
    else:
        cmd += ['--stdout', '--graph-json', str(graph_input), '--graph-sha256', sha(graph_input)]
    p = subprocess.run(cmd, capture_output=True)
    (O / (name + '.stdout.raw')).write_bytes(p.stdout)
    (O / (name + '.stderr.raw')).write_bytes(p.stderr)
    events.append(dict(name=name, command=cmd, returncode=p.returncode))
    save(O / 'events.json', events)
    trace = json.loads(p.stderr.split(b'READ_TRACE=')[-1])
    return p, trace

# The real original path reads the full oversized file before its eventual refusal.
b, bt = cli(S, O/'oversized-dtb.bin', source, 'before-dtb')
a, at = cli(C, O/'oversized-dtb.bin', source, 'after-dtb')
assert b.returncode == a.returncode == 2 and bt[0]['requested'] == -1
assert at[0]['requested'] == limit+1 and at[0]['returned'] == limit+1
assert b'raw DTB reader bound' in a.stderr and not a.stdout and len(at) == 1
b, bg = cli(S, raw, O/'oversized-graph.json', 'before-graph')
a, ag = cli(C, raw, O/'oversized-graph.json', 'after-graph')
assert b.returncode == a.returncode == 2 and bg[1]['requested'] == -1
assert ag[1]['requested'] == limit+1 and b'source JSON reader bound' in a.stderr and not a.stdout
for filename, bounded in [('exact-dtb.bin',False),('plus-one-dtb.bin',True)]:
    p, trace = cli(C, O/filename, source, filename)
    assert p.returncode == 2 and (b'raw DTB reader bound' in p.stderr) == bounded
    assert trace[0]['requested'] == limit+1
legacy, lt = cli(C, O/'oversized-dtb.bin', source, 'legacy-refusal', legacy=True)
assert legacy.returncode == 2 and b'raw DTB reader bound' in legacy.stderr
assert not (O/'legacy-refusal.output.json').exists()
equivalences = []
for i, entry in enumerate(manifest['sources'][:2]):
    dtb, graph_input = Path(entry['dtb']), Path(entry['graph_json'])
    before, _ = cli(S, dtb, graph_input, 'real-before-'+str(i))
    after, trace = cli(C, dtb, graph_input, 'real-after-'+str(i))
    assert before.returncode == after.returncode == 0 and before.stdout == after.stdout
    assert all(t['requested'] == limit+1 for t in trace)
    doc=json.loads(after.stdout)
    assert not doc['generated_policy'] and not doc['hardware_qualification']
    equivalences.append(dict(source_id=entry['id'], stdout_bytes_identical=True))
# Legacy's successful exclusive output behavior is preserved in a fresh directory.
for script, name in [(S,'legacy-before'),(C,'legacy-after')]:
    p, _ = cli(script,raw,source,name,legacy=True,guarded=False)
    assert p.returncode == 0
assert (O/'legacy-before.output.json').read_bytes() == (O/'legacy-after.output.json').read_bytes()
# Both dependency layers remain exact, including on the legacy path.
for dependency, error in [(graph,b'pinned graph verifier changed'),(provenance,b'pinned provenance verifier changed')]:
    saved=dependency.read_bytes()
    try:
        dependency.write_bytes(saved+b'\n# isolated tamper\n')
        p, trace=cli(C,raw,source,'pin-refusal-'+dependency.stem)
        assert p.returncode == 2 and error in p.stderr and trace == []
    finally:
        dependency.write_bytes(saved)
assert sha(S) == PIN
result=dict(scope='isolated UNAPPLIED power-source CLI input bounds;no policy selection',
            original_SHA=PIN,original_unchanged=True,candidate_SHA=sha(C),
            before_DTB_trace=bt,after_DTB_trace=at,before_graph_trace=bg,after_graph_trace=ag,
            exact_and_plus_one_boundary_pass=True,legacy_oversize_creates_no_output=True,
            legacy_success_output_bytes_identical=True,two_real_stdout_equivalences=equivalences,
            two_candidate_pin_refusals_before_input_read=True,
            new_legacy_dependency_requirement='strict candidate graph/provenance/parser pins checked before input;not runtime qualification',
            guarded_stdout_paths_no_write_process=True,legacy_success_writes_fresh_host_outputs_only=True,
            candidate_graph_SHA=sha(graph),candidate_provenance_SHA=sha(provenance),
            hardware_qualification=False,native_execution=False,device_operations=False)
save(O/'result.json',result)
print('PASS: actual DTB/graph read amplification reproduced and bounded;2 real stdout and legacy equivalence;exact/+1,pins,no-partial-output')
