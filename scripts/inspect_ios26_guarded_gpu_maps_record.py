"""Decode the v90 guarded register mapping result from archived pages."""
import re
import struct
import zlib

MAGIC = b'HJPAN026'
PAGE_BYTES = 4096
RECORD_BYTES = 544
COMPLETE = re.compile(
    r'K80 guarded maps: board=1 sub=0 smmu=([01])/([0-9a-f]{8}) '
    r'maps=([01])/([0-9a-f]{8}); PID1 EL0'
)
MOUNT_PREFIX = 'K80 guarded maps mount: '
MOUNT_COMPLETE = re.compile(r'smmu=([01])/([0-9a-f]{8}) maps=([01])/([0-9a-f]{8})')
MOUNT_BOARD = re.compile(r'board=([0-9a-f]{8})/([01])/([0-9a-f]{8})/([0-9]+)')
MOUNT_SUBMISSION = re.compile(r'sub=([0-9a-f]{8})')
MOUNT_LIMITS = {'board worker timeout', 'submission timeout', 'startup result timeout',
                'result allocation failed'}
REFUSED = re.compile(r'K80 guarded maps: board=([01]) sub=([0-9a-f]{8}); PID1 EL0')


def inspect_page(page, expected_run_id, before):
    if len(page) != PAGE_BYTES or len(before) != PAGE_BYTES or len(expected_run_id) != 16:
        raise ValueError('expected two full pages and an exact artifact ID')
    if page == before or before.startswith(MAGIC + expected_run_id):
        raise ValueError('stale artifact record')
    magic, run_id, length, crc, payload = struct.unpack('<8s16sII512s', page[:RECORD_BYTES])
    if magic != MAGIC or run_id != expected_run_id:
        raise ValueError('record identity differs')
    if not 0 < length < len(payload) or payload[length] or any(page[RECORD_BYTES:]):
        raise ValueError('record envelope differs')
    record = bytearray(page[:RECORD_BYTES])
    record[28:32] = bytes(4)
    if zlib.crc32(record) != crc:
        raise ValueError('record CRC differs')
    message = payload[:length].decode('ascii')
    if message.startswith(MOUNT_PREFIX):
        return inspect_mount_result(message[len(MOUNT_PREFIX):], run_id)
    completed = COMPLETE.fullmatch(message)
    if completed:
        smmu_returned, smmu_raw, maps_returned, maps_raw = completed.groups()
        smmu_ok = smmu_returned == '1' and int(smmu_raw, 16) == 0
        maps_ok = maps_returned == '1' and int(maps_raw, 16) == 0
        if maps_ok and not smmu_ok:
            raise ValueError('successful mapping without successful SMMU resource preparation')
        return dict(artifact_id=run_id.hex(), pid1_el0=True, board_ready=True,
                    submission_raw=0, smmu_returned=smmu_returned == '1',
                    smmu_raw=int(smmu_raw, 16), maps_returned=maps_returned == '1',
                    maps_raw=int(maps_raw, 16), guarded_register_mapping_complete=maps_ok)
    refused = REFUSED.fullmatch(message)
    if refused and int(refused[2], 16):
        return dict(artifact_id=run_id.hex(), pid1_el0=True, board_ready=refused[1] == '1',
                    submission_raw=int(refused[2], 16), guarded_register_mapping_complete=False)
    raise ValueError('unexpected guarded mapping result')

def inspect_mount_result(message, run_id):
    result = dict(artifact_id=run_id.hex(), root_mount=True, pid1_el0=False,
                  guarded_register_mapping_complete=False)
    completed = MOUNT_COMPLETE.fullmatch(message)
    if completed:
        smmu_returned, smmu_raw, maps_returned, maps_raw = completed.groups()
        smmu_ok = smmu_returned == '1' and int(smmu_raw, 16) == 0
        maps_ok = maps_returned == '1' and int(maps_raw, 16) == 0
        if maps_ok and not smmu_ok:
            raise ValueError('successful mapping without successful SMMU resource preparation')
        return dict(result, smmu_returned=smmu_returned == '1', smmu_raw=int(smmu_raw, 16),
                    maps_returned=maps_returned == '1', maps_raw=int(maps_raw, 16),
                    guarded_register_mapping_complete=maps_ok)
    board = MOUNT_BOARD.fullmatch(message)
    if board:
        return dict(result, board_setup_raw=int(board[1], 16),
                    board_preparation_returned=board[2] == '1',
                    board_preparation_raw=int(board[3], 16), board_phase=int(board[4]))
    submission = MOUNT_SUBMISSION.fullmatch(message)
    if submission and int(submission[1], 16):
        return dict(result, submission_raw=int(submission[1], 16))
    if message in MOUNT_LIMITS:
        return dict(result, diagnostic=message)
    raise ValueError('unexpected guarded mapping root-mount result')
