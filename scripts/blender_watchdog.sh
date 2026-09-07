#!/bin/zsh
# Kill headless Blender processes that are idle: older than 5 min AND used < 1 s of CPU over a 15 s sample.
# Usage: scripts/blender_watchdog.sh            (one pass)
#        scripts/blender_watchdog.sh --loop     (every 60 s, for the lead's session)
cpusec() { ps -o cputime= -p "$1" 2>/dev/null | awk -F'[:.]' '{ if (NF>=3) print $1*60+$2; else print 0 }'; }
etimesec() { ps -o etime= -p "$1" 2>/dev/null | awk -F'[-:]' '{ n=NF; s=$n; if (n>=2) s+=$(n-1)*60; if (n>=3) s+=$(n-2)*3600; if (n>=4) s+=$(n-3)*86400; print s+0 }'; }
pass() {
  local pids=$(pgrep -f "MacOS/Blender --background" || true)
  [ -z "$pids" ] && return 0
  typeset -A before
  for p in ${(f)pids}; do before[$p]=$(cpusec $p); done
  sleep 15
  for p in ${(f)pids}; do
    kill -0 $p 2>/dev/null || continue
    local age=$(etimesec $p) used=$(( $(cpusec $p) - ${before[$p]:-0} ))
    if [ "$age" -gt 300 ] && [ "$used" -lt 1 ]; then
      echo "$(date '+%H:%M:%S') watchdog: killing idle Blender pid $p (age ${age}s, cpu +${used}s/15s): $(ps -o command= -p $p | cut -c1-120)"
      kill $p; sleep 5; kill -9 $p 2>/dev/null
    fi
  done
}
if [ "$1" = "--loop" ]; then while true; do pass; sleep 45; done; else pass; fi
