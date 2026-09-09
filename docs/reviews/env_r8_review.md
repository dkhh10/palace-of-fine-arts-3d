# env round 8 code review (head fa04322, vs main f426672) — 2026-09-09

**MERGE WITH FIXES**

Verified as claimed: frame-band clearer `moved 0, shortened 3, dropped 0, kept 12` (env_r8h_build.log:120); north band
38.5 % foliage / 50.3 arch / 11.2 sky (env_r8f_band.log, env_r8_coverage_final.log); band lum 91.9 -> 133.1, south 83.4,
shore 79.7, cam03 26.7, cam06 106.6/0 lines, cam05 4.8/59.6 all machine-written into r7_numbers.json by env_r7_measure.py;
`SCREEN_OVER` 0.022 -> 0.000; the five A conifers' quoted frame x (0.640-0.758) reproduce exactly from the closed-form
projection with cam 01's real station, at 123-129 m along the view axis; render chain ran *after* the height revert
(pids 14217 build h -> 14322 master -> 14357 hero -> 14794/14809 cams), so the shipped numbers are the reverted state;
98561e1 leaves no trace in env_trees.py (only heights 28/30/24/28 -> 21/26/22/21 and the comment, both reverted);
PLAN positions are literal data; env_build rebuilds ENV via `rebuild_collection`; no other owner's file touched; no new
tracked intermediate > 5 MB (sheet 3.3 MB; environment.blend is the deliverable, already tracked in main).

1. **scripts/env_trees.py:293 / docs/environment_notes.md:1346 — "the dark mass runs frame x 0.61-0.735" cannot come from
   the tool cited.** `env_r8_fit.ref_profile` buckets only `range(68, 100)` (env_r8_fit.py:42); the committed log
   (env_r8_ref_profile.log) starts at 0.68 (0.23 dark) and first crosses the stated 0.35 threshold at 0.69. The left bound
   0.61 — and the "left edge 0.64/0.64/0.61" row in r8_numbers.json — is unmeasured, and env_r8_fit.py's own docstring says
   the mass is at 0.705-0.745. The whole cluster was solved 0.07 of frame left of the brief's 0.71-0.76 target on that bound.
   *Severity: fix now.* Widen the loop to `range(55, 100)`, rerun `--ref`, commit the log; if 0.61-0.67 is not >= 0.35, shift
   the five conifers right and re-measure the band. **Lead decision:** the brief said land the mass at 0.71-0.76; it landed
   at 0.640-0.758 by the owner's own re-measurement. Acceptance should be granted explicitly, not implicitly.
2. **scripts/env_trees.py:524 — `COLONNADE_TOP_Z` silently rose 16.0 -> 16.4 m** (AP.COLONNADE_ABACUS 14.0 +
   ENTABLATURE_H 2.4). The notes present this as "now read from arch_params instead of being copied", i.e. as a no-op, but
   it raises the screen cap 0.4 m in the same build that drops `SCREEN_OVER` 0.022 -> 0 (~3.3 m at the wing), so the net cap
   change is ~-2.9 m, not -3.3, and "screen tops exactly on the cornice line" is 0.4 m optimistic. *Fix now (notes only):*
   state the 16.0 -> 16.4 correction as a second change; the direction is right and the measured band already includes it.
3. **scripts/env_trees.py:311 and :341 — two hand-placed comments are stale for the shipped build.** `shadow_relief`
   (which runs before the pinned clearer and still moves hand-placed trees: "moved 16, dropped 3") relocates the A cypress
   from PLAN (-42, -30) to (-47.7, -40.5) — actual frame x ~0.719, not the commented 0.668-0.740 — and the A2 column from
   (-36, -18) to (-38.7, -20.8) (env_r8f_band.log, env_r8h_build.log:141). *Carry:* note in the PLAN comments that
   shadow_relief may still move a pinned tree, or print the post-relief frame x for the solved entries.
4. **scripts/env_r8_fit.py:149,154 — `solve()` hard-codes cam 01's station and lens** (`lx, ly = -14.1, 100.0`, `36/20`)
   instead of reading `qa_cameras.CAMERAS` the way `band_cast` does. They match today; this is exactly the drift the round-7
   review flagged for the colonnade constants. *Fix now (2 lines):* pull the spec from `qa_cameras`.
5. **scripts/env_r8_fit.py:48 — the y-extent window is hard-coded 0.705-0.745**, i.e. measured over columns the report now
   calls the mass's right half. *Carry:* make it a parameter and rerun with the corrected mass columns from finding 1.
   Also `solve(..., y_hint=-15.0)` (line 135) is an unused parameter — drop it.
6. **scripts/env_trees.py:306 vs docs/environment_notes.md (carry table) — cam03 std for the reverted experiment is quoted
   as 26.0 -> 21.4 in the code and 26.7 -> 21.4 in the notes.** *Carry:* one of the two; the measured r8 value is 26.7.
7. **A-group share of the box is ~8.5 %, not the "~11 %" claimed** (env_r8f_band.log: 5.61 + 1.39 + 0.91 + 0.54 + 0.05 +
   0.01); with the P bed it is 14.3 %. Two of the five re-solved conifers contribute 0 % (occluded by the wing) and the box's
   left columns are held mostly by the near P broadleaf at (-30, 30), frame x 0.711. *Carry:* the grove is doing less of the
   work than the report implies — relevant if the lead pursues the 0.025-of-frame height item in round 9.
