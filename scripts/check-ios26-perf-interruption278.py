#!/usr/bin/env python3
"""Actual observer interruption:partial sample endpoint precedes done publication."""
import importlib.util,hashlib,json,sys
from pathlib import Path
p=Path(__file__).with_name('check-ios26-perf-observer278.py');s=importlib.util.spec_from_file_location('observer278',p);base=importlib.util.module_from_spec(s);s.loader.exec_module(base);original=base.module
def module(path,name):
 m=original(path,name)
 if name=='base269':
  old='if(mode==11)normalContext=false;';assert old in m.PREFIX;m.PREFIX=m.PREFIX.replace(old,'if(mode==11||(mode==12&&ms==10000))normalContext=false;')
 return m
base.module=module;base.MAIN=base.MAIN.replace('{0u,8u,9u,10u,11u}','{0u,8u,9u,10u,11u,12u}').replace('assert(out[0]==7&&!out[3]);','assert(out[0]==7&&out[3]==(m==12?1u:0u));if(m==12)assert(out[6]==100000&&out[7]==90000);');base.main();out=Path(sys.argv[sys.argv.index('--out')+1]);source=Path(sys.argv[sys.argv.index('--source')+1])/'ZornUiSceneService269.cpp';text=source.read_text();assert 'if(!normal() || !nativeK80(platform)){interrupted=true;break;}' in text and text.index('store(6,uptimeMs());')<text.index('if(interrupted)finish(7);');r=json.loads((out/'result.json').read_text());r.update(partial_sample_endpoint_saved_before_done=True,interrupted_after_one_sample_executed=True,adapter=dict(path=str(Path(__file__).resolve()),sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()));(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
