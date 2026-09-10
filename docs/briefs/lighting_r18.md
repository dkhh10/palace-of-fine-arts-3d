# Lighting round 18 — the rotunda interior fill on the hero (QA-10-2 blocker; brief from the lead, 2026-09-10). Branch `lighting`.
Read docs/briefs/process.md. `git merge main` first. Opus high, SHORT: bordered Cycles hero frames on the arch region only (border ~ x 780-1120,
y 260-620 of 1920x1080, 64 spp; each counts as a quarter frame; at most 6) + ONE full Cycles hero 64 spp + ONE Cycles cam02 720p + ONE Cycles cam04
720p for the holds. Report < 20 lines. Read docs/qa_round_10.md QA-10-2, QA-10-13, QA-10-17 and the "Notes for the lead" item 2.
1. QA-10-2 (blocker): on the Cycles hero the vault field box 900 380 1010 430 is 103.1 lum against ref 169's 44.9 (2.30x) and the jamb box
   872 400 892 480 is hue 338.5 (magenta) against 22.2 / R-B +58.9. Acceptance: vault field 45-65 lum; jamb hue 25-60 with positive R-B.
   Levers, in order: the rotunda interior fill level (r17 colour (1,0.95,0.88)) down until the field lands; then the jamb's magenta, which is the
   az-25 blue LIGHT_shade_fill_00 mixed with the warm fill on a surface that faces the camera (say which term it is by isolating each once).
2. Holds that WILL move and must be re-stated: cam02 soffit_l / soffit_r (hue 25-60, sat <= 0.35, rib/field contrast >= 15, and QA-10-13 says
   the current "gold on indigo" contrast is the wrong kind: the field must not be blue: field hue 25-60 too), cam04 coffer / own-sky 0.35-0.55,
   the hero shaded attic / sunlit attic / sky boxes (unchanged), cam03 near column p95 >= 25 (QA-10-17 says it reads as a flat olive slab:
   state its flute ridge / floor contrast on the new frame).
3. Do not move the sun, the sky, or the water. Do not touch other owners' files.
Deliverables: light_presets values, assets/lighting.blend, light_r18_sheet.png (arch 1:1 before / after / ref 169 crop + the hold table), §28 in the
notes with the table on your rebuilt master (object count), commits after every successful script, report with the last commit id.
