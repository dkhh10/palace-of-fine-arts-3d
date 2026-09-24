# QA round 27 — Phase 10 gate on the Cycles master (brief from the lead, 2026-09-24; dispatched after the Phase 10 merges and the master rebuild). Opus 5 xhigh. Fresh agent. No Chrome. Blender only for the six Cycles station renders if the lead has not rendered them (the lead says which in the dispatch message).
Read: docs/qa_round_26.md (the Phase 9 close: hero 4.05, stations 3.55 / 3.08 / 3.05 / 3.24 / 3.15 — the baseline and its residual list), docs/approach_review_2026-09-24.md (why Phase 10 exists),
docs/decisions.md "PHASE 10 OPENED", the round reports docs/briefs/phase10_projection_report.md (or the projection agent's report section in docs/materials_notes.md "Phase 10 r1"),
docs/briefs/phase10_env_report.md, docs/materials_notes.md "Phase 10 r2" if the water round ran, and the review files docs/reviews/phase10_*.
Inputs: the six Cycles station renders from the rebuilt Phase 10 master (renders/qa_comparisons/cycles_p10/cam0N_1080_32spp.png; the hero also at 64 spp) vs the Phase 9 set
renders/qa_comparisons/cycles_p9/ (same stations, same spp) and the six reference photos of scripts/qa_cameras.py (ref 169 for the hero).
Gate checks first: scripts/qa_name_sweep.py on master.blend; the ray-cast test on the hero arch and the cam03 / cam04 openings (CLAUDE.md gate checks); the six-station
full-resolution tile review (3 x 2 tiles at 1920x1080 minimum) with every visible geometry or material defect listed — new atlas seams, projection ghosting (people,
tree shadows or sky baked into the stone), texel stretching on the columns, crown intersections with the rotunda silhouette.
Method: (1) the projection: attic / drum / column / entablature 100 % crops vs ref 169; the round-9 anisotropy and std-ratio metrics on the same boxes; the round-10b hold table;
column-shaft hue / sat vs ref 169's shafts; cam02 and cam03 seam check; (2) the trees: the NE mass and willow boxes (dark share, sky-through, crown-top row) vs ref 169,
rotunda silhouette untouched; (3) water if round 2 ran: reflection breakup and open-water boxes vs ref 169 with the hold; (4) regression: stations 3, 4, 6 against cycles_p9
(MAE % of range, moved-pixel share; explain every move by a Phase 10 change or flag it).
Scores: the QA-17 rubric, six rows per station, all six stations, deltas vs QA 26; mobile not scored (no web deploy in Phase 10 yet).
Verdict: PHASE 10 GATE PASSED (hero >= 4.05 and no new blocker) or NOT with the named cause and owner; then the residual list for docs/delivery.md "Phase 10".
Write docs/qa_round_27.md (< 60 lines), renders/qa_comparisons/round27_gate.png (960 px: hero crops before | after | ref 169 for attic, column, trees, water), append
docs/quality_checklist.md; commit only those + scripts/qa_r27_*.py on main with the attribution lines. Report < 10 lines.
