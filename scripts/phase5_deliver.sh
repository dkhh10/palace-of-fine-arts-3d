#!/bin/zsh
# Phase 5 delivery driver (docs/phase5_checklist.md steps 2-6). One Blender at a time, every run through
# scripts/blender_run.sh with a registered max duration (CLAUDE.md watchdog categories: Eevee preview 600 s,
# 4K timing 7200 s). Stops on the first non-zero exit. Logs to renders/logs/phase5_<step>.log. Each step is
# individually runnable.
#
#   scripts/phase5_deliver.sh                                        # steps 2..6 in order
#   scripts/phase5_deliver.sh 4                                      # just the 4K hero timing probe
#   scripts/phase5_deliver.sh 5                                      # final hero, sample count/res auto-picked
#                                                                     # from step 4's logged wall_time_s
#   scripts/phase5_deliver.sh 5 --final-spp 768 --res 3840 2160      # override the auto pick
#
set -e -o pipefail
cd "$(dirname "$0")/.."
LOGS=renders/logs
mkdir -p "$LOGS" renders/final renders/anim

step2() {
  local log=$LOGS/phase5_2.log
  local t0=$SECONDS
  # checklist step 2, verbatim: master.blend open time must be < 60 s (round 6 measured 0.72 s).
  scripts/blender_run.sh 300 -- --background master.blend --python-expr "import time" 2>&1 | tee "$log"
  echo "[phase5_deliver] step 2 (master.blend open time) wall $(( SECONDS - t0 ))s -- log $log"
}

step3() {
  local log=$LOGS/phase5_3.log
  local t0=$SECONDS
  # checklist step 3: the saved Eevee viewport preset, six QA cameras, target < 150 s total.
  scripts/blender_run.sh 600 -- --background --python scripts/qa_render_round.py -- --round final --eevee 2>&1 | tee "$log"
  echo "[phase5_deliver] step 3 (eevee six-camera pass) wall $(( SECONDS - t0 ))s -- log $log"
}

step4() {
  local log=$LOGS/phase5_4.log
  local t0=$SECONDS
  # checklist step 4: 128 spp FIXED, adaptive OFF, time_limit 0, 3840x2160, cam01, final preset. max 7200 s.
  scripts/blender_run.sh 7200 -- --background --python scripts/phase5_hero.py -- \
      --spp 128 --res 3840 2160 --adaptive off --time-limit 0 2>&1 | tee "$log"
  echo "[phase5_deliver] step 4 (4K hero timing probe, 128 spp fixed) wall $(( SECONDS - t0 ))s -- log $log"
}

# Picks step 5's sample count / resolution from step 4's measured wall_time_s (checklist: target under 90 min;
# 768 spp only if 128 spp took < 12 min at 4K; otherwise the checklist says render at 2560 wide instead).
pick_step5_settings() {
  local log=$LOGS/phase5_4.log
  local t128=""
  if [[ -f "$log" ]]; then
    t128=$(grep -o 'wall_time_s=[0-9.]*' "$log" | tail -1 | cut -d= -f2 || true)
  fi
  if [[ -z "$t128" ]]; then
    echo "[phase5_deliver] step 5: no step-4 wall_time_s found in $log; falling back to a conservative 2560x1440 @ 128 spp" >&2
    echo "128 2560 1440"
    return
  fi
  if awk -v t="$t128" 'BEGIN{exit !(t<720)}'; then
    echo "768 3840 2160"
  else
    echo "128 2560 1440"
  fi
}

step5() {
  local spp="" resw="" resh=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --final-spp) spp="$2"; shift 2 ;;
      --res) resw="$2"; resh="$3"; shift 3 ;;
      *) echo "[phase5_deliver] step5: unknown arg $1" >&2; exit 2 ;;
    esac
  done
  if [[ -z "$spp" || -z "$resw" || -z "$resh" ]]; then
    local auto_spp auto_resw auto_resh
    read auto_spp auto_resw auto_resh <<< "$(pick_step5_settings)"
    spp="${spp:-$auto_spp}"; resw="${resw:-$auto_resw}"; resh="${resh:-$auto_resh}"
  fi
  echo "[phase5_deliver] step 5: rendering final hero at ${resw}x${resh} @ ${spp} spp"
  local log=$LOGS/phase5_5.log
  local t0=$SECONDS
  scripts/blender_run.sh 7200 -- --background --python scripts/phase5_hero.py -- \
      --spp "$spp" --res "$resw" "$resh" --adaptive off --denoise on --time-limit 0 2>&1 | tee "$log"
  echo "[phase5_deliver] step 5 (final hero ${resw}x${resh} @ ${spp} spp) wall $(( SECONDS - t0 ))s -- log $log"

  local native="renders/final/hero_cam01_${resw}x${resh}_${spp}spp.png"
  local canonical="renders/final/hero_cam01_3840x2160.png"
  if [[ "$resw" == "3840" && "$resh" == "2160" ]]; then
    cp "$native" "$canonical"
  else
    # checklist: "render at 2560 wide and upscale if native 4K is too slow". Same aspect ratio (16:9), so an exact
    # resize does not distort; this is a delivery-name convenience copy, the native file above is the real render.
    sips -z 2160 3840 "$native" --out "$canonical" >/dev/null
    echo "[phase5_deliver] step 5: upscaled ${resw}x${resh} -> 3840x2160 (native 4K was too slow) -> $canonical"
  fi
}

step6() {
  local log=$LOGS/phase5_6.log
  local t0=$SECONDS
  # checklist step 6: 640x360, 16 TAA, every 2nd frame. tech_notes.md: "give blender_run.sh an honest max (7200)".
  scripts/blender_run.sh 7200 -- --background --python scripts/phase5_flythrough.py -- \
      --res 640 360 --samples 16 --frame-step 2 2>&1 | tee "$log"
  echo "[phase5_deliver] step 6 (flythrough test frames) wall $(( SECONDS - t0 ))s -- log $log"

  local fps fstep
  fps=$(grep -o 'fps=[0-9.]*' "$log" | tail -1 | cut -d= -f2 || true)
  fstep=$(grep -o 'frame_step=[0-9]*' "$log" | tail -1 | cut -d= -f2 || true)
  fps=${fps:-24}; fstep=${fstep:-2}
  local outfps=$(( fps / fstep ))
  local t1=$SECONDS
  ffmpeg -y -loglevel error -framerate "$outfps" -pattern_type glob \
      -i "renders/anim/flythrough_test/frame_*.png" \
      -c:v libx264 -crf 18 -pix_fmt yuv420p renders/final/flythrough_test_640.mp4
  echo "[phase5_deliver] step 6 (ffmpeg encode @ ${outfps} fps) wall $(( SECONDS - t1 ))s -- renders/final/flythrough_test_640.mp4"
}

target="${1:-all}"
[[ $# -gt 0 ]] && shift

case "$target" in
  2) step2 ;;
  3) step3 ;;
  4) step4 ;;
  5) step5 "$@" ;;
  6) step6 ;;
  all)
    step2
    step3
    step4
    step5
    step6
    ;;
  *)
    echo "usage: $0 [2|3|4|5|6|all] [step-5 only: --final-spp N --res W H]" >&2
    exit 2
    ;;
esac
