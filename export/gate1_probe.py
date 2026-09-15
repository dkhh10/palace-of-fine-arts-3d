"""Gate 1 probe (read-only): the numbers the export set needs before it is built.

    scripts/blender_run.sh 600 -- --background <master_delivery.blend> --python export/gate1_probe.py

Writes export/out/gate1/probe.json. Nothing is saved back to the source file.

What it measures
  * the walkable surface: ENV_ground_colonnade_walk and the per-material face sets of ENV_terrain_ground
    (face count, area, XY bounds) so the tree near/far rule can be stated against real geometry, not a guess;
  * every ENV_ tree at LOD1: world trunk base (the XY of its lowest vertex), height, prototype mesh, and the
    horizontal distance to the nearest walkable face centre under three candidate rules;
  * the ARCH_/INST_ export candidates grouped by (element, material) for the Gate 2 PBR atlases.
"""
import bpy
import os
import sys
import json
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
import common  # noqa: E402
from mathutils import Vector  # noqa: E402

g1.ensure_dirs()
step = g0.Step("gate1_probe")
scene = bpy.context.scene
report = {"source": bpy.data.filepath}

# every _LOD0 object is hide_viewport=True in the delivery file and therefore absent from the depsgraph
for ob in bpy.data.objects:
    if ob.type == "MESH":
        ob.hide_viewport = False
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def face_centres(ob, mat_filter=None, max_faces=200000):
    """World-space face centres (and areas) of ob, optionally only for the named materials."""
    me = ob.data
    mats = [m.name if m else None for m in me.materials]
    mw = ob.matrix_world
    out = []
    for p in me.polygons:
        if mat_filter is not None:
            mn = mats[p.material_index] if p.material_index < len(mats) else None
            if mn not in mat_filter:
                continue
        out.append(((mw @ p.center), p.area, mats[p.material_index] if p.material_index < len(mats) else None))
        if len(out) >= max_faces:
            break
    return out


# ---------------------------------------------------------------- 1. the walkable candidates
walk_objs = {}
for name in ("ENV_ground_colonnade_walk", "ENV_terrain_ground", "ENV_backdrop_city_ground"):
    ob = bpy.data.objects.get(name)
    if not ob:
        continue
    per_mat = {}
    for c, a, mn in face_centres(ob):
        d = per_mat.setdefault(mn, dict(faces=0, area=0.0, xmin=1e9, xmax=-1e9, ymin=1e9, ymax=-1e9,
                                        zmin=1e9, zmax=-1e9))
        d["faces"] += 1
        d["area"] += a
        d["xmin"] = min(d["xmin"], c.x); d["xmax"] = max(d["xmax"], c.x)
        d["ymin"] = min(d["ymin"], c.y); d["ymax"] = max(d["ymax"], c.y)
        d["zmin"] = min(d["zmin"], c.z); d["zmax"] = max(d["zmax"], c.z)
    walk_objs[name] = {k: {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                       for k, v in per_mat.items()}
report["ground_objects"] = walk_objs

# candidate walkable point sets (world XY of face centres)
PAVING = {"MAT_paving_stone", "MAT_paving_stone_worn"}
GRAVEL = {"MAT_gravel_path"}
LAWN = {"MAT_lawn"}
walk_pts = {}
gw = bpy.data.objects.get("ENV_ground_colonnade_walk")
tg = bpy.data.objects.get("ENV_terrain_ground")
walk_pts["A_paved_walk"] = [(c.x, c.y) for c, a, m in face_centres(gw)] if gw else []
walk_pts["B_paved_plus_gravel"] = list(walk_pts["A_paved_walk"]) + (
    [(c.x, c.y) for c, a, m in face_centres(tg, GRAVEL)] if tg else [])
walk_pts["C_paved_gravel_lawn_site"] = list(walk_pts["B_paved_plus_gravel"]) + (
    [(c.x, c.y) for c, a, m in face_centres(tg, LAWN) if abs(c.x) <= 130.0 and abs(c.y) <= 130.0] if tg else [])
report["walkable_point_counts"] = {k: len(v) for k, v in walk_pts.items()}
for k, v in walk_pts.items():
    if v:
        xs = [p[0] for p in v]; ys = [p[1] for p in v]
        report.setdefault("walkable_bounds", {})[k] = [round(min(xs), 1), round(min(ys), 1),
                                                       round(max(xs), 1), round(max(ys), 1)]

# ---------------------------------------------------------------- 2. the trees
trees = []
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.name.startswith("ENV_tree") or g1.lod_of(ob.name) != 1:
        continue
    mw = ob.matrix_world
    corners = [mw @ Vector(c) for c in ob.bound_box]
    zmin = min(c.z for c in corners)
    zmax = max(c.z for c in corners)
    base = Vector((sum(c.x for c in corners) / 8.0, sum(c.y for c in corners) / 8.0, zmin))
    me = ob.evaluated_get(dg).to_mesh()
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    ob.evaluated_get(dg).to_mesh_clear()
    trees.append(dict(name=ob.name, mesh=ob.data.name, tris=tris,
                      base=[round(base.x, 2), round(base.y, 2), round(zmin, 2)],
                      height_m=round(zmax - zmin, 2),
                      radius_m=round(max(max(c.x for c in corners) - min(c.x for c in corners),
                                         max(c.y for c in corners) - min(c.y for c in corners)) / 2.0, 2)))


def near_count(pts, radius):
    if not pts:
        return 0, []
    near = []
    for t in trees:
        bx, by = t["base"][0], t["base"][1]
        d = min(math.hypot(bx - px, by - py) for px, py in pts)
        if d <= radius:
            near.append((t["name"], round(d, 1)))
    return len(near), near


report["tree_total"] = len(trees)
report["tree_near_by_rule"] = {}
for rule, pts in walk_pts.items():
    n, lst = near_count(pts, g1.TREE_NEAR_RADIUS_M)
    report["tree_near_by_rule"][rule] = dict(count=n, radius_m=g1.TREE_NEAR_RADIUS_M,
                                             names=sorted(x[0] for x in lst))
report["trees"] = trees

# ---------------------------------------------------------------- 3. ARCH / INST grouping for the PBR atlases
groups = {}
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    n = ob.name
    lod = g1.lod_of(n)
    if n.startswith(g1.NEVER_PREFIX) or n in g1.NEVER_NAME:
        continue
    if n.startswith("ARCH_") and lod in (None, 0):
        cls = "ARCH"
    elif n.startswith("INST_") and lod == 0:
        cls = "ORN"
    elif n.startswith("ENV_") and lod in (None, 1):
        cls = "ENV"
    else:
        continue
    mat = ob.data.materials[0].name if ob.data.materials and ob.data.materials[0] else "NONE"
    # element = the name up to the last numeric run
    el = n
    for sep in ("_LOD0", "_LOD1"):
        el = el.replace(sep, "")
    parts = [p for p in el.split("_") if not p.isdigit()]
    el = "_".join(parts[:4])
    k = f"{cls}|{el}|{mat}"
    g = groups.setdefault(k, dict(cls=cls, element=el, material=mat, objects=0, meshes=set()))
    g["objects"] += 1
    g["meshes"].add(ob.data.name)
report["pbr_groups"] = {k: dict(cls=v["cls"], element=v["element"], material=v["material"],
                                objects=v["objects"], unique_meshes=len(v["meshes"]))
                        for k, v in sorted(groups.items())}
report["pbr_group_count"] = {c: sum(1 for v in groups.values() if v["cls"] == c) for c in ("ARCH", "ORN", "ENV")}

(g1.OUT / "probe.json").write_text(json.dumps(report, indent=1) + "\n")
step.done(g1.OUT / "probe.json", trees=len(trees),
          near_A=report["tree_near_by_rule"]["A_paved_walk"]["count"],
          near_B=report["tree_near_by_rule"]["B_paved_plus_gravel"]["count"],
          near_C=report["tree_near_by_rule"]["C_paved_gravel_lawn_site"]["count"],
          pbr_groups=report["pbr_group_count"])
