#!/bin/zsh
# Copy the finished Gate 0 outputs to the MAIN checkout, which is where the viewer worktree reads them from
# (export/out/ is gitignored in both). Source of truth stays in this worktree.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN=${PFA_MAIN_ROOT:-/Users/dk/Projects/3d render blender 3rd attempt building}
mkdir -p "$MAIN/export/out/gate0" "$MAIN/renders/web"
# review finding 9: no --delete. $MAIN/export/out/gate0/ is shared with the export and viewer agents.
[ -d "$ROOT/export/out/gate0" ] && \
  rsync -a --exclude 'gate0_set.blend*' "$ROOT/export/out/gate0/" "$MAIN/export/out/gate0/"
# Gate 1: the same rule - no --delete, and the two working .blends stay in this worktree (325 MB).
if [ -d "$ROOT/export/out/gate1" ]; then
  mkdir -p "$MAIN/export/out/gate1"
  rsync -a --exclude 'gate1_set.blend*' --exclude 'gate1_bake.blend*' \
        "$ROOT/export/out/gate1/" "$MAIN/export/out/gate1/"
  echo "[gate1] synced to $MAIN/export/out/gate1 ($(du -sk "$MAIN/export/out/gate1" | cut -f1) KiB)"
fi
# Gate 2: same rule - no --delete, the two bake blends (400 MB) stay in this worktree.
if [ -d "$ROOT/export/out/gate2" ]; then
  mkdir -p "$MAIN/export/out/gate2"
  # tex/ is the 16-bit PNG bake output (regenerable, ~700 MB); only tex_ktx2 ships.
  rsync -a --exclude 'gate2_bake.blend*' --exclude 'gate2_orn_bake.blend*' --exclude 'tex/' --exclude 'verify/verify_*.png' \
        "$ROOT/export/out/gate2/" "$MAIN/export/out/gate2/"
  echo "[gate2] synced to $MAIN/export/out/gate2 ($(du -sk "$MAIN/export/out/gate2" | cut -f1) KiB)"
fi
# Gate 3: this worktree only WRITES the export hand-off (uv2_relay_status.json) into out/gate3; the bake's
# own gate3 outputs live in MAIN and must not be touched, hence no --delete and no blends/EXRs from here.
if [ -d "$ROOT/export/out/gate3" ]; then
  mkdir -p "$MAIN/export/out/gate3"
  rsync -a --exclude 'gate3_*.blend*' --exclude 'tex/' \
        "$ROOT/export/out/gate3/" "$MAIN/export/out/gate3/"
  echo "[gate3] synced to $MAIN/export/out/gate3 ($(du -sk "$MAIN/export/out/gate3" | cut -f1) KiB)"
fi
mkdir -p "$MAIN/export/out/bake_queue"
cp -f "$ROOT/export/out/bake_queue/status.json" "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || true
for f in "$ROOT"/renders/web/gate0_*.png(N); do cp -f "$f" "$MAIN/renders/web/"; done
echo "[gate0] synced to $MAIN/export/out/gate0 ($(du -sk "$MAIN/export/out/gate0" | cut -f1) KiB)"
