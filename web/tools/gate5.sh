#!/bin/zsh
# Gate 5 capture: the six stations against a BASE URL (the staging deployment), plus the payload
# record and the performance pass, plus the mobile tier.  Run from the repo root:
#
#   web/tools/gate5.sh https://pfa-walkthrough.pages.dev
#   web/tools/gate5.sh                       # no url: serve web/dist locally, same outputs
#   PFA_TAG=gate5b web/tools/gate5.sh <url>  # a second round without overwriting the first
#
# It writes EXACTLY these files, because docs/briefs/qa_round_18.md reads them by name:
#   renders/web/<tag>_cam0N.png     stations 1-6, 1920x1080, DESKTOP tier
#   renders/web/<tag>_net.json      bytes before the first frame, time to first frame, per-tier
#                                   arrival and bytes, every request with its own bytes
#   renders/web/<tag>_perf.json     the 1440p performance pass, gate4 settings, DESKTOP tier
#   renders/web/<tag>m_cam0N.png    stations 1-6 with ?tier=mobile at 1170x2532 (the iPhone 16 Pro's
#                                   own pixel size; the viewer caps the drawing buffer itself)
# plus the sidecars beside each (<tag>_cam.json, <tag>m_cam.json, <tag>_perf_shot.json).
#
# Same guards as gate4.sh: it refuses to start while a Blender process or the bake queue owns the
# GPU, re-checked before every Chrome session, and it never sets PFA_DEV_SHARE_GPU.  The manifest
# and the query are the Gate 4 delivery look; PFA_QUERY is appended last and therefore wins.
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
MAIN=${PFA_MAIN_ROOT:-$ROOT}
export PFA_MAIN_ROOT="$MAIN"
BASE=${1:-}
TAG=${PFA_TAG:-gate5}
MANIFEST=${PFA_MANIFEST:-/assets/gate5/manifest.json}
SHOTSIZE=${PFA_SHOT_SIZE:-1920x1080}
PERFSIZE=${PFA_PERF_SIZE:-2560x1440}
MOBILESIZE=${PFA_MOBILE_SIZE:-1170x2532}

# the Gate 4 delivery look, unchanged; ?tiers=all is 6b's default and is stated rather than assumed
QUERY=(--query "manifest=$MANIFEST" --query tiers=all --query t=0 --query billboards=0 --query treeboards=0
       --query lighting=baked --query post=all --query probe=1 --query impostors=1 --query water=1)
for kv in ${=PFA_QUERY}; do QUERY+=(--query "$kv"); done
URLARG=()
[ -n "$BASE" ] && URLARG=(--url "$BASE")

guard() {
	ST=$(cat "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || echo '{"state":"absent"}')
	if echo "$ST" | grep -q '"running"'; then echo "gate5.sh: bake queue is running, refusing to use the GPU ($1)" >&2; exit 3; fi
	if pgrep -f "MacOS/Blender" >/dev/null; then echo "gate5.sh: a Blender process is alive, refusing to use the GPU ($1)" >&2; exit 3; fi
}
guard start

python3 web/tools/dump_stations.py
if [ -z "$BASE" ]; then
	( cd web && npm run build >/dev/null ) && echo "gate5.sh: web/dist $(du -sh web/dist | cut -f1)"
	echo "gate5.sh: no base url — serving web/dist locally"
else
	echo "gate5.sh: base url $BASE"
fi
echo "gate5.sh: tag $TAG, manifest $MANIFEST, query ${QUERY[*]}"

# 1. the six stations, desktop tier, with the payload record on the same session
guard "$SHOTSIZE desktop capture"
scripts/chrome_run.sh 2400 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size "$SHOTSIZE" --frames 0 --warmup 12 --timeout 900000 \
	"${URLARG[@]}" "${QUERY[@]}" --query tier=desktop \
	--out "renders/web/${TAG}.png" --json "renders/web/${TAG}_cam.json" \
	--net "renders/web/${TAG}_net.json"

# 2. the performance pass, desktop tier, measure only (gate4 settings)
guard "$PERFSIZE performance pass"
scripts/chrome_run.sh 2400 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size "$PERFSIZE" --frames 120 --warmup 24 --shots 0 --timeout 900000 \
	"${URLARG[@]}" "${QUERY[@]}" --query tier=desktop \
	--out "renders/web/${TAG}_perf1440.png" --json "renders/web/${TAG}_perf_shot.json" \
	--perf "renders/web/${TAG}_perf.json"

# 3. the six stations on the MOBILE tier, at the iPhone 16 Pro's own pixel size
guard "$MOBILESIZE mobile capture"
scripts/chrome_run.sh 2400 -- node web/tools/screenshot.mjs \
	--stations 1-6 --size "$MOBILESIZE" --frames 0 --warmup 12 --timeout 900000 \
	"${URLARG[@]}" "${QUERY[@]}" --query tier=mobile \
	--out "renders/web/${TAG}m.png" --json "renders/web/${TAG}m_cam.json" \
	--net "renders/web/${TAG}m_net.json"

echo "gate5.sh: wrote renders/web/${TAG}_cam0[1-6].png, ${TAG}_net.json, ${TAG}_perf.json, ${TAG}m_cam0[1-6].png"
