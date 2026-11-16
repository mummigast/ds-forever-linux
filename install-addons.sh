#!/usr/bin/env bash
# Copy DS Forever's add-ons (the APK's own set) into the PC game's AddOns folder.
# Same job as DS Forever Desktop's add-on install. Re-run after pulling upstream updates.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)/companion/app/src/main/assets/companion/addons"
WOW="${DSF_WOW_DIR:-$HOME/.local/share/Steam/steamapps/compatdata/3809046808/pfx/drive_c/Program Files (x86)/World of Warcraft/_forever_}"
DST="$WOW/Interface/AddOns"
[ -d "$DST" ] || { echo "No AddOns folder at: $DST (set DSF_WOW_DIR)"; exit 1; }
for d in "$SRC"/WowCompanion*/; do
  n=$(basename "$d")
  rm -rf "$DST/$n"
  cp -r "$d" "$DST/$n"
  echo "installed $n"
done
