#!/bin/zsh
# Phase 8b: the band-atlas queue - one Blender per prototype over export/out/gate3/band/band_set.json.
#
#   export/band_queue.sh start     # fork the runner, return immediately
#   export/band_queue.sh run       # run it in the foreground (what `start` execs)
#   export/band_queue.sh status    # print export/out/bake_queue/status.json
#   export/band_queue.sh stop      # ask the runner to stop after the job it is on
#
# Same contract as export/bake_queue.sh (CLAUDE.md "Phase 6 / Machine rules"): export/out/bake_queue/status.json
# is the ONLY signal another agent reads for GPU liveness, it is mirrored into MAIN on every write, `running`
# carries this runner's pid and an honest expires_at, a job starts only when no OTHER registered Blender pid is
# live, and every Blender goes through scripts/blender_run.sh with a per-job maximum. Resume: a prototype whose
# band/rec/<proto>.json exists is skipped (that record is written only after the PNG is read back verified).
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
SET="$ROOT/export/out/gate3/band/band_set.json"
BLEND="$ROOT/export/out/gate3/band_imp.blend"
RECDIR="$ROOT/export/out/gate3/band/rec"
QDIR="$ROOT/export/out/bake_queue"
STATUS="$QDIR/status.json"
LOG="$QDIR/band_queue.log"
STOP="$QDIR/BAND_STOP"
STATE=${BLENDER_WATCHDOG_STATE:-$HOME/.cache/pfa_blender_watchdog}
MAXS=${PFA_BAND_MAXS:-600}        # 36 views at ~1.6 s + the 67 MB nursery load; measured ~90 s/prototype
mkdir -p "$QDIR" "$RECDIR"

write_status () {  # state current done total note
  local lpid="" lexp=""
  case "$1" in running|waiting) lpid=$RUNNER_PID; lexp=$(( $(date +%s) + MAXS + 60 ));; esac
  python3 - "$STATUS" "$1" "$2" "$3" "$4" "$5" "$lpid" "$lexp" <<'PY'
import json, os, sys, time
path, state, current, done, total, extra, pid, exp = sys.argv[1:9]
old = {}
if os.path.exists(path):
    try:
        old = json.load(open(path))
    except Exception:
        old = {}
old.update(dict(state=state, current=current or None, done=int(done), total=int(total),
                owner=os.environ.get("PFA_QUEUE_OWNER", "phase8-bake/band"),
                updated=time.strftime("%Y-%m-%dT%H:%M:%S%z")))
old["pid"] = int(pid) if pid else None
old["expires_at"] = float(exp) if exp else None
if state == "waiting" and not old.get("started_band"):
    old["started_band"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
old.setdefault("started", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
if extra:
    old["note"] = extra
json.dump(old, open(path, "w"), indent=1)
PY
  mkdir -p "$MAIN/export/out/bake_queue"
  cp -f "$STATUS" "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || true
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
  cp -f "$STATUS" "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || true
}

RUNNER_TAG="band_queue_$$"
RUNNER_PID=$$
export BLENDER_RUN_OWNER="$RUNNER_TAG"
gpu_free () {
  local busy=0
  for f in "$STATE"/*(N); do
    local pid=${f:t}
    [[ "$pid" == <-> ]] || continue
    kill -0 "$pid" 2>/dev/null || continue
    [[ "$(awk 'NR==1{print $3}' "$f" 2>/dev/null)" == "$RUNNER_TAG" ]] && continue
    busy=1
  done
  return $busy
}

cmd=${1:-start}
case "$cmd" in
  status) cat "$STATUS" 2>/dev/null || echo '{"state":"absent"}' ;;
  stop)   touch "$STOP"; echo "[band_queue] stop requested" ;;
  start)
    [ -f "$SET" ] || { echo "band_queue: $SET missing - run export/band_set.py first" >&2; exit 2; }
    rm -f "$STOP"
    nohup "$0" run >>"$LOG" 2>&1 &
    echo "[band_queue] detached pid $! - status: $STATUS, log: $LOG"
    ;;
  run)
    [ -f "$BLEND" ] || { echo "band_queue: $BLEND missing" >&2; exit 2; }
    queue_died () {
      python3 -c "import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if d.get('state')=='idle' else 1)" \
        "$STATUS" 2>/dev/null && return 0
      write_status idle "" "${done_n:-0}" "${total:-0}" "band runner exited"
    }
    trap queue_died EXIT INT TERM
    ids=(${(f)"$(python3 -c "import json;print('\n'.join(json.load(open('$SET'))['jobs']))")"})
    total=${#ids}
    done_n=0
    write_status waiting "" 0 "$total" "band atlases queued"
    for id in $ids; do
      rec="$RECDIR/$id.json"
      if [ -f "$rec" ]; then
        done_n=$((done_n+1)); echo "[band_queue] skip $id (already done)"
        write_status waiting "" "$done_n" "$total" "resume skip"; continue
      fi
      [ -f "$STOP" ] && { write_status stopped "" "$done_n" "$total" "STOP file"; echo "[band_queue] stopped"; exit 0; }
      waited=0
      until gpu_free; do
        write_status waiting "$id" "$done_n" "$total" "another registered Blender holds the GPU (${waited}s)"
        sleep 20; waited=$((waited+20))
        [ -f "$STOP" ] && { write_status stopped "" "$done_n" "$total" "STOP file"; exit 0; }
      done
      write_status running "$id" "$done_n" "$total" "band atlas"
      t0=$(date +%s)
      set +e
      "$ROOT/scripts/blender_run.sh" $MAXS -- --background "$BLEND" --python-exit-code 1 \
          --python "$HERE/bake_band.py" -- --proto "$id"
      rc=$?
      set -e
      [ -f "$rec" ] || rc=$(( rc == 0 ? 90 : rc ))
      dt=$(( $(date +%s) - t0 ))
      record_job "$id" "$dt" "$rc"
      if [ $rc -eq 0 ]; then done_n=$((done_n+1)); else echo "[band_queue] job $id FAILED rc=$rc" >&2; fi
      echo "[band_queue] $id rc=$rc ${dt}s ($done_n/$total)"
      write_status waiting "" "$done_n" "$total" "between band jobs"
    done
    write_status idle "" "$done_n" "$total" "band atlases finished"
    echo "[band_queue] finished $done_n/$total"
    ;;
  *) echo "usage: band_queue.sh {start|run|status|stop}" >&2; exit 2 ;;
esac
