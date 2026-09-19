#!/bin/zsh
# Phase 8b step 5: the band PNGs -> KTX2, then publish export/out/gate3/band/ into the MAIN checkout.
#
#   export/band_pack.sh            # toktx + rsync to MAIN
#   export/band_pack.sh --no-sync  # toktx only
#
# CPU only (toktx): safe while the GPU is busy. Idempotent. The flags are the ones export/gate3_pack.sh
# uses for the octahedral atlases, including NO mip chain - a frame atlas mips across frame boundaries,
# and the band's frames are 341 px, so one mip level already bleeds a neighbouring azimuth into the edge.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
export PATH="$MAIN/tools/bin:$PATH"
BAND="$ROOT/export/out/gate3/band"
command -v toktx >/dev/null || { echo "band_pack.sh: toktx not on PATH" >&2; exit 2; }
[ -d "$BAND" ] || { echo "band_pack.sh: $BAND missing" >&2; exit 2; }

t0=$(date +%s); n=0
for f in "$BAND"/band_*_albedo_4096.png(N); do
  b=${f:t:r}
  toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --assign_oetf linear "$BAND/$b.ktx2" "$f" >/dev/null
  n=$((n+1))
done
t1=$(date +%s)
echo "[band] STEP toktx_band_nomips wall_s=$((t1-t0)) files=$n"
echo "[band] png $(du -k "$BAND"/*.png | awk '{s+=$1} END {print s}') KiB, ktx2 $(du -k "$BAND"/*.ktx2 | awk '{s+=$1} END {print s}') KiB"

if [ "$1" != "--no-sync" ]; then
  mkdir -p "$MAIN/export/out/gate3/band"
  rsync -a --delete --exclude '*_view.exr' "$BAND/" "$MAIN/export/out/gate3/band/"
  echo "[band] synced -> $MAIN/export/out/gate3/band/"
fi
