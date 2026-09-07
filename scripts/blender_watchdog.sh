#!/bin/zsh
# Kill headless Blender processes whose CPU time has not advanced for more than 5 minutes.
# 2026-09-07 lead fix (QA-03-1): a Cycles Metal render accrues almost no CPU time in the Blender process, so the
# integer-second cputime read as "idle" and three live GPU renders were killed. Now: cputime is compared at
# centisecond resolution, and nothing is killed while the GPU reports > 5 % device utilization.
# Matches ONLY the Blender binary itself (anchored), never shells whose command line mentions Blender.
# Usage: scripts/blender_watchdog.sh            (one pass; needs a previous pass's state to decide)
#        scripts/blender_watchdog.sh --loop     (every 30 s; the lead keeps this running during agent waves)
STATE=${BLENDER_WATCHDOG_STATE:-${TMPDIR:-/tmp}/blender_watchdog_state}
mkdir -p "$STATE"
IDLE_LIMIT=300
cpusec() { ps -o cputime= -p "$1" 2>/dev/null | tr -d ' '; }   # full string incl. centiseconds, e.g. 12:34.56
gpu_busy() { local u=$(ioreg -r -d 1 -c IOAccelerator 2>/dev/null | grep -o '"Device Utilization %"=[0-9]*' | head -1 | grep -o '[0-9]*$'); [ "${u:-0}" -gt 5 ]; }
pass() {
  local now=$(date +%s)
  local pids=$(pgrep -f "^/Applications/Blender.app/Contents/MacOS/Blender --background" || true)
  for f in "$STATE"/*(N); do kill -0 "${f:t}" 2>/dev/null || rm -f "$f"; done   # forget dead pids
  for p in ${(f)pids}; do
    local cpu=$(cpusec $p) last_cpu=-1 since=$now
    [ -f "$STATE/$p" ] && read last_cpu since < "$STATE/$p"
    if [ "$cpu" != "$last_cpu" ]; then since=$now; fi
    echo "$cpu $since" > "$STATE/$p"
    local idle=$(( now - since ))
    if [ "$idle" -gt "$IDLE_LIMIT" ] && gpu_busy; then
      echo "$(date '+%H:%M:%S') watchdog: pid $p has no CPU progress for ${idle}s but the GPU is busy; not killing"
    elif [ "$idle" -gt "$IDLE_LIMIT" ]; then
      echo "$(date '+%H:%M:%S') watchdog: killing Blender pid $p, no CPU progress for ${idle}s: $(ps -o command= -p $p | cut -c1-140)"
      kill $p; sleep 5; kill -9 $p 2>/dev/null; rm -f "$STATE/$p"
    fi
  done
}
if [ "$1" = "--loop" ]; then while true; do pass; sleep 30; done; else pass; fi
