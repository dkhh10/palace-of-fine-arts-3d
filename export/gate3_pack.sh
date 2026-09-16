#!/bin/zsh
# Gate 3 step 4: the PNGs export/bake_lm.py and export/gate3_compose.py wrote -> KTX2, and the probe/sky .hdr in place.
#
#   export/gate3_pack.sh
#
# CPU only (toktx): safe to run while the bake queue holds the GPU. Idempotent - it rewrites out/gate3/tex_ktx2.
#
# Two encodings per lightmap, as export/README.md "manifest v4" specifies:
#   *_rgbm8.png  -> LOSSLESS KTX2 (zstd only, no Basis). RGBM cannot survive block compression: a one-step
#                   error in the M channel scales all three colour channels.
#   *_gamma2.png -> UASTC -> ASTC 4x4 on the Apple GPU, 4x less resident, the encoding the budget ships.
# Impostor atlases get NO mip chain: an octahedral atlas mips across frame boundaries.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
export PATH="$MAIN/tools/bin:$PATH"
OUT="$ROOT/export/out/gate3"
KTX="$OUT/tex_ktx2"
command -v toktx >/dev/null || { echo "gate3_pack.sh: toktx not on PATH" >&2; exit 2; }
rm -rf "$KTX"; mkdir -p "$KTX"

t0=$(date +%s); n=0
for f in "$OUT"/tex/*_rgbm8.png(N); do
  b=${f:t:r}
  toktx --t2 --zcmp 18 --genmipmap --assign_oetf linear "$KTX/$b.ktx2" "$f" >/dev/null
  n=$((n+1))
done
t1=$(date +%s)
echo "[gate3] STEP toktx_rgbm8_lossless wall_s=$((t1-t0)) files=$n"

t0=$(date +%s); m=0
for f in "$OUT"/tex/*_gamma2.png(N); do
  b=${f:t:r}
  toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf linear "$KTX/$b.ktx2" "$f" >/dev/null
  m=$((m+1))
done
t1=$(date +%s)
echo "[gate3] STEP toktx_gamma2_uastc wall_s=$((t1-t0)) files=$m"

t0=$(date +%s); k=0
for f in "$OUT"/impostor/gate3_imp_*.png(N); do
  b=${f:t:r}
  toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --assign_oetf linear "$KTX/$b.ktx2" "$f" >/dev/null
  k=$((k+1))
done
t1=$(date +%s)
echo "[gate3] STEP toktx_impostor_nomips wall_s=$((t1-t0)) files=$k"
echo "[gate3] tex_ktx2 total $(du -k "$KTX" | tail -1 | cut -f1) KiB, $((n+m+k)) files"
