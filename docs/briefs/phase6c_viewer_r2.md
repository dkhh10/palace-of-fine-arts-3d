# 6c viewer brief, round 2 (Opus high, fresh agent, 2026-09-17). Branch phase6-viewer (worktree .claude/worktrees/phase6-viewer; `git merge main` first).
Read: docs/briefs/phase6c_viewer.md (C2's far-tree half, C3, C4) and docs/briefs/phase6c_foliage.md; CLAUDE.md "Phase 6" and machine rules; web/README.md on your branch
(the 6c section: `src/foliage.js`, every switch and default, "Open, with owners"); docs/decisions.md from "2026-09-17 · Impostor blue cast" to the end; export/README.md in
MAIN is stale for 6c — read the export worktree's copy read-only (.claude/worktrees/phase6-export/export/README.md section "Phase 6c") and the bake worktree's spec
(.claude/worktrees/phase6-bake/export/README.md section "`trees.far_mesh.lighting`"). MAIN's export/out/gate3/manifest.json now carries `trees.far_mesh`, `shrubs.lod1`,
`materials.foliage` (the lead ran manifest_v4 this morning); `trees.far_mesh.lighting` arrives when the bake lands and env_trees.glb gets COLOR_0 when the export re-runs.
1. Far-tree consumer: lazily load env_trees.glb after the first frame (manifest `trees.far_mesh`), draw the 127 placements as meshes within treeMeshDist with the leaf shader,
   COLOR_0 vertex AO (when present; 1.0 until then) x per-placement E_placement (from `trees.far_mesh.lighting` when present, else the chroma fallback) x the leaf shader;
   iNear on the 127; impostor beyond with the existing dissolve; `?impmod=full` becomes the default once E_bake is in the manifest (ratio clamp: 4.0, fall back to 1 where E_bake
   has a zero channel — the lead's ceiling). Prove it with the station-2 walk-in.
2. C3 live: shrub/reed LOD1 within 30 m from env_shrubs.glb (`shrubs.lod1`, placements share the LOD2 irradiance rows). Consume `materials.foliage` (the translucency
   factor map per material; the tinted albedo replaces the raw card when the export's round 2 lands — read the manifest, do not hardcode paths).
3. House-keeping: the 18 untracked renders/web/round16* sidecars in your worktree — commit the JSON, downscale the bare-URL PNG to 960 px and commit that, gitignore the rest.
4. Capture "round16b" with gate4.sh (six stations, post-off control, tiles, perf, walk) + one bare-URL 1280x720 capture + the station-2 walk-in at 3 m from the nearest tree
   (same coordinates as round16), ONLY after MAIN's export/out/bake_queue/status.json says idle AND env_trees.glb in MAIN carries COLOR_0 (verify_glb or a glb header check),
   waiting with ONE `until` shell loop (sleep 120 s, max 3 h). Frame time within +3 ms of round 15 (28.2 ms median at 1440p); report resident GPU memory. README QA notes
   updated for QA 16 (every default, every A/B, the numbers). Chrome only through scripts/chrome_run.sh; screenshot.mjs pauses on status.json — code while it says running.
Commit after every measured step. Report < 20 lines: per item before/after, the tile paths, per-station ms, memory, commit id.
