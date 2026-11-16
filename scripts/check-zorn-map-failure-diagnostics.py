#!/usr/bin/env python3
"""Source-only null-VM refusal path; never execute client or VM queries."""
import argparse,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--review',type=Path,required=True);o=ap.parse_args().review.resolve()
old=(R/'out/zorn/gpu-catalog-service-dependencies/Adreno740/NativeAdrenoUserClient.cpp').read_text();new=(o/'map-diagnostics-candidate.cpp').read_text()
line='            native_adreno_map_fail[5][0]=(uint32_t)vm_->spanCount();native_adreno_map_fail[5][1]=(uint32_t)vm_->objectCount();'
guarded='            if(vm_) {\n    '+line+'\n            }'
def check(c):
 assert c.count(guarded)==1
 assert c.replace(guarded,line,1)==old
 assert 'open_=false;vm_=nullptr;' in old
 method=old[old.index('IOReturn NativeAdrenoUserClient::mapBo'):old.index('IOReturn NativeAdrenoUserClient::mapBo')+260]
 assert 'if(!open_)return kIOReturnNotReady;' in method
 assert 'status=mapBo(&request,&reply);\n        if(!status)memcpy(output,&reply,sizeof(reply));\n        else {' in old
check(new);refused=[]
for name,c in [('removed-guard',old),('wrong-polarity',new.replace('if(vm_) {','if(!vm_) {',1)),('invented-count',new.replace('(uint32_t)vm_->objectCount()','0',1))]:
 try:check(c)
 except AssertionError:refused.append(name)
 else:raise AssertionError(name)
p=o/'map-diagnostics-result.json';x=json.loads(p.read_text());x['three_source_corruptions_refused']=refused;p.write_text(json.dumps(x,indent=2)+'\n');print('PASS:closed-client failure source path;two queries guarded;3 corruptions refused;no native/getter execution')
