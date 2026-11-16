#!/usr/bin/env python3
"""Compare raw power-source bytes across explicitly listed,unselected base inputs."""
import argparse
import hashlib
import json
import runpy
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
READER = Path(__file__).with_name('read-zorn-gpu-power-source.py')
READER_SHA = '8e15bbef1f754f2808f5ffeeff76bdd0a707f5d8f77a136cec621f3d7929361b'
DIAGNOSTICS = Path(__file__).with_name('diagnose-zorn-gpu-source-schema.py')
DIAGNOSTICS_SHA = '5c6ebb26356f2f77c5b2f652b8da995d1a48b90a371c8b1165a3281d5dd45126'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def compare(snapshots):
    """Raw equality only;missing and zero-length properties remain distinct."""
    paths = sorted(set().union(*(set(s['nodes']) for s in snapshots)))
    rows, same, different = [], 0, 0
    for path in paths:
        keys = sorted(set().union(*(set(s['nodes'].get(path, {})) for s in snapshots)))
        properties = []
        for key in keys:
            values = []
            for source in snapshots:
                props = source['nodes'].get(path, {})
                raw = props.get(key)
                values.append(dict(source_id=source['id'], available=raw is not None,
                                   raw_hex=raw.hex() if raw is not None else None,
                                   bytes=len(raw) if raw is not None else None))
            equal = all(v['available'] for v in values) and len({v['raw_hex'] for v in values}) == 1
            same += int(equal); different += int(not equal)
            properties.append(dict(property=key, same_bytes_in_all_sources=equal, values=values))
        rows.append(dict(source_node=path, present_in=[s['id'] for s in snapshots if path in s['nodes']], properties=properties))
    return dict(source_nodes=rows, same_property_bytes_count=same, different_or_missing_property_count=different)


def inspect_inputs(manifest, schema_diagnostics=False):
    if not isinstance(manifest, dict) or set(manifest) != {'sources'}:
        raise ValueError('manifest requires only explicit sources')
    entries = manifest['sources']
    if not isinstance(entries, list) or not 2 <= len(entries) <= 16:
        raise ValueError('explicit source count must be2..16')
    if sha(READER.read_bytes()) != READER_SHA:
        raise ValueError('pinned source reader changed')
    reader = runpy.run_path(str(READER))
    diagnose = None
    if schema_diagnostics:
        if sha(DIAGNOSTICS.read_bytes()) != DIAGNOSTICS_SHA:
            raise ValueError('pinned source diagnostics changed')
        diagnose = runpy.run_path(str(DIAGNOSTICS))['describe']
    identities, snapshots, ids, raw_ids = [], [], set(), set()
    required = {'id', 'dtb', 'dtb_sha256', 'graph_json', 'graph_sha256'}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != required or any(not isinstance(v, str) or not v for v in entry.values()):
            raise ValueError('source requires exact id/path/independent SHA fields')
        label = entry['id']
        if label in ids:
            raise ValueError('duplicate explicit source id')
        ids.add(label)
        raw_path, graph_path = Path(entry['dtb']), Path(entry['graph_json'])
        if not raw_path.is_absolute() or not graph_path.is_absolute():
            raise ValueError('source paths must be absolute')
        raw, source = raw_path.read_bytes(), graph_path.read_bytes()
        digest = sha(raw)
        if digest != entry['dtb_sha256']:
            raise ValueError('raw source SHA mismatch')
        if digest in raw_ids:
            raise ValueError('duplicate raw source identity;not distinct base inputs')
        raw_ids.add(digest)
        from unixnu.devicetree import Error as SourceError
        try:
            root = reader['helper'].read_fdt(raw)
            provenance, _ = reader['verified_graph'](root, digest, source, entry['graph_sha256'])
            tables = reader['read'](root)
        except (SourceError, UnicodeError, struct.error) as exc:
            raise ValueError('invalid raw source: ' + str(exc)) from exc
        actual = reader['helper'].index(root)
        paths = {item['source_node'] for item in tables['gpu_tables'] + tables['gmu_tables']}
        for table in tables['gpu_tables']:
            paths.update(item['source_node'] for item in table['entries'])
            container = table['source_node'].rsplit('/', 1)[0]
            paths.update((container, container.rsplit('/', 1)[0]))
        snapshots.append(dict(id=label, nodes={path: actual[path].properties for path in sorted(paths)}))
        identity = dict(id=label, dtb=str(raw_path), raw_dtb_sha256=digest,
                               graph_json=str(graph_path), graph_json_sha256=entry['graph_sha256'],
                               provenance=provenance, gpu_table_count=len(tables['gpu_tables']),
                               gmu_source_count=len(tables['gmu_tables']))
        if diagnose is not None:
            # Pass the same verified raw tree,not serialized caller diagnostics.
            identity['schema_diagnostics'] = diagnose(root, reader)
        identities.append(identity)
    result = dict(sources=identities, comparison=compare(snapshots), source_identities_preserved=True,
                unknown_properties='retained as raw bytes;no runtime interpretation',
                variant_selected=False, policy_derived=False, generated_policy=False,
                hardware_qualification=False, scope='raw GPU/GMU source equality/differences only;not policy compatibility')
    if schema_diagnostics:
        result['source_schemas_compatible'] = all(s['schema_diagnostics']['pure_source_check']['compatible'] for s in identities)
        result['prepare_allowed'] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--schema-diagnostics', action='store_true',
                        help='attach pinned pure source-schema diagnostics;incompatibility returns2,no emission')
    args = parser.parse_args()
    try:
        raw = args.inputs.read_bytes()
        if len(raw) > 1024 * 1024 or sha(raw) != args.sha256:
            raise ValueError('input manifest bound/SHA mismatch')
        result = inspect_inputs(json.loads(raw, object_pairs_hook=unique), args.schema_diagnostics)
    except (ValueError, TypeError, OSError, StopIteration) as exc:
        print(json.dumps(dict(compared=False, error=str(exc), generated_policy=False, hardware_qualification=False)))
        return 2
    print(json.dumps(dict(compared=True, **result), indent=2))
    return 0 if result.get('source_schemas_compatible', True) else 2


if __name__ == '__main__':
    raise SystemExit(main())
