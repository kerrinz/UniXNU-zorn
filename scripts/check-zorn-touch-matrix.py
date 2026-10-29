#!/usr/bin/env python3
"""Check actual per-channel baseline/pair encoding across native/host boundaries."""
from pathlib import Path
import hashlib,json,subprocess,importlib.util,struct
root=Path(__file__).resolve().parents[2];out=root/'out/zorn/touch';header=root/'UniXNU-zorn/native/display/ZornTouchMatrix.h'
test=r'''
#include <cassert>
#include <cstdio>
#include "ZornTouchMatrix.h"
#include "ZornTouchRawLog.h"
int main(int argc,char **argv) {
 assert(argc==2);uint8_t raw[3120]={0xa5,0x5f};uint32_t sum[720]={};
 for(unsigned i=0;i<720;++i){unsigned v=10000+i%100;raw[64+i*2]=v>>8;raw[65+i*2]=v;}
 for(unsigned i=0;i<8;++i)assert(ZornMatrix::addBaseline(raw,sum));
 uint8_t copy[3120];memcpy(copy,raw,3120);
 assert(!ZornMatrix::packPair(copy,sum,3)&&!memcmp(raw,copy,3120));
 assert(!ZornMatrix::packPair(copy,sum,9)&&!memcmp(raw,copy,3120));
 raw[0]^=1;assert(!ZornMatrix::addBaseline(raw,sum));raw[0]^=1;
 raw[64]=0x80;assert(!ZornMatrix::addBaseline(raw,sum));memcpy(raw,copy,3120);
 unsigned index=30*18+4,value=ZornMatrix::big16(raw+64+index*2)+1000;
 raw[64+index*2]=value>>8;raw[65+index*2]=value;
 assert(ZornMatrix::packPair(raw,sum,8));
 for(unsigned i=0;i<720;++i){assert(ZornMatrix::big16(raw+64+2*i)==10000+i%100);assert(ZornMatrix::big16(raw+1504+2*i)==10000+i%100+(i==index?1000:0));}
 assert(!memcmp(raw+2944,"ZORNCAL1",8));
 uint8_t block[4096];assert(ZornTouchLog::install(block,4096,raw,3120,1));
 FILE *f=fopen(argv[1],"wb");assert(f);assert(fwrite(block,1,4096,f)==4096);assert(!fclose(f));
}
'''
(out/'matrix-check.cpp').write_text(test)
subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-fsanitize=address,undefined','-I',str(header.parent),'-I',str(root/'UniXNU-zorn/native/ufs-read'),str(out/'matrix-check.cpp'),'-o',str(out/'matrix-check')],check=True)
subprocess.run([str(out/'matrix-check'),str(out/'matrix-check.bin')],check=True)
spec=importlib.util.spec_from_file_location('reader',root/'UniXNU-zorn/scripts/read-zorn-log.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
b=(out/'matrix-check.bin').read_bytes();raw=reader.touch_raw(b);baseline=struct.unpack_from('>720H',raw,64);active=struct.unpack_from('>720H',raw,1504)
delta=[a-c for a,c in zip(active,baseline)];assert max(delta)==1000 and delta.index(1000)==30*18+4 and min(delta)==0
r={'passed':True,'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'geometry':[40,18],'bounded_4_to_8_baselines':True,'reject_wrong_header_or_non_sensor_data':True,'all_720_big_endian_channels_cross_checked':True,'cpp_host_pair_decoder_matches':True,'asan_ubsan':True,'hardware_qualified':False}
(out/'matrix-host-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
