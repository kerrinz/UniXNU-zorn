"""Source-defined CDC-first progress frames. Never a full GPU verdict."""
import re
from inspect_ios26_gpu_metal194 import inspect_metal


def inspect_progress(data, tag, program_tag):
    if not re.fullmatch(r'[0-9a-f]{32}', tag) or not re.fullmatch(r'[0-9a-f]{32}', program_tag):
        raise ValueError('invalid expected identity')
    if len(data) > 64512:
        raise ValueError('progress stream exceeds source bound')
    prefix = b'K80 GPU PROGRESS ' + tag.encode() + b' '
    frames, tail = [], b''
    for line in data.splitlines(keepends=True):
        if not line.endswith(b'\r\n'):
            if tail or not (line.startswith(prefix) or prefix.startswith(line)):
                raise ValueError('invalid partial frame prefix')
            tail = line
            continue
        if tail or not line.startswith(prefix) or len(line) > 3072 or len(frames) >= 21:
            raise ValueError('invalid frame envelope/count')
        fields = {}
        for token in line[len(prefix):-2].split(b','):
            key, sep, value = token.partition(b'=')
            if not sep or key in fields:
                raise ValueError('missing/duplicate field')
            fields[key] = value
        required = {b'seq', b'state', b'smr', b'spawn', b'snap', b'ap', b'au', b'at', b'ms', b'mp', b'mt'}
        count_text = fields.get(b'ms', b'').split(b'/')[0]
        if not re.fullmatch(rb'[0-4]', count_text):
            raise ValueError('session count differs')
        count = int(count_text)
        if set(fields) != required | {f'mh{i}'.encode() for i in range(count)}:
            raise ValueError('unexpected/missing progress fields')
        values = {}
        for key in (b'seq', b'state', b'smr', b'spawn', b'snap'):
            if not re.fullmatch(rb'0|[1-9][0-9]*', fields[key]):
                raise ValueError('invalid progress number')
            values[key.decode()] = int(fields[key])
        seq, state, smr, spawn, snap = (values[k] for k in ('seq', 'state', 'smr', 'spawn', 'snap'))
        if seq != len(frames) or state > 4 or smr > 88 or spawn > 0xffffffff or snap > 1:
            raise ValueError('progress bounds/sequence differ')
        if (state != 3 and smr) or (state == 4) != bool(spawn):
            raise ValueError('worker result/state differs')
        if not frames and (state or smr or spawn):
            raise ValueError('initial frame must precede GPU scheduling')
        if frames:
            old = frames[-1]['state']
            if state < old or (old == 3 and state != 3) or (old == 4 and state != 4):
                raise ValueError('worker state regressed')
        if not re.fullmatch(rb'[0-9a-f]{16}', fields[b'ap']):
            raise ValueError('invalid publication syntax')
        publication = int(fields[b'ap'], 16)
        if publication and publication >> 32 != 1:
            raise ValueError('invalid publication value')
        app = inspect_metal(fields[b'au'], fields[b'at'], fields[b'ms'],
                            [fields[f'mh{i}'.encode()] for i in range(count)],
                            program_tag, fields[b'mp'], fields[b'mt'])
        if not snap and (any(app['native'].values()) or any(app['program_identity'].values()) or
                         fields[b'at'] or fields[b'mt'] or count or fields[b'ms'] != b'0/0/0'):
            raise ValueError('failed snapshot contains observation')
        frames.append(dict(values, publication=publication,
                           published=publication == 0x100000000,
                           application=app if snap else None))
    return dict(transport_frames_valid=bool(frames), frames=frames, frame_count=len(frames),
                partial_tail_bytes=len(tail), last_application=next(
                    (f['application'] for f in reversed(frames) if f['application'] is not None), None),
                initial_frame_before_GPU=bool(frames),
                worker_entered_observed=any(f['state'] in (2, 3) for f in frames),
                deferred_call_returned=any(f['state'] == 3 for f in frames),
                full_GPU_qualification=False, known_image_complete=False,
                scope='Partial progress and actual application reports; no complete GPU-register/known-image envelope.')
