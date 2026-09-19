# QA round 22 — Phase 8 items 8a (relight + shrub-card UV scale), 8d (backdrop), 8e (mobile leaf cards) + the fix round, on the live site (brief from the lead,
2026-09-19; capture tag filled at dispatch). Opus 5 xhigh. Fresh agent. No Chrome, no Blender.
Read: docs/decisions.md from "8a decision 2 (re-scope)" to the end (every change in this deploy and its accepted numbers: the relight's constraints as reframed in the
"Relight review r4" entry; 8a-3 k = 2 shrubs / shrub_dry ku 1 kv 2 / reeds 1; 8d R1+R2 targets; 8e ku 2 / kv 3 with solved cutoffs; the fix round's shrub cull and resident
counter; the water-reflector A/A caveat), docs/qa_round_21.md (the before: scores 3.89 / 3.31 / 2.75 / 2.88 / 3.12 / 2.95, mobile 3.2 / 3.3 / 2.4 / 2.7 / 2.8 / 2.5;
the dotted-rim residual), docs/qa_round_20.md §shrubs (the eight boxes, the leaf-green share now a REPORT figure, not a gate), docs/qa_round_17.md §3/§4, docs/qa_round_19.md
§4 (the mobile leaf-blade finding this round closes or not), docs/briefs/phase8a_relight_report.md, phase8a3_shrub_cards_analysis.md, phase8d_env_report.md,
phase8e_analysis.md, the export chain report the lead names, web/README.md "Phase 8a" / "Phase 8b fix round" / "Phase 8e".
Inputs: the `<tag>` capture on the URL (desktop 1-6 at 1920x1080, net, 1440p perf sidecar, mobile 1-6, the mobile close orbit `<tag>_orbit_*.png`); before = gate9 / gate9m and
gate7_orbit; Cycles references and reference photos as in round 17. Because the planar reflector is not session-reproducible, every viewer-vs-viewer pixel claim at a water
station uses a mask above the waterline (state the mask).
Method (scripts/qa_r21_* extended to qa_r22_*): (1) SHRUBS (8a + 8a-3): the eight QA-17 boxes — level (within 3 % of gate9), hard-edge (no new crossing, no box moving more
than 0.3 points), leaf-green share (report), hue; 100 % tiles of the shore band at 1, 3, 5: Cycles | gate9 | now — are the cards lit-and-shaded bushes with small varied
leaves, or still gold cut-outs / magnified confetti; the 25 m LOD switch at cam05 (is it visible?). (2) BACKDROP (8d): the hero r2c1 N-colonnade band at 100 % vs ref 169
(dark tree belt with light through the gaps, hall roofline above; no floating crowns, no gap under a crown); cam05 band; cam06 top rows vs ref 105 — luma, saturation,
hf detail before/after; any seam or tiling on the city blocks; the far-ground lawn not washed out. (3) MOBILE (8e): the close orbit at 37-45 m — blade run width p90 per
species (target <= 25 px, was 26-36), coverage of the crowns vs gate7_orbit (no thinning), the walk-up at 2.5 m; the six mobile stations vs gate9m (nothing else may move
except the shrub cards and the backdrop). (4) FIX ROUND: draws/tris per station vs gate9 (shrub set culled: hero -1.41 M, cam06 -2.02 M); resident from the sidecar = the
new figure of record (compare with 1 814.2 "before fix 2"); one paired 1440p run for the band third-frame drop (must not be slower). (5) Regression: luma/MAE vs gate9 at
all six stations with the water mask; architecture boxes unmoved (< 3 %); far crowns unchanged (crossings within 0.3 of QA 21); the QA-21 dotted rim restated. (6) Rules:
payload before the first frame (<= 50 000 000; the export states the tier-0 delta), perf medians vs gate9, 0 page errors, name sweep on the export set.
Scores per station, desktop and mobile, deltas vs QA 21. Verdict per item: 8a CLOSED / NOT (on the tiles, with the leaf share reported), 8d CLOSED / NOT, 8e CLOSED / NOT,
fix round VERIFIED / NOT; any regression is a blocker with its owner. Write docs/qa_round_22.md (< 120 lines), renders/web/<tag>_gate.png (960 px composite: the shore
band strip at 5, the hero N-colonnade band vs ref 169, the cam06 city, the mobile orbit crown), append docs/quality_checklist.md; commit only those + scripts/qa_r22_*.py
on main with the attribution lines. Report < 15 lines.
