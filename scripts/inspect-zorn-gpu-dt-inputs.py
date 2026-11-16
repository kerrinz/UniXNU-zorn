#!/usr/bin/env python3
"""Inspect cached GPU DT source inputs. Emits no headers or runtime policy."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'UniXNU/scripts'))
DT = importlib.import_module('unixnu.devicetree')


def inspect(blob):
    tree = DT.read_fdt(blob)
    paths, nodes, handles = {}, {}, {}
    def visit(node, path):
        paths[id(node)] = path
        nodes[path] = node
        for child in node.children:
            childpath = path.rstrip('/') + '/' + child.name
            if childpath in nodes:
                raise ValueError('ambiguous node path: ' + childpath)
            visit(child, childpath)
    visit(tree, '/')
    for path, node in nodes.items():
        hs = [node.scalar(k) for k in ('phandle', 'linux,phandle') if k in node.properties]
        if hs and (len(set(hs)) != 1 or hs[0] in (0, 0xffffffff)):
            raise ValueError('invalid phandle at ' + path)
        if hs:
            if hs[0] in handles:
                raise ValueError('duplicate phandle at ' + path)
            handles[hs[0]] = node
    seeds = [n for n in tree.walk() if any(s in n.strings('compatible') for s in
             ('qcom,kgsl-3d0', 'qcom,gmu', 'qcom,gen7-gmu'))]
    if not seeds:
        raise ValueError('cached tree has no supported GPU/GMU source node')
    queue = list(seeds)
    seen, output = set(), []
    while queue:
        node = queue.pop(0)
        path = paths[id(node)]
        if path in seen:
            continue
        seen.add(path)
        refs = []
        for key in node.properties:
            if key not in ('clocks', 'power-domains', 'iommus', 'operating-points-v2') and not key.endswith('-supply'):
                continue
            cells, pos = node.cells(key), 0
            while pos < len(cells):
                handle = cells[pos]
                count_key = {'clocks': '#clock-cells', 'power-domains': '#power-domain-cells',
                             'iommus': '#iommu-cells'}.get(key)
                if handle not in handles or (count_key and count_key not in handles[handle].properties):
                    refs.append(dict(property=key, unresolved_phandle=handle,
                                     unresolved_tail_cells=cells[pos:], reason='provider/arity unavailable; no argument boundaries inferred'))
                    break
                provider = handles[handle]
                count = provider.scalar(count_key) if count_key else 0
                if count < 0 or count > 16 or pos + 1 + count > len(cells):
                    raise ValueError(f'{path}:{key}: truncated provider arguments')
                if key.endswith('-supply') and len(cells) != 1:
                    raise ValueError(f'{path}:{key}: supply must have one phandle')
                refs.append(dict(property=key, provider=paths[id(provider)],
                                 source_arguments=cells[pos + 1:pos + 1 + count]))
                queue.append(provider)
                pos += 1 + count
        output.append(dict(path=path, source_enabled=node.enabled(),
                           properties_hex={k:v.hex() for k,v in sorted(node.properties.items())},
                           references=refs))
        queue.extend(node.children)
    return dict(scope='cached DT source graph only; not runtime policy or hardware authority',
                roots=[paths[id(n)] for n in seeds], nodes=sorted(output, key=lambda n:n['path']),
                resolution_complete=not any('unresolved_phandle' in ref for item in output for ref in item['references']),
                generated_policy=False, hardware_qualification=False, device_operations=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dtb', type=Path, required=True)
    ap.add_argument('--sha256', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    blob = args.dtb.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    if digest != args.sha256:
        ap.error('cached input SHA mismatch')
    result = inspect(blob)
    result['input'] = dict(path=str(args.dtb.resolve()), sha256=digest)
    # Exclusive creation: never replace active artifacts or archived inputs.
    with args.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
