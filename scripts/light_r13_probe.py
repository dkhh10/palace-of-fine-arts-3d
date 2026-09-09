"""Round-13 diagnostic: WHAT does Eevee's world lighting actually evaluate?

Round 12 shipped the shade as three DIFFUSE-only world sockets (boost 2.50, a blue tint, anti-sun and horizon
weights) gated by `Fac = 1 - min(is_camera + is_glossy, 1)`. Cycles honours them; the lead's Eevee hero frame does
not (shaded attic 94.9 / hue 42.2 / sat 0.769 against Cycles' 116.7 / 35.4 / 0.412), while the visible sky and the
lagoon match to 0.2 lum. The hypothesis is that Eevee evaluates the world's Light Path node as a CAMERA ray when it
captures the world for lighting, so the lighting gets `camera_boost` (2.10) and `camera_saturation` (1.20) and none
of the tint. 94.9 / 116.7 = 0.813 against 2.10 / 2.50 = 0.840, which is the right size but not a proof.

This script proves it on a 12-second scene instead of on an 11 M-triangle master: one pure-diffuse sphere, no lamps,
lit by the world alone, rendered to linear EXR (no view transform, so every number is a physical ratio).

  * `sh`  setups have NO light probe, so Eevee lights the sphere from the world's spherical harmonics.
  * `vol` setups put one baked irradiance volume around it, which is the path that lights the master's interiors
    and anything else inside LIGHTPROBE_rotunda / LIGHTPROBE_colonnade.
  * `flatbake` bakes that volume with `split_rays=False` (the round-13 world: the diffuse branch applied to every
    ray) and then RENDERS with the shipped world. That is the proposed fix, measured end to end.

    scripts/blender_run.sh 900 -- --background --python scripts/light_r13_probe.py
"""
import bpy, os, sys, math, json, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_build as lb
import light_calibrate as cal
import light_probes as probes

OUT = Path(common.RENDERS) / "logs" / "r13_probe"
OUT.mkdir(parents=True, exist_ok=True)
RES = 192
AZ, EL, SRC = lb.solar_position("morning")
SUN = common.sun_direction(AZ, EL)          # points TOWARD the sun


def build_scene():
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    s = bpy.context.scene
    bpy.ops.mesh.primitive_uv_sphere_add(radius=5.0, segments=64, ring_count=32, location=(0, 0, 0))
    sph = bpy.context.object
    sph.name = "PROBE_sphere"
    bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new("PROBE_diffuse")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    for n in ("Specular IOR Level", "Specular"):
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = 0.0
    sph.data.materials.append(m)
    # camera on the ANTI-SUN side, horizontal: the pixel at the centre of the sphere has a normal pointing straight
    # away from the sun, i.e. exactly the geometry of the hero's shaded attic face.
    cam_d = -SUN.copy()
    cam_d.z = 0.0
    cam_d.normalize()
    cd = bpy.data.cameras.new("PROBE_cam")
    cd.type = "ORTHO"
    cd.ortho_scale = 12.0
    cam = bpy.data.objects.new("PROBE_cam", cd)
    cam.location = cam_d * 40.0
    cam.rotation_euler = common.lookat_rotation(cam.location, (0.0, 0.0, 0.0))
    s.collection.objects.link(cam)
    s.camera = cam
    s.render.resolution_x = s.render.resolution_y = RES
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.render.image_settings.color_mode = "RGB"
    s.view_settings.view_transform = "Standard"     # EXR is written pre-transform anyway; keep it honest
    s.view_settings.exposure = 0.0
    s.view_settings.look = "None"
    return s, sph


def world(tag, **kw):
    p = dict(strength=lb.SKY_STRENGTH, camera_boost=lb.SKY_CAMERA_BOOST, camera_saturation=lb.SKY_CAMERA_SATURATION,
             glossy_boost=lb.SKY_GLOSSY_BOOST, glossy_saturation=lb.SKY_GLOSSY_SATURATION,
             diffuse_saturation=lb.SKY_DIFFUSE_SATURATION, diffuse_hue=lb.SKY_DIFFUSE_HUE,
             diffuse_tint=lb.SKY_DIFFUSE_TINT, diffuse_boost=lb.SKY_DIFFUSE_BOOST,
             diffuse_tint_antisun=lb.SKY_DIFFUSE_TINT_ANTISUN, diffuse_tint_horizon=lb.SKY_DIFFUSE_TINT_HORIZON)
    p.update(kw)
    old = bpy.data.worlds.get("W_" + tag)
    if old:
        bpy.data.worlds.remove(old)
    return cal.make_sky_world("W_" + tag, AZ, EL, lb.SKY, sun_disc=False, **p)


def add_volume(scene):
    for o in [o for o in scene.objects if o.type == "LIGHT_PROBE"]:
        bpy.data.objects.remove(o, do_unlink=True)
    lp = bpy.data.lightprobes.new("PROBE_vol", type="VOLUME")
    for k, v in probes.PROBE_DATA.items():
        try:
            setattr(lp, k, v)
        except Exception:
            pass
    lp.resolution_x = lp.resolution_y = lp.resolution_z = 8
    obj = bpy.data.objects.new("PROBE_vol", lp)
    obj.location = (0, 0, 0)
    obj.scale = (9.0, 9.0, 9.0)
    scene.collection.objects.link(obj)
    return obj


def bake_volume(scene):
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.gi_irradiance_pool_size = probes.IRRADIANCE_POOL
    try:
        bpy.ops.object.lightprobe_cache_free(subset="ALL")
    except Exception:
        pass
    bpy.ops.object.lightprobe_cache_bake(subset="ALL")


def render(scene, engine, name):
    fp = OUT / f"{name}.exr"
    scene.render.filepath = str(fp)
    if engine == "CYCLES":
        scene.render.engine = "CYCLES"
        common.configure_cycles(scene, samples=256, denoise=True)
    else:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = 32
        scene.eevee.use_raytracing = False
        scene.eevee.gi_irradiance_pool_size = probes.IRRADIANCE_POOL
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r13probe] {name}: {time.time()-t:.1f}s", flush=True)
    return str(fp)


def measure(path, label):
    """Mean linear RGB of the sphere's centre disc (normal = anti-sun) and of its top (normal = up)."""
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    px = list(img.pixels)
    ch = img.channels
    W, H = img.size

    def box(x0, y0, x1, y1):
        acc = [0.0, 0.0, 0.0]
        n = 0
        for y in range(y0, y1):
            row = (H - 1 - y) * W * ch          # bpy images are bottom-up
            for x in range(x0, x1):
                i = row + x * ch
                acc[0] += px[i]; acc[1] += px[i + 1]; acc[2] += px[i + 2]
                n += 1
        return [v / max(1, n) for v in acc]

    c = RES // 2
    r = RES // 12
    centre = box(c - r, c - r, c + r, c + r)
    top = box(c - r, RES // 8, c + r, RES // 8 + 2 * r)
    bpy.data.images.remove(img)
    print(f"[r13probe] {label:26s} centre {centre[0]:.4f} {centre[1]:.4f} {centre[2]:.4f}  "
          f"lum {0.2126*centre[0]+0.7152*centre[1]+0.0722*centre[2]:.4f}  B/R {centre[2]/max(1e-9,centre[0]):.3f}"
          f"   top lum {0.2126*top[0]+0.7152*top[1]+0.0722*top[2]:.4f}", flush=True)
    return dict(label=label, centre=centre, top=top)


if __name__ == "__main__":
    res = []
    scene, sph = build_scene()

    W_ship = world("ship")
    W_cb1 = world("cb1", camera_boost=1.0)
    W_db1 = world("db1", diffuse_boost=1.0)
    W_flat = world("flat", split_rays=False)

    # ---- no probe: Eevee's world spherical harmonics
    scene.world = W_ship
    res.append(measure(render(scene, "CYCLES", "cyc_ship"), "CYCLES ship (truth)"))
    res.append(measure(render(scene, "EEVEE", "eev_sh_ship"), "EEVEE sh ship"))
    scene.world = W_cb1
    res.append(measure(render(scene, "EEVEE", "eev_sh_cb1"), "EEVEE sh camera_boost=1"))
    scene.world = W_db1
    res.append(measure(render(scene, "EEVEE", "eev_sh_db1"), "EEVEE sh diffuse_boost=1"))
    scene.world = W_flat
    res.append(measure(render(scene, "EEVEE", "eev_sh_flat"), "EEVEE sh split_rays=False"))

    # ---- baked irradiance volume
    add_volume(scene)
    scene.world = W_ship
    bake_volume(scene)
    res.append(measure(render(scene, "EEVEE", "eev_vol_ship"), "EEVEE vol bake=ship"))
    scene.world = W_flat
    bake_volume(scene)
    scene.world = W_ship                      # THE FIX: bake with the flat world, render with the shipped one
    res.append(measure(render(scene, "EEVEE", "eev_vol_flatbake"), "EEVEE vol bake=flat"))

    (OUT / "r13_probe.json").write_text(json.dumps(res, indent=1))
    print("[r13probe] done", flush=True)
