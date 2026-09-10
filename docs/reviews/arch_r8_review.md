# MERGE WITH FIXES — branch `architecture` @ 3a358ca (round 8, vault chord-triangle fix)

The fix is right and the evidence holds. `arch_lib.bisect_grid` (arch_lib.py:401) uses `bmesh.ops.bisect_plane` with
`clear_inner/clear_outer=False`, so it only splits faces — nothing deleted; both plates carry one material slot, so no
material-index loss, and the `registers` reveal loops are built by `plate` before the cut and survive it. It is called
BEFORE the vertex mapping in both places (arch_build.py:743 vault, :969 ceiling). Grid axes are correct: both plates are
built with `xaxis=(1,0,0), yaxis=(0,1,0)` at origin (0,0,0), so the local cut planes are the parametric arc/depth axes.
Bent-plate audit is complete: `grep 'vertices:' arch_build.py` finds exactly the two mapping loops (743, 972); outer and
inner archivolts are `L.sweep_open` along an `n_arc`-sampled arc (arch_build.py:401, :470), the vault panel is a loft,
attic panel frames / string courses / attic roof are flat plates never bent — none can chord. The face check uses the
tapered `r(t)=R0+(R1-R0)t` from each face centre's apothem (arch_vault_facecheck.py:57-66) and exits 1 on failure (:139).
Idempotent: `common.rebuild_collection("ARCH")` (arch_build.py:42) plus a fresh mesh per `plate`, so no double-cut.
`arch_uvproj` re-ran: "33 objects / 31 meshes; missing: none", 0 clamped, round-trip 0.0 px — `UVProj` / `UVProj_valid`
intact for materials. All touched files are ARCH-owned; the only binary > 5 MB is the owned `assets/architecture.blend`
(50.5 -> 58.9 MB). The composite sheet confirms the barrel visually.

1. arch_r8_sheet.py:12 — `MAIN = "/Users/dk/Projects/..."` hard-codes the main checkout. **fix now**:
   `os.environ.get("PFA_MAIN_ROOT", ...)` (PIL-only script, so it cannot import `common.MAIN_ROOT`).
2. "+5.2 %" understates the cost: the delta is the same +140,284 tris on every LOD — LOD1 1,109,390 -> 1,249,674
   (**+12.6 %**), LOD2 726,542 -> 866,826 (**+19.3 %**); the plates are not decimated per LOD. ARCH has no tri-budget
   gate (that is ORN's), but LOD1 is the viewport default and Phase 5 wants master.blend open < 1 min.
   **carry**: re-run `scripts/arch_perf.py` after the merge.
3. arch_r8_cam03.py:50-62 — `px_width` ignores its `dist` arg and measures the raw bound box, dropping only corners
   behind the camera: it prints 2939 x 7508 px in a 1280x720 frame and "0 x 0" for columns 029/030. The notes' "423 px,
   33 % of the frame" is a hand calculation, not this script. **carry**: clip to the frame before quoting a px width.
4. arch_vault_facecheck.py:85,90 — rays start at apothem 30 m on the bay axis (no qa_cameras station is copied, right
   call) but each cast is `distance=70.0`, so "clear" means only "nothing within ~70 m", never the far-side/soffit hit
   the brief asked for. **carry**: raise the distance or reword the print so it cannot read as a missing far wall.
5. build_ceiling was fixed but never seen: ceiling ribs are report-only in the check (largest face 1.26 m2 vs the 1.0
   the vaults must pass; drop 0.568 vs COFFER_DEPTH 0.55) and cam04 was not rendered. **carry**: QA to check the
   ceiling in cam04; tighten `CEILING_RIB_STEP` only if it reads faceted.
6. arch_lib.py:401 docstring — the cuts are world-aligned in local space, equal to the parametric axes only because
   both callers pass the identity axes. **carry**: say so before a rotated plate uses it.
