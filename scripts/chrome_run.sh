#!/bin/zsh
# Run one headless-Chrome job (the raw Chrome binary, or a node/puppeteer script that launches it) with a registered
# maximum duration, blocking until it exits. Phase 6 screenshot hygiene, same model as scripts/blender_run.sh.
# Usage: scripts/chrome_run.sh <max_seconds> -- <command...>
#   scripts/chrome_run.sh 120 -- node web/tools/screenshot.mjs --station 1 --out renders/web/cam01.png
#   scripts/chrome_run.sh 60  -- "$PFA_CHROME" --headless=new --screenshot=out.png --window-size=2560,1440 URL
# Registers pid + deadline in the blender_run.sh state dir, so scripts/blender_watchdog.sh --loop kills it ONLY past
# its deadline; any headless Chrome left behind is killed on exit. Never run while the bake queue owns the GPU.
STATE=${BLENDER_WATCHDOG_STATE:-$HOME/.cache/pfa_blender_watchdog}
mkdir -p "$STATE"
export PFA_CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
max=$1; shift
[[ "$max" == <-> ]] || { echo "chrome_run.sh: first arg must be max seconds (got '$max')" >&2; exit 2; }
[ "$1" = "--" ] && shift
start=$(date +%s); deadline=$(( start + max ))
"$@" &
pid=$!
printf '%s %s %s %s\n' "$deadline" "$start" "${BLENDER_RUN_OWNER:-$USER}-chrome" "$*" > "$STATE/$pid"
wait $pid; rc=$?
rm -f "$STATE/$pid"
pkill -f "Google Chrome.*--headless" 2>/dev/null && echo "chrome_run.sh: killed leftover headless Chrome" >&2
echo "chrome_run.sh: pid $pid exited rc=$rc after $(( $(date +%s) - start )) s (max $max)" >&2
exit $rc
