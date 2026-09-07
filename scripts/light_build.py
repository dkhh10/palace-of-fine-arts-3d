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
SKY_STRENGTH = 1.0                 # world strength for LIGHTING (physical). Was 2.0: an art bias from round 05 to open
                                   # the shade, which is what was washing blue over every sunlit face.
SKY_CAMERA_BOOST = 1.20            # what the CAMERA sees of the sky. Swept 3.0 / 2.4 / 2.0 / 1.5 / 1.2 / 1.0 against
                                   # ref 169's sky-top luminance of 165.7: 213.6 / 204.3 / 195.7 / 179.9 / 165.7 /
                                   # 153.2. 1.20 lands on the reference exactly. (The sky is deep on the AgX shoulder,
                                   # which is why it takes a 2.5x cut in scene radiance to move it 23 %.)
SKY_GLOSSY_BOOST = 3.00            # what GLOSSY (reflection) rays see. Split from the camera boost in round 08b: the
                                   # camera's sky had to come down to match ref 169 while the lagoon's reflection had
                                   # to stay up, and one socket could not do both. 1.0 x 3.00 = the 2.0 x 1.50 the
                                   # lagoon reflected before, so the water keeps its brightness.
SKY_CAMERA_SATURATION = 1.20       # saturation of the sky for CAMERA + GLOSSY rays only (Hue/Sat node in the world);
                                   # the diffuse lighting keeps the physical colour. AgX desaturates the bright sky:
                                   # measured B/R 1.37 in the render vs 1.95 in ref 169 at matching luminance.
SUN_BLUE_MULT = 1.00               # multiplier on the CALIBRATED lamp colour's blue channel, applied after the sky's
                                   # own sun disc has been integrated (so the calibration itself stays physical and
                                   # reproducible). Round 09 lever for QA-02-14 / the sunlit-stone chroma: the lamp
                                   # colour is (1.000, 0.607, 0.258) and on a sun-facing surface the sky still
                                   # supplies 10.4 of the 27.7 blue units (calibration_report E_sunfacing), so the
                                   # sun's own blue is the only part of it lighting can take out without touching
                                   # the shade. 1.00 = the physical colour.
SUN_ANGLE = 0.0093                 # rad, real solar disc 0.533 deg (same as the sky's sun_size)
EXPOSURE_BIAS = 1.75               # EV added to the grey-card calibration. Round 08b: SKY_STRENGTH 2.0 -> 1.0 takes
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
LOOK = "AgX - High Contrast"       # Round 05 chose Base Contrast because Punchy crushed the sky-lit shade. At +0.9 EV
                                   # that reason is gone (the shade is 25 % too light, so crushing it is the fix), and
                                   # the look turned out to be the strongest chroma lever of the three available:
                                   # attic R-B, all at strength 1.0 - Base 94.8, Medium High 108.6, High 113.5-118.1,
                                   # Punchy 112.7. Punchy also drops the attic to 144.9 and the water to 71.3, i.e. a
                                   # stop of luminance for no extra chroma over High Contrast. High Contrast it is.
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
# avoid, so the settings below are the physically defensible middle: L = 800 m (a clear-morning extinction length,
# not the 400 m of round 07's ramp) at a 0.50 cap, with the warmth carried by the haze COLOUR instead of its amount.
MIST = dict(start=20.0, depth=2000.0, falloff="LINEAR")   # mist pass = (d - 20) / 2000, clamped; SHAPED in the compositor
COMP = dict(haze_strength=0.50,          # now the CAP: the maximum airlight fraction at infinite distance, not a scale
            haze_extinction=2.5,         # k in cap * (1 - exp(-k * mist)); L = MIST["depth"] / k = 800 m
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
FILL = dict(name="LIGHT_rotunda_bounce", location=(0.0, 0.0, 7.5), size=36.0, energy=7600.0,   # 9000 in
            # round 07; the coffer field came in at 0.50 of cam04's own sky against ref 083's 0.39, and VAULT_FILL
            # below now adds to it as well, so the central disk gives back 0.24 EV (QA-02-12).
            color=(1.0, 0.86, 0.68), spread_deg=150.0,
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
VAULT_FILL = dict(name="LIGHT_rotunda_vault_bounce", n=8, az0=82.0, radius=17.5, z=13.0,
                  size=12.5, size_y=4.0, energy=2400.0, color=(1.0, 0.86, 0.68), spread_deg=90.0,
                  note="QA-02-12 vault-soffit bounce: the plaza light the eight bays get through their own openings")

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


def build_vault_fill(coll):
    """QA-02-12: eight up-facing rectangles, one under each rotunda vault bay (see the VAULT_FILL comment above)."""
    V = VAULT_FILL
    made = []
    for k in range(V["n"]):
        a = math.radians(V["az0"] + 360.0 / V["n"] * k)
        nx, ny = -math.cos(a), math.sin(a)          # arch_params.az_dir: azimuth clockwise from north, north = -X
        name = f"{V['name']}_{k:02d}"
        light = bpy.data.lights.new(name, "AREA")
        light.shape = "RECTANGLE"
        light.size, light.size_y = V["size"], V["size_y"]
        light.energy = V["energy"]
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
        coll.objects.link(obj)
        made.append(obj)
    area = V["size"] * V["size_y"]
    print(f"[light_build] {V['name']}: {V['n']} x {V['size']}x{V['size_y']} m up-facing rectangles at r {V['radius']} "
          f"z {V['z']}, {V['energy']} W each (radiance {V['energy'] / (math.pi * area):.3f} sky units)")
    return made


def build_world(az, el, calib, moment):
    old = bpy.data.worlds.get(WORLD_NAME)
    if old:
        bpy.data.worlds.remove(old)
    w = cal.make_sky_world(WORLD_NAME, az, el, SKY, sun_disc=False, strength=SKY_STRENGTH,
                           camera_boost=SKY_CAMERA_BOOST, camera_saturation=SKY_CAMERA_SATURATION,
                           glossy_boost=SKY_GLOSSY_BOOST)  # disc OFF: LIGHT_sun carries it
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
    w["sky_camera_glossy_saturation"] = SKY_CAMERA_SATURATION
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
    g.links.new(gi.outputs["Image"], haze.inputs[6]); g.links.new(gi.outputs["Haze Color"], haze.inputs[7])
    # --- bloom on sun-lit highlights
    glare = _new(g, "CompositorNodeGlare", "bloom", (250, 100))
    _set_menu(glare.inputs["Type"], "Bloom"); _set_menu(glare.inputs["Quality"], "High")
    g.links.new(haze.outputs[2], glare.inputs["Image"])
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
    g.links.new(glare.outputs["Image"], vig.inputs[6]); g.links.new(fac.outputs[0], vig.inputs[7])
    g.links.new(vig.outputs[2], go.inputs["Image"])

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
                sky_glossy_boost=SKY_GLOSSY_BOOST,
                exposure_ev=exposure, look=LOOK, sun_angle_rad=SUN_ANGLE, sun_blue_mult=SUN_BLUE_MULT,
                E_sun_rgb_sky_units=calib["sky"]["E_sun_rgb"], E_sky_horizontal_rgb=calib["sky"]["E_horizontal_disc_off"],
                grey_card_display_srgb=calib["exposure"]["grey_card_display_srgb_agx_base"])
    sun = build_sun(coll, az, el, energy, color, moment, meta)
    fill = build_fill(coll)
    vault_fill = build_vault_fill(coll)     # QA-02-12
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
