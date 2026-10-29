#!/usr/bin/env python3
"""Exercise the actual edge policy: contact lifetime, axes, IDs and bounds."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[2];out=root/'out/zorn/touch'
header=root/'UniXNU-zorn/native/display/ZornTouchEdges.h'
source=r'''
#include <cassert>
#include "ZornTouchEdges.h"
int main() {
 ZornEdgePolicy::Tracker t={};
 assert(t.mark(1,2,true,32768,65535));
 assert(t.mark(1,0,true,32768,32768));
 assert(t.mark(1,2,false,32768,32768));
 assert(!t.mark(1,2,true,32768,32768));
 assert(!t.mark(1,0,true,1,32768));
 assert(!t.mark(1,2,false,1,32768));
 assert(t.mark(2,2,true,1,32768));
 assert(t.mark(3,2,true,65536,32768));
 assert(t.mark(4,2,true,32768,0));
 assert(!t.mark(256,2,true,0,0));
 assert(!t.mark(255,2,true,-1,0));
 assert(!t.mark(255,2,true,0,65537));
 assert(!t.edge[255]);
 assert(!t.mark(255,2,true,ZornEdgePolicy::EdgeX,ZornEdgePolicy::EdgeY));
 assert(t.mark(255,2,true,ZornEdgePolicy::EdgeX-1,32768));
 assert(t.mark(2,0,true,32768,32768));
}
'''
(out/'edges-check.cpp').write_text(source)
subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-fsanitize=address,undefined','-I',str(header.parent),str(out/'edges-check.cpp'),'-o',str(out/'edges-check')],check=True)
subprocess.run([str(out/'edges-check')],check=True)
r=dict(passed=True,header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),contact_lifetime_lift_id_reuse_and_bounds=True,center_never_promoted_by_moving_to_edge=True,independent_ids_all_four_edges=True,asan_ubsan=True,hardware_qualified=False)
(out/'edges-host-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
