# Phase 10 ENV round 2: report (2026-09-24)

Files: scripts/env_trees.py (PLAN line, P10R2_WIDEN, P10R2_ADD), env_r9_replan.py (--verify now rings the widened crowns), new scripts/env_p10r2_{mask,willowbox,plan,sheet}.py, env_p10_preview.py (--prefix), assets/environment.blend.
**Item 1, method.** Ours: Cycles cam01 1920x1080 at LOD0. The tree is the only non-holdout object and the film is transparent, so own pixels are alpha > 0.5. No colour is used. Ref 169: the weeping willow is hand-traced as a polygon on a 4.5x gridded zoom of the registered frame (REF_WILLOW). The pale tree behind it on the left is excluded. Crown-top row: over the box columns that hold the tree, the median of the first row that starts a run of 3 pixels.
**The finding contradicts the brief's premise.** Ref's willow does not reach the impost. It is a low, broad crown: x 691-850 px, crown top at row 604 (y 0.559) with its apex at row 601, and its drape reaches the water at row 703. The round-1 tree was not near 0 in the box: it filled 17.3 % of the box, and its crown top at row 548 was 56 px too high. It stood in the slot of the pale tree (ref x ~633-777, top row ~535).
| willow box x .39-.47 y .45-.62 | own % | envelope % | crown-top row (apex) | x span px |
|---|---|---|---|---|
| ref 169 willow (polygon) | 21.7 | 21.8 | 604 (601) | 691-850 |
| before: (6.9,43.4) h9 | 17.3 | 19.7 | 548 (539) | 646-800 |
| after: (4.4,43.4) h5.4 w1.7 | 17.7 | 19.4 | 607 (601) | 689-836 |
Acceptance: own share is 4.0 points below ref (limit 10). Crown top is 3 px below ref (limit 20).
**Item 2, plan change.** `("willow", 6.9, 43.4, 9.0, "P hero-shore willow, ref 169 x 0.33-0.42; ...")` -> `("willow", 4.4, 43.4, 5.4, "P hero-shore willow, ref 169 x 0.36-0.44; p10r2 ...")`, plus `P10R2_WIDEN` 1.7 in X/Y for this instance only.
- **Height window.** For this one instance it is lowered, not raised. The species keeps 8-12 m; this instance is 5.4 m because ref's crown top is 5.1 m above the tree's ground at d 58.6 m. The trunk moved 2.5 m north, so its frame x is 0.401, the ref willow's centre.
- **Width.** At 1.4 the crown rendered 126 px wide against ref's 159, so the factor went to 1.7.
- **Added, not in the brief: `P10R2_ADD`.** One more instance of the existing willow prototype at (7.9,42.6), 9 m, appended after P10_ADD, so no existing seed, RNG draw or position changes. Without it, moving the willow left the podium and stair bare at x 0.33-0.37, where ref has the pale crown. The added crown renders x 624-794 with its top at row 539, against ref's pale crown at ~633-777 and ~535. It is a separate commit (b1f7c49); drop it if unwanted.
**Item 3, silhouette.** Rays are cast through the arch_params octagon: the aperture on the lagoon face, then the first ARCH_rotunda hit more than 2.5 m behind the wall plane.
- Moved willow: 0 hero-arch pixels and 0 drum pixels. It covers 367 px of the left side-arch aperture. Ref's willow covers 397 px of the same aperture (rows 602-618), so this matches the photo.
- P10R2_ADD crown: 0 hero-arch pixels, 0 drum pixels, 2,543 side-arch pixels. That is about the same as the round-1 tree in the same slot (2,961).
**Gates.** `env_r9_replan --verify`: 0 failures (willow ring 37.8 m, added crown 37.6 m, both with the widened crown). `env_p10_plan --check`: 0 failing. `env_p10r2_plan --check`: 2 PASS (dry, gallery, ring, 3.5 m spacing). Land snap moved 0 trees. Shadow relief is unchanged (27 crowns lowered, 103 m). The frame-band list lost only the old willow. The hero-shore shadow went 18.0 -> 22.0 % from the move, and P10R2_ADD adds +2 (24 -> 26 % on the P10 line).
**Item 4, triangles.** Round-1 numbers -> now: LOD0 16,440,294 -> 16,590,536 (+0.9 %); LOD1 5,741,062 -> 5,815,986 (+1.3 %); LOD2 849,706 -> 854,142 (+0.5 %). All of the change is P10R2_ADD; the move itself costs 0 triangles.
**Open.**
- **The second hero-shore willow (-2.6,45.9)** was not moved (not in this brief). It covers 2,065 px of the hero arch aperture (rows 561-614, x 882-936, 712 px of them seen straight through). It also fills 23.5 % of the box, where ref shows only the urn and pedestal.
- **Leaf colour hand-off (materials, still open).** Both crowns read as dark hedge in Cycles.
- **Shadow gates.** `shadow_relief` and `_frame_box` still use CROWN_R, not the widened crown (review carry 4).
Sheet: renders/qa_comparisons/env_p10r2_sheet.png. Last commit: 9e43109 (report commit follows).
**Lead item, second hero-shore willow.** Plan line: `("willow", -2.6, 45.9, 8.5, "P hero-shore willow, ref 169 x 0.44-0.52 ...")` -> `("willow", -2.6, 45.9, 4.0, "... p10r2 8.5 -> 4.0 m ...")`. Only the height changed, not the position. The opening's sill (z 4.3 m on the lagoon face) projects to row ~614, so from this trunk the crown top has to stay under z ~3.4 m.
Alpha-holdout test: central arch opening 2,065 -> 0 px; drum 0 -> 0 px; own pixels 10,276 -> 3,324. Its share of the willow box went 23.5 -> 7.6 %, against 0 % in the photo, which shows only the urn and pedestal here; its crown-top row went 566 -> 622. The moved willow's box share rose 17.7 -> 19.1 % (ref 21.7) now that the second willow no longer hides it. `--verify` 0 failures; shadow relief kept its 4.0 m (floor); hero-shore shade 22 -> 18 %; tris unchanged.
Evidence: Eevee cam01 pair renders/previews/environment/p10r2_after_cam01.png (before) / p10r2_w2_cam01.png (after), masks p10r2_w2_mask_*.png, sheet row 3 in renders/qa_comparisons/env_p10r2_sheet.png.
