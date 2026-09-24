# phase10-proj r1 — FINAL review (ba87ab76..81f79839, plus the part-1 fix-now items) — **MERGE WITH FIXES**
Read-only, no Blender. Read: brief, process.md, the report, notes "Phase 10 r1", decisions 2026-09-24, every mat_p10_* script and
arch_uvbake.py diff, cameras.json, and the work/ stats on disk (proj_stats, texture_stats, hero_table, seam_cam0*, run logs).
Viewed: mat_p10_sheet.png, mat_p10_registration.jpg (960 px). The pipeline is careful and the report is mostly honest. Two acceptance
items fail as stated (shaded-attic hold, column sat). One passes only by construction (registration). The fix-now items are cheap (CPU or 33 s runs).
**Fix now before the merge: 1, 5, 9, 12.** The rest carries to the round-2 materials pass or the lead.

## Registration (part-1 #1-3)
1. **fix now**: the 0.71 px median is a fit residual, not a measurement. `peakfix` rotates each camera by exactly the shift that `peak` measures,
   twice, and `peak` then re-measures the same objective on the same contour points. The controls (10/20/40 -> 10.5/20.5/40.0) prove only
   that the estimator is shift-equivariant, which holds by construction: `score(dx+s)`. They cannot show that it locked onto the right feature.
   The only independent number, the oriented chamfer 6.09 -> 5.29 px, has a control ratio of 1.05, so it is flat and proves nothing. Its level (5.3 px) is still above the
   4 px target. The registration sheet shows chamfer medians of 3.8-14.3 px on 12 cameras (the ungated first 12), and the overlay is invisible at 960 px.
   The lead's hold asked for proof of registration, so this item is not closed. Fix (CPU, about 10 min): a held-out split. For each of the 43 used cameras, run `peak` on
   disjoint contour halves (left/right and top/bottom of the frame, or near vs far depth) and report the median |split difference|. At or under 4 px,
   it proves the local registration and catches the roll, scale and perspective errors that a 2D shift cannot fix. Alternatively, use >= 6 hand-clicked points in 5 photos.
2. **checked**: the gates are applied as reported in `load_views` (residual <= 6, `usable_physical` z -0.5..6 / r 30-250, rot <= 1.5 deg).
   proj_stats lists 43 views. ref_086 (z -0.7) and ref_150 (r 558) fail the physical gate. ref_169's peak residual is 23.3 px after a 0.33 deg
   correction, so the fit did not converge. That is consistent with ref 169 being a stitched 24 mm panorama (reference_sheet), which a pinhole cannot fit. Excluding it is right.
   The consequence is in #10: the atlas carries none of the hero's own view.
3. **carry (station plausibility; answers check 8)**: I tested the camera centres against the OSM lagoon polygon (`site_local.json`,
   converted with `osm_to_world`). **28 of 71 centres lie inside the lagoon polygon**, up to 36 m from its edge, and **5 of them are among the 43 used**
   (ref_064, 067, 017, 090, 058). On the lagoon axis the water spans r 46-117 m. About 20 cameras sit at r 140-186 m, 25-70 m behind the east
   shore. Seven of those cluster at r 172-186 m and z 4-5 m (ref_070/071/144/145/148/156/171). ref_169, the hero twin that the reference sheet puts
   at about 114 m on the shore, lands at 160 m, z 5.2. The physical gate (r 30-250) cannot see any of this.
   This looks like per-image focal/distance ambiguity, not an ENV error. `env_backdrop.py` builds the houses from OSM footprints.
   **Do not hand this to ENV.** Instead, add a land gate (outside the lagoon polygon and outside the OSM buildings) or down-weight those stations.
   Hiding `ENV_backdrop*` / `ENV_terrain*` and the 12 m near clip hide the symptom. A photo can project through a real foreground tree that
   the clipped model does not have, or through geometry that sits between a mis-placed station and its true one. The 36-40-view weighted median limits the damage.
4. **checked (part-1 #2 closed, one residue)**: `mat_p10_step2.sh` records the order, `icp` deletes refine/refine_cams/edges.json, and
   `cameras` folds refinements in only through `--with-*` flags. refine_cams.json has fscale 1.0 on all 71 cameras, so no chamfer refinement leaked
   in. Residue (carry): step 2c keeps `depth_arch` on the existence of meta.json, and `icp` does not invalidate it. After a new similarity, the contour set
   comes from the old cameras. Delete it in `icp` or key the cache to a hash of sim.json. `mat_p10_sfm.py` still hard-codes `MAIN` (part-1 #11).

## Projection, delighting, integration
5. **fix now (the recipe regresses)**: `mat_p10_render.py --atlas-off` zeroes only `P10_w`. Since 3472d7ee, `P10_unr9` removes round 9 at
   `conf` independently of the weight, so re-running the recipe's "before" now renders round 9 stripped, not round 9. The committed before
   (render at 13:01-13:14, before 3472d7ee at 13:15) was fair, so the numbers stand, but round 2 will measure against a wrong baseline.
   Also zero the `P10_unr9` factor under `--atlas-off`.
6. **checked / note**: the depth test is `z <= Zm + 0.05 + 1 % z` (about 1.6 m at 150 m). Both sides are planar camera depth (Cycles Z, and C.project z),
   undistorted for the half-res pass. The facing weight is (n.v)^2 above 0.15, the border feather 40 px, and the registration and resolution weights are included. Gaps: no erosion
   margin at depth discontinuities (occluder colour can bleed a few px onto the wall behind a column or tree edge), and no footprint blur. The
   docstring's "texel smaller than a pixel" is false for the shipped 1024 quadrants: attic 21 texels/m against photos up to 40 px/m.
   Coverage reproduces from proj_stats: 95.8/97.5/69.8/87.7, weighted 85.3 %. Confident texels (conf > 0.5) are only 73/82/62/**34** %.
7. **carry (delighting claim is weaker than stated)**: the spread 0.701 -> 0.315 uses the same texels and the same W before and after (good). But the per-photo gain+gamma is fitted
   to the consensus over those same texels, so the metric is in-sample. It also pools faces 07/00/01 instead of comparing sunlit and shaded panels as the brief
   asks. A global per-photo tone map cannot equalise a panel that is sunlit in one photo and shaded in another. The drum's 5.4 %/10 deg azimuth gradient is
   still in the shipped ratio (the LF sigma of 0.75 m cannot remove it). The raw gradient is never reported. On the new cameras, (d) wins the gradient (5.0 vs 5.4) and
   group 2's spread (0.373 vs 0.386). The `VARIANT` comment in mat_p10_texture.py ("(d) ... LARGER drum sun gradient 7.2 vs 5.9") is stale.
   Round 2: detrend log-lum against azimuth per group before the bands (cheap numpy), and report raw/(a)/(d) gradients with a split sunlit/shaded panel table.
   The same risk applies to the columns: the ratio is normalised per normal bin only, so the photos' lit/unlit side of the shaft is baked into all 16 instances.
8. **checked**: integration touches only `P10_*` nodes in `PFA_concrete` and `P10_colsat` in `MAT_column_rose`, and it is idempotent (removes and relinks).
   Meshes without UVBake read corner (0,0), which has confidence 0. The sunlit ORN attic box is unchanged, which confirms this in Cycles. The Hue node value 0.5 - 6/360 is correct. There is no hash or node-count
   check of the other materials. By reading the code they are safe, but add a before/after node-count print. Dead nodes `P10_r9w` / `P10_r9c` remain. `base_src` trusts that
   the node feeding Group Output is round 9's mix: assert that it is (its Factor comes from `PFA_photo`.Weight) before rewiring. **Recipe:** the
   hand-off is documented (report + notes pipeline step 5), but `mat_build.py` does not call it. The next `mat_build` run silently drops the atlas.
   The lead must put the hook in the round-2 materials brief.
9. **fix now (evidence)**: none of the numbers in the report are backed by a committed log. work/ is gitignored, and the only uvbake log on disk
   (`uvbake_save.log`) is the pre-quadrant run (89/102/131/277). Commit final copies of the peak table with controls, the chamfer check, the gate summary,
   proj_stats.json, texture_stats.json, hero_table.txt and seam_cam0*.txt, plus the uvbake log from #12, under renders/logs/ or docs/.
10. **carry (the hold break is mostly structural; the planned retune is only partly plausible)**: `P10_unr9` removes round 9 in proportion to `conf`
   (about 1), but the atlas comes in at 0.6 x conf x 0.6-1.0. On confident texels the hero loses 100 % of its own-view (ref 169) ratio and gains only 36-60 % of a
   43-view mean-1 map that contains no ref 169. So the shaded attic drifting 119.8 -> 129.1, away from ref 120.0, is the expected result. **Weight 0.4 alone will not restore it**
   and may make it worse. Tie the removal to the same w (`unr9` factor = w), and measure once at w = 0 to separate the two effects. Columns: x0.8 moved
   sat only 0.701 -> 0.658. Extrapolating linearly, x0.7 gives about 0.647, still out of 0.545-0.625, and about x0.6 is needed. Lum 82 vs ref 97 stays the bigger gap.
11. **carry (lead: exception)**: per-instance columns. The pattern is identical in position on all 16, and only its level (±3 %) and its share (0.6-1.0) vary. At hero
   distance that does not decorrelate the streaks. It is layered on the procedural per-instance weathering, which does vary. The stated reason is true for a UVBake lookup,
   but not in general. A (theta, z) shaft map (a numpy resample of the column atlas using `lpos`), sampled from Object coords with Random x 2pi, gives the
   real U offset of decision (b). Log the exception for r1, or ask for the theta map in round 2.

## UVBake (part-1 #5-7)
12. **fix now (hook prerequisite)**: exit 1 when run directly (`_run_directly`), `work/` created, and 37 per-mesh SHA-1 written. All verified in code. But
   hashes were written for the first time in db6a16f4 with `committed = {}`, so **no run has ever compared two layouts**. "Byte-identical re-save" has
   no committed evidence, and the SHA is exact on float bytes, so one ULP of packer drift fails every `arch_build`. Run `arch_uvbake.py` twice on the committed
   architecture.blend without `--save` / `--write-hashes`, and commit both logs showing `0 failure(s)`. That run is the determinism test. If it fails, compare
   with a tolerance (max |dUV| < 1e-5) instead of SHA. Minor: `--write-hashes` rewrites hashes even when other checks failed (gate it on
   `fails == 0`). A mesh that disappears is not flagged. A `--preview` build still rewrites uvbake_groups.json.
   Lead's hook: as planned. Note that any later ARCH geometry change now forces the full projection re-run, steps 3-8.

## Acceptance (brief) and scope
13. Registration <= 4 px: **not independently shown** (#1). Coverage >= 80 %: **pass** (85.3). Spread <= 0.5x: **pass as defined** (0.45x, in-sample, #7).
   Columns in window: **fail** (hue 28.3 within ±4, sat 0.658 outside). Holds: **fail** (shaded-attic lum 129.1 against 121.3 ±2, moving away from ref). Entablature slightly further from ref.
   Seams: **pass** (cam02 blurred step 4.96, cam03 3.09, not visible on the sheet). Anisotropy >= 2.0: **pass vacuously**. The box is ORN relief, which the atlas does not
   reach (5.07 -> 5.07). The visible effect is mostly on the column shafts, which the report states.
14. **checked**: the scope is clean. `git diff main...phase10-proj` touches only owned files plus `.gitignore` (.venv-p10/, projection2/work/). There is nothing in lighting, ENV,
   export/ or web/. Committed textures: 1.54 + 0.52 = 2.07 MB, as claimed. Renders go through blender_run.sh (logs end `blender_run.sh: pid … rc=0`).
   Merge note: the branch includes the main merge at 65700a95, so `diff ba87ab76..HEAD` shows ENV files that are main's, not this agent's.
