#!/bin/zsh
# Phase 6c: claim / release the GPU status the OTHER agents read, for a one-off Blender run that is not a
# bake_queue job (the 6c impostor diagnosis, the trees_far set-up runs).
#
#   export/gpu_lock.sh claim   <note> [secs]      # status.json -> running, with pid + expires_at
#   export/gpu_lock.sh release [note]             # status.json -> idle
#   export/gpu_lock.sh check                      # print the EFFECTIVE state (running|idle) and why
#   export/gpu_lock.sh run <secs> -- <cmd...>     # claim, run, release on EXIT/INT/TERM even on a crash
#
# Why this exists: CLAUDE.md makes export/out/bake_queue/status.json the ONLY signal another agent (the viewer
# engineer's headless Chrome, which also wants the GPU) may read for GPU liveness - never CPU, never log
# silence. A Blender run outside the queue therefore has to keep that file honest, in the worktree AND in the
# MAIN checkout where the other agents read it. Mutual exclusion itself is already enforced one level down:
# every run goes through scripts/blender_run.sh, which registers the pid with the watchdog, and
# bake_queue.sh's gpu_free() refuses to start a job while any registered Blender that is not its own is live.
#
# Review r1 findings 1 and 2 (docs/reviews/phase6c_bake_r1_review.md):
#   1. a crash between claim and release used to leave the file saying `running` for ever - the watchdog kills
#      pids, it never edits this file. `claim` now records `pid` and `expires_at`, `run` releases from a trap,
#      and a reader (here, bake_queue.sh and any agent) treats `running` as IDLE once that pid is dead or
#      `expires_at` has passed. Both are recorded honestly: `secs` is the same duration the run registers with
#      blender_run.sh.
#   2. claim/release used to ignore who held the file, so a release during a live bake flipped a real bake to
#      idle. Both now refuse while the record is EFFECTIVELY running under a different owner, unless --force.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
QDIR="$ROOT/export/out/bake_queue"
STATUS="$QDIR/status.json"
# Review r2 finding 3: CLAUDE.md's GPU signal is the MAIN checkout's copy, not this worktree's. Writes
# already mirror to MAIN; the READER has to read MAIN too, or an agent in another worktree - whose own copy
# is a stale `idle` from an earlier gate - is told the GPU is free in the middle of a live bake. `lock_state`
# reads BOTH and the effective-RUNNING one wins, so the lock holds whichever file a caller happens to have.
MAIN_STATUS="$MAIN/export/out/bake_queue/status.json"
mkdir -p "$QDIR"
OWNER=${PFA_QUEUE_OWNER:-phase6-bake/gpu_lock}

force=0
args=()
for a in "$@"; do
  [ "$a" = "--force" ] && { force=1; continue; }
  args+=("$a")
done
set -- "${args[@]}"

# ---------------------------------------------------------------- the reader: state, and why
# Prints "<effective state> <holder owner> <reason>".  A `running` record whose pid is gone or whose
# expires_at has passed is reported as idle (stale), which is what makes a crash self-healing.
lock_state () {
  python3 - "$MAIN_STATUS" "$STATUS" <<'PYEOF'
import json, os, sys, time


def read(path):
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path))
    except Exception:
        return {}


def effective(d, where):
    """(state, description). `running` with a dead pid or a passed expires_at reads as IDLE - that is what
    makes a crash between claim and release self-healing (review r1 finding 1)."""
    state, owner = d.get("state", "absent"), d.get("owner", "-")
    if state != "running":
        return "idle", f"idle {owner} state={state} [{where}]"
    pid, exp = d.get("pid"), d.get("expires_at")
    if pid:
        try:
            os.kill(int(pid), 0)
        except ValueError:
            pass
        except ProcessLookupError:
            return "idle", f"idle {owner} stale: pid {pid} is gone [{where}]"
        except PermissionError:
            pass          # EPERM means the process EXISTS and is not ours: alive, not stale
    if exp and time.time() > float(exp):
        return "idle", f"idle {owner} stale: expired {int(time.time() - float(exp))}s ago [{where}]"
    left = int(float(exp) - time.time()) if exp else "-"
    return "running", f"running {owner} pid={pid} expires_in={left}s [{where}]"


rows = [effective(read(p), w) for p, w in ((sys.argv[1], "MAIN"), (sys.argv[2], "worktree"))]
for st, msg in rows:
    if st == "running":
        print(msg)
        raise SystemExit(0)
print(rows[0][1])
PYEOF
}

write_status () {   # state note pid expires_at
  python3 - "$STATUS" "$1" "$2" "$3" "$4" "$OWNER" <<'PY'
import json, os, sys, time
path, state, note, pid, exp, owner = sys.argv[1:7]
d = {}
if os.path.exists(path):
    try:
        d = json.load(open(path))
    except Exception:
        d = {}
d.update(dict(state=state, current=note or None, owner=owner,
              updated=time.strftime("%Y-%m-%dT%H:%M:%S%z"), note=note or state))
d["pid"] = int(pid) if pid else None
d["expires_at"] = float(exp) if exp else None
d.setdefault("started", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
d.setdefault("done", 0)
d.setdefault("total", 0)
json.dump(d, open(path, "w"), indent=1)
PY
  mkdir -p "$MAIN/export/out/bake_queue"
  cp -f "$STATUS" "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || true
}

guard () {          # refuse to touch a lock somebody else is effectively holding
  local line=$(lock_state)
  local st=(${=line})
  if [ "${st[1]}" = "running" ] && [ "${st[2]}" != "$OWNER" ] && [ $force -eq 0 ]; then
    echo "[gpu_lock] refusing: $line - use --force only if you know that holder is dead" >&2
    exit 3
  fi
}

release_trap () { write_status idle "released by trap" "" ""; }

case "${1:-}" in
  check)
    lock_state
    ;;
  claim)
    # A bare `claim` is an AGENT-level hold: there is no process to name, so it records NO pid and the
    # honest `secs` alone governs it. Naming the calling shell's pid (what this did) was worse than useless -
    # that shell exits when the command returns, so every later `check` read a live lock as stale. A claim
    # around a real process uses `gpu_lock.sh run`, which records its own pid, or passes PFA_LOCK_PID.
    guard
    secs=${3:-1800}
    write_status running "${2:-}" "${PFA_LOCK_PID:-}" $(( $(date +%s) + secs ))
    echo "[gpu_lock] running  ${2:-}  (pid ${PFA_LOCK_PID:-none}, ${secs}s)"
    ;;
  release)
    guard
    write_status idle "${2:-}" "" ""
    echo "[gpu_lock] idle  ${2:-}"
    ;;
  run)
    secs=${2:?usage: gpu_lock.sh run <secs> -- <cmd...>}
    shift 2
    [ "$1" = "--" ] && shift
    [[ "$secs" == <-> ]] || { echo "gpu_lock.sh run: <secs> must be a number" >&2; exit 2; }
    guard
    write_status running "$*" "$$" $(( $(date +%s) + secs ))
    trap release_trap EXIT INT TERM
    echo "[gpu_lock] running (pid $$, ${secs}s): $*"
    "$@"
    ;;
  *) echo "usage: gpu_lock.sh {claim <note> [secs]|release [note]|check|run <secs> -- <cmd...>} [--force]" >&2; exit 2 ;;
esac
