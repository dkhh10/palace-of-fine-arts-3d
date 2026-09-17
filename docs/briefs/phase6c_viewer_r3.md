# 6c viewer brief, round 3 = the LAST 6c round (Opus high, fresh agent, 2026-09-17). Branch phase6-viewer (worktree .claude/worktrees/phase6-viewer; `git merge main` first).
Read: docs/qa_round_16.md in full (verdict ONE MORE ROUND; the crown interior/rim numbers: cam02 centre/edge 0.504 vs ref 0.364, range/mean 2.05 vs 3.12; cam05 1.26 vs 1.77,
p10 58.9 vs 31.7; shrub boxes level 1.34-1.70x with 2-8x the hard-edge share; the tile defect list; the 1 800.6 MB memory figure that the README and decisions.md misreport
as 1 717), docs/decisions.md from "2026-09-17 · Lead 100 % tile judgement" to the end, web/README.md 6c sections and open items, web/src/foliage.js, foliageLazy.js,
lightmaps.js, CLAUDE.md "Phase 6" and machine rules (Chrome only via scripts/chrome_run.sh + screenshot.mjs, which pauses on MAIN's export/out/bake_queue/status.json —
the export engineer holds it for ~10 min of Cycles this session).
1. Crown volume (stations 2 and 5, the hero's shore trees): the crowns read as uniformly lit balloons. Bring the interior/rim contrast to the reference: gate or reduce the
   crown-bent normal blend, add an interior-darkening term per fragment (distance from the crown centre normalised by the crown radius, and the near trees' COLOR_0
   irradiance / the far meshes' vertex AO, whichever the tree carries), keep the rim translucency. Measure with QA's crown boxes (scripts/qa_r16_probe.py) until cam02
   centre/edge is within 0.05 of 0.364 and cam05 within 0.1 of 1.77 without the level leaving 0.9-1.1x; judge the 100 % tile, not only the box.
2. Shrub/reed level and edges (stations 1, 2, 3, 5): level 1.34-1.70x the reference. The export engineer is settling whether the albedo is right (docs/qa_round_16.md says
   albedo; the lead doubts it because the tint is the Phase 5 material's own) with a Cycles DiffCol pass — read export/out/gate3/foliage/albedo_check.json when it lands (ONE
   `until` loop, sleep 60 s, max 60 min) and act on its verdict: if the albedo matches, the gap is yours: the per-placement irradiance is mean_nonzero over the cov mask, so
   multiply by the shipped `cov` to get the placement's true average, add the same interior/height darkening as the trees to the card clusters (lower and inner cards darker),
   and cut the hard-edge share (the alpha path: the MASK cutoff vs alpha-to-coverage sample count, mip bias on the cut-outs). Measure with QA's shrub boxes.
3. Walk-up: consume `trees.walkup_mesh` (env_trees_lod1.glb, export item 2) within `?walkupmesh=` 15 m of the walker, else the LOD2 within 12 m, else the impostor; same
   placement rows and irradiance; prove it with the station-2 walk-in shot.
4. Fix the memory figure everywhere it is quoted (1 800.6 MB per round16b_perf.json) and report what 6c added per asset class; do not chase the budget (6b's tiers do).
5. Capture "round16c" with gate4.sh (six stations, post-off, tiles, perf, walk) + bare URL + the station-2 walk-in, only after the export's glb and the lead's manifest re-run
   (wait for `trees.walkup_mesh` in MAIN's manifest with ONE `until` loop, max 2 h) and when the lock is idle. Frame time within +3 ms of round 15. README QA notes for QA 17.
Commit after every measured step. Report < 20 lines: the crown and shrub boxes before/after per station, tile paths, per-station ms, memory, commit id.
