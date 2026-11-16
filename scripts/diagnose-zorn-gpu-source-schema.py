#!/usr/bin/env python3
"""Describe source schema mismatches without converting or emitting policy."""
import argparse
import ast
import builtins
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
READER = Path(__file__).with_name('read-zorn-gpu-power-source.py')
READER_SHA = '8e15bbef1f754f2808f5ffeeff76bdd0a707f5d8f77a136cec621f3d7929361b'
PURE = ROOT / 'out/zorn/gpu-votes-source-identity-20261103/candidate.py'
PURE_SHA = '7ad80015d140f5ed62bd10ee54923743041fc7d3e769eeb1ce6b4790705e3923'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def pure_contract(nodes):
    if sha(PURE.read_bytes()) != PURE_SHA:
        raise ValueError('pinned pure generator source changed')
    module = ast.parse(PURE.read_text())
    fn = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_source_nodes')
    if fn.decorator_list or fn.args.defaults:
        raise ValueError('unexpected pure checker metadata')
    # Extract the actual fixed consumer paths/counts,not inferred board paths.
    loop = next(n for n in fn.body if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)
                and [x.id for x in n.target.elts] == ['kind', 'path', 'limit'])
    paths = ast.literal_eval(loop.iter)
    env = {'__builtins__': {k: getattr(builtins, k) for k in
           ['ValueError', 'isinstance', 'dict', 'str', 'bytes', 'int', 'set', 'len', 'range']}}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'pinned-pure-source-only', 'exec'), env)
    result = dict(compatible=False, source_sha256=PURE_SHA,
                  function_AST_sha256=sha(ast.dump(fn, include_attributes=False).encode()))
    try:
        result['shape'] = env['validate_source_nodes'](nodes)
        result['compatible'] = True
    except ValueError as exc:
        result['error'] = str(exc)
    expected = [dict(kind=kind, node=path, table=path+'/opp-table', count_limit=limit,
                     binding_property='operating-points-v2',
                     entry_properties={'opp-hz': dict(bytes=8, required=True),
                                       'opp-level': dict(bytes=4, required=True),
                                       'qcom,opp-acd-level': dict(bytes=4, required=False),
                                       **({'opp-peak-kBps': dict(bytes=4, required=True)} if kind=='gpu' else {})})
                for kind, path, limit in paths]
    return result, expected


def property_record(props, key):
    raw = props.get(key)
    return dict(property=key, available=raw is not None, bytes=len(raw) if raw is not None else None,
                raw_hex=raw.hex() if raw is not None else None)


def describe(root, reader):
    actual = reader['helper'].index(root)
    pure, expected = pure_contract({p: n.properties for p, n in actual.items()})
    tables = reader['read'](root)
    diagnostics = []
    for contract in expected:
        kind = contract['kind']
        compatibles = {'qcom,kgsl-3d0'} if kind == 'gpu' else {'qcom,gen7-gmu'}
        roots = [(p, n) for p, n in actual.items() if compatibles.intersection(n.strings('compatible'))]
        for path, node in roots:
            diagnostics.append(dict(kind=kind, issue='fixed_path_contract', source_path=path,
                                    expected_path=contract['node'], same_path=path==contract['node'],
                                    expected_node_present=contract['node'] in actual,
                                    expected_table_present=contract['table'] in actual,
                                    source_binding=property_record(node.properties, contract['binding_property']),
                                    expected_binding_property=contract['binding_property'],
                                    reason='actual fixed consumer paths are retained;no alternate path selected'))
    for table in tables['gpu_tables']:
        path = table['source_node']; node = actual[path]
        diagnostics.append(dict(kind='gpu', issue='multi_table_metadata', source_path=path,
                                source_enabled=table['source_enabled'], selected=False,
                                metadata=[property_record(node.properties, k) for k in
                                          ['qcom,speed-bin', 'qcom,sku-codes', 'qcom,initial-pwrlevel']],
                                reason='unselected raw multi-table source;absence is unknown,not default bin0'))
        for entry in table['entries']:
            path = entry['source_node']; props = actual[path].properties
            expected_fields = expected[0]['entry_properties']
            diagnostics.append(dict(kind='gpu', issue='different_entry_schema', source_path=path,
                                    source_enabled=entry['source_enabled'],
                                    source_properties=[property_record(props,k) for k in props],
                                    expected_properties=[dict(property=k, **v, present_here=k in props)
                                                         for k,v in expected_fields.items()],
                                    unclassified_properties=[k for k in props if k not in entry['fields']],
                                    reason='qcom pwrlevel properties are not OPPv2 properties;no alias,width conversion or value derivation'))
    for table in tables['gmu_tables']:
        path=table['source_node'];props=actual[path].properties
        diagnostics.append(dict(kind='gmu',issue='cell_pairs_not_opp_children',source_path=path,
                                source_property=property_record(props,table['property']),
                                cell_bytes=table['cell_bytes'],pair_bytes=table['pair_bytes'],
                                pairs=table['pairs'],selected=False,
                                expected_table=expected[1]['table'],
                                reason='raw GMU cell pairs retained;no frequency/voltage reinterpretation or OPP construction'))
    return dict(pure_source_check=pure, expected_source_contract=expected, diagnostics=diagnostics,
                prepare_allowed=False, generated_policy=False, hardware_qualification=False,
                scope='source schema diagnosis only;no conversion,selection or emission')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dtb',type=Path,required=True);parser.add_argument('--sha256',required=True)
    parser.add_argument('--graph-json',type=Path,required=True);parser.add_argument('--graph-sha256',required=True)
    args=parser.parse_args();result=dict(diagnostics_complete=False,prepare_allowed=False,generated_policy=False,hardware_qualification=False)
    try:
        if sha(READER.read_bytes())!=READER_SHA:raise ValueError('pinned source reader changed')
        reader=runpy.run_path(str(READER))
        from unixnu.devicetree import Error as SourceError
        raw=args.dtb.read_bytes()
        if sha(raw)!=args.sha256:raise ValueError('raw source SHA mismatch')
        try:
            root=reader['helper'].read_fdt(raw)
            provenance,_=reader['verified_graph'](root,sha(raw),args.graph_json.read_bytes(),args.graph_sha256)
            result.update(describe(root,reader),source_provenance=provenance,diagnostics_complete=True)
        except (SourceError,UnicodeError) as exc:raise ValueError('invalid raw source: '+str(exc)) from exc
    except (ValueError,TypeError,OSError,StopIteration) as exc:result['error']=str(exc)
    print(json.dumps(result,indent=2))
    return 0 if result.get('pure_source_check',{}).get('compatible') else 2


if __name__=='__main__':raise SystemExit(main())
