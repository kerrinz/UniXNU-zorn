#!/usr/bin/env python3
"""Audit actual linked touch calls and unchanged original HID instructions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--kernel', type=Path, default=ROOT/'UniXNU/out/zorn/kernel/kernel.macho')
p.add_argument('--plan', type=Path)
p.add_argument('--output', type=Path, default=ROOT/'out/zorn/touch/runtime-linked-calls.json')
a = p.parse_args()
sys.path.insert(0, str(ROOT/'UniXNU/out/zorn/tree/kits/XnuPrelink'))
from native_prelink import macho, backed_offset
blob = a.kernel.read_bytes()
image = macho(blob)
symbols = {}
for line in subprocess.check_output(['xcrun', 'nm', '-n', str(a.kernel)], text=True).splitlines():
    f = line.split()
    if len(f) == 3 and re.fullmatch('[0-9a-f]+', f[0]):
        symbols[f[2]] = int(f[0], 16)

def calls(name):
    body = subprocess.check_output(['xcrun', 'llvm-objdump', '--disassemble',
        '--disassemble-symbols='+name, str(a.kernel)], text=True)
    return {int(v, 16) for v in re.findall(r'\b(?:bl|b)\s+0x([0-9a-f]+)\b', body)}, body

start = '__ZN16ZornTouchRuntimeL5startEv'
worker = '__ZN16ZornTouchRuntimeL6workerEPvi'
assert symbols[start] in calls('_native_legacy_display_late_probe')[0]
start_calls, assembly = calls(start)
assert symbols['_kernel_thread_start_priority'] in start_calls
assert re.search(r'mov\s+w2, #0x51', assembly), 'actual linked worker must use priority81 with cooperative wire reads'
assert symbols['_zorn_touch_hid_publish'] in start_calls
assert symbols['_zorn_touch_hid_send'] in calls(worker)[0]
yield_name = '__ZN14ZornTouchIdBus9afterByteEj'
yield_calls, yield_assembly = calls(yield_name)
assert symbols['_IOSleep'] in yield_calls and re.search(r'mov\s+w0, #0x1\b', yield_assembly)
wire_names = {n for n in symbols if 'ZornFt' in n or 'ZornTouchIdBus' in n}
pending, visited = [worker], set()
while pending:
    name = pending.pop()
    if name in visited:
        continue
    visited.add(name)
    addresses = calls(name)[0]
    pending.extend(n for n in wire_names if symbols[n] in addresses and n not in visited)
assert yield_name in visited, 'runtime worker must actually reach cooperative wire yields'
ctor = symbols['__GLOBAL__sub_I_ZornTouchHid.cpp']
for segment in image['segments']:
    for section in segment['sections']:
        if section['name'] == '__mod_init_func':
            size = section['size']
            assert size % 8 == 0
            offset = backed_offset(image['segments'], section['va'], size, len(blob))
            assert ctor not in struct.unpack('<'+'Q'*(size//8), blob[offset:offset+size])
plan = json.loads((a.plan or a.kernel.with_suffix('.json')).read_text())
extent = next(e for e in plan['extents'] if e['module'] == 'com.apple.iokit.IOHIDFamily' and e['segment'] == '__TEXT_EXEC')
offset = backed_offset(image['segments'], extent['va'], extent['size'], len(blob))
original_sha = hashlib.sha256(blob[offset:offset+extent['size']]).hexdigest()
assert original_sha == plan['original_executable_sha256']['com.apple.iokit.IOHIDFamily'] == '7e4c5104814f2e773d5be13d092dec53ee44ba5a61a81264b229780406e86b72'
result = dict(kernel_sha256=hashlib.sha256(blob).hexdigest(), late_probe_to_runtime_start=True,
    runtime_to_original_hid_adapter=True, worker_to_hid_report_send=True,
    hid_initializer_deferred=True, original_hid_instructions_unchanged=True,
    linked_thread_priority=81, actual_wire_sleep_1ms_reachable=True, hardware_qualified=False)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
