#!/bin/zsh
# Blender watchdog, registered-deadline model (rewritten 2026-09-09 on the user's rule):
#   kills ONLY Blender pids whose registered maximum duration (written by scripts/blender_run.sh) has passed.
#   Never infers idleness from CPU time (a Metal GPU render accrues almost none) or from log silence.
#   Unregistered headless Blender pids are reported once per pass, never killed.
# Usage: scripts/blender_watchdog.sh            (one pass)
#        scripts/blender_watchdog.sh --loop     (every 30 s; the lead keeps this running during agent waves)
STATE=${BLENDER_WATCHDOG_STATE:-$HOME/.cache/pfa_blender_watchdog}
mkdir -p "$STATE"
pass() {
  local now=$(date +%s)
  for f in "$STATE"/*(N); do
    local p=${f:t}
    if ! kill -0 "$p" 2>/dev/null; then rm -f "$f"; continue; fi
    local deadline start owner cmd
    read deadline start owner cmd < "$f"
    if [ "$now" -gt "$deadline" ]; then
      echo "$(date '+%H:%M:%S') watchdog: killing Blender pid $p ($owner), registered max $(( deadline - start )) s exceeded by $(( now - deadline )) s: ${cmd[1,140]}"
      kill $p; sleep 10; kill -9 $p 2>/dev/null; rm -f "$f"
    fi
  done
  local pids=$(pgrep -f "^/Applications/Blender.app/Contents/MacOS/Blender --background" || true)
  for p in ${(f)pids}; do
    [ -f "$STATE/$p" ] || echo "$(date '+%H:%M:%S') watchdog: unregistered Blender pid $p (not killed; launch via scripts/blender_run.sh): $(ps -o etime=,command= -p $p | cut -c1-150)"
  done
}
if [ "$1" = "--loop" ]; then while true; do pass; sleep 30; done; else pass; fi
