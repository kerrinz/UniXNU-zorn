"""Exact native recipes for the opt-in CPU-only Gen7 owned-memory component.

No service, MMIO, SMMU or firmware execution. Outputs and compiler metadata
belong to this build directory; never write an active recipe's output paths.
"""
import hashlib,json,subprocess
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def compile_command(record,source,target,includes):
    a=record['arguments'];cmd=[];i=0
    while i<len(a):
        v=a[i]
        if v==record['file']:cmd.append(str(source))
        elif v=='-o':cmd+=['-o',str(target)];i+=1
        elif v in ('-MF','-MJ','-MT'):i+=1
        elif v not in ('-MD','-MP'):cmd.append(v)
        i+=1
    cmd += ['-mgeneral-regs-only','-fstack-usage']
    for p in includes:cmd+=['-I',str(p)]
    return cmd

def build(tree,device,out,enabled,env=None):
    tree,device,out=Path(tree).resolve(),Path(device).resolve(),Path(out).resolve()
    device=(device/'native').resolve().parent
    root=device.parent;core=root/'UniXNU';native=device/'native/gpu-owned'
    adreno=core/'drivers/Adreno740';firmware=core/'kits/AdrenoFirmware'
    out.mkdir(parents=True,exist_ok=True)
    base=tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
    recipes={'c':base/'bsd/DEVELOPMENT/bsd_init.o.json','cxx':base/'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'}
    records={k:json.JSONDecoder().raw_decode(p.read_text())[0] for k,p in recipes.items()}
    files=[];commands=[];objects=[]
    def run(cmd,cwd=None):
        result=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True)
        (out/('compile-%02d.log'%len(commands))).write_text(result.stdout+result.stderr)
        result.check_returncode()

    if enabled:
        if not (core.is_dir() and native.is_dir()):raise ValueError('GPU device/core paths differ')
        sources=[native/(n+'.cpp') for n in ('ZornGpuFirmwarePlan','ZornGpuNativePlatform','ZornGpuOwnedMemory','ZornGpuOwnedRuntime')]
        sources += [adreno/(n+'.cpp') for n in ('NativeAdrenoBoard','NativeAdrenoMemory','NativeAdrenoCpu','NativeAdrenoSha256')]+[firmware/'AdrenoFirmware.c']
        pins=json.loads((native/'firmware-pins.json').read_text())
        asm=['.section __TEXT,__const',' .p2align 3']
        for key in ('gmu','sqe','aqe','zap'):
            rec=pins[key];p=(root/rec['path']).resolve()
            if not p.is_relative_to(root) or p.stat().st_size!=rec['bytes'] or digest(p)!=rec['sha256']:
                raise ValueError('fixed stock firmware differs: '+key)
            files.append(p)
            # Path is generated only from pinned local records, not boot arguments.
            if any(c in str(p) for c in ('"','\n','\\')):raise ValueError('unsafe assembly input path')
            asm+=['.p2align 3',f'.globl _zorn_gpu_mem_{key}',f'_zorn_gpu_mem_{key}:',f'.incbin "{p}"',
                '.p2align 3',f'.globl _zorn_gpu_mem_{key}_size',f'_zorn_gpu_mem_{key}_size:',f'.quad {rec["bytes"]}']
        assembly=out/'stock-firmware.s';assembly.write_text('\n'.join(asm)+'\n');files.append(assembly)
        obj=out/'stock-firmware.o';cmd=[records['c']['arguments'][0],'-target','arm64-apple-ios17.0.0','-c',str(assembly),'-o',str(obj)]
        run(cmd);objects.append(obj);commands.append(dict(arguments=cmd,cwd=str(root)))
        files += list(native.glob('*'))+[device/'native/display/ZornDisplayProgress.h']
        files += list(adreno.glob('*.h'))+[firmware/'AdrenoFirmware.h']
    else:sources=[native/'ZornGpuOwnedStub.c']
    for source in sources:
        rec=records['c' if source.suffix=='.c' else 'cxx'];obj=out/(source.stem+'.o')
        cmd=compile_command(rec,source,obj,[native,adreno,firmware,tree/'.cache/xnu-work/osfmk'])
        run(cmd,cwd=rec['directory'])
        files.append(source);objects.append(obj);commands.append(dict(arguments=cmd,cwd=rec['directory']))
    files += list(recipes.values())+[Path(__file__).resolve()]
    report=dict(enabled=bool(enabled),runtime_complete=False,commands=commands,
        source_sha256={str(p):digest(p) for p in sorted(set(files)) if p.is_file()},
        object_sha256={str(p):digest(p) for p in objects},
        scope='CPU-owned allocation only. Independent watchdog mandatory; IOKit calls may block. No final kernel/virtual ABI/ready qualification.')
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    return objects
