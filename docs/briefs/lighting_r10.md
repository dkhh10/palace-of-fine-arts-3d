# Lighting round 10 — brief from the lead (2026-09-08)

Measured hand-offs collected after QA round 3, lighting r09, materials r4, environment r4. All numbers are on the
1920x1080 Cycles hero (cam01) vs ref 169 unless stated; measure with scripts/mat_r4_measure.py (reproduces QA's boxes) and
scripts/light_measure.py. Rebuild-and-measure on the merged master (scripts/lead_build.sh output), never on a stale file.

1. Sunlit stone saturation and R-B (QA-03-2, still a blocker). Attic sat 0.440 vs ref 0.588, R-B 102 vs 136. Materials ran
   two albedo experiments (round 3 blue -44 %, round 4 blue -37 % / green +25 %) and moved sunlit saturation < 0.02: AgX's
   inset makes ~77 % of display blue leakage from R and G, so saturation is not reachable from albedo. Materials' analysis: the
   photo drops 11 deg of hue from sun to shade (sun 40.3, shade 29.5); we RISE 5 deg (sun 37.7, shade 42.5). More / bluer sky
   fill in the shade fixes the shade hue and widens the sunlit R-B at the same time. Test: sky fill colour/strength on the shade
   side (SKY_* knobs, sun/sky ratio, sun colour temperature) at 1920x1080 / 64 spp; target attic sat >= 0.53, R-B >= 120, shade
   hue within 6 deg of 29.5, attic luminance within 0.94-1.06 of ref, sky top within the 149-182 window.
2. Column shafts 1.62x too bright (mask lum 155 vs ref 96) after a 37 % albedo cut. Materials says fill, not albedo: the
   photo's shafts sit in the colonnade's own shadow with sky fill only. Check sun azimuth/elevation against the shadow edges in
   ref 169 (scripts/light_calibrate.py) and the FILL/soffit emitters' spill onto the outer shafts.
3. Near-water chroma (QA-03-7): near-field sat 0.486 vs 0.270, hue 206 vs 192. Materials measured that murk, tint and
   transmission do nothing at grazing angles: the lagoon is a Fresnel mirror of the horizon sky, so this is the sky's horizon
   colour, i.e. item 4.
4. QA-03-12: no haze band toward the horizon: sky_left 144 vs ref 194 (0.74) while sky top is 0.93. Target sky_left/sky_top
   within 10 % of the photo's 1.17 (air/aerosol density, altitude, SKY_CAMERA_BOOST split).
5. cam06 far-field contrast: environment got rotunda/far-shore from 1.15 to 1.45:1 (target >= 1.5); the last step is mist
   density (scripts/env_cam06_audit.py DOME/FAR_SHORE boxes).
6. Eevee vault fills (from r09): Eevee ignores the 45 deg spread; viewport dome ~3x too bright (Eevee soffit/sky 0.405,
   coffer/sky 1.137 vs Cycles 0.541/0.384). Find an Eevee-side fix (engine-conditional fill energy applied in
   light_presets.apply_viewport_eevee / apply_preview_eevee, or separate Eevee-only lights) so the Eevee QA previews of cam04 are
   within 0.15 of the Cycles ratios. Note architecture's vault coffers are now visible at every LOD and 0.38-0.55 m deep.
7. Lead item to do at the END of your round if the GPU is quiet: the 4K timing test (QA-03-16): one 3840x2160 hero at the
   FINAL preset, time logged in docs/lighting_notes.md; abort at 60 min and log the sample count reached.
Deliverables: as usual (light_presets/light_build values, assets/lighting.blend rebuilt, one composite
renders/previews/lighting/light_r10_sheet.png with before/after/ref and the numbers, r10 section in docs/lighting_notes.md,
commits after every successful script, final report < 30 lines).
