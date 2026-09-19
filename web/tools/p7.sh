#!/bin/zsh
# Phase 7 capture helper.  Every Phase 7 number and picture in web/README.md "Phase 7" comes from
# this script, so a round can be repeated without reconstructing a command line.  Run from the repo
# root, with PFA_MAIN_ROOT pointing at the MAIN checkout (the assets are served from its export/out):
#
#   web/tools/p7.sh desk  <tag> [extra k=v ...]   stations 1,2,5 at 1920x1080, DESKTOP tier
#   web/tools/p7.sh six   <tag> [extra k=v ...]   stations 1-6   at 1920x1080, DESKTOP tier
#   web/tools/p7.sh perf  <tag> [extra k=v ...]   the 2560x1440 measure-only pass (120 frames, warmup 24)
#   web/tools/p7.sh mob   <tag> [extra k=v ...]   stations 1-6 at 1170x2532, ?tier=mobile
#   web/tools/p7.sh orbit <tag> [extra k=v ...]   the close orbit of the rotunda, ?tier=mobile
#   PFA_TIER=desktop web/tools/p7.sh orbit <tag>  ... the same orbit on the desktop tier
#
# THE ORBIT is the user's phase-7 screenshot as a repeatable fixture: __pfaOrbit around the rotunda
# centre at 80 m, height 5 m, headings 253 deg (the hero's own bearing, measured from the station's
# world matrix: sin/cos of (-79.80, -24.40) is 253.0 deg) and 215 deg.  80 m and not 30: 30 m from
# the WORLD ORIGIN is inside the colonnade, where no tree is in shot at all, while 80 m stands the
# camera where the user's screenshot stands, about 30 m out from the building's own edge.
#
# Same GPU guards as gate4.sh / gate5.sh, re-checked before the Chrome session, and it never sets
# PFA_DEV_SHARE_GPU.
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
MAIN=${PFA_MAIN_ROOT:-$ROOT}
export PFA_MAIN_ROOT="$MAIN"
MODE=${1:?usage: p7.sh desk|six|perf|mob|orbit <tag> [k=v ...]}
TAG=${2:?usage: p7.sh desk|six|perf|mob|orbit <tag> [k=v ...]}
shift 2
MANIFEST=${PFA_MANIFEST:-/assets/gate5/manifest.json}
TIER=${PFA_TIER:-}
ORBIT=${PFA_ORBIT:-0,0,0:80:5:253,215}

QUERY=(--query "manifest=$MANIFEST" --query tiers=all --query t=0 --query billboards=0 --query treeboards=0
       --query lighting=baked --query post=all --query probe=1 --query impostors=1 --query water=1)
for kv in "$@"; do QUERY+=(--query "$kv"); done

guard() {
	ST=$(cat "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || echo '{"state":"absent"}')
	if echo "$ST" | grep -q '"running"'; then echo "p7.sh: bake queue is running, refusing the GPU ($1)" >&2; exit 3; fi
	if pgrep -f "MacOS/Blender" >/dev/null; then echo "p7.sh: a Blender process is alive, refusing the GPU ($1)" >&2; exit 3; fi
}
guard "$MODE"

case "$MODE" in
desk|six)
	[ "$MODE" = six ] && ST=1-6 || ST=1,2,5
	scripts/chrome_run.sh 1500 -- node web/tools/screenshot.mjs --stations "$ST" --size 1920x1080 \
		--frames 0 --warmup 12 --timeout 600000 "${QUERY[@]}" --query "tier=${TIER:-desktop}" \
		--out "renders/web/${TAG}.png" --json "renders/web/${TAG}_cam.json" ;;
perf)
	scripts/chrome_run.sh 2400 -- node web/tools/screenshot.mjs --stations 1-6 --size 2560x1440 \
		--frames 120 --warmup 24 --shots 0 --timeout 900000 "${QUERY[@]}" --query "tier=${TIER:-desktop}" \
		--out "renders/web/${TAG}.png" --json "renders/web/${TAG}_shot.json" \
		--perf "renders/web/${TAG}_perf.json" ;;
mob)
	scripts/chrome_run.sh 1500 -- node web/tools/screenshot.mjs --stations 1-6 --size 1170x2532 \
		--frames 0 --warmup 12 --timeout 600000 "${QUERY[@]}" --query "tier=${TIER:-mobile}" \
		--out "renders/web/${TAG}.png" --json "renders/web/${TAG}_cam.json" ;;
orbit)
	scripts/chrome_run.sh 1500 -- node web/tools/screenshot.mjs --station 1 --size 1170x2532 \
		--frames 120 --warmup 24 --timeout 600000 --orbit "$ORBIT" "${QUERY[@]}" \
		--query "tier=${TIER:-mobile}" \
		--out "renders/web/${TAG}.png" --json "renders/web/${TAG}.json" \
		--perf "renders/web/${TAG}_perf.json" ;;
*) echo "p7.sh: unknown mode $MODE" >&2; exit 2 ;;
esac
echo "p7.sh: $MODE -> renders/web/${TAG}*"
