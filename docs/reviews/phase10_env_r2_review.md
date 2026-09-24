# phase10-env2 r2 (bda6ec5) — MERGE WITH FIXES

Read-only review of `git diff main...phase10-env2`, 10 commits, 58ee374 .. **bda6ec5**. That includes the lead-requested extra commit
(the second hero-shore willow (-2.6,45.9) 8.5 -> 4.0 m). The branch merges clean into main (`git merge-tree`).
Scope is clean. Outside `renders/logs/p10r2_*`, `renders/previews/environment/p10r2_*` and `scripts/env_*`, the only changed files are
`assets/environment.blend`, `docs/briefs/phase10_env_r2_report.md`, the `docs/environment_notes.md` PLAN table and
`renders/qa_comparisons/env_p10r2_sheet.png`. There is no materials, lighting, ARCH, export/, web/ or master change. All 23 committed
logs end in a `blender_run.sh: pid ... exited rc=0` line, and both new Blender scripts document the `blender_run.sh` launch.

**Reproduced without Blender.** `env_p10r2_willowbox.py` on the committed masks gives exactly the report's numbers:
ref 21.7 / 21.8 % top 604 (apex 601); before 17.3 / 19.7 % top 548; after3 17.7 / 19.4 % top 607 (apex 601).
The committed `p10r2_ref169_willow_mask.png` reproduces the `REF_WILLOW` polygon (identical row). The box is
`int(.39*1920)..int(.47*1920)` x rows 486-669, which matches the brief. The silhouette counts (target 0 hero-arch / 0 drum /
367 side-arch; P10R2_ADD 0 / 0 / 2,543; ref polygon 397 side-arch) come from the SAME holdout alpha PNGs as the box numbers:
`p10r2_mask_after3.log` renders each mask once and `classify()` reads that array. The placed transforms in the JSON confirm the
settings: target `ENV_tree_willow_03` h 5.4, scale (0.927, 1.237, 0.472); ADD `willow_10` h 9.
**Plan invariants hold.** The placement loop makes six unconditional `rnd` draws per tree. `seed = seeds[i % n]` and
`per_species_idx` depend only on the index. P10R2_ADD is appended after P10_ADD, so no other tree's seed, draw or name moves.
`docs/phase8d_belt_r2_trees.json` was rewritten by build3 and build4 and is byte-identical to main. The build3 log differs from
round 1 in only these places: the moved willow, relief iterations 77 -> 79 (the same 27 crowns and 103 m lowered, dropped 3), the
frame-band `kept` count 12 -> 11, the hero-shore shadow and the +1 willow. The widening multiplies after the draws, keyed only to the
one PLAN note. No solver clamps a height below the "8-12 m window". The window is a comment, not code (PLAN already has 7 m
willows). Shadow relief lowers only when `h > max(frac*h0, 8)+0.5`, frame-band only when `h > max(6, .75h)`, and neither raises a
height. The log shows `h 5.4 (plan h5)` and `h 4.0 (plan h4)` placed as planned.
**Tris (build log).** 16,440,294 / 5,741,062 / 849,706 -> 16,590,536 / 5,815,986 / 854,142 (+0.91 / +1.30 / +0.52 %). The deltas
(150,242 / 74,924 / 4,436) are exactly one willow seed-11 prototype, i.e. P10R2_ADD. The move and bda6ec5 cost 0 (build4 = build3).
**Acceptance** is met on the numbers: own share -4.0 points (limit 10), crown top +3 px (limit 20), 0 px on the hero arch and the drum.
Note that the round-1 tree already passed the share clause (17.3 vs 21.7). The crown-top row is the metric that actually moved.

1. **fix now**: bda6ec5 is not measured. Its note and PLAN table claim "central arch opening 2,065 -> 0 px", but there is no master
   rebuild, mask/classify run, preview or report update after it. The sheet, Eevee/Cycles previews and report all show the 8.5 m (relief
   7 m) tree. The 0 px comes from a geometric estimate: the crown top must stay under z ~3.4 m. At 4.0 m on ground -0.95, the tallest
   `sz` draw (1.08) reaches z 3.37, so the margin is 3 cm. Rebuild master, run `env_p10r2_mask.py` (target/other), and put the measured
   hero-arch / drum px and the other willow's box share in the report. Refresh the cam01 Eevee crop on the sheet, and set the report's
   last-commit id.
2. **fix now**: the podium ring is again gated on the nominal draw, not the placed crown (round-1 fix-now 2, recurring). `--verify`
   and `env_p10r2_plan --check` ring the target at `0.49 x 1.3 x 1.7 x 5.4 = 5.85 m` -> 37.8 m. The placed scale (0.927, 1.237) on the
   seed-11 prototype (r 5.6 m at gen_h 10.9) gives local semi-axes 5.19 / 6.93 m. Along the long axis that is |trunk| 43.62 - 6.93 =
   **36.7 m < 37**, depending on `rot`. The x2.21 widening amplifies the 0.82-1.16 draw to about +/-0.9 m. Run `env_p10_census.py`
   (CPU) on the built blend, report the measured world-bbox ring distance of `willow_03` and `willow_10`, and fix or log a decision if
   it is below 37.
3. **carry (round-1 carry 4, sharper now)**: `shadow_relief`, `p10_shadow_report` (`L.shadowed_fraction`) and `_frame_box` still use
   `CROWN_R` (willow 0.45, x CROWN_SAFETY). The target's real crown is 0.49 x 1.3 x 1.7 = **1.08 R/H**, 2.4x the radius (about 5.8x
   the area) the gates see. The consequences:
   (a) the hero-shore line is a lower bound. At 9e43109 it read 24.0 -> 26.0 % against SHORE_TARGET 25 %, over target and not flagged
   by the report. bda6ec5 brings it to 22.0 -> 24.0 %, but with the real radius it is likely above 25 %.
   (b) the frame-band list dropping the moved willow ("kept 12 -> 11") and the cam02/cam05 boxes in `env_p10r2_plan` (cam05 x
   0.54-0.63) are underestimates.
   (c) nothing moves because of it: P trees are pinned and the relief only lowers generated trees, so the risk is unguarded
   composition and shadow, not placement drift. Read `CROWN_XY x P10R2_WIDEN` in all three.
4. **carry**: `P10R2_WIDEN` is keyed by the full note string, duplicated as a literal. If the note is edited (bda6ec5 edited the
   neighbouring note), the widening silently disappears, and `env_p10r2_plan --check` silently skips the entry (`note in P10R2_WIDEN`)
   while still printing "0 failing". Assert that every key matches exactly one PLAN note, or move the factor into a 6th tuple field.
5. **note**: the ref-169 registration is reused through `env_p10_boxes.ref_frame` (sheet) and the hand trace. The copied `REF_XF`
   constant and the hard-coded `MAIN` path from round-1 carry 8 remain. `env_p10r2_willowbox.py` names `env_r8_fit.REF_XF` in its
   docstring but does not use it: its polygon is already in cam-01 px, so the metric is registration-free once traced.
6. **note**: P10R2_ADD and the target are both seed 11 (same Sapling prototype), 3.6 m apart at hero distance. Scales differ
   (z 0.47 vs 0.79, XY x2.2 vs x1.3), so the repeat is unlikely to read. QA should look for it in the tiles.
7. **note (QA/lead)**: the sheet shows the willow box still reading as dark hedge in Eevee and Cycles, where ref 169 has a pale,
   fine weeping curtain. The metric is colour-independent by design, and colour is the open materials hand-off. The 4.0 m right-of-stair
   willow is now a low curtain. QA should score both hero-shore crowns against `canonical/cam_01`, not just the box metric.
