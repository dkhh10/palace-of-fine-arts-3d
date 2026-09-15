#!/bin/zsh
# Gate 0 acceptance in one command (run from the repo root):
#   web/tools/gate0.sh [column_name_substring] [capital_name_substring]
# 1. refuses to start while a Blender bake owns the GPU (status.json or a live Blender process);
# 2. builds web/dist;
# 3. one headless-Chrome run through scripts/chrome_run.sh: station 1 at 1280x720 ->
#    renders/web/gate0_viewer_cam01.png, frame-time stats, and the projected pixel boxes of the
#    column and capital (the ROIs the measurements use, identical in both frames);
# 4. builds renders/web/gate0_pair.png and prints the measurements.
set -e
MAIN="/Users/dk/Projects/3d render blender 3rd attempt building"
COL=${1:-column}
CAP=${2:-capital}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"

ST=$(cat "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || echo '{"state":"absent"}')
if echo "$ST" | grep -q '"running"'; then echo "gate0.sh: bake queue is running, refusing to use the GPU" >&2; exit 3; fi
if pgrep -f "MacOS/Blender" >/dev/null; then echo "gate0.sh: a Blender process is alive, refusing to use the GPU" >&2; exit 3; fi

( cd web && npm run build >/dev/null ) && echo "gate0.sh: web/dist $(du -sh web/dist | cut -f1)"

scripts/chrome_run.sh 300 -- node web/tools/screenshot.mjs \
	--station 1 --size 1280x720 --frames 120 \
	--out renders/web/gate0_viewer_cam01.png --probe "$COL,$CAP"

python3 - "$COL" "$CAP" <<'PY' > /tmp/pfa_gate0_rois.txt
import json, sys
d = json.load(open('renders/web/gate0_viewer_cam01.json'))
probes = {p['name']: p for p in (d.get('probes') or []) if 'bbox' in p}
def roi(needle, pad=14):
    for n, p in probes.items():
        if needle.lower() in n.lower():
            x0, y0, x1, y1 = p['bbox']
            return f"{max(0,int(x0-pad))},{max(0,int(y0-pad))},{min(1280,int(x1+pad))},{min(720,int(y1+pad))}"
    return ""
print(roi(sys.argv[1]))
print(roi(sys.argv[2]))
PY
COL_ROI=$(sed -n 1p /tmp/pfa_gate0_rois.txt)
CAP_ROI=$(sed -n 2p /tmp/pfa_gate0_rois.txt)
echo "gate0.sh: column ROI $COL_ROI   capital ROI $CAP_ROI"

python3 web/tools/pair_sheet.py \
	--cycles renders/web/gate0_cycles_cam01.png \
	--viewer renders/web/gate0_viewer_cam01.png \
	--out renders/web/gate0_pair.png \
	--column-roi "$COL_ROI" ${CAP_ROI:+--capital-roi "$CAP_ROI"}
