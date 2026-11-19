#!/usr/bin/env python3
"""Extend K80's existing HLOS graph with the stock display register bus."""

import argparse
import hashlib
import json
from pathlib import Path
import re


PROVIDERS = ('cnoc_main', 'cnoc_cfg')
EXTRA_BCMS = ('CN0', 'CN1')


def entries(source, declaration):
    matches = re.findall(rf'^static {declaration}\s+(\w+)\s*=\s*\{{(.*?)^\}};', source, re.M | re.S)
    return dict(matches)


def body(source, name):
    return re.search(rf'(?<=\b){name}\[\]\s*=\s*\{{(.*?)^\}};', source, re.M | re.S)[1]


def integer(source, name, default=None):
    match = re.search(rf'\.{name}\s*=\s*(0x[\da-fA-F]+|\d+)\s*,', source)
    if not match and default is None:
        raise ValueError(f'Missing numeric field {name}')
    return int(match[1], 0) if match else default


def field_list(source, name):
    match = re.search(rf'\.{name}\s*=\s*\{{(.*?)\}}', source, re.S)
    return re.findall(r'\w+', match[1]) if match else []


def insert_before(source, marker, added):
    if source.count(marker) != 1:
        raise ValueError(f'Unexpected retained graph marker {marker}')
    return source.replace(marker, added + marker)


def extend(retained, stock, ids, topology):
    known = re.findall(r'\{"(\w+)",(\d+)u,(\d+)u,', body(retained, 'nodes'))
    old_nodes = {int(id): (name, int(provider)) for name, id, provider in known}
    if len(known) != len(old_nodes) or len(known) != 19 or max(provider for _, provider in old_nodes.values()) != 1:
        raise ValueError('Expected the existing two-provider K80 GPU graph')

    node_source = entries(stock, r'struct qcom_icc_node')
    all_nodes = dict(old_nodes)
    links, added = [], []
    indexed = {name: index for index, (name, _, _) in enumerate(known)}
    for provider, name in enumerate(PROVIDERS, start=2):
        symbols = re.findall(r'\[(\w+)\]\s*=\s*&(\w+)', body(stock, name + '_nodes'))
        projected = topology['cnoc_provider_nodes'][name]
        if symbols != [(row['id'], row['symbol']) for row in projected]:
            raise ValueError(f'{name} member evidence and source differ')
        for node_id, symbol in symbols:
            description = node_source[symbol]
            if (ids[node_id] in all_nodes or symbol in indexed or
                    re.search(r'\.(?:qosbox|clk|clock|bw_scale|toggle_clock)\s*=', description)):
                raise ValueError(f'CNOC member requires separate handling {symbol}')
            if not re.search(rf'\.id\s*=\s*{node_id}\s*,', description):
                raise ValueError(f'CNOC member ID differs for {symbol}')
            node_links = [ids[link] for link in field_list(description, 'links')]
            if len(node_links) != integer(description, 'num_links'):
                raise ValueError(f'CNOC link count differs for {symbol}')
            link_name = 'display_links_' + symbol
            links.append(f'constexpr uint32_t {link_name}[]={{' +
                         ','.join(f'{id}u' for id in (node_links or [0])) + '};\n')
            channels, width = (integer(description, field) for field in ('channels', 'buswidth'))
            added.append(f' {{"{symbol}",{ids[node_id]}u,{provider}u,{channels}u,{width}u,'
                         f'0u,0u,false,false,false,{link_name},{len(node_links)}}},\n')
            indexed[symbol] = len(all_nodes)
            all_nodes[ids[node_id]] = symbol, provider

    old_bcms = re.findall(r'\{"(\w+)",(\d+)u,', body(retained, 'bcms'))
    if [name for name, _ in old_bcms] != ['SH0', 'SH1', 'ACV', 'MC0']:
        raise ValueError('Retained GPU and TBU BCM projection differs')
    masks = [1 << int(provider) for _, provider in old_bcms]
    source_bcms = entries(stock, r'struct qcom_icc_bcm')
    membership, groups = [], []
    largest_group = 0
    for name in EXTRA_BCMS:
        symbol = 'bcm_' + name.lower()
        description = source_bcms[symbol]
        voter = re.search(r'\.voter_idx\s*=\s*(\w+)\s*,', description)
        if not voter or voter[1] not in ('0', 'VOTER_IDX_HLOS'):
            raise ValueError(f'{name} is outside the original HLOS voter')
        members = field_list(description, 'nodes')
        if (members != [row['symbol'] for row in topology['bcm_members'][name]] or
                len(set(members)) != integer(description, 'num_nodes')):
            raise ValueError(f'{name} member evidence and source differ')
        mask = 0
        for member in members:
            mask |= 1 << next(provider for node, provider in all_nodes.values() if node == member)
        for offset, provider in enumerate(PROVIDERS, start=2):
            declared = re.search(rf'&{symbol}\b', body(stock, provider + '_bcms')) is not None
            if declared != bool(mask & (1 << offset)):
                raise ValueError(f'{name} provider registration differs')
        masks.append(mask)
        largest_group = max(largest_group, len(members))
        membership.append(f'constexpr size_t display_members_{name}[]={{' +
                          ','.join(f'{indexed[member]}u' for member in members) + '};\n')
        enable = integer(description, 'enable_mask', 0)
        perf = integer(description, 'perf_mode_mask', 0)
        scale = integer(description, 'vote_scale', 0)
        keepalive = str('.keepalive = true' in description).lower()
        early = str('.keepalive_early = true' in description).lower()
        first_provider = (mask & -mask).bit_length() - 1
        groups.append(f' {{"{name}",{first_provider}u,{enable}u,{perf}u,{scale}u,{keepalive},{early},false,'
                      f'display_members_{name},{len(members)}}},\n')

    path = [row['id'] for row in topology['display_path']]
    if len(path) != 6 or not all(id in all_nodes for id in path):
        raise ValueError('Display route is outside the canonical HLOS domain')
    retained = insert_before(retained, 'constexpr Node nodes[]={', ''.join(links))
    retained = insert_before(retained, '};\nconstexpr size_t bcm_nodes_0[]=', ''.join(added))
    retained = insert_before(retained, 'constexpr Bcm bcms[]={', ''.join(membership))
    retained = insert_before(retained, '};\nconstexpr uint32_t gpu_path[]=', ''.join(groups))
    old_counts = 'constexpr size_t node_count=19,bcm_count=4,path_count=4;'
    if retained.count(old_counts) != 1:
        raise ValueError('Retained graph size is unavailable')
    return retained.replace(old_counts, (
        'constexpr uint32_t display_path[]={' + ','.join(f'{id}u' for id in path) + '};\n'
        'constexpr uint32_t bcm_provider_masks[]={' + ','.join(f'{mask}u' for mask in masks) + '};\n'
        f'constexpr size_t provider_count={2 + len(PROVIDERS)},node_count={len(all_nodes)},'
        f'bcm_count={len(masks)},max_bcm_members={largest_group},path_count=4;\n'
        f'constexpr size_t display_path_count={len(path)},gpu_startup_bcm_count={len(old_bcms)};'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('retained', 'stock', 'bindings', 'topology', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    topology = json.loads(args.topology.read_text())
    for path in (args.retained, args.stock, args.bindings):
        expected, = [row for row in topology['input_sources'] if Path(row['path']) == path.resolve()]
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected['sha256']:
            raise ValueError(f'Exact input hash differs for {path}')
    ids = {key: int(value) for key, value in re.findall(
        r'^#define\s+(\w+)\s+(\d+)\s*$', args.bindings.read_text(), re.M)}
    graph = extend(args.retained.read_text(), args.stock.read_text(), ids, topology)
    with args.output.open('x') as output:
        output.write(graph)


if __name__ == '__main__':
    main()
