#!/bin/zsh
# 6c round 3 — the A/B capture loop for the crown / shrub work (run from the repo root):
#   web/tools/r3_shots.sh <tag> [stations] [extra query ...]
# One Chrome session, the gate4 DELIVERY query (so a box measured here is the shipped look), no perf
# pass, no tiles.  gate4.sh stays the gate capture; this is the measurement loop between gates.
set -e
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
export PFA_MAIN_ROOT="$MAIN"
TAG=${1:?tag}
ST=${2:-1,2,5}
shift 2 2>/dev/null || shift 1
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
QUERY=(--query "manifest=/assets/gate3/manifest.json" --query t=0 --query billboards=0 --query treeboards=0
       --query lighting=baked --query post=all --query probe=1 --query impostors=1 --query water=1)
for kv in "$@"; do QUERY+=(--query "$kv"); done
( cd web && npm run build >/dev/null )
scripts/chrome_run.sh 1200 -- node web/tools/screenshot.mjs \
	--stations "$ST" --size 1920x1080 --frames 0 --warmup 12 --timeout 420000 \
	"${QUERY[@]}" --out "renders/web/${TAG}.png" --json "renders/web/${TAG}_cam.json"
echo "r3_shots: renders/web/${TAG}_cam0N.png"
