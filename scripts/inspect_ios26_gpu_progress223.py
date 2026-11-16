"""Control trial: mapping observation calls are unselected, not successful."""
from inspect_ios26_gpu_progress222 import inspect_progress as inspect_base


def inspect_progress(data, tag, program_tag):
    result = inspect_base(data, tag, program_tag)
    if any(f['callback']['point'] for f in result['frames']):
        raise ValueError('mapping observation appeared in a no-map-wait control')
    result['mapping_waits_unselected_control'] = True
    result['callback_scope'] = ('Original IOUserClient mapClientMemory64 restored byte-for-byte. '
        'No four-point mapping gates selected. Source timing control of222 image success, '
        'not a proven PAC fix or full GPU qualification.')
    return result
