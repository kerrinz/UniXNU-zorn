#!/usr/bin/env python3
"""Fail closed on stale progress objects, mismatched linked code or menu."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import tomllib
import types

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT/'UniXNU/out/zorn/tree'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paired_relocations(raw):
    """Validate the SDK's ADDEND+BRANCH26/PAGE21/PAGEOFF12 record form."""
    result=[];i=0
    while i<len(raw):
        item=dict(raw[i]);i+=1;addend=0
        if item['type']==10:
            if item['external'] or item['pcrel'] or item['length']!=2 or i==len(raw):
                raise ValueError('malformed ARM64 ADDEND prefix')
            following=dict(raw[i]);i+=1
            if following['site']!=item['site'] or following['type'] not in (2,3,4) or not following['external'] or following['length']!=2:
                raise ValueError('invalid ARM64 ADDEND pair')
            if following['pcrel'] != (following['type'] in (2,3)):
                raise ValueError('invalid ARM64 ADDEND pair PC-relative flag')
            addend=item['symbol_value']
            if addend&(1<<23):addend-=1<<24
            item=following
        item['addend']=addend;result.append(item)
    return result


def verify_got_relaxation(original,linked,page_word,page_pc,target):
    """Only accept LDR(GOT)->ADD when its actual ADRP+ADD names the symbol."""
    if original&0xffc00000!=0xf9400000 or linked&0xffc00000!=0x91000000 or original&0x3ff!=linked&0x3ff:
        raise ValueError('unexpected GOT load relaxation')
    base=(original>>5)&31
    if page_word&0x9f000000!=0x90000000 or page_word&31!=base:
        raise ValueError('GOT relaxation has wrong ADRP base')
    immediate=((page_word>>29)&3)|(((page_word>>5)&0x7ffff)<<2)
    if immediate&(1<<20):immediate-=1<<21
    address=(page_pc&~0xfff)+(immediate<<12)+((linked>>10)&0xfff)
    if address!=target:raise ValueError('relaxed GOT target differs from actual symbol')


def parse_object(path):
    sys.path.insert(0,str(TREE/'kits/XnuPrelink'))
    from native_prelink import macho
    data=path.read_bytes();image=macho(data)
    sections=[sec for seg in image['segments'] for sec in seg['sections']]
    text=next(sec for sec in sections if sec['name']=='__text')
    at=next(at for cmd,at,_ in image['commands'] if cmd==2)
    offset,count,strings,_=struct.unpack_from('<4I',data,at+8)
    symbols=[];functions={}
    for i in range(count):
        ix,kind,sect,_,value=struct.unpack_from('<IBBHQ',data,offset+i*16)
        name=data[strings+ix:data.index(b'\0',strings+ix)].decode()
        symbols.append(name)
        if not kind&0xe0 and kind&0xe==0xe and sect==sections.index(text)+1 and name.startswith('_'):
            functions[name]=value
    relocs=[]
    offset,count=struct.unpack_from('<II',data,text['command_offset']+56)
    for i in range(count):
        site,bits=struct.unpack_from('<iI',data,offset+i*8)
        relocs.append(dict(site=site,type=bits>>28,length=(bits>>25)&3,pcrel=bool(bits&(1<<24)),symbol_value=bits&0xffffff,
                           external=bool(bits&(1<<27)),name=symbols[bits&0xffffff] if bits&(1<<27) else None))
    return data,text,functions,paired_relocations(relocs)


def verify_menu(text):
    entries=tomllib.loads(text)['entry'];xnu=[e for e in entries if e.get('type')=='xnu']
    if len(xnu)!=1:raise ValueError('expected exactly one XNU entry')
    tokens=xnu[0]['args'].split()
    required=['zorn_display_progress=1','zorn_touch_trace=1','zorn_touch=6',
        'zorn_smp_preflight=8','zorn_smp_continue=1','zorn_smp_root_publish=1',
        'cpus=8','zorn_data_store=2','zorn_data_retained=1','zorn_brightness=3',
        'zorn_gui_watch=1','zorn_wdt=1','sheng-vsync=60','offline-legacy-cpu-present=1']
    for token in required:
        key=token.split('=')[0]+'='
        if [t for t in tokens if t.startswith(key)] != [token]:
            raise ValueError('missing/duplicate/conflicting menu token: '+key)
    if any(t.startswith(('zorn_gui_stack=','zorn_gui_kstack=','zorn_gui_krun=','zorn_smp_stop=')) for t in tokens):
        raise ValueError('CPU0 sampler or stop leaked into eight-core observation')
    return tokens


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel',type=Path,default=ROOT/'UniXNU/out/zorn/kernel/kernel.macho')
    p.add_argument('--payload',action='store_true')
    p.add_argument('--output',type=Path,default=ROOT/'out/zorn/display-progress/linked-audit.json')
    a=p.parse_args();a.output.unlink(missing_ok=True)
    sys.path.insert(0,str(TREE/'kits/XnuPrelink'))
    from native_prelink import macho,backed_offset
    blob=a.kernel.read_bytes();image=macho(blob)
    symbols={n:int(pc,16) for pc,n in re.findall(r'^([0-9a-f]+)\s+\S\s+(\S+)$',subprocess.check_output(['xcrun','nm','-n',str(a.kernel)],text=True),re.M)}
    required=['_zorn_display_progress_configure','_zorn_display_progress_overlay',
              '_native_legacy_retirement_observed','_native_legacy_vsync_observed']
    if any(n not in symbols for n in required):raise ValueError('kernel lacks actual progress functions')
    display_report=json.loads((TREE/'build/native-legacy-display/build-report.json').read_text())
    for path,expected in display_report['source_sha256'].items():
        if sha(Path(path))!=expected:raise ValueError('display source differs from compiled report: '+path)
    if sha(TREE/'build/native-legacy-display/libNativeLegacyDisplay.late.a')!=display_report['archive_sha256']:
        raise ValueError('compiled display archive changed')
    probe=TREE/'build/native-legacy-display/ZornDisplayProbe.o'
    ufs=TREE/'build/zorn-ufs/ZornUfsRead.o'
    with tempfile.TemporaryDirectory(prefix='progress-linked-',dir=ROOT/'out/zorn') as temp:
        temp=Path(temp)
        builder=ROOT/'UniXNU-zorn/scripts/build-zorn-display.py'
        fn=next(n for n in ast.parse(builder.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='compile_source')
        def require(ok,msg):
            if not ok:raise ValueError(msg)
        env=dict(json=json,subprocess=subprocess,ROOT=TREE,OUT=TREE/'build/native-legacy-display',touch_runtime=True,require=require)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(builder),'exec'),env)
        env['compile_source'](ROOT/'UniXNU-zorn/native/display/ZornDisplayProbe.cpp',temp/'ZornDisplayProbe.o')
        builder=ROOT/'UniXNU-zorn/scripts/build-zorn-ufs.py';part=[];started=False
        for stmt in ast.parse(builder.read_text()).body:
            if isinstance(stmt,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='includes' for n in stmt.targets):started=True
            if started:
                if isinstance(stmt,ast.Expr) and isinstance(stmt.value,ast.Call) and isinstance(stmt.value.func,ast.Name) and stmt.value.func.id=='print':break
                part.append(stmt)
        env=dict(TREE=TREE,SOURCE=ROOT/'UniXNU-zorn/native/ufs-read',HEADERS=TREE/'build/xnu/ios-obj/EXPORT_HDRS',
            OBJDIR=TREE/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT',obj=temp/'ZornUfsRead.o',
            clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++',
            os=types.SimpleNamespace(environ=dict(os.environ,UNIXNU_ZORN_SMP='8',UNIXNU_ZORN_DATA_PROFILE='8g',UNIXNU_ZORN_TOUCH_RUNTIME='1')))
        exec(compile(ast.fix_missing_locations(ast.Module(body=part,type_ignores=[])),str(builder),'exec'),env)
        subprocess.run(env['command'],cwd=TREE,check=True,capture_output=True)
        object_hashes={}
        for obj in [probe,ufs]:
            fresh=temp/obj.name
            if sha(obj)!=sha(fresh):raise ValueError('independent compilation differs from '+str(obj))
            object_hashes[obj.name]=sha(obj)

    matched=[];call_edges=[];relaxations=[]
    # Compare real code, retaining opcodes/registers in PAGE relocs and checking
    # actual B/BL operands. PAGE addresses remain the normal linker's contract.
    for obj in [probe,ufs,TREE/'build/native-legacy-display/NativeLegacyDisplay.o']:
        data,text,functions,relocs=parse_object(obj)
        wanted=set(required)&functions.keys()
        for rel in relocs:
            if rel['external'] and rel['type']==2 and rel['name'] in required:
                candidates=[(v,n) for n,v in functions.items() if v<=text['va']+rel['site']]
                if not candidates:raise ValueError('call lacks object function boundary')
                caller=max(candidates)[1];wanted.add(caller);call_edges.append((obj.name,caller,rel['name']))
        for name in sorted(wanted):
            if name not in symbols:raise ValueError('linked function missing: '+name)
            lo=functions[name];hi=min([v for v in functions.values() if v>lo]+[text['va']+text['size']])
            original=data[text['fileoff']+lo-text['va']:text['fileoff']+hi-text['va']]
            at=backed_offset(image['segments'],symbols[name],len(original),len(blob));linked=blob[at:at+len(original)]
            masks={};verified_words=set()
            for rel in relocs:
                site=rel['site']+text['va']-lo
                if not 0<=site<len(original):continue
                if rel['length']!=2 or site%4:raise ValueError('unsupported text relocation size')
                kind=rel['type']
                if kind==2:
                    mask=0xfc000000
                    if not rel['external'] or rel['name'] not in symbols:raise ValueError('unresolved branch target')
                    oldword=struct.unpack_from('<I',original,site)[0];word=struct.unpack_from('<I',linked,site)[0]
                    signed=lambda value: value-(1<<26) if value&(1<<25) else value
                    target=symbols[name]+site+signed(word&0x3ffffff)*4
                    expected=symbols[rel['name']]+signed(oldword&0x3ffffff)*4+rel['addend']
                    if target!=expected:raise ValueError('linked branch target mismatch')
                elif kind in (3,5):mask=0x9f00001f
                elif kind in (4,6):
                    oldword=struct.unpack_from('<I',original,site)[0];word=struct.unpack_from('<I',linked,site)[0]
                    if kind==6 and (oldword&0xffc003ff)!=(word&0xffc003ff):
                        candidates=[r for r in relocs if r['type']==5 and r['name']==rel['name'] and lo<=r['site']+text['va']<lo+site]
                        if not candidates or rel['name'] not in symbols:raise ValueError('GOT relaxation missing PAGE pair/symbol')
                        page=max(candidates,key=lambda r:r['site']);page_off=page['site']+text['va']-lo
                        pageword=struct.unpack_from('<I',linked,page_off)[0]
                        verify_got_relaxation(oldword,word,pageword,symbols[name]+page_off,symbols[rel['name']])
                        verified_words.add(site);relaxations.append(dict(function=name,offset=site,target=rel['name']))
                    mask=0xffc003ff
                else:raise ValueError('unsupported text relocation kind '+str(kind))
                masks[site]=mask
            if len(original)%4:raise ValueError('unaligned function span')
            for off in range(0,len(original),4):
                if off in verified_words:continue
                x=struct.unpack_from('<I',original,off)[0];y=struct.unpack_from('<I',linked,off)[0]
                if x&masks.get(off,0xffffffff)!=y&masks.get(off,0xffffffff):
                    raise ValueError('linked instruction differs from object: '+name+'+'+hex(off))
            matched.append(dict(object=obj.name,function=name,bytes=len(original),relocated_words=len(masks)))
    for target in required[:2]:
        if not any(obj=='ZornUfsRead.o' and callee==target for obj,caller,callee in call_edges):raise ValueError('UFS to progress call absent')
    for target in required[2:]:
        if not any(obj=='NativeLegacyDisplay.o' and 'NativeLegacyDisplay' in caller and callee==target for obj,caller,callee in call_edges):raise ValueError('backend callback call absent')
    plan=json.loads(a.kernel.with_suffix('.json').read_text())
    extent=next(e for e in plan['extents'] if e['module']=='com.apple.iokit.IOMobileGraphicsFamily' and e['segment']=='__TEXT_EXEC')
    offset=backed_offset(image['segments'],extent['va'],extent['size'],len(blob))
    original_family=hashlib.sha256(blob[offset:offset+extent['size']]).hexdigest()
    if original_family!='2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b':raise ValueError('original display family changed')
    result=dict(kernel_sha256=sha(a.kernel),independent_object_sha256=object_hashes,
        object_to_linked_code=matched,actual_call_edges=call_edges,
        verified_got_load_to_add_relaxations=relaxations,
        original_mobile_graphics_family_sha256=original_family,
        page_relocation_scope='opcode/register match; PAGE immediate addresses are not exhaustively re-proved',
        hardware_qualified=False)
    if a.payload:
        with tempfile.TemporaryDirectory(prefix='progress-payload-',dir=ROOT/'out/zorn') as temp:
            temp=Path(temp)
            for name in ['unixnu.toml','Payloads/kernel.macho','Payloads/kernel.macho.adt']:
                subprocess.run(['mcopy','-i',str(ROOT/'out/zorn/payload.img'),'::/EFI/UniXNU/'+name,str(temp/Path(name).name)],check=True,capture_output=True)
            tokens=verify_menu((temp/'unixnu.toml').read_text())
            if sha(temp/'kernel.macho')!=sha(a.kernel):raise ValueError('packed kernel mismatch')
            if sha(temp/'kernel.macho.adt')!=sha(ROOT/'out/zorn/payload-with-trustcache.adt'):raise ValueError('packed ADT mismatch')
            if sha(temp/'unixnu.toml')!=sha(ROOT/'out/zorn/payload-ramdata.toml'):raise ValueError('packed menu mismatch')
            result.update(packed_kernel_exact=True,packed_adt_exact=True,packed_menu_exact=True,
                display_progress_token_once=True,no_stack_samplers_or_stop=True,menu_tokens=tokens)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(kernel_sha256=result['kernel_sha256'],
        independently_compiled_objects=len(object_hashes),linked_functions_checked=len(matched),
        actual_call_edges=len(call_edges),verified_got_relaxations=len(relaxations),
        packed_payload_checked=a.payload,hardware_qualified=False)))


if __name__=='__main__':main()
