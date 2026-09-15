#!/bin/zsh
# Gate 0 step 6b: glTF -> toktx (KTX2 UASTC + zstd + mips) -> gltfpack (meshopt, instancing) -> gate0.glb
#
#   export/gltf_pack.sh
#
# Idempotent: it rewrites export/out/gate0/tex_ktx2 and gate0.glb every run. Needs export/gltf_export.py to have
# written gate0.gltf first. Prints one line per step with wall seconds and output bytes.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN="/Users/dk/Projects/3d render blender 3rd attempt building"
export PATH="$MAIN/tools/bin:$PATH"
OUT="$ROOT/export/out/gate0"
GLTF="$OUT/gate0.gltf"
[ -f "$GLTF" ] || { echo "gltf_pack.sh: $GLTF missing - run export/gltf_export.py first" >&2; exit 2; }
command -v toktx    >/dev/null || { echo "gltf_pack.sh: toktx not on PATH" >&2; exit 2; }
command -v gltfpack >/dev/null || { echo "gltf_pack.sh: gltfpack not on PATH" >&2; exit 2; }

TEXIN="$OUT/tex_gltf"
KTX="$OUT/tex_ktx2"
rm -rf "$KTX"; mkdir -p "$KTX"

t0=$(date +%s)
n=0
for f in "$TEXIN"/*.png(N); do
  b=${f:t:r}
  case "$b" in
    *lightmap*) continue ;;            # RGBM8 stays PNG: UASTC blocks would quantise the M channel
    *albedo*)   oetf=srgb ;;
    *)          oetf=linear ;;
  esac
  toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf $oetf \
        "$KTX/$b.ktx2" "$f" >/dev/null
  n=$((n+1))
done
t1=$(date +%s)
echo "[gate0] STEP toktx wall_s=$((t1-t0)) files=$n bytes=$(du -k "$KTX" | tail -1 | cut -f1)KiB"

python3 "$HERE/gltf_ktx2_patch.py" "$GLTF" "$OUT/gate0_ktx2.gltf" "tex_ktx2"

t2=$(date +%s)
if gltfpack -i "$OUT/gate0_ktx2.gltf" -o "$OUT/gate0.glb" -cc -mi -kn 2>"$OUT/gltfpack.log"; then
  SRC=ktx2
else
  echo "[gate0] gltfpack refused the KHR_texture_basisu glTF; falling back to the PNG glTF" >&2
  cat "$OUT/gltfpack.log" >&2
  gltfpack -i "$GLTF" -o "$OUT/gate0.glb" -cc -mi -kn 2>>"$OUT/gltfpack.log"
  SRC=png
fi
t3=$(date +%s)
echo "[gate0] STEP gltfpack wall_s=$((t3-t2)) source=$SRC gate0.glb=$(stat -f%z "$OUT/gate0.glb")B"
grep -E "^(input|output)" "$OUT/gltfpack.log" || true
python3 - "$OUT/gate0.glb" "$OUT/manifest.json" "$SRC" <<'PY'
import json, os, sys
glb, man_p, src = sys.argv[1], sys.argv[2], sys.argv[3]
man = json.load(open(man_p))
man["glb"] = dict(path=os.path.basename(glb), bytes=os.path.getsize(glb), texture_source=src,
                  gltfpack="-cc -mi -kn (EXT_meshopt_compression + EXT_mesh_gpu_instancing; the viewer needs "
                           "MeshoptDecoder and, for texture_source=ktx2, KTX2Loader with the basis transcoder)")
json.dump(man, open(man_p, "w"), indent=1)
print(f"[gate0] manifest glb: {man['glb']}")
PY
