"""Gate 0 step 5: (a) the AgX High Contrast 3D LUT, (b) the two sky equirects. Both from gate0_set.blend.

    scripts/blender_run.sh 1800 -- --background export/out/gate0/gate0_set.blend --python export/bake_lut.py

(a) THE LUT - how, exactly, because a wrong LUT makes every parity score wrong.
    Blender exposes no OCIO API to Python, so the transform is obtained by pushing an identity lattice through
    Blender's OWN view transform and reading the result back:
      1. the lattice coordinate is not a linear ramp but an AgX log2 SHAPER coordinate, so the open domain fits
         in [0,1]:  x in [0,1] -> v_post = 0.18 * 2^(-12.47393 + x * 16.5)   (scene-linear, AFTER exposure);
         the value written into the image is v_pre = v_post * 2^(-exposure_ev), so Blender's own exposure of
         -2.8331399 EV brings it back to v_post before the view transform. The LUT therefore *is* "AgX - High
         Contrast at exposure -2.833". The viewer applies the same exposure (multiply linear by 2^exposure_ev)
         before the shaper; that is what keeps the sunlit stone inside the domain (at 67.3 W/m2 it would sit
         ~5.9 EV over mid grey, above the shaper's +4.03 EV ceiling, if exposure were left out);
      2. the lattice is a 1089 x 33 tile strip in a float image with colour space Non-Color, so nothing touches
         the numbers on the way in;
      3. it is pushed through the view transform by **rendering it through the compositor** (an Image node wired
         straight to the Composite output, render resolution = the lattice size, every object hidden, 1 sample):
         the render output path applies view transform, look AND exposure. `Image.save_render()` does NOT - that
         is measured in this same script and reported as `save_render_probe`; it wrote the raw buffer back, which
         is why the first version of this script produced a LUT that was 27/255 wrong on mid grey;
      4. the rendered PNG is read back as Non-Color (raw display code values) and written out as a 33^3 .cube
         plus the strip PNG.
    PROOF (brief step 5): a flat 0.18 grey emission plane rendered by Cycles through the same scene settings must
    equal the LUT applied to linear 0.18, within 1/255. Both numbers are in the report and in the manifest.

(b) THE EQUIRECTS - the world node tree branches on Light Path (camera x2.5, glossy x1.7, a tinted diffuse branch).
    The branch is isolated IN MEMORY by deleting the six links out of the LIGHT_PATH node and writing the constant
    for the branch into each destination input (Is Camera Ray = 1 / Is Glossy Ray = 0 for the camera equirect, and
    the reverse for the glossy one). The links are restored afterwards; the .blend is never saved. An
    equirectangular panoramic camera would give the camera branch for free but can never give the glossy one, so
    both are done the same way. The sun's measured position in the image verifies the mapping.
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
report = {"lights": lights}
N = g0.LUT_SIZE
EXP = scene.view_settings.exposure
assert abs(EXP - g0.EXPOSURE_EV) < 1e-4, f"exposure {EXP} != {g0.EXPOSURE_EV}"
assert scene.view_settings.look == g0.LOOK and scene.view_settings.view_transform == g0.VIEW_TRANSFORM
s = scene.render.image_settings
OUT = g0.OUT


def set_linear_output():
    s.color_management = "OVERRIDE"
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0.0
    s.view_settings.gamma = 1.0


def set_follow_scene():
    s.color_management = "FOLLOW_SCENE"


def read_png(path, w, h):
    im = bpy.data.images.load(str(path))
    im.colorspace_settings.name = "Non-Color"
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3].copy()
    bpy.data.images.remove(im)
    return a


# ================================================================ 1. the Cycles ground truth ==================
step = g0.Step("bake_lut:grey_proof_render")
prev_hidden = bl.hide_all_but(set())
mat = bpy.data.materials.new("GATE0_grey018")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1.0)
em.inputs["Strength"].default_value = 1.0
mo = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(em.outputs["Emission"], mo.inputs["Surface"])
me = bpy.data.meshes.new("GATE0_grey018")
me.from_pydata([(-10, -10, 0), (10, -10, 0), (10, 10, 0), (-10, 10, 0)], [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new("GATE0_grey018", me)
plane.data.materials.append(mat)
scene.collection.objects.link(plane)
plane.location = (0, 0, 490)
cam_d = bpy.data.cameras.new("GATE0_grey_cam")
cam = bpy.data.objects.new("GATE0_grey_cam", cam_d)
scene.collection.objects.link(cam)
cam.location = (0, 0, 500)                 # looks along -Z, straight down at the plane 10 m below
cam_d.lens = 50.0
keep = dict(cam=scene.camera, res=(scene.render.resolution_x, scene.render.resolution_y),
            nodes=scene.use_nodes, tree=scene.compositing_node_group, path=scene.render.filepath)
scene.camera = cam
# Blender 5.2: `scene.use_nodes = False` is a NO-OP - the compositor still runs. Only setting
# scene.compositing_node_group = None disables it. Measured: the same 0.18 emission plane renders 0.075029 with
# COMP_scene_golden_hour still attached and 0.082078 without it, and 0.082078 is what the view transform alone
# gives. The first LUT "proof failure" (1.7/255) was this, not the LUT.
scene.use_nodes = False
scene.compositing_node_group = None         # the compositor's vignette / mist / bloom must not touch the proof
scene.render.resolution_x = scene.render.resolution_y = 64
scene.render.film_transparent = False
scene.cycles.samples = 16
scene.cycles.use_adaptive_sampling = False
scene.cycles.use_denoising = False
set_follow_scene()
s.file_format, s.color_depth, s.color_mode, s.compression = "PNG", "16", "RGB", 0
PATCHES = [0.0025, 0.02, 0.18, 1.0, 8.0]      # a proof at one value only cannot catch a shaper/domain error
cycles_patch = {}
t0 = time.time()
for pv_ in PATCHES:
    em.inputs["Color"].default_value = (pv_, pv_, pv_, 1.0)
    png = OUT / f"lut_proof_grey_{pv_}.png"
    scene.render.filepath = str(png)[:-4]
    bpy.ops.render.render(write_still=True)
    cycles_patch[pv_] = float(read_png(png, 64, 64)[32, 32, 0])
t_grey = time.time() - t0
cycles_018 = cycles_patch[0.18]
grey_png = OUT / "lut_proof_grey_0.18.png"
bpy.data.objects.remove(plane)
bpy.data.objects.remove(cam)
print(f"[gate0] Cycles ground truth: linear 0.18 -> display {cycles_018:.6f}")
step.done(grey_png, display=round(cycles_018, 6), patches=len(PATCHES))

# ================================================================ 2. what save_render actually does ===========
probe_vals = [0.18, 0.18 * (2.0 ** EXP)]
pr = bpy.data.images.new("LUT_probe", 2, 1, alpha=True, float_buffer=True, is_data=True)
pr.colorspace_settings.name = "Non-Color"
pr.pixels.foreach_set(np.array([probe_vals[0]] * 3 + [1.0] + [probe_vals[1]] * 3 + [1.0], dtype=np.float32))
probe_png = OUT / "lut_save_render_probe.png"
pr.save_render(str(probe_png), scene=scene)
pv = read_png(probe_png, 2, 1)
bpy.data.images.remove(pr)
o0, o1 = float(pv[0, 0, 0]), float(pv[0, 1, 0])
verdict = ("no transform at all (raw buffer)" if abs(o0 - probe_vals[0]) < 0.005 and abs(o1 - probe_vals[1]) < 0.005
           else "view transform + look, exposure NOT applied" if abs(o1 - cycles_018) < 0.005
           else "view transform + look + exposure")
report["compositor_note"] = ("Blender 5.2: scene.use_nodes = False does NOT disable the compositor; only "
                             "scene.compositing_node_group = None does. Measured on a 0.18 emission plane: "
                             "0.075029 with COMP_scene_golden_hour attached, 0.082078 without.")
report["save_render_probe"] = dict(inputs=[round(v, 6) for v in probe_vals],
                                   outputs=[round(o0, 6), round(o1, 6)], verdict=verdict)
print(f"[gate0] save_render probe {[round(v, 5) for v in probe_vals]} -> {[round(o0, 5), round(o1, 5)]}: {verdict}")

# ================================================================ 3. the lattice, through the compositor ======
step = g0.Step("bake_lut:lattice")
W, H = N * N, N
xs = np.arange(N) / (N - 1.0)
vals = np.array([g0.shaper_inverse(x) for x in xs], dtype=np.float64)
lin = np.zeros((H, W, 4), dtype=np.float32)
lin[:, :, 3] = 1.0
for b in range(N):                          # tile index = blue
    for gch in range(N):                    # row = green
        lin[gch, b * N:(b + 1) * N, 0] = vals            # column inside the tile = red
        lin[gch, b * N:(b + 1) * N, 1] = vals[gch]
        lin[gch, b * N:(b + 1) * N, 2] = vals[b]
lin[:, :, :3] *= 2.0 ** (-EXP)              # v_pre: Blender's own -2.833 EV brings it back to v_post

lat = bpy.data.images.new("LUT_lattice", W, H, alpha=True, float_buffer=True, is_data=True)
lat.colorspace_settings.name = "Non-Color"
lat.pixels.foreach_set(lin.ravel())

# Blender 5.2: the compositor is a node group on scene.compositing_node_group, with a NodeGroupOutput,
# not the old scene.node_tree + CompositorNodeComposite.
old_group = bpy.data.node_groups.get("GATE0_LUT_COMP")
if old_group:
    bpy.data.node_groups.remove(old_group)
ct = bpy.data.node_groups.new("GATE0_LUT_COMP", "CompositorNodeTree")
ct.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
imn = ct.nodes.new("CompositorNodeImage")
imn.image = lat
gout = ct.nodes.new("NodeGroupOutput")
ct.links.new(imn.outputs["Image"], gout.inputs[0])
scene.compositing_node_group = ct
scene.use_nodes = True
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.film_transparent = False
scene.cycles.samples = 1
set_follow_scene()
s.file_format, s.color_depth, s.color_mode, s.compression = "PNG", "16", "RGB", 0
strip_png = OUT / f"lut_agx_high_contrast_{N}.png"
scene.render.filepath = str(strip_png)[:-4]
bpy.ops.render.render(write_still=True)
disp = read_png(strip_png, W, H)

cube_path = OUT / f"lut_agx_high_contrast_{N}.cube"
with open(cube_path, "w") as fh:
    fh.write("# AgX - High Contrast at exposure %.7f EV, baked from Blender 5.2.1's own OCIO by export/bake_lut.py\n"
             "# INPUT is the AgX log2 shaper coordinate of the POST-exposure scene-linear value:\n"
             "#   v = linear * 2^(%.7f);  x = clamp((log2(max(v,1e-10)/0.18) - (%.5f)) / %.5f, 0, 1)\n"
             "# OUTPUT is display-referred sRGB code values; write them to the framebuffer with no further encode.\n"
             % (EXP, EXP, g0.SHAPER_MIN_EV, g0.SHAPER_MAX_EV - g0.SHAPER_MIN_EV))
    fh.write(f"TITLE \"AgX High Contrast {EXP:.4f}EV\"\nLUT_3D_SIZE {N}\n"
             f"DOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n")
    for b in range(N):
        for gch in range(N):
            for r in range(N):
                px = disp[gch, b * N + r]
                fh.write(f"{px[0]:.6f} {px[1]:.6f} {px[2]:.6f}\n")
step.done(strip_png, cube_path, size=N)


def lut_apply(v):
    """Trilinear lookup of a scene-linear (pre-exposure) RGB triple, exactly as the viewer will do it."""
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
    return acc


lut018 = lut_apply((0.18, 0.18, 0.18))
diff255 = [abs(float(lut018[i]) - cycles_018) * 255.0 for i in range(3)]
patch_proof = {}
for pv_, cy in cycles_patch.items():
    lv = lut_apply((pv_, pv_, pv_))
    patch_proof[str(pv_)] = dict(cycles=round(cy, 6), lut=round(float(lv[0]), 6),
                                 diff_255=round(abs(float(lv[0]) - cy) * 255.0, 4))
worst = max(v["diff_255"] for v in patch_proof.values())
report["lut"] = dict(size=N, strip=strip_png.name, cube=cube_path.name, cube_bytes=cube_path.stat().st_size,
                     exposure_ev=EXP, method="compositor render of the lattice through the scene's view transform",
                     shaper=dict(min_ev=g0.SHAPER_MIN_EV, max_ev=g0.SHAPER_MAX_EV, pivot=g0.SHAPER_PIVOT),
                     white_point=[round(float(v), 6) for v in disp[N - 1, (N - 1) * N + (N - 1)]],
                     black_point=[round(float(v), 6) for v in disp[0, 0]],
                     proof=dict(cycles_render=round(cycles_018, 6),
                                lut=[round(float(v), 6) for v in lut018],
                                abs_diff_255=[round(d, 4) for d in diff255],
                                within_1_255=bool(max(diff255) <= 1.0),
                                patches=patch_proof, worst_diff_255=round(worst, 4),
                                all_patches_within_1_255=bool(worst <= 1.0),
                                render_s=round(t_grey, 1)))
print(f"[gate0] LUT proof 0.18: cycles {cycles_018:.6f} lut {lut018[0]:.6f} diff/255 {diff255[0]:.3f} "
      f"-> {'PASS' if max(diff255) <= 1.0 else 'FAIL'}")
print(f"[gate0] LUT proof patches: {json.dumps(patch_proof)} worst/255 {worst:.3f} "
      f"-> {'PASS' if worst <= 1.0 else 'FAIL'}")

# (the compositor group stays detached until the end of the script; it is restored with the rest of the state)

# ================================================================ 4. the equirects =============================
wt = scene.world.node_tree
lp = next(n for n in wt.nodes if n.bl_idname == "ShaderNodeLightPath")
saved = [(l.from_socket.name, l.to_node.name, list(l.to_node.inputs).index(l.to_socket))
         for l in [l for o in lp.outputs for l in o.links]]
report["light_path_links"] = saved


def isolate(is_camera, is_glossy):
    const = {"Is Camera Ray": float(is_camera), "Is Glossy Ray": float(is_glossy)}
    for o in lp.outputs:
        for l in list(o.links):
            wt.links.remove(l)
    for sock_name, node_name, idx in saved:
        wt.nodes[node_name].inputs[idx].default_value = const.get(sock_name, 0.0)


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
ptype = getattr(pano_d, "panorama_type", None) or getattr(getattr(pano_d, "cycles", None), "panorama_type", None)
assert ptype == "EQUIRECTANGULAR", f"panorama type is {ptype!r}"
pano.location = (0.0, 0.0, 12.0)
pano.rotation_euler = (math.pi / 2.0, 0.0, 0.0)     # image centre = world +Y (the lagoon side)
scene.camera = pano
scene.render.resolution_x, scene.render.resolution_y = 4096, 2048
scene.cycles.samples = 16
scene.use_nodes = False
scene.compositing_node_group = None         # no vignette / mist on the sky equirects
equi = {}
for name, (isc, isg) in (("camera", (1, 0)), ("glossy", (0, 1))):
    step = g0.Step(f"bake_lut:equirect_{name}")
    isolate(isc, isg)
    set_linear_output()
    s.file_format, s.color_depth, s.exr_codec = "OPEN_EXR", "32", "ZIP"
    exr = OUT / f"sky_{name}_4096x2048.exr"
    scene.render.filepath = str(exr)[:-4]
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    s.file_format = "HDR"
    hdr = OUT / f"sky_{name}_4096x2048.hdr"
    scene.render.filepath = str(hdr)[:-4]
    bpy.ops.render.render(write_still=True)
    set_follow_scene()
    im = bpy.data.images.load(str(exr))
    a = np.array(im.pixels[:], dtype=np.float32).reshape(2048, 4096, 4)[:, :, :3]
    bpy.data.images.remove(im)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    iy, ix = np.unravel_index(int(np.argmax(lum)), lum.shape)
    u, v = (ix + 0.5) / 4096.0, (iy + 0.5) / 2048.0
    rows = lum.mean(axis=1)
    horizon_v = (int(np.argmax(np.abs(np.diff(rows)))) + 1.0) / 2048.0
    equi[name] = dict(exr=exr.name, exr_bytes=exr.stat().st_size, hdr=hdr.name, hdr_bytes=hdr.stat().st_size,
                      render_s=round(dt, 1),
                      stats=dict(min=round(float(a.min()), 6), max=round(float(a.max()), 4),
                                 mean=round(float(a.mean()), 6), p99=round(float(np.percentile(lum, 99)), 4)),
                      brightest=dict(u=round(u, 5), v=round(v, 5)),
                      horizon_row_v=round(horizon_v, 5))
    step.done(exr, hdr, max=equi[name]["stats"]["max"], u=round(u, 4), horizon_v=round(horizon_v, 4))

for sock_name, node_name, idx in saved:
    wt.links.new(lp.outputs[sock_name], wt.nodes[node_name].inputs[idx])

from mathutils import Vector  # noqa: E402
sun = next(o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN")
d = -(sun.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()      # direction TOWARD the sun
el = math.degrees(math.asin(max(-1.0, min(1.0, d.z))))
az = math.degrees(math.atan2(d.y, -d.x)) % 360.0                               # clockwise from north (-X)
ang_from_plusY = math.degrees(math.atan2(d.x, d.y))                            # 0 at +Y, + toward +X
u_expected = (0.5 + ang_from_plusY / 360.0) % 1.0
report["equirects"] = equi
report["sun_check"] = dict(direction_to_sun=[round(v, 5) for v in d], elevation_deg=round(el, 3),
                           azimuth_deg_cw_from_north=round(az, 3), u_expected=round(u_expected, 5),
                           u_measured={k: v["brightest"]["u"] for k, v in equi.items()},
                           u_error_deg={k: round((v["brightest"]["u"] - u_expected) * 360.0, 3)
                                        for k, v in equi.items()},
                           horizon_v={k: v["horizon_row_v"] for k, v in equi.items()},
                           mapping="u = 0.5 + atan2(x, y)/360 (u=0.5 is world +Y, u grows toward +X); "
                                   "v = 0.5 - elevation/180 (v=0 is the zenith). The sun disc is off, so the "
                                   "brightest pixel sits on the horizon at the sun's azimuth: u verifies the "
                                   "azimuth and horizon_row_v verifies that v=0.5 is the horizon.")
print("[gate0] sun check:", json.dumps(report["sun_check"]))

scene.camera = keep["cam"]
scene.render.resolution_x, scene.render.resolution_y = keep["res"]
scene.render.filepath = keep["path"]
scene.use_nodes = keep["nodes"]
scene.compositing_node_group = keep["tree"]
bl.restore_hidden(prev_hidden)
bpy.data.objects.remove(pano)

(OUT / "bake_lut.json").write_text(json.dumps(report, indent=1) + "\n")
g0.manifest_merge(
    lut=dict(path=cube_path.name, strip_png=strip_png.name, size=N,
             domain="AgX log2 shaper of the POST-exposure scene-linear value",
             shaper=dict(min_ev=g0.SHAPER_MIN_EV, max_ev=g0.SHAPER_MAX_EV, pivot=g0.SHAPER_PIVOT),
             exposure_ev=EXP, exposure_applied_by="viewer (multiply linear by 2^exposure_ev before the shaper)",
             output="display-referred sRGB, write straight to the framebuffer with three.js tone mapping OFF",
             method=report["lut"]["method"], proof=report["lut"]["proof"]),
    sky=dict(camera=dict(exr=equi["camera"]["exr"], hdr=equi["camera"]["hdr"], use="background sphere",
                         bytes_hdr=equi["camera"]["hdr_bytes"]),
             glossy=dict(exr=equi["glossy"]["exr"], hdr=equi["glossy"]["hdr"], use="PMREM source for reflections",
                         bytes_hdr=equi["glossy"]["hdr_bytes"]),
             resolution=[4096, 2048], colorspace="scene-linear (EXR 32-bit, .hdr RGBE)",
             mapping=report["sun_check"]["mapping"],
             branch_isolation="the six LIGHT_PATH links are deleted in memory and the branch constants written "
                              "into the destination inputs (camera: Is Camera Ray=1, Is Glossy Ray=0; glossy: the "
                              "reverse); the links are restored afterwards and the .blend is never saved",
             sun=dict(elevation_deg=round(el, 3), azimuth_deg_cw_from_north=round(az, 3)),
             verification=report["sun_check"]))
g0.queue_state("idle")
print("[gate0] bake_lut done")
