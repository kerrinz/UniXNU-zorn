#!/usr/bin/env bash
# Validate the two concrete K80 profiles with the upstream format-2 resolver.
set -euo pipefail
device=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
upstream="$device/../UniXNU"
output=${1:?usage: bash scripts/check-package-profiles.sh /path/to/new-output}
revision=630b85a307f19c8d8a4699d5bfc12f6796b874aa
profile=ios-26.6.2-23G90

if [[ $(git -C "$upstream" rev-parse HEAD) != "$revision" ]]; then
    echo "Preflight requires a separate sibling UniXNU checkout at $revision" >&2
    exit 1
fi
profile_dir="$upstream/profiles/os/$profile"
profile_source="$device/profiles/os/$profile/profile.toml"
mkdir -p "$profile_dir" "$output"
if [[ ! -e "$profile_dir/profile.toml" && ! -L "$profile_dir/profile.toml" ]]; then
    (set -o noclobber; cat "$profile_source" > "$profile_dir/profile.toml")
fi
cmp "$profile_source" "$profile_dir/profile.toml"
cmp "$device/scripts/package.sh" "$upstream/templates/package.sh"

export PYTHONDONTWRITEBYTECODE=1
for target in ipados-17.7.11-21H461 "$profile"; do
    "$device/scripts/package.sh" --no-deps --check --os "$target" --out "$output"
    python3 "$upstream/unixnu" status -D "$device" --os "$target" --out "$output" --json > "$output/$target.json"
done

python3 - "$output" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
for profile, product, build, config, pages, patches in (
    ('ipados-17.7.11-21H461', 'iPad7,1', '21H461', 'zorn_union_defconfig', 4096, 157),
    ('ios-26.6.2-23G90', 'iPhone18,1', '23G90', 'zorn_ios26_defconfig', 16384, 0),
):
    status = json.loads((root / f'{profile}.json').read_text())
    board = status['board']
    inputs = (board['board']['os_profile'], board['ipsw']['product'], board['ipsw']['build'],
              status['configuration'], board['arch']['page_size'], len(status['patch_order']))
    if not status['configured'] or inputs != (profile, product, build, config, pages, patches):
        sys.exit(f'{profile}: unexpected resolved profile: {inputs}')
    if profile.startswith('ios-') and (board['arch']['name'] != 'arm64e' or
            any(key in board for key in ('userdata', 'payload', 'adt')) or 'prelink' in board['kernel']):
        sys.exit(f'{profile}: inherited incompatible ABI or board inputs')
    print(f'PASS {profile}: {product}/{build}, {config}, {pages} byte CPU pages, {patches} generic patches')
PY
