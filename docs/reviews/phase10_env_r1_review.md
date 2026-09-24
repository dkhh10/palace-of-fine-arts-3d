# phase10-env r1 (c1b5e43) — MERGE WITH FIXES

Read-only review of `git diff main...phase10-env` (8 commits, merges clean into main). I re-checked the report's numbers
where I could do it without Blender. `env_p10_boxes.py` re-run on the committed previews reproduces **every** Eevee and
Cycles-after number in the report table exactly (box 1 20.4/57.7/474 -> 30.2/45.3/422 -> 31.8/43.4/407; Cycles after2
23.6/45.8/411; box 2 53.7 -> 63.2; box 3 32.5 -> 27.7). It also reproduces the Cycles "before" (15.4/58.7/479) against
MAIN's `cycles_p9/cam01_1080_32spp.png`.
The ref-169 registration is the same transform as `env_r8_fit.REF_XF` (0.7640, 223.2, 0.7667, 97.0, raw = cam px * s + d,
applied as an EXTENT resample). Two things to fix there: it is a copied constant, not an import, and `MAIN` is hard-coded (carry 8).
The belt manifest diff is **scale only**: 26 of 39 rows, no location/rotation/seed/prototype change, and the ratio is uniform per
prototype (cypress 0.994-0.995, column 0.995-0.996, pine 0.994). That matches the report's explanation: bigger cards raise
`gen_height`, and `scale = h / gen_height`. P10_ADD is appended after `hall_belt`, so `seed = seeds[i % n]`, the six `rnd` draws
of trees 0..N-1 and the `per_species_idx` names are unchanged. `CROWN_XY`/`widen` multiply after the draws. `env_build` rebuilds
the `ENV` collection (`rebuild_collection`), and the three hard gates are re-asserted in `build_all`. Every Blender launch in the
docstrings and logs goes through `blender_run.sh`. Scope is clean: no materials, lighting, ARCH, export/, web/ or master change.
The two extra files are the auto-written `docs/phase8d_belt_r2_trees.json` (ENV-generated) and 4 tracked logs.
The brief's acceptance is **not met**: box 1 sky is +8.6..11 points off, box 1 dark is +8.4 points off (Cycles) and box 2 fails.
The report says so honestly, and the remaining excess is plausibly the foliage colour hand-off.

1. **fix now**: the final-state evidence is not committed. The 20 m front-column build (`p10env_env_build3.log`), `p10env_verify3.log`
   (0 failures), `p10env_check3.log`, `p10env_cycles_after2.log`, `p10env_preview_after{,2}.log` and `p10env_build_after{,2}.log`
   are untracked in the worktree. The committed build logs are the 19/20 m state from before the change, so the report's "--verify 0 failures,
   shadow cost 0 at 20 m" cannot be traced. Commit the 8 logs.
2. **fix now**: the rotunda span rule is checked on the *prediction*, not the placed tree. `env_p10_plan.cam01` uses
   `P10_REAL_R * w * h` at the nominal width. The placed instance also gets `sx = scale * rnd.uniform(0.82, 1.16)`
   (`env_trees.py:1414`), so the front column's left edge, predicted at 0.659 against the rotunda's right edge at 0.655
   (a 7 px margin), can land at up to ~0.655 with the widest draw. That is on the edge. `env_p10_census.py` exists for exactly
   this and was not run after the build. Run it (CPU, no render) on the after `environment.blend` and put the measured bbox span
   of the two P10 columns in the report.
3. **fix now (lead decision)**: item 2 moved the box **away** from ref in both renderers. Dark went 53.7 -> 63.2 (Eevee) and
   28.4 -> 44.6 (Cycles) against ref 8.9, and the Cycles leaf share fell from 10.9 to 8.8. The report says the box holds only
   "our shadowed rotunda base, the willow is not at ref's x .39-.47". That contradicts PLAN (the hero-shore willows
   ship x 0.340-0.417 and 0.423-0.500, crown tops at y ~0.49, inside the box) and the report's own willow-box leaf colour, luma 48.
   The dark rise came from the willow densify. The cost is willow prototype LOD0 82-85k -> 149-150k tris (+74-83 %) and LOD1
   44-45k -> 74-75k (+64-71 %). Either keep it on a willow-only mask measurement that shows it helps, or revert `branches`/`leaves`
   and keep only `CROWN_XY`.
4. **carry**: `CROWN_XY["willow"] = 1.30` widens all 10 willows, but no gate sees it. `env_r9_replan --verify`/`--shipped`/`span()`
   and `L.shadowed_fraction` still use `CROWN_R`, and the shadow-relief line is byte-identical before and after (hero shore 18.0 %).
   Recomputed ring margins with 0.49 x 1.3: min 37.3 m ((-40,16) and (6.9,43.4)), so the ring still holds at the nominal draw.
   The hero-shore spans widen about 30 % and now overlap each other (0.328-0.429 / 0.411-0.512). Read `CROWN_XY` in the replan
   ring/span and in the shadow samples.
5. **carry (export)**: the LOD2 +1.9 % (833,874 -> 849,706) is a consequence of the shared Sapling generation. LOD2 is the same
   tree's leafless skeleton, and willow L2 `branches` 30 -> 40 grows it (3,284/3,812 -> 4,436/4,564 per prototype) on top of
   2 x ~2k for the new columns. It was avoidable only by leaving `branches` alone. Tier impact: far trees ship a 2-triangle
   billboard, so LOD2 tris cost nothing on the web. What does cost is that the cypress/pine/willow LOD1 prototypes changed
   (cards +20-24 %, willow new geometry), so the baked impostor atlases and the `EXPM_*_LOD1_thin` rows of
   `docs/briefs/phase6_budget.md` are stale. Willow s37 thin goes 24,272 -> ~40k. The next export needs an impostor rebake and a budget update.
6. **carry**: the Cycles pair is not controlled. "Before" is MAIN's `cycles_p9` (untracked, rendered 09-21 06:54, before the
   8d R3 backdrop-material commits); "after2" is the worktree master. Cycles deltas include non-ENV changes, so rely on the
   Eevee before/after pair.
7. **note**: cam02. There is no `FRAME_BANDS` entry or plan rule for `_qa_02_`, so the columns covering the rotunda's left base at
   x 0.04-0.36 break no rule. It is still an unguarded composition change on a QA station, and QA should score it against
   `canonical/cam_02`. cam05's QA-03-13 box is respected with margin: `_frame_box` uses CROWN_R 0.20 x 1.3 = 0.26, while
   the widened real crowns are 0.154/0.198 (0.23 with the widest draw).
8. **note**: the shadow of the P10 columns (sun az 118.5, el 7.4) passes 38.8 m from the rotunda axis, and the report's 0 cost on
   the 4 targets is consistent with that. The ring re-check in `build_all` hard-codes `37.0` instead of `PODIUM_R + CLEAR`.
9. **note**: small tidy-ups. The `env_p10_preview.py` docstring says `p9r3_<tag>_cam<NN>.png` but the script writes `p10_`.
   The report still carries the stale checkpoint (19 m front column, "master NOT yet rebuilt"); trim it. `environment.blend` is
   +14 MB (195 -> 209 MB).
