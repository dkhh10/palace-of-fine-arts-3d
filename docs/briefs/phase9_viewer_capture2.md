# Phase 9 viewer capture 2 — the round-2 specular gate on the re-baked assets (brief from the lead, 2026-09-21). Opus 5 high. Fresh agent.
Branch `phase9-viewer-capture2` from main (dfb284b or later), worktree .claude/worktrees/phase9-viewer-capture2. Read docs/briefs/process.md, docs/briefs/phase9_viewer_capture.md
(the previous window: its settings, the gate5 look query, the MAE method) and its report docs/briefs/phase9_viewer_capture_report.md (set B is the round-1 table you
compare against), docs/reviews/phase9_viewer_shade_r2_review.md (finding 5: without sky.diffuse_lobes the r2 gate is OFF — MAIN's gate5 manifests now carry it), and
docs/briefs/phase9_rebake_report.md section 3 (what the re-bake changed: new lightmaps, new sky constants (2.197, 3.361, 5.825), env.glb re-exported).
The GPU is FREE and yours for this window: no Blender may start; check `pgrep -fl "MacOS/Blender|headless"` is empty before each Chrome run; every run through
`scripts/chrome_run.sh <honest seconds> -- node web/tools/screenshot.mjs ...`. Assets: MAIN's export/out is now the PHASE 9 bake and `web/dist` is built from
main d1ac476+ with the constants in export/out/gate5 — serve/capture from MAIN as the previous window did (the local dist + MAIN's export/out; read-only, write
nothing into export/out). Do not run manifest_v4 or tiers: the pack chain already did, and re-running would touch the deploy set.
Frames (1920x1080, --frames 0, the gate5 look query from the previous brief):
A. Stations 1-6 gate ON (default) -> renders/web/p9s2_cam0N.png; station 3 with `--query specgate=0` (Phase 8 path) -> p9s2_cam03_specgate0.png and with
   `--query specgate=1` (round 1) -> p9s2_cam03_specgate1.png; station 5 with specgate=0 -> p9s2_cam05_specgate0.png (the sunlit regression control).
B. `?tier=mobile` stations 1-6 -> renders/web/p9s2m_cam0N.png.
Measures: per station MAE vs the NEW Cycles refs renders/qa_comparisons/cycles_p9/cam0N_1080_32spp.png (whole frame; and outside shade / in the Cycles-sunlit band
as the previous report defined them) — this is the parity table QA 25 will read; per station MAE vs gate12 (deploy 12) for the size of the total Phase 9 change;
station 3 near_column and p10 luma for specgate 0 / 1 / 2 vs Cycles p9 (export/p9_shade_terms.py --boxes --viewer <frame> --cycles <cycles_p9 cam03>);
station 5 p10 and mean for specgate 0 vs 2 (the round-1 regression must be gone: p10 within 3 % of Cycles p9); the boot log's modulation line and
activateImpostorMeshes re-lit counts (expect 166/166 and 131 desktop / 149 mobile: the belt rule is packed now); page errors count; the sidecar's gate state.
Output: 960 px copies under renders/web/960/ committed; full-size PNGs not added (gitignored or left untracked). Write docs/briefs/phase9_viewer_capture2_report.md
(< 30 lines: the parity table, the specgate A/B, the counters) and commit it on your branch. No deploy, no edits to web/src, no Blender. Final message: the report
and the last commit id.
