#!/bin/zsh
# Gate 0 step 6b: glTF -> toktx (KTX2 UASTC + zstd + mips) -> gltfpack (meshopt, instancing) -> gate0.glb
#   export/gltf_pack.sh --gate1   ->  Gate 1: tex_ktx2 + arch/orn/env/ground .glb (see the --gate1 block below)
#
#   export/gltf_pack.sh
#
# Idempotent: it rewrites export/out/gate0/tex_ktx2 and gate0.glb every run. Needs export/gltf_export.py to have
# written gate0.gltf first. Prints one line per step with wall seconds and output bytes.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
export PATH="$MAIN/tools/bin:$PATH"

# ---------------------------------------------------------------- Gate 1: one glb per class
if [ "$1" = "--gate1" ]; then
  OUT="$ROOT/export/out/gate1"
  KTX="$OUT/tex_ktx2"
  TEXIN="$OUT/tex_gltf"
  command -v toktx    >/dev/null || { echo "gltf_pack.sh: toktx not on PATH" >&2; exit 2; }
  command -v gltfpack >/dev/null || { echo "gltf_pack.sh: gltfpack not on PATH" >&2; exit 2; }
  rm -rf "$KTX"; mkdir -p "$KTX"
  : > "$OUT/gltfpack.log"                      # review finding 10: never append forever
  t0=$(date +%s); n=0
  for f in "$TEXIN"/*.(png|jpg|jpeg)(N); do
    b=${f:t:r}
    # review finding 1: COLOUR is the default and DATA is the exception, not the other way round. Tagging an
    # sRGB colour texture `linear` makes the viewer skip the decode and it comes back ~1.47x too bright
    # (0.5 linear grey is 0.735 in the file), which poisons every parity number.
    case "$b" in
      *lightmap*) continue ;;                 # RGBM8 stays PNG (UASTC would quantise the M channel)
      *_normal|*_nrm|*normal*|*_ao|*rough*|*disp*|*translu*|*_mask*) oetf=linear ;;
      *) oetf=srgb ;;
    esac
    toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf $oetf \
          "$KTX/$b.ktx2" "$f" >/dev/null
    n=$((n+1))
  done
  t1=$(date +%s)
  echo "[gate1] STEP toktx wall_s=$((t1-t0)) files=$n bytes=$(du -k "$KTX" 2>/dev/null | tail -1 | cut -f1)KiB"
  for cls in arch orn env ground; do
    G="$OUT/$cls.gltf"
    [ -f "$G" ] || { echo "[gate1] $cls.gltf missing - skipped"; continue; }
    python3 "$HERE/gltf_ktx2_patch.py" "$G" "$OUT/${cls}_ktx2.gltf" "tex_ktx2" >/dev/null
    t2=$(date +%s)
    # gltfpack 1.2 refuses -mi together with -kn; the lead's call (docs/decisions.md 2026-09-15) is
    # "-cc -mi": EXT_mesh_gpu_instancing, node names dropped, identity carried by the manifest.
    if gltfpack -i "$OUT/${cls}_ktx2.gltf" -o "$OUT/$cls.glb" -cc -mi 2>>"$OUT/gltfpack.log"; then
      SRC=ktx2
    else
      echo "[gate1] gltfpack refused the KTX2 $cls.gltf; falling back to the PNG glTF" >&2
      gltfpack -i "$G" -o "$OUT/$cls.glb" -cc -mi 2>>"$OUT/gltfpack.log"
      SRC=png
    fi
    echo "[gate1] STEP gltfpack:$cls wall_s=$(( $(date +%s)-t2 )) source=$SRC $cls.glb=$(stat -f%z "$OUT/$cls.glb")B"
  done
  python3 - "$OUT" <<'PY2'
import json, os, sys
out = sys.argv[1]
man_p = os.path.join(out, "manifest.json")
man = json.load(open(man_p))
gl = json.load(open(os.path.join(out, "gltf_gate1.json")))
glbs = {}
for cls in ("arch", "orn", "env", "ground"):
    p = os.path.join(out, cls + ".glb")
    if os.path.exists(p):
        glbs[cls] = dict(path=cls + ".glb", bytes=os.path.getsize(p),
                         placed_tris=gl["classes"].get(cls, {}).get("placed_tris"),
                         objects=gl["classes"].get(cls, {}).get("objects"),
                         meshes=gl["classes"].get(cls, {}).get("meshes"))
ktx = os.path.join(out, "tex_ktx2")
tex = sorted(os.listdir(ktx)) if os.path.isdir(ktx) else []
man["glb"] = dict(per_class=glbs, total_bytes=sum(v["bytes"] for v in glbs.values()),
                  gltfpack="-cc -mi (EXT_meshopt_compression + KHR_mesh_quantization + "
                           "EXT_mesh_gpu_instancing; node names dropped, the manifest's `assets` are the "
                           "identity). The viewer needs MeshoptDecoder and KTX2Loader.")
prev_tex = man.get("textures") if isinstance(man.get("textures"), dict) else {}
man["textures"] = dict(schema=prev_tex.get("schema"), ktx2_dir="tex_ktx2", files=tex,
                       bytes=sum(os.path.getsize(os.path.join(ktx, f)) for f in tex),
                       encoding="toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap, "
                                "linear OETF for the normal and AO data maps",
                       uv="UV1 (TEXCOORD_0)")
json.dump(man, open(man_p, "w"), indent=1)
print("[gate1] manifest glb:", json.dumps(man["glb"]["per_class"]))
PY2
  exit 0
fi

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

# gltfpack 1.2 warns: "-kn disables mesh merge (-mm) and mesh instancing (-mi)". The brief asks for -cc -mi -kn,
# which cannot all hold at once, so both variants are produced and measured: gate0.glb keeps the node names (the
# manifest's `assets` are keyed by them) and gate0_instanced.glb trades them for EXT_mesh_gpu_instancing.
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
IN=$OUT/gate0_ktx2.gltf; [ "$SRC" = png ] && IN=$GLTF
gltfpack -i "$IN" -o "$OUT/gate0_instanced.glb" -cc -mi 2>>"$OUT/gltfpack.log" && \
  echo "[gate0] STEP gltfpack_instanced wall_s=$(( $(date +%s)-t3 )) gate0_instanced.glb=$(stat -f%z "$OUT/gate0_instanced.glb")B"
grep -E "^(input|output)" "$OUT/gltfpack.log" || true
python3 - "$OUT/gate0.glb" "$OUT/manifest.json" "$SRC" <<'PY'
import json, os, sys
glb, man_p, src = sys.argv[1], sys.argv[2], sys.argv[3]
man = json.load(open(man_p))
alt = os.path.join(os.path.dirname(glb), "gate0_instanced.glb")
man["glb"] = dict(path=os.path.basename(glb), bytes=os.path.getsize(glb), texture_source=src,
                  instanced_variant=(dict(path="gate0_instanced.glb", bytes=os.path.getsize(alt),
                                          note="gltfpack -cc -mi (EXT_mesh_gpu_instancing) but WITHOUT -kn, so "
                                               "node names are gone; gltfpack 1.2 refuses -mi together with -kn")
                                     if os.path.exists(alt) else None),
                  gltfpack="-cc -mi -kn; gltfpack 1.2 honours -kn and therefore skips -mi, so this file has "
                           "EXT_meshopt_compression + KHR_mesh_quantization and named nodes, and the 16 column "
                           "placements are 16 nodes sharing one mesh (not EXT_mesh_gpu_instancing). The viewer "
                           "needs MeshoptDecoder and, for texture_source=ktx2, KTX2Loader with the basis "
                           "transcoder.")
json.dump(man, open(man_p, "w"), indent=1)
print(f"[gate0] manifest glb: {man['glb']}")
PY
