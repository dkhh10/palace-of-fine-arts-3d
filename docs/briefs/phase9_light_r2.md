# Phase 9 lighting, resumed with the corrected premise (brief from the lead, 2026-09-20). Opus 5 high. Fresh agent.
Branch `phase9-light`, worktree .claude/worktrees/phase9-light — resume at fe12cf5, do NOT start over. Read, in order: docs/briefs/process.md;
docs/briefs/phase9_light.md (the original brief: acceptance, holds, BEFORE frames, build, report format — ALL unchanged); the branch's
docs/lighting_notes.md section 29 (your predecessor's round so far, notes 29.0-29.1 and whatever follows); docs/briefs/phase9_bake_analysis_report.md
section A.0 (on main after the bake merge; until then `git show phase9-bake:docs/briefs/phase9_bake_analysis_report.md`).

## The corrected premise (replaces the "Why" paragraph's mechanism; the acceptance numbers stand)
`LIGHT_shade_fill` is 0 W in both engines since f40d0e7 and build_shade_fill builds no lamp; the Gate 3 scene audit lists no shade fill. The violet on the
NNE face is `SKY_DIFFUSE_TINT` (1.0, 0.65, 70.0) with its anti-sun / horizon / sun-side weights (light_build.py:125, light_calibrate.make_sky_world) — the
world's DIFFUSE branch only. The lever is therefore the diffuse sockets (tint, antisun_p, horizon_p, sunside, diffuse_boost) and nothing else:
**the camera and glossy branches stay untouched** (the tints are gated Fac = 1 − min(Is Camera Ray + Is Glossy Ray, 1)), so the re-bake chain skips the
camera and glossy equirects and the LUT. Do not re-arm the shade fill lamp and do not add a lamp: a lamp forces the full 7 h 24 m chain and reaches the
impostor nursery. Your predecessor's finding stands as a starting point: tint fully off moves the hero only ~4.2 deg hue while cam02 gains ~25 b* — the
round is now a sweep over the diffuse sockets that lands station 2 inside the acceptance while the hero / 03 / 04 holds are met at the noise floor.

## Method
Keep the world-patch shortcut (light_r19_sweep.py, notes 29.1, base MAE 0.0138 vs noise floor 2.91) for the sweep; the SHIPPED winner goes into
scripts/light_build.py constants with comments in the file's style, then ONE full chain (light_build -> lead_build.sh in your worktree -> phase5_deliver 1b
scratch copy -> p8_cycles_refs cam02 + cam01, then 03 + 04 once) to prove the shortcut's winner reproduces through the real build. GPU is yours: nobody else
renders while you do (the lead's marker is already there; check `pgrep -fl "MacOS/Blender"` is empty before each run; scripts/blender_run.sh, honest seconds).
The lead has no other GPU job queued until you report, but keep each run short (the Air throttles).

## Report (the original brief's format) into docs/briefs/phase9_light_report.md and the final message
Plus the two hand-off lines the bake engineer asked for: (1) class of change = diffuse sockets only (confirm no lamp, no camera/glossy socket moved, by
reading the sockets back from the rebuilt file as light_r19_sweep.py does); (2) the exact socket values shipped. The lead reports to the user before
the re-bake chain starts.
