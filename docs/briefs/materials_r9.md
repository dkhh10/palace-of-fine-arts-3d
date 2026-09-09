# Materials round 9 — the photo-projection pass, the mirror level, the sunlit chroma (brief from the lead, 2026-09-09). Branch `materials`.
Read docs/briefs/process.md first. `git merge main` first (main has LIGHT r15 + the round-08 stations: cam01 at z 1.3 = 2.6 m over the water,
cam02 NNE at (-79.8, 24.4, 1.55) 40 mm). Never concurrent with lighting: lighting r15 is merged before you start; do not touch lighting's files.
Opus xhigh. Budget: this is the last materials round before the gate; one sweep per item, at most 3 Cycles hero frames (64-128 spp, 1920x1080),
1 Cycles cam04 (720p), 1 Eevee five-camera pass. Report < 30 lines.
Read: docs/briefs/materials_r8_projection.md (item B and constraints 1-6 are the spec; the aligned overlay is now
renders/qa_comparisons/round08pre_cam01_aligned_vs_ref169.png, scale 1.3108, dx -291.8, dy -127.6, and the stack table is docs/status.md "Session
restart" + docs/qa_round_07.md section (g)); docs/qa_round_07.md QA-07-1 (materials' half), QA-07-2, QA-07-3, QA-07-9, sections (a), (b), (h);
docs/reviews/mat_r8_review.md carries 4-8; docs/status.md "LIGHT r15 reported" for lighting's hand-off numbers on the water.
A. The projection (QA-07-2 blocker expected to close with it). Item B of the r8 brief, constraints 1-6 unchanged, on the registered stack (every
   course within 6 rows of ref 169 on the 2.6 m station). Sample the ratio map through architecture's UVProj layer weighted by UVProj_valid AND the
   facing mask (arch_notes round 4 hand-off); per-band vertical shift from the stack table, geometry frozen. Acceptance on the hero: attic box
   900 222 1020 256 sat 0.53-0.62, R-B >= 120, lum held 178-201; shaded attic hue 29.5 +- 6 / sat <= 0.50 held; columns hue 24.5 +- 4 / sat
   0.55-0.65 held; anisotropy >= 1.5 on QA's box and >= 2.0 on 900 224 1020 248; std ratio >= 0.60. Seam test: cam02 and cam05 1:1 crops at the
   mask edge with the row-std across the edge stated; a visible seam from either camera is a blocker in QA round 8.
B. QA-07-3 (major): hero reflection box 900 760 1020 840 lum 124-208 with R-B >= +35 and hue 25-45 held; reflection / own sunlit attic toward 0.88
   (now 0.55). The camera is now at 2.6 m (incidence 87-89 deg on the box) so measure first, then the specular level / roughness at grazing and the
   luminance of what is mirrored. Lighting r15's hand-off tells you what the sky's horizon term now gives the glossy ray; do not compensate for the
   sky in the water if lighting already moved it.
C. QA-07-1, materials' half: whatever lighting r15 reports as the frontier on the near-water box 1150 1000 1450 1050 (hue 185-200, lum within
   25 % of 105) and the flank 100 900 400 960 (within 25 % of 152 at hue <= 210) is yours through the sky-facing sheen / murk vs incidence.
   cam05 band lum 70-117 with sat >= 0.24 held; the review's carry 4 (camera-depth ramps hit cam05/cam06 at full slope) is the likely cause of
   cam05's 1.38x. Carry 5 (ramps pump on the flythrough) — a world-space term if it costs one knob, else document it for Phase 5.
D. QA-07-9 minor: coffer rim sat 0.38-0.50 with the field held; one Cycles cam04 (carry 7).
F. Added after LIGHT r15 (docs/status.md "LIGHT r15 reported"): (i) the lagoon's residual is 9.4 deg of hue on the near-water box (107.7 / hue 209.4
   vs ref 105.4 / 190): ref 169's water is ~18 deg greener than the sky it mirrors, so the body colour of MAT_water_lagoon is the knob, not the
   level; (ii) QA-07-7: the hero shaded attic sits at 136.4 (window 103.5-126.5) with the fill nearly off; lighting measured the shaded
   albedo ~12 % hot relative to the sunlit stone on the same wall (shaded went +17.5 % under a rig that moved sunlit +5 %). The projection's
   ratio map must not add to it: land the shaded attic 1110 225 1150 260 in 103.5-126.5 at hue 23.5-35.5 / sat <= 0.50 through the albedo.
E. One Eevee hero crop (carry 6): the projected albedo and the water in Eevee, side by side with Cycles.
Hold list (before / after, nothing leaves its window): every box in A, the shaded attic, cam05 lagoon sat, cam06 lagoon Cycles level.
Deliverables: scripts/mat_projection.py + assets/textures/projection/ (one 4K ratio map + one 4K mask pack, licence line in docs/reference_sheet.md),
assets/materials.blend, mat_r9_sheet.png (attic + entablature 1:1 before / after / ref, seam crops, reflection box, Eevee crop; ONE composite),
Round 9 section in docs/materials_notes.md with the acceptance table on your rebuilt master (object count stated), commits after every successful
script, report < 30 lines with the last commit id. If a UV layer on ARCH meshes turns out unavoidable, stop and report (lead routes it).
