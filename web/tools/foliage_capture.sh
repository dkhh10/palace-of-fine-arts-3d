#!/bin/zsh
# The 6c foliage capture, in one command (run from the repo root):
#
#   PFA_TAG=round16b web/tools/foliage_capture.sh
#
# It is gate4.sh (six stations at 1920x1080, the 1440p performance pass, the pair sheets and the
# cam01 tiles) plus the three things the 6c brief asks for on top:
#   * a BARE-URL capture at 1280x720 with NO query string at all - the lesson of 5e1fffa, that the
#     delivery look has to be what a visitor gets without a single flag;
#   * the station-2 WALK-IN: the camera 3 m from the far tree that fills the middle of cam02
#     (ENV_tree_redwood_s43_LOD1, placement 90, Blender -39.89 8.57 -1.04, 17.0 m tall, 43 m from the
#     station - it is the tree the user's close-up is about), shot from the station's own side and
#     from the sunlit side, at walker eye height;
#   * the foliage box tables as a COMMITTED json sidecar (round-1 review carry 7), so every number in
#     web/README.md and in the QA report can be re-derived without the full-res PNGs.
#
# Every Chrome session goes through scripts/chrome_run.sh and gate4.sh's own guard refuses to start
# while the bake queue or any Blender process owns the GPU.
set -e
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
export PFA_MAIN_ROOT="$MAIN"
TAG=${PFA_TAG:-round16b}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
REF_CAM02="$MAIN/renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png"

# --- 1. the gate set (six stations, perf, sheets, tiles) --------------------------------------
PFA_TAG="$TAG" web/tools/gate4.sh

# --- 2. the post-off control -------------------------------------------------------------------
PFA_TAG="${TAG}nopost" PFA_QUERY="post=none" web/tools/gate4.sh

# --- 3. the bare URL: no query string whatsoever ------------------------------------------------
scripts/chrome_run.sh 900 -- node web/tools/screenshot.mjs \
	--size 1280x720 --frames 0 --warmup 12 --timeout 420000 \
	--out "renders/web/${TAG}_bareurl.png" --json "renders/web/${TAG}_bareurl.json"

# --- 4. the station-2 walk-in, 3 m from the tree that fills cam02 -------------------------------
# --orbit target is THREE space: Blender (x, y, z) -> three (x, z, -y).  The target is the crown
# centre (base z -1.04 + 17.0/2) and `height` is relative to it, so the camera sits at y = 0.66, a
# walker's eye 1.7 m above that tree's own ground.  Headings: 248 deg is the station-2 side, 68 deg
# the sunlit side.
scripts/chrome_run.sh 900 -- node web/tools/screenshot.mjs \
	--size 1920x1080 --frames 0 --warmup 12 --timeout 420000 \
	--query manifest=/assets/gate3/manifest.json --query t=0 --query billboards=0 --query treeboards=0 \
	--orbit "-39.89,7.46,-8.57:3:-6.8:248,68" \
	--out "renders/web/${TAG}_walkin.png" --json "renders/web/${TAG}_walkin.json"

# --- 4b. the walk clamp, re-run on the 6c scene (QA 16 section 6.4) ----------------------------
# 6c added 1.0 M placed triangles a ground clamp may now hit, and round16_walk.json was taken before
# env_trees.glb and env_shrubs.glb existed and over the short 6 s window round 15 flagged.  24 probes,
# six stations x four headings x 30 s at 3.2 m/s: the acceptance is 0 probes below WATER_Z + 0.1.
scripts/chrome_run.sh 1500 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size 1280x720 --frames 0 --shots 0 --warmup 8 --timeout 420000 \
	--query manifest=/assets/gate3/manifest.json --query t=0 --query billboards=0 --query treeboards=0 \
	--walkprobe 0,90,180,270:30 \
	--out "renders/web/${TAG}_walk.png" --json "renders/web/${TAG}_walk.json"

# --- 4c. the treeMeshDist A/B (PFA_M60=1 only; ratified at 12 m in round 2) --------------------
# The far tree that fills cam02 stands at 43 m, just outside the 40 m default, so the frame that
# started this pass is decided by this one number.  Station 2 at delivery resolution and the six-
# station 1440p performance pass are both taken at 60 m so the choice is made on a measured frame
# time and a measured tile, not on an opinion.
if [[ -n "${PFA_M60:-}" ]]; then
scripts/chrome_run.sh 900 -- node web/tools/screenshot.mjs \
	--station 2 --size 1920x1080 --frames 0 --warmup 12 --timeout 420000 \
	--query manifest=/assets/gate3/manifest.json --query t=0 --query billboards=0 --query treeboards=0 \
	--query treemesh=60 \
	--out "renders/web/${TAG}m60_cam02.png" --json "renders/web/${TAG}m60_cam.json"
scripts/chrome_run.sh 1200 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size 2560x1440 --frames 120 --warmup 24 --shots 0 --timeout 420000 \
	--query manifest=/assets/gate3/manifest.json --query t=0 --query billboards=0 --query treeboards=0 \
	--query treemesh=60 \
	--out "renders/web/${TAG}m60_perf1440.png" --json "renders/web/${TAG}m60_perf_shot.json" \
	--perf "renders/web/${TAG}m60_perf.json"
fi

# --- 5. the box tables, committed -------------------------------------------------------------
if [[ -f "$REF_CAM02" && -f "renders/web/${TAG}_cam02.png" ]]; then
	python3 web/tools/foliage_boxes.py --ref "$REF_CAM02" \
		renders/web/round15_cam02.png:round15 renders/web/round16b_cam02.png:round16b \
		"renders/web/${TAG}_cam02.png:${TAG}" \
		--box "60 520 700 980:near trees (the round-15 box)" \
		--box "700 660 1240 950:the far tree that fills cam02" \
		--json "renders/web/${TAG}_foliage_boxes.json"
fi
if [[ -f "renders/web/${TAG}_cam01.png" ]]; then
	python3 web/tools/foliage_boxes.py \
		--ref "$MAIN/renders/final/hero_cam01_3840x2160_128spp.png" \
		renders/web/round16b_cam01.png:round16b "renders/web/${TAG}_cam01.png:${TAG}" \
		--box "0 700 700 1080:cam01 left shore foliage" \
		--json "renders/web/${TAG}_hero_boxes.json" || true
fi

# --- 6. the 100 % tiles and the 960 px copies --------------------------------------------------
python3 web/tools/foliage_tile.py --tag "$TAG" --prev round16b
python3 web/tools/r3_crown_tile.py --tag "$TAG" --boxes crown --prev round16b
python3 web/tools/r3_crown_tile.py --tag "$TAG" --boxes shrub --prev round16b
for f in renders/web/${TAG}_cam0*.png renders/web/${TAG}_bareurl.png renders/web/${TAG}_walkin*.png; do
	[[ -f "$f" ]] || continue
	sips -Z 960 "$f" --out "renders/web/960/$(basename ${f%.png}).jpg" >/dev/null
done
echo "foliage_capture.sh: $TAG done"
