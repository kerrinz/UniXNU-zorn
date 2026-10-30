#!/usr/bin/env python3
"""Exercise the exact 84-byte FT touch read, including every payload CRC corruption."""
from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parents[2];out=root/'out/zorn/touch'
out.mkdir(parents=True,exist_ok=True)
header=root/'UniXNU-zorn/native/display/ZornFt3683Wire.h'
source=r'''
#include <cassert>
#include <cstring>
#include "ZornFt3683Wire.h"
struct Bus {
 unsigned calls=0,delays=0,mode=0,flip=0;
 bool transfer(const uint8_t *tx,uint8_t *rx,unsigned n) {
  assert(n==93 && tx[0]==1 && tx[1]==0xa0 && tx[2]==0 && tx[3]==84);
  for(unsigned i=4;i<n;++i)assert(tx[i]==0);
  ++calls;memset(rx,0,n);
  for(unsigned i=0;i<84;++i)rx[i+7]=(i*13)^0x5a;
  uint16_t crc=ZornFt::crc(rx+7,84);rx[91]=crc;rx[92]=crc>>8;
  if(mode==1)rx[7+flip]^=1;
  if(mode==2)rx[91]^=1;
  if(mode==3)rx[92]^=1;
  if(mode==4)rx[3]=0x20;
  if(mode==5)rx[3]=0x80;
  if(mode==6)return false;
  if(mode==7)memset(rx,0xff,n);
  if(mode==8&&calls==1)rx[92]^=1;
  return true;
 }
 void delay(unsigned us){assert(us==150);++delays;}
};
template<unsigned N=93> struct Pins {
 unsigned cs=1,clk=0,mosi=0,bits=0,samples=0;
 unsigned yields=0;
 uint8_t tx[N]={};
 void set(unsigned i,unsigned v) {
  assert(v<2 && i>=1 && i<=3);
  if(i==1){assert(!cs&&!clk);mosi=v;}
  if(i==2){if(v){assert(!cs&&!clk&&bits<N*8);tx[bits/8]|=mosi<<(7-bits%8);++bits;}clk=v;}
  if(i==3){assert(!clk);cs=v;}
 }
 unsigned sample(){assert(!cs&&clk&&samples<N*8);return (samples++/8)&1;}
 void delay(unsigned us){assert(us==1);}
 void afterByte(unsigned n){assert(!cs&&!clk&&n*8==bits&&samples==bits);if(n%8==0)++yields;}
};
struct FullBus {
 unsigned calls=0,mode=0,flip=0;
 bool transfer(const uint8_t *tx,uint8_t *rx,unsigned n) {
  assert(n==3129&&tx[0]==1&&tx[1]==0xa0&&tx[2]==0x0c&&tx[3]==0x30);
  for(unsigned i=4;i<n;++i)assert(!tx[i]);
  ++calls;memset(rx,0,n);for(unsigned i=0;i<3120;++i)rx[i+7]=i*17;
  auto c=ZornFt::crc(rx+7,3120);rx[3127]=c;rx[3128]=c>>8;
  if(mode==1)rx[7+flip]^=1;if(mode==2)rx[3128]^=1;
  if(mode==3)rx[3]=0x20;if(mode==4)return false;if(mode==5)memset(rx,255,n);
  return true;
 }
 void delay(unsigned n){assert(n==150);}
};
struct MatrixBus {
 unsigned calls=0,mode=0,flip=0;
 bool transfer(const uint8_t *tx,uint8_t *rx,unsigned n) {
  assert(n==1513&&tx[0]==1&&tx[1]==0xa0&&tx[2]==0x05&&tx[3]==0xe0);
  for(unsigned i=4;i<n;++i)assert(!tx[i]);
  ++calls;memset(rx,0,n);for(unsigned i=0;i<1504;++i)rx[i+7]=i*17;
  auto c=ZornFt::crc(rx+7,1504);rx[1511]=c;rx[1512]=c>>8;
  if(mode==1)rx[7+flip]^=1;if(mode==2)rx[1512]^=1;
  if(mode==3)rx[3]=0x20;if(mode==4)return false;if(mode==5)memset(rx,255,n);
  if(mode==6&&calls==1)rx[1511]^=1;
  return true;
 }
 void delay(unsigned n){assert(n==150);}
};
int main() {
 MatrixBus matrix;ZornFt::MatrixFrameResult cells;
 assert(!ZornFt::readMatrixFrame(matrix,cells)&&matrix.calls==1&&cells.attempts==1);
 for(unsigned i=0;i<1504;++i){matrix={};matrix.mode=1;matrix.flip=i;assert(ZornFt::readMatrixFrame(matrix,cells)==4&&matrix.calls==3&&cells.attempts==3);}
 for(unsigned mode=2;mode<=5;++mode){matrix={};matrix.mode=mode;assert(ZornFt::readMatrixFrame(matrix,cells)&&matrix.calls==3);}
 matrix={};matrix.mode=6;assert(!ZornFt::readMatrixFrame(matrix,cells)&&matrix.calls==2);
 Pins<1513> matrixPins;uint8_t matrixTx[1513]={1,0xa0,0x05,0xe0},matrixRx[1513]={};
 assert(!ZornFt::transfer(matrixPins,matrixTx,matrixRx,1512)&&!matrixPins.bits);
 assert(ZornFt::transfer(matrixPins,matrixTx,matrixRx,1513)&&matrixPins.bits==12104&&matrixPins.samples==12104&&!memcmp(matrixTx,matrixPins.tx,1513));
 assert(matrixPins.yields==189);
 for(unsigned i=0;i<1513;++i)assert(matrixRx[i]==(i&1?255:0));
 FullBus full;ZornFt::FullFrameResult whole;
 assert(!ZornFt::readFullFrame(full,whole)&&full.calls==1&&whole.attempts==1);
 for(unsigned i=0;i<3120;++i){full={};full.mode=1;full.flip=i;assert(ZornFt::readFullFrame(full,whole)==4&&full.calls==3&&whole.attempts==3);}
 for(unsigned mode=2;mode<=5;++mode){full={};full.mode=mode;assert(ZornFt::readFullFrame(full,whole)&&full.calls==3);}
 Pins<3129> fullPins;uint8_t fullTx[3129]={1,0xa0,0x0c,0x30},fullRx[3129]={};
 assert(!ZornFt::transfer(fullPins,fullTx,fullRx,3128)&&!fullPins.bits);
 assert(ZornFt::transfer(fullPins,fullTx,fullRx,3129)&&fullPins.bits==25032&&fullPins.samples==25032&&!memcmp(fullTx,fullPins.tx,3129));
 for(unsigned i=0;i<3129;++i)assert(fullRx[i]==(i&1?255:0));
 Bus b;ZornFt::FrameResult r;
 assert(!ZornFt::readFrame(b,r)&&r.attempts==1&&b.calls==1&&b.delays==1);
 for(unsigned flip=0;flip<84;++flip){b={};b.mode=1;b.flip=flip;assert(ZornFt::readFrame(b,r)==4&&r.attempts==3&&b.calls==3&&b.delays==3);}
 for(unsigned mode=2;mode<=7;++mode){b={};b.mode=mode;assert(ZornFt::readFrame(b,r)&&r.attempts==3&&b.calls==3&&b.delays==3);}
 b={};b.mode=8;assert(!ZornFt::readFrame(b,r)&&r.attempts==2&&b.delays==2);
 Pins<> pins;uint8_t tx[93]={1,0xa0,0,84},rx[93]={};
 assert(!ZornFt::transfer(pins,tx,rx,92)&&pins.bits==0);
 assert(ZornFt::transfer(pins,tx,rx,93)&&pins.cs==1&&!pins.clk&&pins.bits==744&&pins.samples==744);
 assert(!memcmp(tx,pins.tx,93));for(unsigned i=0;i<93;++i)assert(rx[i]==(i&1?255:0));
}
'''
(out/'frame-check.cpp').write_text(source)
subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-fsanitize=address,undefined','-I',str(header.parent),str(out/'frame-check.cpp'),'-o',str(out/'frame-check')],check=True)
subprocess.run([str(out/'frame-check')],check=True)
report={'passed':True,'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'payload_crc_corruption_cases':84,'status_crc_transport_all_ff_and_bounded_retries':True,'actual_744_gpio_edges_tested':True,'full_3120_payload_corruption_cases':3120,'actual_25032_bit_gpio_tested':True,'matrix_1504_payload_corruption_cases':1504,'actual_12104_bit_gpio_tested':True,'hardware_qualified':False,'frame_parser':'raw capture only'}
(out/'frame-host-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
