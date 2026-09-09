# Lighting round 14 — the violet flood and the reflection (brief from the lead, 2026-09-09). Branch `lighting`. Read docs/briefs/process.md first.
`git merge main` first (main has your r13 and the r14 prep). Never concurrent with materials: materials r8 starts after your merge.
Read: docs/qa_round_06.md defects QA-06-2 (blocker), QA-06-3 (materials' water, but the horizon sky you own is what it mirrors), QA-06-7,
QA-06-13 and section (a); docs/decisions.md 2026-09-09 "After QA round 6"; docs/lighting_notes.md §21-22.
1. QA-06-2 (blocker). The r12 diffuse tint (1.0, 0.65, 17.0) with the anti-sun and horizon weights turns every shaded surface on cam02/03/05/06
   blue-violet (cam06 roofs hue 36.6 -> 253.4; the photo's shade is a neutral-cool grey-blue, hue 205-225 at low saturation). A tint with
   G < R cannot make a sky colour. Find the diffuse-sky colour and level that keeps the hero's shaded attic inside its window
   (hue 29.5 +- 6, sat <= 0.55, lum 0.9-1.1 of 115) AND puts the shaded roofs on cam06 / the shaded shafts on cam03 / the shaded stone on
   cam02 in hue 195-230 at sat <= 0.35 (state each box). Measure all four cameras on the same rig before choosing.
2. Reflection warmth. Hero reflection column box 900 760 1020 840: R-B +2.5 vs +69 in ref 169 (materials measured the box is 100 % water at
   22 m and that no sheen weight fixes it). The mirrored image is the sunlit building, so the reflection's R-B is set by what the water sees:
   check the glossy-ray sky boost and the Fresnel-weighted murk's contribution at that angle on the merged master; report what lighting can
   move (sky glossy term, horizon colour) and what is materials' (murk, roughness, ripple normal scale) with numbers, then hand the materials
   half to r8 precisely.
3. QA-06-7: cam03's outer lagoon-side row 880 120 1200 600 at 0.066 of sunlit; the re-based box passes at 0.384. Say whether the row is
   occluded like the old box (ray test) or reachable; fix it if reachable without breaking item 1.
4. QA-06-13: the Eevee six-camera pass rose 120.6 -> 218.6 s (+81 %) with the r13 Eevee-only rigs; bring it under 150 s (shadow settings /
   lamp count / probe resolution) while the Eevee shade windows from r13 hold.
Deliverables: as usual (values, assets/lighting.blend, light_r14_sheet.png with the four cameras' shade boxes before / after / ref, §24 in
the notes, commits after every successful script, report < 30 lines with the materials hand-off for the water).
