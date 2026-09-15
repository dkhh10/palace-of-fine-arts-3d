#!/bin/zsh
# Phase 6 Gate 0 driver: steps 1-7 in order, one Blender at a time, blocking, each through scripts/blender_run.sh.
#
#   export/gate0.sh [first_step] [last_step]        # default 1 7
#
# Idempotent: every step rebuilds its own outputs. Logs to renders/logs/gate0_<step>.log. Stops at the first failure.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN="/Users/dk/Projects/3d render blender 3rd attempt building"
SRC="$MAIN/master_delivery.blend"
SET="$ROOT/export/out/gate0/gate0_set.blend"
export BLENDER_RUN_OWNER=phase6-bake
export PATH="$MAIN/tools/bin:$PATH"
mkdir -p "$ROOT/renders/logs"
FROM=${1:-1}; TO=${2:-7}

run() {  # run <step> <max_s> <blend> <script> [args...]
  local step=$1 max=$2 blend=$3 script=$4; shift 4
  [ "$step" -ge "$FROM" ] && [ "$step" -le "$TO" ] || return 0
  echo "=== gate0 step $step: $script"
  "$ROOT/scripts/blender_run.sh" "$max" -- --background "$blend" --python "$ROOT/export/$script" -- "$@" \
      2>&1 | tee "$ROOT/renders/logs/gate0_$step.log" | grep -E "^\[gate0\]|Error|Traceback" || true
}

run 1  900 "$SRC" export_set.py --gate0
run 2 2400 "$SET" bake_normal.py
run 3 1800 "$SET" bake_pbr.py
run 4 5400 "$SET" bake_lightmap.py
run 5 1800 "$SET" bake_lut.py
run 6  900 "$SET" gltf_export.py
if [ "$FROM" -le 6 ] && [ "$TO" -ge 6 ]; then "$HERE/gltf_pack.sh" 2>&1 | tee "$ROOT/renders/logs/gate0_6b.log"; fi
run 7 2400 "$SET" render_reference.py

# hand the finished set to the MAIN checkout, where the viewer worktree reads it from
if [ "$TO" -ge 6 ]; then "$HERE/sync_main.sh"; fi
echo "=== gate0 done"
