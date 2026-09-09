# QA round 08 — brief from the lead (2026-09-09). Model: Opus 5 xhigh. Read docs/briefs/qa.md first; docs/qa_round_07.md is the pattern.

Round 08 renders the master rebuilt after: the round-08 stations (cam01 at 2.6 m over the water = z 1.3, per your item 5; cam02 at your fitted
NNE station (-79.8, 24.4, 1.55) -> (0, 0, 23.5) 40 mm), lighting r15 (lagoon horizon term, hero shade level, cam03 row, cam02 boxes re-based),
materials r9 (THE photo-projection pass on the hero-facing stack + mirror level + lagoon sheen + coffer rim), ornament r8 (capital presets,
re-baked) if merged. What merged and every owner's numbers: docs/status.md from "Session restart" to the end.
Required beyond the standard renders / comparisons / scores / defect list:
1. Re-base first. cam01 moved 0.30 m down and cam02 moved to the other side of the building: re-run the aligned overlay (qa_silhouette.py align,
   crops as round 07; the lead's pre-registration is renders/qa_comparisons/round08pre_cam01_aligned_vs_ref169.png) and state whether any
   round-07 box on the hero (light_r10_measure / qa_r07_measure boxes) needs a row shift; if so shift, say by how much, and use the shifted
   boxes for every number this round. cam02: new boxes on the new frame (lighting r15 re-based its four; use theirs), ref 062 residuals restated.
2. The projection: this is the first QA round after the photo-projection pass (definition of done, CLAUDE.md). Seam crops from cam02 and cam05
   at the mask edge in the composite; any visible seam, doubled feature or sun baked into the shade is a blocker. Anisotropy on both boxes,
   std ratio, sunlit chroma (QA-07-2's test), Eevee vs Cycles albedo agreement on one hero crop.
3. Status of every QA-07 defect with the number that proves it, measured on the master (the acceptance tests in the round-07 table).
   Add the mirror ratio (reflection / own sunlit attic, photo 0.88) and the camera-height check at the new station (your item-5 method).
4. State the hero delta vs round 07 explicitly, and the rule: gate passes at hero >= 4.0; otherwise the two-round < +0.1 clock starts now.
5. Gate composite renders/qa_comparisons/round08_gate.png with deltas r07 -> r08 and the trend r02 -> r08. Every Blender run through
   scripts/blender_run.sh; renders as round 07 (Eevee six cameras, Cycles hero + cam04); no 4K run this round.
Commit only docs/qa_round_08.md, docs/quality_checklist.md, scripts/qa_*.py, renders/qa_comparisons/round08_*, renders/previews/qa/round08_*.
Touch renders/previews/qa/round08_RENDERS_DONE when every render has exited. Final report under 60 lines, numbers not adjectives.
