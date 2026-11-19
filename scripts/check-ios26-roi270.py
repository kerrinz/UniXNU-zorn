#!/usr/bin/env python3
"""Actual checked265 sampler reused through270 ROI/header and late-stream adapter."""
import argparse,hashlib,json,os,subprocess,sys,struct,zlib
from pathlib import Path
from inspect_ios26_ui_roi270 import split_roi
TEST=r'''
#include "ZornSerialShot270.h"
#include <cassert>
#include <cstdio>
#include <vector>
#include <thread>
#include <atomic>
#include <cstring>
static unsigned controls;
static uint32_t record[16]={2,64,4,2,4,4,1,3,1,1,1,63,64,1125,2436,0};
uint32_t le(const char *p){const auto *v=reinterpret_cast<const uint8_t*>(p);return v[0]|uint32_t(v[1])<<8|uint32_t(v[2])<<16|uint32_t(v[3])<<24;}
struct Next {unsigned calls=0,result=37;};
unsigned normal(void *c,char *out,unsigned,unsigned){auto &n=*static_cast<Next*>(c);++n.calls;if(n.result!=ZORN_CDC_PENDING270&&n.result<=3072)memset(out,'N',n.result);return n.result;}
void late(){ZornCdcStream201 s{};Next n;n.result=ZORN_CDC_PENDING270;assert(zorn_cdc_next270(&s,false,false,0,normal,&n)==-1&&!s.frames);++controls;n.result=37;assert(zorn_cdc_next270(&s,false,false,0,normal,&n)==1&&s.frames==1&&s.length==37);++controls;
 for(unsigned mask=0;mask<8;++mask){auto copy=s;Next pending{0,ZORN_CDC_PENDING270};bool ready=mask&1,busy=mask&2;unsigned completed=mask&4?s.length:s.length-1;assert(zorn_cdc_next270(&copy,ready,busy,completed,normal,&pending)==0);assert(!memcmp(&copy,&s,sizeof(s)));assert(pending.calls==(ready&&!busy&&completed==s.length?1u:0u));++controls;}
 for(unsigned value:{0u,3073u}){auto copy=s;Next bad{0,value};assert(zorn_cdc_next270(&copy,true,false,s.length,normal,&bad)==-1);assert(!memcmp(&copy,&s,sizeof(s)));++controls;}
 {auto copy=s;copy.total=119807;Next real;assert(zorn_cdc_next270(&copy,true,false,s.length,normal,&real)==-1);++controls;}
 {auto copy=s;copy.frames=40;Next pending{0,ZORN_CDC_PENDING270};assert(zorn_cdc_next270(&copy,true,false,s.length,normal,&pending)==-1&&!pending.calls);++controls;}
 {auto copy=s;Next pending{0,ZORN_CDC_PENDING270};assert(zorn_cdc_next270(&copy,true,false,s.length+1,normal,&pending)==-1&&!pending.calls);++controls;}
 assert(zorn_cdc_next270(nullptr,true,false,0,normal,&n)==-1);assert(zorn_cdc_next270(&s,true,false,s.length,nullptr,&n)==-1);++controls;
}
struct Ui {bool available=false;bool ready()const{return available;}unsigned packet(char *p,unsigned cap,const uint8_t(&tag)[16])const{uint32_t status[16]{};status[0]=6;status[2]=1023;return ZornUiSceneWire269::packet(p,cap,status,tag);}};
struct Shot {const ZornSerialRoi270 &image;bool available;enum{Bytes=ZornSerialRoi270::Bytes,PacketHeader=ZornSerialRoi270::PacketHeader};bool ready()const{return available&&image.ready();}unsigned packet(char *p,unsigned cap,unsigned offset,const uint8_t(&tag)[16])const{return image.packet(p,cap,offset,tag);}};
struct Composite {ZornSerialMux270 mux;const ZornSerialRoi270 &image;Ui ui;Next normal;bool available=false;uint8_t tag[16]{};};
unsigned compose(void *cookie,char *out,unsigned cap,unsigned completed){auto &c=*static_cast<Composite*>(cookie);return c.mux.next(&c.normal,out,cap,completed,normal,Shot{c.image,c.available},c.ui,c.tag,true);}
int main(int argc,char **argv){assert(argc==3);uint8_t tag[16]{};assert(strlen(argv[1])==32);for(unsigned i=0;i<16;++i){unsigned v;assert(sscanf(argv[1]+2*i,"%2x",&v)==1);tag[i]=v;}
 late();constexpr unsigned W=384,H=832,Stride=W*4;std::vector<uint32_t> pixels(W*H);for(unsigned y=0;y<H;++y)for(unsigned x=0;x<W;++x)pixels[y*W+x]=0xff000000u|(y<<12)|x;
 {ZornSerialRoi270 r;assert(!r.capture(pixels.data(),W,H,Stride,pixels.size()*4,record)&&!r.ready());assert(r.request()&&!r.request()&&r.pending());assert(!r.capture(nullptr,W,H,Stride,pixels.size()*4,record));assert(!r.capture(reinterpret_cast<uint32_t*>(reinterpret_cast<uintptr_t>(pixels.data())+1),W,H,Stride,pixels.size()*4,record));assert(!r.capture(pixels.data(),W-1,H,Stride,pixels.size()*4,record));assert(!r.capture(pixels.data(),W,H-1,Stride,pixels.size()*4,record));assert(!r.capture(pixels.data(),W,H,Stride,pixels.size()*4-1,record));assert(!r.capture(pixels.data(),W,H,W*4-4,pixels.size()*4,record));assert(!r.capture(reinterpret_cast<uint32_t*>(UINTPTR_MAX-3),W,H,Stride,pixels.size()*4,record));assert(r.pending()&&!r.ready());++controls;}
 ZornSerialRoi270 r;assert(r.request());std::atomic<unsigned> won{0};std::vector<std::thread> threads;for(unsigned i=0;i<8;++i)threads.emplace_back([&]{if(r.capture(pixels.data(),W,H,Stride,pixels.size()*4,record))++won;});for(auto&t:threads)t.join();assert(won==1&&r.ready()&&!r.pending());++controls;
 std::vector<char> payload;FILE *f=fopen(argv[2],"wb");assert(f);char p[3072]{};unsigned off=0,chunks=0;
 while(off<r.Bytes){const unsigned n=r.packet(p,sizeof(p),off,tag);assert(n&&n<=3072&&!memcmp(p,"K80SH270",8)&&le(p+44)==270);assert(le(p+48)==W/2&&le(p+52)==0&&le(p+56)==W/2&&le(p+60)==H/2);assert(le(p+64)==zorn_panic_crc236(reinterpret_cast<uint8_t*>(p),64));assert(le(p+24)==off&&le(p+28)==n-r.PacketHeader);assert(le(p+36)==zorn_panic_crc236(reinterpret_cast<uint8_t*>(p+r.PacketHeader),n-r.PacketHeader));fwrite(p,1,n,f);payload.insert(payload.end(),p+r.PacketHeader,p+n);off+=n-r.PacketHeader;++chunks;}
 fclose(f);assert(chunks==7&&payload.size()==r.Bytes&&off==r.Bytes);assert(!r.packet(p,68,0,tag)&&!r.packet(p,3073,0,tag)&&!r.packet(p,sizeof(p),r.Bytes,tag));++controls;
 assert(!memcmp(payload.data(),"SHOT",4)&&le(payload.data()+4)==48&&le(payload.data()+8)==104);for(unsigned y=0;y<104;++y)for(unsigned x=0;x<48;++x)assert(le(payload.data()+16+(y*48+x)*4)==pixels[(y*4)*W+W/2+x*4]);assert(!memcmp(payload.data()+16+19968,record,sizeof(record)));++controls;
 char before[3072]{};const unsigned first=r.packet(before,sizeof(before),0,tag);std::fill(pixels.begin(),pixels.end(),0);assert(!r.capture(pixels.data(),W,H,Stride,pixels.size()*4,record));assert(r.packet(p,sizeof(p),0,tag)==first&&!memcmp(p,before,first));++controls;
 Composite c{{},r};ZornCdcStream201 stream{};unsigned wire=0;
 while(c.normal.calls<30){c.ui.available=wire>=8;int step=zorn_cdc_next270(&stream,true,false,stream.length,compose,&c);assert(step==1);++wire;}
 assert(wire==31&&stream.frames==31&&c.mux.normal==30&&c.mux.sentUi&&!c.mux.offset);auto saved=stream;for(unsigned i=0;i<100;++i){assert(zorn_cdc_next270(&stream,true,false,stream.length,compose,&c)==0);assert(!memcmp(&saved,&stream,sizeof(stream))&&c.normal.calls==30&&c.mux.wire==31);}++controls;
 c.available=true;while(c.mux.offset<r.Bytes){assert(zorn_cdc_next270(&stream,true,false,stream.length,compose,&c)==1);assert(!memcmp(stream.bytes,"K80SH270",8));++wire;}
 assert(wire==38&&stream.frames==38&&c.mux.wire==38&&c.mux.normal==30);assert(zorn_cdc_next270(&stream,true,false,stream.length,compose,&c)==-1&&stream.frames==38);++controls;
 printf("PASS270 %u controls:actual265 sampler ROI pixels/records,7headers+CRCs,one immutable writer,late Pending never starts/reuses DMA or consumes frame counters;30normal+1UI+7ROI=38\n",controls);
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);f=a.out/'actual-roi.cpp';f.write_text(TEST);exe=a.out/'actual-roi';wire=a.out/'synthetic-roi-wire.bin';san='address,undefined' if a.sanitizer=='address-undefined' else 'thread';args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),str(f),'-o',str(exe)];env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1')
    r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/'compile.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();r=subprocess.run([str(exe),a.tag,str(wire)],capture_output=True,env=env,timeout=120);(a.out/'run.stdout').write_bytes(r.stdout);(a.out/'run.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();data=wire.read_bytes();normal,pixels,roi=split_roi(data,a.tag);assert not normal and roi['complete'] and roi['packet_count']==7 and roi['source_roi']['x']==192 and roi['source_roi']['height']==416
    refused=[]
    def reject(name,raw):
        try:split_roi(raw,a.tag)
        except ValueError:refused.append(name)
        else:raise AssertionError(name)
    for offset,name in [(8,'foreign-boot'),(48,'ROI-header-CRC'),(64,'header-CRC'),(68,'pixel-CRC')]:
        raw=bytearray(data);raw[offset]^=1;reject(name,raw)
    first=68+struct.unpack_from('<I',data,28)[0]
    reject('repeated-image',data+data)
    reject('reordered-chunks',data[first:]+data[:first])
    raw=bytearray(data);struct.pack_into('<I',raw,48,193);struct.pack_into('<I',raw,64,zlib.crc32(raw[:64]));reject('source-quadrant-after-valid-header-CRC',raw)
    for n in [1,7,8,20,67,68,100,len(data)-1]:assert not split_roi(data[:n],a.tag)[2]['complete']
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());result=dict(passed=True,sanitizer=a.sanitizer,sources=[pin(a.source/n) for n in ['ZornSerialShot270.h','ZornSerialShot265.h','ZornCdcLate270.h','ZornCdcStream201.h','ZornUiSceneWire269.h','ZornPanicPacket236.h']],test=pin(f),executable=pin(exe),wire=pin(wire),source_ROI=roi,decoder=pin(Path(__file__).with_name('inspect_ios26_ui_roi270.py')),refused=refused,partial_prefixes=8,arguments=args,stdout=r.stdout.decode(),phone_access=False,actual_GPU_or_UI_image_qualified=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(r.stdout.decode().strip(),';decoder refusals',len(refused))
if __name__=='__main__':main()
