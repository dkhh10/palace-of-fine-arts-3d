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

# The slice's low-poly objects carry their own `*_bakemat` copies (export_set.py made them as bake targets),
# so the Phase 5 material has to come from the hi twin - which IS the untouched master_delivery object - and,
# for the ground (no hi twin), from the source object's material that is still in the file.
JOBS = [("column", f"{g0.LO_COLUMN}_00", g0.COLUMN_HI),
        ("capital", g0.LO_CAPITAL, g0.CAPITAL_HI),
        ("ground", "GATE0_ground", None)]
GROUND_MATERIAL = "MAT_concrete_podium"   # ARCH_rotunda_pedestal_00's material, still present in gate0_set.blend
lo_objs = {k: bpy.data.objects[n] for k, n, _ in JOBS if bpy.data.objects.get(n)}
report["slice"] = {k: v.name for k, v in lo_objs.items()}

# ---------------------------------------------------------------- 1. relink the Phase 5 materials
real = {}
for key, lo_name, hi_name in JOBS:
    hi = bpy.data.objects.get(hi_name) if hi_name else None
    if hi is not None and hi.data.materials and hi.data.materials[0]:
        real[key] = hi.data.materials[0].name
    elif key == "ground":
        real[key] = GROUND_MATERIAL
need = sorted(set(real.values()))
got, missing = g2.append_materials(need)
if missing:
    raise SystemExit(f"[gate2_verify] materials missing from {g2.SRC_BLEND}: {missing}")
for ob in bpy.data.objects:                       # the hi twins carried the stale copies
    if ob.type != "MESH" or ob.data is None:
        continue
    for i, m in enumerate(ob.data.materials):
        if m is not None and m.name.startswith("STALE_"):
            ob.data.materials[i] = got[m.name[len("STALE_"):]]
for key, lo in lo_objs.items():                   # and the low-poly carried its own bake-target copy
    lo.data.materials.clear()
    lo.data.materials.append(got[real[key]])
report["relinked"] = sorted(got)
report["slice_materials"] = real
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
# the noise floor: the same scene again with a different sampling seed. Every delta below has to be read
# against this number, because the boxes are a few hundred pixels of a partly specular surface.
scene.cycles.seed = 12345
A2, wall_a2, path_a2 = render_exr("A2_procedural_seed2")
scene.cycles.seed = 0
print(f"[gate2_verify] A2 (procedural, seed 12345) {wall_a2} s -> {path_a2}")

# ---------------------------------------------------------------- 4. flat Principled materials from the bake
def flat_material(name, maps, use_normal=True):
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
    if not use_normal:
        return m
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = bpy.data.images[maps["normal"]["image"]]
    nt.links.new(uv.outputs["UV"], tn.inputs["Vector"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = g0.UV1
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# B0 isolates the MATERIAL: baked albedo + roughness, geometry normal. That is the 3 % test, because A's
# low-poly has no hi-poly relief either. B adds the baked normal map, which carries relief A cannot have, so
# B - A measures what the normal map contributes, not a bake error.
for key, maps in baked.items():
    lo = lo_objs.get(key)
    if lo is None:
        continue
    fm = flat_material(f"MAT_GATE2_FLAT0_{key}", maps, use_normal=False)
    lo.data.materials.clear()
    lo.data.materials.append(fm)
B0, wall_b0, path_b0 = render_exr("B0_baked_no_normal")
print(f"[gate2_verify] B0 (baked, no normal map) {wall_b0} s -> {path_b0}")
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

# A_hi: the decisive control for the ORN case. The capital's maps are baked SELECTED-TO-ACTIVE from a
# 64 000-triangle hi-poly, so they carry every term MAT_ornament_concrete evaluates on the hi surface
# (Geometry.Normal, PFA_concrete's edge and ledge weights, the dirt in the recesses). The 6 000-triangle
# low-poly with the procedural material cannot reproduce those, so A is the wrong reference for it: the
# question is whether lo + baked matches HI + procedural, which is the asset the bake replaces.
A_HI = None
cap_lo, cap_hi = lo_objs.get("capital"), bpy.data.objects.get(g0.CAPITAL_HI)
if cap_lo is not None and cap_hi is not None:
    def layer_colls(lc):
        yield lc
        for c in lc.children:
            yield from layer_colls(c)
    for lc in layer_colls(bpy.context.view_layer.layer_collection):
        if lc.name == g0.GATE0_HI_COLL:
            lc.exclude = False
            lc.hide_viewport = False
    for c in cap_hi.users_collection:
        c.hide_render = c.hide_viewport = False
    cap_hi.hide_render = cap_hi.hide_viewport = False
    cap_hi.matrix_world = cap_lo.matrix_world.copy()
    cap_lo.hide_render = True
    bpy.context.view_layer.update()
    A_HI, wall_ahi, path_ahi = render_exr("Ahi_procedural_hipoly")
    cap_lo.hide_render = False
    cap_hi.hide_render = True
    print(f"[gate2_verify] A_hi (hi-poly, procedural) {wall_ahi} s -> {path_ahi}")
    report["a_hi"] = dict(path=path_ahi, wall_s=wall_ahi, hi=cap_hi.name, lo=cap_lo.name)

# ---------------------------------------------------------------- 5. the boxes
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402

def box_blur(a, r=3):
    """Mean over a (2r+1)^2 window, by summed-area table. The sunlit / shaded split has to come from a
    NOISE-FREE criterion: splitting on A's own per-pixel luminance selects A's noise into the two halves and
    biases A's mean in each of them (measured: a 16-54 % 'noise floor' between two renders of the SAME scene,
    which is the selection bias, not the render). Splitting on a blurred A removes it."""
    p = np.pad(a.astype(np.float64), r, mode="edge")
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    k = 2 * r + 1
    return ((c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / float(k * k)).astype(np.float32)


H, W = A.shape[0], A.shape[1]
LUM = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
la, la2, lb0, lb = A @ LUM, A2 @ LUM, B0 @ LUM, B @ LUM
la_blur = box_blur(la, 3)
lahi = (A_HI @ LUM) if A_HI is not None else None


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
    sub_blur = la_blur[y0:y1, x0:x1]
    lit = sub_blur > np.median(sub_blur)
    for half, mask in (("sunlit", lit), ("shaded", ~lit)):
        if mask.sum() < 16:
            continue
        ma = float(sub_a[mask].mean())
        ma2 = float(la2[y0:y1, x0:x1][mask].mean())
        mb0 = float(lb0[y0:y1, x0:x1][mask].mean())
        mb = float(sub_b[mask].mean())
        pct = (lambda v: round(100.0 * (v / ma - 1.0), 3) if ma > 0 else None)
        boxes[f"{name}_{half}"] = dict(object=ob.name, box=[x0, y0, x1, y1], px=int(mask.sum()),
                                       procedural=round(ma, 6), baked_material_only=round(mb0, 6),
                                       baked_full=round(mb, 6),
                                       noise_floor_pct=pct(ma2), delta_pct=pct(mb0),
                                       delta_with_normal_pct=pct(mb))
        if lahi is not None and name == "capital":
            mh = float(lahi[y0:y1, x0:x1][mask].mean())
            boxes[f"{name}_{half}"].update(
                procedural_hipoly=round(mh, 6),
                delta_vs_hipoly_pct=round(100.0 * (mb / mh - 1.0), 3) if mh > 0 else None,
                lo_vs_hipoly_pct=round(100.0 * (ma / mh - 1.0), 3) if mh > 0 else None)
            print(f"[gate2_verify]   {name}_{half} vs hi-poly: A_hi={mh:.6f} "
                  f"B-A_hi={100.0 * (mb / mh - 1.0):+.2f} %  (A-A_hi {100.0 * (ma / mh - 1.0):+.2f} %)")
        print(f"[gate2_verify] {name}_{half}: A={ma:.6f} B0={mb0:.6f} ({pct(mb0):+.2f} %) "
              f"B={mb:.6f} ({pct(mb):+.2f} %) noise floor {pct(ma2):+.2f} % ({int(mask.sum())} px)")

report["render"] = dict(A=dict(path=path_a, wall_s=wall_a), A2=dict(path=path_a2, wall_s=wall_a2),
                        B0=dict(path=path_b0, wall_s=wall_b0), B=dict(path=path_b, wall_s=wall_b),
                        samples=64, resolution=[W, H],
                        note="A = procedural; A2 = the same at a different seed (the noise floor); "
                             "B0 = baked albedo + roughness, geometry normal (the material test); "
                             "B = B0 plus the baked normal map, which carries hi-poly relief A has not got")
report["boxes"] = boxes
# the pass test uses the right reference per class: the hi-poly where a hi-poly exists, A otherwise
def best_delta(v):
    return v["delta_vs_hipoly_pct"] if v.get("delta_vs_hipoly_pct") is not None else v["delta_pct"]


worst = max((abs(best_delta(v)) for v in boxes.values() if best_delta(v) is not None), default=None)
report["worst_abs_delta_pct"] = worst
report["pass_3pct"] = bool(worst is not None and worst <= 3.0)
report["frame_mean"] = dict(procedural=round(float(la.mean()), 6),
                            baked_material_only=round(float(lb0.mean()), 6),
                            baked_full=round(float(lb.mean()), 6),
                            noise_floor_pct=round(100.0 * (float(la2.mean()) / float(la.mean()) - 1.0), 3),
                            delta_pct=round(100.0 * (float(lb0.mean()) / float(la.mean()) - 1.0), 3),
                            delta_with_normal_pct=round(100.0 * (float(lb.mean()) / float(la.mean()) - 1.0), 3))
(g2.OUT / "verify.json").write_text(json.dumps(report, indent=1) + "\n")
step_all.done(g2.OUT / "verify.json", worst_delta_pct=worst, pass_3pct=report["pass_3pct"])
report["worst_abs_delta_with_normal_pct"] = max(
    (abs(v["delta_with_normal_pct"]) for v in boxes.values() if v["delta_with_normal_pct"] is not None),
    default=None)
report["worst_abs_noise_floor_pct"] = max(
    (abs(v["noise_floor_pct"]) for v in boxes.values() if v["noise_floor_pct"] is not None), default=None)
print(f"[gate2_verify] worst material-only box delta {worst} %  pass(<=3 %)={report['pass_3pct']}; "
      f"with the normal map {report['worst_abs_delta_with_normal_pct']} %; "
      f"noise floor {report['worst_abs_noise_floor_pct']} %; "
      f"frame mean {report['frame_mean']['delta_pct']} % / "
      f"{report['frame_mean']['delta_with_normal_pct']} %")
