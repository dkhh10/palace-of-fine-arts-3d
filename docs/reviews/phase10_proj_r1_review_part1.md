# phase10-proj r1, part 1 (steps 1-3b, c46ee61c..7cdede75) — PARTIAL: steps 1-3, NOT MERGEABLE YET
Read-only, early review of the committed state; branch head at review time e602c93f. Covered: `mat_p10_sfm.py`, `mat_p10_align.py`,
`mat_p10_edges.py`, `mat_p10_depth.py`, `mat_p10_common.py`, `cameras.json`, `arch_uvbake.py` (last change 7cdede75), the
registration sheet. Not covered (final review starts at ba87ab76): steps 4-8 (atlas, depth, project, texture, integrate, materials.blend).
**Blocking a merge so far:** findings 1, 2, 3, 5, 6 (7 is needed for the lead's hook).
The maths is right. The gravity from the right vectors (smallest singular vector, sign from the mean up vector) is correct, and so are
B = [f x up, f, up] (det +1), the grid-to-ICP handoff (T = -s Rz (B^T axis) + tz), the point-to-plane linearisation and its update,
the model-to-world camera mapping (Rw = R Rs^T, tw = s t - Rw Ts), the D^-1 fold (tw computed before Rw is rotated), the per-camera
rotation about the centre (centre unchanged), and the COLMAP-to-Blender camera (flip diag(1,-1,-1), lens/shift from K for both sensor fits).
The compass maths matches CLAUDE.md (az 0 = -X, 90 = +Y). Coarse registration is plausible: aligned sparse points peak at r 21.5-22 m at z 20-30 (ARCH 22.0), the dome points reach z 50.5
(apex 52.8), and the ref 169 camera lands at (-40.8, 156.6, 3.6).

1. **fix now**: the acceptance number has no discriminating power. It is computed against the master mesh edges, as the brief asks
   (ARCH LOD0 Position pass, depth jumps + creases, projected into the photo, one-sided chamfer to Canny edges). I re-ran it on the
   agent's own `work/depth_arch` passes (CPU, no Blender) with the model edges shifted by a known amount, on 12 cameras.
   Median of medians: as registered 3.39 px, shifted 10 px 3.47, shifted 20 px 3.49, a random pixel in the bbox 7.10. On 8 cameras,
   a 40 px shift gives 3.57 (silhouette/jump edges only: 3.29 -> 4.21). Photo Canny density is 6.4-11.8 %, and the LOD0 crease
   edges sit in dense ornament, so a model edge is always near some photo edge. "3.42 px, 59 <= 6 px" does not show <= 4 px
   registration, and the ref 169 overlay (1.29 px) is equally uninformative. The `refine` D (shift 1.64 m in -Y, 1.35 deg) and the
   per-camera refine (3.58 -> 3.42) were fitted on the same flat objective. Fix: a calibrated metric that must rise at least 2x under
   a 10 px control shift, reported with the control. Options: an oriented chamfer (gradient direction within 15 deg), sky-silhouette
   edges only (dome / attic / cornice against the sky mask), or >= 6 hand-clicked control points (capital centres, cornice corners)
   in >= 5 photos. Then re-judge D and the per-camera refine on it.
2. **fix now**: step 2 cannot be reproduced from the committed scripts. `work/edges.json` (`per_image`) feeds `residual_px` in
   cameras.json and the <= 6 px camera gate in `mat_p10_project.py:51`, but no committed script writes it. The run order is recorded
   nowhere committed: icp --sector=0 -> cameras -> depth --arch-only --cams (12 cams) -> refine -> cameras -> edges cams -> cameras
   -> check. That order matters. `cmd_cameras` silently folds in whatever `refine.json` / `refine_cams.json` are on disk. `refine`
   and `cams` measure against the current cameras.json, while `cameras` re-applies the deltas to the sim base. Re-running `icp`
   therefore applies a stale D, and re-running `cams` drops the earlier per-camera deltas. Commit the edges.json writer, a runner
   (or a numbered recipe in the notes), and have `icp` delete stale refine files.
3. **fix now**: no camera sanity gate. The brief asks for az ~82, z ~ +1 m, r 50-190 m. Measured: az 5/50/95 % 59/82.1/107
   (82 is forced by the sector prior, so it is not independent evidence), z -1.04/0.76/2.57, r 50.7/138/184. Outliers:
   ref_150 at r 558 m, **z -94.6 m** (telephoto f 7870, residual 6.04: dropped by the 6 px gate by 0.04 px only); ref_086 at z -2.92
   (1.6 m under the water, residual 1.09: IS used); ref_161 at r 36.9; ref_135 at 40.8 px and ref_095 at 28.8 px. The projection
   must exclude on physical bounds (z -1.3..+6, r 30..250) as well as on the residual. The residual cannot be the only gate while
   finding 1 stands.
4. **carry**: the camera-height prior (`HZ_W` 3.0 on the median z - 1.0) is a gauge choice: the chamfer trades tilt against height.
   Keep it, but report it as a prior, not a measurement ("z median 0.76" is mostly the prior). The scale is weakly determined: the other seven sectors preferred 16.75 m/unit, the forced sector 15.25, and ICP gave 15.32.
   The radial check above supports about 15.3 to within a few %.
5. **fix now**: `docs/materials_notes.md` on the branch holds only the checkpoint, which says "nothing saved to any .blend", "step 2
   in progress" and "UVBake NOT saved". The branch has saved architecture.blend twice (47f390be, 7cdede75) and materials.blend
   (e602c93f). Write the "Phase 10 r1" section. The stale docstrings: `mat_p10_align.py` Method 1-3 still describes image-up
   gravity, a mean-heading and a 4-24 scale multi-start. `arch_uvbake.py` still quotes 89/102/131/277 texels/m (the committed
   quadrant layout measures 43/50/64/136) and a "5 px at 4096" margin (0.0012 of a 2048 quadrant is ~2.5 atlas px). Its `--dry`
   exits before every check, yet the checkpoint calls the dry run "checks pass".
6. **fix now (arch_uvbake exit)**: the failures only block `--save`, and the run exits 0. `blender_run.sh` reported rc=0 either way,
   so neither a caller nor the build hook can see a failure. Raise `SystemExit(1)` when `fails` (outside `--dry`). Also, `OUT/"work"`
   is never created (only `projection2/` is), and `np.save(OUT/"work"/"uvcov_*.npy")` crashes on a clean checkout.
7. **carry (for the lead's arch_build hook)**: exec `arch_uvbake.py` after the `arch_uvproj.py` exec and before the save. Order
   matters: its layer test expects UVProj to exist and UVBake to be appended last. It sees arch_build's argv (`--no-save`/`--preview`,
   not `--save`/`--dry`), so it will not save or exit on its own. The hook must read `fails` from the exec namespace and refuse to
   save when it is non-zero. It must also check that the rebuilt layout is the one the committed atlases were baked against.
   `PFA_p10_ratio/mask.png` are only valid for the 7cdede75 pack, and any change to ARCH geometry or to Blender's packer silently
   misaligns them. Ask the agent to write a per-mesh UVBake SHA-1 into `uvbake_groups.json`. The hook then fails when the hash
   differs, which means the projection must be re-run.
8. **checked, OK**: the arch_uvbake invariants. It adds only `UVBake`, appended last. The test compares the layer list to
   before + [UVBake], UVMap first / active / sole active_render, and the UVMap and UVProj SHA-1s, the UVProj_valid attribute hash
   and the vertex/face counts before and after. It unwraps shared meshes once per group (group 1: 6 objects / 4 meshes, group 2:
   51 / 6) and restores the visibility flags. It is idempotent: an existing UVBake is removed first. The rasterised overlap test
   (pixel centres, strict barycentrics) and the quadrant test do fail the run. The report shows 0 overlap texels in all 4 groups.
   The object list is `arch_uvproj.py`'s plus the columns, bases, archivolt_00 and imposts_00, which matches the brief.
   Weak spots: the pre-run active_render state is not recorded (forced True before the test); `face_weight`/`STATIONS` are dead code.
9. **carry (lead decision)**: texel density is 43/50/64/136 texels/m, not the brief's >= 200. The agent chose one shared 4096
   atlas (four 2048 quadrants) instead of the allowed four 4096s. It is defensible: the registered photos give about 16-40 px/m
   (1600 px at 50-190 m, f 1250-2400 px), so finer texels add no photo detail. It is still a deviation from the brief and must be
   logged in docs/decisions.md with that measurement. The colonnade was left out without reporting how many registered views cover
   it (the ref 169/174 overlays show colonnade edges).
10. **carry (non-negotiable)**: the 16 columns share one mesh, so they share one atlas region and get one identical projected pattern,
   6-8 of them at hero distance. CLAUDE.md forbids identical instances at hero distance. The integration must vary it per instance
   (object-random offset/rotation of the LF band, or a per-instance tint), or the lead must log an exception.
11. **note**: hygiene is clean. The changed files are all owned, plus `.gitignore`, which is the lead's file (adds `.venv-p10/` and
   `projection2/work/`; 2.7 GB of work files are correctly ignored). Nothing touches lighting, ENV, export/ or web/. Every
   Blender launch in the docstrings and the work logs goes through `blender_run.sh`. The committed binaries are the two atlas PNGs
   (2.1 MB) and the two .blends. `mat_p10_sfm.py` hard-codes `MAIN`: use `common.ROOT`'s parent logic / `common.REFERENCE_DIR`.
   `work/icp.log` is the pre-sector run (az 217); the step-2 logs are gitignored: commit final icp/refine/cams/check copies.
12. **note**: `cameras.json` meets the brief's schema: file, K, k1, R, t, centre, size [w, h] and residual_px, plus the similarity,
   D and the refined count. The convention is world-to-camera `x = K(RX + t)`, COLMAP axes (+x right, +y down, +z forward); state
   those axes explicitly in `note`. The residual is in pixels at the registered size, and portrait images are only 1062-1340 px
   wide, so "4 px at 1600 wide" is looser for them.
