"""Decode early launch and independent CPU samples without a probe/desktop verdict."""
import re
from inspect_ios26_gpu_journal248 import inspect_progress as inspect_previous
from inspect_ios26_gpu_progress236 import MAGIC, WIRE_LIMIT


def inspect_progress(data, tag, program_tag):
    if len(data) > WIRE_LIMIT:
        raise ValueError('early252 wire budget exceeded')
    at = data.find(MAGIC)
    normal, terminal = (data, b'') if at < 0 else (data[:at], data[at:])
    output, records = [], []
    pattern = (rb'([0-9a-f]{1,8})/([0-9a-f]{1,16})/([01])/'
               rb'([0-9a-f]{1,2})/(0|[1-9][0-9]?)/([0-9a-f]{1,2})/([0-9a-f]{1,2})')
    for line in normal.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            output.append(line)
            continue
        if len(line) > 3072 or line.count(b',ep=') != 1:
            raise ValueError('early252 frame envelope differs')
        head, _, rest = line.partition(b',ep=')
        raw, sep, tail = rest.partition(b',jl=')
        match = re.fullmatch(pattern, raw)
        if not sep or not match:
            raise ValueError('early252 sample syntax differs')
        bases = (16,16,10,16,10,16,16)
        keys = ('flags','ready_ticks','cpu_done','cpu_mask','cpu_online','user_mask','system_mask')
        r = dict(zip(keys, (int(v, b) for v, b in zip(match.groups(), bases))))
        if (r['flags'] & ~0x8000003f or r['flags'] & 0x3d != 0x3d or
                not r['ready_ticks'] or r['cpu_online'] > 8 or
                (r['user_mask'] | r['system_mask']) & ~r['cpu_mask'] or
                (not r['cpu_done'] and any(r[k] for k in keys[3:]))):
            raise ValueError('early252 sample bounds differ')
        if records:
            old = records[-1]
            if (r['flags'] & old['flags'] != old['flags'] or
                    r['ready_ticks'] != old['ready_ticks'] or
                    r['cpu_done'] < old['cpu_done'] or
                    (old['cpu_done'] and any(r[k] != old[k] for k in keys[2:]))):
                raise ValueError('early252 immutable publication regressed')
        records.append(r)
        output.append(head + b',jl=' + tail)
    result = inspect_previous(b''.join(output) + terminal, tag, program_tag)
    if len(records) != result['frame_count']:
        raise ValueError('early252 frame count differs')
    result['early252'] = records
    result['last_early252'] = records[-1] if records else None
    result['early_launch_observed252'] = bool(records and not records[-1]['flags'] & 0x80000000)
    last = records[-1] if records else None
    result['CPU_samples_valid252'] = bool(last and last['cpu_done'] and last['cpu_mask'] == 255 and last['cpu_online'] == 8)
    # Attribution needs the strict backboardd successful-write observer's actual
    # task identity to agree with the native-session identity. Empty diagnostics
    # cannot prove which process used the driver.
    journal = result['journal248']
    app = result.get('last_application')
    identity = app['program_identity'] if app else None
    j = journal['last']
    result['ordinary_client_identity_correlated252'] = bool(
        j and identity and identity['unique'] and
        (j['unique'], j['pid']) == (identity['unique'], identity['pid']))
    result['ordinary_journal_prefix_intact252'] = bool(
        j and not j['gaps'] and not j['pending'] and
        j['seen_bytes'] == j['reserved'] == j['published'] == journal['received_bytes'] and
        not journal['pending_checksum_prefixes'])
    result['ordinary_GPU_desktop_qualified252'] = False
    result['full_GPU_qualification'] = False
    result['scope252'] = 'Source-defined early launch,actual CPU sample metadata and bounded ordinary-client diagnostics;discovery/render/present/physical acceptance separate'
    return result
