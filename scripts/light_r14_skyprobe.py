"""Round-14 sky ILLUMINANT probe (QA-06-2). Cheap, master-free, and it answers the question the round is about.

QA-06-2 is not a level defect, it is a CHROMA defect of the light itself: the r12 diffuse tint (1.0, 0.65, 17.0)
has G < R, and no product of a sky colour with a G < R multiplier is a sky colour -- it is magenta-blue. Which
surfaces show it is decided by how much of their light comes from the diffuse sky rather than from warm bounce,
so the hero's shaded attic (deep under the entablature, >90 % bounce) passed while every up-facing surface in the
build -- cam03's walk, cam06's roofs / plaza / trees, the lagoon's murk -- went violet.

Measuring that on the master costs a 6-camera pass per candidate. This tool measures the ILLUMINANT instead:
four neutral / ochre Lambertian cards in an otherwise empty scene, each seeing only the world, rendered through
the SAME AgX + look + calibrated exposure the master uses, so the numbers are directly comparable with the
displayed hue / sat of a render box.

  up        horizontal, normal +Z          -- the walk, the roofs, the plaza, the water's murk
  wall_as   vertical, normal ANTI-sun      -- the shaded stone the r12 tint was tuned on
  wall_sun  vertical, normal toward the sun-- the sunlit stone the tint must not reach
  wall_x    vertical, normal 90 deg off    -- the general shaded flank

    scripts/blender_run.sh 900 -- --background --python scripts/light_r14_skyprobe.py -- \
        --case "tag=r13" --case "tag=cand;tg=1.6;tb=9;thp=3"
"""
import bpy, os, sys, math, time
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_build as lb
import light_calibrate as cal

args = common.script_args()


def arg(name, default, n=0):
    if name not in args:
        return default
    out = []
    for v in args[args.index(name) + 1:]:
        if v.startswith("--"):
            break
        out.append(v)
        if n and len(out) >= n:
            break
    return out or default


DEFAULTS = dict(sky=lb.SKY_STRENGTH, db=lb.SKY_DIFFUSE_BOOST,
                tr=lb.SKY_DIFFUSE_TINT[0], tg=lb.SKY_DIFFUSE_TINT[1], tb=lb.SKY_DIFFUSE_TINT[2],
                ta=lb.SKY_DIFFUSE_TINT_ANTISUN, th=lb.SKY_DIFFUSE_TINT_HORIZON,
                tap=1.0, thp=1.0,          # ROUND 14: the exponents on the two weights
                dsat=lb.SKY_DIFFUSE_SATURATION, dhue=lb.SKY_DIFFUSE_HUE,
                sun=0.0)                   # 1 = LIGHT_sun on as well (the sunlit control)
RES = int(arg("--res", ["96"], n=1)[0])
SAMPLES = int(arg("--samples", ["64"], n=1)[0])
OUT = Path(arg("--out", [str(common.RENDERS / "previews" / "lighting" / "skyprobe")], n=1)[0])
OUT.mkdir(parents=True, exist_ok=True)

# Lambertian test albedos, LINEAR. `grey` is a neutral 0.18 card: its rendered colour IS the illuminant.
# `ochre` is the build's shaded-stone albedo, back-solved in round 12 from the four-row table (docs/lighting_notes
# 21.5: the stone's G/R is 0.78-0.81 and its B/R about 0.34 under both illuminations), so the ochre card predicts
# what a real shaded wall does with a candidate sky.
ALBEDO = dict(grey=(0.180, 0.180, 0.180), ochre=(0.180, 0.140, 0.061))


def parse(case):
    c = dict(DEFAULTS, tag=None)
    for part in case.split(";"):
        part = part.strip()
        if not part:
            continue
        k, v = part.split("=", 1)
        c[k.strip()] = v if k.strip() == "tag" else float(v)
    return c


CASES = [parse(x) for x in arg("--case", ["tag=r13"])]

AZ, EL, SRC = lb.solar_position("morning")
SUNDIR = common.sun_direction(AZ, EL)          # unit vector FROM the scene TOWARD the sun
_m = cal.measure_sky(AZ, EL, lb.SKY, samples=512)
_e = cal.measure_exposure(AZ, EL, _m["lamp_energy"], _m["sun_color_normalised"], lb.SKY,
                          samples=256, sky_strength=lb.SKY_STRENGTH)
EXPOSURE = _e["exposure_ev"] + lb.EXPOSURE_BIAS
print(f"[skyprobe] sun az {AZ:.2f} el {EL:.2f} ({SRC}); lamp {_m['lamp_energy']:.2f} W/m2; "
      f"exposure {EXPOSURE:.3f} EV; look {lb.LOOK!r}", flush=True)

# ---------------------------------------------------------------------------------------------- the probe scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
scene = bpy.context.scene
common.setup_scene(scene)
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = lb.LOOK
scene.view_settings.exposure = EXPOSURE

_up = Vector((0.0, 0.0, 1.0))
_as = Vector((-SUNDIR.x, -SUNDIR.y, 0.0)).normalized()        # anti-sun, in plan
_su = Vector((SUNDIR.x, SUNDIR.y, 0.0)).normalized()
_pp = Vector((-_as.y, _as.x, 0.0)).normalized()
# `wall_ov` is `wall_as` with a 2 m soffit 1 m above its top edge -- the hero's shaded attic geometry, which sees
# the sky only in near-horizontal directions. It is the card that predicts the box QA-06-2 must not break.
ORIENT = dict(up=_up, wall_as=_as, wall_sun=_su, wall_x=_pp, wall_ov=_as)
OVERHANG = {"wall_ov"}

MATS = {}
for a_name, rgb in ALBEDO.items():
    mat = bpy.data.materials.new(f"PROBE_{a_name}")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    d.inputs["Roughness"].default_value = 0.0
    nt.links.new(d.outputs[0], out.inputs["Surface"])
    MATS[a_name] = mat

CARDS = {}
for o_name, n in ORIENT.items():
    for a_name in ALBEDO:
        me = bpy.data.meshes.new(f"PROBE_{o_name}_{a_name}")
        # a 4 m card, its own plane, 200 m from every other card so no card can bounce onto another
        k = len(CARDS) * 200.0
        u = n.cross(Vector((0, 0, 1))) if abs(n.z) < 0.9 else Vector((1, 0, 0))
        u = u.normalized()
        v = n.cross(u).normalized()
        c = Vector((k, 0.0, 60.0))
        me.from_pydata([c + 2 * (su_ * u + sv_ * v) for su_, sv_ in ((-1, -1), (1, -1), (1, 1), (-1, 1))],
                       [], [(0, 1, 2, 3)])
        me.update()
        ob = bpy.data.objects.new(f"PROBE_{o_name}_{a_name}", me)
        ob.data.materials.append(MATS[a_name])
        scene.collection.objects.link(ob)
        extra = []
        if o_name in OVERHANG:
            top = c + 2 * v + n * 0.0 + Vector((0, 0, 1.0))
            me2 = bpy.data.meshes.new(f"PROBE_{o_name}_{a_name}_soffit")
            me2.from_pydata([top + su_ * 2 * u + sv_ * n * 2.0
                             for su_, sv_ in ((-1, 0.0), (1, 0.0), (1, 1.0), (-1, 1.0))], [], [(0, 1, 2, 3)])
            me2.update()
            ov = bpy.data.objects.new(f"PROBE_{o_name}_{a_name}_soffit", me2)
            ov.data.materials.append(MATS[a_name])
            scene.collection.objects.link(ov)
            extra.append(ov)
        CARDS[(o_name, a_name)] = (ob, c, n, extra)

cam_data = bpy.data.cameras.new("PROBE_CAM")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 3.0
cam = bpy.data.objects.new("PROBE_CAM", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

sun = bpy.data.objects.new("PROBE_SUN", bpy.data.lights.new("PROBE_SUN", "SUN"))
sun.data.angle = lb.SUN_ANGLE
scene.collection.objects.link(sun)
common.aim_sun(sun, AZ, EL)

scene.render.resolution_x = scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.image_settings.color_depth = "8"
scene.render.film_transparent = False


def srgb_stats(px):
    r, g, b = px
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d < 1e-9:
        h = 0.0
    elif mx == r:
        h = (60.0 * ((g - b) / d)) % 360.0
    elif mx == g:
        h = 60.0 * ((b - r) / d) + 120.0
    else:
        h = 60.0 * ((r - g) / d) + 240.0
    return dict(lum=0.2126 * r + 0.7152 * g + 0.0722 * b, hue=h, sat=d / max(mx, 1e-9), rb=r - b,
                rgb=(round(r, 1), round(g, 1), round(b, 1)))


def shoot(name):
    fp = OUT / f"{name}.png"
    scene.render.filepath = str(fp)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(fp))
    px = list(img.pixels)
    n = len(px) // 4
    acc = [0.0, 0.0, 0.0]
    for i in range(n):
        for ch in range(3):
            acc[ch] += px[4 * i + ch]
    bpy.data.images.remove(img)
    # the PNG is already display-referred; Blender reads it back through the sRGB colorspace, so undo that
    def to_srgb8(x):
        x = max(0.0, min(1.0, x / n))
        return 255.0 * (12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055)
    return srgb_stats([to_srgb8(c) for c in acc])


ROWS = []
for c in CASES:
    tag = c["tag"] or "case"
    w = bpy.data.worlds.get(f"R14P_{tag}")
    if w:
        bpy.data.worlds.remove(w)
    w = cal.make_sky_world(f"R14P_{tag}", AZ, EL, lb.SKY, sun_disc=False, strength=c["sky"],
                           camera_boost=lb.SKY_CAMERA_BOOST, camera_saturation=lb.SKY_CAMERA_SATURATION,
                           glossy_boost=lb.SKY_GLOSSY_BOOST, glossy_saturation=lb.SKY_GLOSSY_SATURATION,
                           diffuse_saturation=c["dsat"], diffuse_hue=c["dhue"], diffuse_boost=c["db"],
                           diffuse_tint=(c["tr"], c["tg"], c["tb"]),
                           diffuse_tint_antisun=c["ta"], diffuse_tint_horizon=c["th"],
                           diffuse_tint_antisun_p=c["tap"], diffuse_tint_horizon_p=c["thp"])
    scene.world = w
    sun.data.energy = _m["lamp_energy"] if c["sun"] > 0.5 else 0.0
    sc = _m["sun_color_normalised"]
    sun.data.color = (sc[0], sc[1], sc[2] * lb.SUN_BLUE_MULT)
    common.configure_cycles(scene, samples=SAMPLES, denoise=False)
    scene.cycles.use_adaptive_sampling = False
    t0 = time.time()
    print(f"\n[skyprobe] {tag}: db {c['db']:g} tint ({c['tr']:g}, {c['tg']:g}, {c['tb']:g}) "
          f"ta {c['ta']:g}^{c['tap']:g} th {c['th']:g}^{c['thp']:g} sun {'ON' if c['sun'] > 0.5 else 'off'}", flush=True)
    print(f"  {'card':16s} {'sRGB':>18s} {'lum':>7s} {'hue':>7s} {'sat':>7s} {'R-B':>7s}")
    for o_name in ORIENT:
        for a_name in ALBEDO:
            ob, cpos, n, extra = CARDS[(o_name, a_name)]
            cam.location = cpos + n * 8.0
            cam.rotation_mode = "QUATERNION"
            cam.rotation_quaternion = (-n).to_track_quat("-Z", "Y")
            for k, (o2, _, _, ex2) in CARDS.items():
                o2.hide_render = (k != (o_name, a_name))
                for e in ex2:
                    e.hide_render = (k != (o_name, a_name))
            s = shoot(f"{tag}_{o_name}_{a_name}")
            s.update(tag=tag, card=o_name, albedo=a_name)
            ROWS.append(s)
            print(f"  {o_name + '/' + a_name:16s} {str(s['rgb']):>18s} {s['lum']:7.1f} {s['hue']:7.1f} "
                  f"{s['sat']:7.3f} {s['rb']:+7.1f}")
    print(f"[skyprobe] {tag} done in {time.time() - t0:.0f}s", flush=True)

print("\n[skyprobe] summary (grey card = the illuminant itself)")
print(f"  {'tag':14s} {'ochre up':>16s} {'ochre wall_as':>16s} {'ochre wall_ov':>16s} "
      f"{'ochre wall_sun':>16s} {'grey wall_ov':>16s}")
for c in CASES:
    tag = c["tag"] or "case"
    g = {(r["card"], r["albedo"]): r for r in ROWS if r["tag"] == tag}
    print(f"  {tag:14s} {g[('up','ochre')]['hue']:8.1f}/{g[('up','ochre')]['sat']:.3f} "
          f"{g[('wall_as','ochre')]['hue']:8.1f}/{g[('wall_as','ochre')]['sat']:.3f} "
          f"{g[('wall_ov','ochre')]['hue']:8.1f}/{g[('wall_ov','ochre')]['sat']:.3f} "
          f"{g[('wall_sun','ochre')]['hue']:8.1f}/{g[('wall_sun','ochre')]['sat']:.3f} "
          f"{g[('wall_ov','grey')]['hue']:8.1f}/{g[('wall_ov','grey')]['sat']:.3f}")
print("[skyprobe] done", flush=True)
