# QA round 20 — Phase 8 items 8a (shrubs), 8b part 1 (2K crowns + coverage), 8c (column projection) on the live site (brief from the lead, 2026-09-19). Opus 5 xhigh. Fresh agent. No Chrome, no Blender.
Read: docs/decisions.md from "PHASE 8 APPROVED" to the end (what each item changed and why; the accepted budget exception; the band atlas is NOT in this deploy), docs/qa_round_19.md
(the before: scores 3.78 / 3.25 / 2.63 / 2.88 / 3.06 / 2.83, mobile 3.2 / 3.3 / 2.3 / 2.7 / 2.8 / 2.4, residual list), docs/qa_round_17.md §3 (the shrub boxes at 1/2/3/5 with reference
values: leaf-green share ~0.5x, hard-edge share, level, hue) and §4 (cam03 column blur/banding), docs/briefs/phase8a_env_report.md, phase8b_bake_analysis.md, phase8c_export_analysis.md,
web/README.md "Phase 8b" / "Phase 8 far-tree A/B" / "Phase 8c" sections on main, export/README.md "Phase 8a".
Inputs: the `gate8` capture on the URL (renders/web/gate8_cam0[1-6].png, gate8_net.json, gate8_perf.json, gate8m_cam0[1-6].png, gate8m_net.json, gate8_orbit_*.png if present; 960 px
copies in renders/web/960/); the before = the gate7 set; the Cycles references and the reference photos as in round 17; the shipped-state tiles the viewer committed (p8k2, p8cproj).
Method (scripts/qa_r17/r19 probes extended to qa_r20_*): (1) SHRUBS, the point of 8a: the QA-17 shrub boxes at 1, 2, 3, 5 — leaf-green pixel share vs the reference photo (target: from ~0.5x
toward 1.0x), hard-edge share (must not rise above the reference), level and hue (must hold); 100 % tiles of the shore band at 1, 2, 3, 5 beside the gate7 crop and the reference: is the band a
continuous mass of small varied foliage or still angular slabs; at 3 m (station 3) the LOD1 walk-in set. (2) CROWNS (8b part 1): the crown boxes at 1, 2, 5 — crossings per 100 px
(export/p8_atlas_probe.py viewer), centre/edge, level, p10; 100 % tiles vs Cycles: edge fringe, halftone/dot texture at 200 % (must be absent at the shipped share 0.15), sky through the
crown; state plainly whether the crown reads as twigs or a mass (the band atlas is the next round's answer, not this one's). (3) COLUMNS (8c): cam03 100 % tile at the near column vs gate7
and the reference: vertical smear gone, grain and pores present, no flute seam; cam03 frame luma. (4) Regression: luma/MAE vs gate7 at all six stations; architecture boxes unmoved
(< 3 %); payload before the first frame on the URL (<= 50 000 000; expected ~49.4 MB — the env_t0 group grew); perf vs gate7 with the drift caveat; resident (expect ~+48 MB for the 2K
atlases; report). (5) Mobile: six stations + orbit vs gate7m/gate7_orbit — the mobile draws LOD2 shrubs (densified) and 1K atlases (unchanged); resident vs 561.9 MB. (6) Name sweep.
Scores on the rubric per station, desktop and mobile, with deltas vs QA 19. Verdict: items 8a / 8c CLOSED or NOT (each), 8b part 1 improvement measured (closure waits for the band atlas).
Write docs/qa_round_20.md (< 110 lines), renders/web/gate8_gate.png (960 px composite: shrub bands, crowns, the cam03 column), append docs/quality_checklist.md; commit only those +
scripts/qa_r20_*.py on main with the attribution lines. Report < 15 lines: verdict per item, shrub box numbers before/after vs reference, crown numbers, column tile finding, scores, payload, perf, resident, commit id.
