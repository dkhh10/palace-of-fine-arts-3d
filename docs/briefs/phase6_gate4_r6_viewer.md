# Phase 6 Gate 4 — round 6, the one bounded polish round after QA 14 (lead, 2026-09-16). Branch `phase6-viewer`. Opus high. Same agent as round 5 if still in session, else fresh.
Read: docs/qa_round_14.md (whole file: verdict ONE MORE ROUND, items QA-14-1..5, the 6a criteria table, tile defects), docs/decisions.md from "2026-09-16 · Gate 4 frame rate" to the end,
web/README.md (yours), docs/qa_round_10b.md (the hero boxes), reference: renders/previews/qa/round13_0N_*_cycles.png and the Phase 5 hero.
Scope, in this order, each measured against the QA-14 numbers before and after, no other look change:
1. QA-14-1 water at cam01: ripple structure (open-water std 0.97 vs 13.23; row/col 0.72 vs 3.24), level 0.57x, hue 200 vs 145°, sat 8x, Fresnel flat ~41 where the reference falls
   96.5 -> 60.4 toward the near edge, and the reflection stopping along a hard line. Work with the Phase 5 water material's own numbers (docs/reference_sheet.md material catalog,
   assets/materials.blend MAT_water_* parameters as read by the export: murk, ripple scale/amplitude, roughness) — the ripple normal map must break the reflection into streaks
   the way Cycles does, not blur it; Fresnel by the Schlick term on the true view angle; the hard reflection edge is a clip-plane or frustum bug, find it. Acceptance: open-water
   std within 0.5x-2x of 13.23, hue within 20°, Fresnel gradient sign and magnitude right, no hard line at 100 %.
2. QA-14-4 bloom: threshold/radius so the hero keeps its contact shade (capital-row std >= 0.85x of Cycles, S-colonnade mid >= 0.7x, sunlit-attic sat hold back to >= 0.89x)
   while the dome-cap halo and the leaf-edge fireflies go; measure the presented ms (a smaller radius buys part of the frame budget).
3. QA-14-3 cam06 lower frame (p10 9.7 vs 65.6, near ground 0.53x, far terrain sat 3.7x) and QA-14-2 cam03 shade (1.67x, p10 39.8 vs 7.3): diagnose with __pfaPick which surfaces
   carry the error (terrain vertex irradiance? probe irradiance on the far terrain? the mist on the near ground?) and fix only what is viewer-owned; report the rest as bake/export.
4. Minors: walk floor (3 of 24 probes at −1.225 m, 25 mm below WATER_Z + 0.1 — raise the clamp), loading-screen denominator (planned 522.3 vs loaded 639.0 MB: count what is
   actually fetched), restore the "QA notes — read before scoring" section in web/README.md and keep it (it was lost twice).
5. Capture "round15" with web/tools/gate4.sh (same set as round14: six stations, post-off control, pair sheets, cam01 tiles under renders/web/tiles/round15/, perf json, walk json,
   loading screen at 960 px). Commit after every measured step. Chrome through scripts/chrome_run.sh only; the GPU is free.
Report < 20 lines: per item before/after numbers, what was reported to other owners, per-station ms, last commit id.

## Resume (lead, 2026-09-16 session 4). Fresh agent, Opus high, worktree `.claude/worktrees/phase6-viewer` at 2dab197 (WIP, tree clean).
Read first: `git log -1 --format=%B 2dab197` (the exact state of the water rebuild: what is on by default, what failed, the next lever), then the brief above, docs/qa_round_14.md,
docs/decisions.md from "2026-09-16 · QA 14 verdict" to the end, web/README.md. The two earlier viewer engineers' items 1-3 + 5 of round 5 are merged; the round-5 review's seven
fix-now items are closed at 1e9d2be — do not redo them.
Item 1 continues, in this order, and then STOP and report (the lead judges the open-water tile before items 2-5):
 a. Murk to the reference sheet's MAT_water_lagoon (docs/reference_sheet.md material catalog line: absorption 0.04/0.07/0.04 over 1.5 m to a muddy bottom 0.12/0.10/0.06; the
    WIP message computes the current murk ~5x too dark, ~10x too saturated). Derive the upwelling term from those numbers (Beer-Lambert over the two-way depth, bottom albedo),
    not by tuning to the metric; re-measure with web/tools/water_probe.py (lum 118, hue 145°, sat 0.041, Fresnel 96.5 -> 60.4 toward the near edge are the targets).
 b. Capture cam01 fresh and cut the 100 % open-water tile to renders/web/960/qa14_1_openwater_100pct.png (also the same crop of the Phase 5 hero beside it, one composite,
    960 px wide) — this is what the lead judges. Report the before/after table (rowHF, row/col, lum, hue, sat, Fresnel) and the composite path, then stop.
Chrome only through scripts/chrome_run.sh; a bake engineer runs a short GPU job early this session — screenshot.mjs pauses on export/out/bake_queue/status.json, so if a capture
refuses, do code work and retry; no perf measurement while that file says running. Commit after every measured step.
Queued after the lead's judgement (do not start yet): items 2-5 above, plus item 1c: consume `lightmaps.instance_irradiance` (manifest block per docs/decisions.md "PER PLACEMENT"
entry) as an InstancedBufferAttribute on the 28 shrub/reed card meshes — exactly like the ORN slot offsets — replacing the probe irradiance for those materials only; it lands
in env.glb/manifest after the export engineer's re-export (the lead tells you when).
