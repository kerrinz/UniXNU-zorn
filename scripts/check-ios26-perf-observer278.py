#!/usr/bin/env python3
"""Exercise actual manual observer/creator/CPU collector/wire;no phone access."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path
def module(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
MAIN=r'''
void reset(unsigned m){assert(platform.refs==1&&!attachedService);mode=m;normalContext=boardValid=true;nowTick=0;starts=deallocs=serviceFrees=sends=lockDepth=0;pending=nullptr;pendingContext=nullptr;scheduled269=done269=schedulingReturned269=0;captureDeadline270=0;for(auto &v:status269)v=0;}
int main(int argc,char**argv){unsigned controls=0;
 for(unsigned m: {0u,8u,9u,10u,11u}){reset(m);uint32_t out[304]{};assert(!zorn26_ui_menu_snapshot278(out));zorn26_ui_menu_schedule278(&platform);assert(starts==1);const auto refs=platform.refs;zorn26_ui_menu_schedule278(&platform);assert(starts==1&&refs==platform.refs);
  if(m!=9){assert(platform.refs==2&&pending);try{pending(pendingContext,0);}catch(Terminated&){};}
  assert(platform.refs==1&&!attachedService&&!sends&&!serviceFrees&&zorn26_ui_menu_done278()&&zorn26_ui_menu_snapshot278(out));
  if(m==0||m==8||m==10){assert(out[0]==6&&out[3]==9&&out[4]==10000&&out[5]==90000&&out[6]==170000&&out[2]==(m==10?61u:63u));for(unsigned n=0;n<9;++n){unsigned at=7+33*n;assert(out[at]==90000+10000*n&&out[at+1]==7&&out[at+2]==out[at]);assert(out[at+17]==278&&out[at+18]==out[at]/10000);}}
  else {assert(out[0]==7&&!out[3]);if(m==9)assert(out[1]==5&&!pending);}
  assert(!zorn26_ui_menu_capture_ready278());nowTick+=4999;assert(!zorn26_ui_menu_capture_ready278());++nowTick;assert(zorn26_ui_menu_capture_ready278());++controls;
 }
 reset(0);normalContext=false;zorn26_ui_menu_schedule278(&platform);assert(!starts&&!scheduled269&&platform.refs==1);++controls;
 reset(0);boardValid=false;zorn26_ui_menu_schedule278(&platform);assert(!starts&&!scheduled269&&platform.refs==1);++controls;
 reset(0);IOService foreign;zorn26_ui_menu_schedule278(&foreign);assert(!starts&&!scheduled269&&foreign.refs==1);++controls;
 reset(0);zorn26_ui_menu_schedule278(&platform);assert(platform.refs==2);schedulingReturned269=0;try{pending(pendingContext,0);}catch(Terminated&){}assert(done269&&status269[0]==7&&platform.refs==1&&!status269[3]&&!sends);++controls;
 reset(10);zorn26_ui_menu_schedule278(&platform);assert(platform.refs==2&&!done269&&!deallocs); /* Unknown worker execution retains the platform. */ try{pending(pendingContext,0);}catch(Terminated&){}assert(platform.refs==1&&done269);++controls;
 reset(0);zorn26_ui_menu_schedule278(&platform);try{pending(pendingContext,0);}catch(Terminated&){}uint32_t v[304];assert(zorn26_ui_menu_snapshot278(v));char wire[1248];uint8_t tag[16]{};for(unsigned n=0;n<16;++n)tag[n]=n;
 assert(!ZornUiMenuWire278::packet(nullptr,1248,v,tag)&&!ZornUiMenuWire278::packet(wire,1247,v,tag));assert(ZornUiMenuWire278::packet(wire,1248,v,tag)==1248&&!memcmp(wire,"K80PF278",8));if(argc==2){FILE*f=fopen(argv[1],"wb");assert(f&&fwrite(wire,1,1248,f)==1248&&!fclose(f));}
 printf("PASS278 %u controls:actual creator/worker,no HID allocation or sends,9 real CPU callback samples,once-only scheduling,wrong board/context refusal,failed thread cleanup,unknown handle lifetime,5s capture boundary,1248byte wire\n",controls);
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--touch-common',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sanitizer',choices=['address-undefined','thread'],required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 base=module(Path(__file__).with_name('check-ios26-ui-service269.py'),'base269');old=module(Path(__file__).with_name('check-ios26-ui-menu-dismiss275.py'),'collector274');source=a.source/'ZornUiSceneService269.cpp';body=source.read_text();assert all(x not in body for x in ['submitFrame(','registerService(','new ZornUiSceneService269','ZornUiTap275','ZornUiMenu274::run']);body=body[body.index('namespace {'):]
 prefix=base.PREFIX.replace('zorn26_ui_scene_gpu_ready269','zorn26_ui_desktop_ready272')+'\n#include "ZornUiMenuWire278.h"\nextern "C" void zorn26_ui_menu_progress274(uint32_t (&out)[16]){for(auto &v:out)v=0;out[0]=7;out[1]=uint32_t(nowTick);}\nextern "C" int zorn26_present_cost_snapshot278(uint32_t (&out)[16]){for(auto &v:out)v=0;out[0]=278;out[1]=unsigned(nowTick/10000);out[2]=unsigned(nowTick);out[3]=out[1];out[4]=2;out[11]=out[1];return 1;}\n#define NSEC_PER_SEC 1000000000ULL\nvoid clock_interval_to_deadline(unsigned n,uint64_t unit,uint64_t *out){assert(n==5&&unit==NSEC_PER_SEC);*out=mach_absolute_time()+uint64_t(n)*unit;}\n'
 env=os.environ|dict(ASAN_OPTIONS='symbolize=0',UBSAN_OPTIONS='symbolize=0:print_stacktrace=0',TSAN_OPTIONS='symbolize=0:halt_on_error=1');san='address,undefined' if a.sanitizer=='address-undefined' else 'thread';rows=[]
 for name,text in [('manual',prefix+body+MAIN),('progress',old.PROGRESS)]:
  f=a.out/(name+'.cpp');f.write_text(text);exe=a.out/name;args=['xcrun','clang++','-std=c++17','-O1','-g','-pthread','-fno-omit-frame-pointer','-fsanitize='+san,'-I'+str(a.source),'-I'+str(a.touch_common),str(f),'-o',str(exe)];r=subprocess.run(args,capture_output=True,env=env,timeout=120);(a.out/(name+'-compile.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();cmd=[str(exe)]+([str(a.out/'actual-packet278.bin')] if name=='manual' else []);r=subprocess.run(cmd,capture_output=True,env=env,timeout=120);(a.out/(name+'-run.stdout')).write_bytes(r.stdout);(a.out/(name+'-run.stderr')).write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();rows.append(dict(arguments=args,stdout=r.stdout.decode()));print(r.stdout.decode().strip())
 pin=lambda q:dict(path=str(q.resolve()),sha256=hashlib.sha256(q.read_bytes()).hexdigest());sources=[source]+[a.source/n for n in ['ZornUiMenuWire278.h','ZornUiMenuProgress274.inc','ZornClientFailureStore261.h','ZornClientFailure261.h','ZornPresentTrace245.h','ZornApplicationObservation26.h']];(a.out/'result.json').write_text(json.dumps(dict(passed=True,sources=[pin(q) for q in sources],sanitizer=a.sanitizer,tests=rows,no_synthetic_HID_service_or_contacts=True,CPU_snapshots_are_not_UI_or_physical_touch_qualification=True,host_boundaries='Actual observer and CPU collector bodies;explicit host time/thread/platform objects,not actual FT3683 bus or hardware',phone_access=False,hardware_qualified=False),indent=2)+'\n')
if __name__=='__main__':main()
