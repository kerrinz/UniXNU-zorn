#!/usr/bin/env python3
"""Verify the actual native/Turnip/frontend header and target dependencies."""
import argparse,hashlib,json,shlex,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();B=a.build.resolve();a.out.mkdir();load=lambda p:json.loads(Path(p).read_text())
    pin=lambda p:dict(path=str(Path(p).resolve()),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    C=load(B/'candidate.json');M=Path(C['Turnip_source']);F=Path(C['frontend_source']);source=M/'src/freedreno/vulkan/tu_knl_darwin.cc'
    commands=load(B/'turnip/build/compile_commands.json');rows=[r for r in commands if (Path(r['directory'])/r['file']).resolve()==source]
    assert len(rows)==1;command=rows[0];args=shlex.split(command['command'])
    assert args[args.index('-target')+1]=='arm64e-apple-ios26.0'
    SDK=Path(args[args.index('-isysroot')+1]);assert SDK.name=='iPhoneOS27.0.sdk'
    obj=Path(command['directory'])/command['output'];assert obj.is_file()
    result=subprocess.run(['ninja','-C',command['directory'],'-t','deps',command['output']],capture_output=True,text=True,timeout=30)
    (a.out/'actual-ninja-deps.txt').write_text(result.stdout+result.stderr);assert not result.returncode
    deps=[(Path(command['directory'])/line.strip()).resolve() for line in result.stdout.splitlines() if line.startswith('    ')]
    header=M/'k80-abi280/ZornDarwinCallCost287.h';abi=M/'k80-abi280/NativeAdrenoABI.h'
    assert header in deps and abi in deps
    front_deps=B/'metal-compile/NativeBridgeMetalFrontend279.d'
    front_tokens=front_deps.read_text().replace('\\\n',' ').split();front_headers=[Path(n).resolve() for n in front_tokens if Path(n).name=='ZornDarwinCallCost287.h']
    assert front_headers==[(F/'ZornDarwinCallCost287.h').resolve()]
    repo=Path(__file__).resolve().parents[1];copies=[header,F/header.name,repo/'native/ios26-perf290'/header.name]
    assert len({pin(p)['sha256'] for p in copies})==1
    V=load(B/'native-vfs.json');mapping={r['name']:Path(r['external-contents']) for r in V['roots'] if 'external-contents'in r};native_ABI=[]
    for dep in (B/'native-compile').glob('*.deps'):
        for token in dep.read_text().replace('\\\n',' ').split():
            if Path(token).name=='NativeAdrenoABI.h':native_ABI.append(mapping.get(token,Path(token)).resolve())
    native_ABI=sorted(set(native_ABI));assert native_ABI and all(pin(p)['sha256']==pin(abi)['sha256'] for p in native_ABI)
    front=load(B/'frontend290.command.json')['arguments'];assert front[front.index('-target')+1]=='arm64e-apple-ios26.0' and Path(front[front.index('-isysroot')+1])==SDK
    plugin=load(B/'metal-plugin/build-result290.json');turnip=load(B/'turnip/build-result290.json')
    assert plugin['passed'] and turnip['passed'] and plugin['ABI']==turnip['ABI']==1
    assert plugin['files']['libvulkan_freedreno.dylib']==turnip['dylib_sha256']==pin(turnip['dylib'])['sha256']
    assert plugin['native_PAC_archive_unchanged'] and not plugin['postlink_instruction_rewrite']
    assert pin(plugin['retained_Rust_archive']['path'])==plugin['retained_Rust_archive']
    assert plugin['CPU_page_bytes']==16384 and plugin['GPU_page_bytes']==plugin['signature_page_bytes']==4096
    report=dict(passed=True,source=pin(source),test_tool=pin(__file__),shared_scalar_header_copies=list(map(pin,copies)),actual_native_ABI=list(map(pin,native_ABI)),actual_Mesa_ABI=pin(abi),
        actual_Mesa_compile_command=command,actual_Mesa_object=pin(obj),actual_Mesa_dependency_metadata=pin(a.out/'actual-ninja-deps.txt'),actual_frontend_compile=pin(B/'frontend290.command.json'),actual_frontend_dependency_metadata=pin(front_deps),selected_Mesa_source=pin(B/'selected-source290.json'),signed_Turnip=pin(turnip['dylib']),signed_plugin=pin(B/'metal-plugin/build-result290.json'),retained_Rust_archive=plugin['retained_Rust_archive'],kernel_ABI_unchanged=True,
        scope='Actual compiler dependency/target metadata and exact source/header/binary hashes;no instruction inspection,device access or hardware qualification',phone_access=False,no_disassembly_or_reverse_engineering=True)
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS290 actual compiler dependencies:one scalar header,ABI1,arm64e iOS26,retained native Rust')

if __name__=='__main__':main()
