#!/usr/bin/env python3
"""Extract validated FDT source blobs from a SHA-pinned local image; never select a boot variant."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'UniXNU/scripts'))
from unixnu.devicetree import read_fdt, Error


def candidates(raw):
    pos = 0
    while True:
        at = raw.find(bytes.fromhex('d00dfeed'), pos)
        if at < 0:
            return
        pos = at + 4
        size = int.from_bytes(raw[at+4:at+8], 'big')
        if size < 40 or size > len(raw)-at:
            yield at, None, 'truncated or invalid declared length'
            continue
        blob = raw[at:at+size]
        try:
            root = read_fdt(blob)
        except (Error, ValueError, UnicodeError) as e:
            yield at, None, str(e)
            continue
        yield at, (blob, root), None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--sha256', required=True)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    raw = a.image.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != a.sha256:
        p.error('source image SHA mismatch')
    # No image layout inference,overlay application or output replacement.
    a.out.mkdir(parents=True, exist_ok=False)
    rows = []
    for at, value, error in candidates(raw):
        if error:
            rows.append(dict(offset=at, rejected=error))
            continue
        blob, root = value
        name = f'fdt-{at:08x}.dtb'
        with (a.out/name).open('xb') as f:
            f.write(blob)
        rows.append(dict(offset=at, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
                         file=name, compatible=root.strings('compatible'),
                         overlay_marker=any(n.name in ('__fixups__','__local_fixups__') for n in root.children)))
    report = dict(source=str(a.image.resolve()), source_sha256=digest,
                  parser_scope='validated embedded version17 FDTs only;not Android header/table attestation',
                  candidates=rows, boot_variant_selected=False, overlay_applied=False,
                  generated_policy=False, device_operations=False)
    with (a.out/'extraction.json').open('x') as f:
        json.dump(report,f,indent=2);f.write('\n')


if __name__ == '__main__':
    main()
