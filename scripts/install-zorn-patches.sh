#!/bin/sh
# Copy patches/zorn into a UniXNU checkout's patches/xnu.
#
# The device repository must not contain patches/xnu. That directory name is
# the base patch module, and a device copy would replace it. These files are
# applied by the kernel build only after they sit next to the other
# patches/xnu/*.patch files.
#
#   scripts/install-zorn-patches.sh /path/to/UniXNU
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
unixnu=${1:-}
if [ -z "$unixnu" ]; then
  echo "usage: scripts/install-zorn-patches.sh /path/to/UniXNU" >&2
  exit 1
fi
dest=$unixnu/patches/xnu
if [ ! -d "$dest" ]; then
  echo "not a UniXNU checkout (missing patches/xnu): $unixnu" >&2
  exit 1
fi
cp -p "$root"/patches/zorn/*.patch "$dest"/
echo "installed zorn patches into $dest"
