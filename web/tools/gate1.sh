#!/bin/zsh
# Gate 1 viewer acceptance in one command (run from the repo root):
#   web/tools/gate1.sh [manifest_url]        default /assets/gate1/manifest.json
# 1. refuses to start while a Blender bake or the export queue owns the GPU;
# 2. regenerates web/src/stations_blender.json from scripts/ and builds web/dist;
# 3. ONE headless-Chrome session, stations 1-6 at 1920x1080 -> renders/web/gate1_cam0N.png;
# 4. ONE more session at 2560x1440, measure only -> renders/web/gate1_perf.json;
# 5. the six pair sheets + the cam01 100 % tiles.
# Both Chrome runs go through scripts/chrome_run.sh.  Nothing here writes outside renders/web and web/.
set -e
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
export PFA_MAIN_ROOT="$MAIN"
MANIFEST=${1:-/assets/gate1/manifest.json}
# PFA_QUERY="k=v" adds one extra query parameter to both captures (QA round 11: PFA_QUERY=billboards=0 hides the far-tree placeholder quads).
EXTRAQ=(); for kv in ${=PFA_QUERY}; do EXTRAQ+=(--query "$kv"); done   # space-separated k=v list
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"

# The GPU guard is re-run immediately before EVERY Chrome session: the build and the first session
# take minutes, and the bake queue can claim the GPU in between.
guard() {
	ST=$(cat "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || echo '{"state":"absent"}')
	if echo "$ST" | grep -q '"running"'; then echo "gate1.sh: bake queue is running, refusing to use the GPU ($1)" >&2; exit 3; fi
	if pgrep -f "MacOS/Blender" >/dev/null; then echo "gate1.sh: a Blender process is alive, refusing to use the GPU ($1)" >&2; exit 3; fi
}
guard start

python3 web/tools/dump_stations.py
( cd web && npm run build >/dev/null ) && echo "gate1.sh: web/dist $(du -sh web/dist | cut -f1)"

guard "1920x1080 capture"
scripts/chrome_run.sh 900 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size 1920x1080 --frames 0 --warmup 12 \
	--query "manifest=$MANIFEST" --query t=0 "${EXTRAQ[@]}" \
	--out renders/web/gate1.png --json renders/web/gate1_cam.json

guard "1440p performance pass"
scripts/chrome_run.sh 900 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size 2560x1440 --frames 120 --warmup 24 --shots 0 \
	--query "manifest=$MANIFEST" --query t=0 "${EXTRAQ[@]}" \
	--out renders/web/gate1_perf1440.png --json renders/web/gate1_perf_shot.json \
	--perf renders/web/gate1_perf.json

python3 web/tools/gate1_sheets.py --viewer-glob 'renders/web/gate1_cam%02d.png' --out-dir renders/web
