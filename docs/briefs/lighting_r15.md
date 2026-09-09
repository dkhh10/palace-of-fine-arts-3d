# Lighting round 15 — the lagoon horizon, the hero shade level, cam03's row (brief from the lead, 2026-09-09). Branch `lighting`. Read docs/briefs/process.md first.
`git merge main` first (main has your r14 + lead corrections and the round-08 camera stations: cam01 now at z 1.3 = 2.6 m over the water,
cam02 re-stationed NNE at (-79.8, 24.4, 1.55) -> (0, 0, 23.5), 40 mm). Never concurrent with materials: MAT r9 starts after your merge. ONE sweep,
Opus high, short round: budget is tight, report within ~2 h of wall time. Materials will move the water shader after you; leave MAT_water_lagoon alone.
Read: docs/qa_round_07.md defects QA-07-1 (blocker, your half), QA-07-5, QA-07-7, QA-07-11, sections (a), (d), (e); docs/reviews/light_r14_review.md
carries; docs/lighting_notes.md §24.9.
0. cam02 moved. Re-base the cam02 boxes in light_r14_measure.BOXES (shade_pier, soffit, water, ...) on ONE Eevee frame from the new station before
   anything else, and say in the notes which boxes are new. The QA-06-2 / QA-07-11 windows stay (hue 25-60 shade pier at sat <= 0.35).
1. QA-07-1, lighting's half (blocker). The water's sky component is 1.24x too bright and 24 deg too blue: hero flank 100 900 400 960 lum 189.5 / hue 224
   vs the photo's 152 / 200; near water 1150 1000 1450 1050 lum 144 / hue 228 vs 105 / 190; cam05 band 128.6 vs 93.4. The r14 sky moved near-water hue
   214 -> 228 with the water untouched. Find what the horizon band of the r14 sky gives a glossy ray at 87-89 deg incidence (level and colour, the
   sky's horizon term / MULTIPLE_SCATTERING aerosol / your glossy-ray boost) and bring it to: near water hue 185-200 and lum within 25 % of 105, flank
   within 25 % of 152 at hue <= 210, cam05 band lum 70-117 with sat >= 0.24, WITH the hero reflection box 900 760 1020 840 held (R-B >= +35, hue 25-45)
   and the sky boxes above the horizon inside their r13/r14 windows. If the horizon term cannot land both, report the frontier with numbers and hand
   the remainder to materials r9 precisely (what the water sees vs what its shader returns).
2. QA-07-7. Hero shaded attic 1110 225 1150 260 at 134.0; window 103.5-126.5 with hue 23.5-35.5 and sat <= 0.50 held (target ~119, ref 118.8).
   LIGHT_shade_fill energy / the diffuse boost; keep cam06 roofs and cam03 shafts inside their r14 windows.
3. QA-07-5. cam03 outer lagoon-side row 880 120 1200 600 at 0.097 of the sunlit rotunda on the merged master (your r14 frames said 0.138): test >= 0.15
   at hue 25-60, and the frame under lum 10 <= 20 % (28 % now). Your r14 item: the SSW shade lamp's reach / sky visibility into the colonnade.
4. r14 review carries (docs/reviews/light_r14_review.md): sweep defaults from lb., commit measure stdout, docstrings, cam06 roofs (hue 316 over-warm)
   and cam02 pier (hue 7.0) back into 195-230 / 25-60 if the item-1 change does not already do it.
Hold list (measure before and after, nothing on it may leave its window): hero shaded attic, hero sunlit attic 900 222 1020 256 (lum 178-201), hero
reflection box, hero sky boxes, cam06 roofs, cam03 shafts, cam05 lagoon sat.
Deliverables: values in light_presets, assets/lighting.blend, light_r15_sheet.png (hero + cam02 + cam03 + cam05 before / after / ref, one composite),
§25 in the notes with the acceptance table on the rebuilt master (lead_build.sh in YOUR worktree, object count stated), commits after every
successful script, report < 25 lines: the numbers per box, what is handed to materials r9, and the last commit id. Renders: one Eevee five-camera
pass + at most 2 Cycles hero frames (64-128 spp, 1920x1080) + 1 Cycles cam05.
