#!/bin/zsh
# Gate 2 viewer acceptance in one command (run from the repo root):
#   web/tools/gate2.sh [manifest_url]        default /assets/gate2/manifest.json
#
# gate1.sh generalised.  Differences that matter:
#   * BOTH placeholder sets are hidden by default (billboards=0 treeboards=0), because a QA capture
#     must never score a placeholder as vegetation.  PFA_QUERY is added on top and WINS: e.g.
#     PFA_QUERY="billboards=1" puts the far-tree quads back, PFA_QUERY="materials=grey" reproduces
#     the Gate 1 grey frames from the same build.
#   * every output is named by PFA_TAG (default gate2), so a grey control pass can be captured next
#     to the PBR one:  PFA_TAG=gate2grey PFA_QUERY="materials=grey" web/tools/gate2.sh
#
# 1. refuses to start while a Blender bake or the export queue owns the GPU (re-checked before EVERY
#    Chrome session: the build and the first session take minutes), and refuses to capture a manifest
#    whose textures are not all on disk (check_manifest_files.py, exit 4);
# 2. regenerates web/src/stations_blender.json from scripts/ and builds web/dist;
# 3. ONE headless-Chrome session, stations 1-6 at 1920x1080 -> renders/web/<tag>_cam0N.png;
# 4. ONE more session at 2560x1440, measure only -> renders/web/<tag>_perf.json;
# 5. the six pair sheets + the cam01 100 % tiles.
# Both Chrome runs go through scripts/chrome_run.sh.  Nothing here writes outside renders/web and web/.
set -e
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
export PFA_MAIN_ROOT="$MAIN"
MANIFEST=${1:-/assets/gate2/manifest.json}
TAG=${PFA_TAG:-gate2}
SHOTSIZE=${PFA_SHOT_SIZE:-1920x1080}
PERFSIZE=${PFA_PERF_SIZE:-2560x1440}
# Defaults first, PFA_QUERY after: screenshot.mjs builds the URL in order, so a later k=v wins.
QUERY=(--query "manifest=$MANIFEST" --query t=0 --query billboards=0 --query treeboards=0)
for kv in ${=PFA_QUERY}; do QUERY+=(--query "$kv"); done   # space-separated k=v list
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"

guard() {
	ST=$(cat "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || echo '{"state":"absent"}')
	if echo "$ST" | grep -q '"running"'; then echo "gate2.sh: bake queue is running, refusing to use the GPU ($1)" >&2; exit 3; fi
	if pgrep -f "MacOS/Blender" >/dev/null; then echo "gate2.sh: a Blender process is alive, refusing to use the GPU ($1)" >&2; exit 3; fi
}
guard start

# Refuse to capture a half-baked set: every texture the manifest names must be on disk.  The path
# is the MAIN checkout's, which is what the page's /assets/* is served from.
python3 web/tools/check_manifest_files.py "$MAIN/export/out/gate2/manifest.json" \
	|| { echo "gate2.sh: the manifest references files that are not on disk, refusing to capture" >&2; exit 4; }

python3 web/tools/dump_stations.py
( cd web && npm run build >/dev/null ) && echo "gate2.sh: web/dist $(du -sh web/dist | cut -f1)"
echo "gate2.sh: tag $TAG, manifest $MANIFEST, query ${QUERY[*]}"

guard "$SHOTSIZE capture"
scripts/chrome_run.sh 1200 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size "$SHOTSIZE" --frames 0 --warmup 12 --timeout 300000 \
	"${QUERY[@]}" \
	--out "renders/web/${TAG}.png" --json "renders/web/${TAG}_cam.json"

guard "$PERFSIZE performance pass"
scripts/chrome_run.sh 1200 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size "$PERFSIZE" --frames 120 --warmup 24 --shots 0 --timeout 300000 \
	"${QUERY[@]}" \
	--out "renders/web/${TAG}_perf1440.png" --json "renders/web/${TAG}_perf_shot.json" \
	--perf "renders/web/${TAG}_perf.json"

python3 web/tools/gate1_sheets.py --viewer-glob "renders/web/${TAG}_cam%02d.png" --out-dir renders/web \
	--prefix "$TAG" --tile-dir "renders/web/tiles/${TAG}"      # never overwrite the Gate 1 tiles
