from pathlib import Path
import json,hashlib,importlib.util,re
import argparse
p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--parent-source',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();S=a.source_root.resolve();PS=a.parent_source.resolve();O=a.out.resolve();O.mkdir();tool=Path(__file__).with_name('check-ios26-failure-source.py');spec=importlib.util.spec_from_file_location('source261_projection',tool);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def extra(t):
 key='// The exact existing preflight refusal,not a larger resource allowance.'
 if key in t:
  a=t.index(key);z=t.index('        return kIOReturnNoResources;',a);cpu=t[a:z]
  expected='''// The exact existing preflight refusal,not a larger resource allowance.
        // CPU scalar sizes only:no IOVA/PA/task pointers or hardware access.
        const bool objectLimit262=objects_>=ZornGen7DirectVm26MaxObjects;
        const size_t first262=objectLimit262?objects_:capacity_-spanCount();
        const size_t second262=objectLimit262?ZornGen7DirectVm26MaxObjects:memory->spanCount();
        zorn_failure_note261(ZornFailureMapPreflight262,uint32_t(kIOReturnNoResources),ZornFailureBackend261,
            objectLimit262?ZornFailureObjectCapacity262:ZornFailureSpanCapacity262,
            first262>UINT32_MAX?UINT32_MAX:uint32_t(first262),second262>UINT32_MAX?UINT32_MAX:uint32_t(second262));
'''
  assert m.tokens(cpu)==m.tokens(expected),'Observation block changed;review every removed expression'
  t=t[:a]+t[z:];t=re.sub(r'\{\s*return kIOReturnNoResources;\s*\}',r'return kIOReturnNoResources;',t)
 return m.project(t)
rows=[]
for n in ['direct-runtime/ZornGen7DirectClient26.cpp','direct-runtime/ZornGen7DirectSubmit26.cpp','direct-runtime/ZornGen7DirectVm26.cpp','ZornGen7HostRing26.cpp','ZornGen7SmmuDomain26.cpp']:
 a=m.tokens(extra((PS/n).read_text()));b=m.tokens(extra((S/n).read_text()));assert a==b,n;rows.append(dict(file=n,parent=pin(PS/n),current=pin(S/n),native_operational_tokens_equal_after_explicit_diagnostic_projection=True))
same=[]
for n in ['ZornGen7HostGpuTables26.cpp','ZornGen7DarwinBoardOwner.cpp','ZornGen7AppExecution26.cpp','ZornGen7PhysicalOob26.h','ZornGen7DirectHfi26.cpp','direct-ring/NativeAdrenoRing.cpp','direct-ring/NativeAdrenoRing.h','ZornClientFailureStore261.h','ZornClientFailureWire261.h','direct-runtime/ZornGen7AppIo26.cpp','direct-runtime/ZornGen7AppIo26.h']:
 assert (S/n).read_bytes()==(PS/n).read_bytes(),n;same.append(pin(S/n))
(O/'result.json').write_text(json.dumps(dict(passed=True,scope='Source-only projection;extra CPU size reads are explicit,not instruction equivalence or hardware acceptance',native_source_checks=rows,unchanged=same,tool=pin(Path(__file__)),base_projection_tool=pin(tool),native_capacity_unchanged=True,native_return_lifetime_and_operational_call_chain_preserved=True,phone_access=False,hardware_qualified=False),indent=2)+'\n');print('PASS262 source projection;real native capacity/returns/lifetime unchanged,CPU diagnostics explicit')
