#!/bin/zsh
# Copy the finished Gate 0 outputs to the MAIN checkout, which is where the viewer worktree reads them from
# (export/out/ is gitignored in both). Source of truth stays in this worktree.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
MAIN="/Users/dk/Projects/3d render blender 3rd attempt building"
mkdir -p "$MAIN/export/out/gate0" "$MAIN/renders/web"
rsync -a --delete --exclude 'gate0_set.blend*' "$ROOT/export/out/gate0/" "$MAIN/export/out/gate0/"
mkdir -p "$MAIN/export/out/bake_queue"
cp -f "$ROOT/export/out/bake_queue/status.json" "$MAIN/export/out/bake_queue/status.json" 2>/dev/null || true
for f in "$ROOT"/renders/web/gate0_*.png(N); do cp -f "$f" "$MAIN/renders/web/"; done
echo "[gate0] synced to $MAIN/export/out/gate0 ($(du -sk "$MAIN/export/out/gate0" | cut -f1) KiB)"
