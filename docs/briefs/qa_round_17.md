# QA round 17 — the 6c foliage gate, round two of two (brief from the lead, 2026-09-17). Opus 5 xhigh. Fresh agent. Do NOT run Chrome or Blender.
Read: docs/qa_round_16.md (your predecessor: the verdict, the three open items with owners, the shrub/crown boxes and their reference values, the tile defect list, the memory
finding), docs/briefs/qa_round_16.md (method + addendum), docs/briefs/phase6c_viewer_r3.md and phase6c_export_r3.md (what round 2 was allowed to change: crown interior term,
shrub level/edges after the DiffCol albedo check, walk-up LOD1 glb), docs/decisions.md from "2026-09-17 · QA 16 (8cf34ec)" to the end, export/out/gate3/foliage/albedo_check.json
(the albedo verdict), web/README.md on main (QA notes for QA 17), CLAUDE.md "Phase 6" gate checks and the 6c stopping rule (two rounds maximum: this is the last).
Inputs: the "round16c" capture on main (six stations, post-off control, pair sheets, perf, walk, bare URL, the station-2 walk-in), named in the latest docs/status.md entry;
full-resolution tiles in .claude/worktrees/phase6-viewer/renders/web/tiles/round16c/ (read-only) plus your own 100 % tiles cut from renders/web/round16c_cam0N.png.
Method: scripts/qa_r16_probe.py / qa_r16_gate.py extended to qa_r17_*; the same boxes as round 16 (shrub/reed at 1/2/3/5, crown interior/rim at 2 and 5, the far-tree and
near-tree boxes, the hero boxes), the six-station tile review, the name sweep restated, the bare-URL check, the walk-in judged as a tile, perf and resident memory.
Score table per station vs round 16, round 15 and Phase 5. Verdict: 6c ACCEPTED (no station below its round-15 score by more than 0.1, station 2 above round 15, perf within
+3 ms of round 15, and the tiles show crowns with interior and shrubs at the reference level) or 6c CLOSED WITH RESIDUALS (the two-round rule stops polishing either way; name
every residual with its owner and the one-line fix for docs/delivery.md). Write docs/qa_round_17.md (< 120 lines), renders/web/round16c_gate.png (960 px composite), append
docs/quality_checklist.md; commit only those + scripts/qa_*.py on main, attribution line at the end of the commit message.
Report < 20 lines: the verdict, per-station scores with deltas, the crown and shrub boxes vs round 16 and the reference, tile defects, perf and memory, commit id.
