#!/usr/bin/env python3
"""Verify the exact ADT-only development identity candidate and refusal cases."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


payload = module("zorn_payload", ROOT / "uefi-zorn/scripts/make-zorn-payload.py")
# Only the pure ADT parser/serializer is imported; no SMP preparation is run.
adt = module("zorn_adt_parser", Path(__file__).with_name("prepare-zorn-smp.py"))
source = ROOT / "out/zorn/builds/0959f393/kernel.macho.adt"
raw = source.read_bytes()
assert payload.trustcache_adt(raw) == raw
address = payload.development_wifi_identity()
assert len(address) == 6 and address[0] & 3 == 2
result = payload.trustcache_adt(raw, wifi_identity=address)
tree = adt.parse_adt(result)
chosen = adt.child(tree, b"chosen")
assert dict(chosen[0])[b"mac-address-wifi0"] == address
chosen[0] = [(key, value) for key, value in chosen[0] if key != b"mac-address-wifi0"]
assert adt.emit(tree) == raw
assert payload.trustcache_adt(result, wifi_identity=address) == result
rejected = 0
for invalid in (b"", address[:5], address + b"\0", bytes(6), b"\xff" * 6,
                bytes([address[0] | 1]) + address[1:]):
    try:
        payload.trustcache_adt(raw, wifi_identity=invalid)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("invalid development address accepted")
try:
    payload.trustcache_adt(result, wifi_identity=address[:5] + bytes([address[5] ^ 1]))
except ValueError:
    rejected += 1
else:
    raise AssertionError("existing identity silently replaced")
out = ROOT / "out/zorn/wifi-identity"
out.mkdir(parents=True, exist_ok=True)
(out / "candidate.adt").write_bytes(result)
proof = {"source_adt_sha256": hashlib.sha256(raw).hexdigest(),
         "candidate_adt_sha256": hashlib.sha256(result).hexdigest(),
         "only_changed_property": "/chosen/mac-address-wifi0", "all_other_adt_bytes_preserved": True,
         "development_mac": ":".join(f"{value:02x}" for value in address),
         "derivation": "SHA256 of explicit UniXNU:zorn:development-wifi:v1 namespace and K80 USB serial",
         "factory_mac_claimed": False, "wifi_transport_implemented": False,
         "default_without_flag_unchanged": True, "invalid_or_conflicting_addresses_rejected": rejected,
         "hardware_verified": False}
(out / "checks.json").write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps(proof, indent=2))
