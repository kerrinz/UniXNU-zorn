#!/usr/bin/env python3
"""Host-only portable SHOT publication/multiplexing controls;no USB or phone IO."""
from pathlib import Path
import argparse,json,hashlib,subprocess,os
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address,undefined','thread'],default='address,undefined');a=p.parse_args();S=a.source_root.resolve();O=a.out.resolve();O.mkdir(parents=True,exist_ok=False);H=Path(__file__).resolve().parents[1]/'native/ios26-serial265/ZornSerialShot265.h'
source=r'''
#include "ZornSerialShot265.h"
#include <cassert>
#include <vector>
#include <thread>
#include <atomic>
#include <cstdio>
static unsigned normalCalls;
static unsigned original(void *,char *out,unsigned cap,unsigned seq){assert(seq==normalCalls++);const int n=snprintf(out,cap,"NORMAL:%u\r\n",seq);assert(n>0&&unsigned(n)<cap);return unsigned(n);}
static uint32_t le(const uint8_t *p){return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
int main(int argc,char **argv){assert(argc==2);constexpr unsigned w=96,h=208,stride=w*4+16;
 std::vector<uint32_t> pixels(stride*h/4,0xdddddddd);for(unsigned y=0;y<h;++y)for(unsigned x=0;x<w;++x)pixels[y*stride/4+x]=0xff000000|(y<<12)|x;
 uint32_t record[16]={2,77,5,2,5,5,1,3,1,1,1,0,1,1125,2436,5};uint8_t tag[16]={'H','O','S','T','F','I','X','T','U','R','E','O','N','L','Y','!'};char bytes[3072];
 ZornSerialShot265 shot;assert(!shot.capture(pixels.data(),w,h,stride,pixels.size()*4,record));assert(!shot.ready()&&!shot.packet(bytes,sizeof(bytes),0,tag));assert(shot.request()&&!shot.request());
 assert(!shot.capture(nullptr,w,h,stride,pixels.size()*4,record));assert(!shot.capture(pixels.data(),47,h,stride,pixels.size()*4,record));assert(!shot.capture(pixels.data(),w,103,stride,pixels.size()*4,record));assert(!shot.capture(pixels.data(),w,h,stride-17,pixels.size()*4,record));assert(!shot.capture(pixels.data(),w,h,stride,stride*h-1,record));assert(!shot.capture(reinterpret_cast<uint32_t *>(reinterpret_cast<uintptr_t>(pixels.data())+1),w,h,stride,pixels.size()*4,record));
 record[9]=0;assert(!shot.capture(pixels.data(),w,h,stride,pixels.size()*4,record));record[9]=1;record[0]=1;assert(!shot.capture(pixels.data(),w,h,stride,pixels.size()*4,record));record[0]=2;
 assert(shot.capture(pixels.data(),w,h,stride,pixels.size()*4,record)&&shot.ready());assert(!shot.capture(pixels.data(),w,h,stride,pixels.size()*4,record));assert(!memcmp(shot.bytes,"SHOT",4)&&le(shot.bytes+4)==48&&le(shot.bytes+8)==104&&le(shot.bytes+12)==192);
 for(unsigned y=0;y<104;++y)for(unsigned x=0;x<48;++x)assert(le(shot.bytes+16+y*192+4*x)==pixels[(2*y)*stride/4+2*x]);for(unsigned i=0;i<16;++i)assert(le(shot.bytes+shot.ShotBytes+4*i)==record[i]);
 const auto crc=shot.crc;pixels[0]=0;assert(crc==zorn_panic_crc236(shot.bytes,shot.Bytes));assert(!shot.packet(nullptr,3072,0,tag)&&!shot.packet(bytes,3073,0,tag)&&!shot.packet(bytes,48,0,tag)&&!shot.packet(bytes,3072,shot.Bytes,tag));
 ZornSerialMux265 mux;ZornCdcStream201 stream{};bool idle=false;std::vector<uint8_t> payload;unsigned packets=0;
 auto next=+[](void *p,char *out,unsigned cap,unsigned completed)->unsigned {auto **args=static_cast<void **>(p);return static_cast<ZornSerialMux265 *>(args[0])->next(nullptr,out,cap,completed,original,*static_cast<ZornSerialShot265 *>(args[1]),*static_cast<uint8_t (*)[16]>(args[2]),*static_cast<bool *>(args[3]));};
 void *args[]={&mux,&shot,&tag,&idle};assert(zorn_cdc_next201(&stream,false,false,0,next,args)==1);assert(normalCalls==1&&mux.normal==1);
 while(stream.frames<38){const unsigned oldWire=mux.wire,oldOffset=mux.offset,oldCalls=normalCalls;assert(zorn_cdc_next201(&stream,true,true,stream.length,next,args)==0);assert(zorn_cdc_next201(&stream,true,false,stream.length-1,next,args)==0);assert(mux.wire==oldWire&&mux.offset==oldOffset&&normalCalls==oldCalls);
  idle=stream.frames>=3;assert(zorn_cdc_next201(&stream,true,false,stream.length,next,args)==1);
  if(!memcmp(stream.bytes,"K80SH265",8)){const auto *b=reinterpret_cast<uint8_t *>(stream.bytes);assert(!memcmp(b+8,tag,16));const auto offset=le(b+24),n=le(b+28);assert(offset==payload.size()&&n==stream.length-48&&le(b+32)==shot.Bytes&&le(b+40)==crc&&le(b+44)==265);assert(le(b+36)==zorn_panic_crc236(b+48,n));payload.insert(payload.end(),b+48,b+48+n);++packets;}
 }
 assert(packets==7&&payload.size()==shot.Bytes&&!memcmp(payload.data(),shot.bytes,shot.Bytes));assert(mux.normal==31&&normalCalls==31&&mux.wire==38);assert(zorn_panic_budget236(stream.frames,stream.total,ZornPanicCapacity236));assert(stream.total<=38*3072&&stream.total+ZornPanicCapacity236<=ZornPanicWireLimit236);assert(!mux.next(nullptr,bytes,3072,38,original,shot,tag,true));
 // A new pending gate suppresses a screenshot and reaches the genuine normal
 // producer. Real XNU deadlines/USB completion remain separate backend tests.
 ZornSerialMux265 pending;normalCalls=0;assert(pending.next(nullptr,bytes,3072,0,original,shot,tag,false)>0&&!memcmp(bytes,"NORMAL",6));assert(pending.offset==0&&pending.normal==1);assert(!pending.next(nullptr,bytes,3072,0,original,shot,tag,true));
 ZornSerialShot265 raced;assert(raced.request());std::atomic<unsigned> wins{0};std::thread writers[2];for(auto &writer:writers)writer=std::thread([&]{if(raced.capture(pixels.data(),w,h,stride,pixels.size()*4,record))++wins;});while(!raced.ready())std::this_thread::yield();assert(raced.packet(bytes,sizeof(bytes),0,tag)>48);for(auto &writer:writers)writer.join();assert(wins==1&&raced.crc==zorn_panic_crc236(raced.bytes,raced.Bytes));
 FILE *f=fopen(argv[1],"wb");assert(f&&fwrite(shot.bytes,1,shot.Bytes,f)==shot.Bytes);fclose(f);puts("PASS265 portable SHOT bounds/sample/publication/mux:7chunks within38normal+1terminal budget,real normal sequence retained,in-flight source never reused;CPU fixtures only");
}
''';f=O/'actual-shot.cpp';f.write_text(source);args=['/usr/bin/clang++','-std=c++17','-O1','-pthread','-fsanitize='+a.sanitizer,'-I'+str(H.parent),'-I'+str(S),str(f),'-o',str(O/'check')];r=subprocess.run(args,capture_output=True,text=True);(O/'compile.json').write_text(json.dumps(dict(arguments=args,exit=r.returncode,stderr=r.stderr),indent=2)+'\n');assert not r.returncode,r.stderr;r=subprocess.run([str(O/'check'),str(O/'SYNTHETIC-shot265.bin')],capture_output=True,text=True,env=os.environ|{'ASAN_OPTIONS':'symbolize=0','UBSAN_OPTIONS':'symbolize=0:print_stacktrace=0','TSAN_OPTIONS':'symbolize=0:halt_on_error=1'});assert not r.returncode,r.stderr;pin=lambda p:dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest());d=dict(passed=True,header=pin(H),shared_sources=[pin(S/n) for n in ['ZornPanicPacket236.h','ZornCdcStream201.h']],tool=pin(__file__),sanitizer=a.sanitizer,synthetic_fixture=pin(O/'SYNTHETIC-shot265.bin'),portable_common_code_only=True,actual_K80_presenter_connection=False,actual_USB_or_GPU_execution=False,current264_phone_path_unchanged=True,hardware_qualification=False,stdout=r.stdout);(O/'result.json').write_text(json.dumps(d,indent=2)+'\n');print(r.stdout)
