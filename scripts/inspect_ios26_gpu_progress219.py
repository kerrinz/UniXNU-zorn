"""Interpret client completion and return boundaries separately from GPU success."""

from inspect_ios26_gpu_progress217 import inspect_progress as inspect_base


def inspect_progress(data, tag, program_tag):
    result = inspect_base(data, tag, program_tag)
    for key in (
        'callback_dispatch_return_observed', 'callback_finish_enter_observed',
        'callback_operation_release_return_observed', 'callback_finish_return_observed',
        'callback_owner_return_observed',
    ):
        result.pop(key, None)
    points = [frame['callback']['point'] for frame in result['frames']]
    for threshold, name in enumerate((
        'done_enter', 'completion_event_return', 'serial_unlock_return',
        'run_return', 'action_return', 'base_external_return',
    ), 1):
        result['callback_' + name + '_observed'] = any(p >= threshold for p in points)
    result['callback_scope'] = (
        'First observed owned BOmap selector3 only. Point1=done entry with actual '
        'owner result or early refusal;2=completion observation event returned;'
        '3=client serial unlock returned;4=run returned to action;'
        '5=action returned to legacy base dispatcher;6=base externalMethod returned '
        'to subclass. Frame acknowledgment confirms delivery of that source point. '
        'A completion observation event is not the whole user-client API return.')
    result['callback_return_scope'] = (
        'Actual IOReturn at each client completion/return source point; unknown is '
        'explicit. Neither a source point nor its acknowledgment implies native '
        'success, subsequent IPC return, GPU completion or Metal rendering.')
    return result
