# Phase 10 r1 projection — report (projection engineer, branch phase10-proj)

**Files:** `scripts/mat_p10_{sfm,align,edges,depth,common,meshdump,atlas,project,texture,integrate,render,sheet}.py`,
`scripts/mat_p10_step2.sh` (the step-2 recipe), `scripts/arch_uvbake.py`. Assets: `assets/architecture.blend` (UVBake only),
`assets/materials.blend`, `assets/textures/projection2/{cameras.json,uvbake_groups.json,PFA_p10_ratio.png,PFA_p10_mask.png}`.
Sheets: `renders/qa_comparisons/mat_p10_sheet.png`, `renders/qa_comparisons/mat_p10_registration.jpg`. Notes: `docs/materials_notes.md` "Phase 10 r1".

1. **Registration:** probe model reused, 71 images; hloc not tried.
2. **Alignment:** 7-DOF ICP with the lagoon-sector prior forced (15.32 m/unit, trimmed RMS 0.46 m). Review part 1 #1 is closed: the chamfer metric was flat (control ratio 1.05 at 10 px). It is replaced by a self-calibrating peak metric: the shift that maximises the photo gradient along the model's occluding contours, searched over ±40 px. On the similarity alone it reads 25.7 px (a systematic ~35 px x offset, about 0.9°). After two per-camera rotation fixes: median 0.71 px over 71 photos, 51 at or under 4 px. Controls: 10 → 10.5, 20 → 20.5, 40 → 40.0 px. This is a fit residual; the independent chamfer moved 6.09 → 5.29 px. Gates: 2 photos fail the physical gate (ref_086 z −2.9 m, ref_150 558 m), 20 have a residual over 6 px, and 13 needed a correction over 1.5°. **43 of 71 cameras used.** ref_169 itself is excluded (residual over 6 px). The global D and the chamfer refinement were dropped. The camera-height prior is a gauge choice, not a measurement: median camera z is 2.1 m.
3. **UVBake:** one 4096 atlas split into four 2048 quadrants. Hero-front density is 43 / 50 / 64 / 136 texels/m (attic / entablature / drum+columns / arch). The shipped texture has half that: 21 / 25 / 32 / 68 texels/m, projected at 1024 per quadrant. The photos resolve 16–40 px/m (lead decision (a)). Fill 41 / 29 / 44 / 13 %, 0 overlap texels, layer-order checks pass. The script now exits 1 on failure, creates `work/`, and writes per-mesh SHA-1 into `uvbake_groups.json` (37 meshes); a changed layout fails the run unless `--write-hashes` is passed. The re-saved layout is byte-identical to the one projected.
4. **Position and normal atlases:** exact numpy raster of UVBake, per instance (the 16 columns share one mesh).
5. **Depth:** one Blender run on the rebuilt master, 43 cameras, 85 s. Many registered stations stand inside ENV's east-shore backdrop houses or canopy (e.g. ref_070/071 at (−4.9, 184, 1.4) inside ENV_backdrop_house_148), so `ENV_backdrop*` and `ENV_terrain*` are hidden and the near clip is 12 m. **Hand-off to ENV (via the lead):** photo stations at 150–190 m on the east shore fall inside `ENV_backdrop_*`.
6. **Projection:** coverage of lagoon-facing texels 95.8 / 97.5 / 69.8 / 87.7 %, about 85 % overall (weighted). Median views 36 / 40 / 33 / 41.
7. **Delighting:** robust inter-view spread of log luminance (1.4826 × MAD). Attic panels: 0.701 raw, 0.315 with (a) per-photo gain + gamma (0.45×, passes ≤ 0.5×), 0.339 with (d) directional shading. All texels: 0.78–1.32 raw, 0.35–0.50 with (a). **(a) wins.** Drum sun gradient 5.4 %/10° with (a), 5.0 % with (d). (b) Marigold was not run: time box, and (a) already meets the target.
8. **Integration:** in PFA_concrete, via UVBake: `c = mix(conf, c_r9, c_base)`, then `mix(0.6 × conf × (0.6–1.0 per object), c, c × ratio)`. Where the atlas is confident it replaces round 9's single-photo ratio. The first cut only filled where round 9 was absent, and moved 0.5–1 % of cam02/03 pixels. Per-instance variation follows lead decision (b) fallback: the column UVBake islands are Smart-UV charts, so a U shift is not possible. Instead each object gets a ±3 % value jitter and its own 0.6–1.0 share of the map. **Please log this as an exception.** Column tint on MAT_column_rose: saturation × 0.8, hue −6°.
9. **Measurement:** before and after on the same rebuilt master, with the atlas switched off for "before" (ENV changed through the main merge). Hero Cycles 1080p 64 spp, cam02 and cam03 at 720p 64 spp, Eevee hero `p10_after_eevee.png`.
   | box | before | after | ref 169 | hold / verdict |
   |---|---|---|---|---|
   | attic sunlit | 187.0 / 36.9 / .513 | unchanged | 189.5 / 40.0 / .590 | holds (ORN relief covers this box) |
   | attic shaded | 119.8 / 41.2 / .687 | 129.1 / 40.9 / .593 | 120.0 / 30.4 / .449 | **lum breaks hold (121.3 ±2), further from ref**; hue and sat closer |
   | entablature | 118.9 / 38.1 / .768 | 117.4 / 38.5 / .772 | 134.5 / 32.4 / .611 | slightly further |
   | column shafts | 73.7 / 28.8 / .701 | 82.3 / 28.3 / .658 | 96.8 / 24.8 / .585 | closer; hue within ±4°, **sat 0.073 outside the ±0.04 window** |

   Attic anisotropy 5.07 → 5.07, narrow box 8.46 → 8.47 (passes ≥ 2.0). Water boxes unchanged. Seams: cam02 2.8 % of pixels moved, blurred step 4.96 lum/px; cam03 1.0 %, 3.09 lum/px. No seam is visible on the sheet crops.
   **The visible effect is mostly on the column shafts.** The hero's attic, frieze and drum band are ORN instances, which have no UVBake and so keep the procedural.
10. **Texture budget:** 2.1 MB total, two 2048² 8-bit PNGs (`PFA_p10_ratio` stores ratio/2 in RGB; `PFA_p10_mask` holds R conf, G views, B covered).

**Hand-offs**
- **ARCH (lead's hook):** exec `arch_uvbake.py` after `arch_uvproj.py`, read `fails`, and refuse to save when it is non-zero.
- **MATERIALS:** `mat_build.py` must run `mat_p10_integrate.py -- --weight 0.6 --col-sat 0.8 --col-hue -6 --save` after it rebuilds.
- **EXPORT:** the atlas sits inside the PFA_concrete node tree, so the Phase 6 PBR bake picks it up. UVBake must exist at bake time (it is in master_delivery) but does not need to survive into the glTF. Images: PFA_p10_ratio.png and PFA_p10_mask.png.

**Open items:** the shaded-attic lum hold (129.1) and the column sat (0.658); one more material iteration would fix both, for example weight 0.4 and column sat × 0.7. Projecting onto ORN instances (the hero's attic reliefs) would need UVBake on ORN, which ORN owns. Colonnade not covered.

## Final-review fixes (docs/reviews/phase10_proj_r1_review.md, 2026-09-24) — supersedes the registration claims above
- **#1 held-out registration** (`mat_p10_edges.py holdout`, evidence/registration_holdout.json): per used camera, the per-camera
  correction is undone, the rotation re-fitted on the left (or right) half of the contour points and the peak residual measured on the
  other half. Fit-half median 0.5 px, **held-out median 20.4 px** (p75 32.5; 7 of 86 halves <= 4 px). The two halves pull in opposite
  x directions (median dx -9.5 vs +11.0, opposite sign in 88 %): a per-image SCALE error (focal / distance ambiguity) that a rotation
  cannot fix. The 0.71 px was a fit residual; the registration is NOT <= 4 px.
- **#3 land gate** (`mat_p10_gates.py`, evidence/camera_gates.json): 28 of 71 centres inside the OSM lagoon, 40 more than 10 m behind the
  east shore on their bearing; **40 of the 43 used cameras drop**, 3 remain (ref_085, ref_095, ref_161). Same cause as #1 (stations
  pushed 20-70 m too far). Steps 6-8 were **not** re-run with 3 cameras: that atlas would be a 3-view projection from mis-scaled
  stations. The shipped atlas (43 views) stays on the branch; recommend round 2 ships it at `--weight 0` (= pre-Phase-10 material,
  now an exact no-op) until the registration gets a per-image scale / focal solve (e.g. PnP from hand-picked points), then re-projects.
- **#5** `mat_p10_render.py --atlas-off` now zeroes P10_w AND unlinks/zeroes P10_unr9 and neutralises the column tint. Note: the round-1
  "before" renders zeroed P10_w only, so round 9 was already removed there where conf > 0: the hold table's before column is not the
  true pre-Phase-10 state (round 2 re-measures on the merged master).
- **#10** round-9 removal is now `--r9-removal tied` (default: factor = conf x weight; weight 0 = no-op) or `full` (round-1 behaviour).
  Round 2 sweep: `mat_p10_integrate.py -- --weight 0 | 0.4 | 0.6` (tied). materials.blend saved with weight 0.6, tied.
- **#9 evidence** in assets/textures/projection2/evidence/: registration_peak(.json/_summary.txt, control table), registration_chamfer_weak,
  registration_holdout, camera_gates, proj_stats, texture_stats, hero_hold_table, hero_hold_vs_ref169, seams_cam02_cam03.
- **#12 determinism**: arch_uvbake.py run twice without --save / --write-hashes on the saved architecture.blend: both runs 0 failures,
  all 37 per-mesh SHA-1 equal to the committed ones (logs evidence/uvbake_determinism_run{1,2}.log) -> the SHA hook is usable as is.
