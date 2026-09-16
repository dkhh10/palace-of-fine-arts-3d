#!/bin/zsh
# Gate 4 viewer capture in one command (run from the repo root):
#   web/tools/gate4.sh [manifest_url]        default /assets/gate3/manifest.json
#
# gate2.sh generalised to manifest v4.  Same guards, same one-session-per-pass shape:
#   1. refuses to start while a Blender bake or the export queue owns the GPU (re-checked before EVERY
#      Chrome session), and refuses to capture a manifest whose files are not all on disk (exit 4);
#   2. regenerates web/src/stations_blender.json and builds web/dist;
#   3. ONE headless-Chrome session, stations 1-6 at 1920x1080 -> renders/web/<tag>_cam0N.png;
#   4. ONE more session at 2560x1440, measure only -> renders/web/<tag>_perf.json;
#   5. the six pair sheets + the cam01 100 % tiles.
#
# Defaults: baked lighting, both placeholder sets hidden, the water phase frozen at t=0 so a repeat
# capture is byte-comparable.  PFA_QUERY is appended LAST and therefore wins:
#   PFA_TAG=r13direct PFA_QUERY="lighting=direct" web/tools/gate4.sh    the control pass
#   PFA_TAG=r13post   PFA_QUERY="post=all"       web/tools/gate4.sh    with the post chain on
set -e
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
export PFA_MAIN_ROOT="$MAIN"
MANIFEST=${1:-/assets/gate3/manifest.json}
TAG=${PFA_TAG:-gate4}
SHOTSIZE=${PFA_SHOT_SIZE:-1920x1080}
PERFSIZE=${PFA_PERF_SIZE:-2560x1440}
QUERY=(--query "manifest=$MANIFEST" --query t=0 --query billboards=0 --query treeboards=0 --query lighting=baked)
for kv in ${=PFA_QUERY}; do QUERY+=(--query "$kv"); done   # space-separated k=v list
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"

guard() {
	ST=$(cat "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || echo '{"state":"absent"}')
	if echo "$ST" | grep -q '"running"'; then echo "gate4.sh: bake queue is running, refusing to use the GPU ($1)" >&2; exit 3; fi
	if pgrep -f "MacOS/Blender" >/dev/null; then echo "gate4.sh: a Blender process is alive, refusing to use the GPU ($1)" >&2; exit 3; fi
}
guard start

LOCAL_MANIFEST="$MAIN/export/out/${MANIFEST#/assets/}"
python3 web/tools/check_manifest_files.py "$LOCAL_MANIFEST" \
	|| { echo "gate4.sh: the manifest references files that are not on disk, refusing to capture" >&2; exit 4; }

python3 web/tools/dump_stations.py
( cd web && npm run build >/dev/null ) && echo "gate4.sh: web/dist $(du -sh web/dist | cut -f1)"
echo "gate4.sh: tag $TAG, manifest $MANIFEST, query ${QUERY[*]}"

guard "$SHOTSIZE capture"
scripts/chrome_run.sh 1500 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size "$SHOTSIZE" --frames 0 --warmup 12 --timeout 420000 \
	"${QUERY[@]}" \
	--out "renders/web/${TAG}.png" --json "renders/web/${TAG}_cam.json"

guard "$PERFSIZE performance pass"
scripts/chrome_run.sh 1500 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size "$PERFSIZE" --frames 120 --warmup 24 --shots 0 --timeout 420000 \
	"${QUERY[@]}" \
	--out "renders/web/${TAG}_perf1440.png" --json "renders/web/${TAG}_perf_shot.json" \
	--perf "renders/web/${TAG}_perf.json"

python3 web/tools/gate1_sheets.py --viewer-glob "renders/web/${TAG}_cam%02d.png" --out-dir renders/web \
	--prefix "$TAG" --tile-dir "renders/web/tiles/${TAG}"
