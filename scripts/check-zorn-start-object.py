#!/usr/bin/env python3
"""Reject stale start.o or an undeclared early-entry trace in the linked kernel."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT / 'UniXNU/out/zorn/tree'
OUT = ROOT / 'out/zorn/smp'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbols(path):
    return subprocess.check_output(['xcrun', 'nm', '-n', str(path)], text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object-only', action='store_true')
    args = parser.parse_args()
    source = TREE / '.cache/xnu-work/osfmk/arm64/start.s'
    obj = TREE / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/osfmk/DEVELOPMENT/start.o'
    recipe = obj.with_name(obj.name + '.json')
    record = json.loads(recipe.read_text().strip().rstrip(','))
    if Path(record['file']).resolve() != source.resolve():
        raise RuntimeError('start.o recipe does not compile the expected staged source')
    command = list(record['arguments'])
    if command.count('-o') != 1 or '-c' not in command:
        raise RuntimeError('unsupported start.o compile recipe')
    expected_trace = 'ZORN_SECONDARY_STAGE' in source.read_text()
    replay = json.loads((ROOT / 'UniXNU/out/zorn/source-replay.json').read_text())
    layers = replay.get('additional_patches', [])
    declared_trace = any(layer['path'] == 'patches/diagnostics/cpu1-early-entry-trace.patch' for layer in layers)
    if declared_trace != expected_trace:
        raise RuntimeError('early-entry trace source and declared diagnostic layer disagree')
    expected_virtual = 'LEXT(zorn_secondary_virtual_trace)' in source.read_text()
    declared_virtual = any(layer['path'] == 'patches/diagnostics/cpu1-virtual-trampoline-trace.patch' for layer in layers)
    if declared_virtual != expected_virtual:
        raise RuntimeError('virtual-trampoline source and declared diagnostic layer disagree')
    expected_translation = 'LEXT(zorn_secondary_translation_probe)' in source.read_text()
    declared_translation = any(layer['path'] == 'patches/diagnostics/cpu1-translation-probe.patch' for layer in layers)
    if declared_translation != expected_translation:
        raise RuntimeError('translation probe source and declared diagnostic layer disagree')
    expected_nop = 'ZORN_TRANSLATION_NOP_CONTROL' in source.read_text()
    declared_nop = any(layer['path'] == 'patches/diagnostics/cpu1-translation-nop-control.patch' for layer in layers)
    if declared_nop != expected_nop or (expected_nop and not expected_translation):
        raise RuntimeError('translation NOP control and declared diagnostic layer disagree')
    expected_source_capture = 'LEXT(zorn_secondary_ttbr_source_capture)' in source.read_text()
    declared_source_capture = any(layer['path'] == 'patches/diagnostics/cpu1-ttbr-source-read.patch' for layer in layers)
    if declared_source_capture != expected_source_capture or (expected_source_capture and not expected_nop):
        raise RuntimeError('TTBR source capture and declared diagnostic layer disagree')
    source_before = sha(source)
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='start-object-audit-', dir=OUT) as temp:
        fresh = Path(temp).resolve() / 'start.o'
        command[command.index('-o') + 1] = str(fresh)
        if '-MJ' in command:
            i = command.index('-MJ')
            del command[i:i + 2]
        subprocess.run(command, cwd=record['directory'], check=True, capture_output=True)
        if sha(source) != source_before:
            raise RuntimeError('start.s changed during independent assembly')
        fresh_hash = sha(fresh)
        if sha(obj) != fresh_hash:
            raise RuntimeError('stale start.o: independent assembly of current source differs; rebuild before packaging')
    if ('_zorn_secondary_exception' in symbols(obj)) != expected_trace:
        raise RuntimeError('start.o trace identity differs from staged source')
    object_symbols = symbols(obj)
    for name in ('_zorn_secondary_virtual_trace', '_zorn_secondary_after_phystokv'):
        if (name in object_symbols) != expected_virtual:
            raise RuntimeError('start.o virtual-trampoline trace differs from source')
    if ('_zorn_secondary_translation_probe' in object_symbols) != expected_translation:
        raise RuntimeError('start.o translation probe differs from source')
    if ('_zorn_secondary_ttbr_source_capture' in object_symbols) != expected_source_capture:
        raise RuntimeError('start.o TTBR source capture differs from source')
    report = dict(ttbr_source_capture=expected_source_capture,
                  translation_nop_control=expected_nop,
                  translation_probe=expected_translation,
                  virtual_trampoline_trace=expected_virtual,
                  source_sha256=source_before, object_sha256=fresh_hash,
                  recipe_sha256=sha(recipe), independent_assembly_exact=True,
                  asm_trace=expected_trace, declared_layer_matches=True)
    if not args.object_only:
        kernel = ROOT / 'UniXNU/out/zorn/kernel/kernel.macho'
        if ('_zorn_secondary_exception' in symbols(kernel)) != expected_trace:
            raise RuntimeError('linked kernel retains an undeclared or missing early-entry trace')
        linked_symbols = symbols(kernel)
        for name in ('_zorn_secondary_virtual_trace', '_zorn_secondary_after_phystokv'):
            if (name in linked_symbols) != expected_virtual:
                raise RuntimeError('linked virtual-trampoline trace differs from source')
        if ('_zorn_secondary_translation_probe' in linked_symbols) != expected_translation:
            raise RuntimeError('linked translation probe differs from source')
        if ('_zorn_secondary_ttbr_source_capture' in linked_symbols) != expected_source_capture:
            raise RuntimeError('linked TTBR source capture differs from source')
        if expected_translation:
            # This pinned probe's AT/NOP and marker must match actual linked code.
            import re
            marker = re.search(r'^([0-9a-f]+)\s+\S\s+_zorn_secondary_translation_probe$', linked_symbols, re.M)
            if not marker:
                raise RuntimeError('translation probe symbol missing')
            address = int(marker.group(1), 16)
            assembly = subprocess.check_output(['xcrun', 'llvm-objdump', '--disassemble',
                '--disassemble-symbols=_zorn_secondary_translation_probe', str(kernel)], text=True)
            words = {int(pc,16):int(op,16) for pc,op in re.findall(r'^([0-9a-f]+):\s+([0-9a-f]{8})\s',assembly,re.M)}
            if words.get(address+0x30) != (0xd503201f if expected_nop else 0xd5087800):
                raise RuntimeError('linked AT/NOP differs from declared probe mode')
            if words.get(address+0x50) != (0xd2801472 if expected_source_capture else 0xd2801452 if expected_nop else 0xd2801432):
                raise RuntimeError('linked diagnostic marker differs from declared probe mode')
            if words.get(address+0x38) != (0xf9401e32 if expected_source_capture else 0xd5387412):
                raise RuntimeError('linked TTBR source/priorPAR read differs from declared mode')
        report.update(kernel_sha256=sha(kernel), linked_trace_matches=True)
    (OUT / 'start-object-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
