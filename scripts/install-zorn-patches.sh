#!/bin/sh
# Copy patches/zorn into a UniXNU checkout's patches/xnu.
#
# The device repository must not contain patches/xnu. That directory name is
# the base patch module, and a device copy would replace it. These files are
# applied by the kernel build only after they sit next to the other
# patches/xnu/*.patch files.
#
#   scripts/install-zorn-patches.sh /path/to/UniXNU [--core]
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
unixnu=${1:-}
if [ -z "$unixnu" ]; then
  echo "usage: scripts/install-zorn-patches.sh /path/to/UniXNU [--core]" >&2
  exit 1
fi
option=${2:-}
if [ "$#" -gt 2 ] || { [ -n "$option" ] && [ "$option" != --core ]; }; then
  echo "usage: scripts/install-zorn-patches.sh /path/to/UniXNU [--core]" >&2
  exit 1
fi
unixnu=$(CDPATH= cd -- "$unixnu" && pwd)
dest=$unixnu/patches/xnu
if [ ! -d "$dest" ]; then
  echo "not a UniXNU checkout (missing patches/xnu): $unixnu" >&2
  exit 1
fi
if [ "$option" = --core ]; then
  for patch in "$root"/patches/core/*.patch; do
    if git -C "$unixnu" apply --reverse --check "$patch" 2>/dev/null; then
      echo "already applied: $(basename "$patch")"
    elif git -C "$unixnu" apply --check "$patch"; then
      git -C "$unixnu" apply "$patch"
      echo "applied: $(basename "$patch")"
    else
      echo "core patch conflicts; review patches/core/README.md: $patch" >&2
      exit 1
    fi
  done
fi
cp -p "$root"/patches/zorn/*.patch "$dest"/
echo "installed zorn patches into $dest"
