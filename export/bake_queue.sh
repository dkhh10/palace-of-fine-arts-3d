#!/bin/zsh
# Gate 1 step 2: detached queue over export/out/gate1/bake_jobs.json - one Blender per ORN prototype.
#
#   export/bake_queue.sh start     # fork the runner, return immediately
#   export/bake_queue.sh run       # run it in the foreground (what `start` execs)
#   export/bake_queue.sh status    # print export/out/bake_queue/status.json
#   export/bake_queue.sh stop      # ask the runner to stop after the job it is on
#
# Contract (CLAUDE.md "Phase 6 / Machine rules" + the lead's GPU rule, docs/decisions.md 2026-09-15):
#   * status.json is {state, current, done, total, started, updated, jobs:[...]} and is the ONLY way another
#     agent learns whether the GPU is busy. Idleness is never read from CPU or log silence.
#   * a job starts only when the watchdog state dir holds no LIVE registered Blender pid other than this
#     queue's own. Liveness is tested with kill -0 on each state file's name (the pid); stale files are ignored.
#   * resume: a job whose export/out/gate1/bake/<id>.json exists and whose two maps exist is skipped.
#   * every Blender goes through scripts/blender_run.sh 900 (the Gate 0 measurement was 9.3 s normal +
#     220.9 s AO for a 64 k capital, so 900 s is ~3.5x the worst job).
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
SRC="$ROOT/export/out/gate1/gate1_bake.blend"
JOBS="$ROOT/export/out/gate1/bake_jobs.json"
QDIR="$ROOT/export/out/bake_queue"
STATUS="$QDIR/status.json"
LOG="$QDIR/bake_queue.log"
STOP="$QDIR/STOP"
STATE=${BLENDER_WATCHDOG_STATE:-$HOME/.cache/pfa_blender_watchdog}
MAXS=900
mkdir -p "$QDIR" "$ROOT/export/out/gate1/bake"

write_status () {  # state current done total extra
  python3 - "$STATUS" "$1" "$2" "$3" "$4" "$5" <<'PY'
import json, os, sys, time
path, state, current, done, total, extra = sys.argv[1:7]
old = {}
if os.path.exists(path):
    try:
        old = json.load(open(path))
    except Exception:
        old = {}
old.update(dict(state=state, current=current or None, done=int(done), total=int(total),
                owner="phase6-export/bake_queue", updated=time.strftime("%Y-%m-%dT%H:%M:%S%z")))
old.setdefault("started", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
if extra:
    old["note"] = extra
json.dump(old, open(path, "w"), indent=1)
PY
}

record_job () {   # id seconds rc
  python3 - "$STATUS" "$1" "$2" "$3" <<'PY'
import json, sys, time
path, jid, secs, rc = sys.argv[1:5]
d = json.load(open(path))
d.setdefault("jobs", [])
d["jobs"] = [j for j in d["jobs"] if j["id"] != jid]
d["jobs"].append(dict(id=jid, wall_s=float(secs), rc=int(rc), at=time.strftime("%Y-%m-%dT%H:%M:%S%z")))
json.dump(d, open(path, "w"), indent=1)
PY
}

gpu_free () {
  # no LIVE registered Blender pid other than one this queue itself started
  local busy=0
  for f in "$STATE"/*(N); do
    local pid=${f:t}
    [[ "$pid" == <-> ]] || continue
    kill -0 "$pid" 2>/dev/null || continue          # stale registration, ignore
    if grep -q "bake_orn.py" "$f" 2>/dev/null; then continue; fi   # our own job
    busy=1
  done
  return $busy
}

cmd=${1:-start}
case "$cmd" in
  status) cat "$STATUS" 2>/dev/null || echo '{"state":"absent"}' ;;
  stop)   touch "$STOP"; echo "[bake_queue] stop requested" ;;
  start)
    [ -f "$JOBS" ] || { echo "bake_queue: $JOBS missing - run export_set.py -- --gate1 first" >&2; exit 2; }
    rm -f "$STOP"
    nohup "$0" run >>"$LOG" 2>&1 &
    echo "[bake_queue] detached pid $! - status: $STATUS, log: $LOG"
    ;;
  run)
    [ -f "$SRC" ] || { echo "bake_queue: $SRC missing" >&2; exit 2; }
    total=$(python3 -c "import json,sys;print(len(json.load(open('$JOBS'))['jobs']))")
    ids=(${(f)"$(python3 -c "import json;print('\n'.join(j['id'] for j in json.load(open('$JOBS'))['jobs']))")"})
    done_n=0
    write_status waiting "" 0 "$total" "queued"
    for id in $ids; do
      rec="$ROOT/export/out/gate1/bake/$id.json"
      if [ -f "$rec" ]; then
        done_n=$((done_n+1))
        echo "[bake_queue] skip $id (already done)"
        write_status waiting "" "$done_n" "$total" "resume skip"
        continue
      fi
      [ -f "$STOP" ] && { write_status stopped "" "$done_n" "$total" "STOP file"; echo "[bake_queue] stopped"; exit 0; }
      # GPU rule: wait (in THIS detached process, never in an agent turn) until no other registered Blender lives
      waited=0
      until gpu_free; do
        write_status waiting "$id" "$done_n" "$total" "another registered Blender holds the GPU (${waited}s)"
        sleep 20
        waited=$((waited+20))
        [ -f "$STOP" ] && { write_status stopped "" "$done_n" "$total" "STOP file"; exit 0; }
      done
      write_status running "$id" "$done_n" "$total" "baking"
      t0=$(date +%s)
      set +e
      "$ROOT/scripts/blender_run.sh" $MAXS -- --background "$SRC" --python "$HERE/bake_orn.py" -- --job "$id"
      rc=$?
      set -e
      dt=$(( $(date +%s) - t0 ))
      record_job "$id" "$dt" "$rc"
      if [ $rc -eq 0 ]; then done_n=$((done_n+1)); else echo "[bake_queue] job $id FAILED rc=$rc" >&2; fi
      echo "[bake_queue] $id rc=$rc ${dt}s ($done_n/$total)"
      write_status waiting "" "$done_n" "$total" "between jobs"
    done
    write_status idle "" "$done_n" "$total" "finished"
    echo "[bake_queue] finished $done_n/$total"
    ;;
  *) echo "usage: bake_queue.sh {start|run|status|stop}" >&2; exit 2 ;;
esac
