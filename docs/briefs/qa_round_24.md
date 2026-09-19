# QA round 24 — verification of the far-tree irradiance re-key on deploy 12 (brief from the lead, 2026-09-19). Opus 5 xhigh. Fresh agent. No Chrome, no Blender. Short round.
Read: docs/qa_round_23.md (the blocker: far-tree crowns against backgrounds +4-16 % after the r2 re-bake, 7/10 boxes away from the Phase 8 Cycles refs, 8e blade p90 22.7 -> 25.2 px;
its box set and scripts/qa_r23_probe.py), docs/decisions.md "QA 23" entry and the phase8d-export3 merge (2be3817: the 127 existing rows restored from the 6c bake, median
modulation 0.9415; the 39 belt rows keep the r2 bake, median 0.2424), docs/qa_round_21.md (the far-crown numbers before Phase 8's belt: crossings 11.97 / 7.35 / 11.67).
Inputs: the `gate12` capture (renders/web/gate12_cam0[1-6].png, gate12_net.json, gate12_perf.json, gate12m_cam0[1-6].png, gate12m_net.json, gate12_orbit*.png/json; 960 px in
renders/web/960/); before = gate11 (QA 23) and gate10 (QA 22, the pre-re-bake far-tree look); Phase 8 Cycles refs renders/qa_comparisons/cycles_p8/960/.
Method (scripts/qa_r23_probe.py re-run as qa_r24): (1) the QA-23 far-tree box set at 1/2/5/6: level vs the Phase 8 Cycles refs and vs gate10 (the 127 existing crowns must
return to their gate10 values within 3 %; the 39 belt trees at cam02/cam05 are a separate population — report their level and say whether they read as shaded trees or
as black cut-outs at 100 %); the mean deviation from the Cycles refs (was 6.7 % pre-re-bake, 9.7 % after; expect the former); dark cores back. (2) 8e on the orbit: blade run
p90 per box (was 22.7 px at gate10, 25.2 at gate11; 5/6 boxes <= 25 expected again). (3) Regression vs gate11 with the water mask: everything but the far trees byte-close
(MAE < 0.5 % outside the far-tree boxes); architecture boxes unmoved; payload / perf / resident / page errors / name sweep restated. Scores per station with deltas vs QA 23
(only stations with far trees in frame may move). Verdict: BLOCKER CLOSED (Phase 8 art items all closed, no open blocker) or NOT with the named cause and owner.
Write docs/qa_round_24.md (< 60 lines), renders/web/gate12_gate.png (960 px: one far-crown strip gate10 | gate11 | gate12 | Cycles at cam02, the orbit crown), append
docs/quality_checklist.md; commit only those + scripts/qa_r24_*.py on main with the attribution lines. Report < 10 lines.
