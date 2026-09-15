"""Gate 2 step 5: baked PBR vs the procedural original, without the viewer (brief item 4).

    scripts/blender_run.sh 1800 -- --background export/out/gate0/gate0_set.blend --python export/gate2_verify.py

The Gate 0 slice (16 rotunda columns + one rotunda capital + the ground), at the Gate 0 reference station
`CAM_qa_01_lagoon_hero`, 1280x720, 64 spp, Cycles GPU, **compositor detached** (`scene.compositing_node_group =
None` - the 5.2 finding in this README: `use_nodes = False` does not detach it and costs 7.5 % linear).

  A. the procedural Phase 5 materials, relinked by name from the regenerated master_delivery.blend
  B. the SAME geometry with flat Principled materials whose Base Color / Roughness / Normal are the Gate 2
     bake of A, produced here by the same code path bake_pbr.py --gate2 uses

Both frames are written as 32-bit linear OpenEXR, so the comparison needs no view transform. The measurement
boxes are derived, not eyeballed: each target object's world bounding box is projected through the camera to a
pixel rectangle, and inside that rectangle the pixels are split at the median luminance OF FRAME A into a
sunlit half and a shaded half. The same pixel masks are then applied to B, so the two numbers come from exactly
the same pixels. Reported per box: mean linear luminance of A, of B, and B/A - 1.
"""
import bpy
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate2_common as g2  # noqa: E402
import bake_lib as bl  # noqa: E402
import numpy as np  # noqa: E402

g2.ensure_dirs()
OUT = g2.OUT / "verify"
OUT.mkdir(parents=True, exist_ok=True)
step_all = g0.Step("gate2_verify")
scene = bpy.context.scene
report = {"station": g0.HERO_CAM}

# ---------------------------------------------------------------- 0. scene, camera, colour
g0.apply_final_cycles_checked(scene)
scene.render.engine = "CYCLES"
scene.cycles.device = "GPU"
scene.cycles.samples = 64
scene.cycles.use_adaptive_sampling = False
scene.cycles.use_denoising = False
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
cam = bpy.data.objects[g0.HERO_CAM]
scene.camera = cam
had_comp = scene.compositing_node_group is not None
scene.compositing_node_group = None          # the 5.2 finding: use_nodes = False does not do this
report["compositor_detached"] = had_comp

JOBS = [("column", f"{g0.LO_COLUMN}_00", g0.COLUMN_HI),
        ("capital", g0.LO_CAPITAL, g0.CAPITAL_HI),
        ("ground", (g0.GROUND_NAME_FILE.read_text().strip() if g0.GROUND_NAME_FILE.exists() else "GATE0_ground"),
         None)]
lo_objs = {k: bpy.data.objects[n] for k, n, _ in JOBS if bpy.data.objects.get(n)}
report["slice"] = {k: v.name for k, v in lo_objs.items()}

# ---------------------------------------------------------------- 1. relink the Phase 5 materials
need = sorted({m.name for k, v in lo_objs.items() for m in v.data.materials if m}
              | {m.name for _, _, hn in JOBS if hn and bpy.data.objects.get(hn)
                 for m in bpy.data.objects[hn].data.materials if m})
got, missing = g2.append_materials(need)
if missing:
    raise SystemExit(f"[gate2_verify] materials missing from {g2.SRC_BLEND}: {missing}")
for ob in bpy.data.objects:
    if ob.type != "MESH" or ob.data is None:
        continue
    for i, m in enumerate(ob.data.materials):
        if m is not None and m.name.startswith("STALE_"):
            ob.data.materials[i] = got[m.name[len("STALE_"):]]
report["relinked"] = sorted(got)
print(f"[gate2_verify] relinked {len(got)} materials from {g2.SRC_BLEND.name}")

# ---------------------------------------------------------------- 2. bake the slice with the Gate 2 code path
baked = {}
for key, lo_name, hi_name in JOBS:
    lo = bpy.data.objects.get(lo_name)
    if lo is None:
        continue
    hi = bpy.data.objects.get(hi_name) if hi_name else None
    cage = 0.0
    if hi is not None:
        dev = bl.deviation(lo, hi)
        cage = round(dev["max"] * 1.25, 4)
    prev = bl.hide_all_but({lo.name} | ({hi.name} if hi else set()))
    maps = {}
    for kind, btype, samples, cspace, neutral in (
            ("albedo", "DIFFUSE", g2.SAMPLES_ALBEDO, "sRGB", (0.5, 0.5, 0.5)),
            ("roughness", "ROUGHNESS", g2.SAMPLES_ROUGHNESS, "Non-Color", (0.5, 0.5, 0.5)),
            ("normal", "NORMAL", g2.SAMPLES_NORMAL, "Non-Color", (0.5, 0.5, 1.0))):
        img = bl.bake_image(f"verify_{key}_{kind}", size=2048, colorspace=cspace, float_buffer=True)
        bl.fill_sentinel(img)
        bl.attach_target(lo, img, g0.UV1)
        bl.select_only(lo, *([hi] if hi else []))
        kw = dict(samples=samples, selected_to_active=hi is not None, cage=cage, max_ray=cage,
                  margin=g2.BAKE_MARGIN_PX, clear=False)
        if kind == "albedo":
            kw.update(use_pass_direct=False, use_pass_indirect=False, use_pass_color=True)
        t = bl.run_bake(btype, **kw)
        st = bl.masked_stats(img, kind)
        bl.flood_sentinel(img, st["mean"] or neutral if kind != "normal" else neutral)
        # save and reload, so B renders from the SHIPPED file (16-bit PNG, sRGB-encoded albedo), not from the
        # in-memory float buffer - that round trip is what the viewer gets, and it is the encode under test.
        png = bl.save_png(img, OUT / f"verify_{key}_{kind}.png", depth=16)
        bpy.data.images.remove(img)
        rd = bpy.data.images.load(png, check_existing=False)
        rd.colorspace_settings.name = cspace
        maps[kind] = dict(image=rd.name, png=png, bake_s=round(t, 1), stats=st)
        print(f"[gate2_verify] bake {key} {kind}: {t:.1f} s coverage={st['coverage']} mean={st['mean']}")
        bl.detach_targets()
    bl.restore_hidden(prev)
    baked[key] = maps
report["bake"] = {k: {kk: dict(bake_s=vv["bake_s"], png=vv["png"], stats=vv["stats"]) for kk, vv in v.items()}
                  for k, v in baked.items()}


# ---------------------------------------------------------------- 3. render helper
def render_exr(tag):
    s = scene.render.image_settings
    prev = (scene.render.filepath, s.file_format, s.color_depth, s.color_mode)
    path = str(OUT / f"gate2_verify_{tag}")
    scene.render.filepath = path
    s.file_format, s.color_depth, s.color_mode = "OPEN_EXR", "32", "RGB"
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    wall = time.time() - t0
    scene.render.filepath, s.file_format, s.color_depth, s.color_mode = prev
    p = path + ".exr"
    img = bpy.data.images.load(p, check_existing=False)
    px = np.asarray(img.pixels[:], dtype=np.float32).reshape(scene.render.resolution_y,
                                                             scene.render.resolution_x, 4)[::-1]
    bpy.data.images.remove(img)
    return px[..., :3], round(wall, 1), p


A, wall_a, path_a = render_exr("A_procedural")
print(f"[gate2_verify] A (procedural) {wall_a} s -> {path_a}")

# ---------------------------------------------------------------- 4. flat Principled materials from the bake
def flat_material(name, maps):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Metallic"].default_value = 0.0
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = g0.UV1
    for kind, socket in (("albedo", "Base Color"), ("roughness", "Roughness")):
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = bpy.data.images[maps[kind]["image"]]
        tn.interpolation = "Linear"
        nt.links.new(uv.outputs["UV"], tn.inputs["Vector"])
        nt.links.new(tn.outputs["Color"], bsdf.inputs[socket])
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = bpy.data.images[maps["normal"]["image"]]
    nt.links.new(uv.outputs["UV"], tn.inputs["Vector"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = g0.UV1
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


for key, maps in baked.items():
    lo = lo_objs.get(key)
    if lo is None:
        continue
    fm = flat_material(f"MAT_GATE2_FLAT_{key}", maps)
    lo.data.materials.clear()
    lo.data.materials.append(fm)
    # every other placement of the same mesh follows automatically (shared mesh data)
B, wall_b, path_b = render_exr("B_baked")
print(f"[gate2_verify] B (baked) {wall_b} s -> {path_b}")

# ---------------------------------------------------------------- 5. the boxes
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402

H, W = A.shape[0], A.shape[1]
LUM = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
la, lb = A @ LUM, B @ LUM


def pixel_box(ob, shrink=0.18):
    xs, ys = [], []
    for c in ob.bound_box:
        p = world_to_camera_view(scene, cam, ob.matrix_world @ Vector(c))
        if p.z <= 0:
            return None
        xs.append(p.x * W)
        ys.append((1.0 - p.y) * H)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    dx, dy = (x1 - x0) * shrink, (y1 - y0) * shrink
    x0, x1, y0, y1 = x0 + dx, x1 - dx, y0 + dy, y1 - dy
    x0, x1 = int(max(0, x0)), int(min(W, x1))
    y0, y1 = int(max(0, y0)), int(min(H, y1))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    return x0, x1, y0, y1


targets = {}
col = None
for i in range(16):
    o = bpy.data.objects.get(f"{g0.LO_COLUMN}_{i:02d}")
    if o is None:
        continue
    b = pixel_box(o)
    if b is None:
        continue
    d = (o.matrix_world.translation - cam.matrix_world.translation).length
    if col is None or d < col[0]:
        col = (d, o, b)
if col:
    targets["column"] = (col[1], col[2])
cap = lo_objs.get("capital")
if cap is not None and pixel_box(cap):
    targets["capital"] = (cap, pixel_box(cap))

boxes = {}
for name, (ob, (x0, x1, y0, y1)) in targets.items():
    sub_a, sub_b = la[y0:y1, x0:x1], lb[y0:y1, x0:x1]
    lit = sub_a > np.median(sub_a)
    for half, mask in (("sunlit", lit), ("shaded", ~lit)):
        if mask.sum() < 16:
            continue
        ma, mb = float(sub_a[mask].mean()), float(sub_b[mask].mean())
        boxes[f"{name}_{half}"] = dict(object=ob.name, box=[x0, y0, x1, y1], px=int(mask.sum()),
                                       procedural=round(ma, 6), baked=round(mb, 6),
                                       delta_pct=round(100.0 * (mb / ma - 1.0), 3) if ma > 0 else None)
        print(f"[gate2_verify] {name}_{half}: A={ma:.6f} B={mb:.6f} delta={100.0 * (mb / ma - 1.0):+.2f} % "
              f"({int(mask.sum())} px)")

report["render"] = dict(A=dict(path=path_a, wall_s=wall_a), B=dict(path=path_b, wall_s=wall_b),
                        samples=64, resolution=[W, H])
report["boxes"] = boxes
worst = max((abs(v["delta_pct"]) for v in boxes.values() if v["delta_pct"] is not None), default=None)
report["worst_abs_delta_pct"] = worst
report["pass_3pct"] = bool(worst is not None and worst <= 3.0)
report["frame_mean"] = dict(procedural=round(float(la.mean()), 6), baked=round(float(lb.mean()), 6),
                            delta_pct=round(100.0 * (float(lb.mean()) / float(la.mean()) - 1.0), 3))
(g2.OUT / "verify.json").write_text(json.dumps(report, indent=1) + "\n")
step_all.done(g2.OUT / "verify.json", worst_delta_pct=worst, pass_3pct=report["pass_3pct"])
print(f"[gate2_verify] worst box delta {worst} %  pass(<=3 %)={report['pass_3pct']}  "
      f"frame mean delta {report['frame_mean']['delta_pct']} %")
