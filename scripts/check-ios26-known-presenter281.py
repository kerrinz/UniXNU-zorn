#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse presenter timing controls and actual known-present/thumbnail classes;host memory only."""
import hashlib,importlib.machinery,importlib.util,json,sys
from pathlib import Path
parent=Path(__file__).with_name('check-ios26-present-cost278.py')
loader=importlib.machinery.SourceFileLoader('actual_presenter_test278',str(parent));spec=importlib.util.spec_from_loader(loader.name,loader);m=importlib.util.module_from_spec(spec);loader.exec_module(m)
known='struct Known{void complete(const uint32_t(&)[16]){}};static Known zornKnownPresent247;'
shot='struct Shot{bool pending(){return false;}template<class...T>void capture(T...){assert(false);}};static Shot zornSerialShot265;'
assert m.PREFIX.count(known)==m.PREFIX.count(shot)==1
m.PREFIX=m.PREFIX.replace(known,'#define KERNEL 1\n#include "ZornKnownPresent247.h"\n#include <vector>\n#include <initializer_list>\nstatic ZornKnownPresent247 zornKnownPresent247;')
m.PREFIX=m.PREFIX.replace(shot,'#include "ZornSerialShot265.h"\nstatic ZornSerialShot265 zornSerialShot265;')
# Original timing cases remain;new cases arm the actual class and use owned host pixels.
new=r'''
 for(unsigned which:{0u,1u,2u,3u}){
  mode=0;tick=40;attempts=held=drops=shows=paceCalls=destructs=0;houji26Presents=0;
  zornPresentCostTrace278={};zornKnownPresent247={};zornSerialShot265={};
  IOMobileFramebuffer fb;MiniIOSurface surface;fb.fSwapSurfaces[0][0]=&surface;
  unsigned frame=64;memcpy(fb.fSwap[0]+SWAP_ID,&frame,4);
  std::vector<uint32_t>pixels(size_t(fb.fPanelWidth)*fb.fPanelHeight,0x00ff00ff);
  fb.fBase=reinterpret_cast<uintptr_t>(pixels.data());assert(zornSerialShot265.request());
  if(which)assert(zornKnownPresent247.arm(which==3?63:64,which==2?8:7));
  try{fb.presenter();}catch(Finished&){}
  assert(zornSerialShot265.ready()==(which==1));
  if(which==1){uint32_t captured[16]{};assert(zornKnownPresent247.query(64,7,captured)&&captured[9]==1);assert(!memcmp(zornSerialShot265.bytes,"SHOT",4));}
  else assert(zornSerialShot265.state==1);
 }
 puts("PASS281 actual known-present arm/complete and full-thumbnail capture:unarmed,wrong SID and wrong frame never capture;only the completed known frame captures owned synthetic host pixels. No GPU/scanout proof.");
'''
needle=' printf("PASS278 actual presenter:'
assert m.MAIN.count(needle)==1;m.MAIN=m.MAIN.replace(needle,new+needle)
m.main()
out=Path(sys.argv[sys.argv.index('--out')+1]);p=out/'result.json';d=json.loads(p.read_text());d['adapter']=dict(path=str(Path(__file__).resolve()),sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());d['parent_test_source']=dict(path=str(parent.resolve()),sha256=hashlib.sha256(parent.read_bytes()).hexdigest());d['actual_known_present_and_thumbnail_classes_executed']=True;d['fixture_boundary']='Original GPU/time/IOKit fixtures;thumbnail pixels are owned synthetic host memory,not a GPU result';p.write_text(json.dumps(d,indent=2)+'\n')
