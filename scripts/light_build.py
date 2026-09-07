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
SKY_STRENGTH = 2.0                 # world strength for LIGHTING. The model's direct:diffuse ratio at el 7.4 is 9.9
                                   # (E_sun 59.7 vs E_sky_horizontal 6.0, luminance); real clear-sky data at this
                                   # elevation give ~5, and refs 054/169 show shade only ~3 stops under sunlit. x2.
SKY_CAMERA_BOOST = 1.15            # extra factor for camera + glossy rays only. Round 07 (QA-01-12): with the
                                   # exposure bias below the sky no longer needs 1.6; a smaller boost also keeps the
                                   # blue out of AgX's desaturating highlight roll-off. Glossy still gets it, so the
                                   # lagoon keeps a bright sky reflection.
SKY_CAMERA_SATURATION = 1.35       # saturation of the sky for CAMERA + GLOSSY rays only (Hue/Sat node in the world);
                                   # the diffuse lighting keeps the physical colour. AgX desaturates the bright sky:
                                   # measured B/R 1.37 in the render vs 1.95 in ref 169 at matching luminance.
SUN_ANGLE = 0.0093                 # rad, real solar disc 0.533 deg (same as the sky's sun_size)
EXPOSURE_BIAS = 1.10               # EV added to the grey-card calibration. Round 07 (QA-01-12): at +0.5 the sunlit
                                   # attic rendered Y 0.287 against ref 169's 0.410 (30 % dark). +0.6 EV closes about
                                   # two thirds of that; the rest is albedo (materials is warming the concrete).
LOOK = "AgX - Base Contrast"       # 'Punchy' crushes the sky-lit shade (A/B in lighting_notes)
MIST = dict(start=30.0, depth=700.0, falloff="LINEAR")    # mist pass 0 at 30 m -> 1 at 730 m. Round 07 (QA-01-12):
                                   # 1500 m put only 6 % haze on the colonnade ends at 200 m; ref 169 clearly veils
                                   # them. 700 m gives 12 % at 110 m, 24 % at 200 m, 67 % at 500 m (backdrop hills).
COMP = dict(haze_strength=0.85, haze_warmth=(1.22, 1.0, 0.74),   # haze colour = measured west-horizon radiance x warmth
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
FILL = dict(name="LIGHT_rotunda_bounce", location=(0.0, 0.0, 7.5), size=36.0, energy=170.0,
            color=(1.0, 0.86, 0.68), spread_deg=150.0,
            note="QA-01-9 interior bounce fill: the plaza/lagoon bounce the model has no geometry for")

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
    obj.location = FILL["location"]      # rotation 0 -> an area light emits along +Z, i.e. straight up into the vault
    obj["note"] = FILL["note"]
    obj["energy_W"] = FILL["energy"]
    coll.objects.link(obj)
    print(f"[light_build] {FILL['name']}: disk r {FILL['size']/2:.1f} m at z {FILL['location'][2]}, {FILL['energy']} W, up-facing")
    return obj


def build_world(az, el, calib, moment):
    old = bpy.data.worlds.get(WORLD_NAME)
    if old:
        bpy.data.worlds.remove(old)
    w = cal.make_sky_world(WORLD_NAME, az, el, SKY, sun_disc=False, strength=SKY_STRENGTH,
                           camera_boost=SKY_CAMERA_BOOST, camera_saturation=SKY_CAMERA_SATURATION)  # disc OFF: LIGHT_sun carries it
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
    w["sky_camera_glossy_boost"] = SKY_CAMERA_BOOST
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
    f_mist = _new(g, "ShaderNodeMath", "mist_x_strength", (-400, -150)); f_mist.operation = "MULTIPLY"
    g.links.new(gi.outputs["Mist"], f_mist.inputs[0]); g.links.new(gi.outputs["Haze Strength"], f_mist.inputs[1])
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
    exposure = calib["exposure_ev"] + EXPOSURE_BIAS

    # fresh file
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    scene = bpy.context.scene
    scene.name = "Scene"
    coll = common.rebuild_collection(COLLECTION)

    meta = dict(solar_source=source, exposure_calibrated_ev=calib["exposure_ev"], exposure_bias_ev=EXPOSURE_BIAS,
                sky_strength_lighting=SKY_STRENGTH, sky_camera_glossy_boost=SKY_CAMERA_BOOST,
                exposure_ev=exposure, look=LOOK, sun_angle_rad=SUN_ANGLE,
                E_sun_rgb_sky_units=calib["sky"]["E_sun_rgb"], E_sky_horizontal_rgb=calib["sky"]["E_horizontal_disc_off"],
                grey_card_display_srgb=calib["exposure"]["grey_card_display_srgb_agx_base"])
    sun = build_sun(coll, az, el, energy, color, moment, meta)
    fill = build_fill(coll)
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
    if save:
        common.save_blend(common.ASSET_FILES["LIGHT"])
    print(f"[light_build] done in {time.time() - t0:.1f}s")
    return dict(azimuth=az, elevation=el, energy=energy, color=color, exposure=exposure, calib=calib)


if __name__ == "__main__":
    args = common.script_args()
    moment = args[args.index("--moment") + 1] if "--moment" in args else "morning"
    build(moment, calibrate="--no-calibrate" not in args)
