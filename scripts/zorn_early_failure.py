"""Offline decoder for the owner-approved terminal-before-payload record.

CRC/expected identity checks are format and freshness checks, not permission,
authentication, native execution or hardware qualification. Fragment contents
remain opaque; their original known/attempted masks must not be invented here.
"""
import struct
import zlib

MAGIC = b'ZORNGQF1'
PARTS = (
    ('query', 128, 272), ('publication', 400, 24),
    ('discovery', 424, 104), ('gpt_reader', 528, 160),
    ('outer_lifetime', 688, 88), ('reader_lifetime', 776, 88),
    ('first_failed_lookup', 864, 48), ('gcd', 912, 1384),
    ('pas_config', 2296, 184),
)


def decode(block, expected=None):
    if len(block) != 4096 or block[:8] != MAGIC:
        raise ValueError('invalid early terminal record size/magic')
    version, size, checksum, flags = struct.unpack_from('<4I', block, 8)
    stage, origin, status, known, mask = struct.unpack_from('<IIQII', block, 104)
    if (version != 1 or size != 4096 or flags != 1 or not 1 <= stage <= 8 or
            known not in (0, 1) or mask & ~511 or any(block[2480:])):
        raise ValueError('unsupported early terminal record shape')
    nonce, kernel, inputs = block[24:40], block[40:72], block[72:104]
    if not all(any(v) for v in (nonce, kernel, inputs)):
        raise ValueError('unbound early terminal record identity')
    if ((not known and (origin or status)) or
            (known and (not status or origin not in (1, 2)))):
        raise ValueError('invalid failure status availability/origin')
    fragments = {}
    for i, (name, offset, count) in enumerate(PARTS):
        raw = block[offset:offset + count]
        present = bool(mask & (1 << i))
        if not present and any(raw):
            raise ValueError('absent fragment contains bytes: ' + name)
        fragments[name] = {'present': present, 'bytes': count,
                           'raw_hex': raw.hex() if present else None}
    if zlib.crc32(block[:16] + bytes(4) + block[20:]) != checksum:
        raise ValueError('early terminal record CRC mismatch')
    identity = dict(nonce=nonce.hex(), kernel_sha256=kernel.hex(), input_sha256=inputs.hex())
    freshness = 'unverified'
    if expected is not None:
        for name, actual in identity.items():
            value = expected.get(name)
            if (not isinstance(value, str) or len(value) != len(actual) or
                    any(c not in '0123456789abcdefABCDEF' for c in value) or
                    value.lower() != actual):
                raise ValueError('early record expected identity mismatch: ' + name)
        freshness = 'matched-expected'
    return dict(format='ZORNGQF1', version=1, terminal_before_payload=True,
                identity=identity, freshness=freshness, failure_stage=stage,
                status_known=bool(known), status_origin=('unavailable', 'adapter', 'native-efi')[origin],
                raw_failure_status=f'0x{status:016x}' if known else None,
                payload_present_mask=mask, fragments=fragments,
                scope='opaque diagnostic bytes; not native/GPU/write authorization')
