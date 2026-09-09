# QA round 06 — brief from the lead (2026-09-09). Model: Opus 5 xhigh. Read docs/briefs/qa.md (standard round) first.

Round 06 renders the master rebuilt after polish round 4: lighting r12, materials r7, architecture r4, environment r7. What merged
and each owner's measured numbers: docs/status.md entries from "RESUME (new session)" on. Score exactly as rounds 03-05 (same rows,
same boxes, same yardstick overlay on ref 169) so the trend is comparable; docs/qa_round_05.md is the pattern.
Required beyond the standard renders / comparisons / scores / defect list:
1. Status of every QA-05 defect with the number that proves it: QA-05-1 shade (cam03 near shaft / sunlit 0.30-0.70; hero shaded
   attic hue vs 29.5), -2 hero stone (attic lum window 178-201, sat, anisotropy vs 4.07, std ratio >= 0.60), -3 coffer (Cycles
   coffer/sky and darkest/lightest quarter vs 0.265), -4 water (reflection sat vs 0.34, near-water hue 190-200), -5 south wing band,
   -6 entablature row-std vs 53.6, -9/-10/-11 environment items. Measure on the master, not on any owner's branch claim.
2. Gate composite renders/qa_comparisons/round06_gate.png: Cycles hero beside ref 169, six Eevee views, score deltas r05 -> r06,
   trend table r02 -> r06. State the hero delta explicitly (the definition of done in CLAUDE.md turns on it).
3. Every Blender run through scripts/blender_run.sh <max_seconds> -- ... (register honest maxima; Cycles hero 1080p 128 spp 1200 s).
   Do NOT run the 4K timing test this round (Phase 5 item, lead schedules it).
Commit only docs/qa_round_06.md, docs/quality_checklist.md, scripts/qa_*.py, renders/qa_comparisons/round06_*,
renders/previews/qa/round06_* (explicit paths). Touch renders/previews/qa/round06_RENDERS_DONE when every render has exited.
Final report under 60 lines: score table with deltas, trend line per camera, pass/fail lines, top 10 defects (id, owner, one line),
composite path. Numbers, not adjectives.
Added 2026-09-09: 4. cam03 shade test is re-based (docs/decisions.md 2026-09-09): lighting proved the near-shaft box 150 150 420 720 is occluded from the
sky and the anti-sun hemisphere. Measure shade-vs-sunlit on a sky-visible shaded shaft face in the cam03 frame (state the box, same 0.30-0.70 window,
anchored on ref 169's shade/sunlit 0.607) and report both the old box and the new one once. 5. Wing bands: report raw and aligned panels for both
wings with the labels frame-left = SOUTH, frame-right = NORTH. 6. Note which master you scored (object count, build time from renders/logs/lead_build_r6.log).
