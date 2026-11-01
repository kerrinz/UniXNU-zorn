"""Fail-closed Mach-O comparison helpers for the CPU-only GPU memory profile.

Reuse the qualified ADDEND/GOT rules without changing the older auditors.
Annotation IOKit objects are disassembly/ABI inputs, never linked or executed.
"""
import hashlib,importlib.util,json,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('zorn_gpu_reloc_base',Path(__file__).with_name('audit-zorn-cpu-active.py'))
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
sys.path.insert(0,str(ROOT/'UniXNU/kits/XnuPrelink'))
from native_prelink import macho,backed_offset
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(v,message):
 if not v:raise ValueError(message)

def symbols(data,image):
 at=next(at for c,at,_ in image['commands'] if c==2);sy,n,st,_=struct.unpack_from('<4I',data,at+8);out=[]
 for i in range(n):
  ix,kind,sec,desc,va=struct.unpack_from('<IBBHQ',data,sy+i*16)
  out.append(dict(name=data[st+ix:data.index(b'\0',st+ix)].decode(),va=va,kind=kind,section=sec))
 return out

class Kernel:
 def __init__(self,path):
  self.path=Path(path);self.data=self.path.read_bytes();self.image=macho(self.data);self.names={}
  for s in symbols(self.data,self.image):
   if not s['kind']&0xe0 and s['kind']&0xe in (2,0xe) and s['name'].startswith('_'):
    self.names.setdefault(s['name'],set()).add(s['va'])
 def address(self,name):
  choices=self.names.get(name,set());require(len(choices)==1,'missing/ambiguous linked symbol '+name);return next(iter(choices))
 def read(self,va,size):
  at=backed_offset(self.image['segments'],va,size,len(self.data));return self.data[at:at+size]
 def section(self,va,size):
  choices=[(g,s) for g in self.image['segments'] for s in g['sections'] if s['va']<=va and va+size<=s['va']+s['size']]
  require(len(choices)==1,'linked range not in exactly one section');return choices[0]

def vtable(path,name):
 data=Path(path).read_bytes();image=macho(data);syms=symbols(data,image)
 table=next(s['va'] for s in syms if s['name']==name);relocs={}
 for seg in image['segments']:
  for sec in seg['sections']:
   if sec['va']<=table<sec['va']+sec['size']:
    at,count=struct.unpack_from('<2I',data,sec['command_offset']+56)
    for i in range(count):
     site,bits=struct.unpack_from('<iI',data,at+i*8)
     if bits>>28==0 and bits>>27&1 and (bits>>25&3)==3:relocs[sec['va']+site]=syms[bits&0xffffff]['name']
 entries=[]
 while table+16+len(entries)*8 in relocs:entries.append(relocs[table+16+len(entries)*8])
 require(entries,'annotation vtable empty');return entries

def compare_vtable(kernel,obj,name,count):
 expected=vtable(obj,name);require(len(expected)==count,'annotation vtable slot count differs')
 addr=kernel.address(name)+16;actual=struct.unpack('<'+'Q'*count,kernel.read(addr,8*count))
 for i,(symbol,value) in enumerate(zip(expected,actual)):
  require(kernel.address(symbol)==value,'original virtual ABI mismatch '+name+' slot'+str(i)+' '+symbol)
 return dict(table=name,slots=count,methods=expected,actual_pointer_sha256=hashlib.sha256(kernel.read(addr,8*count)).hexdigest())

def code_compare(kernel,obj,wanted=None):
 # All new component functions; explicit transitive consumers in BSD/UFS/CPU.
 data,text,functions,relocs=base.parse_object(obj);matched=[];edges=[];relaxations=[];callbacks=[]
 image=macho(data);sections=[sec for seg in image['segments'] for sec in seg['sections']]
 critical=set()
 for entry in symbols(data,image):
  if entry['kind']&0xe0 or not entry['section']:continue
  sec=sections[entry['section']-1]
  if struct.unpack_from('<I',data,sec['command_offset']+64)[0]&255!=1:continue
  if Path(obj).name=='ZornGpuOwnedRuntime.o' or 'gGpuMemoryWire' in entry['name']:
   if entry['name'].startswith('_'):critical.add(entry['name'])

 wanted=set(functions) if wanted is None else set(wanted)
 for name in sorted(wanted):
  require(name in functions,'object function absent '+name)
  lo=functions[name];hi=min([v for v in functions.values() if v>lo]+[text['va']+text['size']])
  original=data[text['fileoff']+lo-text['va']:text['fileoff']+hi-text['va']]
  pc=kernel.address(name);linked=kernel.read(pc,len(original));masks={};verified=set()
  for rel in relocs:
   site=rel['site']+text['va']-lo
   if not 0<=site<len(original):continue
   require(rel['length']==2 and site%4==0,'unsupported text relocation size')
   kind=rel['type'];x=struct.unpack_from('<I',original,site)[0];y=struct.unpack_from('<I',linked,site)[0]
   if kind==2:
    require(rel['external'],'nonexternal branch relocation')
    signed=lambda n:n-(1<<26) if n&(1<<25) else n
    got=pc+site+signed(y&0x3ffffff)*4
    expected=kernel.address(rel['name'])+signed(x&0x3ffffff)*4+rel['addend']
    require(got==expected,'actual B/BL target differs '+name+' -> '+rel['name'])
    masks[site]=0xfc000000;edges.append(dict(object=Path(obj).name,caller=name,callee=rel['name'],offset=site,address=got))
   elif kind in (3,5):masks[site]=0x9f00001f
   elif kind in (4,6):
    masks[site]=0xffc003ff
    if kind==6 and x&0xffc003ff!=y&0xffc003ff:
     pairs=[r for r in relocs if r['type']==5 and r['name']==rel['name'] and lo<=r['site']+text['va']<lo+site]
     require(pairs,'GOT relaxation missing PAGE pair');page=max(pairs,key=lambda r:r['site']);off=page['site']+text['va']-lo
     base.verify_got_relaxation(x,y,struct.unpack_from('<I',linked,off)[0],pc+off,kernel.address(rel['name']))
     verified.add(site);relaxations.append(dict(function=name,offset=site,symbol=rel['name']))
    # Separately bind actual callback and owned-storage addresses; other
    # ordinary PAGE operands retain the explicit normal-linker boundary.
    if kind==4 and rel['name'] in set(functions)|critical:
     pairs=[r for r in relocs if r['type']==3 and r['name']==rel['name'] and lo<=r['site']+text['va']<lo+site and struct.unpack_from('<I',original,r['site']+text['va']-lo)[0]&31==(y>>5&31)]
     require(pairs,'critical PAGE pair absent');page=max(pairs,key=lambda r:r['site']);off=page['site']+text['va']-lo
     adrp=struct.unpack_from('<I',linked,off)[0];reg=(y>>5)&31
     require(adrp&0x9f00001f==0x90000000|reg,'critical ADRP register differs '+name+' -> '+rel['name'])
     imm=((adrp>>29)&3)|((adrp>>5&0x7ffff)<<2);imm-=1<<21 if imm&(1<<20) else 0
     if y&0xffc00000==0x91000000:offset=y>>10&4095
     elif y&0x3b000000==0x39000000 and not y&(1<<26):offset=(y>>10&4095)<<(y>>30&3)
     else:raise ValueError('unmodelled critical PAGEOFF opcode')
     got=((pc+off)&~4095)+(imm<<12)+offset
     require(got==kernel.address(rel['name'])+rel['addend'],'critical PAGE target differs '+name+' -> '+rel['name'])
     callbacks.append(dict(function=name,callback=rel['name'],kind='owned-BSS' if rel['name'] in critical else 'function-pointer',address=got))
   else:raise ValueError('unsupported text relocation kind '+str(kind))
  require(len(original)%4==0,'unaligned function span')
  for off in range(0,len(original),4):
   if off in verified:continue
   x=struct.unpack_from('<I',original,off)[0];y=struct.unpack_from('<I',linked,off)[0];mask=masks.get(off,0xffffffff)
   require(x&mask==y&mask,'linked instruction differs '+name+'+'+hex(off))
  matched.append(dict(object=Path(obj).name,function=name,address=pc,bytes=len(original),relocated_words=len(masks)))
 return matched,edges,relaxations,callbacks

def call_consumers(obj,targets):
 data,text,functions,relocs=base.parse_object(obj);wanted=set();found=[]
 for rel in relocs:
  if rel['type']==2 and rel['external'] and rel['name'] in targets:
   choices=[(v,n) for n,v in functions.items() if v<=text['va']+rel['site']]
   require(choices,'consumer function boundary absent');wanted.add(max(choices)[1]);found.append(rel['name'])
 require(set(found)==set(targets),'consumer edge missing '+str(set(targets)-set(found)))
 return wanted

def bss_zero(kernel,obj,names):
 data=Path(obj).read_bytes();image=macho(data);syms=symbols(data,image);sections=[s for g in image['segments'] for s in g['sections']];rows=[]
 for name,expected in names.items():
  s=next(s for s in syms if s['name']==name);sec=sections[s['section']-1]
  require(struct.unpack_from('<I',data,sec['command_offset']+64)[0]&255==1,'owned object is not zero-init BSS '+name)
  next_va=min([t['va'] for t in syms if t['section']==s['section'] and t['va']>s['va']]+[sec['va']+sec['size']])
  require(next_va-s['va']>=expected,'BSS symbol capacity too small '+name)
  va=kernel.address(name);g,c=kernel.section(va,expected);require(g['initprot']&2,'owned storage is not writable')
  if va+expected<=g['va']+g['filesize']:require(not any(kernel.read(va,expected)),'owned BSS is not initially zero')
  else:require(va>=g['va']+g['filesize'],'mixed file/zerofill range unsupported')
  rows.append(dict(name=name,address=va,minimum_bytes=expected,section=c['name']))
 return rows

def indirect_memory_calls(obj):
 # Recognize the actual target register's last definition and its vptr load;
 # do not infer a slot merely from the nearest arbitrary LDR instruction.
 output=subprocess.check_output(['xcrun','llvm-objdump','--disassemble',str(obj)],text=True)
 instructions=[];rows=[];allowed={5,19,22,27,28,41}
 for line in output.splitlines():
  m=__import__('re').match(r'^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\w+)\s*(.*)',line)
  if m:instructions.append((int(m[1],16),m[2],m[3].split(';')[0].strip()))
 def definition_before(index,reg):
  for j in range(index-1,max(-1,index-17),-1):
   pc,op,args=instructions[j]
   if op in ('bl','blr'):raise ValueError('unmodelled intervening call at virtual site')
   # Stores, comparisons and branches have no first-register destination.
   if op.startswith(('st','b.')) or op in ('cmp','cmn','tst','b','cbz','cbnz','tbz','tbnz','ret','nop'):continue
   first=args.split(',',1)[0].strip()
   if first in ('x'+str(reg),'w'+str(reg)):return j,(pc,op,args)
  raise ValueError('virtual target register definition not found')
 re=__import__('re')
 for i,(pc,op,args) in enumerate(instructions):
  if op not in ('blr','br'):continue
  m=re.fullmatch(r'x(\d+)',args);require(m,'unmodelled indirect operand');reg=int(m[1]);j,(_,load,operands)=definition_before(i,reg)
  m=re.fullmatch(r'x(\d+), \[x(\d+), #(0x[0-9a-f]+|\d+)\]',operands)
  require(load=='ldr' and m and int(m[1])==reg and int(m[2])==reg,'indirect memory call is not a recognized vtable method load')
  byte_offset=int(m[3],0);require(byte_offset%8==0 and byte_offset//8 in allowed,'unqualified memory virtual slot')
  _,(_,vload,voperands)=definition_before(j,reg)
  require(vload=='ldr' and re.fullmatch(r'x'+str(reg)+r', \[x\d+\]',voperands),'virtual base is not an object vptr load')
  rows.append(dict(offset=pc,slot=byte_offset//8,target_register=reg))
 require({r['slot'] for r in rows}==allowed,'not all six memory ABI operations found in actual object')
 return rows
