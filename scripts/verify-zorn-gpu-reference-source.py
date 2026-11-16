#!/usr/bin/env python3
"""Read-only correspondence of declared graph references to saved raw FDT cells."""
import argparse
import ast
import builtins
import hashlib
import json
import runpy
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVENANCE = ROOT / 'UniXNU-zorn/scripts/verify-zorn-gpu-source-provenance.py'
PROVENANCE_SHA = '245b28b55bebd95861933216136fef4c2115c55cdd2dc11f6d96befd07491eb4'
ARITIES = {'clocks': '#clock-cells', 'power-domains': '#power-domain-cells',
           'iommus': '#iommu-cells'}
UNKNOWN_REASON = 'provider/arity unavailable; no argument boundaries inferred'
GPU_COMPATIBLES = {'qcom,kgsl-3d0', 'qcom,gmu', 'qcom,gen7-gmu'}


def cells(raw):
    if len(raw) % 4:
        raise ValueError('reference/provider requires aligned 32-bit cells')
    return list(struct.unpack('>' + 'I' * (len(raw) // 4), raw))


def raw_references(actual, paths):
    """Return original-source edges and their cell offsets;never infer missing arity."""
    handles = {}
    for path, node in actual.items():
        aliases = [cells(node.properties[k]) for k in ('phandle', 'linux,phandle')
                   if k in node.properties]
        if not aliases:
            continue
        if any(len(v) != 1 for v in aliases) or any(v != aliases[0] for v in aliases):
            raise ValueError('invalid raw phandle aliases')
        handle = aliases[0][0]
        if handle in (0, 0xffffffff) or handle in handles:
            raise ValueError('ambiguous/reserved raw phandle')
        handles[handle] = path
    result = {}
    for path in paths:
        refs, locations = [], []
        for key, raw in actual[path].properties.items():
            if key not in ARITIES and key != 'operating-points-v2' and not key.endswith('-supply'):
                continue
            values = cells(raw)
            if key.endswith('-supply') and len(values) != 1:
                raise ValueError('supply reference requires exactly one cell')
            pos = 0
            while pos < len(values):
                handle = values[pos]
                provider = handles.get(handle)
                arity_key = ARITIES.get(key)
                props = actual[provider].properties if provider is not None else {}
                if provider is None or (arity_key and arity_key not in props):
                    ref = dict(property=key, unresolved_phandle=handle,
                               unresolved_tail_cells=values[pos:], reason=UNKNOWN_REASON)
                    refs.append(ref)
                    locations.append(dict(property=key, cell_offset=pos, phandle=handle,
                                          unresolved_tail_cells=values[pos:]))
                    break
                count = 0
                if arity_key:
                    arity = cells(props[arity_key])
                    if len(arity) != 1 or arity[0] > 16:
                        raise ValueError('invalid raw provider arity')
                    count = arity[0]
                if pos + 1 + count > len(values):
                    raise ValueError('truncated raw reference arguments')
                args = values[pos + 1:pos + 1 + count]
                refs.append(dict(property=key, provider=provider, source_arguments=args))
                locations.append(dict(property=key, cell_offset=pos, phandle=handle,
                                      provider=provider, argument_cells=args))
                pos += 1 + count
        result[path] = dict(references=refs, cell_locations=locations)
    return result


def source_closure(actual, doc):
    """Bind the declared graph to source roots and children/known-provider closure."""
    roots = [path for path, node in actual.items()
             if GPU_COMPATIBLES.intersection(node.strings('compatible'))]
    if not roots:
        raise ValueError('raw source has no supported GPU/GMU roots')
    if doc.get('roots') != roots:
        raise ValueError('declared roots differ from raw compatible roots')
    # FDT property identity is already validated against the raw tree. Build
    # closure from raw children/references, never from the declared node list.
    queue, seen, references = list(roots), set(), {}
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        item = raw_references(actual, [path])[path]
        references[path] = item
        queue.extend(path.rstrip('/') + '/' + child.name for child in actual[path].children)
        queue.extend(ref['provider'] for ref in item['references'] if 'provider' in ref)
    declared = {row['path'] for row in doc['nodes']}
    if declared != seen:
        raise ValueError('declared node set differs from raw source dependency closure')
    complete = not any('unresolved_tail_cells' in loc
                       for item in references.values() for loc in item['cell_locations'])
    if type(doc.get('resolution_complete')) is not bool or doc['resolution_complete'] != complete:
        raise ValueError('declared resolution flag differs from raw source closure')
    return dict(roots=roots, node_count=len(seen), resolution_complete=complete)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--graph-check-only', action='store_true',
                    help='also verify raw compatible roots and full source dependency closure;no generation')
    ap.add_argument('--source-schema-check', action='store_true',
                    help='after graph verification,invoke only the pinned pure generator input checker')
    for name in ('input', 'dtb'):
        ap.add_argument('--' + name, required=True, type=Path)
        ap.add_argument('--' + name + '-sha256', required=True)
    args = ap.parse_args()
    if args.source_schema_check and not args.graph_check_only:
        ap.error('--source-schema-check requires --graph-check-only')
    result = dict(references_verified=False, graph_verified=False, generated_policy=False, hardware_qualification=False,
                  scope='declared nodes only;raw reference cells,not root/closure/variant or hardware ownership')
    try:
        sha = lambda raw: hashlib.sha256(raw).hexdigest()
        if sha(PROVENANCE.read_bytes()) != PROVENANCE_SHA:
            raise ValueError('pinned provenance implementation changed')
        impl = runpy.run_path(str(PROVENANCE))
        source, raw = args.input.read_bytes(), args.dtb.read_bytes()
        if sha(source) != args.input_sha256 or sha(raw) != args.dtb_sha256:
            raise ValueError('separate JSON/raw input SHA mismatch')
        if len(source) > 16 * 1024 * 1024:
            raise ValueError('source JSON reader bound')
        doc = json.loads(source, object_pairs_hook=impl['unique'])
        if isinstance(doc, dict) and 'input' in doc:
            if not isinstance(doc['input'], dict) or doc['input'].get('sha256') != sha(raw):
                raise ValueError('declared original SHA mismatch')
        if sha(impl['PARSER'].read_bytes()) != impl['PARSER_SHA']:
            raise ValueError('pinned raw parser changed')
        sys.path.insert(0, str(ROOT / 'UniXNU/scripts'))
        from unixnu.devicetree import read_fdt, Error
        try:
            actual, count = impl['verify'](doc, read_fdt(raw))
            paths = [row['path'] for row in doc['nodes']]
            expected = raw_references(actual, paths)
        except (Error, UnicodeError, struct.error) as exc:
            raise ValueError('invalid raw FDT: ' + str(exc)) from exc
        for row in doc['nodes']:
            # JSON canonical comparison also prevents bool masquerading as integer.
            if json.dumps(row.get('references'), sort_keys=True) != json.dumps(expected[row['path']]['references'], sort_keys=True):
                raise ValueError('declared references differ from raw cells: ' + row['path'])
        if args.graph_check_only:
            try:
                closure = source_closure(actual, doc)
            except (Error, UnicodeError, struct.error) as exc:
                raise ValueError('invalid raw closure: ' + str(exc)) from exc
            result.update(graph_verified=True, raw_source_closure=closure,
                          scope='raw GPU/GMU compatible roots and source dependency closure;no variant choice or hardware ownership')
        result.update(references_verified=True, declared_nodes_verified=count,
                      input_json_sha256=sha(source), raw_dtb_sha256=sha(raw),
                      resolution_complete=not any('unresolved_tail_cells' in loc
                          for item in expected.values() for loc in item['cell_locations']),
                      raw_source_references=expected)
        if args.source_schema_check:
            # No prepare/module execution:extract only the immutable pure entry.
            result['source_schema_compatible'] = False
            checker = impl['CHECKER']
            if sha(checker.read_bytes()) != impl['CHECKER_SHA']:
                raise ValueError('pinned pure generator checker changed')
            module = ast.parse(checker.read_text())
            fn = next(n for n in module.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'validate_source_nodes')
            if fn.decorator_list or fn.args.defaults:
                raise ValueError('unexpected pure checker entry metadata')
            env = {'__builtins__': {k: getattr(builtins, k) for k in
                   ['ValueError', 'isinstance', 'dict', 'str', 'bytes', 'int', 'set', 'len', 'range']}}
            exec(compile(ast.Module(body=[fn], type_ignores=[]), 'pinned-source-schema', 'exec'), env)
            result['source_schema'] = env['validate_source_nodes'](
                {path: node.properties for path, node in actual.items()})
            result['source_schema_compatible'] = True
    except (ValueError, TypeError, OSError, RecursionError, StopIteration) as exc:
        result['error'] = str(exc)
    print(json.dumps(result))
    return 0 if result['references_verified'] and result.get('source_schema_compatible', True) else 2


if __name__ == '__main__':
    raise SystemExit(main())
