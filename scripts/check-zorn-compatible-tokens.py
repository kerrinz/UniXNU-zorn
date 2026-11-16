#!/usr/bin/env python3
"""Pure property bytes only; no provider/probe/start or component selection."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,struct
R=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--component',choices=['paired','smmu'],default='paired');opts=ap.parse_args();O=opts.out.resolve();O.mkdir(exist_ok=False)
B=R/'out/zorn/gpu-catalog-service-dependencies/Adreno740';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a='''    for(size_t at=0;at+sizeof(needle)-1<=length;++at) {
        size_t index=0;
        while(index<sizeof(needle)-1 && text[at+index]==needle[index])++index;
        if(index==sizeof(needle)-1)return true;
    }
    return false;'''
b='''    for(size_t at=0;at<length;) {
        size_t end=at;
        while(end<length && text[end])++end;
        if(end==length)return false;   /* no complete property string */
        if(end-at==sizeof(needle)-1) {
            size_t index=0;
            while(index<sizeof(needle)-1 && text[at+index]==needle[index])++index;
            if(index==sizeof(needle)-1)return true;
        }
        at=end+1;
    }
    return false;'''
components=[];host='#include <stddef.h>\n#include <stdio.h>\n';mutations=[]
selected=[('smmu','NativeAdrenoSmmuService.cpp','qcom,adreno-smmu')] if opts.component=='smmu' else [('gmu','NativeAdrenoGmuService.cpp','qcom,adreno-gmu'),('gpu','NativeAdrenoService.cpp','qcom,adreno')]
for kind,name,needle in selected:
 p=B/name;old=p.read_text();assert old.count(a)==1;new=old.replace(a,b,1);d=O/kind;d.mkdir();(d/name).write_text(new);(d/'original.cpp').write_text(old);(d/(kind+'-compatible.UNAPPLIED.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
 assert new.replace(b,a,1)==old
 for label,c in [('substring-restored',old),('length-check-lost',new.replace('if(end-at==sizeof(needle)-1) {','if(true) {',1)),('terminator-check-lost',new.replace('        if(end==length)return false;   /* no complete property string */\n','',1))]:
  assert b not in c;mutations.append(kind+':'+label)
 for version,loop in [('before',a),('after',b)]:host+='static bool '+kind+'_'+version+'(const char *text,size_t length){static const char needle[]="'+needle+'";\n'+loop+'\n}\n'
 components.append(dict(kind=kind,name=name,needle=needle,original_SHA=sha(p),candidate_SHA=sha(d/name)))
cases=[]
for kind in [x['kind'] for x in components]:
 n=next(x['needle'] for x in components if x['kind']==kind).encode()
 rows=[('exact',n+b'\0',True),('later-token',b'vendor,other\0'+n+b'\0',True),('prefix',b'x'+n+b'\0',False),('suffix',n+b'-other\0',False),('unterminated',n,False),('short',n[:-1]+b'\0',False),('unrelated',b'vendor,other\0',False),('empty',b'\0',False),('empty-prefix',b'\0'+n+b'\0',True),('matched-before-bad-tail',n+b'\0tail',True)]
 if kind=='gpu':rows.append(('actual-gmu-token',b'qcom,adreno-gmu\0',False))
 for name,raw,want in rows:cases.append(dict(kind=kind,name=name,hex=raw.hex(),expected=want))
host+='int main(){bool ok=true;unsigned before_false_matches=0;\n'
for i,c in enumerate(cases):
 raw=bytes.fromhex(c['hex']);host+='const char b'+str(i)+'[]={'+','.join(str(x) for x in raw)+'};\n';host+='ok &= '+c['kind']+'_after(b'+str(i)+',sizeof(b'+str(i)+'))=='+('true' if c['expected'] else 'false')+';\n'
 if not c['expected']:host+='before_false_matches+='+c['kind']+'_before(b'+str(i)+',sizeof(b'+str(i)+'));\n'
 else:host+='ok &= '+c['kind']+'_before(b'+str(i)+',sizeof(b'+str(i)+'));\n'
expected_bad=3 if opts.component=='smmu' else 7
host+='printf("ok=%d cases='+str(len(cases))+' before_false_matches=%u property-bytes-only\\n",ok,before_false_matches);return ok&&before_false_matches=='+str(expected_bad)+'?0:1;}\n'
F=O/'property-bytes.cpp';F.write_text(host);(O/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');events=[]
def run(args,name,cwd=R):
 args=list(map(str,args));p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=50);(O/(name+'.stdout.raw')).write_bytes(p.stdout);(O/(name+'.stderr.raw')).write_bytes(p.stderr);events.append(dict(name=name,arguments=args,directory=str(cwd),returncode=p.returncode));(O/'commands.json').write_text(json.dumps(events,indent=2)+'\n');assert p.returncode==0,p.stderr.decode(errors='replace');return p.stdout.decode()
clang='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++';run([clang,'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-isysroot','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',F,'-o',O/'property-bytes'],'host-build');output=run([O/'property-bytes'],'host-run')
prior=json.loads((R/'out/zorn/gpu-catalog-service-dependencies/compile-result.json').read_text());service=str(B/'NativeAdrenoService.cpp');rec=next(x for x in prior['commands'] if service in x['arguments'] and '-c' in x['arguments'])
for c in components:
 d=O/c['kind'];source=d/c['name'];args=list(rec['arguments']);assert '--target=arm64-apple-ios17.0.0' in args and not any(x in args for x in ['-MF','-MJ']);args[args.index(service)]=str(source);obj=d/'candidate-ios17.o';args[args.index('-o')+1]=str(obj);args+=['-MD','-MF',str(d/'candidate-inputs.d'),'-MT',str(obj)];run(args,c['kind']+'-ios17',Path(rec['directory']))
 raw=obj.read_bytes();assert struct.unpack_from('<I',raw)[0]==0xfeedfacf;at=32;ver=None
 for _ in range(struct.unpack_from('<I',raw,16)[0]):
  cmd,n=struct.unpack_from('<II',raw,at)
  if cmd==0x32:platform,ver=struct.unpack_from('<II',raw,at+8);assert platform==2
  at+=n
 assert ver==17<<16 and sha(B/c['name'])==c['original_SHA']
res=dict(scope='exact complete compatible property tokens; two independent UNAPPLIED source candidates',components=components,property_cases=len(cases),original_false_matches_refused=expected_bad,actual_gmu_token_previously_matched_GPU_needle=opts.component=='paired',pure_property_host_output=output,source_mutations_refused=mutations,ASan_UBSan_pass=True,selected_new_Service_iOS17_objects_pass=True,component_selection_for_checker_only=opts.component,objects_not_linked_or_executed=True,matching_token_must_be_terminated_but_full_list_validity_not_claimed=True,original_needles_scores_start_bodies_and_class_layouts_unchanged=True,no_provider_getProperty_probe_start_map_callback_native_or_success_peer_execution=True,no_new_component_runtimecaller_or_policy_selection=True,catalog_pins_32patches_profiles_unchanged=True,hardware_qualification=False,device_operations=False)
(O/'result.json').write_text(json.dumps(res,indent=2)+'\n');print('PASS:'+str(len(cases))+' new property cases/'+str(expected_bad)+' original false matches/'+str(len(mutations))+' source controls;new selected module only,no provider/probe')
