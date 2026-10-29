#!/usr/bin/env python3
"""Exact 21H461 IOHIDDevice adapter, adapted from UniXNU build-sheng-hid-input.py."""
import hashlib,json,struct

def build(ROOT,DEVICE,OUT,plan,read,names,compile_source,run,require,macho,code,llvm,sdk):
    extent=next(e for e in plan['extents'] if e['module']=='com.apple.iokit.IOHIDFamily' and e['segment']=='__TEXT_EXEC')
    require(hashlib.sha256(read(extent['va'],extent['size'])).hexdigest()==plan['original_executable_sha256']['com.apple.iokit.IOHIDFamily']=='7e4c5104814f2e773d5be13d092dec53ee44ba5a61a81264b229780406e86b72','Exact original 21H461 HID instructions')
    vptr=0xfffffff005d045c0;methods=struct.unpack('<207Q',read(vptr,207*8));base=struct.unpack('<168Q',read(names['__ZTV9IOService']+16,168*8))
    require([i for i in range(168) if methods[i]!=base[i]]==[0,1,7,12,14,21,23,76,81,82,86,87,91,92,93,101,132,140],'Original HID overrides native base at exact slots')
    require([i for i,a in enumerate(methods) if a==names['___cxa_pure_virtual']]==[180] and all(methods),'Original 207-slot abstract HID device')
    require(read(0xfffffff004ad94f8,0x20)==bytes.fromhex('fd7bbfa9fd0300912bd90094489100f008011791080000f9fd7bc1a8c0035fd6'),'Original HID protected constructor')
    require(struct.unpack('<Q',read(0xfffffff005d00f10,8))[0]==names['__ZN9IOServiceC2EPK11OSMetaClass'] and struct.unpack('<Q',read(0xfffffff005d00f18,8))[0]==names['__ZN9IOServiceD2Ev'],'Original HID constructor/destructor thunks')
    require(read(0xfffffff004ad9aec,0x34)==bytes.fromhex('680240f908a142f9e00313aae10314aa00013fd6680240f9603d003608d142f9e1630091e00313aa00013fd6a02d0035e00f40f9'),'Actual descriptor signature and slot')
    require(methods[181]==0xfffffff004add0c4 and read(0xfffffff004add110,28)==bytes.fromhex('680240f9081543f9e00313aae20316aae30315aae40314aa00013fd6'),'Actual handleReport forwarding signature')
    header='''// Generated for original 21H461 IOHIDDevice; opaque private storage only.
#pragma once
#include <IOKit/IOService.h>
#include <IOKit/IOMemoryDescriptor.h>
class IOHIDDevice : public IOService {
 OSDeclareAbstractStructors(IOHIDDevice)
 unsigned char originalPrivate[0xd0-sizeof(IOService)];
public:
 using IOService::setProperty;
 IOReturn Dispatch(IORPC) override;
 void free() override;
 bool init(OSDictionary *properties=nullptr) override;
 bool setProperty(const OSSymbol *,OSObject *) override;
 bool willTerminate(IOService *,IOOptionBits) override;
 IOReturn configureReport(IOReportChannelList *,IOReportConfigureAction,void *,void *) override;
 IOReturn updateReport(IOReportChannelList *,IOReportUpdateAction,void *,void *) override;
 bool start(IOService *) override;
 void stop(IOService *) override;
 bool handleOpen(IOService *,IOOptionBits,void *) override;
 void handleClose(IOService *,IOOptionBits) override;
 bool handleIsOpen(const IOService *) const override;
 bool matchPropertyTable(OSDictionary *,SInt32 *) override;
 IOReturn message(UInt32,IOService *,void *) override;
 IOReturn newUserClient(task_t,void *,UInt32,OSDictionary *,IOUserClient **) override;
'''
    for i in range(168,207):
        if i==171:header+=' virtual OSString *newTransportString() const;\n'
        elif i==173:header+=' virtual OSString *newProductString() const;\n'
        elif i==180:header+=' virtual IOReturn newReportDescriptor(IOMemoryDescriptor **) const=0;\n'
        elif i==181:header+=' virtual IOReturn handleReport(IOMemoryDescriptor *,unsigned,IOOptionBits);\n'
        else:header+=f' virtual __attribute__((deprecated("Unqualified prototype: never call"))) void opaque{i}();\n'
    header+='};\nstatic_assert(sizeof(IOHIDDevice)==0xd0,"Original HID object extent");\n'
    (OUT/'OriginalHidDeviceABI.h').write_text(header)
    driver_vptr=0xfffffff005d06a68;event_vptr=0xfffffff005d07318
    require(read(0xfffffff004af09b0,32)==bytes.fromhex('fd7bbfa9fd0300918fe9ff97a89000d008a12991080000f9fd7bc1a8c0035fd6'),'Actual original EventDriver constructor and vptr')
    require(read(0xfffffff004afb124,32)==bytes.fromhex('fd7bbfa9fd030091f95100946890009008610c91080000f9fd7bc1a8c0035fd6'),'Actual original Event constructor and vptr')
    driver_methods=struct.unpack('<220Q',read(driver_vptr,220*8));event_methods=struct.unpack('<37Q',read(event_vptr,37*8))
    require(all(driver_methods) and all(event_methods) and read(driver_vptr+220*8,24)==bytes(24) and read(event_vptr+37*8,24)==bytes(24),'Exact EventDriver220 and Event37 method boundaries')
    require(driver_methods[198]==0xfffffff004aface8 and read(driver_methods[198],16)==bytes.fromhex('f85fbca9f65701a9f44f02a9fd7b03a9'),'Original dispatchEvent boundary')
    require({i:event_methods[i] for i in (18,23,24,25)}=={18:0xfffffff004afcf90,23:0xfffffff004afcfb8,24:0xfffffff004afefdc,25:0xfffffff004afe4c4},'Actual Event type/integer/set/fixed slots')
    require(read(event_methods[18],12)==bytes.fromhex('080840f9000540b9c0035fd6'),'Actual Event data pointer/type fields')
    # The normal matching personality may instantiate this original subclass,
    # not the IOHIDEventDriver base. It overrides dispatchEvent; retain its
    # own path rather than calling the base implementation behind its back.
    user_vptr=0xfffffff005d012c0
    user_methods=struct.unpack('<220Q',read(user_vptr,220*8))
    require(all(user_methods) and read(user_vptr+220*8,24)==bytes(24),'Exact original AppleUserHIDEventService method extent')
    require(user_methods[7]==0xfffffff004acb110 and read(user_methods[7],12)==bytes.fromhex('c00001f000803991c0035fd6'),'Actual AppleUserHIDEventService metaclass getter')
    require(read(0xfffffff0042e6eb0,25)==b'AppleUserHIDEventService\0','Actual original subclass name')
    require(read(0xfffffff004acd934,32)==bytes.fromhex('c00001b000803991c1c0ffb021c03a91c20001d042c00b910322805227070194'),'Actual subclass metaclass, parent IOHIDEventDriver and size0x110')
    require(user_methods[198]==0xfffffff004acc010 and read(user_methods[198],16)==bytes.fromhex('ff4301d1f65702a9f44f03a9fd7b04a9'),'Actual subclass dispatch override')
    append=event_methods[15];append_end=min(v for v in event_methods if v>append)
    require(0<append_end-append<=2048,'Bounded original appendChild body')
    append_words=struct.unpack('<'+'I'*((append_end-append)//4),read(append,append_end-append))
    require(any(w&0xffc00000==0xf9400000 and (w>>10)&4095==3 for w in append_words),'Actual appendChild reads children at24')
    event_header='''// Generated from individually checked original21H461 constructors/tables.
#pragma once
#include <stdint.h>
namespace ZornEventABI {
enum {DriverSlots=220};
static constexpr uintptr_t DriverVptr=0xfffffff005d06a68ULL,EventVptr=0xfffffff005d07318ULL,Dispatch=0xfffffff004aface8ULL;
static constexpr uintptr_t DriverMethods[DriverSlots]={
'''+','.join(hex(v)+'ULL' for v in driver_methods)+'''};
static constexpr uintptr_t UserDriverVptr=0xfffffff005d012c0ULL;
static constexpr uintptr_t UserDriverMethods[DriverSlots]={
'''+','.join(hex(v)+'ULL' for v in user_methods)+'};\n}\n'
    (OUT/'OriginalHidEventABI.h').write_text(event_header)
    source=DEVICE/'native/display/ZornTouchHid.cpp';obj=OUT/'ZornTouchHid.o';compile_source(source,obj)
    raw=obj.read_bytes();image=macho(raw);st=next(p for c,p,_ in image['commands'] if c==2);sy,count,strings,_=struct.unpack_from('<4I',raw,st+8);symbols=[]
    for i in range(count):
        ix,kind,section,_,va=struct.unpack_from('<IBBHQ',raw,sy+i*16);symbols.append((raw[strings+ix:raw.index(b'\0',strings+ix)].decode(),va,kind))
    table=next(v for n,v,_ in symbols if n=='__ZTV12ZornTouchHid');rel={}
    for segment in image['segments']:
        for sec in segment['sections']:
            if sec['va']<=table<sec['va']+sec['size']:
                ro,rc=struct.unpack_from('<2I',raw,sec['command_offset']+56)
                for i in range(rc):
                    off,bits=struct.unpack_from('<2I',raw,ro+i*8)
                    if bits>>27&1 and bits>>28==0 and bits>>25&3==3:rel[sec['va']+off]=symbols[bits&0xffffff][0]
    compiled=[rel.get(table+16+i*8) for i in range(207)];require(all(compiled) and table+16+207*8 not in rel,'Exact owned 207-slot HID table')
    bindings={'__ZN11IOHIDDeviceC2EPK11OSMetaClass':0xfffffff004ad94f8,'__ZN11IOHIDDeviceD2Ev':0xfffffff004ad9518,'__ZN11IOHIDDevice10gMetaClassE':0xfffffff006ae6fa0,'__ZTV11IOHIDDevice':vptr-16};owned=[]
    for i,name in enumerate(compiled):
        if name.startswith(('__ZN12ZornTouchHid','__ZNK12ZornTouchHid')):owned.append(i)
        elif '11IOHIDDevice' in name:bindings[name]=methods[i]
        else:require(i<168 and names.get(name)==methods[i],'Actual HID inherited native method '+str(i))
    require(owned==[0,1,7,14,86,87,111,171,173,180],'Only qualified HID overrides')
    undefined={n for n,_,kind in symbols if kind==1 and '11IOHIDDevice' in n};require(undefined==set(bindings),'Every original HID import qualified')
    asm=OUT/'hid-original-bindings.S';asm.write_text(''.join(f'.globl {n}\n.set {n}, {a:#x}\n' for n,a in sorted(bindings.items())))
    binding=OUT/'hid-original-bindings.o';run(['xcrun','clang','-target','arm64-apple-ios17.0','-isysroot',sdk,'-c',asm,'-o',binding])
    late=OUT/'ZornTouchHid.late.o';run([llvm/'llvm-objcopy','--remove-section=__DATA,__mod_init_func','--globalize-symbol=__GLOBAL__sub_I_ZornTouchHid.cpp',obj,late]);require(code(raw,image)==code(late.read_bytes(),macho(late.read_bytes())),'HID source instructions unchanged by deferred initialization')
    report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'original_hid_text_sha256':plan['original_executable_sha256']['com.apple.iokit.IOHIDFamily'],'original_slots':207,'instance_size':208,'owned_slots':owned,'bindings':bindings,'runtime_qualified':False}
    report['edge_event_abi']={'driver_vptr':hex(driver_vptr),'driver_slots':220,'driver_instance_size':264,'event_vptr':hex(event_vptr),'event_slots':37,'event_instance_size':80,'dispatch_slot':198,'dispatch_address':hex(driver_methods[198]),'event_methods':{str(i):hex(event_methods[i]) for i in (18,23,24,25)},'children_offset':24,'original_constructors_tables_and_methods_checked':True,'hardware_qualified':False}
    report['edge_event_abi']['qualified_subclass']={'name':'AppleUserHIDEventService','vptr':hex(user_vptr),'instance_size':0x110,'dispatch_address':hex(user_methods[198]),'parent_metaclass':hex(0xfffffff006ae72f0),'full_table_checked':True}
    (OUT/'touch-hid-abi-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return [late,binding]
