# QA round 09 — brief from the lead (2026-09-10). Model: Opus 5 xhigh. Read docs/briefs/qa.md first; docs/qa_round_08.md is the pattern.

Round 09 is the LAST polish round (user's rule: hero under 4.0 after round 08 -> one more round, then Phase 5 regardless). It renders the master
rebuilt after: cam02 lens 27 mm (QA-08-1), lighting r16 (sun-side tint for the sunlit chroma, cam02 boxes at 27 mm, cam03 knob, flythrough
back to 1224 frames with ORN in the clearance check). No materials / ornament / environment round this time. What merged and every owner's
numbers: docs/status.md from "QA round 8 in" to the end.
Required beyond the standard renders / comparisons / scores / defect list:
1. Re-base: cam02 at 27 mm (new frame: new boxes, use lighting r16's; ref 062 residuals restated now that the dome is in frame). cam01 unchanged.
2. Status of every QA-08 defect with the number that proves it. QA-08-3: the lead closes it as "capped by the shipped view transform" (lighting
   r16 measured AgX High Contrast at sat ~0.49 for this box at the reference luminance; the sun has no blue left); state the number, do not
   re-open it unless you measure a lever the owners missed. QA-08-13: frame range must read 1-1224.
3. The definition of done: state the hero delta vs round 08 explicitly and the two-round clock (round 08 was +0.22; a round-09 delta under +0.1
   is 1 of 2). Whatever the number, the lead moves to Phase 5 after this report: write the defect list as the Phase 5 known-issues list,
   ordered by hero visibility, each with its owner and the one-line fix, so it can be pasted into the delivery notes.
4. Gate composite renders/qa_comparisons/round09_gate.png with deltas r08 -> r09 and the trend r02 -> r09. Every Blender run through
   scripts/blender_run.sh; renders as round 08 (Eevee six cameras, Cycles hero + cam04; add ONE Cycles cam02 at 720p 64 spp since its frame is
   new); no 4K run.
Commit only docs/qa_round_09.md, docs/quality_checklist.md, scripts/qa_*.py, renders/qa_comparisons/round09_*, renders/previews/qa/round09_*.
Touch renders/previews/qa/round09_RENDERS_DONE when every render has exited. Final report under 60 lines, numbers not adjectives.
