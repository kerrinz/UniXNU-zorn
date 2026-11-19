from pathlib import Path
import json,subprocess,hashlib,sys,os,struct
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D));from inspect_ios26_gpu_kernel266 import inspect_progress,FIELDS,INDICES
import argparse
parser=argparse.ArgumentParser(description='Actual CPU known-task wire formatter/decoder controls;explicit synthetic metadata,no phone IO')
parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--parent-wire',type=Path,required=True);parser.add_argument('--parent-tag',required=True);parser.add_argument('--tag',required=True);parser.add_argument('--program-tag',required=True);args=parser.parse_args()
S=args.source_root.resolve();O=args.out.resolve();O.mkdir();C=dict(tag=args.tag,program_tag=args.program_tag);PC=dict(tag=args.parent_tag);header=S/'ZornKnownTask266.h';pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());save=lambda p,d:Path(p).write_text(json.dumps(d,indent=2)+'\n')

import re
indices=tuple(int(x) for x in re.search(r'Indices266\[24\]=\{([^}]+)',header.read_text(),re.S)[1].replace('\n','').split(','));assert indices==INDICES
source=r'''
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cassert>
#include <initializer_list>
#include "ZornKnownTask266.h"
int main(int argc,char **argv){assert(argc==2);uint32_t actual[32]{};actual[0]=0;actual[1]=6;actual[2]=63;actual[4]=actual[5]=77;actual[6]=actual[7]=1;actual[13]=0x11223344;actual[14]=0x55667788;actual[15]=0xe843b26a;actual[16]=0xffffffff;actual[19]=actual[20]=2;actual[24]=127;char line[4096]="FIXTURE\r\n";unsigned used=9;const unsigned n=zorn_known_task_append266(line,3072,used,1,actual);assert(n&&n<3072&&!strstr(line,"11223344")&&!strstr(line,"55667788"));
 for(unsigned cap:{0u,1u,used,n-1,n,n+1,3072u}){char b[4096];memset(b,0x5a,sizeof(b));memcpy(b,"FIXTURE\r\n",used);char before[4096];memcpy(before,b,sizeof(b));const unsigned count=zorn_known_task_append266(b,cap,used,1,actual);assert((cap>n)==bool(count));for(unsigned i=cap;i<sizeof(b);++i)assert(b[i]==before[i]);}
 assert(!zorn_known_task_append266(nullptr,3072,used,1,actual)&&!zorn_known_task_append266(line,3072,1,1,actual)&&!zorn_known_task_append266(line,3072,used,2,actual));FILE*f=fopen(argv[1],"wb");assert(f&&fwrite(line,1,n,f)==n);fclose(f);puts("PASS266 actual selected-field formatter bounds,no IOVA/handle export;CPU scalar fixtures only");}
''';f=O/'actual-formatter.cpp';f.write_text(source);a=['/usr/bin/clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(S),str(f),'-o',str(O/'check')];r=subprocess.run(a,capture_output=True,text=True);save(O/'compile.json',dict(arguments=a,exit=r.returncode,stderr=r.stderr));assert not r.returncode,r.stderr;r=subprocess.run([str(O/'check'),str(O/'SYNTHETIC-formatter.bin')],capture_output=True,text=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0'});assert not r.returncode,r.stderr;print(r.stdout)
formatted=(O/'SYNTHETIC-formatter.bin').read_bytes();kt=formatted.split(b',kt=')[1].removesuffix(b'\r\n');good=[int(x,16) for x in kt.split(b'/')[1:]];assert len(good)==24
raw=args.parent_wire.read_bytes();from inspect_ios26_gpu_shot265 import inspect_progress as parent;frames=parent(raw,PC['tag'],C['program_tag'])['frames'];parts=[];at=0;ordinal=0
while at<len(raw):
 if raw[at:at+8]==b'K80SH265':
  n=struct.unpack_from('<I',raw,at+28)[0];p=raw[at:at+48+n];assert p[8:24]==bytes.fromhex(PC['tag']);parts.append(p[:8]+bytes.fromhex(C['tag'])+p[24:]);at+=48+n;continue
 end=raw.index(b'\r\n',at);line=raw[at:end+2].replace(PC['tag'].encode(),C['tag'].encode());ready=b',state=3,' in line
 # Parse the parent's actual typed state rather than guessing from text names.
 ready=frames[ordinal]['state']==3
 field=kt if ready else b'0/'+b'/'.join([b'00000000']*24);parts.append(line.replace(b',jl=',b',kt='+field+b',jl=',1));ordinal+=1;at=end+2
data=b''.join(parts);(O/'SYNTHETIC-current266.raw').write_bytes(data);result=inspect_progress(data,C['tag'],C['program_tag']);assert result['kernel_known_task_complete266'] and result['serial_shot265']['complete'] and not result['full_GPU_qualification'];controls=[]
# Genuine failed task metadata stays valid evidence of failure,never transport success masquerading as task completion.
for name,index,value in [('raw',0,0xe00002ca),('phase',1,4),('flags',2,55),('grant',3,1),('ring-write',5,78),('fence',6,0),('completed',7,2),('native-pending',8,1),('submit-pending',9,1),('vm-poison',10,1),('submit-poison',11,1),('device-ref',12,1),('CRC',13,0),('bad-byte',14,0),('expected-byte',15,255),('actual-byte',16,90),('table-release',18,1),('ring-busy',19,1<<23),('ring-status',20,2),('IO',21,1),('task-OOB',22,63),('task-release-raw',23,1)]:
 bad=good.copy();bad[index]=value;field=b'1/'+b'/'.join(f'{v:08x}'.encode() for v in bad);modified=data.replace(b',kt='+kt,b',kt='+field);d=inspect_progress(modified,C['tag'],C['program_tag']);assert d['transport_frames_valid'] and not d['kernel_known_task_complete266'] and not d['full_GPU_qualification'];controls.append(name+' retains failed evidence')
# The actual source idle predicate permits other busy-register bits and status1.
allow=good.copy();allow[19]=1;allow[20]=1;field=b'1/'+b'/'.join(f'{v:08x}'.encode() for v in allow);d=inspect_progress(data.replace(b',kt='+kt,b',kt='+field),C['tag'],C['program_tag']);assert d['kernel_known_task_complete266'];controls.append('actual source idle mask permits unrelated busy bits/status1')
for name,broken in [('missing',data.replace(b',kt='+kt,b'',1)),('duplicate',data.replace(b',kt='+kt,b',kt='+kt+b',kt='+kt,1)),('unavailable-state',data.replace(b',kt='+kt,b',kt=0/'+b'/'.join(kt.split(b'/')[1:]),1)),('record-mutation',data.replace(b',kt='+kt,b',kt='+kt.replace(b'e843b26a',b'e843b26b'),1))]:
 try:inspect_progress(broken,C['tag'],C['program_tag'])
 except ValueError:controls.append(name+' refused')
 else:raise AssertionError(name)
save(O/'result.json',dict(passed=True,tool=pin(__file__),header=pin(header),decoder=pin(D/'inspect_ios26_gpu_kernel266.py'),actual_parent_wire=pin(args.parent_wire),synthetic_fixture=pin(O/'SYNTHETIC-current266.raw'),synthetic_KT_values_and_retag_only_not_hardware=True,controls=controls,scalar_formatter_ASan_UBSan_pass=True,original_packet_pixel_data_retained=True,full_GPU_qualification=False,phone_access=False));shutil=None
print('PASS266 strict actual-field formatter/decoder;failed-task conditions never qualify,4malformed controls refuse;synthetic not hardware')
