#!/bin/zsh
# Phase 6c: claim / release the GPU status the OTHER agents read, for a one-off Blender run that is not a
# bake_queue job (the 6c impostor diagnosis). bake_queue.sh stays the path for every queued bake.
#
#   export/gpu_lock.sh claim  "<note>"     # status.json -> state running, owner $PFA_QUEUE_OWNER
#   export/gpu_lock.sh release "<note>"    # status.json -> state idle
#
# Why this exists: CLAUDE.md makes export/out/bake_queue/status.json the ONLY signal another agent (the viewer
# engineer's headless Chrome, which also wants the GPU) may read for GPU liveness - never CPU, never log
# silence. A Blender run outside the queue therefore has to keep that file honest, in the worktree AND in the
# MAIN checkout where the other agents read it. Mutual exclusion itself is already enforced one level down:
# every run goes through scripts/blender_run.sh, which registers the pid with the watchdog, and
# bake_queue.sh's gpu_free() refuses to start a job while any registered Blender that is not its own is live.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
QDIR="$ROOT/export/out/bake_queue"
STATUS="$QDIR/status.json"
mkdir -p "$QDIR"
state=idle
case "${1:-}" in
  claim)   state=running ;;
  release) state=idle ;;
  *) echo "usage: gpu_lock.sh {claim|release} [note]" >&2; exit 2 ;;
esac
python3 - "$STATUS" "$state" "${2:-}" <<'PY'
import json, os, sys, time
path, state, note = sys.argv[1:4]
d = {}
if os.path.exists(path):
    try:
        d = json.load(open(path))
    except Exception:
        d = {}
d.update(dict(state=state, current=note or None,
              owner=os.environ.get("PFA_QUEUE_OWNER", "phase6-bake/gpu_lock"),
              updated=time.strftime("%Y-%m-%dT%H:%M:%S%z"), note=note or state))
d.setdefault("started", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
d.setdefault("done", 0)
d.setdefault("total", 0)
json.dump(d, open(path, "w"), indent=1)
PY
mkdir -p "$MAIN/export/out/bake_queue"
cp -f "$STATUS" "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || true
echo "[gpu_lock] $state  ${2:-}"
