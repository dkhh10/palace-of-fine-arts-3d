# Phase 10 ENV round 1 — report (in progress)

## Checkpoint 2026-09-24
Branch `phase10-env`. environment.blend REBUILT with the p10 changes (renders/logs/p10env_env_build2.log, rc 0) and
committed; master NOT yet rebuilt with it (the worktree master.blend is the BEFORE state; it is gitignored).

Done / measured (scripts/env_p10_boxes.py, cam-01 1920x1080; ref 169 registered by env_r8_fit.REF_XF):
| box | ref 169 | before (Eevee, p10_before_cam01) | before (cycles_p9 cam01) |
|---|---|---|---|
| 1 NE mass brief box x .58-.74 y .28-.44: dark / sky / crown-top | 15.2 / 34.8 % / 398 px | 20.4 / 57.7 % / 474 px | 15.4 / 58.7 % / 479 px |
| 1s sky side x .655-.74 (right of rotunda): dark / sky | 5.8 / 64.3 % | 1.6 / 97.3 % | 0.9 / 98.6 % |
| 2 willow x .39-.47 y .45-.62: dark / leaf | 8.9 / 7.1 % | 53.7 / 3.1 % | 28.4 / 10.9 % |
| 3 N wing bays (env_preview skytest box): sky | 11.4 % | 32.5 % | 33.3 % |
- Before previews committed: renders/previews/environment/p10_before_cam{01,02,05}.png (Eevee 1920x1080, LOD1 render).
- Finding: the A cluster stands 141-145 m down the axis; ref's crown-top row (y 0.369) needs z ~36 m there, past every
  species window, so leaf cards / crown scale alone cannot do item 1 -> two new instances of the existing
  cypress_column prototype (env_trees.P10_ADD, appended after the hall belt so NO existing tree's RNG/seed/position
  changes). Placement solved by `scripts/env_p10_plan.py --search` (gates: dry, gallery, podium ring with the width
  factor, 3.5 m trunk spacing, cam01 span 0.658-0.765, cam05 QA-03-13 box). Predicted cam01 spans 0.660-0.710 (top
  372 px) and 0.697-0.758 (top ~400 px at 19 m).  The back column was 20 m -> 19 m: at 20 m it shaded the north wing
  band 21.2 -> 22.5 % (> SHADOW_TARGET 22 %); at 19 m the shadow cost is 0 on all four targets (build log line).
- Other changes (env_trees.py): cypress leafScale .50 -> .62, cypress_column .50 -> .60, pine .48 -> .60 (0 tris);
  willow branches L2 30 -> 40, leaves 180 -> 300, leafScale .45 -> .52, leafScaleX .18 -> .22, CROWN_XY willow 1.30.
- `env_r9_replan.py --verify` passes (0 failures, now also checks P10_ADD); `env_p10_plan.py --check` passes.
- Tri delta (env_build rule): LOD0 15,444,910 -> 16,440,294 (+6.4 %), LOD1 5,298,928 -> 5,741,062 (+8.3 %),
  LOD2 833,874 -> 849,706 (+1.9 %: willow LOD2 skeleton gained branches + 2 new trees). Budget +15 % holds.

In progress (items 1-3 "after" numbers, the sheet, the Cycles hero). Resume exactly:
1. `pgrep -fl "MacOS/Blender"`; then `scripts/lead_build.sh > renders/logs/p10env_build_after.log 2>&1` (~40 s).
2. `scripts/blender_run.sh 900 -- --background --python scripts/env_p10_preview.py -- --tag after --cams 01 02 05`
3. `/opt/homebrew/bin/python3.13 scripts/env_p10_boxes.py before=renders/previews/environment/p10_before_cam01.png after=renders/previews/environment/p10_after_cam01.png`
   Acceptance: box 1 dark and sky within 5 points of ref, crown-top within 12 px (398); box 2 within 8 points.
   If box 1s sky is still high, the next lever is P10 front column 19 -> 20 m (shadow cost 0, checked) or width.
   Box 2 dark is dominated by our dark rotunda-base shadow, not foliage; willow leaf colour is a MATERIALS hand-off.
4. Cycles hero 1920x1080 32 spp (<= 900 s) from master for the sheet; sheet renders/qa_comparisons/env_p10_sheet.png
   (cam01 100 % crops before / after / ref, cam02 + cam05 full at 960). cam02: the new columns appear at x 0.04-0.36.
5. Final report < 20 lines into this file + the reply.
Never use /usr/bin/python3 (Xcode stub); /opt/homebrew/bin/python3.13 has numpy + PIL.
