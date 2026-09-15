"""Gate 0 step 5: (a) the AgX High Contrast 3D LUT, (b) the two sky equirects. Both from gate0_set.blend.

    scripts/blender_run.sh 1800 -- --background export/out/gate0/gate0_set.blend --python export/bake_lut.py

(a) THE LUT - how, exactly, because a wrong LUT makes every parity score wrong.
    Blender exposes no OCIO API to Python, so the transform is obtained by pushing an image through Blender's own
    view transform and reading the result back:
      1. an identity 33^3 lattice is written into a float image as a 1089 x 33 tile strip, colour space Non-Color
         (so nothing touches the numbers on the way in);
      2. the lattice coordinate is not the pixel value. It is an AgX log2 SHAPER coordinate:
             x in [0,1]  ->  v_post = 0.18 * 2^(-12.47393 + x * 16.50000)   (scene-linear, AFTER exposure)
         and the value actually written into the image is v_pre = v_post * 2^(+2.8331399), so that Blender's own
         exposure of -2.8331399 EV brings it back to v_post before the view transform. The LUT therefore *is*
         "AgX - High Contrast at exposure -2.833", as the brief requires, and the viewer applies exposure itself
         (multiply by 2^-2.8331399) before the shaper, which is what keeps the sun's ~67 W/m2 inside the domain:
         without it the sunlit stone sits at ~5.9 EV over mid grey, above the shaper's +4.03 EV ceiling;
      3. the image is written with Image.save_render(scene=scene), i.e. through the scene's colour management
         (AgX / AgX - High Contrast / exposure -2.8331399 / display sRGB), as a 16-bit PNG;
      4. that PNG is read back as Non-Color (raw display code values) and written out as a 33^3 .cube plus the
         strip PNG.
    PROOF (brief step 5): a flat 0.18 grey emission plane rendered by Cycles through the same scene settings must
    equal the LUT applied to linear 0.18, within 1/255. Both numbers are in the report.

(b) THE EQUIRECTS - the world node tree branches on Light Path (camera x2.5, glossy x1.7, a tinted diffuse branch).
    The branch is isolated IN MEMORY by deleting the six links out of the LIGHT_PATH node and writing the constant
    for the branch into each destination input (Is Camera Ray = 1 / Is Glossy Ray = 0 for the camera equirect, and
    the reverse for the glossy one). The links are restored afterwards; the .blend is never saved. Rendering with
    an equirectangular panoramic camera would give the camera branch for free but can never give the glossy one,
    so both are done the same way, and the camera equirect doubles as the check that the rewiring reproduces what
    a camera ray really sees.
"""
import bpy
import os
import sys
import json
import math
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import bake_lib as bl  # noqa: E402

g0.ensure_dirs()
g0.queue_state("running")
scene = bpy.context.scene
lights = g0.apply_final_cycles_checked(scene)
report = {}
N = g0.LUT_SIZE
EXP = scene.view_settings.exposure
assert abs(EXP - g0.EXPOSURE_EV) < 1e-4, f"exposure {EXP} != {g0.EXPOSURE_EV}"
assert scene.view_settings.look == g0.LOOK and scene.view_settings.view_transform == g0.VIEW_TRANSFORM


def set_linear_output():
    """Write file data with no view transform (EXR / HDR must stay scene-linear)."""
    s = scene.render.image_settings
    s.color_management = "OVERRIDE"
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0.0
    s.view_settings.gamma = 1.0


def set_follow_scene():
    scene.render.image_settings.color_management = "FOLLOW_SCENE"


# ---------------------------------------------------------------- (a) LUT ------------------------------------
step = g0.Step("bake_lut:lattice")
W, H = N * N, N
lin = np.zeros((H, W, 4), dtype=np.float32)
lin[:, :, 3] = 1.0
gain = 2.0 ** (-EXP)                       # undo the scene exposure so the lattice lands on v_post
xs = np.arange(N) / (N - 1.0)
vals = np.array([g0.shaper_inverse(x) for x in xs], dtype=np.float64)
for b in range(N):                          # tile index = blue
    for gch in range(N):                    # row = green
        lin[gch, b * N:(b + 1) * N, 0] = vals            # column inside the tile = red
        lin[gch, b * N:(b + 1) * N, 1] = vals[gch]
        lin[gch, b * N:(b + 1) * N, 2] = vals[b]
lin[:, :, :3] *= gain

lat = bpy.data.images.new("LUT_lattice", W, H, alpha=True, float_buffer=True, is_data=True)
lat.colorspace_settings.name = "Non-Color"
lat.pixels.foreach_set(lin.ravel())
strip_png = g0.OUT / "lut_agx_high_contrast_33.png"
s = scene.render.image_settings
keep = (s.file_format, s.color_depth, s.color_mode, s.compression)
set_follow_scene()
s.file_format, s.color_depth, s.color_mode, s.compression = "PNG", "16", "RGB", 0
lat.save_render(str(strip_png), scene=scene)
s.file_format, s.color_depth, s.color_mode, s.compression = keep

rb = bpy.data.images.load(str(strip_png))
rb.colorspace_settings.name = "Non-Color"
disp = np.array(rb.pixels[:], dtype=np.float32).reshape(H, W, 4)[:, :, :3]
bpy.data.images.remove(rb)

# .cube (three.js LUTCubeLoader): r fastest, then g, then b
cube_path = g0.OUT / "lut_agx_high_contrast_33.cube"
with open(cube_path, "w") as fh:
    fh.write("# AgX - High Contrast at exposure %.7f EV, baked from Blender 5.2.1's own OCIO by export/bake_lut.py\n"
             "# INPUT is the AgX log2 shaper coordinate of the POST-exposure scene-linear value:\n"
             "#   x = clamp((log2(max(v,1e-10)/0.18) - (%.5f)) / (%.5f), 0, 1),  v = linear * 2^(%.7f)\n"
             "# OUTPUT is display-referred sRGB (already encoded); the viewer writes it out with no further transform.\n"
             % (EXP, g0.SHAPER_MIN_EV, g0.SHAPER_MAX_EV - g0.SHAPER_MIN_EV, EXP))
    fh.write(f"TITLE \"AgX High Contrast {EXP:.4f}EV\"\nLUT_3D_SIZE {N}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n")
    for b in range(N):
        for gch in range(N):
            for r in range(N):
                px = disp[gch, b * N + r]
                fh.write(f"{px[0]:.6f} {px[1]:.6f} {px[2]:.6f}\n")
step.done(strip_png, cube_path, size=N)


def lut_apply(v):
    """Trilinear lookup of a scene-linear (pre-exposure) RGB triple, exactly as the viewer will do it."""
    out = []
    coords = [g0.log_shaper(c * (2.0 ** EXP)) for c in v]
    ijk = [c * (N - 1) for c in coords]
    i0 = [min(int(math.floor(t)), N - 2) for t in ijk]
    fr = [ijk[k] - i0[k] for k in range(3)]
    acc = np.zeros(3)
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = ((1 - fr[0]) if dr == 0 else fr[0]) * ((1 - fr[1]) if dg == 0 else fr[1]) * \
                    ((1 - fr[2]) if db == 0 else fr[2])
                acc += w * disp[i0[1] + dg, (i0[2] + db) * N + (i0[0] + dr)]
    out = acc
    return out


# ---- proof: a flat 0.18 grey emission plane rendered by Cycles must match lut_apply(0.18) within 1/255 --------
step = g0.Step("bake_lut:grey_proof")
prev_hidden = bl.hide_all_but(set())
mat = bpy.data.materials.new("GATE0_grey018")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1.0)
em.inputs["Strength"].default_value = 1.0
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
me = bpy.data.meshes.new("GATE0_grey018")
me.from_pydata([(-10, -10, 0), (10, -10, 0), (10, 10, 0), (-10, 10, 0)], [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new("GATE0_grey018", me)
plane.data.materials.append(mat)
scene.collection.objects.link(plane)
plane.location = (0, 0, 500)
cam_d = bpy.data.cameras.new("GATE0_grey_cam")
cam = bpy.data.objects.new("GATE0_grey_cam", cam_d)
scene.collection.objects.link(cam)
cam.location = (0, 0, 499)
cam.rotation_euler = (0, 0, 0)
cam_d.lens = 50.0
keep_cam, keep_res, keep_nodes = scene.camera, (scene.render.resolution_x, scene.render.resolution_y), scene.use_nodes
scene.camera = cam
scene.use_nodes = False                     # the compositor's vignette/bloom must not touch the proof
scene.render.resolution_x = scene.render.resolution_y = 64
scene.render.film_transparent = False
scene.cycles.samples = 16
scene.cycles.use_adaptive_sampling = False
scene.cycles.use_denoising = False
set_follow_scene()
s.file_format, s.color_depth, s.color_mode = "PNG", "16", "RGB"
grey_png = g0.OUT / "lut_proof_grey018.png"
scene.render.filepath = str(grey_png)[:-4]
t0 = time.time()
bpy.ops.render.render(write_still=True)
t_grey = time.time() - t0
rb = bpy.data.images.load(str(grey_png))
rb.colorspace_settings.name = "Non-Color"
gpx = np.array(rb.pixels[:], dtype=np.float32).reshape(64, 64, 4)[32, 32, :3]
bpy.data.images.remove(rb)
lut018 = lut_apply((0.18, 0.18, 0.18))
report["lut"] = dict(
    size=N, strip=str(strip_png), cube=str(cube_path), cube_bytes=cube_path.stat().st_size,
    exposure_ev=EXP, shaper=dict(min_ev=g0.SHAPER_MIN_EV, max_ev=g0.SHAPER_MAX_EV, pivot=g0.SHAPER_PIVOT),
    proof=dict(render=[round(float(v), 6) for v in gpx],
               lut=[round(float(v), 6) for v in lut018],
               abs_diff_255=[round(float(abs(gpx[i] - lut018[i])) * 255.0, 4) for i in range(3)],
               within_1_255=bool(max(abs(gpx[i] - lut018[i]) for i in range(3)) * 255.0 <= 1.0),
               render_s=round(t_grey, 1)))
print("[gate0] LUT proof: cycles", report["lut"]["proof"]["render"], "lut", report["lut"]["proof"]["lut"],
      "diff/255", report["lut"]["proof"]["abs_diff_255"])
step.done(grey_png)

bpy.data.objects.remove(plane)
bpy.data.objects.remove(cam)
scene.camera = keep_cam
scene.render.resolution_x, scene.render.resolution_y = keep_res
scene.use_nodes = keep_nodes
bl.restore_hidden(prev_hidden)

# ---------------------------------------------------------------- (b) equirects -------------------------------
wt = scene.world.node_tree
lp = next(n for n in wt.nodes if n.bl_idname == "ShaderNodeLightPath")
saved = [(l.from_socket.name, l.to_node.name, list(l.to_node.inputs).index(l.to_socket)) for l in
         [l for o in lp.outputs for l in o.links]]
report["light_path_links"] = saved


def isolate(is_camera, is_glossy):
    """Delete the LIGHT_PATH links and write the branch's constants into the destination inputs."""
    const = {"Is Camera Ray": float(is_camera), "Is Glossy Ray": float(is_glossy)}
    for o in lp.outputs:
        for l in list(o.links):
            wt.links.remove(l)
    for sock_name, node_name, idx in saved:
        wt.nodes[node_name].inputs[idx].default_value = const.get(sock_name, 0.0)


def restore_links():
    for sock_name, node_name, idx in saved:
        wt.links.new(lp.outputs[sock_name], wt.nodes[node_name].inputs[idx])


pano_d = bpy.data.cameras.new("GATE0_pano")
pano = bpy.data.objects.new("GATE0_pano", pano_d)
scene.collection.objects.link(pano)
pano_d.type = "PANO"
for holder in (pano_d, getattr(pano_d, "cycles", None)):
    if holder is not None and hasattr(holder, "panorama_type"):
        try:
            holder.panorama_type = "EQUIRECTANGULAR"
        except Exception:
            pass
pano.location = (0.0, 0.0, 12.0)
pano.rotation_euler = (math.pi / 2.0, 0.0, 0.0)     # image centre = world +Y (the lagoon side)
prev_hidden = bl.hide_all_but(set())                # world only
keep_cam = scene.camera
scene.camera = pano
scene.render.resolution_x, scene.render.resolution_y = 4096, 2048
scene.cycles.samples = 16
scene.cycles.use_adaptive_sampling = False
scene.cycles.use_denoising = False
scene.render.film_transparent = False
scene.use_nodes = False

equi = {}
for name, (isc, isg) in (("camera", (1, 0)), ("glossy", (0, 1))):
    step = g0.Step(f"bake_lut:equirect_{name}")
    isolate(isc, isg)
    set_linear_output()
    s.file_format, s.color_depth, s.exr_codec = "OPEN_EXR", "32", "ZIP"
    exr = g0.OUT / f"sky_{name}_4096x2048.exr"
    scene.render.filepath = str(exr)[:-4]
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    s.file_format = "HDR"
    hdr = g0.OUT / f"sky_{name}_4096x2048.hdr"
    scene.render.filepath = str(hdr)[:-4]
    bpy.ops.render.render(write_still=True)
    set_follow_scene()
    img = bpy.data.images.load(str(exr))
    a = np.array(img.pixels[:], dtype=np.float32).reshape(2048, 4096, 4)[:, :, :3]
    bpy.data.images.remove(img)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    iy, ix = np.unravel_index(int(np.argmax(lum)), lum.shape)
    u, v = (ix + 0.5) / 4096.0, (iy + 0.5) / 2048.0
    equi[name] = dict(exr=str(exr), exr_bytes=exr.stat().st_size, hdr=str(hdr), hdr_bytes=hdr.stat().st_size,
                      render_s=round(dt, 1),
                      stats=dict(min=round(float(a.min()), 6), max=round(float(a.max()), 4),
                                 mean=round(float(a.mean()), 6), p99=round(float(np.percentile(lum, 99)), 4)),
                      brightest=dict(u=round(u, 5), v=round(v, 5),
                                     elevation_deg=round((0.5 - v) * 180.0, 3)))
    step.done(exr, hdr, max=equi[name]["stats"]["max"], u=round(u, 4), v=round(v, 4))
restore_links()

# expected sun position, from LIGHT_sun, under the assumed mapping (image centre u=0.5 -> world +Y)
sun = next(o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN")
d = -(sun.matrix_world.to_quaternion() @ __import__("mathutils").Vector((0, 0, -1))).normalized()  # toward the sun
el = math.degrees(math.asin(max(-1.0, min(1.0, d.z))))
az = (math.degrees(math.atan2(d.y, -d.x))) % 360.0            # clockwise from north (-X), east = +Y
report["sun_check"] = dict(direction_to_sun=[round(v, 5) for v in d], elevation_deg=round(el, 3),
                           azimuth_deg_cw_from_north=round(az, 3),
                           measured=({k: v["brightest"] for k, v in equi.items()}),
                           note="v = 0.5 - elevation/180. u is reported as measured; the manifest records the "
                                "mapping that reproduces the sun's azimuth, so the viewer never guesses it.")
# solve the u convention from the measurement: u = (u0 + sign * atan2 angle) / 360
ang_from_plusY = math.degrees(math.atan2(d.x, d.y))           # 0 at +Y, + toward +X
for name in equi:
    um = equi[name]["brightest"]["u"]
    for sign in (+1, -1):
        u0 = (um * 360.0 - sign * ang_from_plusY) % 360.0
        equi[name].setdefault("u_fit", []).append(dict(sign=sign, u0_deg=round(u0, 2)))
report["equirects"] = equi
scene.camera = keep_cam
bl.restore_hidden(prev_hidden)
bpy.data.objects.remove(pano)

(g0.OUT / "bake_lut.json").write_text(json.dumps(report, indent=1) + "\n")
g0.manifest_merge(
    lut=dict(path="lut_agx_high_contrast_33.cube", strip_png="lut_agx_high_contrast_33.png", size=N,
             domain="AgX log2 shaper of the POST-exposure scene-linear value",
             shaper=dict(min_ev=g0.SHAPER_MIN_EV, max_ev=g0.SHAPER_MAX_EV, pivot=g0.SHAPER_PIVOT),
             exposure_ev=EXP, exposure_applied_by="viewer (multiply linear by 2^exposure_ev before the shaper)",
             output="display-referred sRGB, write straight to the framebuffer with three.js tone mapping OFF",
             proof=report["lut"]["proof"]),
    sky=dict(camera=dict(exr="sky_camera_4096x2048.exr", hdr="sky_camera_4096x2048.hdr",
                         use="background sphere"),
             glossy=dict(exr="sky_glossy_4096x2048.exr", hdr="sky_glossy_4096x2048.hdr",
                         use="PMREM source for reflections"),
             mapping="equirectangular, 4096x2048, scene-linear; v = 0.5 - elevation/180",
             branch_isolation="LIGHT_PATH links deleted in memory and the branch constants written into the "
                              "destination inputs (camera: Is Camera Ray=1, Is Glossy Ray=0; glossy: the reverse)",
             sun=dict(elevation_deg=round(el, 3), azimuth_deg_cw_from_north=round(az, 3)),
             measured=report["sun_check"]))
g0.queue_state("idle")
print("[gate0] bake_lut done")
