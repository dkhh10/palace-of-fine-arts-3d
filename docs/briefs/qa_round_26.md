# QA round 26 — verification of the ENV R3 backdrop tiles on deploy 14 (brief from the lead, 2026-09-22). Opus 5 xhigh. Fresh agent. No Chrome, no Blender. Short round.
Read: docs/qa_round_25.md (the Phase 9 gate: PASSED, hero 4.05; its residual list is the baseline — nothing there is re-scored unless the tiles touch it), docs/briefs/phase9_env_report.md
item 1 (the tiles, the Eevee/Cycles hf gains, the named cam01/cam05 regression), docs/briefs/phase9_backdrop_export_report.md incl. "## Capture (lead's window)" (the viewer
ON/OFF table: cam06 hf +16.0 / +36.7 / +37.2 %, stations 3/4 unmoved, the gain-off build reproduces deploy 13), docs/reviews/phase9_backdrop_export_r2_review.md carries.
Inputs: the `gate14` capture (renders/web/gate14_cam0[1-6].png, gate14m_*, gate14_orbit*, sidecars; 960 px in renders/web/960/); before = gate13 (QA 25); the round26_* 960 px
frames and crop pairs; Cycles refs renders/qa_comparisons/cycles_p9/ (the tiles are in the Cycles master too, but those refs predate ENV R3 — say so where it matters);
the new 4K hero renders/final/hero_cam01_3840x2160_128spp.png (rendered on the ENV R3 master; the lead's tile pass noted a thin dark band above the right colonnade
entablature at 4K — inspect that band at 100 % and say what it is and whether deploy 14 shows it).
Gate checks first: scripts/qa_name_sweep.py on the export set (the four tile KTX2 are new rows); the six-station tile review at 100 % — every visible defect listed.
Method: (1) cam06 city band at 100 %: do the tiles read as facade / roof / canopy texture or as noise, moiré or a repeat lattice; hf vs Cycles r09 and vs ref 105 (the R1 ceiling
4.3x is known — score the improvement, not the ceiling); (2) stations 1, 2, 5 backdrop bands: only backdrop pixels and reflections move (MAE ON vs OFF < 0.5 % elsewhere; report
what you measure); (3) regression: stations 3 and 4 byte-close to gate13; payload / perf / resident / page errors restated (first frame 49.31 / 47.68 MB); mobile gate14m loads
and walks; (4) the 4K hero band note above. Scores per station with deltas vs QA 25 (only station 6 and the backdrop bands may move; the hero must not drop below 4.0).
Verdict: PHASE 9 CLOSE CONFIRMED (no new blocker, hero >= 4.0) or NOT with the named cause and owner.
Write docs/qa_round_26.md (< 50 lines), renders/web/gate14_gate.png (960 px: cam06 city band gate13 | gate14 | Cycles | ref 105), append docs/quality_checklist.md; commit only
those + scripts/qa_r26_*.py on main with the attribution lines. Report < 10 lines.
