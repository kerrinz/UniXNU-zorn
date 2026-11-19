#!/usr/bin/env bash
# Prepare an isolated sibling UniXNU checkout for the exact K80 OS profile.
set -euo pipefail
device=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
upstream=$(cd "$device/../UniXNU" && pwd)
revision=630b85a307f19c8d8a4699d5bfc12f6796b874aa
profile=ios-26.6.2-23G90
patch="$device/patches/unixnu-release/board-release-backend.patch"

[[ $(git -C "$upstream" rev-parse HEAD) == "$revision" ]] || {
    echo "Use an isolated sibling UniXNU checkout at $revision" >&2
    exit 1
}
cmp "$device/scripts/package.sh" "$upstream/templates/package.sh"

profile_file="$upstream/profiles/os/$profile/profile.toml"
source_profile="$device/profiles/os/$profile/profile.toml"
mkdir -p "$(dirname "$profile_file")"
if [[ -e "$profile_file" || -L "$profile_file" ]]; then
    cmp "$source_profile" "$profile_file"
else
    (set -o noclobber; cat "$source_profile" > "$profile_file")
fi

if git -C "$upstream" apply --check "$patch" 2>/dev/null; then
    git -C "$upstream" apply "$patch"
else
    git -C "$upstream" apply --reverse --check "$patch"
fi
