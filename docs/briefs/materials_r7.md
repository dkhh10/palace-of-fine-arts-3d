# Materials round 7 — brief from the lead (2026-09-09). Branch `materials`, worktree .claude/worktrees/materials. Read docs/briefs/process.md first.

Runs AFTER lighting r12 is merged (decisions.md 2026-09-08: lighting and materials sequential, measured on the merged master).
`git merge main` first; the master you build (scripts/lead_build.sh in your worktree) then carries lighting's r12 rig. Lighting's
hand-offs for you are in docs/status.md (entry "LIGHT r12 merged") and docs/lighting_notes.md §21.
Read: docs/qa_round_05.md (defect QA-05-2 blocker, the "dirt decal" reject paragraph, sections (a) and (b), Notes for the lead 1),
docs/materials_notes.md Round 6 (your own r6 hand-offs), docs/decisions.md 2026-09-08 entries.

Items (hero Cycles 1920x1080 <= 128 spp vs ref 169, QA's boxes via scripts/mat_r6_measure.py or its r7 successor):
1. QA-05-2 (blocker). The r6 macro grunge overshot: attic lum 166.5 (window 178-201), sat 0.643 (ref 0.588), entablature sat 0.836
   (ref 0.604), streak anisotropy 0.64 vs photo 4.07 (weathering must run DOWN the wall: column-mean std / row-mean std). Bring the
   macro amplitude down and make it anisotropic (vertical streak maps under the cornice / string course, run-off from projections);
   keep attic luminance std >= 0.60 of ref (r6 reached 0.66; do not fall back to "clean CAD"). Targets: attic lum 178-201, sat
   0.53-0.62, anisotropy >= 2.0, std ratio >= 0.60; entablature sat <= 0.70, hue 30-40.
2. Shaded stone albedo (QA-04-2 / QA-05-1, materials' share after lighting's r12 shade window): shaded attic box 1110 225 1150 260
   hue within 6 deg of 29.5, sat <= 0.55 on lighting's new rig. Use lighting's measured levers from the hand-off; do not fight the rig.
3. QA-05-3 (with lighting's r12 fill in place): the in-coffer gradient must give Cycles coffer/sky >= 0.35 and darkest/lightest quarter
   >= 0.20 (ref 083 0.265) on the merged master; if lighting's r12 already reaches it, leave the gradient alone and report the number.
4. QA-05-4 water: reflection column box 900 760 1020 840 sat >= 0.25 (ref 0.34; r5's sheen at 0 gave 0.11: ship the sheen at the level
   that meets this, its -1 deg hue cost is accepted), near-water hue toward 190-200 given lighting's horizon sky; ripples must carry the
   stone's warm colour (R-B in box 1100 960 1500 1060 within 10 of ref -26).
5. cam05 distance amplitude (grunge visible at 115 m): report the number you use.
Deliverables: assets/materials.blend, mat_lib/mat_build changes, composite renders/qa_comparisons/mat_r7_sheet.png (1:1 attic +
entablature crops before / after / ref 169 with the numbers; near-water crop), Round 7 section in docs/materials_notes.md, commits after
every successful script, final report < 30 lines. Answer for the lead: if the hero stays flat, what would a camera-projected albedo
from ref 169 / ref 085 onto the hero-facing attic / entablature / drum need from you (UV layer, projection script, blend mask)?
Added 2026-09-09 from ENV r7's report (docs/status.md "ENV r7 reported"): 6. `MAT_paving_stone` and `MAT_paving_stone_worn` are
missing from the library; ENV's colonnade walk (16.7 % of cam03's lower frame) falls back to gravel/soil. Ship both (ref 128 /
ref 169 paving: pale grey-buff slabs, joint lines, damp darkening near the water). 7. Shore band (QA-05-10): needs +43.9 lum to
reach ref 169's 115.6 WITHOUT raising saturation (already 0.775 vs 0.663): shore foliage albedo/translucency, not planting.
