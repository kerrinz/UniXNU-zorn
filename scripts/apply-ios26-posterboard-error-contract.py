#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Apply the pinned iOS26 PosterBoard source fix to a new host file only."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


DEVICE = Path(__file__).resolve().parents[1]
PATCH = DEVICE / 'patches/ios26/userland/posterboard-nserror-contract.patch'
MANIFEST = PATCH.with_suffix('.json')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--output', type=Path)
    action.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    manifest = json.loads(MANIFEST.read_text())
    matching = [item for item in manifest['variants']
                if item['base_source_sha256'] == digest(source)]
    if len(matching) != 1:
        parser.error('source is not the pinned iOS26 baseline')
    cohort = matching[0]
    patch = PATCH.parent / cohort['patch']
    if patch.parent != PATCH.parent or digest(patch) != cohort['patch_sha256']:
        parser.error('pinned patch bytes changed')
    if args.check_only:
        print(json.dumps({'cohort': cohort['name'], 'source_matches': True, 'patch_matches': True,
                          'source_modified': False, 'device_access': False}))
        return
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        parser.error('output must be a new file')
    output.parent.mkdir(parents=True, exist_ok=True)
    before = source.stat()
    result = subprocess.run(
        ['/usr/bin/patch', '-f', '-F0', '-i', str(patch), '-o', str(output),
         '-r', str(output) + '.rejects', str(source)],
        capture_output=True, text=True, timeout=20)
    if result.returncode:
        parser.error('patch failed: ' + result.stderr[-1000:])
    if digest(output) != cohort['patched_source_sha256']:
        parser.error('patched source hash differs')
    after = source.stat()
    if digest(source) != cohort['base_source_sha256'] or (
            before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (
            after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode):
        parser.error('source changed during application')
    print(json.dumps({'cohort': cohort['name'], 'output': str(output), 'sha256': digest(output),
                      'source_modified': False, 'device_access': False}))


if __name__ == '__main__':
    main()
