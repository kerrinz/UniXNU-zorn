"""Decode the physical FT3683, GPU presentation and CPU timing snapshots."""

import re
import struct
import zlib

from inspect_ios26_gpu_progress236 import MAGIC as PANIC_MAGIC, WIRE_LIMIT
from inspect_ios26_scroll309 import MENU_MAGIC, split_scroll309
from inspect_ios26_ui_manual277 import UI_MAGIC as MANUAL_MAGIC, inspect_progress as inspect_manual


MAGIC = b'K80FT313'
COUNTERS = ('polls', 'read_successes', 'decoded', 'accepted', 'forced_releases', 'downs',
            'moves', 'lifts', 'seen_ids', 'max_active', 'edge_downs', 'multi_contact_samples')
PRESENT_WORDS = 160
TOUCH_WORDS = 1 + len(COUNTERS)
SAMPLES = 9
PACKET_BYTES = 32 + 4 * (PRESENT_WORDS + SAMPLES * TOUCH_WORDS)
COST_MAGIC = b'K80FT317'
PANEL_MAGIC = b'K80FT318'
TE_MAGIC = b'K80FT320'
HANDOFF_MAGIC = b'K80FT321'
RESOURCES_MAGIC = b'K80FT322'
LEASE_MAGIC = b'K80FT325'
CLOCK_MAGIC = b'K80FT334'
HELD_DPU_MAGIC = b'K80FT335'
DISPLAY_SMMU_MAGIC = b'K80FT336'
DISPLAY_SMMU_TRANSPORT_MAGIC = b'K80FT337'
DISPLAY_SMMU_APERTURE_MAGIC = b'K80FT338'
DISPLAY_TRANSFER_MAGIC = b'K80FT339'
DISPLAY_AUTOREFRESH_MAGIC = b'K80FT340'
DISPLAY_RUNTIME_FRAME_MAGIC = b'K80FT341'
DISPLAY_RUNTIME_SCENE_MAGIC = b'K80FT342'
DISPLAY_CADENCE_MAGIC = b'K80FT343'
DISPLAY_ATTRIBUTION_MAGIC = b'K80FT344'
DISPLAY_SCANOUT_ALIAS_MAGIC = b'K80FT345'
DISPLAY_SCANOUT_FLIP_MAGIC = b'K80FT346'
DISPLAY_PERIOD_COMPARE_MAGIC = b'K80FT347'
DISPLAY_LIVE_SCANOUT_MAGIC = b'K80FT348'
DISPLAY_SCANOUT_PHASE_MAGIC = b'K80FT349'
DISPLAY_WRITER_GATE_MAGIC = b'K80FT350'
DISPLAY_LIVE_2TE_MAGIC = b"K80FT357"
DISPLAY_2TE_MAGIC = b"K80FT356"
DISPLAY_ROWS_MAGIC = b"K80FT355"
DISPLAY_CONTENT_MAGIC = b"K80FT354"
DISPLAY_DSI_IDLE_MAGIC = b"K80FT353"
DISPLAY_TOPOLOGY_MAGIC = b"K80FT352"
DISPLAY_WCOMB_MAGIC = b'K80FT351'
COST_FIELDS = ('schema', 'copied_frames', 'uptime_ms', 'frame', 'stage', 'queue_us', 'beat_us',
               'lease_wall_us', 'lease_call_us', 'acquire_us', 'show_us', 'attempts', 'pending',
               'terminal', 'faults', 'producer_fence')
COST_TOTALS = ('copied_frames', *COST_FIELDS[5:14])
COST_BYTES = 4 * (1 + len(COST_FIELDS))
PANEL_FIELDS = ('status', 'uptime_ms', 'gcc_ahb', 'core_domain', 'core_domain_config', 'ahb_clock',
                'mdp_clock', 'vsync_clock', 'interface_status', 'tear_enable', 'tear_read_count',
                'tear_write_line', 'interface_frame_count', 'mdp_frame_count', 'video_line')
PANEL_BYTES = 4 * len(PANEL_FIELDS)
COST_END = PACKET_BYTES + SAMPLES * COST_BYTES
PANEL_END = COST_END + SAMPLES * PANEL_BYTES
TE_EDGE_LIMIT = 32
TE_FIELDS = ('status', 'start_uptime_ms', 'initial_ctl', 'final_ctl', 'elapsed_us',
             'polls', 'max_gap_us', 'falling_edges')
TE_BYTES = 4 * (len(TE_FIELDS) + TE_EDGE_LIMIT)
TE_END = PANEL_END + TE_BYTES
HANDOFF_FIELDS = ('status', 'uptime_ms', 'GOP_physical', 'GOP_stride', 'gcc_ahb',
                  'core_domain', 'core_config', 'ahb_clock', 'mdp_clock', 'vsync_clock',
                  'active_ctl_mask', 'active_fetch_mask')
CTL_FIELDS = ('interface_active', 'fetch_active', 'top', 'flush')
PIPE_FIELDS = ('address', 'source_size', 'stride', 'format', 'operation')
PIPE_BITS = (16, 17, 18, 19, 0, 1, 2, 3, 4, 5)
HANDOFF_BYTES = 4 * (len(HANDOFF_FIELDS) + 6 * len(CTL_FIELDS) + len(PIPE_BITS) * len(PIPE_FIELDS))
HANDOFF_END = TE_END + HANDOFF_BYTES
BCM_NAMES = ('SH1', 'CN0', 'CN1')
ARC_NAMES = ('cx.lvl', 'mmcx.lvl', 'mx.lvl')
RESOURCES_BYTES = 4 * (5 * len(BCM_NAMES) + 12 * len(ARC_NAMES))
RESOURCES_END = HANDOFF_END + RESOURCES_BYTES
LEASE_FIELDS = ('status', 'uptime_ms', 'acquire_raw', 'release_raw', 'gcc_before', 'gcc_held',
                'gcc_after', 'acquire_steps', 'release_steps')
LEASE_STATES = ('not_run', 'clock_unavailable', 'acquire_failed', 'held_clock_unavailable',
                'release_failed', 'after_clock_unavailable', 'returned')
LEASE_BYTES = 4 * len(LEASE_FIELDS)
CLOCK_FIELDS = ('status', 'gcc_ahb_before', 'gcc_axi', 'core_domain',
                'core_domain_config', 'ahb_clock', 'mdp_clock', 'vsync_clock',
                'gcc_ahb_after')
CLOCK_STATES = ('not_run', 'gcc_unavailable', 'interface_vote_absent',
                'dispcc_unavailable', 'interface_vote_changed', 'sampled')
CLOCK_BYTES = 4 * len(CLOCK_FIELDS)
LAYOUTS = {313: (MAGIC, PACKET_BYTES), 317: (COST_MAGIC, COST_END),
           318: (PANEL_MAGIC, PANEL_END), 320: (TE_MAGIC, TE_END),
           321: (HANDOFF_MAGIC, HANDOFF_END), 322: (RESOURCES_MAGIC, RESOURCES_END),
           325: (LEASE_MAGIC, RESOURCES_END + LEASE_BYTES),
           334: (CLOCK_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           335: (HELD_DPU_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           336: (DISPLAY_SMMU_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           337: (DISPLAY_SMMU_TRANSPORT_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           338: (DISPLAY_SMMU_APERTURE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           339: (DISPLAY_TRANSFER_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           340: (DISPLAY_AUTOREFRESH_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           341: (DISPLAY_RUNTIME_FRAME_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           342: (DISPLAY_RUNTIME_SCENE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           343: (DISPLAY_CADENCE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           344: (DISPLAY_ATTRIBUTION_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           345: (DISPLAY_SCANOUT_ALIAS_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           346: (DISPLAY_SCANOUT_FLIP_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           347: (DISPLAY_PERIOD_COMPARE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           348: (DISPLAY_LIVE_SCANOUT_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           349: (DISPLAY_SCANOUT_PHASE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           350: (DISPLAY_WRITER_GATE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           351: (DISPLAY_WCOMB_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           352: (DISPLAY_TOPOLOGY_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           353: (DISPLAY_DSI_IDLE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           354: (DISPLAY_CONTENT_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           355: (DISPLAY_ROWS_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           356: (DISPLAY_2TE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           357: (DISPLAY_LIVE_2TE_MAGIC, RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           358: (b"K80FT358", RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           359: (b"K80FT359", RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           360: (b"K80FT360", RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           361: (b"K80FT361", RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           362: (b"K80FT362", RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           363: (b"K80FT363", RESOURCES_END + LEASE_BYTES + CLOCK_BYTES),
           367: (b"K80FT367", RESOURCES_END + LEASE_BYTES + CLOCK_BYTES)}


def display_lease(packet):
    values = struct.unpack_from('<9I', packet, RESOURCES_END - 8)
    status, _, acquire, release, before, held, after, acquire_steps, release_steps = values
    if not any(values):
        return None
    acquire_prefix = (0, 1, 3, 7, 15, 31, 63, 127)
    release_prefix = (0, 1, 65, 69, 77, 93, 125, 253)
    if (status not in range(1, len(LEASE_STATES)) or
            acquire_steps not in acquire_prefix or release_steps not in release_prefix or
            bool(acquire) != (status == 2) or bool(release) != (status == 4) or
            (acquire_steps == 127) != (status >= 3) or
            (release_steps == 253) != (status >= 5) or
            (status < 4 and (release_steps or held)) or (status < 6 and after) or
            (status == 1 and (before or acquire_steps))):
        raise ValueError('Display register resource lease states differ')
    record = dict(zip(LEASE_FIELDS, values))
    record['result'] = LEASE_STATES[status]
    record['gcc_ahb_running'] = {name: (record[name] & 0x80000001) == 1
                                for name, minimum in (('gcc_before', 2), ('gcc_held', 4), ('gcc_after', 6))
                                if status >= minimum}
    return record


def display_clock_state(packet, lease):
    values = struct.unpack_from('<9I', packet, RESOURCES_END + LEASE_BYTES - 8)
    if not any(values):
        return None
    status, before, *_, after = values
    if (not lease or lease['acquire_steps'] != 127
            or not 1 <= status < len(CLOCK_STATES)
            or (status == 2 and (before & 1 or any(values[3:])))
            or (status >= 3 and not before & 1)
            or (status == 3 and after)
            or (status == 4 and after & 1)
            or (status == 5 and not after & 1)):
        raise ValueError('Display clock observation differs from its held lease')
    record = dict(zip(CLOCK_FIELDS, values))
    record['result'] = CLOCK_STATES[status]
    record['gcc_ahb_running_before'] = (before & 0x80000001) == 1
    record['gcc_ahb_running_after'] = status >= 4 and (after & 0x80000001) == 1
    return record


def display_resources(packet):
    at = HANDOFF_END - 8
    if not any(packet[at:at + RESOURCES_BYTES]):
        return None

    def row(name, words):
        status, address, size, *aux = words
        if status not in (1, 2, 3) or (status != 2 and any(words[1:])):
            raise ValueError(f'Display CommandDB status or failed resource data differs for {name}')
        if status == 2 and (not address or address & 3):
            raise ValueError(f'Display CommandDB address differs for {name}')
        return dict(status=status, address=address, aux_bytes=size), aux

    bcm = {}
    for name in BCM_NAMES:
        resource, (unit, fields) = row(name, struct.unpack_from('<5I', packet, at))
        at += 20
        if resource['status'] == 2 and not 8 <= resource['aux_bytes'] <= 65535:
            raise ValueError(f'Display BCM AUX length differs for {name}')
        bcm[name] = resource | dict(unit=unit, width=fields & 0xffff, vcd=(fields >> 16) & 0xff,
                                    reserved=fields >> 24)

    arc = {}
    for name in ARC_NAMES:
        resource, aux = row(name, struct.unpack_from('<12I', packet, at))
        at += 48
        count, *packed = aux
        levels = [level for word in packed for level in (word & 0xffff, word >> 16)]
        size = resource['aux_bytes']
        if resource['status'] == 2 and (
                not 1 <= count <= size // 2 <= 16 or size & 1 or any(levels[count:])
                or any(not b or a > b for a, b in zip(levels[:count], levels[1:count]))):
            raise ValueError(f'Display ARC levels differ for {name}')
        arc[name] = resource | dict(levels=levels[:count])
    addresses = [resource['address'] for resource in (*bcm.values(), *arc.values()) if resource['status'] == 2]
    return dict(bcm=bcm, arc=arc, all_resolved_distinct=len(set(addresses)) == len(BCM_NAMES) + len(ARC_NAMES))


def handoff_sample(packet, first_late_ms):
    at = TE_END - 8
    values = struct.unpack_from(f'<{HANDOFF_BYTES // 4}I', packet, at)
    if not any(values):
        return None
    row = dict(zip(HANDOFF_FIELDS, values))
    if (row['status'] not in (2, 3, 4, 5, 6, 7, 9)
            or (first_late_ms is not None and row['uptime_ms'] > first_late_ms)
            or not 0xfc400000 <= row['GOP_physical'] < 0xfef00000
            or row['GOP_physical'] & 3 or row['GOP_stride'] < 5760 or row['GOP_stride'] & 3
            or row['GOP_stride'] * 3200 > 0xfef00000 - row['GOP_physical']):
        raise ValueError('Early DPU handoff clock or GOP fields differ')
    if row['status'] != 7:
        if any(values[10:]):
            raise ValueError('Early DPU fields were published without a qualified read')
        return row
    if ((row['core_domain'] & 0x80000007) != 0x80000000
            or (row['core_config'] & 0x18000) != 0x10000
            or any((row[key] & 0x80000001) != 1 for key in ('gcc_ahb', 'ahb_clock', 'mdp_clock', 'vsync_clock'))):
        raise ValueError('Early DPU handoff published registers without stable clocks')
    at += 4 * len(HANDOFF_FIELDS)
    active = fetch = 0
    controllers = []
    for index in range(6):
        ctl = dict(zip(CTL_FIELDS, struct.unpack_from('<4I', packet, at)))
        at += 4 * len(CTL_FIELDS)
        if ctl['interface_active'] & 2:
            if ctl['flush']:
                raise ValueError('Early DPU controller still has a pending flush')
            active |= 1 << index
            fetch |= ctl['fetch_active']
        elif any(ctl[key] for key in CTL_FIELDS[1:]):
            raise ValueError('Early DPU inactive controller has secondary data')
        controllers.append(ctl)
    if (active, fetch) != (row['active_ctl_mask'], row['active_fetch_mask']):
        raise ValueError('Early DPU controller and fetch masks differ')
    pipes = {}
    for index, bit in enumerate(PIPE_BITS):
        pipe = dict(zip(PIPE_FIELDS, struct.unpack_from('<5I', packet, at)))
        at += 4 * len(PIPE_FIELDS)
        if fetch & (1 << bit):
            pipes[str(index)] = pipe
        elif any(pipe.values()):
            raise ValueError('Early DPU inactive pipe has source data')
    return row | dict(controllers=controllers, active_pipes=pipes,
                      equal_numeric_GOP_addresses=[
                          index for index, pipe in pipes.items() if pipe['address'] == row['GOP_physical']])


HELD_DPU_FIELDS = ('first_status', 'second_status', 'first_uptime_ms', 'second_uptime_ms',
                   'first_intf_frames', 'first_mdp_frames', 'first_tear_count', 'first_line_count',
                   'second_intf_frames', 'second_mdp_frames', 'second_tear_count', 'second_line_count',
                   'route_status', 'GOP_physical', 'GOP_stride', 'active_ctl_mask', 'active_fetch_mask')
HELD_DPU_STATES = ('not_run', 'clock_state_unavailable', 'fabric_clock_inactive', 'domain_inactive',
                   'display_branch_inactive', 'reset_active', 'interface_unavailable',
                   'clock_changed_during_read', 'window_expired', 'observed')


SMMU_FIELDS = ('status', 'control', 'id0', 'id1')
SMMU_ROUTE_FIELDS = ('mode', 'slot', 'smr', 's2cr', 'cbar', 'cba2r', 'sctlr', 'ttbr0_low', 'ttbr0_high', 'tcr')
SMMU_STATES = ('not_run', 'host_unavailable', 'read_failed', 'unsupported', 'changed', 'observed')
SMMU_TRANSPORT_STATES = ('no_thread_context', 'missing_lock', 'lock_deadline', 'transport_unavailable',
                         'missing_mapping', 'mapping_bounds', 'mapping_physical')
SMMU_MODES = ('invalid', 'unmatched_bypass', 'unmatched_fault', 'stream_bypass', 'stream_fault',
              'context_bypass', 'stage1_enabled', 'other_context')


def display_smmu(values, schema=336):
    count = len(SMMU_FIELDS) + 2 * len(SMMU_ROUTE_FIELDS)
    status, control, id0, id1 = values[:len(SMMU_FIELDS)]
    states = SMMU_STATES + SMMU_TRANSPORT_STATES if schema >= 337 else SMMU_STATES
    if schema >= 338:
        states += ('aperture_unpublished',)
    if (status >= len(states) or (schema >= 337 and status == 1) or
            (schema >= 338 and status in (7, 8)) or any(values[count:]) or
            (status != 5 and any(values[1:]))):
        raise ValueError('Invalid display SMMU state or trailing data')
    if status == 0:
        return None
    result = dict(zip(SMMU_FIELDS, values)) | dict(result=states[status])
    if status != 5:
        return result

    groups, banks, stage2_banks = id0 & 255, id1 & 255, (id1 >> 16) & 255
    extended, supports_extended = bool(control & 8), bool(id0 & 256)
    pages = 1 << (((id1 >> 28) & 7) + 1)
    if (control & 1 or not id0 & (1 << 27) or not groups or not banks or id1 >> 31 or
            (pages + banks) * 4096 > 0xd0000 or stage2_banks > banks or
            (not supports_extended and (extended or ((id0 >> 9) & 15) < 13))):
        raise ValueError('Unexpected display Apps SMMU capabilities')
    routes = []
    for index, sid in enumerate((0x1c00, 0x1c02)):
        at = len(SMMU_FIELDS) + index * len(SMMU_ROUTE_FIELDS)
        raw = values[at:at + len(SMMU_ROUTE_FIELDS)]
        mode, slot, smr, s2cr, cbar, _cba2r, sctlr, *_ = raw
        if slot == 0xffffffff:
            expected = 2 if control & (1 << 10) else 1
            if any(raw[2:]):
                raise ValueError('Unmatched display stream has register data')
        else:
            match_mask = (smr >> 16) & (0xffff if extended else 0x7fff)
            valid = s2cr & (1 << 10) if extended else smr >> 31
            if slot >= groups or not valid or (sid ^ smr) & 0xffff & ~match_mask:
                raise ValueError('Display stream does not match the reported hardware slot')
            stream_type, bank = (s2cr >> 16) & 3, s2cr & 255
            if stream_type in (1, 2):
                expected = stream_type + 2
                if any(raw[4:]):
                    raise ValueError('Bypassed or faulting display stream has context data')
            elif stream_type == 0 and bank < banks:
                if ((cbar >> 16) & 3) == 1 and bank >= stage2_banks and id0 & (1 << 30):
                    expected = 6 if sctlr & 1 else 5
                else:
                    expected = 7
            else:
                raise ValueError('Invalid display stream context')
        if mode != expected:
            raise ValueError('Display stream classification differs from register data')
        routes.append(dict(zip(SMMU_ROUTE_FIELDS, raw)) | dict(sid=sid, interpretation=SMMU_MODES[mode]))
    return result | dict(streams=routes)


def held_dpu_sample(packet, lease, first_late_ms, schema=335):
    offset = TE_END - 8
    values = struct.unpack_from(f'<{HANDOFF_BYTES // 4}I', packet, offset)
    if not any(values):
        return None
    count = len(HELD_DPU_FIELDS) + 6 * len(CTL_FIELDS) + len(PIPE_BITS) * 2
    if not lease or lease['acquire_steps'] != 127 or (schema == 335 and any(values[count:])):
        raise ValueError('Held DPU sample lacks its lease or has nonzero padding')
    result = dict(zip(HELD_DPU_FIELDS, values))
    first, second = values[:2]
    if first not in (1, 2, 3, 4, 5, 6, 7, 9) or not 0 <= second < len(HELD_DPU_STATES):
        raise ValueError('Invalid held DPU status')
    if first != 9 and (second or any(values[2:])):
        raise ValueError('Held DPU sample continued after a failed first read')
    if first == 9 and (second == 0 or result['first_uptime_ms'] < lease['uptime_ms']):
        raise ValueError('Held DPU first sample lacks its acquisition timestamp or second status')
    if second != 9 and (result['second_uptime_ms'] or any(values[8:])):
        raise ValueError('Held DPU sample published an incomplete second read')
    result['first_result'] = HELD_DPU_STATES[first]
    result['second_result'] = HELD_DPU_STATES[second]
    if second != 9:
        return result

    elapsed = result['second_uptime_ms'] - result['first_uptime_ms']
    gop, stride = result['GOP_physical'], result['GOP_stride']
    if (not 120 <= elapsed <= 750
            or (first_late_ms is not None and result['second_uptime_ms'] > first_late_ms)
            or not 0xfc400000 <= gop < 0xfef00000 or gop & 3
            or stride < 5760 or stride & 3 or stride * 3200 > 0xfef00000 - gop
            or result['route_status'] not in (2, 6, 7, 9)):
        raise ValueError('Held DPU window or GOP and route geometry differs')
    result['elapsed_ms'] = elapsed
    result['raw_frame_deltas'] = {
        'intf': (result['second_intf_frames'] - result['first_intf_frames']) & 0xffffffff,
        'mdp': (result['second_mdp_frames'] - result['first_mdp_frames']) & 0xffffffff,
        'tear_read': ((result['second_tear_count'] >> 16) - (result['first_tear_count'] >> 16)) & 0xffff,
    }
    if result['route_status'] != 7:
        if any(values[15:]):
            raise ValueError('Held DPU published invalid route registers')
        return result

    active = fetch = 0
    controllers = []
    at = len(HELD_DPU_FIELDS)
    for index in range(6):
        ctl = dict(zip(CTL_FIELDS, values[at:at + len(CTL_FIELDS)]))
        at += len(CTL_FIELDS)
        if ctl['interface_active'] & 2:
            if ctl['flush']:
                raise ValueError('Held DPU controller has a pending flush')
            active |= 1 << index
            fetch |= ctl['fetch_active']
        elif any(ctl[key] for key in CTL_FIELDS[1:]):
            raise ValueError('Held DPU inactive controller has secondary data')
        controllers.append(ctl)
    if (active, fetch) != (result['active_ctl_mask'], result['active_fetch_mask']):
        raise ValueError('Held DPU controller and fetch masks differ')
    pipes = {}
    for index, bit in enumerate(PIPE_BITS):
        address, pipe_stride = values[at:at + 2]
        at += 2
        if fetch & (1 << bit):
            pipes[str(index)] = dict(address=address, stride=pipe_stride)
        elif address or pipe_stride:
            raise ValueError('Held DPU inactive pipe has source data')
    result.update(controllers=controllers, active_pipes=pipes,
                  equal_numeric_GOP_addresses=[i for i, pipe in pipes.items() if pipe['address'] == gop])
    if schema in (336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
        smmu = display_smmu(values[count:], schema)
        if smmu:
            if not active or not fetch:
                raise ValueError('Display SMMU sample lacks a valid active DPU route')
            result['display_Apps_SMMU'] = smmu
    return result


TRANSFER_FIELDS = ('status', 'sequence', 'retain', 'start_ms', 'latch_us', 'ctl_done_us', 'dsi_done_us',
                   'polls', 'interface_frame_delta', 'auto_config', 'auto_status', 'ctl_irq_enable',
                   'ctl_irq_before', 'dsi_irq_before', 'dsi_irq_last', 'dpu_version', 'dsi_version',
                   'pixel_clock', 'byte_clock', 'byte_intf_clock', 'escape_clock', 'ctl_start_before',
                   'ctl_flush_before', 'dsi_control', 'dsi_clock_control')
TRANSFER_STATES = ('not_run', 'route_unavailable', 'gop_busy', 'lease_unavailable', 'read_unavailable',
                   'existing_activity', 'wrong_topology', 'autorefresh_active', 'arm_failed',
                   'program_uncertain', 'observation_lost', 'timeout', 'transfer_observed')
AUTO_TRANSFER_FIELDS = ('status', 'sequence', 'retain', 'start_ms', 'latch_us', 'auto_kickoff_us', 'dsi_done_us',
                        'polls', 'interface_frame_delta', 'auto_config', 'auto_status', 'tear_irq_enable',
                        'tear_irq_before', 'dsi_irq_before', 'dsi_irq_last', 'tear_irq_last', 'write_line_before',
                        'write_line_last', 'maximum_poll_gap_us', 'interface_frame_before',
                        'pixel_clock', 'byte_clock', 'byte_intf_clock', 'escape_clock', 'evidence')


def check_transfer_route(held, lease, start, retain):
    route = (held or {}).get('display_Apps_SMMU') or {}
    if (not held or held.get('active_ctl_mask') != 1 or held.get('active_fetch_mask') != 0x30000
            or held.get('GOP_physical') != 0xfc400000 or held.get('GOP_stride') != 5760
            or route.get('result') != 'observed' or len(route.get('streams', ())) != 2
            or any(row['interpretation'] != 'context_bypass' or row['slot'] != 3 or
                   row['s2cr'] != 3 or row['smr'] != 0x80021c00 for row in route['streams'])
            or start < held.get('second_uptime_ms', 0)
            or (retain and (lease['result'] != 'release_failed' or lease['release_steps']))):
        raise ValueError('CTL0/DSI0 sequence lacks its inherited route or correct lease retirement')


def display_transfer(packet, lease, held):
    words = struct.unpack_from(f'<{TE_BYTES // 4}I', packet, PANEL_END - 8)
    if not any(words):
        return None
    status, seq, retain, start, latch, ctl, dsi, polls, delta = words[:9]
    if (not 1 <= status < len(TRANSFER_STATES) or any(words[len(TRANSFER_FIELDS):])
            or not lease or lease['acquire_steps'] != 127 or polls > 50
            or max(latch, ctl, dsi) > 50000 or (not polls and (latch or ctl or dsi))
            or seq != int(status >= 9) or retain != int(9 <= status <= 11)
            or (not seq and any(words[2:9])) or (status != 12 and delta)):
        raise ValueError('Invalid CTL0/DSI0 transfer state')
    if seq:
        check_transfer_route(held, lease, start, retain)
    if status == 12 and (not (latch and ctl and dsi) or not words[14] & 0x100 or words[14] & 0x1000000):
        raise ValueError('CTL0/DSI0 completed sequence lacks a new transfer event')
    row = dict(zip(TRANSFER_FIELDS, words))
    row['result'] = TRANSFER_STATES[status]
    for name in ('latch_us', 'ctl_done_us', 'dsi_done_us'):
        row[name] = row[name] - 1 if row[name] else None
    return row


def display_auto_transfer(packet, lease, held, schema=340):
    count = len(AUTO_TRANSFER_FIELDS) if schema in (341, 342) else TE_BYTES // 4
    words = struct.unpack_from(f'<{count}I', packet, PANEL_END - 8)
    if not any(words):
        return None
    status, seq, retain, start, latch, kickoff, dsi, polls, delta = words[:9]
    evidence, gap = words[24], words[18]
    if (not 1 <= status < len(TRANSFER_STATES) or any(words[len(AUTO_TRANSFER_FIELDS):])
            or not lease or lease['acquire_steps'] != 127 or polls > 1350
            or max(latch, kickoff, dsi, gap) > 1350000 or (not polls and (latch or kickoff or dsi or gap))
            or seq != int(status >= 9) or retain != int(9 <= status <= 11)
            or (not seq and any(words[2:9])) or (status != 12 and delta)
            or evidence & ~3 or bool(evidence & 1) != (status >= 10)
            or (kickoff and not evidence & 2)):
        raise ValueError('Invalid INTF1 automatic-transfer state')
    if seq:
        check_transfer_route(held, lease, start, retain)
        if words[9] != 0x8000003c or words[10] or words[11] & 3 or words[13] & 0x1000200:
            raise ValueError('Invalid inherited autorefresh or IRQ ownership')
    if status == 12 and (not (0 < latch <= dsi and 0 < kickoff <= dsi) or evidence != 3
                         or gap > 50000 or words[14] & 0x1000100 != 0x100 or words[15] & 3 != 3
                         or any(value & 0x80000001 != 1 for value in words[20:24])):
        raise ValueError('Autorefresh transfer lacks matched CTL, INTF1 and DSI events')
    row = dict(zip(AUTO_TRANSFER_FIELDS, words))
    row['result'] = 'autorefresh_configuration_changed' if status == 7 else TRANSFER_STATES[status]
    for name in ('latch_us', 'auto_kickoff_us', 'dsi_done_us'):
        row[name] = row[name] - 1 if row[name] else None
    return row


RUNTIME_FRAME_FIELDS = ('status', 'armed_us', 'swap_id', 'producer_fence', 'retired_fence', 'surface_id',
                        'surface_fence', 'copy_generation', 'queued_us', 'copied_us', 'claimed_us',
                        'baseline_signature', 'claimed_signature', 'attempts')
RUNTIME_FRAME_STATES = ('not_run', 'no_baseline', 'publication_closed', 'no_changed_frame', 'frame_claimed', 'route_lost')


def display_runtime_frame(packet, lease, held, transfer, schema=341):
    start = PANEL_END - 8 + 4 * len(AUTO_TRANSFER_FIELDS)
    record = struct.unpack_from(f'<{TE_BYTES // 4 - len(AUTO_TRANSFER_FIELDS)}I', packet, start)
    if not any(record):
        if transfer:
            raise ValueError('Display transfer has no runtime frame')
        return None
    row = dict(zip(RUNTIME_FRAME_FIELDS, record))
    status = row['status']
    if (not 1 <= status < len(RUNTIME_FRAME_STATES) or any(record[len(RUNTIME_FRAME_FIELDS):])
            or not lease or lease['acquire_steps'] != 127 or row['attempts'] > 2500
            or bool(row['armed_us']) != (status not in ((1, 2, 5) if schema == 342 else (1,)))):
        raise ValueError('Invalid runtime display frame state')
    row['result'] = RUNTIME_FRAME_STATES[status]
    if status != 4:
        if transfer or any(record[2:11]) or row['claimed_signature'] or (status in (1, 2, 5) and row['attempts']):
            raise ValueError('Unclaimed runtime display frame carries transfer state')
        return row
    if (not transfer or not held or not row['attempts'] or not row['swap_id'] or not row['surface_id']
            or not row['copy_generation'] or row['baseline_signature'] == row['claimed_signature']
            or not 0 < row['producer_fence'] <= row['surface_fence'] <= row['retired_fence']
            or not held['second_uptime_ms'] * 1000 <= row['armed_us'] <= row['queued_us'] <= row['copied_us'] <= row['claimed_us']
            or row['claimed_us'] >= row['armed_us'] + 50000000
            or (transfer['sequence'] and transfer['start_ms'] < row['claimed_us'] // 1000)):
        raise ValueError('Runtime display frame lacks changed pixels, fence, clock ordering or transfer')
    if transfer['result'] == 'transfer_observed':
        done_ms = transfer['start_ms']
        done_us = transfer['dsi_done_us']
        # The transfer starts are milliseconds in the original v340 format.
        # The bounded interval preserves the omitted sub-millisecond fraction.
        row['submit_to_DSI_observation_min_us'] = done_ms * 1000 + done_us - row['queued_us']
        row['submit_to_DSI_observation_max_us'] = row['submit_to_DSI_observation_min_us'] + 999
    return row


RUNTIME_SCENE_FIELDS = ('status', 'started_ms', 'ended_ms', 'contact_attempts', 'contact_returns', 'first_raw',
                        'lift_raw', 'GOP_unavailable', 'old_copy', 'invalid_ledger', 'unchanged_signature',
                        'claim_deadline', 'readiness_checks', 'last_swap_seen', 'gesture_outcome')
RUNTIME_SCENE_STATES = ('not_run', 'readiness_deadline', 'service_failure', 'gesture_failed', 'gesture_complete')


def display_runtime_scene(packet, frame, transfer):
    raw = struct.unpack_from('<15I', packet, PANEL_END - 8 - PANEL_BYTES)
    if not any(raw):
        if transfer or (frame and frame.get('result') == 'frame_claimed'):
            raise ValueError('Runtime frame has no swipe evidence')
        return None
    row = dict(zip(RUNTIME_SCENE_FIELDS, raw))
    status, start, end, contacts, returned, first, lift = raw[:7]
    reasons = sum(raw[7:12])
    if (not 1 <= status < len(RUNTIME_SCENE_STATES) or not frame
            or end < start or contacts > 17 or returned != contacts
            or row['readiness_checks'] > 301 or raw[-1] > 3
            or (status == 1 and (any(raw[1:12]) or row['last_swap_seen'] or raw[-1]))
            or (status == 2 and (not start or any(raw[3:12]) or row['last_swap_seen'] or raw[-1]))
            or (status == 3 and (not start or not raw[-1] or (not contacts and lift != 0xffffffff)))
            or (status == 4 and (not start or end - start < 1000 or contacts != 17 or first or lift or raw[-1]))
            or (status != 4 and (transfer or frame['attempts'] or row['last_swap_seen']))
            or reasons + int(frame['result'] == 'frame_claimed') != frame['attempts']):
        raise ValueError('Runtime display swipe or rejection counters disagree')
    if frame['armed_us'] and not start * 1000 <= frame['armed_us'] <= end * 1000 + 999:
        raise ValueError('GOP baseline was not captured during the recorded swipe')
    if frame['result'] == 'frame_claimed' and (frame['claimed_us'] < end * 1000 or
                                               row['last_swap_seen'] < frame['swap_id']):
        raise ValueError('Selected GOP frame predates the completed swipe')
    return dict(row, result=RUNTIME_SCENE_STATES[status], physical_touch=False)


CADENCE_FIELDS = ('status', 'retain', 'started_ms', 'elapsed_us', 'ready_checks', 'interface_advances',
                  'fresh_dsi', 'unknown_content', 'changed_content', 'repeated_content', 'first_content',
                  'polling_gaps', 'first_dsi_us', 'last_dsi_us', 'last_known_swap', 'last_known_fence')
CADENCE_STATES = ('not_run', 'route_unavailable', 'publication_closed', 'producer_deadline', 'GOP_unavailable',
                  'config_unavailable', 'arm_unavailable', 'interrupted', 'completed')
ATTRIBUTION_WORDS = 10
SCANOUT_ALIAS_WORDS = 6
SCANOUT_FLIP_WORDS = 8
SCANOUT_ALIAS_STATES = ('not_checked', 'property_missing', 'property_invalid', 'firmware_denied',
                        'kernel_geometry_mismatch', 'descriptor_failed', 'mapping_failed',
                        'wrong_alias', 'alias_verified')
SCANOUT_FIRMWARE_STATES = ('no_witness', 'wrong_gop', 'XNU_overlap', 'GCD_unavailable', 'GCD_conflict',
                           'EFI_map_invalid', 'EFI_map_conflict', 'EFI_map_uncovered', 'reserved')


def display_attribution(words, status, matched, last_swap, last_dsi):
    geometry, qualified, rejected, mask, auto, samples, minimum, maximum, lo, hi = words
    width, height = geometry & 0xffff, geometry >> 16
    total = lo | (hi << 32)
    reasons = ('panel_alias', 'logical_extent', 'copy_timestamp', 'gpu_ledger', 'copy_ledger', 'surface_fence')
    if (status == 4 or (status < 5 and any(words))
            or bool(geometry) != bool(qualified or rejected)
            or (qualified and not (1 <= width <= 16384 and 1 <= height <= 16384))
            or bool(rejected) != bool(mask) or mask >= 1 << len(reasons)
            or samples != matched or bool(last_swap) != bool(samples)
            or (samples and (not qualified or not 0 <= minimum <= maximum <= last_dsi
                             or not minimum * samples <= total <= maximum * samples))
            or (samples == 1 and minimum != maximum)
            or (not samples and (minimum or maximum or total))):
        raise ValueError('Inconsistent GOP attribution or copy-to-DSI observation age')
    return dict(logical_extent=[width, height] if geometry else None,
                qualified_copies=qualified, rejected_copies=rejected,
                copy_rejections=[reason for index, reason in enumerate(reasons) if mask & (1 << index)],
                initial_autorefresh_config=auto if status >= 5 else None,
                copy_to_DSI_observed_us=dict(samples=samples, minimum=minimum, maximum=maximum,
                                             total=total, mean=total / samples) if samples else None)


def display_cadence(packet, lease, held, schema=343):
    data = struct.unpack_from(f'<{TE_BYTES // 4}I', packet, PANEL_END - 8)
    extra = ATTRIBUTION_WORDS if schema >= 344 else 0
    core_end = len(CADENCE_FIELDS) + extra
    used_end = core_end + (SCANOUT_ALIAS_WORDS if schema >= 345 else 0)
    used_end += SCANOUT_FLIP_WORDS if schema == 346 else 0
    if any(data[used_end:]):
        raise ValueError('Unexpected data after display timing records')
    if not any(data[:core_end]):
        return None
    status, retain, start, elapsed, checks, advances, fresh, unknown, changed, repeated, first, gaps = data[:12]
    began, end, swap, fence = data[12:16]
    if (not 1 <= status < len(CADENCE_STATES)
            or not lease or lease['acquire_steps'] != 127 or retain not in (0, 1)
            or (retain and status not in (6, 7))
            or (bool(start) != (status >= 5)) or (status < 7 and (elapsed or any(data[5:16])))
            or (status == 8 and (elapsed < 8000000 or retain))
            or checks > 350 or (status >= 4 and not checks)
            or advances > 2048 or fresh > 8100 or gaps > 8100
            or fresh != unknown + changed + repeated + first or first > unknown + 1
            or bool(fresh) != bool(began and end)
            or (fresh and (not start * 1000 <= began <= end or end - began > elapsed))
            or (fresh == 1 and began != end) or (fresh > 1 and began >= end)
            or bool(swap) != bool(fence) or (swap and not (changed or repeated or first))):
        raise ValueError('Inconsistent passive DSI cadence')
    if status >= 5:
        check_transfer_route(held, lease, start, retain)
    row = dict(zip(CADENCE_FIELDS, data))
    row['result'] = CADENCE_STATES[status]
    if extra:
        row.update(display_attribution(data[len(CADENCE_FIELDS):core_end],
                                        status, changed + repeated + first, swap, end))
    return row


def display_scanout_alias(packet, lease):
    offset = PANEL_END - 8 + 4 * (len(CADENCE_FIELDS) + ATTRIBUTION_WORDS)
    status, firmware, page_bytes, pages, physical, extent = struct.unpack_from('<6I', packet, offset)
    if not any((status, firmware, page_bytes, pages, physical, extent)):
        return None
    if (not 1 <= status < len(SCANOUT_ALIAS_STATES) or firmware >= len(SCANOUT_FIRMWARE_STATES)
            or not lease or lease['acquire_steps'] != 127
            or (status <= 2 and firmware) or (status == 3 and not 1 <= firmware < 8)
            or (status == 4 and firmware not in (0, 8))
            or (status >= 5 and (firmware, page_bytes, physical, extent) != (8, 16384, 0xfd800000, 18432000))
            or (status <= 4 and (page_bytes or physical or extent))
            or (status <= 6 and pages) or pages > 1125 or (status == 8 and pages != 1125)):
        raise ValueError('Inconsistent second scanout reservation and CPU alias')
    return dict(result=SCANOUT_ALIAS_STATES[status], firmware=SCANOUT_FIRMWARE_STATES[firmware],
                CPU_page_bytes=page_bytes, verified_CPU_pages=pages, physical=physical,
                bytes=extent, mapped_for_display_DMA=False)


def display_scanout_flip(packet, lease, alias):
    offset = PANEL_END - 8 + 4 * (len(CADENCE_FIELDS) + ATTRIBUTION_WORDS + SCANOUT_ALIAS_WORDS)
    words = struct.unpack_from('<8I', packet, offset)
    status, retain, samples, forward, restore, forward_us, restore_us, hold_ms = words
    if not any(words):
        return None
    states = ('not_run', 'writer_unavailable', 'original_source_unavailable', 'map_unavailable',
              'pattern_readback_failed', 'incomplete', 'restored')
    attempted = status in (5, 6)
    forward_done = forward == 12
    restored = restore == 12
    uncertain = 9 <= forward < 12 or 9 <= restore < 12 or (forward_done and not restored)
    if (not 1 <= status < len(states) or not lease or lease['acquire_steps'] != 127 or retain not in (0, 1)
            or bool(retain) != uncertain or (retain and lease['result'] != 'release_failed')
            or not 0 <= forward <= 12 or not 0 <= restore <= 12
            or (not attempted and any((retain, forward, restore, forward_us, restore_us, hold_ms)))
            or (status < 4 and samples) or (status == 4 and samples > 2)
            or (attempted and (samples != 3 or not forward))
            or (attempted and (not alias or alias['result'] != 'alias_verified'))
            or (not forward_done and (restore or restore_us or hold_ms))
            or (forward_done and (not 0 < forward_us <= 1350000 or hold_ms < lease['uptime_ms']))
            or forward_us > 1350000 or restore_us > 1350000
            or (restored and (not restore_us or not forward_done))
            or (status == 6) != restored):
        raise ValueError('Inconsistent bounded second scanout transfer')
    return dict(result=states[status], retain=bool(retain), pattern_samples=samples,
                forward_status=forward, restore_status=restore, forward_DSI_us=forward_us,
                restore_DSI_us=restore_us, hold_started_ms=hold_ms)


def display_period_compare(packet, lease, held, flip, comparison_TE=4):
    fields = ('status', 'retain', 'started_ms', 'ready_checks', 'entry_state', 'entry_polls',
              'sample_state', 'elapsed_us', 'interface_advances', 'fresh_dsi', 'polling_gaps',
              'first_dsi_us', 'last_dsi_us', 'revert_state', 'revert_polls', 'saved_vsync',
              'measured_config', 'final_config')
    count = len(CADENCE_FIELDS) + ATTRIBUTION_WORDS
    data = struct.unpack_from(f'<{count}I', packet, PANEL_END - 8)
    if not any(data):
        return None
    row = dict(zip(fields, data))
    status, retained, start, ready, entry, entry_polls, sample, elapsed = data[:8]
    advances, fresh, gaps, first, last, revert, revert_polls, saved, measured, final = data[8:18]
    states = ('not_run', 'route_unavailable', 'publication_closed', 'producer_deadline',
              'awaiting_flip', 'entry_refused', 'entry_uncertain', 'observation_uncertain',
              'revert_uncertain', 'compared')
    if (any(data[len(fields):]) or not 1 <= status < len(states) or retained not in (0, 1)
            or bool(retained) != bool((flip or {}).get('retain'))
            or ready > 350 or (status >= 4 and not ready)
            or entry_polls > 25 or revert_polls > 25 or advances > 2048 or fresh > 8100 or gaps > 8100
            or (status <= 4 and (any(data[4:18]) or start))
            or (status == 5 and (entry or entry_polls))
            or (status == 6 and (not 1 <= entry <= 5 or not retained))
            or (status <= 6 and (start or any(data[6:15]) or measured or final))
            or (status >= 5 and (not flip or flip['forward_status'] != 12))
            or (status >= 7 and (not start or entry != 6 or entry_polls < 2 or not saved & (1 << 20)
                                 or measured != (0x80000000 | comparison_TE) or not 1 <= sample <= 4))
            or (status == 7 and (not retained or sample == 4 or revert or revert_polls or final))
            or (status == 8 and (not retained or sample != 4 or revert > 5 or final))
            or (status == 9 and (sample != 4 or revert != 6 or revert_polls < 2 or final != 0x8000003c))
            or (sample == 4 and elapsed < 1500000)
            or (sample < 3 and (elapsed or advances or fresh or gaps or first or last))
            or bool(fresh) != bool(first and last)
            or (fresh and (not start * 1000 <= first <= last or last - first > elapsed))):
        raise ValueError('Inconsistent bounded static cadence observation')
    if status >= 7:
        check_transfer_route(held, lease, start, retained)
    row['result'] = states[status]
    return row


LIVE_FIELDS = ('status', 'retain', 'ready_checks', 'start_us', 'stop_us', 'attempts', 'completed',
               'refused', 'no_pixels', 'cap_reached', 'last_transfer', 'entry_phase', 'restore_phase',
               'restore_transfer', 'restore_DSI_us', 'timing_lost', 'seeded_copies', 'final_config')
LIVE_FRAMES = 32
LIVE_FRAME_WORDS = 4
LIVE_TRACE_OFFSET = COST_END - 8 + PANEL_BYTES
LIVE_STATES = ('not_run', 'route_unavailable', 'publication_closed', 'producer_deadline',
               'writer_unavailable', 'mapping_unavailable', 'entry_refused', 'entry_uncertain',
               'active', 'transfer_uncertain', 'restore_uncertain', 'restored')


def display_live_scanout(packet, lease, held, alias, schema):
    values = struct.unpack_from(f'<{len(LIVE_FIELDS) + LIVE_FRAMES * LIVE_FRAME_WORDS}I',
                                packet, LIVE_TRACE_OFFSET)
    if not any(values):
        return None
    row = dict(zip(LIVE_FIELDS, values))
    status, retain, ready, start, stop, attempts, completed, refused = values[:8]
    no_pixels, capped, last, entry, revert, restored, restored_us, lost, seeded, config = values[8:18]
    full_window = status in (9, 10, 11)
    window_us = 500_000 if schema in (357, 358, 359, 360, 361, 362) else 1_000_000
    if (status not in (1, 2, 3, 4, 5, 6, 7, 9, 10, 11) or retain != int(status in (7, 9, 10))
            or not 0 <= ready <= 350 or (status >= 4 and not ready)
            or attempts > LIVE_FRAMES or attempts != completed + refused + int(status == 9)
            or capped not in (0, 1) or (capped and attempts != LIVE_FRAMES)
            or not 0 <= last <= (13 if schema in (353, 354, 355, 357, 358, 359, 360, 361, 362) else 12) or (last and not attempts)
            or (not full_window and any((start, stop, attempts, no_pixels, capped, last, seeded)))
            or (status <= 6 and entry) or (status == 7 and not 1 <= entry <= 5)
            or (full_window and (entry != 6 or not 0 < start < stop < 300_000_000 or
                                 not window_us - 2 <= stop - start <= window_us + 2))
            or (status < 10 and any((revert, restored, restored_us, config)))
            or (status == 10 and (revert > 6 or restored > 12 or restored_us or
                                  config != (0x8000003c if revert == 6 else 0)))
            or (status == 11 and (revert != 6 or config != 0x8000003c or
                                 (bool(completed & 1) != bool(restored == 12 and restored_us)) or
                                 (not completed & 1 and (restored or restored_us))))
            or (restored_us > 1_350_001 or lost > completed)):
        raise ValueError('Inconsistent bounded compositor scanout record')
    if full_window or status == 7:
        if not lease or not held or not alias or alias['result'] != 'alias_verified':
            raise ValueError('Compositor scanout lacks the retained display lease or second alias')
        check_transfer_route(held, lease, start // 1000 if full_window else held['second_uptime_ms'], retain)
    frames = []
    previous = start
    for index in range(LIVE_FRAMES):
        offset = len(LIVE_FIELDS) + index * LIVE_FRAME_WORDS
        item = values[offset:offset + LIVE_FRAME_WORDS]
        if index >= completed:
            if any(item):
                raise ValueError('Unused compositor-frame slot contains data')
            continue
        swap, queued, done, phases = item
        if not 0 < queued <= done or not previous < done <= stop + 100_000:
            raise ValueError('Compositor-frame completion time differs')
        previous = done
        display = (phases >> 16) * 4
        after_copy = (phases & 0xffff) * 4
        if phases != 0xffffffff and (display > 100_000 or
                done - display < start or done - display > stop + 3 or
                done - display - after_copy + 6 < queued):
            raise ValueError('Compositor-frame stage timestamp differs')
        frames.append(dict(swap=swap, queued_us=queued, completed_us=done,
                           copy_to_program_us=None if phases == 0xffffffff else after_copy,
                           program_to_DSI_us=None if phases == 0xffffffff else display))
    if sum(f['program_to_DSI_us'] is None for f in frames) != lost:
        raise ValueError('Compositor-frame missing phase count differs')
    row.update(result=LIVE_STATES[status], frames=frames)
    return row


PHASE_OFFSET = PACKET_BYTES - 8
PHASE_FIELDS = ('queued_to_selection_us', 'software_pacing_us', 'producer_and_issuer_wait_us',
                'surface_cache_acquire_us', 'CPU_copy_us')
GUARD_FIELDS = ('CTL_busy', 'auto_refresh_busy', 'tear_interrupt_owned', 'DSI_interrupt_owned_or_error',
                'arm_lease_lost', 'arm_ack_failed', 'arm_read_failed', 'arm_status_dirty', 'arm_deadline')


TOPOLOGY_GUARD_FIELDS = ('DPU_version_mismatch', 'CTL_mode_mismatch', 'CTL_route_mismatch',
                         'buffer_pair_mismatch', 'active_VIG_source_mismatch', 'scanout_stride_mismatch',
                         'DSI_version_mismatch', 'DSI_control_mismatch', 'DSI_lane_state_mismatch')


def display_attempt_phases(packet, live, schema):
    count = live['attempts'] if live else 0
    frames = iter(live['frames'] if live else ())
    rows = []
    for index in range(LIVE_FRAMES):
        raw = struct.unpack_from('<4I', packet, PHASE_OFFSET + index * 16)
        if index >= count:
            if any(raw):
                raise ValueError('Unused compositor phase slot contains data')
            continue
        swap, queue_and_beat, wait_and_cache, copy_and_status = raw
        flags = copy_and_status >> 16
        status, guard = flags & 0xf, (flags >> 6) & 0x1ff
        valid, completed = bool(flags & 32), bool(flags & 0x8000)
        topology = schema in (352, 353, 354, 355, 357, 358, 359, 360, 361, 362) and status == 6
        if ((status > (13 if schema in (353, 354, 355, 357, 358, 359, 360, 361, 362) else 12) or (completed and status != 12)) or
                (status == 5 and not 0 < guard < 16) or
                (status == 8 and guard not in (16, 32, 64, 128, 256)) or
                (topology and not guard) or
                (not topology and status not in (5, 8) and guard)):
            raise ValueError('Compositor phase result or refusal guard differs')
        units = (queue_and_beat & 0xffff, queue_and_beat >> 16, wait_and_cache & 0xffff,
                 wait_and_cache >> 16, copy_and_status & 0xffff)
        if not valid and any(units):
            raise ValueError('Missing compositor phase stamp carries durations')
        durations = [64 * unit for unit in units]
        if completed:
            frame = next(frames, None)
            if frame is None or frame['swap'] != swap:
                raise ValueError('Compositor phase success does not match DSI frame')
            if valid:
                remaining = frame['completed_us'] - frame['queued_us'] - (frame['program_to_DSI_us'] or 0)
                remaining -= frame['copy_to_program_us'] or 0
                if sum(durations) > remaining:
                    raise ValueError('Compositor phase durations exceed recorded frame latency')
        names = TOPOLOGY_GUARD_FIELDS if topology else GUARD_FIELDS
        rows.append(dict(attempt=index + 1, swap=swap, status=status, completed=completed,
                         gpu=bool(flags & 16), preflight=[name for bit, name in enumerate(names)
                                                         if guard & (1 << bit)],
                         durations_us=dict(zip(PHASE_FIELDS, durations)) if valid else None))
    if next(frames, None) is not None:
        raise ValueError('Missing compositor phase success')
    return rows


WRITER_GATE_OFFSET = PHASE_OFFSET + LIVE_FRAMES * 16
WRITER_GATE_FIELDS = ('status', 'lock_attempts', 'lock_wait_us', 'writer_flags', 'VIG0_source', 'VIG1_source')
WRITER_GATE_STATES = ('not_requested', 'context_unavailable', 'no_presenter', 'request_pending',
                      'deadline', 'alias_mismatch', 'writer_inactive', 'port_unreadable',
                      'source_mismatch', 'admitted', 'display_uncertain')


def display_writer_gate(packet, live, schema=350):
    values = struct.unpack_from('<6I', packet, WRITER_GATE_OFFSET)
    reserved = WRITER_GATE_OFFSET + 4 * (len(values) + int(schema in (351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362)) + 3 * int(schema in (353, 354, 355, 357, 358, 359, 360, 361, 362)) + int(schema in (354, 355, 357, 358, 359, 360, 361, 362)) + 3 * int(schema in (355, 357, 358, 359, 360, 361, 362)))
    if schema not in (360, 361, 362) and any(packet[reserved:COST_END - 8]):
        raise ValueError('Unused display writer admission bytes differ')
    state, tries, wait, flags, src0, src1 = values
    live_state = live['status'] if live else 0
    if (state >= len(WRITER_GATE_STATES) or tries > 250 or flags > 7
            or (live_state < 4 and any(values))
            or (live_state == 4 and state in (0, 9))
            or (live_state > 4 and state != 9)
            or (state < 4 and (tries or wait))
            or (state in (5, 6, 7, 8, 9, 10) and (not tries or wait >= 250_000))
            or (state in (7, 8, 9) and flags != 1)
            or (state not in (6, 7, 8, 9) and flags)
            or (state == 6 and flags == 1)
            or (state not in (7, 8, 9) and (src0 or src1))
            or (state == 8 and src0 == src1 == 0xfc400000)
            or (state == 9 and (src0 != 0xfc400000 or src1 != 0xfc400000))):
        raise ValueError('Display writer admission trace differs')
    row = dict(zip(WRITER_GATE_FIELDS, values)) | {'result': WRITER_GATE_STATES[state]}
    if schema in (351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
        cache, = struct.unpack_from('<I', packet, WRITER_GATE_OFFSET + 24)
        if cache & ~0xf00 or (state != 9 and cache) or (live_state >= 6 and cache != 0x400):
            raise ValueError('Second buffer mapping option differs')
        row['second_buffer_map_cache_option'] = cache
    if schema in (353, 354, 355, 357, 358, 359, 360, 361, 362):
        attempts, cleared, maximum = struct.unpack_from('<3I', packet, WRITER_GATE_OFFSET + 28)
        refusals = sum(p['status'] == 13 for p in (live or {}).get('attempt_phases', ()))
        if not (0 <= cleared <= attempts <= (live or {}).get('attempts', 0) and refusals <= attempts - cleared):
            raise ValueError('Prior DSI idle wait counts differ')
        if (not attempts and maximum) or (cleared and not maximum):
            raise ValueError('Prior DSI idle wait time differs')
        row['prior_DSI_idle_wait'] = dict(attempts=attempts, reached_idle=cleared, max_elapsed_us=maximum)
    if schema in (355, 357, 358, 359, 360, 361, 362):
        layers, joins, maximum = struct.unpack_from('<3I', packet, WRITER_GATE_OFFSET + 44)
        if joins > 7 * layers or (not layers and maximum) or (layers and state != 9):
            raise ValueError('Scanout row claim counters differ')
        row['dynamic_scanout_rows'] = dict(layers=layers, helper_joins=joins, max_join_us=maximum)
    return row


def touch_gpi_routes(packet):
    raw = struct.unpack_from('<11I', packet, COST_END - 8 - 44)
    status, control = raw[3:5]
    states = ('not_run', 'host_unavailable', 'read_failed', 'unsupported', 'changed', 'observed',
              'no_thread_context', 'missing_lock', 'lock_deadline', 'transport_unavailable',
              'missing_mapping', 'mapping_bounds', 'mapping_physical', 'unpublished')
    routes = ('unmatched_bypass', 'unmatched_fault', 'stream_bypass', 'stream_fault',
              'context_bypass', 'stage1_enabled', 'other_context')
    if status >= len(states) or (status != 5 and any(raw[4:])):
        raise ValueError('K80 GPI/QUP SMMU sample differs from its publication state')
    configs = [None if word == 0xffffffff else word for word in raw[:3]]
    context_states = [None if word is None else (word >> 20) & 15 for word in configs]
    free = False if any(context_states) else None if None in context_states else True
    result = dict(static_GPII=dict(index=0, configs=dict(zip(('tx', 'rx', 'event'), configs)),
                                   states=dict(zip(('tx', 'rx', 'event'), context_states)),
                                   unallocated=free),
                  apps_smmu=dict(status=states[status], global_control=control, streams={}))
    if status != 5:
        return result
    extended = bool(control & 8)
    for offset, name, sid in ((5, 'gpi', 0xb6), (8, 'qup', 0xa3)):
        packed, smr, s2cr = raw[offset:offset + 3]
        slot, route = packed >> 8, packed & 255
        if not 1 <= route <= len(routes) or slot > 255:
            raise ValueError('K80 GPI/QUP SMMU stream encoding differs')
        if slot == 255:
            if smr or s2cr or route != (2 if control & (1 << 10) else 1):
                raise ValueError('K80 GPI/QUP unmatched stream contains a mapping')
        else:
            limit = 0xffff if extended else 0x7fff
            valid = s2cr & (1 << 10) if extended else smr & (1 << 31)
            stream_type = (s2cr >> 16) & 3
            expected_type = 1 if route == 3 else 2 if route == 4 else 0
            if not valid or (sid ^ smr) & 0xffff & ~((smr >> 16) & limit) or route < 3 or stream_type != expected_type:
                raise ValueError('K80 GPI/QUP stream differs from its matched SMMU entry')
        result['apps_smmu']['streams'][name] = dict(
            sid=sid, route=routes[route - 1], slot=None if slot == 255 else slot, smr=smr, s2cr=s2cr)
    return result


def touch_smmu_round_trip(packet, route, *, with_gate=False):
    at = COST_END - 8
    status, attach, detach, banks, fault, *unused = struct.unpack_from('<15I', packet, at)
    if not status:
        if any((attach, detach, banks, fault, *unused)):
            raise ValueError('Unpublished FT3683 SMMU round trip contains samples')
        return {'result': 'not_attempted'}
    details = {}
    if with_gate:
        gate, geometry, *unused = unused
        stages = ('thread_context', 'aperture_unpublished', 'lock_missing', 'lock_busy',
                  'ufs_host_mismatch', 'full_mapping_unavailable', 'geometry_mismatch',
                  'ufs_bank_out_of_range', 'attach_entered')
        if (not 1 <= gate <= len(stages)
                or ((gate == 9) != (attach != 0xffffffff))
                or (gate <= 6 and geometry)
                or (gate >= 8 and (geometry >> 31 or ((geometry >> 28) & 7) != 6))
                or (gate == 9 and not (geometry & 255))):
            raise ValueError('FT3683 SMMU refusal stage differs from attach or geometry')
        details.update(gate=stages[gate - 1], idr1=geometry if gate >= 7 else None)
    gpi_bank, qup_bank = banks & 0xffff, banks >> 16
    not_called = 0xffffffff
    valid_codes = {*range(12), not_called}
    if (status not in (1, 2, 3) or attach not in valid_codes or detach not in valid_codes
            or fault > 3 or any(unused)
            or route['static_GPII']['unallocated'] is not True
            or any(bank >= 96 for bank in (gpi_bank, qup_bank))
            or (banks and gpi_bank == qup_bank)
            or (status == 1 and (attach == 0 or detach != not_called or fault))
            or (status == 2 and (attach or detach or not banks or fault))
            or (status == 3 and (not banks or attach == not_called
                                  or (attach and detach != not_called)
                                  or (not attach and (detach == not_called or (not detach and not fault)))))):
        raise ValueError('FT3683 SMMU round trip status differs')
    streams = route['apps_smmu']['streams']
    restored = all(stream['route'] == 'unmatched_fault' for stream in streams.values()) if streams else None
    return dict(result={1: 'refused', 2: 'released', 3: 'retained'}[status],
                post_sample_unmatched_fault=restored,
                attach_raw=None if attach == not_called else attach,
                detach_raw=None if detach == not_called else detach,
                gpi_bank=gpi_bank if banks else None, qup_bank=qup_bank if banks else None,
                fault_source={0: None, 1: 'global', 2: 'gpi', 3: 'qup'}[fault], **details)


def touch_geni_inventory(packet):
    fields = ('status', 'clock_vote', 'wrapper_version', 'firmware', 'interface', 'sequencer',
              'geometry', 'dma_mode', 'tx_fifo', 'rx_fifo', 'clock_branches')
    states = ('not_run', 'clock_unavailable', 'read_unavailable', 'inconsistent', 'protocol_mismatch',
              'busy_or_dma_mode', 'fifo_disabled', 'unsupported_fifo', 'fifo_observed')
    row = dict(zip(fields, struct.unpack_from('<11I', packet, COST_END - 8 - 44)))
    state, clocks, branches = (row[k] for k in ('status', 'clock_vote', 'clock_branches'))
    flags = branches & 7
    halted = branches >> 8
    votes = (1 << 20) | (1 << 21) | (1 << 26)
    if state >= len(states) or branches & ~0x707 or flags not in (0, 1, 3, 7) or halted & ~flags:
        raise ValueError('FT3683 GENI clock inventory differs')
    if not state and any(row.values()):
        raise ValueError('Unpublished FT3683 GENI inventory contains samples')
    if state == 1 and (any(row[k] for k in fields[2:-1]) or (flags == 7 and not halted)):
        raise ValueError('Gated FT3683 GENI inventory contains engine samples')
    if state >= 2 and (clocks == 0xffffffff or clocks & votes != votes or branches != 7):
        raise ValueError('FT3683 GENI sample lacks the inherited clock votes')
    if state >= 4:
        version = row['wrapper_version']
        major, minor = version >> 28, (version >> 16) & 0xfff
        depth_mask = 0xff if major > 3 or (major == 3 and minor >= 10) else 0x3f
        depth = (row['geometry'] >> 16) & depth_mask
        width = (row['geometry'] >> 24) & 0x3f
        if any(row[k] == 0xffffffff for k in fields[2:-1]):
            raise ValueError('FT3683 GENI inventory contains an invalid controller value')
        if (row['firmware'] >> 8) & 0xff != 1:
            expected = 4
        elif (row['sequencer'] & 0x1001 or row['dma_mode'] & 1
              or row['tx_fifo'] & 0xfffffff or row['rx_fifo'] & 0x1ffffff):
            expected = 5
        elif row['interface'] & 1:
            expected = 6
        elif not version or depth < 4 or width != 32:
            expected = 7
        else:
            expected = 8
        if expected != state:
            raise ValueError('FT3683 GENI result disagrees with the actual register words')
        row.update(tx_fifo_depth=depth, fifo_width_bits=width)
    row['result'] = states[state]
    return row


def display_sampled_rgb(packet, live):
    changed, = struct.unpack_from('<I', packet, WRITER_GATE_OFFSET + 40)
    frames = (live or {}).get('frames', ())
    if changed >> len(frames):
        raise ValueError('Sampled RGB mask includes an unconfirmed swap')
    if live is not None:
        live['sampled_RGB_grid_points'] = 64
        for index, frame in enumerate(frames):
            frame['sampled_RGB_changed'] = bool(changed & (1 << index))


def te_sample(packet, sample_count, last_uptime_ms):
    values = struct.unpack_from(f'<{TE_BYTES // 4}I', packet, PANEL_END - 8)
    if sample_count != SAMPLES:
        if any(values):
            raise ValueError('Unfinished observation contains TE data')
        return None
    row = dict(zip(TE_FIELDS, values))
    count = row['falling_edges']
    edges = values[len(TE_FIELDS):][:count]
    edge_tail = values[len(TE_FIELDS) + count:]
    status = row['status']
    if (not 1 <= status <= 6 or count > TE_EDGE_LIMIT or any(edge_tail)
            or count > row['polls'] or row['polls'] > 16001
            or row['max_gap_us'] > row['elapsed_us']
            or any(not 0 < a < b for a, b in zip(edges, edges[1:]))
            or (edges and not 0 < edges[-1] <= row['elapsed_us'])):
        raise ValueError('TE sample bounds differ')
    if status == 6:
        ctl = row['initial_ctl']
        if (ctl != row['final_ctl'] or (ctl & 0x23c) != 4
                or (ctl & 0x1800) == 0x800 or row['elapsed_us'] < 160000
                or row['start_uptime_ms'] < last_uptime_ms or not row['polls']):
            raise ValueError('TE observation lacks a stable input or complete time window')
    elif status in (1, 3) and (row['start_uptime_ms'] or row['final_ctl']
                              or row['elapsed_us'] or row['polls'] or (status == 1 and row['initial_ctl'])):
        raise ValueError('TE sample has data without entering the polling loop')
    row['falling_edge_offsets_us'] = list(edges)
    row['steady_sample_hz'] = None
    if status == 6 and len(edges) >= 5 and row['max_gap_us'] <= 100:
        periods = [end - start for start, end in zip(edges, edges[1:])]
        mean = (edges[-1] - edges[0]) / len(periods)
        if 4000 <= mean <= 40000 and max(periods) - min(periods) <= max(mean * 0.05, 2 * row['max_gap_us']):
            row['steady_sample_hz'] = 1_000_000 / mean
    return row


def panel_samples(packet, sample_count, schema=318):
    samples = []
    stopped = False
    count = 1 if schema in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362) else SAMPLES - int(schema == 342)
    for index in range(count):
        at = COST_END - 8 + index * PANEL_BYTES
        values = struct.unpack_from('<15I', packet, at)
        if index >= sample_count:
            if any(values):
                raise ValueError('Unused panel timing slot has values')
            continue
        row = dict(zip(PANEL_FIELDS, values))
        start = struct.unpack_from('<I', packet, 24 + (7 + 17 * index) * 4)[0]
        if not 1 <= row['status'] <= 8 or not start or row['uptime_ms'] < start:
            raise ValueError('Panel timing status or timestamp differs')
        if (row['status'] == 8) != stopped or (stopped and any(values[2:])):
            raise ValueError('Panel timing resumed or carried register values after a fault')
        stopped |= row['status'] in (2, 6)
        if row['status'] != 7:
            if any(values[8:]):
                raise ValueError('Panel timing has counters without a qualified read')
        elif ((row['core_domain'] & 0x80000007) != 0x80000000
              or (row['core_domain_config'] & 0x18000) != 0x10000
              or any((row[key] & 0x80000001) != 1 for key in ('gcc_ahb', 'ahb_clock', 'mdp_clock', 'vsync_clock'))):
            raise ValueError('Panel timing counters have inconsistent clock evidence')
        samples.append(row)
    return samples


def cost_samples(packet, sample_count):
    costs = []
    previous = None
    for index in range(SAMPLES):
        at = PACKET_BYTES - 8 + index * COST_BYTES
        available, *values = struct.unpack_from('<17I', packet, at)
        sampled = index < sample_count
        if available not in (0, 1) or (available and not sampled) or (not available and any(values)):
            raise ValueError('Presentation cost sample availability differs')
        if not sampled:
            continue
        row = None
        if available:
            row = dict(zip(COST_FIELDS, values))
            dispositions = row['copied_frames'] + row['pending'] + row['terminal']
            if (row['schema'] != 278 or row['stage'] not in (1, 2, 3, 4) or row['faults'] & ~7
                    or (not row['faults'] & 2 and dispositions > row['attempts'])
                    or (not row['faults'] & 3 and row['lease_call_us'] > row['lease_wall_us'])):
                raise ValueError('Presentation cost snapshot fields differ')
            if previous is not None and any(row[key] < previous[key] for key in (*COST_TOTALS, 'uptime_ms')):
                raise ValueError('Presentation cost totals regressed within one boot')
            previous = row
        costs.append(row)
    return costs


def parse_packet(packet, boot, schema=313):
    magic, size = LAYOUTS[schema]
    if len(packet) != size or packet[:8] != magic or packet[8:24] != boot:
        raise ValueError('Physical FT3683 packet size, type or boot identity differs')
    crc, wire_schema = struct.unpack_from('<2I', packet, len(packet) - 8)
    if wire_schema != schema or zlib.crc32(packet[:-8]) != crc:
        raise ValueError('Physical FT3683 schema or CRC differs')
    sample_count = struct.unpack_from('<I', packet, 36)[0]
    if sample_count > SAMPLES:
        raise ValueError('Physical FT3683 sample count exceeds the producer bound')
    round_trip = None
    if schema in (363, 367):
        round_trip = touch_smmu_round_trip(packet, touch_gpi_routes(packet), with_gate=schema == 367)
        schema = 362  # The remaining layout and validation are shared.
    touch = []
    previous = None
    offset = 24 + 4 * PRESENT_WORDS
    for index in range(SAMPLES):
        item = struct.unpack_from('<13I', packet, offset + 4 * TOUCH_WORDS * index)
        available, *values = item
        if available > 1 or (index >= sample_count and any(item)) or (not available and any(values)):
            raise ValueError('Physical FT3683 sample availability differs')
        if index >= sample_count:
            continue
        row = None
        if available:
            row = dict(zip(COUNTERS, values))
            if not 0 <= row['accepted'] <= row['decoded'] <= row['read_successes'] <= row['polls']:
                raise ValueError('Physical FT3683 source and report counts differ')
            if (row['edge_downs'] > row['downs'] or row['lifts'] > row['downs'] or row['max_active'] > 10 or
                    row['seen_ids'] >> 20 or row['multi_contact_samples'] > row['accepted']):
                raise ValueError('Physical FT3683 contact counters exceed their source bounds')
            if previous is not None and (
                    any(row[key] < previous[key] for key in COUNTERS if key != 'seen_ids') or
                    row['seen_ids'] & previous['seen_ids'] != previous['seen_ids']):
                raise ValueError('Physical FT3683 counters regressed within one boot')
            previous = row
        touch.append(row)
    # The first 160 words keep the existing manual observer contract. Reuse
    # its host-side validation after checking the complete original packet CRC.
    timeline = MANUAL_MAGIC + packet[8:offset]
    costs = cost_samples(packet, sample_count) if schema in (317, 318, 320, 321, 322, 325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 356) else []
    if round_trip is not None:
        # This schema repurposes the first timing sample. Use the already
        # validated manual sample clock for the remaining paired diagnostics.
        stamp, = struct.unpack_from('<I', packet, 24 + 7 * 4)
        panels = [dict(uptime_ms=stamp, touch_SMMU_round_trip=round_trip)] if sample_count else []
    else:
        panels = panel_samples(packet, sample_count, schema) if schema in (318, 320, 321, 322, 325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362) else []
    if schema in (320, 321, 322, 325, 334, 335, 336, 337, 338):
        observation = te_sample(packet, sample_count, panels[-1]['uptime_ms'] if panels else 0)
        if observation:
            panels[-1]['external_TE'] = observation
    if schema in (321, 322, 325, 334):
        handoff = handoff_sample(packet, panels[0]['uptime_ms'] if panels else None)
        if handoff and panels:
            panels[0]['early_DPU_handoff'] = handoff
    if schema in (360, 361):
        inventory = touch_geni_inventory(packet)
        if panels:
            panels[0]['touch_GENI_inventory'] = inventory
    if schema == 362:
        routes = touch_gpi_routes(packet)
        if panels:
            panels[0]['touch_GPI_routes'] = routes
    if schema in (322, 325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
        resources = display_resources(packet)
        if resources and panels:
            panels[0]['display_CommandDB'] = resources
    if schema in (325, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
        lease = display_lease(packet)
        if lease and panels:
            panels[0]['display_register_resource_lease'] = lease
        if schema in (334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            clock = display_clock_state(packet, lease)
            if clock and panels:
                panels[0]['held_display_clock_state'] = clock
        if schema in (335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
            held = held_dpu_sample(packet, lease, panels[0]['uptime_ms'] if panels else None, schema)
            if held and panels:
                panels[0]['held_DPU'] = held
        if schema in (343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362) and panels:
            if schema not in (347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362):
                cadence = display_cadence(packet, lease, panels[0].get('held_DPU'), schema)
                if cadence:
                    panels[0]['runtime_DSI_cadence'] = cadence
            if schema >= 345:
                scanout = display_scanout_alias(packet, lease)
                if scanout:
                    panels[0]['second_scanout_alias'] = scanout
                if schema in (346, 347, 356):
                    flip = display_scanout_flip(packet, lease, scanout)
                    if flip:
                        panels[0]['second_scanout_flip'] = flip
                    if schema in (347, 356):
                        comparison = display_period_compare(packet, lease, panels[0].get('held_DPU'), flip, 2 if schema == 356 else 4)
                        if comparison:
                            panels[0]['panel_period_comparison'] = comparison
                if schema in (348, 349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
                    live = display_live_scanout(packet, lease, panels[0].get('held_DPU'), scanout, schema)
                    if schema in (349, 350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
                        phases = display_attempt_phases(packet, live, schema)
                        if live is not None:
                            live['attempt_phases'] = phases
                    if schema in (350, 351, 352, 353, 354, 355, 357, 358, 359, 360, 361, 362):
                        gate = display_writer_gate(packet, live, schema)
                        if live is not None:
                            live['writer_gate'] = gate
                    if schema in (354, 355, 357, 358, 359, 360, 361, 362):
                        display_sampled_rgb(packet, live)
                    if live:
                        panels[0]['live_scanout'] = live
        elif schema in (339, 340, 341, 342) and panels:
            held = panels[0].get('held_DPU')
            transfer = (display_transfer(packet, lease, held) if schema == 339 else
                        display_auto_transfer(packet, lease, held, schema))
            if transfer:
                panels[0]['controlled_display_transfer'] = transfer
            if schema in (341, 342):
                frame = display_runtime_frame(packet, lease, held, transfer, schema)
                if frame:
                    panels[0]['runtime_display_frame'] = frame
                if schema == 342:
                    scene = display_runtime_scene(packet, frame, transfer)
                    if scene:
                        panels[0]['runtime_display_scene'] = scene
    return timeline + struct.pack('<2I', zlib.crc32(timeline), 277), (touch, costs, panels)


def split_physical(data, tag, schema=313):
    boot = bytes.fromhex(tag)
    magic, size = LAYOUTS[schema]
    if len(data) > WIRE_LIMIT or len(boot) != 16:
        raise ValueError('Physical FT3683 capture envelope differs')
    rest = bytearray()
    timeline = b''
    samples = None
    at = 0
    while at < len(data):
        tail = data[at:]
        if tail.startswith(magic):
            if samples is not None:
                raise ValueError('Repeated physical FT3683 packet')
            if len(tail) < size:
                return bytes(rest), b'', None, len(tail)
            timeline, samples = parse_packet(tail[:size], boot, schema)
            at += size
        elif magic.startswith(tail):
            return bytes(rest), timeline, samples, len(tail)
        elif tail.startswith(tuple(layout[0] for layout in LAYOUTS.values())):
            raise ValueError('Physical wire does not match package schema')
        elif tail.startswith((b'K80UI', MANUAL_MAGIC)):
            raise ValueError('Different scene packet in physical FT3683 capture')
        elif tail.startswith(MENU_MAGIC):
            if len(tail) < 68:
                rest.extend(tail)
                break
            size = struct.unpack_from('<I', tail, 28)[0]
            if not 0 < size <= 3004:
                raise ValueError('Physical FT3683 screenshot chunk size differs')
            rest.extend(tail[:68 + size])
            at += 68 + size
        else:
            end = data.find(b'\r\n', at)
            if tail.startswith(PANIC_MAGIC) or end < 0:
                rest.extend(tail)
                break
            rest.extend(data[at:end + 2])
            at = end + 2
    return bytes(rest), timeline, samples, 0


def early_scanout_summary(normal):
    # Terminal panic bytes must remain untouched by any progress-field parser.
    progress, panic, terminal = normal.partition(PANIC_MAGIC)
    prefix = b',ds366='
    rows = []
    clean = []
    for line in progress.split(b'\r\n'):
        body, marker, suffix = line.partition(prefix)
        if not marker:
            clean.append(line)
            continue
        if not re.fullmatch(rb'[0-9a-f]{8}(?:/[0-9a-f]{8}){10}', suffix):
            raise ValueError('Early scanout CDC summary syntax differs')
        rows.append(tuple(int(word, 16) for word in suffix.split(b'/')))
        clean.append(body)
    if not rows:
        return normal, None
    status, retain, start, stop, attempts, completed, refused, inside, waits, idle, maximum = rows[0]
    if (any(row != rows[0] for row in rows) or status not in (1, 2, 3, 4, 5, 6, 7, 9, 10, 11)
            or retain != int(status in (7, 9, 10))
            or not 0 <= inside <= completed <= attempts <= LIVE_FRAMES
            or attempts != completed + refused + int(status == 9)
            or not 0 <= idle <= waits <= attempts
            or (not waits and maximum) or (idle and not maximum)
            or (status <= 7 and any((start, stop, attempts)))
            or (status >= 9 and (not 0 < start < stop < 300_000_000
                                 or not 499_998 <= stop - start <= 500_002))):
        raise ValueError('Early scanout CDC summary counters differ')
    return b'\r\n'.join(clean) + panic + terminal, dict(
        result=LIVE_STATES[status], retain=bool(retain), start_us=start, stop_us=stop,
        attempts=attempts, completed=completed, refused=refused, completed_in_window=inside,
        prior_DSI_idle_wait=dict(attempts=waits, reached_idle=idle, max_elapsed_us=maximum),
        copies_received=len(rows))


def inspect_progress(data, tag, program_tag, schema=313, *, early_scanout=False):
    stream, timeline, observations, partial = split_physical(data, tag, schema)
    physical, costs, panels = observations or ([], [], [])
    normal, pixels, crop = split_scroll309(stream, tag)
    summary = None
    if early_scanout:
        normal, summary = early_scanout_summary(normal)
    result = inspect_manual(timeline + normal, tag, program_tag)
    if early_scanout:
        result['early_scanout_summary'] = summary
    frames = result['wire_nonterminal_frames277'] + crop['packet_count']
    if frames > 38:
        raise ValueError('Physical FT3683 frame budget exceeded')
    if partial or crop['partial_packet_bytes']:
        result['transport_frames_valid'] = False
    previous = None
    samples = []
    for index, (present, touch) in enumerate(zip((result.get('manual277') or {}).get('samples', ()), physical)):
        uptime = present['uptime_ms']
        sample = dict(present=present, physical=touch)
        if costs:
            sample['present_cost'] = costs[index]
        if index < len(panels):
            sample['panel_timing'] = panels[index]
        if touch is not None:
            if previous is not None and uptime > previous[0]:
                elapsed = uptime - previous[0]
                sample['poll_rate_hz'] = 1000 * (touch['polls'] - previous[1]['polls']) / elapsed
                sample['read_success_rate_hz'] = 1000 * (touch['read_successes'] - previous[1]['read_successes']) / elapsed
            previous = (uptime, touch)
        samples.append(sample)
    result.update(physical313=samples, crop297=crop, wire_nonterminal_frames313=frames,
                  partial_physical_packet313=partial, physical_FT3683_functionally_qualified=False)
    if schema == 342:
        result['synthetic_input_enabled'] = True
    return result, pixels
