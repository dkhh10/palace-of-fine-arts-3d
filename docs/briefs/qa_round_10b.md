# QA round 10b — hero tile re-check after the two blockers (brief from the lead, 2026-09-10). Model: Opus 5 xhigh. Read docs/briefs/qa.md, CLAUDE.md gate checks.
Master rebuilt after: floating gulls removed (QA-10-1), LIGHT r18 (rotunda ceiling field 103 -> 61 via bay weights) and the lead's shade-fill-off
(QA-10-2 jamb: LIGHT_shade_fill energy 49 -> 0; expected: jamb hue ~26, hero shaded attic hue ~41 / sat ~0.53 = outside its window, cam02 pier warm).
Renders: Cycles hero 1920x1080 128 spp (max 1500) -> renders/final/v2/qa_round10b_cam01_cycles.png; Eevee cam01/02/03 (max 600). Nothing else.
1. Name sweep + the two ray tests as round 10 (scripts/qa_r10_rays.py).
2. Six 100 % tiles of the Cycles hero, each viewed: the round-10 tile list re-stated with FIXED / OPEN per item; new defects added.
3. The QA-10-2 acceptance boxes (vault field 900 380 1010 430 in 45-65; jamb 872 400 892 480 hue 25-60, R-B > 0) and the moved holds stated
   (shaded attic lum/hue/sat, sunlit attic, sky, reflection, entablature, columns) against their windows; cam02 pier / soffits, cam03 near column.
4. Hero score with delta vs 3.56 (round 10) and 3.67 (round 09), the arch 1:1 pair vs ref 169, composite renders/final/v2/round10b_gate.png.
   Verdict line: tile review PASS / FAIL (a FAIL names the blocking tile defect + owner). The lead renders the 4K v2 only on PASS.
Commit only docs/qa_round_10b.md, docs/quality_checklist.md, scripts/qa_*.py, renders/final/v2/round10b_*, renders/final/v2/qa_round10b_*.
Touch renders/final/v2/round10b_RENDERS_DONE when every render has exited. Report under 30 lines.
