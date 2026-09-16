# QA round 15 — Gate 4, round two (brief from the lead, 2026-09-16). Opus 5 xhigh. Fresh agent. Do NOT run Chrome or Blender.
Read: docs/qa_round_14.md (verdict ONE MORE ROUND, items QA-14-1..5, the 6a criteria table, the tile defects), docs/briefs/qa_round_14.md (method + addendum),
docs/briefs/phase6_gate4_r6_viewer.md (what round 15 was allowed to change: water, bloom, cam06/cam03 diagnosis, walk floor, loading denominator), docs/decisions.md from
"2026-09-16 · QA 14 verdict" to the end, web/README.md on the phase6-viewer branch (the "QA notes — read before scoring" section), CLAUDE.md "Phase 6" definition of done 6a and
its stopping rule (6a stops at parity or after two flat QA rounds following Gate 4 — this is the second round).
Inputs: the "round15" capture in the phase6-viewer worktree (six stations Gate 4 look, post-off control, pair sheets, renders/web/tiles/round15/, round15_perf.json, round15_walk.json,
960/round15_loading_screen.jpg), named in the latest docs/status.md entry. References as round 14: Phase 5 hero for station 1, renders/previews/qa/round13_0N_*_cycles.png for 2-6.
Method as round 14 (extend scripts/qa_r14_*.py if they exist, else qa_r13_*): whole-frame ratios, the round-10b boxes, the round-14 boxes for QA-14-1..5, the cam01 six tiles at
100 %, the 6a criteria table, the name sweep restated, score table per station vs round 14, round 13 and Phase 5.
Verdict: 6a PARITY REACHED (every station within 0.5 of Phase 5, none below 2.5, water reflects the rotunda at the hero, walk clamp holds at WATER_Z + 0.1 on every probe, loading
screen with a correct total) or NOT REACHED (name the station and criterion). Then, separately, the round-15 delta per item (closed / improved / flat / regressed with numbers) and
the residual defect list for the delivery notes (docs/delivery.md style: what a viewer of the walkthrough will see that the Cycles frames do not show). Perf: report as measured,
both presets if the capture carries them. No re-bake or geometry request is in scope; note them as post-6a.
Write docs/qa_round_15.md (< 110 lines), renders/web/round15_gate.png (960 px composite), append docs/quality_checklist.md; commit only those + scripts/qa_*.py on main.
Report < 20 lines: the verdict, per-station scores, the per-item delta, the three worst boxes, tile defects, commit id.
