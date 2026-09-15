"""Gate 0 step 1: build the export set from master_delivery.blend and write export/out/gate0/gate0_set.blend.

    scripts/blender_run.sh 900 -- --background <master_delivery.blend> --python export/export_set.py -- --gate0

Idempotent: it always rebuilds the GATE0* collections from the source file and overwrites gate0_set.blend.
master_delivery.blend is never saved (save_as_mainfile(copy=True) keeps bpy.data.filepath pointing at the source).

Contents of gate0_set.blend
  GATE0_REF   the untouched originals (16 ARCH_rotunda_column_*_LOD0, INST_capital_rotunda_000_LOD0, the ground
              object found by the ray cast). These are the hi-poly bake sources AND the Cycles reference frame.
  GATE0       the export set: one decimated column mesh placed 16x, one decimated capital, the ground.
  LIGHT       the lighting rig as saved (LIGHT_sun + the rotunda bounce lamps + the Eevee-only rigs, which every
              Cycles path switches off through light_presets.apply_final_cycles).
  QA_CAMERAS  rebuilt from scripts/qa_cameras.py, never a stale station.
"""
import bpy
import os
import sys
import json
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import common  # noqa: E402
import qa_cameras  # noqa: E402
from mathutils import Vector  # noqa: E402

argv = g0.script_argv()
assert "--gate0" in argv, "export_set.py: pass -- --gate0"
g0.ensure_dirs()
# review finding 5: manifest_merge .update()s dicts, so a rerun after a rename would leave ghost entries in
# the viewer contract. export_set.py is the head of the chain, so it starts the manifest from nothing.
(g0.OUT / "manifest.json").unlink(missing_ok=True)
step = g0.Step("export_set")
scene = bpy.context.scene
report = {}

# ---------------------------------------------------------------- 1. find the slice in the source file
col_hi = bpy.data.objects[g0.COLUMN_HI]
cap_hi = bpy.data.objects[g0.CAPITAL_HI]
placements = [bpy.data.objects[n] for n in g0.COLUMN_PLACEMENTS]

# master_delivery.blend is saved with common.set_lod(viewport=1): every _LOD0 object is hide_viewport=True and is
# therefore NOT in the depsgraph, so its matrix_world reads back as the identity and it is invisible to ray casts.
# Un-hide the slice first, evaluate once, then snapshot the transforms (derived data, valid only after evaluation).
for o in placements + [cap_hi]:
    o.hide_viewport = False
    o.hide_render = False
bpy.context.view_layer.update()

# ground: downward ray cast from just above the column's base, first hit that is not a rotunda column
base_z = min((col_hi.matrix_world @ Vector(c)).z for c in col_hi.bound_box)
origin = Vector((col_hi.location.x, col_hi.location.y, base_z + 0.60))
dg = bpy.context.evaluated_depsgraph_get()
ground = None
ray_trace = []
o = origin.copy()
for _ in range(24):
    ok, loc, nor, idx, hit, mtx = scene.ray_cast(dg, o, Vector((0, 0, -1)))
    if not ok:
        break
    ray_trace.append(dict(obj=hit.name, z=round(loc.z, 3)))
    # skip the column assembly itself (shaft ARCH_rotunda_column_*, base mouldings ARCH_rotunda_colbase_*)
    if not hit.name.startswith("ARCH_rotunda_col"):
        ground = hit
        break
    o = loc + Vector((0, 0, -0.01))
assert ground is not None, f"no ground under the column; trace={ray_trace}"
g0.GROUND_NAME_FILE.write_text(ground.name + "\n")
report["ground"] = dict(name=ground.name, ray_origin=[round(v, 3) for v in origin], trace=ray_trace,
                        tris=sum(len(p.vertices) - 2 for p in ground.data.polygons),
                        mats=[m.name if m else None for m in ground.data.materials],
                        top_z=round(max((ground.matrix_world @ Vector(c)).z for c in ground.bound_box), 3))
print(f"[gate0] ground = {ground.name} ({report['ground']['tris']} tris, top z={report['ground']['top_z']})")

bpy.context.view_layer.update()
MW = {o.name: o.matrix_world.copy() for o in placements + [cap_hi, ground]}
assert (MW[g0.COLUMN_HI].translation - bpy.data.objects[g0.COLUMN_HI].location).length < 1e-4, "stale matrix_world"

# ---------------------------------------------------------------- 2. collections
for name in (g0.GATE0_COLL, "GATE0_REF"):
    c = bpy.data.collections.get(name)
    if c:
        bpy.data.collections.remove(c)
gate0 = bpy.data.collections.new(g0.GATE0_COLL)
ref = bpy.data.collections.new("GATE0_REF")
scene.collection.children.link(gate0)
scene.collection.children.link(ref)


def uv_check(obj, uv_name, grid=1024):
    """Rasterise every UV triangle into a grid x grid bitmap: report coverage and the doubly-covered texel count.
    (bpy.ops.uv.select_overlap's selection flags are not readable from Python in 5.2, so this is measured directly.)"""
    import numpy as np
    me = obj.data
    uvs = me.uv_layers[uv_name].uv
    hits = np.zeros((grid, grid), dtype=np.int32)
    umin = vmin = 1e9
    umax = vmax = -1e9
    for p in me.polygons:
        pts = [uvs[li].vector for li in p.loop_indices]
        for i in range(1, len(pts) - 1):
            tri = [pts[0], pts[i], pts[i + 1]]
            xs = [t[0] for t in tri]
            ys = [t[1] for t in tri]
            umin, umax = min(umin, *xs), max(umax, *xs)
            vmin, vmax = min(vmin, *ys), max(vmax, *ys)
            x0 = max(0, int(min(xs) * grid)); x1 = min(grid - 1, int(max(xs) * grid))
            y0 = max(0, int(min(ys) * grid)); y1 = min(grid - 1, int(max(ys) * grid))
            if x1 < x0 or y1 < y0:
                continue
            ax, ay = tri[0]; bx, by = tri[1]; cx, cy = tri[2]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            px = (xx + 0.5) / grid
            py = (yy + 0.5) / grid
            l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / den
            l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / den
            l3 = 1.0 - l1 - l2
            inside = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
            hits[y0:y1 + 1, x0:x1 + 1] += inside.astype(np.int32)
    covered = int((hits > 0).sum())
    return dict(coverage_pct=round(100.0 * covered / (grid * grid), 2),
                overlapped_texels=int((hits > 1).sum()),
                overlapped_pct_of_covered=round(100.0 * int((hits > 1).sum()) / max(covered, 1), 3),
                uv_bounds=[round(umin, 4), round(vmin, 4), round(umax, 4), round(vmax, 4)], grid=grid)


def make_lo(src, name, target_tris, coll, do_uv1=True):
    """Copy src's mesh, decimate to ~target_tris, unwrap UV1 (material) and UV2 (lightmap)."""
    me = src.data.copy()
    me.name = name
    ob = bpy.data.objects.new(name, me)
    ob.matrix_world = src.matrix_world.copy()
    coll.objects.link(ob)
    src_tris = sum(len(p.vertices) - 2 for p in me.polygons)
    bpy.context.view_layer.objects.active = ob
    for o_ in list(bpy.context.selected_objects):
        o_.select_set(False)
    ob.select_set(True)
    m = ob.modifiers.new("decimate", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = min(1.0, float(target_tris) / float(src_tris))
    m.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=m.name)
    # triangulate so the exported count is the real one
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.quads_convert_to_tris(quad_method="BEAUTY", ngon_method="BEAUTY")
    bpy.ops.object.mode_set(mode="OBJECT")
    lo_tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    # UV1: material / PBR bake target. UV2: lightmap, bigger margin.
    while len(ob.data.uv_layers) and do_uv1:
        ob.data.uv_layers.remove(ob.data.uv_layers[0])
    if do_uv1:
        ob.data.uv_layers.new(name=g0.UV1)
    if g0.UV2 not in ob.data.uv_layers:
        ob.data.uv_layers.new(name=g0.UV2)
    for uv_name, margin in ((g0.UV1, 0.003), (g0.UV2, 0.005)):
        if uv_name == g0.UV1 and not do_uv1:
            continue
        ob.data.uv_layers.active = ob.data.uv_layers[uv_name]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=margin,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    ob.data.uv_layers.active = ob.data.uv_layers[g0.UV1 if do_uv1 else g0.UV2]
    # bake material: a private copy of the source material so the source node tree is never touched
    ob.data.materials.clear()
    src_mat = src.data.materials[0]
    bm = bpy.data.materials.get(f"{name}_bakemat") or src_mat.copy()
    bm.name = f"{name}_bakemat"
    ob.data.materials.append(bm)
    ob.hide_viewport = False
    ob.hide_render = False
    return ob, src_tris, lo_tris


lo_col, col_src_tris, lo_col_tris = make_lo(col_hi, g0.LO_COLUMN, g0.COLUMN_TARGET_TRIS, gate0)
lo_cap, cap_src_tris, lo_cap_tris = make_lo(cap_hi, g0.LO_CAPITAL, g0.CAPITAL_TARGET_TRIS, gate0)

# the ground is exported as modelled: keep its geometry and its UV1, add UV2 only
ground_lo_me = ground.data.copy()
ground_lo_me.name = "GATE0_ground"
ground_lo = bpy.data.objects.new("GATE0_ground", ground_lo_me)
ground_lo.matrix_world = ground.matrix_world.copy()
gate0.objects.link(ground_lo)
bpy.context.view_layer.objects.active = ground_lo
for o_ in list(bpy.context.selected_objects):
    o_.select_set(False)
ground_lo.select_set(True)
if not len(ground_lo_me.uv_layers):
    ground_lo_me.uv_layers.new(name=g0.UV1)
else:
    ground_lo_me.uv_layers[0].name = g0.UV1
if g0.UV2 not in ground_lo_me.uv_layers:
    ground_lo_me.uv_layers.new(name=g0.UV2)
for uv_name, margin in ((g0.UV1, 0.003), (g0.UV2, 0.005)):
    ground_lo_me.uv_layers.active = ground_lo_me.uv_layers[uv_name]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=margin, correct_aspect=True)
    bpy.ops.object.mode_set(mode="OBJECT")
ground_lo_me.uv_layers.active = ground_lo_me.uv_layers[g0.UV1]
ground_lo_me.materials.clear()
gmat = ground.data.materials[0].copy()
gmat.name = "GATE0_ground_bakemat"
ground_lo_me.materials.append(gmat)
ground_tris = sum(len(p.vertices) - 2 for p in ground_lo_me.polygons)

# the 16 placements share the ONE decimated column mesh. Placement 00 keeps its own object (it is the one that
# gets the lightmap at Gate 0); 01..15 are instances of the same mesh with a lightmap-free material at export.
lo_col.name = f"{g0.LO_COLUMN}_00"
lo_col.matrix_world = placements[0].matrix_world.copy()
instances = [lo_col]
for i, src in enumerate(placements[1:], start=1):
    ob = bpy.data.objects.new(f"{g0.LO_COLUMN}_{i:02d}", lo_col.data)
    ob.matrix_world = src.matrix_world.copy()
    gate0.objects.link(ob)
    instances.append(ob)

# ---------------------------------------------------------------- 3. reference originals
for src in placements + [cap_hi, ground]:
    for c in list(src.users_collection):
        c.objects.unlink(src)
    ref.objects.link(src)
    src.hide_viewport = False
    src.hide_render = False

# ---------------------------------------------------------------- 4. strip everything else
keep = set(o.name for o in gate0.objects) | set(o.name for o in ref.objects)
keep |= set(o.name for o in bpy.data.objects if o.type == "LIGHT")
n_removed = 0
for ob in list(bpy.data.objects):
    if ob.name in keep:
        continue
    bpy.data.objects.remove(ob, do_unlink=True)
    n_removed += 1
for c in list(bpy.data.collections):
    if c.name in (g0.GATE0_COLL, "GATE0_REF") or len(c.objects):
        continue
    bpy.data.collections.remove(c)
# relink surviving lights into one LIGHT collection
lightc = bpy.data.collections.get("LIGHT") or bpy.data.collections.new("LIGHT")
if lightc.name not in [c.name for c in scene.collection.children]:
    try:
        scene.collection.children.link(lightc)
    except RuntimeError:
        pass
for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
    if lightc.name not in [c.name for c in ob.users_collection]:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        lightc.objects.link(ob)
# matrix_world set on a freshly created, not-yet-evaluated object does not always stick (it did not for the two
# decimated meshes in the first run: both ended up at the world origin, 25.3 m / 33.1 m from their hi-poly twin).
# Re-apply every placement transform here, after every operator has run, and assert it.
pairs = [(instances[i], placements[i]) for i in range(len(instances))] + [(lo_cap, cap_hi), (ground_lo, ground)]
for ob, src in pairs:
    loc, rot, scl = MW[src.name].decompose()
    ob.rotation_mode = "QUATERNION"
    ob.location = loc
    ob.rotation_quaternion = rot
    ob.scale = scl
bpy.context.view_layer.update()
worst = 0.0
for ob, src in pairs:
    d = max((ob.matrix_world.translation - MW[src.name].translation).length,
            (src.matrix_world.translation - MW[src.name].translation).length)
    worst = max(worst, d)
    assert d < 1e-4, f"{ob.name} is {d:.4f} m from {src.name}"
report["placement_max_error_m"] = round(worst, 8)

qa_cameras.ensure(scene)
scene.camera = bpy.data.objects[g0.HERO_CAM]
common.purge_orphans()

# ---------------------------------------------------------------- 5. checks and save
overlap = {}
for ob in (lo_col, lo_cap, ground_lo):
    for uv in (g0.UV1, g0.UV2):
        try:
            overlap[f"{ob.name}:{uv}"] = uv_check(ob, uv)
        except Exception as e:      # pragma: no cover
            overlap[f"{ob.name}:{uv}"] = f"error: {e}"
    ob.data.uv_layers.active = ob.data.uv_layers[g0.UV1]

g0.save_copy(g0.SET_BLEND)
report.update(dict(
    column=dict(src_tris=col_src_tris, lo_tris=lo_col_tris, target=g0.COLUMN_TARGET_TRIS, placements=len(instances)),
    capital=dict(src_tris=cap_src_tris, lo_tris=lo_cap_tris, target=g0.CAPITAL_TARGET_TRIS, placements=1),
    ground_export=dict(name=ground_lo.name, tris=ground_tris),
    uv_overlap_faces=overlap, objects_removed=n_removed,
    set_blend=str(g0.SET_BLEND), set_blend_bytes=g0.SET_BLEND.stat().st_size,
    placed_tris=lo_col_tris * len(instances) + lo_cap_tris + ground_tris))
(g0.OUT / "export_set.json").write_text(json.dumps(report, indent=1) + "\n")

# ---------------------------------------------------------------- 6. manifest (written EARLY for the viewer)
stations = {}
for cam in [o for o in bpy.data.objects if o.type == "CAMERA"]:
    d = cam.data
    stations[cam.name] = dict(location=[round(v, 6) for v in cam.location],
                              rotation_euler_xyz=[round(v, 8) for v in cam.rotation_euler],
                              rotation_mode=cam.rotation_mode,
                              lens_mm=d.lens, sensor_width_mm=d.sensor_width, sensor_fit=d.sensor_fit,
                              shift_x=d.shift_x, shift_y=d.shift_y,
                              clip_start=d.clip_start, clip_end=d.clip_end,
                              reference_photo=cam.get("reference_photo", ""))
sun = next(o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN")
sun_dir = (sun.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
g0.manifest_merge(
    schema="pfa-phase6-gate0/1",
    generator="export/export_set.py",
    source_blend=str(g0.SRC_BLEND),
    units=dict(scale_m=1.0, up_blender="+Z", up_gltf="+Y",
               note="glTF is written with export_yup=True: Blender +Y -> glTF -Z, Blender +Z -> glTF +Y. "
                    "The viewer never re-rotates the scene. Station locations/rotations below are BLENDER Z-up."),
    water=dict(water_z=common.WATER_Z, plane_axis="blender_z", viewer_y=common.WATER_Z,
               note="viewer places the water plane at y = water_z after the Y-up swap"),
    view=dict(view_transform=scene.view_settings.view_transform, look=scene.view_settings.look,
              exposure_ev=scene.view_settings.exposure, gamma=scene.view_settings.gamma,
              display_device=scene.display_settings.display_device),
    sun=dict(name=sun.name, energy_w_m2=sun.data.energy, color=[round(c, 6) for c in sun.data.color],
             angle_rad=sun.data.angle,
             direction_blender=[round(v, 6) for v in sun_dir],
             direction_gltf=[round(sun_dir.x, 6), round(sun_dir.z, 6), round(-sun_dir.y, 6)],
             note="direction the light travels (from sun to ground). A three.js DirectionalLight is placed at "
                  "-direction_gltf * d and must be specular-only: the diffuse sun is already in the lightmaps."),
    stations=stations,
    hero_camera=g0.HERO_CAM,
    assets={}, textures={}, lut={},
)
step.done(g0.SET_BLEND, g0.OUT / "manifest.json",
          column_lo_tris=lo_col_tris, capital_lo_tris=lo_cap_tris, ground_tris=ground_tris,
          placed_tris=report["placed_tris"], removed=n_removed)
print("[gate0] uv overlap faces:", overlap)
