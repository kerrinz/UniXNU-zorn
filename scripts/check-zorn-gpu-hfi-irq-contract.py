#!/usr/bin/env python3
"""Pinned selected HFI domain and supplied-scalar code; no IRQ/native/phone calls."""
from pathlib import Path
import hashlib, importlib.util, json, re, shlex, subprocess

R = Path(__file__).resolve().parents[2]
O = R / 'out/zorn/gpu-gen7-hfi-irq-contract'
P = R / 'out/zorn/gpu-discovery-20261030/profile-reference'
L = R / 'out/zorn/gpu-discovery-20261030/layout'
S = R / 'out/zorn/gpu-discovery-20261030/stock'
N = R / 'UniXNU/drivers/NativeAdreno'
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
spec = importlib.util.spec_from_file_location('extent_util', R / 'UniXNU-zorn/scripts/check-zorn-gpu-gmu-extent.py')
util = importlib.util.module_from_spec(spec)
spec.loader.exec_module(util)
norm = lambda s: ' '.join(s.split())

def contract(gpulist, gen7, hfi, core, header):
    start = gpulist.index('static const struct adreno_gen7_core adreno_gpu_core_gen7_9_1 =')
    end = gpulist.index('\n};', start)
    assert '.gpudev = &adreno_gen7_9_0_hwsched_gpudev.base,' in gpulist[start:end], 'selected gpudev'
    start = gen7.index('const struct gen7_gpudev adreno_gen7_9_0_hwsched_gpudev =')
    end = gen7.index('\n};', start)
    assert '.hfi_probe = gen7_hwsched_hfi_probe,' in gen7[start:end], 'selected hfi probe'
    probe = norm(util.body(hfi, 'gen7_hwsched_hfi_probe'))
    assert 'kgsl_request_irq(gmu->pdev, "hfi", gen7_hwsched_hfi_handler, adreno_dev)' in probe, 'hwsched cookie and handler'
    assert 'hw_hfi->irq_mask = HFI_IRQ_MASK;' in probe
    b = norm(util.body(hfi, 'gen7_hwsched_hfi_handler'))
    assert 'gmu_core_regread(device, GEN7_GMU_GMU2HOST_INTR_INFO, &status);' in b, 'actual INFO read target'
    assert b.index('GEN7_GMU_GMU2HOST_INTR_INFO') < b.index('GEN7_GMU_GMU2HOST_INTR_CLR'), 'read before masked clear'
    assert 'GEN7_GMU_GMU2HOST_INTR_CLR, status & hfi->irq_mask' in b
    assert 'if (!(hfi->irq_mask & HFI_IRQ_MSGQ_MASK)) status &= ~HFI_IRQ_MSGQ_MASK;' in b, 'only MSGQ suppressed'
    assert 'if (status & (HFI_IRQ_MSGQ_MASK | HFI_IRQ_DBGQ_MASK))' in b
    assert 'if (status & HFI_IRQ_CM3_FAULT_MASK)' in b
    assert 'status &= GENMASK(31 - (oob_max - 1), 0);' in b, 'exact high-window boundary'
    assert 'status & ~hfi->irq_mask' in b
    assert b.count('gmu_core_regread(') == 1, 'no auxiliary register read in selected handler'
    assert 'complete(' not in b and 'gen7_hwsched_fault(adreno_dev, ADRENO_GMU_FAULT)' in b
    assert 'oob_dcvs = 7' in core and re.search(r'oob_dcvs\s*=\s*7[^\n]*\n\s*oob_max,', core), 'oob_max exactly8'
    for name, bit in [('MSGQ', 0), ('SIDEMSGQ', 1), ('DBGQ', 2), ('CM3_FAULT', 15)]:
        assert re.search(r'#define\s+HFI_IRQ_' + name + r'_MASK\s+BIT\(' + str(bit) + r'\)', header), name
    assert re.search(r'#define\s+HFI_IRQ_OOB_MASK\s+GENMASK\(31, 16\)', header)
    return b

def main():
    if (O / 'check-result.json').exists():
        raise SystemExit('completed; do not repeat')
    pins, provenance = {}, []
    for manifest, names, folder in [
        (P / 'manifest.json', ['adreno_gen7.c', 'adreno-gpulist.h', 'adreno_hfi.h'], P),
        (P / 'supplement-manifest.json', ['adreno_gen7_gmu.c'], P),
        (L / 'source-manifest.json', ['adreno_gen7_hfi.c'], L),
        (L / 'hwsched-hfi-source-manifest.json', ['adreno_gen7_hwsched_hfi.c'], L),
    ]:
        data = json.loads(manifest.read_text())
        entries = data['files'] if isinstance(data, dict) else data
        pins[str(manifest)] = sha(manifest)
        for name in names:
            e = next(e for e in entries if e.get('name', e.get('file')) == name and e.get('ok'))
            p = folder / name
            assert sha(p) == e['sha256'], p
            pins[str(p)] = e['sha256']
            provenance.append(dict(path=str(p), url=e['url'], sha256=e['sha256']))
    p = S / 'kgsl_gmu_core.h'
    assert sha(p) == '560027dfe9af8a56cab6db4fbb08597c470abf722686675f138235b71181e8ca'
    pins[str(p)] = sha(p)
    kgsl = R / 'out/zorn/gpu-gen7-preallocated-providers/kgsl.c'
    assert sha(kgsl) == '21f8f7ba8556f4bea965ac4c811843b26c8a59508b912b7a5cdfb9791c9d7da5'
    for p in [kgsl, N / 'NativeAdrenoIrq.h', N / 'NativeAdrenoIrq.cpp']:
        pins[str(p)] = sha(p)
    values = [(P / 'adreno-gpulist.h').read_text(), (P / 'adreno_gen7.c').read_text(),
              (L / 'adreno_gen7_hwsched_hfi.c').read_text(), (S / 'kgsl_gmu_core.h').read_text(),
              (P / 'adreno_hfi.h').read_text()]
    handler = contract(*values)
    (O / 'selected-handler.exact.txt').write_text(util.body(values[2], 'gen7_hwsched_hfi_handler') + '\n')
    legacy = util.body((L / 'adreno_gen7_hfi.c').read_text(), 'gen7_hfi_irq_handler')
    assert 'GEN7_GMU_GMU2HOST_INTR_CLR, HFI_IRQ_MASK' in norm(legacy)
    (O / 'nonselected-handler.exact.txt').write_text(legacy + '\n')
    req = norm(util.body(kgsl.read_text(), 'kgsl_request_irq'))
    assert 'platform_get_irq_byname(pdev, name)' in req and 'IRQF_TRIGGER_HIGH' in req and 'disable_irq(num);' in req
    gmu = (P / 'adreno_gen7_gmu.c').read_text()
    oob = norm(util.body(gmu, 'gen7_gmu_oob_set'))
    assert 'check = BIT(31 - req);' in oob and 'gmu_core_timed_poll_check(' in oob
    assert 'if (req >= oob_boot_slumber)' in oob
    assert 'IrqRbbmStatus = 0x0201' in (N / 'NativeAdrenoIrq.cpp').read_text()
    assert 'IrqBitCpFence = 1u << 20' in (N / 'NativeAdrenoIrq.cpp').read_text()
    controls = []
    for name, which, before, after in [
        ('nonselected-probe', 1, '.hfi_probe = gen7_hwsched_hfi_probe,', '.hfi_probe = gen7_gmu_hfi_probe,'),
        ('wrong-hwsched-cookie', 2, 'gen7_hwsched_hfi_handler, adreno_dev)', 'gen7_hwsched_hfi_handler, KGSL_DEVICE(adreno_dev))'),
        ('clear-before-read', 2, 'GEN7_GMU_GMU2HOST_INTR_INFO, &status', 'GEN7_GMU_GMU2HOST_INTR_CLR, &status'),
        ('OOB-max-drift', 3, 'oob_dcvs = 7', 'oob_dcvs = 8'),
    ]:
        bad = list(values)
        assert before in bad[which]
        bad[which] = bad[which].replace(before, after)
        try:
            contract(*bad)
        except (AssertionError, ValueError) as e:
            controls.append(dict(name=name, refused=str(e)))
        else:
            raise RuntimeError('source corruption survived ' + name)

    commands = []
    def run(args, name, cwd=R, good=True):
        args = list(map(str, args))
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=55)
        commands.append(dict(arguments=args, directory=str(cwd), returncode=p.returncode))
        (O / (name + '.log')).write_text(p.stdout + p.stderr)
        if good:
            p.check_returncode()
        else:
            assert p.returncode != 0, name
        return p.stdout + p.stderr

    flags = ['-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', '-I' + str(O)]
    src = O / 'ZornGpuGmuHfiStatus.c'
    test = O / 'test-hfi-status.c'
    run(['clang', *flags, src, test, '-o', O / 'test-hfi-status'], 'host-build')
    run([O / 'test-hfi-status'], 'host-run')
    negatives = []
    for name, before, after in [
        ('header-OOB-window-substituted', 'UINT32_C(0xfe000000)', 'UINT32_C(0xffff0000)'),
        ('all-branches-mask-gated', 'effective = raw & ~inline_msgq', 'effective = raw & supplied_software_mask'),
        ('unclassified-side-message-erased', 'raw & ~(msgq | dbgq | cm3)', 'raw & ~(msgq | dbgq | cm3 | UINT32_C(2))'),
    ]:
        s = src.read_text()
        assert s.count(before) == 1
        bad = O / (name + '.c')
        bad.write_text(s.replace(before, after))
        run(['clang', *flags, bad, test, '-o', O / name], name + '-build')
        run([O / name], name + '-refused', good=False)
        negatives.append(name)

    abi = O / 'hfi-domain-ABI.cpp'
    abi.write_text('''/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include <stddef.h>
#include "ZornGpuGmuHfiStatus.h"
#include "NativeAdrenoIrq.h"
using Classifier=int(*)(uint32_t,uint32_t,ZGGmuHfiStatus*);
static_assert(__is_same(decltype(&ZGClassifyGmuHfiStatus),Classifier));
static_assert(sizeof(ZGGmuHfiStatus)==36);
static_assert(offsetof(ZGGmuHfiStatus,ignored_high_bits_by_reference)==24);
static_assert(offsetof(ZGGmuHfiStatus,without_direct_branch)==32);
static_assert(sizeof(NativeAdrenoIrqResult)==20);
extern "C" const unsigned zorn_HFI_domain_sizes[]={sizeof(ZGGmuHfiStatus),sizeof(NativeAdrenoIrqResult),24,32};
''')
    objects, inputs = {}, dict(pins)
    b = R / 'UniXNU/out/zorn/tree/build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
    for name, source, recipe_path in [
        ('HFI-status', src, b / 'bsd/DEVELOPMENT/bsd_init.o.json'),
        ('HFI-domain-ABI', abi, b / 'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'),
    ]:
        inputs[str(recipe_path)] = sha(recipe_path)
        rec = json.JSONDecoder().raw_decode(recipe_path.read_text())[0]
        assert '--target=arm64-apple-ios17.0.0' in rec['arguments']
        args = list(rec['arguments'])
        args[args.index(rec['file'])] = str(source)
        obj = O / (name + '.o')
        args[args.index('-o') + 1] = str(obj)
        args += ['-I' + str(O), '-I' + str(N), '-mgeneral-regs-only']
        run(args, name + '-first', rec['directory'])
        first = O / (name + '-first.o')
        first.write_bytes(obj.read_bytes())
        run(args, name + '-independent', rec['directory'])
        assert sha(first) == sha(obj)
        objects[name] = sha(obj)
        imports = run(['nm', '-u', obj], name + '-imports').split()
        assert not any('Adreno' in x for x in imports)
        if name.endswith('ABI'):
            assert not imports
        assert '__mod_init_func' not in run(['otool', '-l', obj], name + '-sections')
        run(['otool', '-tvV', obj], name + '-disassembly')
        pp, i = [], 0
        while i < len(args):
            if args[i] in ['-o', '-MF', '-MT', '-MJ']:
                i += 2
            elif args[i] == '-c':
                i += 1
            else:
                pp.append(args[i]); i += 1
        dep = O / (name + '.d')
        run(pp + ['-M', '-MF', dep, '-MT', 'input'], name + '-deps', rec['directory'])
        for n in shlex.split(dep.read_text().replace('\\\n', ' ').split(':', 1)[1]):
            p = Path(n)
            if not p.is_absolute():
                p = Path(rec['directory']) / p
            inputs[str(p)] = sha(p)
    for p, h in pins.items():
        assert sha(Path(p)) == h
    for p in [src, O / 'ZornGpuGmuHfiStatus.h', test, abi]:
        inputs[str(p)] = sha(p)
    result = dict(source_provenance=provenance, inputs=inputs, objects=objects,
                  commands=commands, selected='gen7_9_1 -> adreno_gen7_9_0_hwsched_gpudev -> gen7_hwsched_hfi_probe -> gen7_hwsched_hfi_handler',
                  source_corruptions_refused=controls, actual_scalar_source_negatives_refused=negatives,
                  supplied_only=True, native_method_IRQ_MMIO_phone_calls=0, native_runtime_or_device_candidate=False,
                  no_successful_hardware_address_handle_fence_model=True,
                  allow_boot=False, readback_qualified=False, WriteAuthorized=0)
    (O / 'check-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Selected HFI domain bound;4 source +3 scalar source refusals;2 independent current iOS17 objects;no native calls')

if __name__ == '__main__':
    main()
