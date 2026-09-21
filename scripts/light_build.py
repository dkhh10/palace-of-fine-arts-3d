"""Lighting & Rendering specialist: builds assets/lighting.blend (collection LIGHT + world WORLD_golden_hour +
compositor node group COMP_golden_hour). Idempotent; everything derives from ONE parameter, the moment:

    blender -b --python scripts/light_build.py                     # morning golden hour (the chosen moment)
    blender -b --python scripts/light_build.py -- --moment evening  # evening alternate, same rig
    blender -b --python scripts/light_build.py -- --no-calibrate    # reuse the last calibration_report.json

Pipeline: moment -> NOAA solar position (Sun Position extension's sun_calc) -> aim LIGHT_sun (common.aim_sun) and the
MULTIPLE_SCATTERING sky (sun_rotation = azimuth - 90 deg, verified in light_calibrate.check_convention) -> integrate
the sky's own sun disc on a Lambertian card to get the lamp's energy and colour -> grey-card exposure -> AgX.
All numbers are stored as custom properties on LIGHT_sun / the world and in
renders/previews/lighting/calibration/calibration_report.json; docs/lighting_notes.md explains them.
"""
import bpy, os, sys, math, json, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_calibrate as cal
import light_presets as lp
import light_probes as probes

# ----------------------------------------------------------------------------- THE parameter
MOMENTS = {
    # local civil time; utc_offset_h is what you ADD to UTC to get local time (PST -8, PDT -7)
    "morning": dict(year=2026, month=11, day=10, hour=7, minute=30, utc_offset_h=-8, tz="PST",
                    note="Chosen golden hour: matches ref 169 (sun over the camera's left shoulder, ESE)."),
    "evening": dict(year=2026, month=10, day=20, hour=17, minute=45, utc_offset_h=-7, tz="PDT",
                    note="Evening alternate for delivery: rotunda backlit from the WSW (ref 035 mood)."),
}
FALLBACK_SUN = {"morning": (118.5, 7.4), "evening": (250.9, 6.9)}   # docs/reference_sheet.md table, if sun_calc is missing

# Sky: clear autumn morning. aerosol 1.0 = the model's 'clear' default (measured horizon-west radiance 4.7/5.1/4.5,
# zenith 0.46/0.87/1.72 in sky units, i.e. a ~5:1 horizon:zenith ratio like ref 169); aerosol hardly changes the sky
# seen by the hero camera (looking away from the sun) but warms the sun-side horizon. ozone 2.0 deepens the blue at
# low sun (B/R 1.59 vs ref 169's 1.65; ozone 1.0 gives a grey-blue 1.39). altitude 5 m (sea-level lagoon).
SKY = dict(sun_size_deg=0.533, sun_intensity=1.0, altitude=5.0, air_density=1.0, aerosol_density=1.6, ozone_density=2.0)
# Round 08b (materials' hand-off after QA-02-4). Materials measured that at +0.9 EV albedo has no authority left over
# chroma - a 44 % cut of albedo blue moved display blue 3 % - and that the sunlit attic's R-B spread was 81 against ref
# 169's 127: right hue, no gold. On a SUNLIT face the excess blue is sky fill, so the round-05 x2 art bias was the
# culprit; it was propping the shade open, and at +0.9 EV the shade no longer needs propping (it measured 146.5
# against ref 169's 117.2, i.e. 25 % too LIGHT). Back to the physical 1.0. Measured on the Cycles hero, five settings:
# attic R-B 88.1 -> 94.8 at strength 1.0, 97.8 at 0.6; shade 146.5 -> 134.0 -> 128.1.
SKY_STRENGTH = 0.80                # world strength for LIGHTING. 2.0 was a round-05 art bias, 1.0 the physical
                                   # value; 0.80 is a measured 20 % trim, and it is a CHROMA knob, not a level
                                   # knob - the exposure is re-calibrated against the 18 % card every time this
                                   # moves, so the scene keeps its brightness and only loses sky-blue fill. On a
                                   # sun-facing surface the sky still supplies 10.4 of 27.7 blue units against
                                   # 11.2 of 78.5 red (calibration_report E_sunfacing), so trimming it is 2.6x
                                   # more effective on blue than on red. Round 09, cam01 hero at 1920x1080/64 spp,
                                   # High Contrast: attic R-B 119.0 at 1.00, 122.9 at 0.80, 125.8 at 0.60; shade
                                   # 134.7 / 132.3 / 129.7 against ref 169's 117.2. 0.80 takes most of the gain
                                   # for the smallest departure from physical; 0.60 is on record if more is wanted.
SKY_CAMERA_BOOST = 2.10            # ROUND 10: 1.50 -> 2.10. This knob does NOT change the look of the sky; it holds
                                   # it still while the view exposure moves. Round 10 took 0.50 EV out of the whole
                                   # frame (EXPOSURE_BIAS below), which would have dropped the visible sky from
                                   # sky_top 168.4 to 144.6 and out of QA's 149-182 window; 1.50 x 2^0.5 = 2.12,
                                   # and 2.10 measured sky_top 168.7 against the 168.4 it had before the exposure
                                   # move (ref 169: 165.7). The old note below still describes what the knob is.
                                   # what the CAMERA sees of the sky: sky x boost = 0.80 x 1.50 = 1.20, i.e. the
                                   # visible sky is EXACTLY what round 08b calibrated, and the round-09 sky trim
                                   # is invisible to the camera and visible only to the diffuse lighting.
                                   # Round 08b swept 3.0 / 2.4 / 2.0 / 1.5 / 1.2 / 1.0 against
                                   # ref 169's sky-top luminance of 165.7: 213.6 / 204.3 / 195.7 / 179.9 / 165.7 /
                                   # 153.2. 1.20 lands on the reference exactly. (The sky is deep on the AgX shoulder,
                                   # which is why it takes a 2.5x cut in scene radiance to move it 23 %.)
SKY_GLOSSY_BOOST = 4.20            # ROUND 15 (QA-07-1): 5.25 -> 4.20. Measured on the round-15 master, Cycles hero
                                   # 64 spp, with nothing else moved: near water 144.7 -> 139.3, open-lagoon flank
                                   # 188.1 -> 180.8, and the hero's REFLECTION box 900 760 1020 840 back inside its
                                   # hold at R-B +31.9 -> +37.9 (test >= +35), because taking sky out of the water
                                   # is what lets the building's warm mirror read. sky_top / sky_left are identical
                                   # to 0.1 lum by construction (camera rays never traverse this socket).
                                   # Round 10's text follows. ROUND 10: 3.75 -> 5.25, the same 2^0.5 exposure hold as SKY_CAMERA_BOOST, so
                                   # the lagoon keeps the sky brightness it reflected before the exposure move
                                   # (water_refl 132.2 at 3.75 after -0.5 EV, 142.1 at 5.25, 153.4 before).
                                   # what GLOSSY (reflection) rays see: 0.80 x 3.75 = 3.00, again unchanged from
                                   # round 08b, so the lagoon reflects the same sky it did. Split from the camera
                                   # boost in round 08b: the
                                   # camera's sky had to come down to match ref 169 while the lagoon's reflection had
                                   # to stay up, and one socket could not do both. 1.0 x 3.00 = the 2.0 x 1.50 the
                                   # lagoon reflected before, so the water keeps its brightness.
SKY_CAMERA_SATURATION = 1.20       # saturation of the sky for CAMERA rays only (Hue/Sat node in the world);
                                   # the diffuse lighting keeps the physical colour. AgX desaturates the bright sky:
                                   # measured B/R 1.37 in the render vs 1.95 in ref 169 at matching luminance.
                                   # Round 10 verified it is still right: sky_top hue 208.7 against ref 169's 208.2
                                   # and saturation 0.427 against 0.487.
SKY_GLOSSY_SATURATION = 0.90       # ROUND 10 (QA-03-7). Split out of SKY_CAMERA_SATURATION, which glossy rays used
                                   # to share. At grazing angles the lagoon is a Fresnel mirror of the horizon sky, so
                                   # the near-water chroma IS the sky's chroma on the glossy socket and nothing in the
                                   # water shader can reach it (materials measured murk / tint / transmission at
                                   # ~0 effect there). Measured on the cam01 hero, near-water saturation against QA's
                                   # 0.22-0.32 window (ref 169: 0.270): gsat 1.20 -> 0.525, 0.85 -> 0.243,
                                   # 0.70 -> 0.173, 0.45 -> 0.086; 0.90 interpolates to ~0.27.
                                   # The remaining 17 deg of near-water HUE (209 vs ref 192) is NOT the sky: the
                                   # visible sky's own hue is 208.7 against ref 169's 208.2, i.e. exact. In the photo
                                   # the water is 16 deg greener than the sky it mirrors, which is the lagoon's own
                                   # upwelling green - environment's water shader, not lighting's.
SKY_GLOSSY_HUE = 0.500             # ROUND 15 (QA-07-1), new socket. Blender Hue/Saturation "Hue" on the GLOSSY
                                   # stage only: 0.5 = no shift, one unit = a full turn, so 0.5 + d rotates the sky
                                   # the LAGOON MIRRORS by d*360 deg while the visible sky (camera rays) and the
                                   # light on shaded stone (diffuse rays) are held exactly still. It exists because
                                   # QA-07-1 is a HUE defect and rounds 10-14 only ever had a level knob
                                   # (SKY_GLOSSY_BOOST) and a chroma knob (SKY_GLOSSY_SATURATION) on that socket.
                                   # Swept in docs/lighting_notes.md 25.2.
SKY_DIFFUSE_SATURATION = 1.00      # saturation of the sky for DIFFUSE rays, i.e. the light that lands on the shaded
                                   # stone. Kept physical. Round 10 swept it to 2.0 and 3.0 hunting the shaded
                                   # attic's hue (43.0 against ref 169's 29.5) and it moved the shade's BLUE channel
                                   # by 1 sRGB unit out of 36 needed (142,112,36 -> 135,107,34): >97 % of the light
                                   # on the shaded stone is warm interreflection off the sunlit stone and ground, not
                                   # sky, so no sky colour can reach it. Handed to materials (see docs/lighting_notes 19).
SKY_DIFFUSE_BOOST = 2.50           # ROUND 12 (QA-05-1): 1.00 -> 2.50. Round 11's note below is kept because its
                                   # measurements stand; what changed is that the lead WITHDREW the sunlit-stone
                                   # budget those measurements were rejected against, and that on the merged master
                                   # the sunlit attic reads 167.6 (QA's own window is 178-201), so the boost now moves
                                   # two numbers the same way instead of trading them: at 2.5 the sunlit attic is 180
                                   # and the shaded attic 115. Round 11's text follows.
                                   # ROUND 11 (QA-04-2), new socket, SHIPPED AT THE PHYSICAL 1.00. Scales the sky on
                                   # every ray that is neither camera nor glossy, i.e. the light that lands on shaded
                                   # stone, without touching the visible sky or the lagoon's reflection of it. It is
                                   # the socket the round-11 brief asked for first and it is NOT the fix: the full
                                   # sweep is in the SHADE_FILL comment below (boost 2 already costs 0.052 attic
                                   # saturation and 9.7 R-B against a budget of 0.02 / 5, and it drives the shade hue
                                   # the WRONG way, 43.1 -> 44.8, because the extra sky lands on the sunlit plaza and
                                   # comes back warm). Kept, measured, at 1.00, so the next round does not re-sweep it.
SKY_DIFFUSE_TINT = (1.0, 0.75, 8.0)   # ROUND 19 (QA-08-2 / QA-09-6): (1.0, 0.65, 70.0) -> (1.0, 0.75, 8.0), together
                                   # with SKY_DIFFUSE_TINT_ANTISUN 1.0 -> 0.0 below. The two move as ONE knob and must
                                   # not be read apart: dropping the anti-sun weight spreads the tint over the whole
                                   # dome, so the same blue on a shaded wall now costs b 8 where it cost b 70 through
                                   # the weight. Station 2's NNE rotunda face rendered blue-violet (b* -4.68 /
                                   # -18.20 / -3.12 on shade_pier / shade_pier_r / shade_arch, against a photograph
                                   # that reads +14.10 / +13.22 / +7.49); it now reads +11.26 / +5.29 / +8.80, every
                                   # one inside the brief's b* >= +5, h_ab 40-80, R-B >= +10. The hero holds 12/12
                                   # boxes (shaded attic lum -2.4 %, hue +0.1 deg; the 32 spp + OIDN noise floor is
                                   # MAE 2.91). g 0.65 -> 0.75 is not cosmetic: under a whole-dome tint the green
                                   # multiplier reaches every shaded surface instead of only the anti-sun horizon,
                                   # and at 0.65 it cost the hero's shaded attic 3.1 % of luminance (the hold is 3 %)
                                   # while at 1.00 it pushed cam02's shade_pier_r to h_ab 89.3 (the window ends at
                                   # 80). 0.75 is the only value measured to satisfy both. Swept in
                                   # docs/lighting_notes.md 29; the acceptance's shade_frieze control does NOT hold
                                   # (+12.82 -> +23.31 against a 9.9-12.9 window) and 29.4 proves with a fitted dose
                                   # model that no diffuse socket can hold it while the shafts come warm: the spread
                                   # between cam02's shaded boxes is set by how much warm bounce each receives, not
                                   # by the sky's colour. Round 16's text follows.
                                   # ROUND 16 (QA-08-3): b 40.0 -> 70.0. Not a new idea, a COUNTERWEIGHT: the
                                   # sun-side socket below takes the sky's blue off the sunlit stone, and the
                                   # ~9 % of the shaded attic's light that has bounced off sunlit stone first
                                   # loses its blue with it, which drove the hero's shaded attic hue 34.6 -> 36.8,
                                   # past QA's 35.5. Measured on the round-16 master, Cycles hero 64 spp, sun-side
                                   # at its floor: b 40 -> 36.8 / sat 0.496, b 55 -> 36.0 / 0.473, b 70 -> 35.1 /
                                   # 0.451 (PASS), with the SUNLIT attic moving 0.492 -> 0.489 of saturation and
                                   # 112.2 -> 111.5 of R-B, i.e. the anti-sun discriminator returns the blue to
                                   # the shaded box and nowhere else. Round 14's text follows.
                                   # ROUND 14 (QA-06-2): b 17.0 -> 40.0, because the two weights below are now
                                   # SHARP and a sharp weight passes much less of the tint: at q3 p6 the shaded wall
                                   # needs b 40 to keep the blue b 17 gave it at q1 p1 (24.1). Round 12's text follows.
                                   # ROUND 12 (QA-05-1), SHIPPED: a white balance on the sky that lights the
                                   # shade only (camera and glossy rays never see it). The shaded attic measures
                                   # (122, 94, 22) against ref 169's (141, 111, 81) -- short 59 units of BLUE and
                                   # only ~18 of R and G -- so the shade needs blue-biased light, not more of the
                                   # same warm light. The three channel gains are the solution of the three power laws
                                   # fitted in docs/lighting_notes.md 21.4 (shade_c ~ base_c * g_c^k, k = 0.17 / 0.25 /
                                   # 0.60): the shade wants g = (2.2, 1.9, 9.5), i.e. green pulled BELOW the boost and
                                   # blue far above it. Under the anti-sun weighting below the effective gain on a
                                   # shaded wall is about half the nominal, so b is 11.5 rather than 3.8. Swept in
                                   # round 12; see docs/lighting_notes.md section 21.
SKY_DIFFUSE_TINT_HORIZON = 1.0     # ROUND 12 (QA-05-1), new socket, SHIPPED AT 1.0. Weights the diffuse tint by
                                   # 1 - |ray.z|, i.e. onto the horizon band a vertical shaded wall samples and off
                                   # the zenith an up-facing surface samples. Without it the lagoon's diffuse (murk)
                                   # term takes the whole tint and the near-water box goes to saturation 0.457
                                   # against QA's 0.22-0.32 window. See docs/lighting_notes.md 21.9.
SKY_DIFFUSE_TINT_ANTISUN = 0.0     # ROUND 19 (QA-08-2 / QA-09-6): 1.0 -> 0.0, the whole-dome tint. Read with the
                                   # SKY_DIFFUSE_TINT comment above -- the pair is one knob. WHY THE SOCKET ROUND 12
                                   # added is now switched off: the weight is not neutral about WHICH shaded surface
                                   # gets the blue. Measured as the mix factor each box's own hemisphere sees
                                   # (docs/lighting_notes.md 29.4), at antisun 1.0 the hero's shaded attic sees
                                   # f = 0.0069 while cam02's shade_pier_r sees 0.0361 -- the tint that exists FOR
                                   # the hero's attic lands 5.2x harder on the station-2 shafts, which is exactly
                                   # QA-08-2. At antisun 0.0 the same two read 0.0733 and 0.0724, i.e. the dome is
                                   # shared, and the tint blue can then be cut from 70 to 8 with the hero unmoved.
                                   # The anti-sun half of the dome IS the blue part at a 7.8 deg sun, so this is a
                                   # loss of physical shape; the sweep kept it as long as it could (antisun_p 1,
                                   # horizon_p 2, horizon 0.5 were all measured, all made the violet worse by 12-20
                                   # b*, table in 29.3) and 0.0 is the only shape in the socket space that puts more
                                   # tint on the hero's attic than on the station-2 shafts. Round 12's text follows.
                                   # ROUND 12 (QA-05-1), new socket, SHIPPED AT 1.0 (fully anti-sun weighted). 0 = SKY_DIFFUSE_TINT is applied to the whole
                                   # dome; 1 = it is applied in proportion to how far the ray points AWAY from the sun
                                   # (weight 0.5 + 0.5 * Incoming.sun_direction). A shaded face samples the anti-sun
                                   # half of the dome and a sunlit face the sun half, so this is the only sky lever
                                   # that can blue the shade without bluing the sunlit stone beside it -- see
                                   # docs/lighting_notes.md 21.6 for the measured separation.
SKY_DIFFUSE_TINT_ANTISUN_P = 3.0   # ROUND 19: INERT since SKY_DIFFUSE_TINT_ANTISUN went to 0.0 -- make_sky_world
                                   # builds the anti-sun branch only when the amount is > 0, so this value is not in
                                   # the shipped node tree. Kept at its round-14 value so that restoring the weight
                                   # restores the shape it was swept at. Round 14's text follows.
                                   # ROUND 14 (QA-06-2), new socket. Exponent on the anti-sun weight
                                   # w = (0.5 + 0.5 * Incoming.sun)^p. Round 12 shipped the anti-sun and horizon
                                   # weights at 1.0 -- their maximum AMOUNT -- and then had no lever left when the
                                   # same tint that fixed the hero's shaded attic flooded every up-facing surface in
                                   # the build (QA-06-2: cam06 roofs hue 36.6 -> 253.4). The exponent is the
                                   # SHARPNESS of the same discriminator and it is a different lever: measured on
                                   # the sky probe (docs/lighting_notes.md 24.1), raising it from 1 to 3 takes the
                                   # tint's blue on a SUN-FACING wall from +36 sRGB units to +2.4 while the shaded
                                   # wall keeps its own.
SKY_DIFFUSE_TINT_HORIZON_P = 6.0   # ROUND 14 (QA-06-2), new socket. Exponent on the horizon weight (1 - |ray.z|)^p.
                                   # A vertical wall's hemisphere is centred on a HORIZONTAL normal (mean |ray.z|
                                   # ~0.42). ONE table, computed once for both files (r14 review carry 8), as the
                                   # cosine-weighted expectation E[(1-|z|)^p] over each surface's own hemisphere --
                                   # NOT (E[1-|z|])^p, which is what the two older comments disagreed about:
                                   #     p     1      2      3      6*     10
                                   #     wall  0.576  0.401  0.307  0.179  0.115
                                   #     roof  0.333  0.167  0.100  0.036  0.015
                                   #     x     1.73   2.41   3.07   5.02   7.59      (* = SHIPPED)
                                   # At p = 1 the wall keeps only 1.73x what a roof, a walk or the lagoon's murk
                                   # keeps -- which is why round 12's horizon weight was worth only 0.045 of
                                   # near-water saturation. At the shipped p = 6 it keeps 5.0x. Physically it is
                                   # also the more honest shape: the anti-sun horizon band (Earth shadow / Belt of
                                   # Venus) at a 7 deg sun is a band a few degrees deep, not a linear ramp.
SKY_DIFFUSE_HUE = 0.5              # ROUND 12 (QA-05-1), new socket. Blender Hue/Saturation "Hue" on the DIFFUSE
                                   # stage only: 0.5 = no shift, one unit = a full turn, so 0.5 + d rotates the sky
                                   # that lands on shaded stone by d*360 deg. See the SKY_DIFFUSE_BOOST comment for
                                   # why it exists and what it measured.
SKY_DIFFUSE_TINT_SUNSIDE = (1.0, 1.0, 0.0)   # ROUND 16 (QA-08-3), new socket, SHIPPED AT ITS FLOOR. The MIRROR of SKY_DIFFUSE_TINT: a
                                   # multiply on the sky that lands on SUN-FACING surfaces only, weighted by
                                   # w_sun = clamp(0.5 - 0.5 * (Incoming . sun_direction))^p, i.e. by how far the
                                   # sampled sky direction lies on the SUN half of the dome. It exists because
                                   # QA-08-3 is a blue EXCESS on the sunlit stone and there was no socket that could
                                   # reach it: SUN_BLUE_MULT has been 0.00 since round 12, so the direct term already
                                   # contributes no blue at all, and every blue unit on the sunlit attic comes from
                                   # the diffuse sky -- which runs at 0.80 x 2.50 = 2.0x physical because
                                   # SKY_DIFFUSE_BOOST is what holds cam03's colonnade open. Measured deficit
                                   # (QA round 08, Cycles hero): attic 227/184/122 against ref 169's 231/186/96 --
                                   # the red matches to 2 %, the blue is 27 % hot. Swept in docs/lighting_notes 26.2.
SKY_DIFFUSE_TINT_SUNSIDE_P = 3.0   # ROUND 16, the SHARPNESS of that weight, on the round-14 pattern (see
                                   # SKY_DIFFUSE_TINT_ANTISUN_P): p = 1 is a broad half-dome and leaks onto shaded
                                   # stone through bounce, p = 3 keeps it on faces that actually see the sun.
SUN_BLUE_MULT = 0.00               # ROUND 12 (QA-05-1): 0.75 -> 0.00. It is the counterweight to the diffuse tint
                                   # above. That tint puts blue on every diffusely lit surface, the sun-facing ones
                                   # included (a sun-facing surface takes ~38 % of its blue from the sky, round 09's
                                   # calibration), which costs the sunlit attic its R-B. Taking the SUN's own blue out
                                   # gives it back on exactly the faces the sky over-blued and nowhere else, because the
                                   # sun only lights the faces that face it: measured +14.4 R-B and +0.03 saturation on
                                   # the sunlit attic between 0.75 and 0.00, with the shaded attic moving 0.6 deg of hue.
                                   # At 0.00 the lamp is the calibrated (1.000, 0.607, 0.000): the sun's blue
                                   # is fully spent buying back what the diffuse tint costs the sunlit stone.
                                   # Round 09's note follows.
                                   # multiplier on the CALIBRATED lamp colour's blue channel, applied after the sky's
                                   # own sun disc has been integrated (so the calibration itself stays physical and
                                   # reproducible). Round 09 lever for QA-02-14 / the sunlit-stone chroma: the lamp
                                   # colour is (1.000, 0.607, 0.258) and on a sun-facing surface the sky still
                                   # supplies 10.4 of the 27.7 blue units (calibration_report E_sunfacing), so the
                                   # sun's own blue is the only part of it lighting can take out without touching
                                   # the shade. 1.00 = the physical colour; 0.75 measured on the cam01 hero at
                                   # 1920x1080/64 spp is worth +3.9 attic R-B and +0.015 attic saturation with
                                   # the attic luminance flat (blue carries 7 % of luminance), taken together
                                   # with SKY_STRENGTH 0.80 in the same sweep row.
SUN_ANGLE = 0.0093                 # rad, real solar disc 0.533 deg (same as the sky's sun_size)
EXPOSURE_BIAS = 1.25               # ROUND 10: 1.75 -> 1.25 (view exposure -4.083 + 1.25 = -2.833 EV).
                                   # QA-03 closed QA-02-4 with the attic at 0.94 of ref 169 and told lighting not to
                                   # move the exposure again - but that reading was taken on a master that was still
                                   # rendering at "AgX - Base Contrast" (the round-09 look bug) and before materials
                                   # r4. On the rebuilt master the same box reads 197.5 against ref 169's 189.6, i.e.
                                   # 1.04x and 19 units above QA's own floor: the +0.9 EV bought in round 08 was
                                   # paying for albedo that materials has since supplied.
                                   # Giving it back is the single strongest CHROMA lever left, because the sunlit
                                   # stone had climbed onto the AgX shoulder where the transform desaturates: at
                                   # 1920x1080 the same rig at -0.5 EV moves the attic from 234,196,133 to
                                   # 222,179,99 - saturation 0.433 -> 0.554, R-B 101 -> 123, hue 37.4 -> 38.8
                                   # (ref 40.3), luminance 199 -> 182 (ref 190). Nothing else in the round-10 sweep
                                   # came close: sun blue x0.35 was worth +4 R-B, a 5x aerosol change -2, and a
                                   # 2x diffuse sky saturation +3. It also closes QA-03-2's column defect on its
                                   # own (mask luminance 145 -> 104 against ref 96) and lands the shaded attic at
                                   # 113.0 against ref 115.0. The visible sky and the lagoon's reflection are held
                                   # still through SKY_CAMERA_BOOST / SKY_GLOSSY_BOOST above, so this is a stone
                                   # exposure change, not a global one.
                                   # EV added to the grey-card calibration. Round 08b: SKY_STRENGTH 2.0 -> 1.0 takes
                                   # light out of the scene, so the 18 % card calibration moved -4.39 -> -4.14 EV and
                                   # the old bias of 2.00 would have landed the view at -2.14, a quarter stop above
                                   # the number QA's sweep asked for AND above the setting every round-08b measurement
                                   # was made at. 1.75 holds the view exposure at -2.39 exactly. EV added to the card. Round 07 (QA-01-12) shipped 1.10.
                                   # Round 08 (QA-02-4, blocker): QA's exposure sweep (scripts/qa_exposure_sweep.py)
                                   # rendered the hero at +0/+0.5/+1.0 EV and measured the display response directly:
                                   # +32.0 / +35.2 / +30.5 / +33.8 sRGB units per EV on attic / column / sky / water.
                                   # The sunlit attic was 142.4 against ref 169's 179.4 -> +1.16 EV, dome +1.07,
                                   # column +0.78, sky top +0.70, water reflection +0.94; the recommendation is +0.9 EV.
                                   # My round-07 estimate of "+0.15" was wrong: I read the deficit as display-referred
                                   # and AgX compresses a 14-26 % display gap into most of a stop of SCENE exposure.
                                   # 1.10 + 0.90 = 2.00 -> view exposure -3.29 -> -2.39. Warmth is NOT chased here:
                                   # hue falls 1.1 deg per +1 EV, so QA-02-14 is a materials/albedo job.
LOOK = lp.LOOK                     # ALIAS, not a copy. Round 08b set this string here and left
                                   # light_presets.LOOK at "AgX - Base Contrast"; build_master.py applies the
                                   # light_presets one, so master.blend - every QA render and the deliverable -
                                   # rendered at Base Contrast while lighting.blend rendered at High Contrast.
                                   # The look is now defined once, in light_presets.py, with the rationale.
# QA-02-8. Round 07 used the mist pass RAW (LINEAR, 30 -> 730 m) as the haze factor, x 0.85. That is a ramp with no
# asymptote: everything past ~730 m sat at 0.85 haze, so at cam06 the dome, the lawn and the lagoon all mixed to the
# same flat colour (measured saturation 0.076-0.091, hue 60-76 deg). Two things were wrong and both are fixed here.
#  1. SHAPE. Airlight is 1 - exp(-d/L), not d/L: it rises fast near the camera and then flattens. So the mist pass is
#     now a plain LINEAR distance ramp over a long baseline (20 -> 2020 m, i.e. mist = (d - 20) / 2000) and the
#     compositor turns it into cap * (1 - exp(-k * mist)) with k = 5.0, i.e. an extinction length L = 2000/5 = 400 m.
#     Matched to round 07 where round 07 was right (0.12 at 110 m, 0.22 at 200 m) and capped where it was wrong:
#     0.42 at 500 m, 0.51 at 800 m, 0.55 at 1200 m instead of 0.85 flat.
#  2. COLOUR. haze_warmth (1.22, 1.0, 0.74) on the measured west-horizon radiance gave (3.82, 3.74, 3.02) - a neutral
#     grey-yellow at linear saturation 0.21, which is exactly the grey-olive QA measured. The anti-solar horizon IS
#     blue-grey physically; the warm veil in ref 169 is the low sun scattering into it, and that is an art bias with a
#     measured target: display hue 30-45 deg. (1.50, 1.00, 0.58) gives (4.70, 3.74, 2.37), hue 35 deg, sat 0.50.
# Sweep result (scripts/light_r08_sweep.py, cam06, 5 settings incl. haze OFF - the numbers are in lighting_notes 15):
# with the haze switched off entirely the aerial ALREADY reads hue 84.6 at saturation 0.178 and a dome/far-shore
# contrast of 1.08:1. So the grey-olive is the scene's own colour and the flatness is the scene's own flatness; the
# round-07 haze made both worse but did not cause them, and no haze setting can reach QA's saturation 0.20 / contrast
# 1.5:1. Heavier haze buys warmth only by veiling more, which is the global desaturation this fix is supposed to
# avoid, so the settings below carry the warmth in the haze COLOUR instead of its amount.
# ROUND 13 REVIEW CARRY 5 (2026-09-09): the sentence that used to end this paragraph -- "L = 800 m (a clear-morning
# extinction length, not the 400 m of round 07's ramp) at a 0.50 cap" -- is no longer what ships and is withdrawn.
# The round-13 cam06 fix below sets k = 5.0 on a 2000 m ramp, i.e. exactly the L = 2000/5 = 400 m that sentence
# argued against, at a 0.25 cap. The two are the same airlight near the camera (cap x k held at 1.25) and the
# 400 m version is the one that passes environment's far-shore std test; the "clear-morning 800 m" was an
# atmospheric-plausibility argument, not a measurement, and the measurement in the table below overrides it.
MIST = dict(start=20.0, depth=2000.0, falloff="LINEAR")   # mist pass = (d - 20) / 2000, clamped; SHAPED in the compositor
# ROUND 13 (QA-05-8, environment's cam06 hand-off): cap 0.50 -> 0.25 and k 2.5 -> 5.0, i.e. cap * k held at 1.25.
# ENV r7 reported that the compositor added +58 lum to cam06's horizon crop and cut its std 44.0 -> 23.5, flattening
# the far-shore line their geometry produces un-composited. Measured on this master (cam06 Eevee 1280x720, crop and
# statistic from env_r7_measure: rows 0-220, and count_lines on rows 0-110):
#   compositor OFF                     mean  89.4  std 59.8   8 far-shore lines
#   as shipped (cap 0.50, k 2.5)       mean 129.7  std 33.8   2      <- fails the std >= 35 test by 1.2
#   cap 0.25, k 5.0 (SHIPPED)          mean 122.2  std 38.1   2      <- passes with 3.1 of margin
#   cap 0.30, k 2.5                    mean 117.2  std 42.4   3
#   cap 0.20, k 2.5 / depth 6000       mean 109.0  std 47.4   4
#   cap 0.25, k 2.5, depth 4000        mean 103.9  std 50.5   6
# Holding cap * k fixed is what makes it nearly free: the airlight is cap*(1-exp(-k*mist)) ~= cap*k*mist while the
# argument is small, so the NEAR and MID field (the wings at ~250 m are at mist 0.115) keep the slope they had and
# only the saturating far field loses veil. The cost on the hero, Cycles 1920x1080 / 64 spp, is the whole difference
# between this and simply lowering the cap: south wing band 94.7 -> 93.6, shore band 91.8 -> 91.5, shaded attic
# 114.6 -> 114.3, sunlit attic 180.5 -> 180.5 / sat 0.475 / R-B 103.1 -> 103.2, columns 1.13x -> 1.13x.
# For comparison, MIST["depth"] 2000 -> 6000 reaches std 47.4 but costs the south wing 94.7 -> 83.9 and the north
# wing 140.7 -> 134.9, i.e. it spends the exact number QA-05-5 is short of. Rejected for that reason.
COMP = dict(haze_strength=0.25,          # the CAP: the maximum airlight fraction at infinite distance, not a scale
            haze_extinction=5.0,         # k in cap * (1 - exp(-k * mist)); L = MIST["depth"] / k = 400 m
            haze_warmth=(1.70, 1.00, 0.48),   # haze colour = measured west-horizon radiance x warmth
            bloom_threshold_display=0.9,   # scene-linear threshold = this / 2^exposure, i.e. only near-white pixels bloom
            bloom_strength=0.05, bloom_size=0.6, vignette=0.08)

# QA-01-9. Measured on master (Cycles 48 spp, cam04): the rotunda vault renders sRGB 12/255 with 3 diffuse bounces
# and 12/255 with 8 - the interior is not bounce-limited, it simply sees almost no sky: a 7.4 deg sun never reaches
# the floor and the four arches subtend a small solid angle from the coffers. That is 7 stops under the sunlit attic
# (182/255); ref 083 shows the coffers ~3.5 stops under a sunlit surface, but ref 083 is exposed FOR the ceiling.
# The real site gets what our model does not: a large pale concrete plaza, the lagoon and the open lawn throwing light
# up into the vault. FILL models exactly that and nothing else - an up-facing area light under the vault, so it lights
# the soffits and the coffers and adds almost nothing to what cam01 sees through the arch. It is an art bias, sized by
# measurement; ENERGY is the one number to change if QA wants it dialled back.
FILL = dict(name="LIGHT_rotunda_bounce", location=(0.0, 0.0, 7.5), size=36.0, energy=10214.0,
            # ROUND 12 (QA-05-3): 3648 -> 10214 (x2.8). Round 11's 3648 was measured on lighting's own branch and
            # read coffer / own sky 0.387; on the LEAD'S MERGED master, with materials r6's in-coffer gradient in
            # place, the same rig reads 0.211. The gradient darkened the coffer floors, so the knob that lights the
            # floors best had to come up to match. Measured on the rebuilt master (docs/lighting_notes.md 21.8):
            # x1 -> coffer 0.230, soffit mean 0.261; x3.2 -> coffer 0.482, quarter 0.249, soffit mean 0.358. The
            # slope is 0.115 of coffer per unit, so x2.8 puts the coffer field on ref 083's own 0.437.
            # ROUND 11 (QA-04-7): 1140 -> 3648 (x3.2). Round 10 took half a stop out of the whole frame
            # and never re-tuned the interior, so the round-09 rig fell from coffer/sky 0.384 to 0.261,
            # out of QA's 0.35-0.55 window, while the soffit mean stayed on ref 083's 0.405. The sweep
            # is in docs/lighting_notes.md 20.5: +1.0 of this knob is worth +0.062 coffer and only
            # +0.019 soffit, because the central disk is the emitter the coffers see best.
            # ROUND 09: 7600 -> 1140 (x 0.15). 9000 in round 07, 7600 in round 08. Halving the sky in round 08b
            # left both fills oversized: the coffer field measured 1.016 of cam04's own sky (Cycles, round-09 rig)
            # against ref 083's 0.39, i.e. a ceiling as bright as the sky seen past it. The central disk is the
            # emitter the COFFERS see best, so it is the one that came down hardest; it still carries the last
            # 0.07 of coffer ratio that the (now narrow) vault emitters no longer throw at the dome.
            # ROUND 17 (brief item 1 / QA-09-6): colour (1.0, 0.86, 0.68) -> (1.0, 0.95, 0.88). The two warm
            # interior fills are the ONLY light on the coffered arch soffits -- ARCH r8 turned those from a flat
            # chord plate into real barrels, and on the round-16 rig they measure hue 34.7 / 32.3 (inside QA's
            # 25-60) at saturation 0.413 / 0.378 against a 0.35 ceiling, i.e. warm enough and too CHROMATIC. The
            # fills' own colour is the whole of that saturation and nothing else in the rig reaches the soffit.
            # Measured on the round-17 master, Cycles cam02 64 spp, soffit_l / soffit_r saturation:
            # (1.0, 0.86, 0.68) -> 0.413 / 0.378; (1.0, 0.93, 0.84) -> 0.354 / 0.328; shipped (1.0, 0.95, 0.88).
            # (r17 review finding 4: THIS row is the shipped one, measured on the round-17 master -- the
            # "34.7 -> 35.8 / 32.2 -> 33.4" and "ships at 0.356" that used to stand here were the intermediate
            # (1.0, 0.93, 0.84) case and the round-16 cam04 value.) SHIPPED, docs/lighting_notes.md 27.6:
            # cam02 soffit_l hue 34.7 -> 36.3, soffit_r 32.3 -> 33.9, saturation 0.413 -> 0.340 / 0.378 -> 0.317,
            # coffer rib / field contrast unmoved at 111.3 / 114.6 lum, so the coffers do not flatten. cam04's
            # coffer ratio RISES with it (the fill is slightly more luminous at the same watts), which is the safe
            # direction: it shipped at 0.386 against a 0.35 floor. ROUND 18 moved that -- see VAULT_FILL below.
            color=(1.0, 0.95, 0.88), spread_deg=150.0,
            note="QA-01-9 interior bounce fill: the plaza/lagoon bounce the model has no geometry for")

# QA-02-12. The probes + the central disk fixed the coffered ceiling (cam04 coffer field / own sky 0.50 vs ref 083's
# 0.39) but NOT the eight barrel-vault soffits around it: 0.20 of the frame's sky vs 0.58 in ref 083. The reason is
# geometric, not a bounce-count: FILL is a disk of radius 18 m at z 7.5 centred on the rotunda axis, and the vault
# soffits are an annulus at radius 15.4-19.5 m, z 17.5 (springing) to 23.75 (crown), facing down and inward. From a
# soffit patch the disk is nearly edge-on and half of it is occluded by the inner colonnade ring, so it collects a
# fraction of what the coffers (straight above the disk centre) collect. Raising FILL fixes the soffits only by
# overshooting the coffers, which are already 28 % over ref 083's ratio.
# So: a separate up-facing rectangle under EACH of the eight vault bays, on the bay axis, below the springing line.
# Real lights, not probes, so Eevee and Cycles agree (QA wants the fix confirmed in both). They face up, and Blender
# area lights are single-sided, so nothing below them (cam04 at z 1.6, cam01 through the arch) ever sees the emitter.
# arch_params: FACE_AZ0 82.0, faces at 82 + 45k; WALL_APOTHEM 21.5, WALL_THICKNESS 2.0 -> soffit outer edge r 19.5;
# INNER_WALL_APOTHEM 15.38 -> soffit inner edge; ARCH_SPAN 12.5; ARCH_SPRING_Z 17.5.
# MEASURED, and this is the important part: the soffit and the coffered ceiling are LOCKED together. Across six
# configurations - emitter at z 8 / 13 / 15, at radius 17.5 and in the arch plane at 20.0 tilted 55 deg inward, with
# the central disk at 7600 W and at 0 - the soffit/coffer luminance ratio never left 0.486-0.556. Raising the soffit
# to QA's 0.45 of sky costs a coffer field at 0.855 of sky, i.e. 2.2x ref 083, which would re-open QA-01-9. The
# reason is physical: in ref 083 the soffits are BRIGHTER than the coffers (0.58 vs 0.39) because they are lit by the
# sunlit plaza seen through the great arches at close range, and a 7.4 deg sun in this model never puts that light on
# the plaza. An interior bounce source cannot reproduce a ratio that comes from outside the building.
# So: ship the middle of the line, and leave the lead one number. energy 2400 -> soffit 0.34, coffer 0.69;
# 8000 with FILL at 0 -> soffit 0.45 (QA's literal target), coffer 0.86. Both bracketing renders are on disk.
# ROUND 09 BREAKS THE LOCK. Round 08 measured soffit/coffer at 0.486-0.556 across height, radius, tilt and the
# central disk, and concluded ref 083's 0.58/0.39 (a 1.49 ratio the other way round) was unreachable from inside.
# It is reachable, and the knob is SPREAD. At 90 deg each emitter floods the whole vault volume, so most of its
# light lands on the central coffered dome rather than on the soffit above it - which is also physically wrong:
# the plaza light these bays actually get arrives through their own arch opening, which subtends roughly +-25 deg
# from a point under the vault, so a restricted cone is the MORE faithful model, not a cheat. Measured in Cycles
# on cam04 at the round-09 rig (fill x, vault y, spread s -> soffit/sky, coffer/sky, soffit/coffer):
#   1.00, 1.00, 90 -> 0.617, 1.016, 0.61     0.00, 0.65, 90 -> 0.316, 0.472, 0.67
#   0.00, 1.00, 30 -> 0.309, 0.186, 1.66     0.40, 1.40, 45 -> 0.531, 0.489, 1.09
#   0.00, 1.80, 45 -> 0.538, 0.305, 1.76     0.15, 1.65, 45 -> 0.535, 0.376, 1.42  <- shipped
# ref 083 is 0.58 / 0.39 / 1.49. The shipped row is inside +-0.08 of BOTH for the first time, so QA-02-12 and
# QA-01-9 stop trading against each other. Cost on record: the two soffit boxes read 0.396 W / 0.674 E, a 1.7:1
# imbalance against 1.14:1 at 90 deg - a narrow cone leaves the obliquest part of the vault to the sky alone.
VAULT_FILL = dict(name="LIGHT_rotunda_vault_bounce", n=8, az0=82.0, radius=17.5, z=13.0,
                  # ROUND 11 (QA-04-7): 3960 -> 3564 (x0.9), the counterweight to FILL x3.2 above.
                  # This knob trades 0.28 of soffit for 0.095 of coffer per unit, so a small cut here
                  # keeps the soffit mean within 4 % of ref 083 while the disk lifts the coffer field.
                  # ROUND 17: colour with FILL above, (1.0, 0.86, 0.68) -> (1.0, 0.95, 0.88); the two fills light
                  # the same soffits and a split colour would put a chroma seam across the barrel.
                  # ROUND 18 (QA-10-2, the blocker): the bay emitters are the term that made the HERO's vault field
                  # 2.30x the photograph, and they are the only term that can come off, because the disk is what
                  # carries cam04's coffer. Isolated on the round-18 master (Cycles hero 64 spp,
                  # bordered on the arch, box 900 380 1010 430; ref 169 aligned reads 44.9 lum / hue 4.5 / sat 0.318):
                  #   f 1 v 1 (r17 SHIPPED)  102.9 lum   hue 39.7 sat 0.449     2.29x the photograph
                  #   f 1 v 0.35              79.3       hue 40.4 sat 0.591     1.77x
                  #   f 1 v 0   (SHIPPED)     60.7       hue 38.8 sat 0.648     1.35x, inside QA's 45-65
                  #   f 0 v 0                 43.9       hue 37.9 sat 0.759     0.98x -- the model's own sky and
                  #                                                             bounce ALONE already reproduce
                  #                                                             ref 169's shade, with no fill at all
                  # The whole 45-65 window is spanned between "no interior fill" and "the disk alone", so v must be
                  # ~0 whatever f does: v 0.05 already reads 63 and v 0.10 reads 66. The disk stays at f 1.0 because
                  # it is worth only 16.8 of the hero's 60.7 and it is the coffer's knob (27.4: 0.115 of coffer per
                  # unit against the bay emitters' 0.095).
                  # THE COST IS cam04 AND IT IS STRUCTURAL, not a tuning miss. ref 083 -- the source of the
                  # 0.35-0.55 coffer window and of the soffit ratio -- is exposed FOR THE CEILING; ref 169 is
                  # exposed for the sunlit stone. Round 08's own table shows no spread / height / radius that
                  # escapes it: the best soffit/coffer trade on record (spread 45 -> 90 at 0.65 of the energy,
                  # the (0.00, 0.65, 90) row above) keeps 0.59 of the soffit, which puts the hero's box at ~86,
                  # still 1.9x the photograph. What DOES escape it is the bay index -- see `bay_weights` below.
                  # See docs/lighting_notes.md 28.
                  # ROUND 18b: the cut is PER BAY, and the two bays that are kept are the two the OTHER cameras
                  # depend on -- which is not a compromise, it is what the ray-cast in docs/lighting_notes.md 28.3
                  # showed. The hero's QA-10-2 box is NOT a bay soffit: it is `ARCH_rotunda_ceiling_field`, the
                  # central coffered ceiling at z 27.3 seen through the great arch, and EVERY bay emitter lights it
                  # (all eight on 102.9 lum, bay 00 alone removed 78.9, all eight off 60.7). cam02's two soffit
                  # boxes are bays 07 and 06 (`ARCH_rotunda_vault_07` / `ARCH_rotunda_vault_coffers_06`), and those
                  # two bays are far enough round the drum that they put 0.2 lum on the hero's patch of ceiling.
                  # Measured on the round-18 master, Cycles 64 spp (bordered hero + full cam02):
                  #   bays kept          hero ceiling   cam02 soffit_l lum / hue / sat   soffit_r
                  #   all eight (r17)       102.9        100.8 / 36.3 / 0.413            93.3 / 33.9 / 0.317
                  #   1-7 (bay 00 off)       78.9        100.9 / 36.2 / 0.338            93.2 / 33.9 / 0.316
                  #   06 + 07 (SHIPPED)      60.9         98.1 / 36.2 / 0.342            89.6 / 33.9 / 0.329
                  #   06 + 07 at 0.6         60.8         80.5 / 34.8 / 0.367            74.4 / 31.6 / 0.332
                  #   none                   60.9         36.9 / 332.9 / 0.190           39.3 / 305.9 / 0.173
                  # So 06 + 07 at full weight lands QA-10-2 (45-65) AND holds cam02's soffits inside hue 25-60 /
                  # sat <= 0.35 / rib-field >= 15; dropping them to 0.6 buys the hero 0.1 lum and costs cam02 18 lum.
                  # The price is cam04, whose `coffer_field` is the SAME surface as the hero's box: see 28.4.
                  bay_weights=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0],
                  size=12.5, size_y=4.0, energy=3564.0, color=(1.0, 0.95, 0.88), spread_deg=45.0,
                  note="QA-02-12 vault-soffit bounce: the plaza light the eight bays get through their own openings")

# ----------------------------------------------------------------------------- ROUND 17: the colonnade gallery
# ARCH r8's hand-off, re-measured here (scripts/light_r17_gallery.py, log light_r17_gallery.log): the camera-facing
# side of `ARCH_colonnade_south_column_028` -- 33 % of cam03's width -- sees **5.5 %** of the sky, cosine-weighted,
# and the walk under it 14.6 %. Straight up from the walk the first hit is the colonnade's own mutule soffit at
# z 15.20, i.e. the gallery is a roofed 4.5 m slot 15 m deep, closed on one long side by ENV's exhibition-hall
# backdrop (21 % of that shaft's hemisphere). Nothing in the round-16 rig reaches it: `LIGHT_shade_fill` is a
# 2 deg sun lamp and the colonnade shadows it, and r15 measured that no value of its weight moves the box. In
# CYCLES the shaft therefore renders at mean luminance **3.3 / 255**, 3 % of the sunlit rotunda opposite, and
# 39.9 % of the whole cam03 frame is under 10 lum.
#
# This is the same class of hole as QA-01-9 and QA-02-12 and it gets the same primitive: an emitter standing in
# for a bounce the model does not carry -- here the gravel walk and the sunlit ground outside the colonnade, both
# of which the render's own paving reads at 13.6 lum, i.e. already too dark to bounce anything. The strips are
# UP-FACING, so they add nothing to the walk directly (an area light emits from one side only) and light the
# shafts, the soffit and the entablature above; the walk comes up through the soffit bounce, which is the right
# order for a covered gallery.
#
# Placement is fitted to the geometry, not to arch_params: both wings' main rows sit on a mean radius of 117.40 m
# about (-11.2, 84.7) -- two rows 4.5 m apart, so the WALK centreline is exactly that mean -- over arcs of 100.9 m
# (south, 58 columns) and 98.3 m (north, 56). Eight strips per wing at 12.6 m spacing with a 13.0 m strip length
# is continuous coverage.
#
# EEVEE gets NONE of it (`energy_eevee` 0.0, so `light_presets.apply_gallery_for_engine` sets hide_render). Two
# reasons, both measured: Eevee's baked irradiance volume already carries the gallery at 5x the Cycles level
# (cam03 near column 16.9 vs 3.3 lum, p95 30 vs 20, frame black 4.6 % vs 39.9 %), so it needs no fill; and
# sixteen shadow-mapped area lights would re-open QA-06-13, the Eevee six-camera pass time that round 14 spent a
# whole item bringing back down. This is the round-13 SHADE_FILL pattern with the engines the other way round.
GALLERY_FILL = dict(name="LIGHT_gallery_fill", n=8, center=(-11.2, 84.7), radius=117.40, z=-0.20,
                    # energy swept on the round-17 master (Cycles cam03 64 spp, bordered), against the brief's
                    # acceptance (near column p95 >= 25 lum, flute ridge - floor >= 8) and QA-06's own holds
                    # (shaft_flank 0.30-0.70 of the sunlit rotunda, outer_row >= 0.15):
                    #   W/strip  near col lum / p95 / ridge-floor   outer_row   shaft_flank   walk hue
                    #        0        3.3 /  20 / 12.0                 0.030       0.510        249.7
                    #      400       14.6 /  47 / 20.9                 0.123       0.553        280.0
                    #     1000       30.2 /  79 / 30.3                 0.251       0.613          6.1
                    #     2500       61.0 / 139 / 47.6                 0.499       0.736         32.1
                    # THE LEVEL IS SET BY THE PHOTOGRAPH, not by the windows. On ref 128 (the cam03 reference,
                    # scripts/light_r17_measure header) the nearest SHADED column reads **0.292** of the sunlit
                    # rotunda behind it, the second, lit column 0.661 and the walk 0.307. 2500 W puts the shaded
                    # shaft at 0.525 and 2000 W at 0.447 -- 1.5x the photograph -- while 400 W leaves outer_row
                    # under its 0.15 floor. **1200 W** interpolates to 0.29-0.30, i.e. the reference ratio, and
                    # still clears every test in the round-17 brief (p95 >= 25, ridge - floor >= 8) with the
                    # frame's black share and outer_row well inside their holds.
                    size=13.0, size_y=4.4, energy=1200.0, energy_eevee=0.0,
                    color=(1.0, 0.86, 0.68), spread_deg=150.0,
                    # arcs measured on the master (degrees about `center`, atan2 of the column origins)
                    wings={"south": (-66.9, -18.0), "north": (-144.3, -96.9)},
                    note="ROUND 17: the gravel-walk and outside-ground bounce the colonnade gallery has no "
                         "geometry for; CYCLES only, see the comment above")

# ----------------------------------------------------------------------------- QA-04-2: the shade fill
# ROUND 11. QA measured the shade collapsed: cam03's near shaft 7.3 against ref 128's 69.7, the cam03 ground 21.2,
# and the hero's shaded north attic at hue 43.1 / saturation 0.736 against ref 169's 29.5 / 0.425 - i.e. the shade is
# not only dark, it is the wrong colour, a yellow-green bounce with no sky in it.
#
# The obvious lever was tried first and MEASURED TO FAIL. `SKY_DIFFUSE_BOOST` (new socket, round 11) scales the sky on
# every ray that is neither camera nor glossy, so it raises the shade without touching the visible sky or the lagoon's
# reflection. Cycles, the lead's merged master, cam03 at 1280x720 and cam01 at 1920x1080 / 64 spp:
#
#   diffuse boost | cam03 shaft | cam03 ground | attic sat | attic R-B | attic lum | shade hue | columns
#   1.0 (r10)     |     4.6     |     23.6     |   0.554   |   122     |   180.4   |   43.1    |  1.27x
#   2.0           |     9.1     |     34.6     |   0.502   |   112.3   |   187.7   |   44.8    |  1.47x
#   4.0           |    17.9     |     53.8     |   0.423   |    96.9   |   198.8   |   47.4    |  1.58x
#
# Two things kill it. (1) The brief's budget is 0.02 saturation and 5 R-B; a boost of 2 already costs 0.052 and 9.7,
# because a sun-facing surface collects ~14 % of its red and ~38 % of its blue from the sky (r09 calibration), so more
# sky lands on the sunlit stone too. (2) It makes the shade hue WARMER, not cooler (43.1 -> 44.8 -> 47.4): the extra
# sky lands mostly on the sunlit plaza and comes back as warm bounce. SKY_DIFFUSE_BOOST therefore ships at 1.00 and is
# kept only as a documented, measured socket.
#
# What the shade actually needs is light that reaches the ANTI-SUN faces and nothing else. Three wide-angle SUN lamps
# on the anti-sun hemisphere do exactly that, and a sun lamp is the right primitive for three reasons: its energy is
# an irradiance in W/m2, directly comparable with the calibrated 67.3 W/m2 of the real sun, so the fill can be quoted
# as a fraction of the sun; it is occluded by the building exactly the way the sky is (no light through walls); and it
# costs almost nothing to sample. They sit LOW (elevation 14-20 deg) on purpose: a low fill rakes vertical shaded
# faces, where the defect is, and lands on the horizontal plaza at cos(el) ~ 0.3, so it adds little of the warm ground
# bounce that made the diffuse boost fail.
# `visible_camera = False` keeps a 55 deg disc out of the sky, and specular_factor 0.10 keeps it out of the lagoon's
# reflection and off the column highlights (QA-03-7 and QA-04-5 are both glossy-side defects).
SUN_REFERENCE_W = 0.0              # set by build() to the calibrated lamp irradiance, so SHADE_FILL can
                                   # be quoted as a fraction of the real sun in the log and the notes
# ROUND 13 (QA-05-1, the EEVEE half). The rig stays OFF in Cycles -- `energy` is still 0.0 and the lamps are
# `hide_render` there, so Cycles is untouched by construction and every round-10/11 cost table below still stands.
# It is switched ON for EEVEE ONLY, through `energy_eevee`, because Eevee cannot reproduce the round-12 shade any
# other way. Measured on the round-13 master (9706 objects), hero 1920x1080, Eevee `apply_preview_eevee` against
# the CYCLES frame of the same rig (shaded attic 114.6 / hue 30.9 / sat 0.375):
#
#   Eevee lever                                   shaded attic lum / hue / sat   near water lum vs Cycles
#   nothing (round 12 as shipped)                      93.3 / 38.2 / 0.650            +19.6 %
#   light-probe bake taken with the diffuse world      93.3 / 38.2 / 0.650            +19.6 %
#   probe caches FREED entirely                        93.3 / 38.0 / 0.632            +19.8 %
#   SKY_DIFFUSE_BOOST 2.5 -> 7.0 (x2.8)                96.0 / 37.7 / 0.606            +70.2 %
#   fast GI off                                       114.6 / 44.6 / 0.740            +31.1 %
#   fill 16 W/m2, the round-11 colour, el 16           112.9 / 41.2 / 0.554            +29.9 %
#   fill 55 W/m2, colour (0.14,0.19,1.00), el 16      116.1 / 35.2 / 0.401            +33.6 %
#   fill 55 W/m2, colour (0.14,0.19,1.00), el 5       119.3 / 35.0 / 0.381            +20.2 %   <- SHIPPED
#
# Two things are being fixed and they need two different properties of the lamp:
#  1. LEVEL. In Eevee the box is lit by the screen-traced horizon scan, not by the world: 2.8x the whole diffuse
#     sky moves it 2.7 lum while it moves the lagoon 50 points, and freeing the baked volumes moves it 1.8 lum.
#     Only a directional lamp reaches it.
#  2. COLOUR. The shaded stone's blue reflectance is ~0.13 of its red (measured from the 16 W/m2 case: the same
#     lamp radiance returns 0.0578 of linear red and 0.0184 of linear blue), so the round-11 colour (0.42,0.62,1.00)
#     lands 16 display units of red and 19 of blue where the gap needs 17 and 43. The colour is therefore
#     re-derived per channel from that reflectance, which is why it is nearly a pure blue.
# ELEVATION 16 -> 5 deg is what makes it cheap: a vertical shaded face keeps cos(5)/cos(16) = 1.04 of the fill
# while the lagoon and the plaza keep sin(5)/sin(16) = 0.25, and the measured cost on the near-water box falls from
# +33.6 % to +20.2 %, which is the +19.6 % Eevee already had before any fill. `specular` 0.10 -> 0.00 keeps a
# 55 deg disc out of the water's reflection and off the column highlights.
# The full round-10/11 cost tables for switching it on in CYCLES are in docs/lighting_notes.md 20.4 and still apply:
# at el 16, 6 W/m2 costs the near-water saturation 0.274 -> 0.207 and the columns 1.29x -> 1.37x of ref. That is why
# `energy` (the Cycles number) stays 0.0 and this is an Eevee-only rig on the EEVEE_VAULT pattern.
# ROUND 15 (QA-07-1, the blocker). The rig goes from THREE lamps to ONE, and its energy from 70 to 49 W/m2, which
# is the same 0.70 x 70 the surviving lamp always had. Nothing about the light on the hero's shaded attic changes;
# what changes is that the other two lamps stop lighting the LAGOON. Isolated on the round-15 master, Cycles hero
# 64 spp, one lamp moved at a time (docs/lighting_notes.md 25.2):
#
#   lamp (az, w)          hero shaded attic          near water 1150 1000 1450 1050     flank 100 900 400 960
#   all three off         130.8 / hue 40.8           118.6 / hue 208.6                  159.1 / hue 210.2
#   WNW 300 at 1.00       130.9 / hue 40.7  (+0.1)   143.9 / hue 227.8  (+25.3, +19)    159.2 / hue 210.3  (+0.1)
#   SSW 205 at 1.00       (not measurable)           +0.8 with NNE                      188.1 / hue 224.2  (+29, +14)
#   NNE  25 at 0.70       136.8 / hue 32.6  (+6.0)   +0.8 with SSW                      +1.4
#
# The hero's shaded attic is a NORTH-facing surface, so the only lamp that colours it is the NNE one. The WNW lamp
# sits at az 300 el 2, i.e. it shines toward az 120 -- straight down the hero camera's axis -- and at 2 degrees over
# a water plane that is a near-specular glint: it buys the hero's shade 0.1 lum and costs the lagoon 25.3 lum and
# 19 degrees of hue. The SSW lamp does the same to the south half of the lagoon (the flank box) and, measured, does
# nothing at all for the colonnade it was aimed into (cam03's outer row 0.115 -> 0.110 when it was DOUBLED, and
# 0.115 -> 0.119 with the whole rig off): what actually opens that box is Eevee's fast GI, see light_presets.
# So both are deleted rather than dimmed. Round 14's text follows.
# LEAD 2026-09-10 (QA-10-2, docs/lighting_notes.md 28.x): the az-25 blue shade lamp is the magenta on the hero's arch jamb (its deposit
# there is B +28 / R +2.5) and the violet on cam02's face. OFF: energy 49.0 -> 0.0, 38.5 -> 0.0. Moves the hero shaded attic hue ~35 -> ~41
# and sat past 0.50 (stated in docs/status.md; the arch reading right at 100 % outranks those two windows). The lamp object stays (rig shape).
SHADE_FILL = dict(name="LIGHT_shade_fill", energy=0.0, energy_eevee=0.0, angle_deg=55.0, specular=0.00,
                  # ROUND 14 (QA-06-2): the rig is no longer Eevee-only. `energy` 0.0 -> 70.0 W/m2 in CYCLES.
                  # The round-12 diffuse tint delivered the shade's blue AND flooded every up-facing surface in the
                  # build, because half of what reaches a shaded wall has bounced off a horizontal surface first
                  # (21.7) -- so no sharpening of a SKY weight can separate them (24.2 measures p 2, 3, 6, 10 and
                  # every one of them loses the hero's shade before the aerial gets its warmth back). A lamp at
                  # 2 deg of elevation can: a vertical wall keeps cos(2) = 0.999 of it and a horizontal surface
                  # sin(2) = 0.035, a 29x discrimination, and a sun-facing wall points away from it entirely.
                  # 70 W/m2 puts the hero's shaded attic at 118.2 / 33.7 / 0.415 against ref 169's 115.0 / 29.5 /
                  # 0.425 with the sky tint sharpened off everything else (24.3b).
                  shadow_res=0.20, shadow_jitter=False,
                  # ROUND 14 (QA-06-13): these three shipped on Blender's DEFAULTS -- 0.001 m/texel, finer than
                  # LIGHT_sun's 0.002, with jitter on -- for three 55 deg soft suns carrying a diffuse blue. That
                  # was the whole +81 % of the Eevee pass (24.5). At 0.20 m/texel with jitter off cam03 goes
                  # 89.0 -> 53.6 s and cam06 46.1 -> 37.1 s, and the shade gets BETTER, not worse (24.6).
                  color=(0.03, 0.02, 1.00),
                  # ROUND 14: round 13's (0.14, 0.19, 1.00) was solved for EEVEE's deficit; in Cycles it adds
                  # +9 red and +12 green for its +26 blue and moves the shade's hue the wrong way as fast as its
                  # blue moves it back (24.3b, cases Af35 / Af55). Re-solved from those deltas.
                  lamps=[dict(az=25.0, el=2.0, w=1.00,
                              note="NNE: the ONLY lamp of the rig since round 15. It carries the hero's shaded "
                                   "attic (hue 40.8 without it, 32.6 with it, window 23.5-35.5) and the north "
                                   "wing's inner face. The WNW 300 and SSW 205 lamps were deleted in round 15: "
                                   "measured, they were worth 0.1 lum to the shade and 25.3 lum + 19 deg of blue "
                                   "to the lagoon (QA-07-1). Its own cost is cam02's shaded pier, which it drives "
                                   "to hue 262 against QA-07-11's 25-60 window -- the same lamp, the same axis, "
                                   "and no value of w lands both (0.70 -> attic 32.6 / pier 262; 0.10 -> attic "
                                   "39.7 / pier 355; 0.00 -> attic 40.7 / pier 23). See docs/lighting_notes 25.3.")],
                  note="QA-05-1 Eevee shade fill on the anti-sun hemisphere: the blue the round-12 diffuse sky "
                       "puts on shaded stone in Cycles and that Eevee's screen-traced GI cannot deliver")

COLLECTION = "LIGHT"
WORLD_NAME = "WORLD_golden_hour"
GROUP_NAME = "COMP_golden_hour"
SCENE_TREE_NAME = "COMP_scene_golden_hour"


# ----------------------------------------------------------------------------- solar position
def solar_position(moment):
    """(azimuth_deg clockwise from north, elevation_deg) via the Sun Position extension's NOAA code."""
    m = MOMENTS[moment]
    local_hours = m["hour"] + m["minute"] / 60.0
    try:
        from bl_ext.blender_org.sun_position import sun_calc
        az, el = sun_calc.get_sun_coordinates(local_hours, common.LAT, common.LON, -m["utc_offset_h"], m["month"], m["day"], m["year"])
        return math.degrees(az) % 360.0, math.degrees(el), "sun_position.sun_calc (NOAA)"
    except Exception as e:      # pragma: no cover
        print(f"[light_build] WARNING sun_calc unavailable ({e}); using the reference-sheet table")
        az, el = FALLBACK_SUN[moment]
        return az, el, "docs/reference_sheet.md table"


# ----------------------------------------------------------------------------- builders
def build_sun(coll, az, el, energy, color, moment, meta):
    light = bpy.data.lights.new("LIGHT_sun", "SUN")
    light.energy = energy
    light.color = color
    light.angle = SUN_ANGLE
    light.use_shadow = True
    try:
        light.shadow_maximum_resolution = 0.002      # Eevee: fine shadows on the ornament (metres per shadow texel)
        light.use_shadow_jitter = True
    except Exception:
        pass
    obj = bpy.data.objects.new("LIGHT_sun", light)
    coll.objects.link(obj)
    obj.location = (0.0, 0.0, 60.0)
    common.aim_sun(obj, az, el)
    m = MOMENTS[moment]
    obj["moment"] = moment
    obj["date"] = f"{m['year']:04d}-{m['month']:02d}-{m['day']:02d}"
    obj["time_local"] = f"{m['hour']:02d}:{m['minute']:02d} {m['tz']}"
    obj["utc_offset_h"] = m["utc_offset_h"]
    obj["latitude"] = common.LAT
    obj["longitude"] = common.LON
    obj["azimuth_deg"] = az
    obj["elevation_deg"] = el
    obj["azimuth_convention"] = "degrees clockwise from true north; north = -X, east = +Y"
    obj["lamp_energy_W_m2"] = energy
    obj["lamp_color"] = list(color)
    for k, v in meta.items():
        obj[k] = v
    return obj


def build_fill(coll):
    """QA-01-9: up-facing area light under the rotunda vault (see the FILL comment above)."""
    light = bpy.data.lights.new(FILL["name"], "AREA")
    light.shape = "DISK"
    light.size = FILL["size"]
    light.energy = FILL["energy"]
    light.color = FILL["color"]
    light.use_shadow = True
    try:
        light.spread = math.radians(FILL["spread_deg"])
    except Exception:
        pass
    obj = bpy.data.objects.new(FILL["name"], light)
    obj.location = FILL["location"]
    obj.rotation_euler = (math.pi, 0.0, 0.0)   # Blender lights emit along local -Z; flip so this one faces UP
    obj["note"] = FILL["note"]
    obj["energy_W"] = FILL["energy"]
    coll.objects.link(obj)
    print(f"[light_build] {FILL['name']}: disk r {FILL['size']/2:.1f} m at z {FILL['location'][2]}, {FILL['energy']} W, "
          f"up-facing (radiance {FILL['energy'] / (math.pi * math.pi * (FILL['size']/2)**2):.3f} sky units)")
    return obj


def build_shade_fill(coll, energy=None, energy_eevee=None):
    """QA-04-2 / QA-05-1: wide-angle sun lamps on the anti-sun hemisphere (see the SHADE_FILL comment above).
    Idempotent: any existing lamps with this prefix are removed first, so a sweep can rebuild them in memory.

    `energy` is the CYCLES irradiance and `energy_eevee` the EEVEE one; as of ROUND 14 BOTH are non-zero
    (SHADE_FILL: 70.0 W/m2 Cycles, 55.0 W/m2 Eevee), i.e. this is real light in both engines and no longer the
    Eevee-only rig of round 13 (r14 review carry 6). The lamps carry both on `energy_W` / `energy_W_eevee` and
    `light_presets.apply_shade_for_engine` switches between them, exactly the way `apply_vault_for_engine`
    switches the vault emitters. `hide_render` is set per engine from whichever of the two is zero; with both
    non-zero the lamps are visible to both renderers."""
    S = SHADE_FILL
    e_total = S["energy"] if energy is None else energy
    e_eevee = S.get("energy_eevee", 0.0) if energy_eevee is None else energy_eevee
    for o in [o for o in bpy.data.objects if o.name.startswith(S["name"])]:
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and d.users == 0:
            bpy.data.lights.remove(d)
    if max(e_total, e_eevee) <= 0.0:
        # r11 review fix 4: at zero in BOTH engines the three SUN lamps still cost three shadow maps in Eevee (the
        # QA previews were already overflowing the shadow pool) and three lights in every Cycles light-tree
        # traversal, for exactly no light. Build nothing; either energy switches the rig on.
        print(f"[light_build] {S['name']}: 0 W/m2 in both engines, no lamps built (see the SHADE_FILL comment)")
        return []
    made = []
    for k, cfg in enumerate(S["lamps"]):
        name = f"{S['name']}_{k:02d}"
        light = bpy.data.lights.new(name, "SUN")
        light.energy = e_total * cfg["w"]
        light.color = S["color"]
        light.angle = math.radians(S["angle_deg"])
        light.use_shadow = True
        try:
            light.specular_factor = S["specular"]
        except Exception:
            pass
        # ROUND 14 (QA-06-13). These three lamps shipped on Blender's DEFAULT shadow settings, i.e. a
        # shadow_maximum_resolution of 0.001 m/texel -- FINER than LIGHT_sun's own 0.002 -- and shadow jitter on,
        # for three 55 deg soft suns whose only job is to put a diffuse blue on shaded stone. That is what the
        # Eevee six-camera pass paid 98 s for. Both are swept in 24.4.
        try:
            light.shadow_maximum_resolution = S.get("shadow_res", 0.001)
            light.use_shadow_jitter = S.get("shadow_jitter", True)
        except Exception:
            pass
        obj = bpy.data.objects.new(name, light)
        obj.location = (0.0, 0.0, 80.0)
        common.aim_sun(obj, cfg["az"], cfg["el"])
        obj.visible_camera = False        # a 55 deg sun disc must never be visible in the sky
        obj["azimuth_deg"], obj["elevation_deg"] = cfg["az"], cfg["el"]
        obj["energy_W"] = light.energy            # the CYCLES irradiance; the r11 sweep scales from this
        obj["energy_W_eevee"] = e_eevee * cfg["w"]   # round 13: the EEVEE-only irradiance
        obj.hide_render = e_total <= 0.0          # Cycles must not traverse a lamp it is not allowed to see
        obj["note"] = cfg["note"]
        obj["rig_note"] = S["note"]
        coll.objects.link(obj)
        made.append(obj)
    print(f"[light_build] {S['name']}: {len(made)} cool sun lamps, Cycles {e_total:.2f} W/m2 "
          f"({e_total / max(1e-9, SUN_REFERENCE_W or 1):.3f} of the calibrated sun), Eevee {e_eevee:.2f} W/m2 "
          f"({e_eevee / max(1e-9, SUN_REFERENCE_W or 1):.3f} of the sun), hidden in render: {e_total <= 0.0}, at "
          f"{[ (c['az'], c['el']) for c in S['lamps'] ]}, angle {S['angle_deg']} deg, colour {S['color']}, "
          f"shadow res {S.get('shadow_res', 0.001)} m/texel, jitter {S.get('shadow_jitter', True)}")
    return made


def build_vault_fill(coll):
    """QA-02-12: eight up-facing rectangles, one under each rotunda vault bay (see the VAULT_FILL comment above).

    ROUND 18: `energy` <= 0, or a per-bay weight of 0 in `bay_weights`, builds NO lamp for that bay, rather than a
    0 W area light both engines would still put in the light list (the GALLERY_FILL pattern). The rig is restored
    by putting the weights back to 1.0 -- nothing else in the build depends on the objects existing, and
    `light_presets.apply_vault_for_engine` reads each lamp's own `energy_W`, so a partial rig switches correctly."""
    V = VAULT_FILL
    made = []
    weights = V.get("bay_weights") or [1.0] * V["n"]
    if V["energy"] <= 0.0 or max(weights) <= 0.0:
        print(f"[light_build] {V['name']}: 0 W (round 18, QA-10-2), no lamps built")
        return made
    for k in range(V["n"]):
        # ROUND 18b: a bay whose weight is 0 gets no lamp at all, rather than a 0 W area light both engines
        # would still carry in the light list (the GALLERY_FILL / round-18 pattern).
        e_k = V["energy"] * float(weights[k % len(weights)])
        if e_k <= 0.0:
            print(f"[light_build] {V['name']}_{k:02d}: bay az {V['az0'] + 360.0 / V['n'] * k:.0f} weight 0, skipped")
            continue
        a = math.radians(V["az0"] + 360.0 / V["n"] * k)
        nx, ny = -math.cos(a), math.sin(a)          # arch_params.az_dir: azimuth clockwise from north, north = -X
        name = f"{V['name']}_{k:02d}"
        light = bpy.data.lights.new(name, "AREA")
        light.shape = "RECTANGLE"
        light.size, light.size_y = V["size"], V["size_y"]
        light.energy = e_k
        light.color = V["color"]
        light.use_shadow = True
        try:
            light.spread = math.radians(V["spread_deg"])
        except Exception:
            pass
        obj = bpy.data.objects.new(name, light)
        obj.location = (nx * V["radius"], ny * V["radius"], V["z"])
        # face UP (flip about X), then spin about Z so the long edge runs tangentially across the bay
        obj.rotation_euler = (math.pi, 0.0, math.atan2(ny, nx))
        obj["note"] = V["note"]
        obj["bay_azimuth_deg"] = V["az0"] + 360.0 / V["n"] * k
        obj["energy_W"] = e_k                # the PHYSICAL (Cycles) energy; light_presets.apply_vault_for_engine
                                             # reads it back when it swaps the Eevee-only override in and out
        coll.objects.link(obj)
        made.append(obj)
    area = V["size"] * V["size_y"]
    print(f"[light_build] {V['name']}: {len(made)} of {V['n']} x {V['size']}x{V['size_y']} m up-facing rectangles "
          f"at r {V['radius']} z {V['z']}, {V['energy']} W x bay weights {weights} "
          f"(radiance {V['energy'] / (math.pi * area):.3f} sky units at weight 1)")
    return made


def build_gallery_fill(coll, energy=None, energy_eevee=None):
    """ROUND 17 (ARCH r8 / QA-09-5): up-facing warm strips along both colonnade walks. See the GALLERY_FILL
    comment. Idempotent: any existing lamp with this prefix is removed first, so a sweep can rebuild the rig in
    memory the way `build_shade_fill` does.

    Both energies are written to custom properties (`energy_W`, `energy_W_eevee`) and
    `light_presets.apply_gallery_for_engine` switches `data.energy` / `hide_render` between them, exactly as for
    the shade fill and the vault emitters. The lamps are invisible to CAMERA and GLOSSY rays: they stand in for a
    diffuse bounce, so a camera at eye level must not photograph them (the walk floor is 0.4 m below them and
    cam03's station is 1.9 m above them) and they must not put a specular streak down a polished shaft -- the same
    reasoning as SHADE_FILL's `specular = 0.00`."""
    G = GALLERY_FILL
    e = G["energy"] if energy is None else energy
    e_eev = G.get("energy_eevee", 0.0) if energy_eevee is None else energy_eevee
    for o in [o for o in bpy.data.objects if o.name.startswith(G["name"])]:
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and d.users == 0:
            bpy.data.lights.remove(d)
    if max(e, e_eev) <= 0.0:
        print(f"[light_build] {G['name']}: 0 W in both engines, no lamps built")
        return []
    cx, cy = G["center"]
    out = []
    for wing, (a0, a1) in sorted(G["wings"].items()):
        for i in range(G["n"]):
            # strip centres at the midpoints of n equal arc slices, so the run is covered end to end
            a = math.radians(a0 + (a1 - a0) * (i + 0.5) / G["n"])
            x, y = cx + G["radius"] * math.cos(a), cy + G["radius"] * math.sin(a)
            name = f"{G['name']}_{wing}_{i:02d}"
            light = bpy.data.lights.new(name, "AREA")
            light.shape = "RECTANGLE"
            light.size, light.size_y = G["size"], G["size_y"]
            light.energy = e
            light.color = G["color"]
            light.use_shadow = True
            try:
                light.spread = math.radians(G["spread_deg"])
            except Exception:
                pass
            obj = bpy.data.objects.new(name, light)
            obj.location = (x, y, G["z"])
            # emit UP, with the strip's long axis along the walk (tangent to the arc)
            obj.rotation_euler = (math.pi, 0.0, a + math.pi / 2.0)
            obj["energy_W"] = e
            obj["energy_W_eevee"] = e_eev
            obj["note"] = G["note"]
            for attr in ("visible_camera", "visible_glossy"):
                try:
                    setattr(obj, attr, False)
                except Exception:
                    pass
            coll.objects.link(obj)
            out.append(obj)
    area = G["size"] * G["size_y"]
    print(f"[light_build] {G['name']}: {len(out)} strips of {G['size']}x{G['size_y']} m on r {G['radius']} at "
          f"z {G['z']}, {e:.0f} W each (radiance {e / (math.pi * area):.2f} sky units), "
          f"eevee {e_eev:.0f} W; camera- and glossy-invisible")
    return out


def build_world(az, el, calib, moment):
    old = bpy.data.worlds.get(WORLD_NAME)
    if old:
        bpy.data.worlds.remove(old)
    w = cal.make_sky_world(WORLD_NAME, az, el, SKY, sun_disc=False, strength=SKY_STRENGTH,
                           camera_boost=SKY_CAMERA_BOOST, camera_saturation=SKY_CAMERA_SATURATION,
                           glossy_boost=SKY_GLOSSY_BOOST, glossy_saturation=SKY_GLOSSY_SATURATION,
                           glossy_hue=SKY_GLOSSY_HUE,
                           diffuse_saturation=SKY_DIFFUSE_SATURATION, diffuse_hue=SKY_DIFFUSE_HUE,
                           diffuse_tint=SKY_DIFFUSE_TINT, diffuse_boost=SKY_DIFFUSE_BOOST,
                           diffuse_tint_antisun=SKY_DIFFUSE_TINT_ANTISUN,
                           diffuse_tint_horizon=SKY_DIFFUSE_TINT_HORIZON,
                           diffuse_tint_antisun_p=SKY_DIFFUSE_TINT_ANTISUN_P,
                           diffuse_tint_horizon_p=SKY_DIFFUSE_TINT_HORIZON_P,
                           diffuse_tint_sunside=SKY_DIFFUSE_TINT_SUNSIDE,
                           diffuse_tint_sunside_p=SKY_DIFFUSE_TINT_SUNSIDE_P)  # disc OFF: LIGHT_sun carries it
    w.node_tree.nodes["SKY"].label = "MULTIPLE_SCATTERING sky, disc off (LIGHT_sun provides the sun)"
    ms = w.mist_settings
    ms.use_mist = True
    ms.start, ms.depth, ms.falloff = MIST["start"], MIST["depth"], MIST["falloff"]
    w["moment"] = moment
    w["sun_azimuth_deg"] = az
    w["sun_elevation_deg"] = el
    w["sky_sun_rotation_deg"] = math.degrees(cal.sky_rotation_for_azimuth(az))
    w["sky_rotation_convention"] = "sun_rotation = azimuth - 90 deg (node rotation 0 = world +Y, clockwise); verified empirically"
    for k, v in SKY.items():
        w["sky_" + k] = v
    w["sky_strength_lighting"] = SKY_STRENGTH
    w["sky_camera_boost"] = SKY_CAMERA_BOOST
    w["sky_glossy_boost"] = SKY_GLOSSY_BOOST
    w["sky_diffuse_boost"] = SKY_DIFFUSE_BOOST
    w["sky_camera_saturation"] = SKY_CAMERA_SATURATION
    w["sky_glossy_saturation"] = SKY_GLOSSY_SATURATION
    w["sky_glossy_hue"] = SKY_GLOSSY_HUE
    w["sky_diffuse_saturation"] = SKY_DIFFUSE_SATURATION
    w["sky_diffuse_hue"] = SKY_DIFFUSE_HUE          # r12 review finding 3: the world carried every other socket but not this one
    w["sky_diffuse_tint"] = list(SKY_DIFFUSE_TINT)
    w["sky_diffuse_tint_antisun"] = SKY_DIFFUSE_TINT_ANTISUN
    w["sky_diffuse_tint_horizon"] = SKY_DIFFUSE_TINT_HORIZON
    w["sky_diffuse_tint_antisun_p"] = SKY_DIFFUSE_TINT_ANTISUN_P
    w["sky_diffuse_tint_horizon_p"] = SKY_DIFFUSE_TINT_HORIZON_P
    w["sky_diffuse_tint_sunside"] = list(SKY_DIFFUSE_TINT_SUNSIDE)
    w["sky_diffuse_tint_sunside_p"] = SKY_DIFFUSE_TINT_SUNSIDE_P
    w["sky_units_E_sun_rgb"] = calib["sky"]["E_sun_rgb"]
    w["sky_units_L_horizon_west"] = calib["sky"]["L_horizon_west"]
    w["sky_units_L_zenith"] = calib["sky"]["L_zenith"]
    return w


def _new(nt, idname, name=None, loc=(0, 0)):
    n = nt.nodes.new(idname)
    n.location = loc
    if name:
        n.name = n.label = name
    return n


def _mix_in(node, name):
    """A ShaderNodeMix input picked by name AND type (r12 review finding 8; same rule as make_sky_world)."""
    return next(i for i in node.inputs if i.name == name and i.type == "RGBA")


def _mix_out(node):
    return next(o for o in node.outputs if o.type == "RGBA")


def _set_menu(sock, value):
    try:
        sock.default_value = value
    except Exception as e:
        print(f"[light_build] WARNING could not set menu socket {sock.name} = {value}: {e}")


def build_compositor_group(haze_color, exposure):
    """COMP_golden_hour: Image + Mist + Depth in -> warm depth haze (geometry only), bloom, <=0.1 vignette -> Image."""
    for name in (GROUP_NAME, SCENE_TREE_NAME):
        g = bpy.data.node_groups.get(name)
        if g:
            bpy.data.node_groups.remove(g)
    g = bpy.data.node_groups.new(GROUP_NAME, "CompositorNodeTree")
    it = g.interface
    it.new_socket("Image", in_out="INPUT", socket_type="NodeSocketColor")
    it.new_socket("Mist", in_out="INPUT", socket_type="NodeSocketFloat")
    it.new_socket("Depth", in_out="INPUT", socket_type="NodeSocketFloat")
    s = it.new_socket("Haze Color", in_out="INPUT", socket_type="NodeSocketColor"); s.default_value = (*haze_color, 1.0)
    s = it.new_socket("Haze Strength", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = COMP["haze_strength"]; s.min_value = 0.0; s.max_value = 1.0
    s = it.new_socket("Haze Falloff", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = COMP["haze_extinction"]; s.min_value = 0.1; s.max_value = 20.0
    s = it.new_socket("Bloom Threshold", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = COMP["bloom_threshold_display"] / (2.0 ** exposure); s.min_value = 0.0
    s = it.new_socket("Bloom Strength", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = COMP["bloom_strength"]; s.min_value = 0.0; s.max_value = 1.0
    s = it.new_socket("Bloom Size", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = COMP["bloom_size"]; s.min_value = 0.0; s.max_value = 1.0
    s = it.new_socket("Vignette", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = COMP["vignette"]; s.min_value = 0.0; s.max_value = 0.1
    it.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")

    gi = _new(g, "NodeGroupInput", "in", (-900, 0))
    go = _new(g, "NodeGroupOutput", "out", (900, 0))
    # --- geometry mask from depth: background pixels (depth beyond the camera clip) get no haze; the sky model already has it
    is_geo = _new(g, "ShaderNodeMath", "is_geometry", (-600, -250)); is_geo.operation = "LESS_THAN"; is_geo.inputs[1].default_value = 4000.0
    g.links.new(gi.outputs["Depth"], is_geo.inputs[0])
    # --- airlight = cap * (1 - exp(-k * mist)); mist is a plain linear distance ramp (see the MIST/COMP comment)
    kt = _new(g, "ShaderNodeMath", "k_x_mist", (-600, -100)); kt.operation = "MULTIPLY"
    g.links.new(gi.outputs["Mist"], kt.inputs[0]); g.links.new(gi.outputs["Haze Falloff"], kt.inputs[1])
    neg = _new(g, "ShaderNodeMath", "negate", (-500, -60)); neg.operation = "SUBTRACT"; neg.inputs[0].default_value = 0.0
    g.links.new(kt.outputs[0], neg.inputs[1])
    ex = _new(g, "ShaderNodeMath", "exp_minus_kd", (-500, -20)); ex.operation = "EXPONENT"
    g.links.new(neg.outputs[0], ex.inputs[0])
    tr = _new(g, "ShaderNodeMath", "airlight_fraction", (-450, -20)); tr.operation = "SUBTRACT"; tr.inputs[0].default_value = 1.0
    g.links.new(ex.outputs[0], tr.inputs[1])
    f_mist = _new(g, "ShaderNodeMath", "airlight_x_cap", (-400, -150)); f_mist.operation = "MULTIPLY"
    g.links.new(tr.outputs[0], f_mist.inputs[0]); g.links.new(gi.outputs["Haze Strength"], f_mist.inputs[1])
    f_haze = _new(g, "ShaderNodeMath", "haze_factor", (-200, -150)); f_haze.operation = "MULTIPLY"
    g.links.new(f_mist.outputs[0], f_haze.inputs[0]); g.links.new(is_geo.outputs[0], f_haze.inputs[1])
    haze = _new(g, "ShaderNodeMix", "aerial_haze", (0, 100)); haze.data_type = "RGBA"; haze.blend_type = "MIX"; haze.clamp_factor = True
    g.links.new(f_haze.outputs[0], haze.inputs["Factor"])
    # r12 review finding 8: ShaderNodeMix carries one socket per data type and several share a name, so pick them by
    # name AND type (as make_sky_world does) -- the indices differ between Blender versions and a silent mis-link
    # would composite the haze colour into the wrong input with no error.
    g.links.new(gi.outputs["Image"], _mix_in(haze, "A")); g.links.new(gi.outputs["Haze Color"], _mix_in(haze, "B"))
    # --- bloom on sun-lit highlights
    glare = _new(g, "CompositorNodeGlare", "bloom", (250, 100))
    _set_menu(glare.inputs["Type"], "Bloom"); _set_menu(glare.inputs["Quality"], "High")
    g.links.new(_mix_out(haze), glare.inputs["Image"])
    g.links.new(gi.outputs["Bloom Threshold"], glare.inputs["Threshold"])
    g.links.new(gi.outputs["Bloom Strength"], glare.inputs["Strength"])
    g.links.new(gi.outputs["Bloom Size"], glare.inputs["Size"])
    glare.inputs["Smoothness"].default_value = 0.2
    glare.inputs["Saturation"].default_value = 0.9
    # --- vignette: 1 - v * (1 - blurred ellipse)
    mask = _new(g, "CompositorNodeEllipseMask", "vignette_mask", (-200, -450))
    mask.inputs["Size"].default_value = (1.0, 1.0)        # ellipse touches the frame edges; corners outside, feathered
    blur = _new(g, "CompositorNodeBlur", "vignette_blur", (0, -450))
    _set_menu(blur.inputs["Type"], "Gaussian")
    blur.inputs["Size"].default_value = (200.0, 200.0)
    blur.inputs["Extend Bounds"].default_value = False
    g.links.new(mask.outputs["Mask"], blur.inputs["Image"])
    inv = _new(g, "ShaderNodeMath", "one_minus_mask", (200, -450)); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    g.links.new(blur.outputs["Image"], inv.inputs[1])
    vs = _new(g, "ShaderNodeMath", "vignette_scaled", (350, -450)); vs.operation = "MULTIPLY"
    g.links.new(inv.outputs[0], vs.inputs[0]); g.links.new(gi.outputs["Vignette"], vs.inputs[1])
    fac = _new(g, "ShaderNodeMath", "vignette_factor", (500, -450)); fac.operation = "SUBTRACT"; fac.inputs[0].default_value = 1.0
    g.links.new(vs.outputs[0], fac.inputs[1])
    vig = _new(g, "ShaderNodeMix", "apply_vignette", (650, 0)); vig.data_type = "RGBA"; vig.blend_type = "MULTIPLY"
    vig.inputs["Factor"].default_value = 1.0
    g.links.new(glare.outputs["Image"], _mix_in(vig, "A")); g.links.new(fac.outputs[0], _mix_in(vig, "B"))
    g.links.new(_mix_out(vig), go.inputs["Image"])

    print("[light_build] glare sockets:", {i.name: (round(i.default_value, 3) if i.type == "VALUE" else i.default_value) for i in glare.inputs if i.type in ("VALUE", "MENU", "INT")})
    return g


def apply_scene_settings(scene, exposure, group):
    """Colour management + passes + compositor on a scene (light_presets.apply_look does the same on master)."""
    common.setup_scene(scene)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = LOOK
    scene.view_settings.exposure = exposure
    scene.view_settings.gamma = 1.0
    return lp.build_scene_compositor(scene, group, SCENE_TREE_NAME)


# ----------------------------------------------------------------------------- main
def build(moment="morning", calibrate=True, save=True):
    t0 = time.time()
    az, el, source = solar_position(moment)
    print(f"[light_build] moment={moment} {MOMENTS[moment]['tz']} -> azimuth {az:.2f} deg, elevation {el:.2f} deg ({source})")

    report = cal.OUT_DIR / "calibration_report.json"
    calib = None
    if not calibrate and report.exists():
        calib = json.loads(report.read_text())
        if abs(calib["azimuth"] - az) > 0.05 or abs(calib["elevation"] - el) > 0.05 or calib.get("sky_strength") != SKY_STRENGTH:
            print("[light_build] cached calibration is for another moment; recalibrating")
            calib = None
    if calib is None:
        calib = cal.calibrate(az, el, SKY, verbose=False, sky_strength=SKY_STRENGTH)   # ~6 s of tiny Cycles renders
    energy, color = calib["lamp_energy"], tuple(calib["lamp_color"])
    color = (color[0], color[1], color[2] * SUN_BLUE_MULT)      # round 09 chroma lever, see SUN_BLUE_MULT
    exposure = calib["exposure_ev"] + EXPOSURE_BIAS

    # fresh file
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    scene = bpy.context.scene
    scene.name = "Scene"
    coll = common.rebuild_collection(COLLECTION)

    meta = dict(solar_source=source, exposure_calibrated_ev=calib["exposure_ev"], exposure_bias_ev=EXPOSURE_BIAS,
                sky_strength_lighting=SKY_STRENGTH, sky_camera_boost=SKY_CAMERA_BOOST,
                sky_glossy_boost=SKY_GLOSSY_BOOST, sky_diffuse_boost=SKY_DIFFUSE_BOOST,
                sky_camera_saturation=SKY_CAMERA_SATURATION,      # round-10 review nit: the three saturations were
                sky_glossy_saturation=SKY_GLOSSY_SATURATION,      # on the world but not on the sun's meta block,
                sky_diffuse_saturation=SKY_DIFFUSE_SATURATION,    # so a rig read back from the sun was incomplete
                sky_diffuse_hue=SKY_DIFFUSE_HUE,                  # r12 review finding 3: the four round-12 sockets
                sky_diffuse_tint=list(SKY_DIFFUSE_TINT),          # were on neither the sun's meta block nor (hue)
                sky_diffuse_tint_antisun=SKY_DIFFUSE_TINT_ANTISUN,   # the world, so a rig read back from either
                sky_diffuse_tint_horizon=SKY_DIFFUSE_TINT_HORIZON,   # could not be reproduced
                sky_diffuse_tint_antisun_p=SKY_DIFFUSE_TINT_ANTISUN_P,
                sky_diffuse_tint_horizon_p=SKY_DIFFUSE_TINT_HORIZON_P,
                sky_diffuse_tint_sunside=list(SKY_DIFFUSE_TINT_SUNSIDE),      # ROUND 16 (QA-08-3)
                sky_diffuse_tint_sunside_p=SKY_DIFFUSE_TINT_SUNSIDE_P,
                exposure_ev=exposure, look=LOOK, sun_angle_rad=SUN_ANGLE, sun_blue_mult=SUN_BLUE_MULT,
                E_sun_rgb_sky_units=calib["sky"]["E_sun_rgb"], E_sky_horizontal_rgb=calib["sky"]["E_horizontal_disc_off"],
                grey_card_display_srgb=calib["exposure"]["grey_card_display_srgb_agx_base"])
    globals()["SUN_REFERENCE_W"] = energy
    sun = build_sun(coll, az, el, energy, color, moment, meta)
    fill = build_fill(coll)
    shade = build_shade_fill(coll)
    vault_fill = build_vault_fill(coll)     # QA-02-12
    gallery_fill = build_gallery_fill(coll)  # ROUND 17: the colonnade gallery bounce
    probes.ensure_probes(scene, coll)      # QA-01-9: unbaked here (no geometry); the lead bakes them on master
    world = build_world(az, el, calib, moment)
    scene.world = world
    Lh = calib["sky"]["L_horizon_west"]
    haze_color = tuple(Lh[i] * COMP["haze_warmth"][i] for i in range(3))
    group = build_compositor_group(haze_color, exposure)
    scene_tree = apply_scene_settings(scene, exposure, group)
    scene["light_moment"] = moment
    scene["light_exposure_ev"] = exposure
    # fake-user so linking/appending by name always finds them
    world.use_fake_user = True
    group.use_fake_user = True
    scene_tree.use_fake_user = False     # scene trees are rebuilt locally by light_presets.build_scene_compositor

    print(f"[light_build] LIGHT_sun energy {energy:.2f} W/m2 colour ({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f}) angle {SUN_ANGLE} rad")
    print(f"[light_build] exposure {calib['exposure_ev']:.2f} EV (18 % card) + bias {EXPOSURE_BIAS:+.2f} = {exposure:.2f} EV, look {LOOK}")
    print(f"[light_build] haze colour (scene units) {tuple(round(c, 3) for c in haze_color)}; bloom threshold {COMP['bloom_threshold_display'] / 2 ** exposure:.1f} scene units")

    # QA-02-11: the flythrough deliverable used to be built by scripts/light_flythrough.py into the same LIGHT
    # collection AFTER this script, so the next light_build run wiped it (rebuild_collection) and the committed
    # assets/lighting.blend shipped without CAM_flythrough*. build_master.py appends the whole LIGHT collection, so
    # the objects have to survive a rig rebuild. Build them here, last, as part of the rig.
    import light_flythrough as fly
    fly.build(scene)

    if save:
        common.save_blend(common.ASSET_FILES["LIGHT"])
    print(f"[light_build] done in {time.time() - t0:.1f}s")
    return dict(azimuth=az, elevation=el, energy=energy, color=color, exposure=exposure, calib=calib)


if __name__ == "__main__":
    args = common.script_args()
    moment = args[args.index("--moment") + 1] if "--moment" in args else "morning"
    build(moment, calibrate="--no-calibrate" not in args)
