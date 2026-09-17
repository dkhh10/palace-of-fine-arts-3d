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

# ---------------------------------------------------------------- Gate 2: the PBR set (no glb is rebuilt here)
if [ "$1" = "--gate2" ]; then
  OUT="$ROOT/export/out/gate2"
  KTX="$OUT/tex_ktx2"
  ETC="$OUT/tex_ktx2_etc1s"
  TEXIN="$OUT/tex"
  command -v toktx >/dev/null || { echo "gltf_pack.sh: toktx not on PATH" >&2; exit 2; }
  rm -rf "$KTX" "$ETC"; mkdir -p "$KTX" "$ETC"
  t0=$(date +%s); n=0
  for f in "$TEXIN"/gate2_*.png(N); do
    b=${f:t:r}
    # Gate 1 review finding 1: colour is the default, data maps are the exception. Only the albedo is sRGB.
    case "$b" in
      *_albedo) oetf=srgb ;;
      *)        oetf=linear ;;
    esac
    toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf $oetf \
          "$KTX/$b.ktx2" "$f" >/dev/null
    n=$((n+1))
  done
  # the shared concrete/ground DETAIL set (QA-12-1): tiled in object space, not part of any atlas
  for f in "$OUT"/detail/detail_*.png(N); do
    b=${f:t:r}
    case "$b" in
      *_albedo) oetf=srgb ;;
      *)        oetf=linear ;;
    esac
    toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf $oetf \
          "$KTX/$b.ktx2" "$f" >/dev/null
    n=$((n+1))
  done
  t1=$(date +%s)
  echo "[gate2] STEP toktx_uastc wall_s=$((t1-t0)) files=$n bytes=$(du -k "$KTX" 2>/dev/null | tail -1 | cut -f1)KiB"
  # the mobile ETC1S variants: only the timing sample the brief asks for (the walk-near ARCH groups).
  SAMPLE=$(python3 "$HERE/gate2_sample.py" 2>/dev/null)
  t2=$(date +%s); m=0
  for b in ${=SAMPLE}; do
    for f in "$TEXIN"/gate2_${b}_*.png(N); do
      k=${f:t:r}
      case "$k" in
        *_albedo) oetf=srgb ;;
        *)        oetf=linear ;;
      esac
      toktx --t2 --encode etc1s --clevel 2 --qlevel 128 --genmipmap --assign_oetf $oetf \
            "$ETC/$k.ktx2" "$f" >/dev/null && m=$((m+1))
    done
  done
  echo "[gate2] STEP toktx_etc1s wall_s=$(( $(date +%s)-t2 )) files=$m bytes=$(du -k "$ETC" 2>/dev/null | tail -1 | cut -f1)KiB sample=\"$SAMPLE\""
  exit 0
fi

# ---------------------------------------------------------------- Phase 6c item D: the foliage card maps
# export/foliage_tex.py writes out/gate3/foliage/tex/*.png (albedo+alpha with the material's tint applied,
# the translucency factor map, the leaf normal maps) at 1024 - 1 K ONLY since the lead dropped the 2 K
# upsample (decisions.md 2026-09-17, decision 2). Its own KTX2 directory, because gate3_pack.sh rm -rf's
# out/gate3/tex_ktx2 on every bake round and these are not the bake's files. `rm -rf "$KTX"` below is what
# keeps a dropped size from surviving in the KTX2 set; foliage_tex.py does the same for the PNGs.
if [ "$1" = "--foliage" ]; then
  OUT="$ROOT/export/out/gate3/foliage"
  KTX="$OUT/tex_ktx2"
  TEXIN="$OUT/tex"
  [ -d "$TEXIN" ] || { echo "gltf_pack.sh: $TEXIN missing - run export/foliage_tex.py first" >&2; exit 2; }
  command -v toktx >/dev/null || { echo "gltf_pack.sh: toktx not on PATH" >&2; exit 2; }
  rm -rf "$KTX"; mkdir -p "$KTX"
  t0=$(date +%s); n=0
  for f in "$TEXIN"/*.png(N); do
    b=${f:t:r}
    # colour is the default, data is the exception (gate1 review finding 1): only the albedo is sRGB.
    case "$b" in
      *_albedo_*) oetf=srgb ;;
      *)          oetf=linear ;;
    esac
    toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf $oetf \
          "$KTX/$b.ktx2" "$f" >/dev/null
    n=$((n+1))
  done
  echo "[foliage] STEP toktx wall_s=$(( $(date +%s)-t0 )) files=$n bytes=$(du -k "$KTX" | tail -1 | cut -f1)KiB"
  python3 - "$OUT" <<'PYF'
import json, os, sys
out = sys.argv[1]
rep = json.load(open(os.path.join(out, "foliage_tex.json")))
ktx = os.path.join(out, "tex_ktx2")
have = {f[:-5] for f in os.listdir(ktx)}
miss = []
for m, v in rep["materials"].items():
    for k, f in v["files"].items():
        if f.endswith(".png") and f[:-4] not in have:
            miss.append(f)
for k, v in rep["normals"].items():
    for f in v["files"].values():
        if f[:-4] not in have:
            miss.append(f)
assert not miss, f"toktx produced no KTX2 for {miss}"
rep["ktx2_dir"] = "tex_ktx2"
rep["ktx2_bytes"] = sum(os.path.getsize(os.path.join(ktx, f)) for f in os.listdir(ktx))
rep["ktx2_files"] = sorted(os.listdir(ktx))
json.dump(rep, open(os.path.join(out, "foliage_tex.json"), "w"), indent=1)
sizes = sorted({f.rsplit("_", 1)[-1][:-5] for f in rep["ktx2_files"]})
per_size = {px: sum(os.path.getsize(os.path.join(ktx, f))
                    for f in rep["ktx2_files"] if f.endswith(f"_{px}.ktx2")) for px in sizes}
print(f"[foliage] {len(rep['ktx2_files'])} KTX2, {rep['ktx2_bytes']/1e6:.1f} MB "
      + ", ".join(f"{px}: {b/1e6:.1f} MB" for px, b in sorted(per_size.items())))
PYF
  exit 0
fi

# ---------------------------------------------------------------- Phase 6c item A: env_trees.glb
# The far trees' LOD2 meshes (export/trees_far.py) pack on their own so nothing else is touched: the four
# class glbs stay byte-identical and the viewer can load this one lazily. Its textures are the leaf and bark
# PNGs env.gltf already uses, so they are normally already in tex_ktx2; any that are not are encoded here with
# the same rule as --gate1 (colour is the default, data maps are the exception).
if [ "$1" = "--trees" ] || [ "$1" = "--shrubs" ]; then
  OUT="$ROOT/export/out/gate1"
  KTX="$OUT/tex_ktx2"
  if [ "$1" = "--trees" ]; then NAME=env_trees; TAG=trees; REPORT=trees_far.json; MAKER=export/trees_far.py
  else                          NAME=env_shrubs; TAG=shrubs; REPORT=shrub_lod1.json; MAKER=export/shrub_lod1.py
  fi
  G="$OUT/$NAME.gltf"
  [ -f "$G" ] || { echo "gltf_pack.sh: $G missing - run $MAKER first" >&2; exit 2; }
  command -v toktx    >/dev/null || { echo "gltf_pack.sh: toktx not on PATH" >&2; exit 2; }
  command -v gltfpack >/dev/null || { echo "gltf_pack.sh: gltfpack not on PATH" >&2; exit 2; }
  mkdir -p "$KTX"
  t0=$(date +%s); n=0
  for f in $(python3 -c "
import json,sys
d=json.load(open('$G'))
print(' '.join(i['uri'] for i in d.get('images',[]) if i.get('uri')))
"); do
    b=${f:t:r}
    [ -f "$KTX/$b.ktx2" ] && continue
    case "$b" in
      *_normal|*_nrm|*normal*|*_ao|*rough*|*disp*|*translu*|*_mask*) oetf=linear ;;
      *) oetf=srgb ;;
    esac
    toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf $oetf \
          "$KTX/$b.ktx2" "$OUT/$f" >/dev/null
    n=$((n+1))
  done
  echo "[$TAG] STEP toktx wall_s=$(( $(date +%s)-t0 )) new_files=$n (the rest were already in tex_ktx2)"
  python3 "$HERE/gltf_ktx2_patch.py" "$G" "$OUT/${NAME}_ktx2.gltf" "tex_ktx2" >/dev/null
  # -km: the viewer picks the leaf materials out by name (MAT_leaf_*), and gltfpack merges materials whose
  # factors match. -kv/-vc 16 only once the item B vertex AO is in the glTF, so the file stays byte-identical
  # between a re-run without it.
  # -tr (keep referring to the original texture paths): the leaf and bark KTX2 are the ones env.glb already
  # carries, and embedding them again costs 24 MB in a file whose geometry is ~1 MB. They sit in the
  # tex_ktx2 directory beside this glb, which is exactly where the relative URIs resolve from.
  EXTRA=(-km -tr)
  if python3 -c "
import json,sys
d=json.load(open('$OUT/$REPORT'))
sys.exit(0 if d.get('gltf',{}).get('color0_meshes') else 1)
"; then EXTRA+=(-kv -vc 16); fi
  t2=$(date +%s)
  # -vpf (float positions), the same as env.glb and arch.glb, and NOT the briefed -vp 16. Measured: with
  # -vp 16 gltfpack folds each mesh's dequantisation transform into its EXT_mesh_gpu_instancing rows, so a
  # row's TRANSLATION is no longer the node's world translation (env_trees rows came out 40-700 m from their
  # nodes, with instance scales of 0.001) and the per-placement join - the only key that survives the pack -
  # cannot be recovered. env.glb takes -vpf for a different reason (QA-11d-2) and its rows match to 5.9 mm.
  # NO PNG FALLBACK. The manifest advertises `textures.ktx2_dir` and the viewer's loader is configured for
  # KTX2, so a glb silently packed from the PNG glTF ships uncompressed textures under a manifest that says
  # otherwise: several hundred MB of GPU memory, a different colour pipeline, and nothing anywhere saying so.
  # A gltfpack refusal is a build failure - fix the KTX2 glTF (gltf_ktx2_patch.py) and re-run.
  if ! gltfpack -i "$OUT/${NAME}_ktx2.gltf" -o "$OUT/$NAME.glb" -cc -mi -vpf $EXTRA 2>>"$OUT/gltfpack.log"; then
    echo "[$TAG] gltfpack refused $OUT/${NAME}_ktx2.gltf - see $OUT/gltfpack.log. NOT falling back to the" >&2
    echo "[$TAG] PNG glTF: the manifest advertises ktx2_dir, so a PNG-textured $NAME.glb would be a lie." >&2
    exit 1
  fi
  SRC=ktx2
  echo "[$TAG] STEP gltfpack wall_s=$(( $(date +%s)-t2 )) source=$SRC $NAME.glb=$(stat -f%z "$OUT/$NAME.glb")B"
  printf '%s\n' "$NAME -cc -mi -vpf $EXTRA" >> "$OUT/gltfpack_flags.txt"
  python3 "$HERE/verify_glb.py" "$OUT" || exit 1
  exit 0
fi

# ---------------------------------------------------------------- Gate 1: one glb per class
if [ "$1" = "--gate1" ]; then
  OUT="$ROOT/export/out/gate1"
  KTX="$OUT/tex_ktx2"
  TEXIN="$OUT/tex_gltf"
  command -v toktx    >/dev/null || { echo "gltf_pack.sh: toktx not on PATH" >&2; exit 2; }
  command -v gltfpack >/dev/null || { echo "gltf_pack.sh: gltfpack not on PATH" >&2; exit 2; }
  rm -rf "$KTX"; mkdir -p "$KTX"
  : > "$OUT/gltfpack.log"
  : > "$OUT/gltfpack_flags.txt"                      # review finding 10: never append forever
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
    # QA-11d-2: the ENV class spans the whole 1.4 km backdrop in one bounding box, so integer position
    # quantisation is metres per step. Measured on env_ktx2.gltf (gltfpack -cc -mi, error as gltfpack reports
    # it): default 37 % / 34,397,340 B; -vp 16 9 % / 34,845,316 B; -vp 18 and -vp 20 identical to -vp 16
    # (16 is gltfpack's maximum, so more bits buy nothing); -vpf no warning / 35,797,240 B. -vp 16 as briefed
    # leaves 9 %, so env takes -vpf: the warning clears for +952 KB (2.7 % of env.glb, 0.5 % of the payload).
    # Revert to (-vp 16) here if that size matters more than the residual error. Splitting the backdrop into
    # its own glb would shrink the box and is the structural fix, a Gate 2/3 option.
    # arch / orn / ground keep the default and stay byte-identical.
    # -km (keep materials): gltfpack merges materials whose factors are identical, and the ten backdrop greys
    # are identical, so nine of the ten names vanished and nine Gate 2 backdrop texture sets matched no scene
    # material (docs/reviews/phase6_viewer_gate2_review.md). env keeps its names; arch/orn/ground are frozen
    # byte-identical this round, and verify_glb reports - without failing - any names they lose.
    # orn takes -kv too since the lead's 2026-09-16 decision: gltf_gate1.py strips the ORN `cavity` colour
    # attribute from the export copies (it is already inside the Gate 2 albedo bake), so orn.glb carries
    # TEXCOORD_1 for the slot-atlas lightmap and no COLOR_0 for three.js to multiply in.
    # -kv (keep source vertex attributes even if they aren't used): gltfpack strips any attribute no material
    # references, and NOTHING in the glb references UV2 or the vertex irradiance - the lightmap textures are
    # separate KTX2 files the viewer attaches from the manifest. Measured on the Gate 2 glbs: arch.gltf and
    # ground.gltf carry TEXCOORD_1 on all 29 / 4 meshes and arch.glb / ground.glb carried NONE of it, so no
    # lightmap could be applied to anything, re-laid or not (orn.gltf's COLOR_0 and TEXCOORD_1 went the same
    # way). arch / env / ground therefore take -kv from Gate 3 on. orn deliberately does NOT: -kv would also
    # restore the ORN meshes' own COLOR_0, which three.js multiplies into base colour, and that is a look
    # change for the lead to decide (it also blocks the ORN slot-atlas lightmap - reported, not fixed here).
    EXTRA=()
    [ "$cls" = env ] && EXTRA=(-vpf -km)
    [ "$cls" = arch ] && EXTRA=(-vpf -km)   # QA-12-1 re-pack: same flags as env, named materials kept
    # a class gets -kv exactly when its .gltf carries an attribute the manifest owns (TEXCOORD_1 for a
    # lightmap, COLOR_0 for the near-tree irradiance), so a class that has none is packed byte-identically.
    KV=$(python3 - "$OUT" "$cls" <<'PY1'
import json, os, sys
c = json.load(open(os.path.join(sys.argv[1], "gltf_gate1.json")))["classes"].get(sys.argv[2], {})
print("-kv" if (c.get("texcoord1_meshes") or c.get("color0_meshes")) else "")
PY1
)
    [ -n "$KV" ] && EXTRA+=(-kv)
    # -vc 16 (colour quantisation bits, default 8): the near-tree irradiance rides in COLOR_0 as a gamma-2
    # code at a per-mesh range (lead's decision, docs/decisions.md 2026-09-16). At the default 8 bits the code
    # step is 1/255, which is a 0.8 % linear error at mid grey and much worse near black; at 16 bits it is
    # 1/65535. Given only to the class that actually carries COLOR_0, so every other class stays byte-identical.
    VC=$(python3 - "$OUT" "$cls" <<'PY1b'
import json, os, sys
c = json.load(open(os.path.join(sys.argv[1], "gltf_gate1.json")))["classes"].get(sys.argv[2], {})
print("-vc" if c.get("color0_meshes") else "")
PY1b
)
    [ -n "$VC" ] && EXTRA+=(-vc 16)
    if gltfpack -i "$OUT/${cls}_ktx2.gltf" -o "$OUT/$cls.glb" -cc -mi $EXTRA 2>>"$OUT/gltfpack.log"; then
      SRC=ktx2
    else
      echo "[gate1] gltfpack refused the KTX2 $cls.gltf; falling back to the PNG glTF" >&2
      gltfpack -i "$G" -o "$OUT/$cls.glb" -cc -mi $EXTRA 2>>"$OUT/gltfpack.log"
      SRC=png
    fi
    echo "[gate1] STEP gltfpack:$cls wall_s=$(( $(date +%s)-t2 )) source=$SRC $cls.glb=$(stat -f%z "$OUT/$cls.glb")B"
    printf '%s\n' "$cls -cc -mi $EXTRA" >> "$OUT/gltfpack_flags.txt"
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
  python3 "$HERE/verify_glb.py" "$OUT" || exit 1
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
