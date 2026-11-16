"""IOSurface probe224: same strict transport, native lifecycle and diagnostic-loss gates."""
from inspect_ios26_gpu_progress223 import inspect_progress as inspect_base

PROBE_TAG = '19a4a5e9872542ebab85c20db1e20129'

def inspect_progress(data, tag, program_tag):
    if tag != PROBE_TAG or program_tag != PROBE_TAG:
        raise ValueError('exact224 boot and signed IOSurface probe identity required')
    result = inspect_base(data, tag, program_tag)
    result['IOSurface_probe_selected'] = True
    result['physical_presentation_proven'] = False
    result['full_GPU_qualification'] = False
    result['probe_scope'] = ('Signed224 ordinary Metal IOSurface texture; phase11 requires independent '
        'getBytes/shared-memory equality and full4096-byte RGBA oracle. Physical presentation remains separate.')
    return result
