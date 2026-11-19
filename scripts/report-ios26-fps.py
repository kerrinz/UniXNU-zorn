#!/usr/bin/env python3
"""Summarize measured rates in a verified iOS 26 serial analysis archive."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def metal_completions(timing):
    if not timing or timing.get('complete') is not True:
        return None
    first, last = timing['reports']
    start, end = first['uptime_us'], last['uptime_us']
    before = first['values']['commit-to-complete']['count']
    after = last['values']['commit-to-complete']['count']
    if not 0 < start < end or not 0 <= before <= after:
        raise ValueError('Metal completion counter or clock regressed')
    return dict(start_uptime_us=start, end_uptime_us=end, completed=after - before,
                completions_per_second=(after - before) * 1_000_000 / (end - start))


def gop_copies(windows):
    measured = []
    for window in windows:
        cost = window.get('present_cost_delta')
        if cost is None:
            continue
        start, end = cost['start_counter_uptime_ms'], cost['end_counter_uptime_ms']
        if (not 0 < start < end or end - start != cost['elapsed_ms']
                or cost['copied_frames'] < 0 or cost['show_us'] < 0
                or (measured and start < measured[-1]['end_counter_uptime_ms'])):
            raise ValueError('Invalid or overlapping GOP copy counter window')
        measured.append(cost)
    if not measured:
        return None
    elapsed = sum(window['elapsed_ms'] for window in measured)
    copies = sum(window['copied_frames'] for window in measured)
    show_us = sum(window['show_us'] for window in measured)
    rates = [window['copied_frames'] * 1000 / window['elapsed_ms'] for window in measured]
    return dict(windows=len(measured), missing_windows=len(windows) - len(measured),
                measured_seconds=elapsed / 1000, copied_frames=copies, copies_per_second=copies * 1000 / elapsed,
                window_copies_per_second_min=min(rates), window_copies_per_second_max=max(rates),
                show_mean_ms=show_us / (1000 * copies) if copies else None)


def latency_percentiles(values):
    if not values:
        return None
    ordered = sorted(values)
    return {**{f'p{p}_us': ordered[(p * len(ordered) + 99) // 100 - 1] for p in (50, 95, 99)},
            'max_us': ordered[-1], 'samples': len(ordered)}


def compositor_scanout(stat):
    if not stat:
        return None
    result = dict(result=stat['result'], attempts=stat['attempts'], refused=stat['refused'],
                  seeded_copies=stat['seeded_copies'], cap_reached=bool(stat['cap_reached']),
                  confirmed_compositor_swaps_per_second=None)
    if 'writer_gate' in stat:
        result['writer_gate'] = stat['writer_gate']
    if not stat['start_us']:
        return result
    frames = [row for row in stat['frames'] if row['completed_us'] <= stat['stop_us']]
    elapsed = stat['stop_us'] - stat['start_us']
    if stat['result'] == 'restored' and not stat['cap_reached']:
        result['confirmed_compositor_swaps_per_second'] = len(frames) * 1_000_000 / elapsed
    result.update(window_us=elapsed, completed_in_window=len(frames),
                  completed_after_deadline=stat['completed'] - len(frames),
                  gap=latency_percentiles([b['completed_us'] - a['completed_us']
                                           for a, b in zip(frames, frames[1:])]),
                  queue_to_DSI=latency_percentiles([r['completed_us'] - r['queued_us'] for r in frames]),
                  program_to_DSI=latency_percentiles([r['program_to_DSI_us'] for r in frames
                                                     if r['program_to_DSI_us'] is not None]))
    if 'sampled_RGB_grid_points' in stat:
        changed = sum(frame['sampled_RGB_changed'] for frame in frames)
        valid_rate = result['confirmed_compositor_swaps_per_second'] is not None
        result.update(sampled_RGB_grid_points=stat['sampled_RGB_grid_points'],
                      confirmed_swaps_with_changed_RGB_samples=changed,
                      confirmed_swaps_with_no_sampled_RGB_change=len(frames) - changed,
                      changed_sampled_RGB_swaps_per_second=changed * 1_000_000 / elapsed if valid_rate else None)
    if 'attempt_phases' in stat:
        phases = stat['attempt_phases']
        confirmed = [row for row in phases if row['completed']]
        in_window = [row for row, frame in zip(confirmed, stat['frames'])
                     if frame['completed_us'] <= stat['stop_us']]
        timed = [row['durations_us'] for row in in_window if row['durations_us'] is not None]
        result.update(attempt_outcomes=dict(Counter(str(row['status']) for row in phases)),
                      preflight_counts=dict(Counter(guard for row in phases for guard in row['preflight'])),
                      completed_GPU_swaps_in_window=sum(row['gpu'] for row in in_window),
                      completed_phase_times={key: latency_percentiles([row[key] for row in timed])
                                             for key in (timed[0] if timed else {})})
    return result


def summarize(report):
    if (report.get('serial_and_recovery_bound') is not True or report.get('synthetic_fixture') is not False
            or report.get('terminal_panic_observed') is not False):
        raise ValueError('Expected a verified, panic-free physical serial archive')
    windows = report['windows']
    held = report.get('held_DPU') or {}
    wire_schema = report.get('physical_observer_wire_schema')
    # The touch-only extensions preserve the v362 display record and timestamps.
    display_schema = 362 if wire_schema in (363, 367) else wire_schema
    result = dict(boot_tag=report['boot_tag'], scope=report['scope'],
                  metal_command_buffer_completion=metal_completions(report.get('scalar_timing')),
                  CPU_GOP_copy=gop_copies(windows),
                  panel_hardware_counter_windows=sum('panel_counter_delta' in window for window in windows),
                  unique_complete_panel_frames_per_second=None)
    if held.get('first_result') == held.get('second_result') == 'observed':
        result['held_DPU_counter_window'] = {key: held[key] for key in
                                             ('first_uptime_ms', 'second_uptime_ms', 'elapsed_ms', 'raw_frame_deltas')}
    if display_schema in (336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
        result['display_Apps_SMMU'] = report.get('display_Apps_SMMU')
    if report.get('display_transfer_archive_bound') is True:
        result['controlled_display_transfer'] = report.get('controlled_display_transfer')
    if report.get('physical_observer_wire_schema') in (341, 342):
        result['runtime_display_frame'] = report.get('runtime_display_frame')
    if report.get('physical_observer_wire_schema') == 342:
        result['runtime_display_scene'] = report.get('runtime_display_scene')
    if report.get('physical_observer_wire_schema') in (343, 344, 345, 346, 347):
        cadence = report.get('runtime_DSI_cadence')
        result['runtime_DSI_cadence'] = cadence
        if cadence and cadence['result'] == 'completed':
            elapsed = cadence['elapsed_us'] / 1_000_000
            result['runtime_DSI_observation_rates'] = dict(
                seconds=elapsed,
                interface_counter_advances_per_second=cadence['interface_advances'] / elapsed,
                observed_DSI_completions_per_second=cadence['fresh_dsi'] / elapsed,
                confirmed_changed_sampled_content_per_second=cadence['changed_content'] / elapsed,
                counter_and_event_counts_agree=cadence['interface_advances'] == cadence['fresh_dsi'],
                polling_gaps=cadence['polling_gaps'])
    if report.get('physical_observer_wire_schema') in (347, 356):
        comparison = report.get('panel_period_comparison')
        result['static_panel_period_comparison'] = comparison
        if comparison and comparison['sample_state'] == 4:
            elapsed = comparison['elapsed_us'] / 1_000_000
            synchronized = (not comparison['polling_gaps'] and comparison['fresh_dsi'] ==
                            comparison['interface_advances'] and elapsed <= 1.55)
            result['static_DSI_observation_rates'] = dict(
                seconds=elapsed, raw_DSI_completions_per_second=comparison['fresh_dsi'] / elapsed,
                interface_counter_advances_per_second=comparison['interface_advances'] / elapsed,
                full_window_observation=synchronized)
    if display_schema in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        result['compositor_scanout'] = compositor_scanout(report.get('live_scanout'))
    if display_schema in (359, 360, 361, 362) and result['compositor_scanout']:
        scanout = result['compositor_scanout']
        scanout['swap_time_origin'] = 'present-entry'
        if 'queue_to_DSI' in scanout:
            scanout['present_entry_to_DSI'] = scanout.pop('queue_to_DSI')
        phases = scanout.get('completed_phase_times', {})
        if 'queued_to_selection_us' in phases:
            phases['present_entry_to_selection_us'] = phases.pop('queued_to_selection_us')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis', type=Path, help='analysis.json from analyze-ios26-ft-capture.py')
    args = parser.parse_args()
    try:
        data = args.analysis.read_bytes()
        report = summarize(json.loads(data))
    except (KeyError, TypeError, ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
    report['source'] = dict(path=str(args.analysis.resolve()), sha256=hashlib.sha256(data).hexdigest())
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
