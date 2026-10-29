#!/usr/bin/env python3
"""Run the actual bounded tracker on synthetic edge/noise/lift cases and captured matrices."""
from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parents[2];out=root/'out/zorn/touch';header=root/'UniXNU-zorn/native/display/ZornTouchContacts.h'
source=r'''
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
#include "ZornTouchContacts.h"
#include "ZornTouchPacing.h"
static void fill(uint8_t *p,unsigned v){memset(p,0,3120);p[0]=0xa5;p[1]=0x5f;for(unsigned i=0;i<720;++i){p[64+2*i]=v>>8;p[65+2*i]=v;}}
static void spot(uint8_t *p,unsigned r,unsigned c){for(int dr=-1;dr<=1;++dr)for(int dc=-1;dc<=1;++dc){int y=int(r)+dr,x=int(c)+dc;if(y<0||y>=18||x<0||x>=40)continue;unsigned i=y*40+x,v=10000-((!dr&&!dc)?1000:500);p[64+2*i]=v>>8;p[65+2*i]=v;}}
int main(int argc,char **argv){
 ZornTouchPacing::Settings pace;assert(ZornTouchPacing::select(0,pace)&&pace.cooperateBytes==8&&pace.pollMs==100);assert(ZornTouchPacing::select(1,pace)&&pace.cooperateBytes==32&&pace.pollMs==20);assert(!ZornTouchPacing::select(2,pace)&&!ZornTouchPacing::select(~0u,pace));
 uint8_t raw[3120];fill(raw,10000);ZornContacts::Detector detector;for(unsigned i=0;i<8;++i)assert(detector.add(raw));ZornContacts::Frame f;
 assert(detector.decode(raw,f)&&!f.count);spot(raw,4,10);assert(detector.decode(raw,f)&&f.count==1);assert(f.points[0].x>7000&&f.points[0].x<8500&&f.points[0].y>7800&&f.points[0].y<9000);unsigned id=f.points[0].id;
 fill(raw,10000);spot(raw,4,11);assert(detector.decode(raw,f)&&f.count==1&&f.points[0].id==id);
 fill(raw,10000);assert(detector.decode(raw,f)&&!f.count);
 fill(raw,10000);spot(raw,0,0);spot(raw,17,39);assert(detector.decode(raw,f)&&f.count==2&&f.points[0].id!=f.points[1].id);
 raw[0]=0;assert(!detector.decode(raw,f));
 // Regression for the weak extra blob seen in the first real calibration:
 // multiple above-threshold cells without a strong peak must not become a finger.
 ZornContacts::Detector quiet;fill(raw,10000);for(unsigned i=0;i<8;++i)assert(quiet.add(raw));
 for(unsigned r=3;r<=5;++r)for(unsigned c=9;c<=11;++c){unsigned at=64+2*(r*40+c);raw[at]=9800>>8;raw[at+1]=9800&255;}
 assert(quiet.decode(raw,f)&&!f.count);
 // Portrait direction regression: the first row is left, low TX is top.
 // These four known electrode centers must preserve X and give top-left Y.
 for(unsigned rx: {4u,13u})for(unsigned tx: {10u,29u}){
  ZornContacts::Detector corners;fill(raw,10000);for(unsigned i=0;i<8;++i)assert(corners.add(raw));
  spot(raw,rx,tx);assert(corners.decode(raw,f)&&f.count==1);
  assert((rx<9)==(f.points[0].x<16384));assert((tx<20)==(f.points[0].y<16384));
 }
 // Holding a finger must not be learned into the adaptive untouched baseline.
 fill(raw,10000);spot(raw,4,10);
 for(unsigned i=0;i<100;++i)assert(quiet.decode(raw,f)&&f.count==1);
 fill(raw,10000);assert(quiet.decode(raw,f)&&!f.count);
 // A panel-wide common-mode shift is rejected as a contact, while a highly
 // noisy matrix or out-of-range sensor value must fail the frame.
 fill(raw,9500);assert(quiet.decode(raw,f)&&!f.count);
 for(unsigned i=0;i<720;++i){unsigned v=(i&1)?11000:9000;raw[64+2*i]=v>>8;raw[65+2*i]=v&255;}
 assert(!quiet.decode(raw,f));fill(raw,10000);raw[64]=0x80;assert(!quiet.decode(raw,f));
 if(argc>1){FILE *file=fopen(argv[1],"rb");assert(file);assert(fread(raw,1,3120,file)==3120);fclose(file);ZornContacts::Detector actual;for(unsigned i=0;i<8;++i)assert(actual.add(raw));memmove(raw+64,raw+1504,1440);assert(actual.decode(raw,f));printf("count=%u noise=%u threshold=%u peak=%u",f.count,actual.noise,actual.threshold,actual.peak);for(unsigned i=0;i<f.count;++i)printf(" id=%u x=%u y=%u",f.points[i].id,f.points[i].x,f.points[i].y);puts("");}
}
'''
(out/'contacts-check.cpp').write_text(source)
subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-fsanitize=address,undefined','-I',str(header.parent),str(out/'contacts-check.cpp'),'-o',str(out/'contacts-check')],check=True)
subprocess.run([str(out/'contacts-check')],check=True)
actual=[]
for folder in ('20261028-204840-7d332caf','20261028-205207-7d332caf'):
 p=root/'out/zorn/debug'/folder/'checkpoints.touch.bin'
 if p.exists():actual.append({'run':folder,'output':subprocess.check_output([str(out/'contacts-check'),str(p)],text=True).strip()})
r={'passed':True,'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'synthetic_noise_motion_lift_two_edge_contacts':True,'weak_blob_regression_and_100_frame_hold':True,'common_mode_noise_invalid_sensor_controls':True,'asan_ubsan':True,'pacing_closed_profiles_and_invalid_modes':True,'captures':actual,'hid_qualified':False}
(out/'contacts-host-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
