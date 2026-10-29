#!/usr/bin/env python3
"""Host fault tests of the exact bounded FT identity/GPIO transport."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/zorn/touch'
HEADER=ROOT/'UniXNU-zorn/native/display/ZornFt3683Wire.h'
source=r'''
#include <cassert>
#include <cstring>
#include "ZornFt3683Wire.h"
struct Bus {
 unsigned calls=0,delays=0,mode=0;uint8_t reg=0xa3;
 bool transfer(const uint8_t*tx,uint8_t*rx,unsigned n){
  ++calls;assert(n==10 && tx[0]==reg && tx[1]==0xa0 && tx[2]==0 && tx[3]==1);
  for(unsigned i=4;i<n;++i)assert(tx[i]==0);
  memset(rx,0,n);rx[7]=0x36;uint16_t crc=ZornFt::crc(rx+7,1);rx[8]=crc;rx[9]=crc>>8;
  if(mode==1)rx[3]=0x20;if(mode==2)rx[3]=0x80;if(mode==3)rx[8]^=1;
  if(mode==4)return false;
  if(mode==5)memset(rx,0xff,n);
  if(mode==6&&calls==1)rx[8]^=1;
  return true;
 }
 void delay(unsigned n){assert(n==150);++delays;}
};
struct Pins {
 unsigned cs=1,clk=0,mosi=0,bits=0,samples=0,pauses=0;uint8_t sent[10]={};
 void set(unsigned i,unsigned value){
  assert(value<=1 && (i==1 || i==2 || i==3));
  if(i==1){assert(!cs&&!clk);mosi=value;}
  if(i==2){if(value){assert(!cs&&!clk&&bits<80);sent[bits/8]|=mosi<<(7-bits%8);++bits;}clk=value;}
  if(i==3){assert(!clk);cs=value;}
 }
 unsigned sample(){assert(!cs&&clk&&samples<80);return (0xa5>>(7-(samples++)%8))&1;}
 void delay(unsigned us){assert(us==1);++pauses;}
 void afterByte(unsigned n){assert(!cs&&!clk&&n*8==bits&&samples==bits);}
};
int main(){
 const uint8_t check[]="123456789";assert(ZornFt::crc(check,9)==0x6f91);
 ZornFt::ReadResult r;uint8_t v=0x77;Bus b;
 for(unsigned cmd=0;cmd<256;++cmd){b={};b.reg=cmd;v=0x77;unsigned result=ZornFt::readIdentity(b,cmd,v,r);
  if(cmd==0xa3||cmd==0x9f||cmd==0xa6)assert(!result&&v==0x36&&b.calls==1&&b.delays==1);
  else assert(result==1&&v==0x77&&b.calls==0&&b.delays==0);
 }
 for(unsigned mode=1;mode<=5;++mode){b={};b.mode=mode;v=0x77;assert(ZornFt::readIdentity(b,0xa3,v,r)!=0&&v==0x77&&b.calls==3&&b.delays==3&&r.attempts==3);}
 b={};b.mode=6;assert(!ZornFt::readIdentity(b,0xa3,v,r)&&b.calls==2&&b.delays==2&&v==0x36);
 assert(ZornFt::pinOwned(1)&&!ZornFt::pinOwned(0xffffffff)&&!ZornFt::pinOwned(1u<<11)&&ZornFt::pinOwned(3u<<11));
 assert(!ZornFt::gpiIdle(0xffffffff,0)&&!ZornFt::gpiIdle(0,0xffffffff));
 for(unsigned state=0;state<16;++state)assert(ZornFt::gpiIdle(state<<20,4)==(state==0||state==1||state==3));
 for(unsigned i=0;i<6;++i){uint32_t c=ZornFt::gpioConfig(i,0xabcdffff);assert((c&~0x3ffu)==(0xabcdffff&~0x3ffu));assert(((c>>9)&1)==(i!=0&&i!=5));assert((c&0x3c)==0);}
 uint8_t tx[10]={0xa3,0xa0,0,1,0,0,0,0,0,0},rx[10]={};Pins p;
 assert(!ZornFt::transfer(p,tx,rx,9)&&p.bits==0);assert(ZornFt::transfer(p,tx,rx,10));
 assert(p.cs==1&&p.clk==0&&p.bits==80&&p.samples==80&&!memcmp(tx,p.sent,10));
 for(auto x:rx)assert(x==0xa5);
}
'''
OUT.mkdir(parents=True,exist_ok=True);(OUT/'wire-check.cpp').write_text(source)
subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-fsanitize=address,undefined','-I',str(HEADER.parent),str(OUT/'wire-check.cpp'),'-o',str(OUT/'wire-check')],check=True)
subprocess.run([str(OUT/'wire-check')],check=True)
r={'passed':True,'header_sha256':hashlib.sha256(HEADER.read_bytes()).hexdigest(),'command_space_cases':256,
   'tests':['CRC known vector','command whitelist','3 bounded retries/status/CRC/transport/all-FF errors','success after transient CRC error','GPIO AP ownership','16 GPI states','pin configuration preserves ownership bits','SPI mode0 wire edges/TX/RX'],
   'controller_writes_supported':False,'hardware_qualified':False}
(OUT/'wire-host-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
