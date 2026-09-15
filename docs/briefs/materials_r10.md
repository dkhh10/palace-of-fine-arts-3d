# Materials round 10 — ONE bounded round before Phase 6 Gate 2 (lead, 2026-09-15). Branch `materials`, worktree .claude/worktrees/materials. Opus xhigh.
`git merge main` first (main carries Phase 6; nothing of yours moved). Read docs/briefs/process.md, docs/materials_notes.md (last section), docs/qa_round_10.md
QA-10-8, docs/qa_round_09.md QA-09-8, docs/qa_round_10b.md (the hero boxes = hold list). Lighting is frozen: no edit to assets/lighting.blend or light_*.py.
Scope, nothing else: (A) QA-10-8 dome cap: `ARCH_rotunda_dome` / MAT_dome_membrane reads as an untextured near-white lid (box 920 95 1000 120 on the
1920 hero grid: lum 189.5 / hue 38.0 / sat 0.397 / col-sd 5.1 vs ref 169's 224.3 / 44.1 / 0.272). Give it the real cap: a weathered concrete/plaster
membrane with ridge-and-panel structure and rain streaking, from photos in reference/photos (find the cap in the index: ref 169 and any aerial).
Acceptance: box lum 205-235, hue 38-50, sat 0.22-0.32, col-sd >= 8 (structure, not noise), and a 100 % crop next to the ref crop. (B) QA-09-8 coffer
saucer: MAT_plaster_ceiling field sat 0.341 / MAT_plaster_ceiling_rib rim 0.634 vs window 0.38-0.50 (ref 083: 0.427 / 0.438), by
`scripts/mat_r9_measure.py coffer` on a cam04 Cycles frame; land both in window with the coffer ratio (round-10b: 0.347) held within 0.02.
Renders (the GPU is shared with the Phase 6 export queue; a job of yours starts only when `ls ~/.cache/pfa_blender_watchdog` shows no live pid but
your own — check in a separate command, never poll in turns): rebuild master in your worktree (scripts/lead_build.sh), then ONE Cycles hero
1920x1080 64 spp (max 900 s) and ONE cam04 1280x720 64 spp (max 600 s) through scripts/blender_run.sh; the QA box tools as in round 9b.
Hold list (hero, round 10b, +-2 lum / +-2 deg / +-0.02 sat): sunlit attic 186.1 / sat 0.520 / R-B +117; shaded attic 121.3 / 41.3 / 0.633;
reflection 126.8; near water 123.9 / 205.7; vault field 60.5; jamb hue 24.0. Report < 25 lines: before / after / ref per box, the crops, the
hold table, files changed (assets/materials.blend, scripts/mat_*.py, docs/materials_notes.md only), last commit id.
