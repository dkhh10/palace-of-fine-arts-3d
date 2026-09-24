#!/bin/zsh
# Phase 10 Cycles station references for QA 27 (lead, 2026-09-24): six stations at 1080p 32 spp (+ hero at 64 spp)
# from a SCRATCH COPY of master_delivery.blend (regenerate it first: PFA_PACK=1 scripts/phase5_deliver.sh 1b).
# One Blender at a time through blender_run.sh; 960 px copies for git. Usage: scripts/p10_cycles_refs.sh [tag=cycles_p10]
set -e
cd "$(dirname "$0")/.."
TAG=${1:-cycles_p10}; OUT=renders/qa_comparisons/$TAG; mkdir -p "$OUT/960" renders/logs
SCRATCH=renders/logs/${TAG}_scratch.blend; cp master_delivery.blend "$SCRATCH"
for job in "01 64" "01 32" "02 32" "03 32" "04 32" "05 32" "06 32"; do
  set -- ${=job}; cam=$1; spp=$2; png="$OUT/cam${cam}_1080_${spp}spp.png"
  [[ -f $png ]] && { echo "skip $png"; continue; }
  scripts/blender_run.sh 1500 -- --background --python scripts/p8_cycles_refs.py -- --blend "$SCRATCH" --cam "$cam" --out "$png" --samples "$spp" \
    > "renders/logs/${TAG}_cam${cam}_${spp}.log" 2>&1
  sips -Z 960 "$png" --out "$OUT/960/cam${cam}_1080_${spp}spp.jpg" >/dev/null
done
rm -f "$SCRATCH"; touch "$OUT/.refs_done"; echo "[p10refs] done -> $OUT"
