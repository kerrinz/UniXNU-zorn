#!/usr/bin/env python3
"""Self-contained checks of actual CPU-active native source and strict guards."""
import argparse,ast,hashlib,importlib.util,json,subprocess,struct,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
NATIVE=ROOT/'UniXNU-zorn/native/cpu-active'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def parser_guard(path,builder):
    tree=ast.parse(path.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');body=[]
    for n in fn.body:
        if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.values[0],ast.Attribute) and n.test.values[0].attr=='cpu_active_observation':guard=n;break
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='args' for t in n.targets):break
    # Pull only the actual parser declarations and feature guard, never main().
    declarations=[]
    for n in fn.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='args' for t in n.targets):break
        declarations.append(n)
    guard=next(n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.values[0],ast.Attribute) and n.test.values[0].attr=='cpu_active_observation')
    env=dict(argparse=argparse,Path=Path,ROOT=ROOT,REPO=ROOT/'uefi-zorn')
    exec(compile(ast.fix_missing_locations(ast.Module(body=declarations,type_ignores=[])),str(path),'exec'),env)
    args=env['parser'].parse_args([])
    values=dict(cpu_active_observation=True,display_progress=True,smp_preflight=8,smp_continue=True,smp_root_publication=1,smp_stop_after_pass=False,gui_watch=True,touch_trace=True,touch_runtime=True,retained_data=True,fresh_data=False,data_profile='8g',memory_mib=8192,early_watchdog=1,gui_hold_seconds=300,display_mode=3,brightness_mode=3,data_store_mode=2,gui_user_stacks=False,gui_kernel_stacks=False,gui_runnable_kernel_stacks=False)
    if builder:values.update(source_pins=Path('pins'),incremental_patched_tree=True,recovery_timeout=600,boot=False,reuse_kernel_control=None,reuse_smp_publication_control=None,reuse_gui_budget_control=None)
    for k,v in values.items():setattr(args,k,v)
    # Replace parser.error only to retain exact guard evaluation without stderr.
    def error(message):raise ValueError(message)
    env['parser'].error=error;env['args']=args
    code=compile(ast.fix_missing_locations(ast.Module(body=[guard],type_ignores=[])),str(path),'exec');exec(code,env)
    negatives=[]
    for k,v in values.items():
        if k=='cpu_active_observation':continue
        if isinstance(v,bool):bad=not v
        elif v is None:bad=Path('forbidden-reuse')
        elif isinstance(v,int):bad=v+1
        elif isinstance(v,Path):bad=None
        else:bad='wrong-profile'
        setattr(args,k,bad)
        try:exec(code,env)
        except ValueError:negatives.append(k)
        else:raise AssertionError('guard accepted invalid '+k)
        setattr(args,k,v)
    args.cpu_active_observation=False;args.smp_preflight=0;exec(code,env)
    return negatives
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'out/zorn/cpu-active/host-check.json');a=p.parse_args()
    guards={str(path.relative_to(ROOT)):parser_guard(path,b) for path,b in [(ROOT/'UniXNU-zorn/scripts/build-zorn-debug.py',True),(ROOT/'uefi-zorn/scripts/make-zorn-payload.py',False)]}
    with tempfile.TemporaryDirectory(prefix='cpu-active-host-') as directory:
        work=Path(directory);obs=work/'observer';obs.mkdir()
        for f in NATIVE.iterdir():
            if f.is_file():(obs/f.name).write_bytes(f.read_bytes())
        for f in (NATIVE/'tests').iterdir():
            if f.is_file():(work/f.name).write_bytes(f.read_bytes())
        (obs/'observer-host-shim.h').write_bytes((work/'observer-host-shim.h').read_bytes())
        def run(cmd):
            r=subprocess.run([str(v) for v in cmd],capture_output=True,text=True)
            if r.returncode:raise RuntimeError(r.stderr[-3000:])
            return r.stdout
        common=['-O1','-g','-fsanitize=address,undefined','-Wall','-Wextra','-Werror','-I',str(obs)]
        tests={}
        for name,sources in [('two-sweep',['two-sweep.c','two-sweep-test.c']),('codec',['active-log-v2-codec.c','active-log-v2-test.c'])]:
            src=[obs/f if (obs/f).exists() else work/f for f in sources];exe=work/name;run(['xcrun','clang','-std=c11',*common,'-pthread',*src,'-o',exe]);tests[name]=json.loads(run([exe]))
        source=(ROOT/'UniXNU-zorn/native/ufs-read/ZornUfsRead.cpp').read_text();start=source.index('static IOReturn zorn_write_log4k(');brace=source.index('{',start);end=brace+1;depth=1
        while depth:
            if source[end]=='{':depth+=1
            elif source[end]=='}':depth-=1
            end+=1
        (work/'writer-body.inc').write_text(source[start:end]+'\n')
        objects=[]
        for name in ['two-sweep','active-log-v2-codec','ZornCpuActive']:
            obj=work/(name+'.o');run(['xcrun','clang','-std=c11',*common,'-DZORN_ACTIVE_INTEGRATION_HOST_TEST','-c',obs/(name+'.c'),'-o',obj]);objects.append(obj)
        exe=work/'pipeline';run(['xcrun','clang++','-std=c++17',*common,'-pthread',work/'pipeline-host-test.cpp',*objects,'-o',exe])
        raw=bytearray(4096);struct.pack_into('<8s2I',raw,0,b'ZORNLOGD',84,17)
        for i in range(84):raw[16+i*12:20+i*12]=f'D{i:03}'.encode()
        struct.pack_into('<8s6IQ',raw,1024,b'ZORNGUI1',19,3072,1,12,0,1,15000)
        trace=[0]*108;trace[0]=2;trace[1]=0x3152545a;trace[10]=1;struct.pack_into('<108I',raw,3496,*trace);struct.pack_into('<Q',raw,3952,0xffffffff)
        fixture=work/'source.bin';fixture.write_bytes(raw)
        reader=load('cpu_active_main_reader',ROOT/'UniXNU-zorn/scripts/read-zorn-log.py');decoder=load('cpu_active_decoder',ROOT/'UniXNU-zorn/scripts/zorn_cpu_active.py');reader.gui_state(bytes(raw))
        pipeline=[]
        for mode in ['off','healthy','busy','not-ready','clock-bad','overflow','late','absent','backward']:
            wire=work/(mode+'.bin');pipeline.append(json.loads(run([exe,mode,fixture,wire])))
            block=wire.read_bytes()
            if mode=='off':assert block[:8]==b'ZORNLOGD';continue
            active=decoder.decode(block);old=active['original_block'];assert old[1024:]==raw[1024:]
            assert reader.decode(block)==reader.decode(old)
            new=reader.gui_state(block);metadata=new.pop('cpu_active');assert new==reader.gui_state(old) and metadata['measurement_available']==(mode=='healthy')
    result=dict(actual_native_asan_ubsan=tests,pipeline=pipeline,actual_guard_negative_controls=guards,self_contained_fixture=True,phone_log_dependency=False,production_boot_qualified=False,
        inputs={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [*NATIVE.rglob('*.c'),*NATIVE.rglob('*.h'),*NATIVE.rglob('*.cpp'),ROOT/'UniXNU-zorn/scripts/zorn_cpu_active.py',Path(__file__)]})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(host_pass=True,builder_negatives=len(next(iter(guards.values()))),pipeline_modes=len(pipeline))))
if __name__=='__main__':main()
