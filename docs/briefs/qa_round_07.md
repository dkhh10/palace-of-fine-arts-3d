# QA round 07 — brief from the lead (2026-09-09). Model: Opus 5 xhigh. Read docs/briefs/qa.md first; docs/qa_round_06.md is the pattern.

Round 07 renders the master rebuilt after polish round 5: architecture r6 (hero stack registered on ref 169) + r7 (archivolt sockets),
lighting r14 (violet flood, reflection, Eevee cost), materials r8 (water blocker + the photo-projection pass on the hero-facing stack),
environment r9 (gallery clear width, PLAN = shipped), ornament r6 (+ r7 if merged: capitals 3.0 m, rinceau frieze, attic panels refit).
What merged and every owner's measured numbers: docs/status.md from "QA round 6 in" to the end.
Required beyond the standard renders / comparisons / scores / defect list:
1. Status of every QA-06 defect with the number that proves it, measured on the master: -1 stack (qa_stack_offset per course; all eight
   within 8 rows; attic storey within 10 %), -2 violet flood (shade hue / sat on cam02 / 03 / 05 / 06 boxes: 195-230 at sat <= 0.35), -3 water
   (reflection column R-B, near-water sat / hue, cam05 lagoon sat, cam06 lagoon level), -4 anisotropy on both boxes, -5 sunlit chroma,
   -6 capitals (px height AND the luminance-alternation count on a render, the half ornament could not measure), -7 cam03 lagoon-side row,
   -8 coffer sat, -9 entablature row std on the model's cornice window, -13 Eevee pass time. Environment: wing shadow share on a render
   (QA-02-7 cap 22 %, env's probe says 21.2 %), walk clearance visible on cam03, cam06 gate as the ratio composited / un-composited >= 0.60.
2. cam02 station: architecture r7 reports the ref 062 best station on the new stack; re-station cam02 if its residuals beat the current
   (state both). Do not move courses.
3. The definition of done (CLAUDE.md): this is the first QA round after the photo-projection pass. State the hero delta vs round 6 explicitly
   and whether the projection registered (seam crops from cam02 / cam05 in the composite; any visible seam or doubled feature is a blocker).
4. Gate composite renders/qa_comparisons/round07_gate.png with deltas r06 -> r07 and the trend r02 -> r07. Every Blender run through
   scripts/blender_run.sh; no 4K run this round.
Commit only docs/qa_round_07.md, docs/quality_checklist.md, scripts/qa_*.py, renders/qa_comparisons/round07_*, renders/previews/qa/round07_*.
Touch renders/previews/qa/round07_RENDERS_DONE when every render has exited. Final report under 60 lines, numbers not adjectives.
Added after MAT r8: 5. Hero camera height. Materials measured the hero's mirror geometry: cam01 sits 2.90 m over the water (Fresnel 0.46 on
the reflection box) while ref 169's reflection box is 0.88 of its own direct stone (a near-total mirror at 87-89 deg). Measure ref 169's
camera height over the water from the reflection geometry (water-line to reflected-cornice distance vs direct cornice height, or the horizon
row) and report it against 2.90 m. Do NOT move cam01 this round (every yardstick is aligned to it); state the number for the lead.
