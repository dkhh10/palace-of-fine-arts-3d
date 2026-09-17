# 6c viewer brief (Opus high, fresh agent). Branch phase6-viewer (worktree .claude/worktrees/phase6-viewer; `git merge main` first — main carries the bare-URL default fix 5e1fffa).
Read docs/briefs/phase6c_foliage.md (item C, F), CLAUDE.md "Phase 6" and machine rules, web/README.md (yours: the QA notes, the impostor section, the instance-irradiance consumer,
the flags), docs/qa_round_15.md tile defects, docs/decisions.md from "2026-09-17" to the end, web/src/lightmaps.js (vertex irradiance and instance irradiance consumers),
the impostor module, and the user's finding: at station 2 a far-tree impostor stands metres from the camera as a blue blob, the near tree is flat cards, the shrubs confetti.
C1. Leaf shader now, on the shipped assets: two-sided leaf cards with a translucency term (sun through the card; a constant per material until the export's mask lands),
    soft edges (alpha-to-coverage if the render target is multisampled, else alpha hash; keep the manifest's MASK cutoffs), normals bent toward each tree's crown centre
    (per tree object at load; document the blend), applied to the 14 near trees and the shrub/reed cards. Measure at cam02 and the hero: the round-15 boxes (tree level 0.99x
    must hold, cyan must not return) and a 100 % tile of the near tree at cam02 beside the Cycles reference; judge by the tile, not the metric.
C2. Runtime LOD: `treeMeshDist` (default 40 m from the walker, `?treemesh=`) — within it the tree renders its mesh, beyond it the impostor, short crossfade (alpha over ~5 m).
    For the 127 far trees the mesh arrives in `env_trees.glb` (export item A, lazily loaded after the first frame; consume the manifest block `trees.far_mesh`, its per-prototype
    vertex AO and per-placement irradiance when the bake lands: AO x instance RGB x the leaf shader). Until it lands, wire the switch on the 14 near trees (they have meshes and
    impostor prototypes) and prove it walks. Impostor atlas: the 2K variant by default on desktop (`?imp2k=0` reverts).
C3. Shrubs/reeds: LOD1 within 30 m (`?shrublod=`) from the export's LOD1 set (item E) sharing the placement's irradiance; LOD2 beyond.
C4. Capture "round16" with gate4.sh (all six stations, post-off control, tiles, perf, walk) PLUS one bare-URL capture at 1280x720 with NO query string (the lesson of 5e1fffa)
    PLUS a station-2 walk-in shot 3 m from the nearest tree (name the coordinates). Frame time within +3 ms of round 15; report resident memory.
Chrome only through scripts/chrome_run.sh; screenshot.mjs pauses on export/out/bake_queue/status.json (the bake engineer runs GPU jobs this session) — code while it says running.
Commit after every measured step; README QA notes updated for QA 16. Report < 20 lines: per item before/after, the tile paths, what waits on export/bake, per-station ms, commit id.
