#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Test the pinned source wrappers with typed host stand-ins, without a phone."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


DEVICE = Path(__file__).resolve().parents[1]
MANIFEST = DEVICE / 'patches/ios26/userland/posterboard-nserror-contract.json'
READ = {'pb_store_for_provider': 'id', 'pb_create_dynamic': 'id',
        'pb_migrate': 'BOOL', 'pb_build': 'id', 'pb_fm_create': 'BOOL',
        'pb_data_write': 'BOOL', 'pb_fm_copy': 'BOOL', 'pb_url_update': 'BOOL'}
RETRY = {name: 'BOOL' for name in ('pb_url_conform', 'pb_fm_create',
         'pb_data_write', 'pb_set_purgable', 'pb_url_update')}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def wrapper(text, name, kind):
    match = re.search(r'\n' + name + r'\([^\n]*\)\n\{', text)
    if not match:
        raise ValueError('missing pinned wrapper: ' + name)
    start = match.start() + 1
    brace = text.index('{', start)
    depth = 0
    for end in range(brace, len(text)):
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
            if depth == 0:
                return 'static ' + kind + '\n' + text[start:end + 1]
    raise ValueError('incomplete pinned wrapper: ' + name)


def retry_cases():
    cases = []
    for index, name in enumerate(RETRY):
        if name == 'pb_set_purgable':
            sequences = [('1', 0, 0), ('0', 0, 0)]
        elif name == 'pb_data_write':
            sequences = [('1', 0, 0), ('0', 0, 0), ('01', 0, 1), ('00', 0, 1),
                         ('01', 0, 0xf0000000), ('00', 0, 0xf0000000),
                         ('01', 0, 0xf0000001), ('001', 0, 0xf0000001),
                         ('000', 0, 0xf0000001)]
        else:
            sequences = [('1', 1, 0), ('0', 0, 0), ('01', 1, 0), ('00', 1, 0)]
        for sequence, strip, options in sequences:
            for caller in (0, 1, 2):
                cases.append((index, sequence, strip, options, caller))
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    matching = [item for item in manifest['variants']
                if item['base_source_sha256'] == digest(args.baseline)]
    if len(matching) != 1 or digest(args.candidate) != matching[0]['patched_source_sha256']:
        parser.error('source hashes do not match the iOS26 patch manifest')
    args.output_dir.mkdir(parents=True)
    results = {}
    for group, names in [('read', READ), ('retry', RETRY)]:
        fixture = DEVICE / ('tests/ios26-posterboard-' + group + '-error-host.c.in')
        template = fixture.read_text()
        if template.count('@WRAPPERS@') != 1:
            raise ValueError('fixture wrapper slot differs')
        group_results = {}
        for label, path in [('baseline', args.baseline), ('candidate', args.candidate)]:
            text = path.read_text()
            bodies = '\n'.join(wrapper(text, name, kind) for name, kind in names.items())
            stem = args.output_dir / (group + '-' + label)
            source = stem.with_suffix('.c')
            source.write_text(template.replace('@WRAPPERS@', bodies))
            command = ['/usr/bin/clang', '-std=c11', '-fsanitize=address,undefined',
                       str(source), '-o', str(stem)]
            compile_result = subprocess.run(command, capture_output=True, text=True)
            stem.with_suffix('.compile.stderr').write_text(compile_result.stderr)
            compile_result.check_returncode()
            cases = ([(index, mode) for index in range(len(READ)) for mode in range(5)]
                     if group == 'read' else retry_cases())
            observations = []
            for index, case in enumerate(cases):
                last = str(int(label == 'baseline' if group == 'read' else label == 'candidate'))
                result = subprocess.run([str(stem), *map(str, case), last],
                                        capture_output=True, text=True)
                (args.output_dir / (stem.name + '-' + str(index) + '.stderr')).write_text(result.stderr)
                result.check_returncode()
                if group == 'retry':
                    observations.append(json.loads(result.stdout))
            group_results[label] = {'cases': len(cases), 'source_sha256': digest(path),
                                    'compile_arguments': command, 'observations': observations}
        if group == 'retry':
            differences = []
            for case, old, new in zip(retry_cases(), group_results['baseline']['observations'],
                                      group_results['candidate']['observations'], strict=True):
                if any(old[key] != new[key] for key in ('ok', 'calls', 'operands')):
                    raise AssertionError('native result/call sequence changed')
                if old['output'] != new['output']:
                    differences.append({'case': case, 'old': old, 'new': new})
            if not any(item['new']['ok'] for item in differences) or not any(
                    not item['new']['ok'] for item in differences):
                raise AssertionError('baseline success/failure regressions not reproduced')
            group_results['reproduced_output_differences'] = differences
        results[group] = group_results
    report = {'result': 'PASS', 'cohort': matching[0]['name'], 'groups': results, 'sanitizers': ['address', 'undefined'],
              'actual_patched_wrapper_bodies': True, 'Apple_implementations_executed': False,
              'device_access': False, 'runtime_boot_cause_proven': False}
    (args.output_dir / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'result': 'PASS', 'read_cases_per_variant': 40,
                      'retry_cases_per_variant': 69, 'device_access': False}))


if __name__ == '__main__':
    main()
