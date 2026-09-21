# QA round 25 — the Phase 9 gate on deploy 13 (brief from the lead, 2026-09-20, filled 2026-09-21). Opus 5 xhigh. Fresh agent. No Chrome, no Blender.
Read: docs/qa_round_24.md (the Phase 8 close scores per station; hero 3.97), docs/decisions.md from "Phase 9 session 9 start" to the end (the lighting change at station 2,
the cam03 specular-gating decision, the belt billboard-only rule, the dotted-rim quantiser), docs/briefs/phase9_light_report.md (the shipped sockets and the Cycles
acceptance / hold table), docs/briefs/phase9_bake_analysis_report.md B.6 (the predicted cam03 effect), docs/reviews/phase9_*_review.md carries, docs/quality_checklist.md.
Inputs: the `gate13` capture (renders/web/gate13_cam0[1-6].png, gate13_net.json, gate13_perf.json, gate13m_cam0[1-6].png, gate13_orbit*; 960 px in renders/web/960/);
before = gate12 (QA 24); the Phase 9 Cycles AFTER refs renders/qa_comparisons/cycles_p9/cam0N_1080_32spp.png (rendered by the lead from the re-built master_delivery)
and the Phase 8 BEFORE refs renders/qa_comparisons/cycles_p8/; reference photos per docs/reference_sheet.md; the viewer's own p9_cam03_* flag frames and p9s_* frames.
Gate checks first (CLAUDE.md 2026-09-10): scripts/qa_name_sweep.py on the export set; the six-station full-resolution tile review (3x2 tiles per station at 1920x1080)
BEFORE any number — every visible geometry / material defect listed regardless of the metrics.
Method: (1) Parity per station vs the Phase 9 Cycles refs (viewer within 0.5 of its Cycles score, none below 2.5; QA-17 boxes) and the rubric vs the photo.
(2) Station 2: the shaded-shaft boxes (light_r16 BOXES["02"]) b* / h_ab / R-B in the viewer vs Cycles AFTER vs ref 062 — did the lighting change reach the viewer through
the re-bake (compare against docs/briefs/phase9_light_report.md's per-box table: shade_pier +11.26 / shade_pier_r +5.29 / shade_arch +8.80; frieze +23.3 and soffit h_ab 82.6 are the accepted structural residual, decisions.md 2026-09-21 — score them, do not block on them)? (3) Station 3: near_column and p10 luma, viewer vs Cycles (was 2.55x / p10 38-40 vs 7.3; B.6 predicts ~1.05x);
the belt trees: no mesh belt tree in frame drawn as a magnified card (belt_rule --frustum's two in-frame rows are KEPT meshes), the modulation counters: 166/166 joined, 131 re-lit desktop / 149 mobile, `166 far + 0 near modulated` (the belt rule excludes the 18 near placements; round 1 read 184/184). Known from capture 2 (docs/briefs/phase9_viewer_capture2_report.md): near_column stays 1.44x Cycles in R with the gate (not a specular term — name the owner you think it is), p10 13.3 vs Cycles 6.1; cam05 p10 60.2 gated vs Cycles 64.0 (ungated 68.4) — judge on the tiles which reads closer to the photo and to Cycles.
(4) Stations 2 and 5: the far-crown rim at 100 % (rim index via web/tools/p9v_rim.py ab gate12 gate13; period-2 share) — closed or not.
(5) Regression: hero and 4/6 within 0.5 % MAE outside the changed boxes; payload / perf / resident / page errors restated; mobile gate13m loads and walks.
Scores per station with deltas vs QA 24. Verdict: PHASE 9 GATE PASSED (hero >= 4.0 or not below QA 24 by more than 0.1, no open blocker) or NOT with the named cause and owner.
Write docs/qa_round_25.md (< 70 lines), renders/web/gate13_gate.png (960 px strip: cam02 shaded shafts gate12 | gate13 | Cycles p9 | ref 062; cam03 column shade the same),
append docs/quality_checklist.md; commit only those + scripts/qa_r25_*.py on main with the attribution lines. Report < 12 lines.
