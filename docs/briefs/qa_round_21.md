# QA round 21 — Phase 8 item 8b (the band-atlas far trees) on the live site, plus regression (brief from the lead, 2026-09-19). Opus 5 xhigh. Fresh agent. No Chrome, no Blender.
Read: docs/decisions.md from "8b decision 2" to the end (the band atlas contract, the QA 20 findings, the session-7 close), docs/qa_round_20.md (the before: scores
3.78 / 3.25 / 2.75 / 2.88 / 3.06 / 2.89, mobile 3.2 / 3.3 / 2.4 / 2.7 / 2.8 / 2.5; §2 crowns; the dot grid at 100 %; the walk-in shrub-set bug; the resident counter),
docs/briefs/phase8b_band_atlas.md (the contract), docs/briefs/phase8b_bake_report.md (frame pitch, the willow clip), web/README.md "Phase 8b" band sections on main
(share 0.10, the crossings table, the willow 1.6 % clip note), docs/reviews/phase8_viewer_r2_review.md (the resident 3 553 vs 1 863 explanation), docs/qa_round_17.md §3
(crown/shrub boxes and reference values), docs/briefs/qa_round_20.md (the method you extend).
Inputs: the `gate9` capture on the URL after deploy 9 (renders/web/gate9_cam0[1-6].png at 1920x1080, gate9_net.json, gate9_perf.json + gate9_perf_shot.json at 1440p,
gate9m_cam0[1-6].png, gate9m_net.json; 960 px copies in renders/web/960/). Before = the gate8 set (round 20). Cycles references and the reference photos as in round 17.
Method (scripts/qa_r20_* extended to qa_r21_*; export/p8_atlas_probe.py viewer as-is): (1) CROWNS, the point of the round: crossings per 100 px at the QA-17 crown boxes
at 1, 2, 5 vs Cycles (11.73 / 7.76 / 15.89) and vs gate8 (7.99 / 6.97 / 8.53), centre/edge, level, p10; the station-2 crown tile as a three-way strip at 100 %: Cycles |
gate8 (2K) | gate9 (band) — does the crown now show limbs and sky, or is it still a mass; the hero crown at 200 %: is the QA-20 ordered dot grid gone at share 0.10 (check
every far crown against the sky at 100 % on 1, 2, 5, 6, not only the hero); band-frame seams or popping between azimuth frames visible at any station (compare the two
captures for crowns that changed shape, not only tone). (2) WILLOWS at the water's edge (1, 2, 5): flat white highlights on the body from the 1.6 % clipped texels —
measure the p99 luma of the willow boxes vs Cycles and gate8 and say whether the `PFA_BAND_RANGE=band` re-bake (10 min GPU) is needed. (3) Regression vs gate8: luma /
MAE at all six stations; architecture boxes unmoved (< 3 %); the shrub boxes from round 20 restated (they must not move; the band does not touch them). (4) Rules:
payload before the first frame on the URL (<= 50 000 000; the export states 49 393 776 desktop / 47 629 409 mobile); perf vs gate8 (drift caveat; the walk-in shrub set is
STILL drawn at every station in this deploy — the viewer fix round runs in parallel — report the medians, do not re-fail on it); resident from the sidecar, stated with the
caveat that the counter omits the impostor atlases (report the sidecar figure and the corrected estimate = sidecar + the band's 67 MB + the 2K atlases' 48 MB, and name it as
an estimate). (5) Mobile: the export says tier-mobile is byte-identical to gate8 — verify with MAE at the six stations (expect ~0) and say so; resident vs round 20.
(6) Name sweep restated (scripts/qa_name_sweep.py on the export set, as in rounds 19-20).
Scores on the rubric per station, desktop and mobile, with deltas vs QA 20. Verdict: 8b CLOSED (station-2 crown has structure, no dot grid at 100 %, no willow highlight, no
regression, rules hold) or 8b NOT CLOSED with the named fix (share value, the willow re-bake, or a seam fix) and its owner.
Write docs/qa_round_21.md (< 110 lines), renders/web/gate9_gate.png (960 px composite: the station-2 three-way crown strip, the hero 200 % crop, one willow box),
append docs/quality_checklist.md; commit only those + scripts/qa_r21_*.py on main with the attribution lines. Do not touch any other file. Report < 15 lines:
verdict, crown numbers before/after vs Cycles, the dot-grid finding, the willow finding, scores, payload, perf, resident (sidecar + estimate), commit id.
