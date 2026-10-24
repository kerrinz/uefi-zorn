#!/bin/sh
# Link the zorn platform into a Mu-Silicium checkout. Does not copy blobs and
# does not touch the phone. Pass the checkout as $1. Links are untracked in
# that checkout and must not be committed there.
#
#   scripts/stage-into-mu.sh /path/to/Mu-Silicium
#
# With no argument, a sibling ../Mu-Silicium is used when it is a checkout.
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
if [ -n "${1:-}" ]; then
  mu=$1
elif [ -f "$root/../Mu-Silicium/build_uefi.py" ]; then
  mu=$root/../Mu-Silicium
elif [ -f /Volumes/macData/projects/Mu-Silicium/build_uefi.py ]; then
  # Checkout used while this port was brought up. A published clone should
  # pass the path, or keep Mu-Silicium next to this repository.
  mu=/Volumes/macData/projects/Mu-Silicium
else
  echo "usage: scripts/stage-into-mu.sh /path/to/Mu-Silicium" >&2
  exit 1
fi
if [ ! -f "$mu/build_uefi.py" ]; then
  echo "not a Mu-Silicium checkout: $mu" >&2
  exit 1
fi
mkdir -p "$mu/Platforms/Xiaomi" "$mu/Resources/Configs"
ln -sfn "$root/Platforms/Xiaomi/zornPkg" "$mu/Platforms/Xiaomi/zornPkg"
ln -sfn "$root/Resources/Configs/zorn.toml" "$mu/Resources/Configs/zorn.toml"
echo "linked zornPkg and zorn.toml into $mu"
