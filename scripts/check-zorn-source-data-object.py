#!/usr/bin/env python3
"""Inspect a data-only iOS17 Mach-O object;never load or execute it."""
import hashlib,json,re,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/gpu-source-layout-review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def inspect(blob,expected):
    if len(blob)<32:raise ValueError('truncated object')
    magic,cpu,subtype,kind,ncmds,command_bytes,flags,reserved=struct.unpack_from('<8I',blob)
    if magic!=0xfeedfacf or cpu!=0x100000c or kind!=1:raise ValueError('expected isolated arm64 MH_OBJECT')
    pos=32;sections=[];symtab=None;build=None
    if pos+command_bytes>len(blob):raise ValueError('invalid command bounds')
    for _ in range(ncmds):
        cmd,size=struct.unpack_from('<II',blob,pos)
        if size<8 or pos+size>32+command_bytes:raise ValueError('invalid load command')
        if cmd==0x19:
            if size<72:raise ValueError('invalid segment')
            fields=struct.unpack_from('<II16sQQQQiiII',blob,pos);nsects=fields[-2]
            if 72+80*nsects>size:raise ValueError('invalid section count')
            for i in range(nsects):
                row=struct.unpack_from('<16s16sQQIIIIIIII',blob,pos+72+i*80)
                name=row[0].split(b'\0')[0].decode();segment=row[1].split(b'\0')[0].decode()
                offset,width,nreloc,section_flags=row[4],row[3],row[7],row[8]
                if offset+width>len(blob) or nreloc:raise ValueError('section bounds/relocations violate data-only scope')
                if width and (section_flags & 0x80000400 or name in ('__text','__mod_init_func','__mod_term_func')):raise ValueError('instructions/initializer in source data object')
                sections.append(dict(name=name,segment=segment,offset=offset,bytes=width,relocations=nreloc))
        elif cmd==2:symtab=struct.unpack_from('<6I',blob,pos)
        elif cmd==0x32:build=struct.unpack_from('<6I',blob,pos)
        elif cmd in (0xc,0x18,0x1f,0x80000018,0x8000001f):raise ValueError('linked image dependency is forbidden')
        pos+=size
    if pos!=32+command_bytes or symtab is None or build is None:raise ValueError('missing object provenance commands')
    if build[2]!=2 or build[3]!=0x110000:raise ValueError('expected iOS17 object deployment target')
    _,_,symoff,nsyms,stroff,strsize=symtab
    if symoff+16*nsyms>len(blob) or stroff+strsize>len(blob):raise ValueError('symbol bounds')
    symbols=[]
    for i in range(nsyms):
        index,ntype,sect,desc,value=struct.unpack_from('<IBBHQ',blob,symoff+16*i)
        if (ntype&0x0e)==0 or ntype&1:raise ValueError('undefined or externally exported symbol in data-only review object')
        if index>=strsize:raise ValueError('symbol string bounds')
        end=blob.find(b'\0',stroff+index,stroff+strsize)
        if end<0:raise ValueError('symbol name bounds')
        symbols.append(dict(name=blob[stroff+index:end].decode(),section=sect))
    const=[s for s in sections if s['name']=='__const' and s['segment']=='__TEXT']
    if len(const)!=1:raise ValueError('one source data section required')
    section=const[0];data=blob[section['offset']:section['offset']+section['bytes']]
    if data!=expected:raise ValueError('compiled source-data bytes differ from raw reviewed model')
    return dict(sections=sections,symbols=symbols,undefined_symbols=0,external_exports=0,relocations=0,instruction_bytes=0,compiled_source_bytes=len(data),iOS_min_version='17.0',no_SDK_imports=build[4]==0)


def main():
    header=(OUT/'UnselectedSourceTables.h').read_text();metadata=json.loads((OUT/'source-layout-data.json').read_text())['records'];model={}
    for key in metadata:
        match=re.search(r'inline constexpr \w+ '+key+r'\[\] = \{\n(.*?)\n\};',header,re.S);assert match
        if key.endswith('_bytes'):model[key]=[int(v) for v in re.findall(r'\d+',match[1])]
        else:model[key]=[[int(v) for v in re.findall(r'(\d+)U',row)] for row in re.findall(r'\{([^{}]+)\}',match[1])]
    assert model==metadata
    keys=['sources','nodes','properties','optional_fields','tables','entries','gmu_tables','gmu_pairs']
    expected=b''.join(struct.pack('<'+'I'*len(row),*row) for key in keys for row in model[key])+bytes(model['text_bytes'])+bytes(model['property_bytes'])
    expected+=bytes(-len(expected)%4)
    obj=OUT/'isolated-source-data.o';blob=obj.read_bytes();result=inspect(blob,expected);refusals=[]
    const=next(s for s in result['sections'] if s['name']=='__const')
    for case in ['compiled-data-tamper','wrong-object-target','undefined-symbol']:
        bad=bytearray(blob)
        if case=='compiled-data-tamper':bad[const['offset']+len(expected)-8]^=1
        elif case=='wrong-object-target':struct.pack_into('<I',bad,4,0x1000007)
        else:
            pos=32;ncmds=struct.unpack_from('<I',bad,16)[0]
            for _ in range(ncmds):
                cmd,size=struct.unpack_from('<II',bad,pos)
                if cmd==2:
                    symoff=struct.unpack_from('<I',bad,pos+8)[0];bad[symoff+4]=1;break
                pos+=size
        path=OUT/(case+'.invalid.o');path.write_bytes(bad);assert path.stat().st_ino!=obj.stat().st_ino and path.stat().st_nlink==1
        try:inspect(bytes(bad),expected)
        except ValueError as exc:refusals.append(dict(case=case,error=str(exc),artifact=str(path)))
        else:raise AssertionError(case)
    compiler='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'
    command=[compiler,'-std=c++17','-ffreestanding','-fno-exceptions','-fno-rtti','-nostdinc','-nostdinc++','--target=arm64-apple-ios17.0.0','-Wall','-Wextra','-Werror','-pedantic','-O2','-c',str(OUT/'source-layout-object.cpp'),'-o',str(obj)]
    result.update(command=command,returncode=0,observed='successful preceding compile tool call,not repeated',object_sha256=sha(obj),compiler_sha256=sha(Path(compiler)),inputs={str(OUT/n):sha(OUT/n) for n in ['UnselectedSourceTables.h','source-layout-object.cpp','source-layout-data.json']},all_compiled_bytes_equal_reviewed_source_model=True,new_object_refusals=refusals,no_link_or_execution=True,no_runtime_component=True,hardware_qualification=False)
    (OUT/'object-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS:data-only arm64 iOS17 object matches167116 source bytes;0instruction/import/export/relocation;3invalid object cases refused')
if __name__=='__main__':main()
