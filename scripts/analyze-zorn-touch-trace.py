#!/usr/bin/env python3
"""Read a bound recovered K80 trace; score five points only after owner confirmation."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--five-point-confirmed', action='store_true',
                        help='owner confirms the prescribed order, without extra touches or mis-presses')
    parser.add_argument("--final-center-repeat-confirmed", action="store_true",
                        help="owner confirms a sixth press repeating only the final center")
    args = parser.parse_args()
    if args.final_center_repeat_confirmed and not args.five_point_confirmed:
        parser.error("center repeat requires confirmed five-point order")
    run = args.run.resolve()
    if run.parent != (ROOT / 'out/zorn/debug').resolve():
        parser.error('require a local out/zorn/debug trial')
    trial = json.loads((run/'run.json').read_text())
    build = json.loads((run/'build-inputs.json').read_text())
    if (trial.get('serial') != '92988a43' or trial.get('product') != 'zorn' or trial.get('slot') != 'b'
            or trial.get('status') != 'recovered' or trial.get('kernel_log_changed') is not True
            or build.get('status') != 'ready' or trial.get('sha256') != build.get('sha256')):
        parser.error('require a recovered, changed log and matching identified ready build')
    archive = ROOT/'out/zorn/builds'/build['sha256'][:8]
    kernel_key = str(ROOT/'UniXNU/out/zorn/kernel/kernel.macho')
    reader_path = Path(__file__).with_name('read-zorn-log.py')
    if (digest(archive/'boot.img') != build['sha256']
            or digest(archive/'kernel.macho') != build['inputs'][kernel_key]
            or digest(archive/'inputs.json') != digest(run/'build-inputs.json')
            or digest(reader_path) != trial['host_log_reader_sha256']
            or digest(run/'checkpoints.bin') == trial.get('preboot_log_sha256')):
        parser.error('image, kernel, archive, reader or fresh-log identity mismatch')
    spec = importlib.util.spec_from_file_location('zorn_log_reader', reader_path)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    state = reader.gui_state((run/'checkpoints.bin').read_bytes())
    trace = state.get('touch_trace') if state else None
    result = {'run': str(run.relative_to(ROOT)), 'boot_sha256': build['sha256'],
              'kernel_sha256': build['inputs'][kernel_key], 'log_sha256': digest(run/'checkpoints.bin'),
              'fresh_recovered_log_and_archive_bound': True,
              'owner_five_point_confirmed': args.five_point_confirmed,
              'owner_final_center_repeat_confirmed': args.final_center_repeat_confirmed,
              'trace': trace, 'touch': state.get('touch') if state else None,
              'touch_edges': state.get('touch_edges') if state else None,
              'coordinate_qualified': False, 'ui_hit_test_qualified': False, 'gestures': []}
    if trace and trace['status'] == 'coherent':
        active, orphaned = {}, []
        for point in trace['records']:
            identity = point['id']
            if point['phase'] == 'down':
                if identity in active:
                    orphaned.append(active.pop(identity))
                active[identity] = [point]
            elif identity not in active:
                orphaned.append([point])
            else:
                active[identity].append(point)
                if point['phase'] == 'up':
                    points = active.pop(identity)
                    held = points[:-1]
                    result['gestures'].append({
                        'id': identity, 'down_ms': points[0]['ms'], 'up_ms': point['ms'],
                        'duration_ms': point['ms']-points[0]['ms'], 'records': len(points),
                        'x': statistics.median(p['x'] for p in held)/32767,
                        'y': statistics.median(p['y'] for p in held)/32767,
                        'normal_release': point['release_reason'] == 'normal',
                        'single_contact': all(p['contacts'] == 1 for p in held)})
        result['gestures'].sort(key=lambda g: g['down_ms'])
        result['incomplete_trace_records'] = sum(len(p) for p in orphaned)+sum(len(p) for p in active.values())
        valid = (args.five_point_confirmed and trace['overwritten_records'] == 0
                 and result['incomplete_trace_records'] == 0
                 and len(result['gestures']) == (6 if args.final_center_repeat_confirmed else 5)
                 and all(g['normal_release'] and g['single_contact'] for g in result['gestures']))
        if valid:
            targets = ((.25,.25),(.75,.25),(.25,.75),(.75,.75),(.5,.5))
            if args.final_center_repeat_confirmed:
                targets = (*targets, (.5,.5))
            candidates = []
            for swap in (False, True):
                for flip_x in (False, True):
                    for flip_y in (False, True):
                        errors = []
                        for gesture, (tx,ty) in zip(result['gestures'], targets):
                            x,y = gesture['x'],gesture['y']
                            if swap:
                                x,y = y,x
                            if flip_x:
                                x = 1-x
                            if flip_y:
                                y = 1-y
                            errors.append(math.hypot(x-tx,y-ty))
                        candidates.append({'swap_xy':swap,'flip_x':flip_x,'flip_y':flip_y,
                                           'rms_error':math.sqrt(sum(v*v for v in errors)/len(targets)),
                                           'max_error':max(errors)})
            candidates.sort(key=lambda c:c['rms_error'])
            result['orientation_comparison'] = candidates
            result['orientation_distinguished'] = (candidates[0]['max_error'] <= .18
                                                   and candidates[1]['rms_error']-candidates[0]['rms_error'] >= .1)
            result['interpretation'] = 'sensor orientation evidence only; never applies a transform or qualifies UIKit hit testing'
        else:
            result['interpretation'] = 'target order not confirmed or complete five-point gesture evidence unavailable; do not infer axis correction'
    else:
        result['interpretation'] = 'no coherent coordinate trace; do not infer a successful empty capture'
    (run/'touch-coordinate-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
