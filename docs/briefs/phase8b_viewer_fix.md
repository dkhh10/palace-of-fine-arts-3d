# Phase 8b viewer fix round (brief from the lead, 2026-09-19). Opus 5 high. Fresh agent. Branch `phase8b-viewer` from main, worktree .claude/worktrees/phase8b-viewer.
Read first: CLAUDE.md (Phase 6 machine rules), docs/qa_round_20.md (the bug and the counter finding, §"walk-in", §resident), docs/reviews/phase8_viewer_r2_review.md
(the resident 3 553 vs 1 863 explanation), web/README.md "Phase 8b" sections and "Performance" / "Capturing a gate 5 round" / "Screenshots and the gate passes",
docs/perf_ab_6c.md (the same-session A/B rule), export/README.md "Phase 8a" (env groups, the shrub LOD sets, which set the stations draw).
Three items, in order, each its own commit:
(a) BUG: `env_shrubs.glb` (the 6c LOD1 walk-in shrub set, 463 922 tris) is drawn in full at every station although `shrubLod` reports lod1:0 — +1.12 M triangles per
    frame at the five water stations, on mobile too. Find why the distance gate does not hide it (a frustum/visibility flag, a group that bypasses the LOD switch, an
    instanced mesh whose count is never reduced, a stale `?` default — measure, do not guess: count the drawn triangles per group with the renderer info at each station
    before and after). Fix so that the LOD1 set draws only inside its walk-in radius. Re-measure 1440p perf at stations 1-6 SAME-SESSION before/after (web/tools perf
    capture, `?` switch to restore the old behaviour for the A/B), desktop and `?tier=mobile`; tris and draws per station in the table.
(b) `resident()` never counts the impostor atlases (custom uniform textures; the 1K/2K albedo, normdepth, and the 16 band atlases). Count every GPU texture the renderer
    holds (walk `renderer.info.memory` plus the custom uniforms' textures by their KTX2 dimensions/levels) and restate the figure of record in the README perf table and
    the `__pfaInfo()` sidecar schema; give old vs new at the hero (gate9 sidecar 1 862.9 MB; the bake says the band is 67 MB, the 2K atlases 48 MB).
(c) Blue-violet tint on shaded stone at desktop cam02 (the probe tint; QA 20 carry). Measure: mean chroma (a*, b* in Lab, or hue/sat) of the QA-17 shaded-stone boxes at
    cam02 in the gate9 capture vs the Cycles reference render and the reference photo; locate where the tint enters (the irradiance probe SH encoding, the LUT, the
    lightmap decode, the sky-branch equirect) by switching each `?` lighting/post flag and re-measuring. PROPOSE the fix with numbers; implement it ONLY if it is a viewer-
    side encoding/decoding error (a wrong coefficient, a wrong colour space). Anything that changes the frozen Phase 5 look (assets/*.blend materials or lighting, or a
    tone tweak that is not restoring parity with Cycles) is a proposal for the lead, not a change.
Rules: Chrome only through `scripts/chrome_run.sh <max_seconds> -- <cmd>` and only after `pgrep -fl "MacOS/Blender|headless"` is empty and export/out/bake_queue/status.json
says idle (check both before every run; two other agents are CPU-only this session). No Blender. Never deploy (the lead deploys after review). Do not edit
export/out or export/*.py; if a fix needs the export, write the exact change to the report and stop that item. Tests green (`npm test` in web/). Commit after every item
or every 15 minutes with the attribution lines. Write web/README.md "Phase 8b fix round" (a/b/c: cause, fix, before/after tables, the `?` switches) and
docs/briefs/phase8b_viewer_fix_report.md (< 60 lines). Report to the lead < 15 lines: per item the cause, the fix or the proposal, perf before/after per station, the
restated resident figure, the cam02 tint numbers, commit ids.
