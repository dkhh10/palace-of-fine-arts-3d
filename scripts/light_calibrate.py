"""Radiometric calibration + convention checks for the lighting rig (Lighting & Rendering specialist).

Importable (light_build.py calls `calibrate(az, el, sky)`), or run standalone for the full report:
    blender -b --python scripts/light_calibrate.py [-- --convention] [-- --az 118.5 --el 7.4]

What it measures, all with tiny Cycles renders written as 32-bit EXR and read back with bpy:
  1. Sun-lamp convention: a white Lambertian plane facing a Sun lamp of energy E renders E/pi (verified 1/pi).
  2. Sky-disc integration: the same plane facing the sun direction under the MULTIPLE_SCATTERING sky, disc ON minus
     disc OFF, gives the sun irradiance per channel -> the Sun lamp's energy (luminance) and colour (chromaticity)
     that reproduce the sky's own sun. Also reports sky-only irradiance on the sun-facing and horizontal planes.
  3. Exposure: an 18 % grey card facing the sun under lamp + sky (disc OFF) -> exposure EV so the card is 0.18
     scene-linear before AgX; then a check render through AgX reports the display value of the card.
  4. (--convention) Empirical check of ShaderNodeTexSky.sun_rotation: an equirectangular render with the sky's disc ON
     is compared against colour-coded emissive markers at true north / east / zenith, and a "pole shadow" photo
     (lamp + disc) is written to renders/previews/lighting/calibration/.
"""
import bpy, os, sys, math, time, json
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

OUT_DIR = common.RENDERS / "previews" / "lighting" / "calibration"

# Sky parameters used when none are given (kept in sync with light_build.SKY by the caller).
DEFAULT_SKY = dict(sun_size_deg=0.545, sun_intensity=1.0, altitude=5.0, air_density=1.0, aerosol_density=1.0, ozone_density=1.0)


# ----------------------------------------------------------------------------- image IO
def read_image(path):
    """Return (w, h, list-of-floats RGBA) of an image file (EXR = scene linear, PNG = display encoded)."""
    img = bpy.data.images.load(str(path), check_existing=False)
    w, h = img.size
    px = [0.0] * (w * h * 4)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return w, h, px


def mean_rgb(path, box=None):
    """Average RGB of an image (optionally of a centred box fraction, e.g. 0.5)."""
    w, h, px = read_image(path)
    x0, x1, y0, y1 = 0, w, 0, h
    if box:
        x0, x1 = int(w * (0.5 - box / 2)), int(w * (0.5 + box / 2))
        y0, y1 = int(h * (0.5 - box / 2)), int(h * (0.5 + box / 2))
    acc = [0.0, 0.0, 0.0]; n = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            i = (y * w + x) * 4
            acc[0] += px[i]; acc[1] += px[i + 1]; acc[2] += px[i + 2]; n += 1
    return [a / n for a in acc]


def argmax_pixel(path, weight=(0.2126, 0.7152, 0.0722)):
    """(x, y, value) of the pixel maximising the weighted channel sum. y counts from the BOTTOM (bpy convention)."""
    w, h, px = read_image(path)
    best, bx, by = -1e30, 0, 0
    for y in range(h):
        row = y * w * 4
        for x in range(w):
            i = row + x * 4
            v = px[i] * weight[0] + px[i + 1] * weight[1] + px[i + 2] * weight[2]
            if v > best:
                best, bx, by = v, x, y
    return bx, by, best, w, h


# ----------------------------------------------------------------------------- scene helpers
def _fresh_scene():
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    s = bpy.context.scene
    common.setup_scene(s)
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0.0
    s.render.film_transparent = False
    return s


def _diffuse_material(name, albedo):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (albedo, albedo, albedo, 1.0)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.0
    return m


def _emissive_material(name, rgb, strength=1000.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def _card(name, normal, size, albedo, scene):
    """A square Lambertian card of the given albedo whose +Z normal is rotated onto `normal`, at the origin."""
    me = bpy.data.meshes.new(name)
    h = size / 2
    me.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
    me.update()
    obj = bpy.data.objects.new(name, me)
    obj.rotation_euler = Vector(normal).to_track_quat("Z", "Y").to_euler()
    scene.collection.objects.link(obj)
    obj.data.materials.append(_diffuse_material(name + "_mat", albedo))
    return obj


def _ortho_camera_looking_along(scene, direction, distance=5.0, ortho_scale=1.0):
    """Orthographic camera placed `distance` along `direction` from the origin, looking back at the origin."""
    cam = bpy.data.objects.new("CAL_cam", bpy.data.cameras.new("CAL_cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho_scale
    d = Vector(direction).normalized()
    cam.location = d * distance
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def _sat_stage(nt, name, color_out, fac_out, saturation, hue=0.5):
    """One Hue/Saturation stage that applies `saturation` (and, round 12, `hue`) to the rays selected by fac_out and
    passes every other ray class through untouched.

    Round 12 (QA-05-1): `hue` is Blender's Hue/Saturation Hue input, 0.5 = no shift, and one unit is a full turn of the
    hue circle, so hue = 0.5 + d rotates the sky's colour by d*360 deg. It exists because the DIFFUSE socket needed a
    lever that saturation alone cannot supply: at a 7.4 deg sun the sky that lands on shaded stone is horizon-weighted
    and therefore WARM, so raising its saturation makes the shade more orange, not more blue (round 10 and round 11
    both measured that). Rotating it toward blue first, then saturating, is what moves the shade's hue."""
    hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.name = name
    hs.inputs["Saturation"].default_value = saturation
    hs.inputs["Hue"].default_value = hue
    nt.links.new(color_out, hs.inputs["Color"])
    nt.links.new(fac_out, hs.inputs["Fac"])          # Fac blends between the input and the saturated colour
    return hs.outputs["Color"]


def make_sky_world(name, az_deg, el_deg, sky=None, sun_disc=False, strength=1.0, camera_boost=1.0,
                   camera_saturation=1.0, glossy_boost=None, glossy_saturation=None, glossy_hue=0.5,
                   diffuse_saturation=1.0,
                   diffuse_boost=1.0, diffuse_hue=0.5, diffuse_tint=None, diffuse_tint_antisun=0.0, diffuse_tint_horizon=0.0,
                   diffuse_tint_antisun_p=1.0, diffuse_tint_horizon_p=1.0,
                   split_rays=True):
    """World with a MULTIPLE_SCATTERING sky. sun_rotation = azimuth (clockwise from north), verified in check_convention().
    strength scales the whole sky (lighting AND visible sky); camera_boost additionally scales what camera rays see and
    glossy_boost what glossy (reflection) rays see, leaving diffuse lighting untouched (Light Path node);
    camera_saturation does the same for saturation (AgX desaturates the bright sky, so the visible blue needs help that
    the lighting must not get).

    Round 08b: camera and glossy used to share one boost. They want different numbers now - the sky the CAMERA sees has
    to come down to match ref 169 while the sky the LAGOON reflects has to stay up, and one socket cannot do both. If
    glossy_boost is None it falls back to camera_boost, which is the old single-knob behaviour.

    Round 11 (QA-04-2): `diffuse_boost` completes the set. It scales the sky on every ray that is neither camera nor
    glossy, i.e. exactly the light that lands on shaded stone, and it is the only sky knob that does NOT move the
    sunlit numbers through the exposure calibration (which is driven by SKY_STRENGTH). The per-ray gain becomes
        gain = diffuse_boost + is_camera*(camera_boost - diffuse_boost) + is_glossy*(glossy_boost - diffuse_boost)
    so the three sockets stay independent: raising diffuse_boost cannot change the visible sky or the lagoon's
    reflection of it."""
    sky = dict(DEFAULT_SKY, **(sky or {}))
    w = bpy.data.worlds.new(name)
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    node = nt.nodes.new("ShaderNodeTexSky")
    node.name = "SKY"
    node.sky_type = "MULTIPLE_SCATTERING"
    node.sun_disc = sun_disc
    node.sun_size = math.radians(sky["sun_size_deg"])
    node.sun_intensity = sky["sun_intensity"]
    node.sun_elevation = math.radians(el_deg)
    node.sun_rotation = sky_rotation_for_azimuth(az_deg)
    node.altitude = sky["altitude"]
    node.air_density = sky["air_density"]
    node.aerosol_density = sky["aerosol_density"]
    node.ozone_density = sky["ozone_density"]
    sky_color = node.outputs[0]
    glossy_boost = camera_boost if glossy_boost is None else glossy_boost
    glossy_saturation = camera_saturation if glossy_saturation is None else glossy_saturation
    # ROUND 13 (Eevee shade, QA-05-1). `split_rays=False` builds the SAME world with the DIFFUSE branch applied to
    # every ray: no Light Path node, boost = diffuse_boost, the camera and glossy saturation stages dropped, and the
    # diffuse tint (with its anti-sun and horizon weights) multiplied in unconditionally. It is not a look; it is the
    # world that `light_probes.bake` swaps in while it bakes the Eevee irradiance volumes, because Eevee evaluates
    # the world's Light Path node as a CAMERA ray in that capture and therefore bakes the camera branch (measured:
    # shaded attic 94.9 Eevee vs 116.7 Cycles, ratio 0.813 = camera_boost / diffuse_boost). Applying the diffuse
    # branch to every ray makes the capture correct whatever ray class Eevee claims it is.
    vis_out = None          # 1 for camera OR glossy rays (used by the saturation blend)
    cam_ray = gl_ray = None
    gain_out = None         # per-ray multiplier: camera_boost on camera rays, glossy_boost on glossy rays, else 1
    if not split_rays:
        strength = strength * diffuse_boost          # the gain every ray gets; no Light Path node is built
        zero = nt.nodes.new("ShaderNodeValue"); zero.name = "no_camera_or_glossy"
        zero.outputs[0].default_value = 0.0          # "is camera or glossy" == 0, so every Fac below is the diffuse one
        vis_out = zero.outputs[0]
        camera_saturation = glossy_saturation = 1.0  # their stages would have Fac 0; do not build them
    elif (camera_boost != 1.0 or glossy_boost != 1.0 or diffuse_boost != 1.0 or camera_saturation != 1.0
            or glossy_saturation != 1.0 or diffuse_saturation != 1.0 or abs(diffuse_hue - 0.5) > 1e-9
            or abs(glossy_hue - 0.5) > 1e-9):
        lpn = nt.nodes.new("ShaderNodeLightPath"); lpn.name = "LIGHT_PATH"
        vis = nt.nodes.new("ShaderNodeMath"); vis.operation = "ADD"; vis.name = "cam_or_glossy"
        nt.links.new(lpn.outputs["Is Camera Ray"], vis.inputs[0]); nt.links.new(lpn.outputs["Is Glossy Ray"], vis.inputs[1])
        clampn = nt.nodes.new("ShaderNodeMath"); clampn.operation = "MINIMUM"; clampn.inputs[1].default_value = 1.0
        nt.links.new(vis.outputs[0], clampn.inputs[0])
        vis_out = clampn.outputs[0]
        cam_ray, gl_ray = lpn.outputs["Is Camera Ray"], lpn.outputs["Is Glossy Ray"]
        # gain = diffuse_boost + is_camera*(camera_boost-db) + is_glossy*(glossy_boost-db); a camera ray is never
        # also a glossy ray, and everything that is neither (the light landing on shaded stone) keeps diffuse_boost.
        cam_t = nt.nodes.new("ShaderNodeMath"); cam_t.operation = "MULTIPLY_ADD"; cam_t.name = "camera_boost"
        cam_t.inputs[1].default_value = camera_boost - diffuse_boost; cam_t.inputs[2].default_value = diffuse_boost
        nt.links.new(lpn.outputs["Is Camera Ray"], cam_t.inputs[0])
        gl_t = nt.nodes.new("ShaderNodeMath"); gl_t.operation = "MULTIPLY_ADD"; gl_t.name = "glossy_boost"
        gl_t.inputs[1].default_value = glossy_boost - diffuse_boost
        nt.links.new(lpn.outputs["Is Glossy Ray"], gl_t.inputs[0])
        nt.links.new(cam_t.outputs[0], gl_t.inputs[2])
        gain_out = gl_t.outputs[0]
    # Round 10: three independent saturations, chained. Each stage's Fac selects one ray class and passes every other
    # class through untouched, so DIFFUSE (the light that lands on the shaded stone), CAMERA (the visible sky) and
    # GLOSSY (the sky the lagoon mirrors) can each carry their own sky chroma. camera/glossy were one knob before;
    # the water is a Fresnel mirror of the horizon at grazing angles, so the near-water chroma (QA-03-7) is set by
    # the glossy socket alone and could not be moved without dragging the visible sky with it.
    if (camera_saturation != 1.0 or glossy_saturation != 1.0 or diffuse_saturation != 1.0
            or abs(diffuse_hue - 0.5) > 1e-9 or abs(glossy_hue - 0.5) > 1e-9):
        if diffuse_saturation != 1.0 or abs(diffuse_hue - 0.5) > 1e-9:
            inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.name = "not_cam_or_glossy"
            inv.inputs[0].default_value = 1.0
            nt.links.new(vis_out, inv.inputs[1])
            sky_color = _sat_stage(nt, "sky_saturation_diffuse", sky_color, inv.outputs[0], diffuse_saturation,
                                   hue=diffuse_hue)
        if camera_saturation != 1.0:
            sky_color = _sat_stage(nt, "sky_saturation", sky_color, cam_ray, camera_saturation)
        if glossy_saturation != 1.0 or abs(glossy_hue - 0.5) > 1e-9:
            # ROUND 15 (QA-07-1): `glossy_hue` is the GLOSSY twin of `diffuse_hue`. At 87-89 deg incidence the open
            # lagoon is a Fresnel mirror of the horizon band, so what the near-water and flank boxes read as "the
            # water's colour" IS the sky's colour on this socket. Rounds 10-14 could only change its LEVEL
            # (glossy_boost) and its CHROMA (glossy_saturation); neither can move a hue, and the measured defect is
            # a HUE one (rendered 227.9 against ref 169's 190.0). Camera rays never traverse this stage, so the
            # visible sky's own hue -- which already matches ref 169 to 0.5 deg -- is held exactly still.
            sky_color = _sat_stage(nt, "sky_saturation_glossy", sky_color, gl_ray, glossy_saturation,
                                   hue=glossy_hue)
    # Round 12 (QA-05-1): a DIFFUSE-only colour tint, i.e. a white balance on the light that lands on shaded stone.
    # It is the lever the shade actually needs and a hue rotation is not: the render's shaded attic is (122, 94, 22)
    # against ref 169's (141, 111, 81), i.e. it is short 59 units of BLUE and only ~18 of R and G, and a hue rotation
    # big enough to blue the warm horizon band (+0.47 of a turn) would rotate the zenith's blue round to red. A
    # multiply by a blue-biased tint makes every sky direction bluer, horizon included, and leaves the ordering of
    # the sky's own gradient intact. Camera and glossy rays never see it (Fac = not_cam_or_glossy), so the visible
    # sky and the lagoon's reflection are held exactly still.
    if diffuse_tint is not None and tuple(diffuse_tint) != (1.0, 1.0, 1.0):
        if vis_out is None:
            lpn = nt.nodes.new("ShaderNodeLightPath"); lpn.name = "LIGHT_PATH"
            vis = nt.nodes.new("ShaderNodeMath"); vis.operation = "ADD"; vis.name = "cam_or_glossy"
            nt.links.new(lpn.outputs["Is Camera Ray"], vis.inputs[0])
            nt.links.new(lpn.outputs["Is Glossy Ray"], vis.inputs[1])
            clampn = nt.nodes.new("ShaderNodeMath"); clampn.operation = "MINIMUM"; clampn.inputs[1].default_value = 1.0
            nt.links.new(vis.outputs[0], clampn.inputs[0])
            vis_out = clampn.outputs[0]
        inv2 = nt.nodes.new("ShaderNodeMath"); inv2.operation = "SUBTRACT"; inv2.name = "not_cam_or_glossy_tint"
        inv2.inputs[0].default_value = 1.0
        nt.links.new(vis_out, inv2.inputs[1])
        fac_out = inv2.outputs[0]
        # ROUND 12 (QA-05-1): weight the tint by how far the ray points AWAY from the sun. A shaded face samples the
        # anti-sun half of the dome (its hemisphere is centred on its own normal, which points away from the sun);
        # a sunlit face samples the sun half; a horizontal surface samples both and gets about half. So an anti-sun
        # weighted tint is the only sky lever that reaches shaded stone WITHOUT the same multiple landing on the
        # sunlit stone next to it -- which is the whole reason rounds 10 and 11 could not use the diffuse sky.
        # It is also the physically right shape: at a 7 deg sun the anti-sun sky IS the blue part of the dome.
        # w = clamp(0.5 + 0.5 * (Incoming . sun)), and Incoming is -ray_direction, so w = 1 for a ray travelling
        # straight away from the sun and 0 for one travelling into it. diffuse_tint_antisun blends w in:
        # 0 = the uniform tint, 1 = fully anti-sun weighted.
        if diffuse_tint_antisun > 0.0:
            geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.name = "ray_direction"
            dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.name = "dot_sun"
            sd = common.sun_direction(az_deg, el_deg)
            dot.inputs[1].default_value = (sd.x, sd.y, sd.z)
            nt.links.new(geo.outputs["Incoming"], dot.inputs[0])
            wt = nt.nodes.new("ShaderNodeMath"); wt.operation = "MULTIPLY_ADD"; wt.name = "antisun_weight"
            wt.inputs[1].default_value = 0.5; wt.inputs[2].default_value = 0.5; wt.use_clamp = True
            nt.links.new(dot.outputs["Value"], wt.inputs[0])   # NOT `w`: `w` is the world being built
            wt_out = wt.outputs[0]
            if abs(diffuse_tint_antisun_p - 1.0) > 1e-9:      # ROUND 14, see the horizon exponent below
                pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.name = "antisun_weight_p"
                pw.inputs[1].default_value = diffuse_tint_antisun_p; pw.use_clamp = True
                nt.links.new(wt_out, pw.inputs[0])
                wt_out = pw.outputs[0]
            blend = nt.nodes.new("ShaderNodeMapRange"); blend.name = "antisun_blend"
            blend.inputs["From Min"].default_value = 0.0; blend.inputs["From Max"].default_value = 1.0
            blend.inputs["To Min"].default_value = 1.0 - diffuse_tint_antisun
            blend.inputs["To Max"].default_value = 1.0
            nt.links.new(wt_out, blend.inputs["Value"])
            m = nt.nodes.new("ShaderNodeMath"); m.operation = "MULTIPLY"; m.name = "tint_fac_antisun"
            nt.links.new(inv2.outputs[0], m.inputs[0])
            nt.links.new(blend.outputs["Result"], m.inputs[1])
            fac_out = m.outputs[0]
        # ROUND 12b: the second discriminator, by ray ELEVATION. A vertical shaded wall samples the sky in
        # near-HORIZONTAL directions (its hemisphere is centred on a horizontal normal); a horizontal surface --
        # the lagoon, the plaza -- samples it cosine-weighted about the ZENITH. So weighting the tint by
        # 1 - |ray.z| puts it on shaded stone and keeps it off the water, which is what the first ship of this
        # round got wrong: the lagoon's murk term went to saturation 0.457 (QA's window is 0.22-0.32) because a
        # tint applied to the whole dome reaches anything that faces up. Physically this is the anti-sun horizon
        # band, which at a 7 deg sun is the bluest part of a real sky (the Earth-shadow / Belt of Venus band).
        if diffuse_tint_horizon > 0.0:
            geo2 = nt.nodes.new("ShaderNodeNewGeometry"); geo2.name = "ray_direction_z"
            sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.name = "ray_z"
            nt.links.new(geo2.outputs["Incoming"], sep.inputs[0])
            ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; ab.name = "abs_ray_z"
            nt.links.new(sep.outputs["Z"], ab.inputs[0])
            hz = nt.nodes.new("ShaderNodeMath"); hz.operation = "SUBTRACT"; hz.name = "horizon_weight"
            hz.inputs[0].default_value = 1.0; hz.use_clamp = True
            nt.links.new(ab.outputs[0], hz.inputs[1])
            hz_out = hz.outputs[0]
            # ROUND 14 (QA-06-2): the SHARPNESS of the elevation weight, not its amount, is the discriminator that
            # separates a shaded WALL from anything that faces UP. A vertical wall samples the sky cosine-weighted
            # about a HORIZONTAL normal, so its mean |ray.z| is ~0.42 and its mean (1-|z|) ~0.58; an up-facing
            # surface samples it cosine-weighted about the ZENITH (E[z] = 2/3), mean (1-|z|) ~0.33. The
            # discrimination is E[(1-|z|)^p] per hemisphere; the single table lives in light_build.py next to
            # SKY_DIFFUSE_TINT_HORIZON_P: 1.73x at p = 1, 3.07x at p = 3, 5.02x at the SHIPPED p = 6. Round 12 spent the
            # amount of this weight (it ships at 1.0, the maximum) and had no lever left; the exponent is a new one,
            # and it is the MORE physical shape -- the anti-sun horizon band (the Earth-shadow / Belt of Venus band)
            # really is a narrow band a few degrees deep, not a linear ramp from zenith to horizon.
            if abs(diffuse_tint_horizon_p - 1.0) > 1e-9:
                hp = nt.nodes.new("ShaderNodeMath"); hp.operation = "POWER"; hp.name = "horizon_weight_p"
                hp.inputs[1].default_value = diffuse_tint_horizon_p; hp.use_clamp = True
                nt.links.new(hz_out, hp.inputs[0])
                hz_out = hp.outputs[0]
            hb = nt.nodes.new("ShaderNodeMapRange"); hb.name = "horizon_blend"
            hb.inputs["From Min"].default_value = 0.0; hb.inputs["From Max"].default_value = 1.0
            hb.inputs["To Min"].default_value = 1.0 - diffuse_tint_horizon
            hb.inputs["To Max"].default_value = 1.0
            nt.links.new(hz_out, hb.inputs["Value"])
            mh = nt.nodes.new("ShaderNodeMath"); mh.operation = "MULTIPLY"; mh.name = "tint_fac_horizon"
            nt.links.new(fac_out, mh.inputs[0])
            nt.links.new(hb.outputs["Result"], mh.inputs[1])
            fac_out = mh.outputs[0]
        mixn = nt.nodes.new("ShaderNodeMix"); mixn.name = "sky_tint_diffuse"
        mixn.data_type = "RGBA"; mixn.blend_type = "MULTIPLY"; mixn.clamp_factor = True
        # ShaderNodeMix carries one socket per data type and several share a name, so pick them by name AND type
        # rather than by index: the indices differ between Blender versions and a silent mis-link would render a
        # whole sweep against the wrong graph.
        fac = next(i for i in mixn.inputs if i.name == "Factor" and i.type == "VALUE")
        a_in = next(i for i in mixn.inputs if i.name == "A" and i.type == "RGBA")
        b_in = next(i for i in mixn.inputs if i.name == "B" and i.type == "RGBA")
        res = next(o for o in mixn.outputs if o.type == "RGBA")
        nt.links.new(fac_out, fac)
        nt.links.new(sky_color, a_in)
        b_in.default_value = (diffuse_tint[0], diffuse_tint[1], diffuse_tint[2], 1.0)
        sky_color = res
    nt.links.new(sky_color, bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    if gain_out is not None:
        mult = nt.nodes.new("ShaderNodeMath"); mult.operation = "MULTIPLY"; mult.name = "strength"
        mult.inputs[1].default_value = strength
        nt.links.new(gain_out, mult.inputs[0])
        nt.links.new(mult.outputs[0], bg.inputs["Strength"])
    nt.links.new(bg.outputs[0], out.inputs[0])
    try:   # better importance sampling of the tiny sun disc
        w.cycles.sampling_method = "MANUAL"
        w.cycles.sample_map_resolution = 4096
    except Exception:
        pass
    return w


def sky_rotation_for_azimuth(az_deg):
    """ShaderNodeTexSky.sun_rotation (radians) that puts the sky's sun at compass azimuth az_deg (clockwise from north,
    north = -X, east = +Y).

    VERIFIED EMPIRICALLY by check_convention() (equirect render vs N/E/zenith markers, 2026-09-07): the node's
    sun_rotation = 0 puts the sun at world +Y and increases CLOCKWISE seen from above (toward +X). Blender therefore
    treats +Y as its 'north'; since our +Y is EAST, sun_rotation = azimuth - 90 deg. With the naive
    sun_rotation = azimuth the disc landed at 208.1 deg for a requested 118.5 deg (delta +89.6 deg)."""
    return math.radians((az_deg - 90.0) % 360.0)


def _render_exr(scene, path, res=8, samples=256):
    scene.render.engine = "CYCLES"
    common.configure_cycles(scene, samples=samples, denoise=False)
    scene.cycles.use_adaptive_sampling = False
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "NONE"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def _render_png(scene, path, res=(64, 64), samples=64, view="AgX", look="None", exposure=0.0):
    scene.render.engine = "CYCLES"
    common.configure_cycles(scene, samples=samples, denoise=False)
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = view
    scene.view_settings.look = look
    scene.view_settings.exposure = exposure
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


# ----------------------------------------------------------------------------- measurements
def measure_lamp_convention():
    """White card facing a Sun lamp of energy 1 under a black world. Expect 1/pi."""
    s = _fresh_scene()
    _card("CAL_card", (0, 0, 1), 4.0, 1.0, s)
    _ortho_camera_looking_along(s, (0, 0, 1))
    sun = bpy.data.objects.new("CAL_sun", bpy.data.lights.new("CAL_sun", "SUN"))
    sun.data.energy = 1.0; sun.data.angle = 0.0093
    s.collection.objects.link(sun)
    w = bpy.data.worlds.new("CAL_black"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    s.world = w
    p = _render_exr(s, OUT_DIR / "cal_lamp_convention.exr", res=8, samples=64)
    v = mean_rgb(p)
    return dict(white_card_radiance_per_unit_energy=v[0], expected_1_over_pi=1 / math.pi)


def measure_sky(az_deg, el_deg, sky=None, samples=1024):
    """Integrate the sky's sun disc and sky dome on Lambertian cards. Returns irradiances in the sky node's units."""
    d = common.sun_direction(az_deg, el_deg)
    res = {}
    for tag, disc in (("disc_on", True), ("disc_off", False)):
        s = _fresh_scene()
        s.world = make_sky_world(f"CAL_sky_{tag}", az_deg, el_deg, sky, sun_disc=disc)
        _card("CAL_card_sun", d, 2.0, 1.0, s)        # facing the sun
        _ortho_camera_looking_along(s, d, distance=3.0, ortho_scale=0.8)
        L = mean_rgb(_render_exr(s, OUT_DIR / f"cal_sky_sunfacing_{tag}.exr", res=8, samples=samples))
        res[f"E_sunfacing_{tag}"] = [v * math.pi for v in L]    # irradiance = pi * radiance of a white card
    # horizontal card, disc off (sky-only irradiance on the ground) and disc on (total)
    for tag, disc in (("disc_on", True), ("disc_off", False)):
        s = _fresh_scene()
        s.world = make_sky_world(f"CAL_sky_h_{tag}", az_deg, el_deg, sky, sun_disc=disc)
        _card("CAL_card_h", (0, 0, 1), 2.0, 1.0, s)
        _ortho_camera_looking_along(s, (0, 0, 1), distance=3.0, ortho_scale=0.8)
        L = mean_rgb(_render_exr(s, OUT_DIR / f"cal_sky_horizontal_{tag}.exr", res=8, samples=samples))
        res[f"E_horizontal_{tag}"] = [v * math.pi for v in L]
    # sky radiance samples: zenith and the horizon opposite the sun (what the hero camera sees behind the rotunda)
    s = _fresh_scene()
    s.world = make_sky_world("CAL_sky_rad", az_deg, el_deg, sky, sun_disc=False)
    cam = bpy.data.objects.new("CAL_cam", bpy.data.cameras.new("CAL_cam"))
    cam.data.lens = 200.0
    s.collection.objects.link(cam); s.camera = cam
    for tag, direction in (("zenith", (0, 0, 1)), ("horizon_west", (0, -1, 0.05)), ("horizon_sunward", common.sun_direction(az_deg, 3.0)), ("sky_30deg_south", common.sun_direction(180, 30))):
        cam.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
        L = mean_rgb(_render_exr(s, OUT_DIR / f"cal_sky_radiance_{tag}.exr", res=8, samples=64))
        res[f"L_{tag}"] = L
    E_sun = [a - b for a, b in zip(res["E_sunfacing_disc_on"], res["E_sunfacing_disc_off"])]
    lum = 0.2126 * E_sun[0] + 0.7152 * E_sun[1] + 0.0722 * E_sun[2]
    res["E_sun_rgb"] = E_sun
    res["E_sun_luminance"] = lum
    res["sun_color_normalised"] = [v / max(E_sun) for v in E_sun]
    res["lamp_energy"] = max(E_sun)          # lamp energy x colour (max channel = 1) reproduces E_sun exactly
    return res


def measure_exposure(az_deg, el_deg, lamp_energy, lamp_color, sky=None, samples=512, sky_strength=1.0):
    """18 % grey card facing the sun under Sun lamp + sky (disc OFF). Returns exposure so the card is 0.18 pre-AgX."""
    d = common.sun_direction(az_deg, el_deg)
    s = _fresh_scene()
    s.world = make_sky_world("CAL_sky_exposure", az_deg, el_deg, sky, sun_disc=False, strength=sky_strength)
    _card("CAL_grey_card", d, 2.0, 0.18, s)
    _ortho_camera_looking_along(s, d, distance=3.0, ortho_scale=0.8)
    sun = bpy.data.objects.new("CAL_sun", bpy.data.lights.new("CAL_sun", "SUN"))
    sun.data.energy = lamp_energy; sun.data.color = lamp_color; sun.data.angle = 0.0093
    s.collection.objects.link(sun)
    common.aim_sun(sun, az_deg, el_deg)
    L = mean_rgb(_render_exr(s, OUT_DIR / "cal_grey_card_linear.exr", res=8, samples=samples))
    lum = 0.2126 * L[0] + 0.7152 * L[1] + 0.0722 * L[2]
    exposure = math.log2(0.18 / lum)
    out = dict(grey_card_linear_rgb=L, grey_card_linear_luminance=lum, exposure_ev=exposure)
    # verification through AgX at that exposure (display-referred sRGB value of the card)
    p = _render_png(s, OUT_DIR / "cal_grey_card_agx.png", res=(32, 32), samples=64, view="AgX", look="None", exposure=exposure)
    out["grey_card_display_srgb_agx_base"] = mean_rgb(p)
    # same card facing the zenith in the shade of a wall would be the shade reference; instead report the horizontal card
    return out


# ----------------------------------------------------------------------------- convention check
def check_convention(az_deg, el_deg, sky=None):
    """Equirectangular render: where does the sky's sun disc land compared with markers at true N, E and zenith?"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    W, H = 1440, 720          # 0.25 deg per pixel
    # -- markers under a black world
    s = _fresh_scene()
    cam = bpy.data.objects.new("CAL_pano", bpy.data.cameras.new("CAL_pano"))
    cam.data.type = "PANO"
    cam.data.panorama_type = "EQUIRECTANGULAR"
    cam.rotation_euler = (math.radians(90), 0, 0)   # looking east (+Y), up = +Z
    s.collection.objects.link(cam); s.camera = cam
    markers = {"north": ((-40, 0, 0), (1, 0, 0)), "east": ((0, 40, 0), (0, 1, 0)), "zenith": ((0, 0, 40), (0, 0, 1))}
    for name, (loc, rgb) in markers.items():
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=loc)
        o = bpy.context.object; o.name = "CAL_marker_" + name
        o.data.materials.append(_emissive_material("CAL_em_" + name, rgb, 100.0))
    w = bpy.data.worlds.new("CAL_black"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    s.world = w
    p = _render_exr_wh(s, OUT_DIR / "cal_pano_markers.exr", W, H, samples=16)
    ww, hh, px = read_image(p)
    found = {}
    for name, (loc, rgb) in markers.items():
        c = rgb.index(1)
        found[name] = _centroid(px, ww, hh, lambda i: px[i + c] - px[i + (c + 1) % 3] - px[i + (c + 2) % 3])
    # -- the sky alone with the disc ON
    for o in [o for o in s.objects if o.name.startswith("CAL_marker")]:
        bpy.data.objects.remove(o, do_unlink=True)
    s.world = make_sky_world("CAL_sky_disc", az_deg, el_deg, sky, sun_disc=True)
    p2 = _render_exr_wh(s, OUT_DIR / "cal_pano_sky_disc.exr", W, H, samples=16)
    _, _, dv, _, _ = argmax_pixel(p2)
    ww2, hh2, px2 = read_image(p2)
    dx, dy = _centroid(px2, ww2, hh2, lambda i: 0.2126 * px2[i] + 0.7152 * px2[i + 1] + 0.0722 * px2[i + 2])
    # -- decode: equirect is linear in azimuth (columns) and elevation (rows)
    uN, vN = found["north"]; uE, vE = found["east"]; uZ, vZ = found["zenith"]
    du = (uE - uN)
    if du < -ww / 2: du += ww
    if du > ww / 2: du -= ww
    deg_per_px_az = 90.0 / du                    # signed: +ve if azimuth increases to the right
    v_eq = (vN + vE) / 2.0
    deg_per_px_el = 90.0 / (vZ - v_eq)
    def px_to_azel(x, y):
        ddx = x - uN
        if ddx > ww / 2: ddx -= ww
        if ddx < -ww / 2: ddx += ww
        return (ddx * deg_per_px_az) % 360.0, (y - v_eq) * deg_per_px_el
    disc_az, disc_el = px_to_azel(dx, dy)
    result = dict(markers_px=found, disc_px=(dx, dy), disc_peak_value=dv, deg_per_px=(deg_per_px_az, deg_per_px_el),
                  requested=(az_deg, el_deg), measured_disc=(disc_az, disc_el),
                  delta=(((disc_az - az_deg + 180) % 360) - 180, disc_el - el_deg))
    # -- the "pole shadow" photo: lamp + disc together
    s = _fresh_scene()
    ground = _card("CAL_ground", (0, 0, 1), 400.0, 0.35, s)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=12.0, location=(0, 0, 6.0), vertices=32)
    pole = bpy.context.object; pole.name = "CAL_pole"; pole.data.materials.append(_diffuse_material("CAL_pole_mat", 0.5))
    d = common.sun_direction(az_deg, el_deg)
    sun = bpy.data.objects.new("CAL_sun", bpy.data.lights.new("CAL_sun", "SUN"))
    sun.data.energy = 3.0; sun.data.angle = 0.0093; s.collection.objects.link(sun); common.aim_sun(sun, az_deg, el_deg)
    s.world = make_sky_world("CAL_sky_photo", az_deg, el_deg, dict(sky or {}, sun_size_deg=2.0), sun_disc=True)
    s.world.node_tree.nodes["SKY"].sun_intensity = 0.02   # a 2-degree, dimmed disc so it is visible next to the shadow
    cam = bpy.data.objects.new("CAL_cam", bpy.data.cameras.new("CAL_cam")); cam.data.lens = 24.0
    horiz = Vector((d.x, d.y, 0)).normalized()
    side = Vector((-horiz.y, horiz.x, 0))
    cam.location = -horiz * 24.0 + side * 16.0 + Vector((0, 0, 2.5))   # behind and beside the shadow, looking at pole + sun
    cam.rotation_euler = (Vector((0, 0, 6.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    s.collection.objects.link(cam); s.camera = cam
    p3 = _render_png(s, OUT_DIR / "convention_pole_shadow_and_disc.png", res=(960, 540), samples=48, view="AgX", exposure=-1.5)
    result["pole_shadow_png"] = str(p3)
    for big in (OUT_DIR / "cal_pano_markers.exr", OUT_DIR / "cal_pano_sky_disc.exr"):
        try:
            os.remove(big)     # 16 MB each, intermediate only
        except OSError:
            pass
    (OUT_DIR / "convention_check.json").write_text(json.dumps(result, indent=1, default=str))
    return result


def _centroid(px, w, h, score):
    """Sub-pixel centroid (x, y) of the pixels scoring above half of the maximum score. Rows count from the bottom."""
    vals = [score((y * w + x) * 4) for y in range(h) for x in range(w)]
    m = max(vals)
    sx = sy = sw = 0.0
    for y in range(h):
        for x in range(w):
            v = vals[y * w + x]
            if v > 0.5 * m:
                sx += (x + 0.5) * v; sy += (y + 0.5) * v; sw += v
    return sx / sw, sy / sw


def _render_exr_wh(scene, path, w, h, samples=16):
    scene.render.engine = "CYCLES"
    common.configure_cycles(scene, samples=samples, denoise=False)
    scene.cycles.use_adaptive_sampling = False
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "NONE"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


# ----------------------------------------------------------------------------- driver
def calibrate(az_deg, el_deg, sky=None, verbose=True, sky_strength=1.0):
    """Full calibration used by light_build.py. Returns a dict with lamp energy/colour and exposure.
    sky_strength is the world Background strength used for LIGHTING (the sun disc integral is independent of it)."""
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {"azimuth": az_deg, "elevation": el_deg, "sky": dict(DEFAULT_SKY, **(sky or {})), "sky_strength": sky_strength}
    out["lamp_convention"] = measure_lamp_convention()
    out["sky"] = measure_sky(az_deg, el_deg, sky)
    color = out["sky"]["sun_color_normalised"]
    energy = out["sky"]["lamp_energy"]
    out["exposure"] = measure_exposure(az_deg, el_deg, energy, color, sky, sky_strength=sky_strength)
    out["lamp_energy"] = energy
    out["lamp_color"] = color
    out["exposure_ev"] = out["exposure"]["exposure_ev"]
    out["seconds"] = time.time() - t0
    for f in OUT_DIR.glob("cal_*.exr"):
        f.unlink()           # tiny intermediates; the numbers live in calibration_report.json
    # r13 review carry 11: round before writing. Re-measuring the same rig moved the file by ~1e-7 per value and
    # produced a diff on every run; 6 significant figures is far finer than any number the notes quote.
    def _round(v):
        if isinstance(v, float):
            return float(f"{v:.6g}")
        if isinstance(v, dict):
            return {k: _round(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [_round(x) for x in v]
        return v
    (OUT_DIR / "calibration_report.json").write_text(json.dumps(_round(out), indent=1, default=str))
    if verbose:
        print("[light_calibrate] " + json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    args = common.script_args()
    az = float(args[args.index("--az") + 1]) if "--az" in args else 118.5
    el = float(args[args.index("--el") + 1]) if "--el" in args else 7.4
    if "--convention" in args:
        r = check_convention(az, el)
        print("[light_calibrate] convention check:", json.dumps(r, indent=1, default=str))
    else:
        calibrate(az, el)
