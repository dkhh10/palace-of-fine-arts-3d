#!/bin/zsh
# Run one headless Blender with a registered maximum duration, blocking until it exits.
# Usage: scripts/blender_run.sh <max_seconds> -- <blender args...>
#   e.g. scripts/blender_run.sh 900 -- --background --python scripts/light_preview.py -- --cams 1,3
# Registers the Blender pid + deadline for scripts/blender_watchdog.sh (which kills ONLY pids past their deadline).
# Exits with Blender's exit code. One agent, one Blender at a time: refuses if this agent's previous run is still alive
# (checked via the state files this wrapper wrote, keyed by BLENDER_RUN_OWNER, default the current user's tty/agent id).
STATE=${BLENDER_WATCHDOG_STATE:-$HOME/.cache/pfa_blender_watchdog}
mkdir -p "$STATE"
BLENDER_BIN=/Applications/Blender.app/Contents/MacOS/Blender
max=$1; shift
[[ "$max" == <-> ]] || { echo "blender_run.sh: first arg must be max seconds (got '$max')" >&2; exit 2; }
[ "$1" = "--" ] && shift
case " $* " in *" --background "*) ;; *) echo "blender_run.sh: refusing to run Blender without --background" >&2; exit 2;; esac
start=$(date +%s); deadline=$(( start + max ))
"$BLENDER_BIN" "$@" &
pid=$!
printf '%s %s %s %s\n' "$deadline" "$start" "${BLENDER_RUN_OWNER:-$USER}" "$*" > "$STATE/$pid"
wait $pid; rc=$?
rm -f "$STATE/$pid"
echo "blender_run.sh: pid $pid exited rc=$rc after $(( $(date +%s) - start )) s (max $max)" >&2
exit $rc
