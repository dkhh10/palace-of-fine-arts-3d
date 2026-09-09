# Code review — branch `lighting`, round 14 prep (head 4fa11be) vs main
MERGE WITH FIXES — the route, the profile and the ray-cast gate are sound and reproducible; four small fixes (1-4) and one hand-off to the lead (6).

1. **fix now** `scripts/light_flythrough.py:73,85,113` — the cam01/cam02/cam04 stations are hand-copied literals
   ((-14.10,100.00), (70.50,25.60), (0.00,3.00)); the script never imports `qa_cameras`. They match `CAMERAS` today, but
   §23.1.2 is a record of exactly this desyncing once already. Fix: `import qa_cameras`, look the three loc[:2] up by name.
2. **fix now** `light_flythrough.py:295` and `:398` use `st[4]` (the arc theta) where the note is `st[5]`, so every
   `cam["schedule"]["stations"][i]["note"]` and every station line in the build log reads `None`. One-character fix.
3. **fix now** `light_flythrough.py:44` says the check "gates that leg at 1.30 m"; the code (`CLEAR_MIN_GALLERY`) and
   notes §23.3 say 1.35. Stale comment.
4. **fix now (doc)** notes §23.3 headlines "min 1.70 m outside the gallery" — that is the step-12 run. The step-4 rerun
   (`renders/logs/light_r14_check_step4.log:316`) measured **1.57 m** outside the gallery, i.e. 0.07 m of margin, and it
   ran with the older 1.25 gallery gate, so the committed 1.35 script has never been run at step 4. Quote the step-4
   minima in the gate table (they still pass) and re-run `--step 4` once with the shipped gates.
5. **carry** `light_flythrough_check.link_site` sets `set_lod(viewport=1, render=0)` and casts against the viewport
   depsgraph, so every clearance number is measured on **LOD1** (all hit names end `_LOD1`) while the animation renders
   LOD0. Column flutes only add margin, but ENV foliage LOD0 is fatter than LOD1 — re-run the check with `viewport=0`
   before the final flythrough render.
6. **fix now — lead's file** `scripts/build_master.py` sets no `frame_start/frame_end/fps`, and linking/appending the
   LIGHT collection does not carry lighting.blend's scene frame range: master.blend opens at **1-250**, so a Render
   Animation there yields 250 of the 1224 frames. tech_notes documents the manual set; two lines in build_master
   (`sch = light_flythrough.load_schedule()`) is better. Master's scene camera is `CAM_qa_01_lagoon_hero`
   (`qa_cameras.ensure` → `cams[0]`), not CAM_flythrough — correct, no action.
7. **carry** The brief's north grove (120-135 m, environment r8) is not on the shipped route and §23 does not say why
   it was dropped. Lead call; state it in the notes either way.
8. **carry** `light_flythrough_check.py:41` gates "over water" on the literal name `ENV_lagoon_water`; if ENV renames or
   LOD-suffixes the water surface the gate passes **vacuously** (0 samples) instead of failing. Assert `len(zw) > 0`.
9. **carry** `light_flythrough_check.columns()` hardcodes `cx, cy = -11.2, 84.7` instead of `arch_params.COL_ARC_CENTER`
   (probe-only tool, but it is the constant the whole gallery leg is built on).
10. **carry** The dome "hold" is stationary in position only — `TARGET_KEYS` moves the target (0,2,26) → (0,4.5,45)
    across the hold window and the holds gate measures translation only. Deliberate and good; say so in §23.3.

**Verified as claimed.** Idempotency: `_clear_old()` removes the same three object names the round-02 script created,
plus `CAM_flythrough*` actions and orphaned curve/camera data — no duplicates, no round-02 leftovers; and
`light_build.build()` calls `fly.build(scene)` last, so a rig rebuild cannot drop them. Arc geometry, `COL_ARC_R/
_ROW_SPACING/COLONNADE_GROUND_Z` come from `arch_params`; the check's `WATER_MIN_Z` from `common.WATER_Z`.
Frame range set in lighting.blend (`build()`), 1224 frames @ 24 fps, `offset_factor` keyed at every frame and forced
LINEAR through `_all_fcurves` (5.2 slotted-action safe). Gates 1.50 / 1.35 / agl 1.50 / -0.80 / 6.0 / 10.0 / 3.0 s and
the numbers 1.70 / 1.42 / 5.60 / 9.20 / 3.50 / 4.17 all appear in the committed `light_r14_check_final.log:113-119`
plus `light_flythrough_check.json` (103 rows, ARCH+ENV linked, 96-dir Fibonacci, ENV shrubs are hit). r13 carries
2, 5, 6, 7, 10, 11 are each present and do what the notes say; 8 correctly deferred (needs the GPU). No render path is
reachable by default (`render_test` is never called from `__main__`); no absolute paths; nothing outside lighting's
ownership (docs/tech_notes.md is allowed); largest new tracked binary is assets/lighting.blend at 0.9 MB. Every
tech_notes number traces to qa_round_04/05 or lighting_notes.
Nits: `light_r13_sheet.py` adds `import pathlib, tempfile` beside an existing `from pathlib import Path`;
`light_calibrate` prints the unrounded dict but writes the rounded one; `vmax_land` rebuilds `set(wat)` per frame.
