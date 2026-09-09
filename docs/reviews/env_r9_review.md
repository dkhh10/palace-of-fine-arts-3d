# env round 9 code review (head e0b383f, vs main) — 2026-09-09

**MERGE WITH FIXES**

Verified: `env_lib.gallery_clear` derives centre/radius/3.10 m structure from `arch_params` (never copied) and is enforced in
`land_ok`, `put`, `build_lamp_posts`, `redwood_screen`, `env_trees._land` and the final plan gate; walk probe 102 samples over both
wings, eye band z −1.10…+1.90, BEFORE 0.26/0.03 m FAIL -> AFTER 4.21/1.71 m PASS, both logs committed; `shadow_relief` `moved 0`
with 4 "NOT moved" reports and 1 podium refusal (env_r9f_build.log:117-131); the five A conifers reproduce
`env_r8_fit.solve(x, +13)` to 0.1 m and the six podium coordinates reproduce `env_r9_podium.log` exactly (solve is deterministic —
fixed 4000-step arc scan, no RNG); LOD1 4,705,602; frame-band clearer moved 0 / shortened 3 / dropped 0; hand-placed pins on all
three bands (`pin=PIN_HAND_PLACED`); only environment-owned files touched; no new tracked binary (environment.blend 188.3 -> 188.1 MB,
existing deliverable); new scripts use `common.ROOT`, no absolute paths; r7 carries 5/7/10 and r8 carries 2/4/5/6/7 done.

1. **fix now — env_trees.py:1116-1130: the "onto land" spiral snap runs AFTER the gallery gate and the podium ring** and moves 6
   hand-placed trees up to 5.6 m (env_r9f_build.log:141-148), so "PLAN now holds the shipped coordinate" is still not true: the A2
   column ships at (−38.7, −20.8) against PLAN (−37.9, −19.0) — the same coordinate the r8 review flagged — and the A redwood ships
   at (−35.0, 0.1), r 35.0 with a 3.5 m crown = 31.5 m, i.e. inside the very 37 m podium ring its bake was for. Pre-existing, but it
   disproves the round's headline claim. *Fix:* run the land snap before the podium/gallery gates, or re-check both after it.
2. **fix now — env_trees.py:770 `changed["moved_pinned"] += 0 if movable else 1` sits inside `elif movable and ...`**, so
   "hand-placed 0" in the log is a tautology and proves nothing; what actually proves the claim is `moved 0` overall. Delete the
   counter or increment it in the refusal branch.
3. **fix now (notes) — 137 -> 131 is not "3 dropped by the relief"** (the relief dropped 3 in r8 too). The six are generated E-group
   screen redwoods `redwood_screen` now refuses: screen crowns 57 -> 51 (env_r8h_build.log:118 vs env_r9f_build.log:116), plan into
   relief 140 -> 134. No PLAN tree was dropped and the gallery gate dropped 0. Say so.
4. **fix now (comment) — env_r8_fit.py:26 calls MASS_X 0.62-0.735 "dark fraction >= 0.35"**; the committed profile reads
   0.33 / 0.19 / 0.25 / 0.28 / 0.23 over 0.64-0.68 (env_r9_ref_profile.log). The notes state it honestly ("a thin stretch in the
   middle"); the code comment does not.
5. **fix now — the cam 06 gate's 0.637 is transcribed from docs/lighting_notes.md:2010, not computed by `--c06ratio`.** The only
   committed run is env's own r7 pair (`r7_numbers.json` c06_ratio 0.536), and `c06_ratio_note` hard-codes "LIGHT r13 ships 0.637"
   whatever it measures — the stale-constant trap the round was meant to close. Both frames are committed
   (`renders/previews/lighting/r13ship_base_06e.png` and `r13g_nocomp_06e.png`) and the tool needs no Blender: run it, commit the log,
   and make the note quote the measured pair. Definition itself (crop, Rec.709 on 8-bit sRGB, population std, comp/uncomp ratio,
   PNG not JPEG) is complete and matches the code.
6. **carry — three of the five re-solved A comments still quote pre-move spans.** PLAN pine (−37.2, −43.1) says 0.638-0.705 where
   `env_r9_podium.log` measures 0.642-0.702; cypress (−44.5, −41.4) 0.665-0.743 vs 0.668-0.740; pine (−40.0, −42.5) 0.652-0.716 vs
   0.653-0.715 (slots 3 and 4 match). The section header claims the spans below are the re-measured ones.
7. **carry — PLAN is a literal snapshot of `solve()` with nothing asserting it.** A change to `COL_ARC_CENTER`/`COL_ARC_R`, the cam-01
   station or the lens silently makes all 11 baked coordinates stale; only the gallery gate and the walk probe would notice, never the
   frame x. Add a `--verify` mode (recompute and diff) to `env_r9_replan.py`.
8. **carry — the 21.2 / 21.2 % wing-shadow figure is a probe on the wrong geometry.** `env_lib.wing_samples` samples the OSM roof
   polygons about `env_lib.ARC_CENTRE = (0, 52)`, not `arch_params.COL_ARC_CENTER` (−11.2, 84.7) / R 117.4 — the exact mismatch item 1
   fixed for planting. It is also ~80 samples per wing, so one sample is ~1.2 points and the 0.8-point margin under QA-02-7's 22 % cap
   is smaller than the quantum. QA must confirm on a render before the cap is called met.
9. **carry — env_r9_walk.py:127 exits non-zero on the ORIGIN statistic only.** The eye-band extent (1.71 m south, 0.31 m of margin over
   the 1.40 m half clear width) is printed but never gated; a joined run (rip-rap, verges) whose origin is far away could pass. Gate both.
10. **carry — "the belt reshapes, it does not thin" is not what the log says:** shrub instances 1414 -> 1378, −36 (r8h:19 vs r9f:17).
11. **carry — the podium bake is exactly on the boundary** (P broadleaf reaches r 37.0 against the 37 m ring, so a refusal fires every
    build) and it moved the C broadleaf 14.5 m, cam01 x 0.358 -> 0.258, away from the user-image feature its comment cites. Add a 0.1 m
    epsilon, and re-check that C comment against the composition. Also: the BEFORE probe ran on an uncommitted scratchpad blend
    (`env_r8_merged.blend`), so the BEFORE row of the table is not reproducible from the repo.
