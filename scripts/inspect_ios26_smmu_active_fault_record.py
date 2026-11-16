#!/usr/bin/env python3
"""Inspect an archived K80 iOS26 SMMU active-fault page. Never contact a phone or transport."""
import argparse
import json
import pathlib
import struct
import zlib
import re

MAGIC = b'HJPAN026'
RECORD_BYTES = 544
PAGE_BYTES = 4096
PATTERN=re.compile('K80 domain: copied=1 gpucc=(?P<ur>[01])/(?P<uc>[01]) graph=(?P<gr>[01])/(?P<ga>[0-9]{1,10})/(?P<gh>[0-9]{1,10})/(?P<gn>[0-9]{1,10})/(?P<gc>[0-9]{1,10})/(?P<gd>[01]) list=(?P<lr>[01])/(?P<la>[0-9]{1,10})/(?P<lv>[01])/(?P<ls>-?[0-9]{1,10})/(?P<ln>-?[0-9]{1,10}) hub=(?P<hr>[01])/(?P<hs>[0-9a-f]{1,8}) ddr=(?P<dr>[01])/(?P<ds>[0-9a-f]{1,8}) core=(?P<kr>[01])/(?P<ks>[0-9a-f]{1,8}) cx=(?P<xr>[01])/(?P<xa>[01])/(?P<xc>[01])/(?P<xt>[01])/(?P<xd>[01]) cc=(?P<cr>[01])/(?P<cs>[0-9a-f]{1,8}) completion=(?P<nr>[01])/(?P<nd>[01]) smmu=(?P<sr>[01])/(?P<ss>[0-9a-f]{1,8}) maps=(?P<mr>[01])/(?P<ms>[0-9a-f]{1,8}) cxon=(?P<pr>[01])/(?P<pw>[0-9]{1,10})/(?P<pv>[01])/(?P<ps>-?[0-9]{1,10})/(?P<pd>[0-9]{1,10})/(?P<pk>[0-9]{1,10})/(?P<pa>[01])/(?P<px>[0-9a-f]{1,16}) power=(?P<qr>[01])/(?P<qd>[0-9]{1,10})/(?P<qk>[0-9]{1,10})/(?P<qa>[01])/(?P<qx>[0-9a-f]{1,16}) pm=(?P<vr>[01])/(?P<vx>[0-9a-f]{1,8}) pstep=(?P<cp>[0-9]{1,10})/(?P<sp>[0-9]{1,10}) bulk=(?P<ba>[0-9]{1,10})/(?P<bp>[0-9]{1,10})/(?P<be>[0-9]{1,10})/(?P<bn>-?[0-9]{1,10})/(?P<en>-?[0-9]{1,10}) probe=(?P<ir>[01])/(?P<ix>[0-9a-f]{1,8})/(?P<ib>[01])/(?P<in>[0-9]{1,10})/(?P<i0>[0-9a-f]{1,8})/(?P<i1>[0-9a-f]{1,8})/(?P<i2>[0-9a-f]{1,8})/(?P<ic>[01])/(?P<nb>[0-9]{1,10})/(?P<ns>[0-9]{1,10})/(?P<bi>[0-9]{1,10})/(?P<bo>[0-9]{1,10})/(?P<bpv>[0-9]{1,10})/(?P<rs>[0-9]{1,10}) gclk=(?P<cg_r>[01])/(?P<cg_x>[0-9a-f]{1,8})/(?P<cg_a>[0-9]{1,10})/(?P<cg_v>[01])/(?P<cg_s>-?[0-9]{1,10})/(?P<cg_p>[01])/(?P<cg_rd>[0-9]{1,10})/(?P<cg_fv>[01])/(?P<cg_f>[0-9]{1,10})/(?P<cg_gv>[01])/(?P<cg_g>-?[0-9]{1,10})/(?P<cg_hv>[01])/(?P<cg_h>-?[0-9]{1,10})/(?P<cg_b>[0-9]{1,10})/(?P<cg_bp>[0-9]{1,10})/(?P<cg_be>[0-9]{1,10})/(?P<cg_bn>-?[0-9]{1,10})/(?P<cg_en>-?[0-9]{1,10}) ahb=(?P<ha_r>[01])/(?P<ha_x>[0-9a-f]{1,8}) timer=(?P<ct_r>[01])/(?P<ct_x>[0-9a-f]{1,8})/(?P<ct_rr>[01])/(?P<ct_reset>[0-9a-f]{1,8})/(?P<ct_gr>[01])/(?P<ct_gx>[0-9a-f]{1,8})/(?P<ct_o>[01])/(?P<ct_a>[0-9]{1,10})/(?P<ct_n>[0-9]{1,10})/(?P<ct_s>[01]) girqm=(?P<gi_r>[01])/(?P<gi_x>[0-9a-f]{1,8})/(?P<gi_io>[01])/(?P<gi_ar>[01])/(?P<gi_k>-?[0-9]{1,10})/(?P<gi_id>[0-9]{1,10})/(?P<gi_src>[0-9]{1,10})/(?P<gi_m>[01]) gobs=(?P<go_mask>[0-9a-f]{1,8})/(?P<go_ctrl>[0-9a-f]{1,8})/(?P<go_prio>[0-9a-f]{1,8})/(?P<go_cfg>[0-9a-f]{1,8})/(?P<go_en>[01])/(?P<go_want>[0-9a-f]{1,16})/(?P<go_route>[0-9a-f]{1,16})/(?P<go_group>[01])/(?P<go_mod>[01])/(?P<go_type>[0-9]{1,10}) acr=(?P<ac_flags>[0-7])/(?P<ac_before>[0-9a-f]{1,8})/(?P<ac_after>[0-9a-f]{1,8}) gctl=(?P<gc_flags>[0-9a-f]{1,3})/(?P<gc_cr0>[0-9a-f]{1,8})/(?P<gc_gfsr>[0-9a-f]{1,8})/(?P<gc_rb>[0-9a-f]{1,8})/(?P<gc_sync>[0-9a-f]{1,8})/(?P<gc_reads>[0-9]{1,4})/(?P<gc_io>[0-9a-f]{1,8})/(?P<gc_arm>[0-9a-f]{1,8}); PID1 EL0; GMU GPU off')


def inspect_page(page, expected_run_id, before=None):
    if len(page) != PAGE_BYTES or len(expected_run_id) != 16:
        raise ValueError('exact4096-byte archived page and16-byte artifact tag required')
    magic, run_id, length, crc, text = struct.unpack('<8s16sII512s', page[:RECORD_BYTES])
    if magic != MAGIC or run_id != expected_run_id:
        raise ValueError('record identity differs')
    if not 0 < length < 512 or text[length] != 0:
        raise ValueError('record length/terminator differs')
    raw = bytearray(page[:RECORD_BYTES])
    raw[28:32] = b'\0' * 4
    if zlib.crc32(raw) != crc:
        raise ValueError('record CRC differs')
    if any(page[RECORD_BYTES:]):
        raise ValueError('nonzero bytes outside unchanged544-byte record')
    message = text[:length].decode('utf-8', errors='replace')
    freshness = 'not checked: no archived pre-trial page'
    if before is not None:
        if len(before) != PAGE_BYTES:
            raise ValueError('exact4096-byte archived pre-trial page required')
        if before == page or before[:24] == MAGIC + expected_run_id:
            raise ValueError('artifact tag already present before trial; stale/reused record')
        freshness = 'before/after local pages differ; artifact tag absent before'
    unavailable=message=='K80 domain: unavailable; PID1 EL0; GMU GPU off'
    if unavailable:
        actual=None;clock=False;domain=False;maps=False;cx=False;power=False;pm=False;probe=False;gclk=False;ahb=False;timer=False;girq=False;cfg=False;active_fault_control=False
    else:
        m=PATTERN.fullmatch(message)
        if not m:raise ValueError('not this scoped clock/domain resource record')
        hexfields={'hs','ds','ks','cs','ss','ms','px','qx','vx','ix','i0','i1','i2','cg_x','ha_x','ct_x','ct_reset','ct_gx','gi_x','go_mask','go_ctrl','go_prio','go_cfg','go_want','go_route','ac_before','ac_after','gc_flags','gc_cr0','gc_gfsr','gc_rb','gc_sync','gc_io','gc_arm'}
        v={k:int(x,16 if k in hexfields else 10) for k,x in m.groupdict().items()}
        if any(not -(1<<31)<=v[k]<(1<<31) for k in ['ls','ln','ps','bn','en','cg_s','cg_g','cg_h','cg_bn','cg_en','gi_k']):raise ValueError('actual signed list result outside int32')
        if any(v[k]>0xffffffff for k in ['gh','gn','gc']):raise ValueError('actual graph count outside uint32')
        if (v['gr'] and v['ga']>6) or (v['lr'] and v['la']>3):raise ValueError('actual returned graph/list enum outside source domain')
        ret=lambda k:bool(v[k])
        scalar=lambda k,s:{'returned':ret(k),'raw':v[s] if ret(k) else None}
        clock=bool(v['ur'] and v['uc'] and v['gr'] and v['gd'] and v['lr'] and v['la']==3)
        domain=bool(clock and all(v[k] and v[s]==0 for k,s in [('hr','hs'),('dr','ds'),('kr','ks'),('cr','cs'),('sr','ss')]) and v['xr'] and v['xd'] and v['nr'] and v['nd'])
        actual={'gpucc':{'returned':ret('ur'),'complete':ret('uc') if v['ur'] else None},
          'graph':{'returned':ret('gr'),'assessment':v['ga'] if v['gr'] else None,'hardware_constructed':v['gh'] if v['gr'] else None,'namespace_records':v['gn'] if v['gr'] else None,'cores_registered':v['gc'] if v['gr'] else None,'complete':ret('gd') if v['gr'] else None},
          'list':{'returned':ret('lr'),'assessment':v['la'] if v['lr'] else None,'raw_available':ret('lv') if v['lr'] else None,'raw':v['ls'] if v['lr'] and v['lv'] else None,'entries_returned':v['ln'] if v['lr'] else None},
          'hub':scalar('hr','hs'),'ddr':scalar('dr','ds'),'core_inputs':scalar('kr','ks'),
          'cx_probe':{'returned':ret('xr'),'attempted':ret('xa') if v['xr'] else None,'configuration_store_returned':ret('xc') if v['xr'] else None,'retain_update_returned':ret('xt') if v['xr'] else None,'native_prefix_returned':ret('xd') if v['xr'] else None},
          'cx_core':scalar('cr','cs'),'completion':{'returned':ret('nr'),'registered':ret('nd') if v['nr'] else None},'smmu_power_resources':scalar('sr','ss'),'CPU_register_mappings':scalar('mr','ms')}
        maps=bool(domain and v['mr'] and v['ms']==0)
        if v['pr'] and (v['pw']>3 or v['pd']>2 or v['pk']>3):raise ValueError('returned CX result outside retained enum domains')
        if v['pr'] and v['pa'] and v['pk'] in (1,2) and v['px']>0xffffffff:raise ValueError('actual CX32 status outside uint32')
        actual['CX_primary']={'returned':ret('pr'),'wait_assessment':v['pw'] if v['pr'] else None,'wait_raw_available':ret('pv') if v['pr'] else None,'wait_raw':v['ps'] if v['pr'] and v['pv'] else None,'regulator_disposition':v['pd'] if v['pr'] else None,'regulator_domain':v['pk'] if v['pr'] else None,'regulator_raw_available':ret('pa') if v['pr'] else None,'regulator_raw':v['px'] if v['pr'] and v['pa'] else None}
        cx=bool(maps and v['pr'] and v['pw']==1 and v['pd']==0)
        if v['qr'] and (v['qd']>2 or v['qk']>3):raise ValueError('returned power result outside source enum domains')
        if v['qr'] and v['qa'] and v['qk'] in (1,2) and v['qx']>0xffffffff:raise ValueError('actual power32 status outside uint32')
        actual['SMMU_source_power']={'returned':ret('qr'),'disposition':v['qd'] if v['qr'] else None,'domain':v['qk'] if v['qr'] else None,'raw_available':ret('qa') if v['qr'] else None,'raw':v['qx'] if v['qr'] and v['qa'] else None}
        actual['SMMU_native_held_PM']={'returned':ret('vr'),'raw':v['vx'] if v['vr'] else None}
        power=bool(cx and v['qr'] and v['qd']==0)
        pm=bool(power and v['vr'] and v['vx']==0)
        if v['ir'] and v['in']>3:raise ValueError('actual identification prefix exceeds three source reads')
        actual['SMMU_capability_probe']={'returned':ret('ir'),'raw':v['ix'] if v['ir'] else None,'io_bound':ret('ib') if v['ir'] else None,'identification_reads':v['in'] if v['ir'] else None,'identification':[v['i0'] if v['ir'] and v['in']>0 else None,v['i1'] if v['ir'] and v['in']>1 else None,v['i2'] if v['ir'] and v['in']>2 else None],'capabilities_ready':ret('ic') if v['ir'] else None,'banks':v['nb'] if v['ir'] and v['ic'] else None,'s2banks':v['ns'] if v['ir'] and v['ic'] else None,'S1_input_bits':v['bi'] if v['ir'] and v['ic'] else None,'S1_output_bits':v['bo'] if v['ir'] and v['ic'] else None,'physical_output_bits':v['bpv'] if v['ir'] and v['ic'] else None,'register_shift':v['rs'] if v['ir'] and v['ic'] else None}
        probe=bool(pm and v['ir'] and v['ix']==0 and v['ib'] and v['in']==3 and v['ic'])
        if v['cg_r'] and (v['cg_a']>7 or v['cg_rd']>3 or v['cg_b']>3 or v['cg_bp']>5 or v['cg_be']>3 or v['cg_f']>0xffffffff):raise ValueError('returned GMU clock result outside source domain')
        actual['GMU_cold_clocks']={'returned':ret('cg_r'),'raw':v['cg_x'] if v['cg_r'] else None,'assessment':v['cg_a'] if v['cg_r'] else None,'source_return_available':ret('cg_v') if v['cg_r'] else None,'source_return':v['cg_s'] if v['cg_r'] and v['cg_v'] else None,'state_published':ret('cg_p') if v['cg_r'] else None,'RDPM_assessment':v['cg_rd'] if v['cg_r'] else None,'source_frequency_available':ret('cg_fv') if v['cg_r'] else None,'source_frequency_Hz':v['cg_f'] if v['cg_r'] and v['cg_fv'] else None,'GMU_rate_return':v['cg_g'] if v['cg_r'] and v['cg_gv'] else None,'HUB_rate_return':v['cg_h'] if v['cg_r'] and v['cg_hv'] else None,'bulk_assessment':v['cg_b'] if v['cg_r'] else None,'prepare_assessment':v['cg_bp'] if v['cg_r'] else None,'enable_assessment':v['cg_be'] if v['cg_r'] else None,'prepare_entries':v['cg_bn'] if v['cg_r'] else None,'enable_entries':v['cg_en'] if v['cg_r'] else None}
        actual['GMU_AHB_source']={'returned':ret('ha_r'),'raw':v['ha_x'] if v['ha_r'] else None}
        gclk=bool(probe and v['cg_r'] and v['cg_x']==0 and v['cg_a']==7 and v['cg_v'] and v['cg_s']==0 and v['cg_p'] and v['cg_b']==3 and v['cg_bn']==v['ln'] and v['cg_en']==v['ln'])
        ahb=bool(gclk and v['ha_r'] and v['ha_x']==0)
        if v['ct_o'] and (v['ct_a']>3 or v['ct_n']>16):raise ValueError('actual timer progress outside source domain')
        actual['CX_timer']={'returned':ret('ct_r'),'raw':v['ct_x'] if v['ct_r'] else None,'CM3_reset_read_returned':ret('ct_rr') if v['ct_r'] else None,'CM3_reset':v['ct_reset'] if v['ct_r'] and v['ct_rr'] else None,'GX_state_read_returned':ret('ct_gr') if v['ct_r'] else None,'GX_state':v['ct_gx'] if v['ct_r'] and v['ct_gr'] else None,'operation_returned':ret('ct_o') if v['ct_r'] else None,'assessment':v['ct_a'] if v['ct_r'] and v['ct_o'] else None,'samples':v['ct_n'] if v['ct_r'] and v['ct_o'] else None,'seed_available':ret('ct_s') if v['ct_r'] and v['ct_o'] else None}
        timer=bool(ahb and v['ct_r'] and v['ct_x']==0 and v['ct_rr'] and (v['ct_reset']&1) and v['ct_gr'] and (v['ct_gx']&3)==3 and v['ct_o'] and v['ct_a']==3 and v['ct_n']==16 and v['ct_s'])
        actual['SMMU_global_masked_IRQ']={'returned':ret('gi_r'),'raw':v['gi_x'] if v['gi_r'] else None,'readonly_IO_bound':ret('gi_io') if v['gi_r'] else None,'attach_returned':ret('gi_ar') if v['gi_r'] else None,'attach_KERN_raw':v['gi_k'] if v['gi_r'] and v['gi_ar'] else None,'INTID':v['gi_id'] if v['gi_r'] and v['gi_ar'] else None,'source_index':v['gi_src'] if v['gi_r'] and v['gi_ar'] else None,'registered_masked':ret('gi_m') if v['gi_r'] else None}
        girq=bool(timer and v['gi_r'] and v['gi_x']==0 and v['gi_io'] and v['gi_ar'] and v['gi_k']==0 and 32<=v['gi_id']<1020 and v['gi_src']==0 and v['gi_m'])
        flags=v['ac_flags']
        if flags not in (0,1,3,7):raise ValueError('nonsequential actual cfg-probe operations')
        actual['SMMU_nonsecure_cfg_probe']={'read_before_returned':bool(flags&1),'write_returned':bool(flags&2),'read_after_returned':bool(flags&4),'sACR_before':v['ac_before'] if flags&1 else None,'sACR_after':v['ac_after'] if flags&4 else None,'cache_lock_clear':not bool(v['ac_after']&(1<<26)) if flags&4 else None}
        cfg=bool(timer and flags==7 and not (v['ac_after']&(1<<26)))
        gc={k:v[key] for k,key in [('flags','gc_flags'),('cr0_before','gc_cr0'),('gfsr','gc_gfsr'),('cr0_readback','gc_rb'),('sync_status','gc_sync'),('last_io_raw','gc_io'),('arm_raw','gc_arm')]}
        gc['sync_reads']=v['gc_reads']
        if gc['flags'] & ~0x1ff or gc['sync_reads']>4096:
            raise ValueError('global fault-control result outside source-defined bounds')
        actual['SMMU_global_fault_control']={
            'attempted':bool(gc['flags']&1),'CR0_before_returned':bool(gc['flags']&2),
            'GFSR_returned':bool(gc['flags']&4),'active_controller':bool(gc['flags']&8),
            'sync_write_returned':bool(gc['flags']&16),'CR0_write_returned':bool(gc['flags']&32),
            'CR0_readback_returned':bool(gc['flags']&64),'IRQ_arm_returned':bool(gc['flags']&128),
            'complete_returned':bool(gc['flags']&256),'CR0_before':gc['cr0_before'],
            'GFSR':gc['gfsr'],'CR0_readback':gc['cr0_readback'],'sync_status':gc['sync_status'],
            'sync_reads':gc['sync_reads'],'last_MMIO_raw':gc['last_io_raw'],'IRQ_arm_raw':gc['arm_raw'],
            'context_fault_bits_unchanged':(gc['cr0_readback']&0x30)==(gc['cr0_before']&0x30),
            'IRQ_delivery_proven':False}
        active_fault_control=bool(girq and gc['flags']==0x1ff and gc['gfsr']==0 and
            gc['cr0_readback']==(gc['cr0_before']|0x06) and not (gc['sync_status']&1) and
            gc['sync_reads']>=1 and gc['last_io_raw']==0 and gc['arm_raw']==0)
        mask=v['go_mask'];obs=lambda name,bit:v[name] if mask&bit else None
        actual['SMMU_global_masked_IRQ']['actual_GIC_readback']={'read_mask':mask,'control':obs('go_ctrl',8),'priority':obs('go_prio',64),'configuration':obs('go_cfg',1),'enabled':obs('go_en',4),'route':obs('go_route',2),'requested_route':v['go_want'] if v['gi_ar'] else None,'requested_type':v['go_type'] if v['gi_ar'] else None,'group':obs('go_group',16),'modifier':obs('go_mod',32)}
        if v['qr'] and (v['cp']>12 or v['sp']>8):raise ValueError('returned power source phase outside actual definition')
        actual['SMMU_power_progress']={'caller_phase':v['cp'] if v['qr'] else None,'source_phase':v['sp'] if v['qr'] and v['cp']==12 else None,'bulk_assessment':v['ba'] if v['qr'] and v['sp']>=7 else None,'prepare_assessment':v['bp'] if v['qr'] and v['sp']>=7 else None,'enable_assessment':v['be'] if v['qr'] and v['sp']>=7 else None,'prepare_entries':v['bn'] if v['qr'] and v['sp']>=7 else None,'enable_entries':v['en'] if v['qr'] and v['sp']>=7 else None}
    return {'status':'existing-Hp26-record-byte-envelope-valid','run_id':run_id.hex(),'text':message,'freshness':freshness,'actual_clock_domain':actual,'completed_result_available':not unavailable,'clock_prefix_complete':clock,'domain_resource_prefix_complete':domain,'CPU_register_maps_complete':maps,'CX_primary_prefix_complete':cx,'SMMU_source_power_complete':power,'SMMU_native_held_PM_cycle_complete':pm,'SMMU_capability_probe_complete':probe,'native_GMU_clock_enable_complete':gclk,'native_GMU_AHB_source_complete':ahb,'native_CX_timer_source_complete':timer,'native_SMMU_global_masked_irq_complete':girq,'native_SMMU_nonsecure_cfg_probe_complete':cfg,'native_SMMU_global_fault_control_complete':active_fault_control,'IRQ_delivery_proven':False,'SMMU_mapping_proven':False,'GMU_startup_proven':False,'GPU_execution_proven':False,'native_writer_readback_success_proven':False,'can_support_fresh_trial_when_bound_to_actual_capture_and_bundle':before is not None,'standalone_inspection_proves_native_or_device_execution':False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archived_page', type=pathlib.Path)
    p.add_argument('--expected-run-id', required=True)
    p.add_argument('--before', type=pathlib.Path)
    a = p.parse_args()
    try:
        tag = bytes.fromhex(a.expected_run_id)
        result = inspect_page(a.archived_page.read_bytes(), tag,
                              a.before.read_bytes() if a.before else None)
    except (ValueError, OSError) as e:
        p.error(str(e))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
