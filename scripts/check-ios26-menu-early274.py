#!/usr/bin/env python3
"""Reuse252 early-launch tests at the actual274 block-form EL0 callsite."""
import hashlib,json,sys
from pathlib import Path
def main():
    base=Path(__file__).with_name('check-ios26-early-system.py');text=base.read_text()
    old="u.index('if(zorn_early_mode252()==1)zorn_gpu_early_schedule252(owner);')"
    new="u.index('zorn_gpu_early_schedule252(owner);',u.index('if(zorn_early_mode252()==1){'))"
    assert text.count(old)==2;text=text.replace(old,new)
    # Only the source-order assertion's callsite spelling changes. Actual
    # worker/CPU/record/filter bodies are still extracted from --source-root.
    exec(compile(text,str(base),'exec'),dict(__name__='__main__',__file__=str(base)))
    source=Path(sys.argv[sys.argv.index('--source-root')+1]);out=Path(sys.argv[sys.argv.index('--out')+1]);u=(source/'ZornUfsOwner26.cpp').read_text();begin=u.index('if(zorn_early_mode252()==1){');end=u.index('\n        }',begin);block=u[begin:end]
    assert block.index('zorn_gpu_early_schedule252(owner);')<block.index('zorn26_ui_menu_schedule274(IOService::getPlatform());')
    pin=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest());r=json.loads((out/'result.json').read_text());r.update(retained_early_test_base=pin(base),current_callsite_adapter=pin(Path(__file__)),observer_process='backboardd',actual_gpu_then_virtual_scene_inside_same_EL0_block=True);(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
