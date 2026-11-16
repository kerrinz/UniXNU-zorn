"""Same bounded source-format protocol with exact public panic macro suffix support."""
from inspect_ios26_gpu_progress232 import inspect_progress as inspect_previous, FORMATS


def inspect_progress(data, run_id, probe_run_id):
    result = inspect_previous(data, run_id, probe_run_id)
    terminal = result.pop('terminal232')
    terminal['format_matching'] = ('canonical literal, or literal followed only by the exact '
                                   'static panic_call.h suffix @%s:%d; ambiguous matches stay unknown')
    terminal['format_arguments_inspected'] = False
    terminal['exact_callsite_proven'] = False
    result['terminal233'] = terminal
    return result
