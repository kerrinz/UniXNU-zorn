#!/usr/bin/env python3
"""Check the reference CLI's own file reads in an isolated pinned repair chain."""
from pathlib import Path
import argparse, difflib, hashlib, json, subprocess, sys

R = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
O = a.out.resolve()
O.mkdir(exist_ok=False)
P = R / 'out/zorn/gpu-provenance-bounded-read-20261103'
S = R / 'UniXNU-zorn/scripts/verify-zorn-gpu-reference-source.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
pin = '05973a22c22e8b40d83ae37d67890ab4af7d96b5c91a1f73de4992d6f9caa19b'
assert sha(S) == pin
original = S.read_text()
(O / 'original.py.txt').write_text(original)
provenance = P / 'mirror/UniXNU-zorn/scripts/verify-zorn-gpu-source-provenance.py'
candidate = original.replace(
    '245b28b55bebd95861933216136fef4c2115c55cdd2dc11f6d96befd07491eb4', sha(provenance))
candidate = candidate.replace(
    '        source, raw = args.input.read_bytes(), args.dtb.read_bytes()',
    "        source = impl['read_bounded'](args.input, impl['MAX_SOURCE_JSON_BYTES'], 'source JSON')\n"
    "        raw = impl['read_bounded'](args.dtb, impl['MAX_RAW_DTB_BYTES'], 'raw DTB')")
candidate = candidate.replace("        if len(source) > 16 * 1024 * 1024:\n            raise ValueError('source JSON reader bound')\n", '')
assert candidate != original
C = provenance.with_name(S.name)
assert not C.exists()
C.write_text(candidate)
(O / 'reference-reader.UNAPPLIED.patch').write_text(''.join(difflib.unified_diff(
    original.splitlines(True), candidate.splitlines(True),
    fromfile='a/scripts/' + S.name, tofile='b/scripts/' + S.name)))
guard = R / 'out/zorn/gpu-votes-source-cli-20261103/no-side-effects.py'
events = []
def cli(script, source, dtb, name):
    cmd = [sys.executable, '-B', str(guard), str(P / 'trace-cli.py'), str(script),
           '--input', str(source), '--input-sha256', sha(source),
           '--dtb', str(dtb), '--dtb-sha256', sha(dtb), '--graph-check-only']
    p = subprocess.run(cmd, capture_output=True)
    (O / (name + '.stdout.raw')).write_bytes(p.stdout)
    (O / (name + '.stderr.raw')).write_bytes(p.stderr)
    events.append(dict(name=name, command=cmd, returncode=p.returncode))
    (O / 'events.json').write_text(json.dumps(events, indent=2) + '\n')
    return p.returncode, json.loads(p.stdout), json.loads(p.stderr)['real_read_trace']

_, before, old = cli(S, P / 'oversized-json.bin', P / 'small.dtb', 'before-json')
code, after, new = cli(C, P / 'oversized-json.bin', P / 'small.dtb', 'after-json')
assert code == 2 and before['error'] == after['error'] == 'source JSON reader bound'
assert len(old) == 2 and old[0]['requested'] == -1
assert len(new) == 1 and new[0]['requested'] == 16 * 1024 * 1024 + 1
_, _, old_raw = cli(S, P / 'small.json', P / 'oversized-dtb.bin', 'before-dtb')
code, after, new_raw = cli(C, P / 'small.json', P / 'oversized-dtb.bin', 'after-dtb')
assert code == 2 and after['error'] == 'raw DTB reader bound'
assert old_raw[1]['requested'] == -1 and new_raw[1]['requested'] == 16 * 1024 * 1024 + 1
manifest = json.loads((R / 'out/zorn/gpu-power-source-compare-20261103/inputs.json').read_text())
equivalences = []
for i, row in enumerate(manifest['sources'][:2]):
    bcode, before, _ = cli(S, Path(row['graph_json']), Path(row['dtb']), 'real-before-' + str(i))
    acode, after, trace = cli(C, Path(row['graph_json']), Path(row['dtb']), 'real-after-' + str(i))
    assert bcode == acode == 0 and before == after and after['graph_verified']
    assert all(t['requested'] == 16 * 1024 * 1024 + 1 for t in trace)
    assert not after['hardware_qualification'] and not after['generated_policy']
    equivalences.append(dict(source_id=row['id'], output_identical=True, graph_verified=True))
# A damaged candidate dependency must fail before either data file is opened.
saved = provenance.read_bytes()
try:
    provenance.write_bytes(saved + b'\n# deliberate isolated pin mismatch\n')
    code, refusal, trace = cli(C, P / 'small.json', P / 'small.dtb', 'candidate-pin-refusal')
    assert code == 2 and refusal['error'] == 'pinned provenance implementation changed' and trace == []
finally:
    provenance.write_bytes(saved)
assert sha(S) == pin
result = dict(original_unchanged=True, original_SHA=pin, candidate_SHA=sha(C),
              provenance_candidate_SHA=sha(provenance), candidate_dependency_pin_enforced=True,
              before_json_trace=old, after_json_trace=new,
              before_raw_trace=old_raw, after_raw_trace=new_raw,
              real_input_equivalences=equivalences, guarded_no_write_process=True,
              old_proofs_or_pins_updated=False, device_operations=False, hardware_qualification=False)
(O / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: reference own-read bounds,2 real graph equivalences,strict candidate pin refusal;original chain unchanged')
