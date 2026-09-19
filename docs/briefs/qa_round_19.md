# QA round 19 — Phase 7 foliage look on the live site, the closing round (brief from the lead, 2026-09-19; capture tag filled at dispatch). Opus 5 xhigh. Fresh agent. Do NOT run Chrome or Blender.
Read: docs/decisions.md "2026-09-19 · PHASE 7 APPROVED" (scope A-E) and the Phase 7 merge entry after it (the adopted mesh distance, the mobile settings), docs/briefs/phase7_viewer.md,
the viewer's web/README.md "Phase 7" section on main (before/after numbers and captures), docs/qa_round_17.md §3, §4, §7 (the crown/shrub boxes, reference values, residuals
2 and 3 which this phase claims to close), docs/qa_round_18b.md (the mobile baseline: scores 2.9 / 3.0 / 2.3 / 2.7 / 2.5 / 2.4, resident 499.7 MB), docs/perf_ab_6c.md (the
same-session A/B rule), the user's two screenshots that opened the phase (renders/web/user/phase7_desktop_hero_user.png, phase7_iphone_close_user.png; view at 960 px).
Inputs (the lead names the tag in the latest docs/status.md entry): the `<tag>` capture on the URL by web/tools/gate5.sh (desktop stations 1-6 at 1920x1080, net, 1440p perf,
mobile stations 1-6 at 1170x2532) plus the lead's close-orbit mobile captures `renders/web/<tag>_orbit_*.png`; the round-18b captures (gate5b / gate5c) as the before.
Method: (1) Desktop far trees, the point of the phase: the QA-17 crown boxes at stations 1, 2, 5 (scripts/qa_r17_probe.py, extended to qa_r19_*) — hard-edge share, halo
share, crown p10 vs the reference (must be >= 0.8x; was 0.57x), centre/edge (must keep ~0.39 vs ref 0.364 at cam02), station 5 frame luma (1.00 +- 0.01); 100 % tiles of
the tree bands at 1, 2, 5 beside the round-18b crop and beside the Cycles reference: jagged/dithered silhouettes, pale halo, near-black blotches must be gone or named.
(2) Whole-frame regression: luma and MAE vs round16c at all six stations; every architecture box unmoved (< 3 %); scores on the rubric with deltas vs QA 17/18b.
(3) Perf: 1440p medians vs gate5cold and the viewer's own same-session A/B table; the adopted mesh distance must be inside +3 ms same-session by the viewer's table
(you check the table's arithmetic and that the files exist); resident vs 1 861 MB (+100 MB max). (4) Mobile: the six stations and the close orbit on the rubric and at
100 %: near trees must be meshes within the stated radius (count crowns that are still flat cards inside it), impostor cores no longer black, shrubs LOD1 inside the
radius; resident < 700 MB from the sidecar with the delta from 499.7; tris and draws; 0 page errors. (5) Payload: bytes before the first frame on the URL unchanged
(<= 50 000 000; the phase must not touch tier 0). (6) Name sweep restated. (7) Shrub card STRUCTURE (QA 17 residual 1) is deferred by decision: report it, do not fail on it.
Verdict: PHASE 7 DONE (residuals 2 and 3 closed on the desktop tiles; mobile near trees are meshes with no black cores; no regression; perf and payload inside the rules)
or PHASE 7 DONE WITH RESIDUALS (named, owners) or NOT DONE (a regression, a payload change, a perf breach, or the tiles still show the user's two defects).
Write docs/qa_round_19.md (< 100 lines), renders/web/<tag>_gate.png (960 px composite: desktop tree bands, mobile close orbit), append docs/quality_checklist.md; commit only
those + scripts/qa_r19_*.py on main with the attribution lines at the end of the commit message. Report < 15 lines: verdict, box numbers before/after, tile findings,
mobile findings and resident, perf, payload, commit id.
