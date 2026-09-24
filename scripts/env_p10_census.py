"""Phase 10 ENV: which tree instances fill cam 01's foliage boxes, and the ENV triangle count per LOD.

    scripts/blender_run.sh 300 -- --background --python scripts/env_p10_census.py -- [--blend assets/environment.blend]

For every render-visible tree instance (LOD0 objects) whose projected world bounding box falls in cam 01's frame
x 0.30-0.82 above frame y 0.62, prints species, note, location, planted height, projected frame-x span and crown-top
frame y (bounding-box projection, so it is the extreme, not the silhouette).  Then the ENV placed-triangle totals per
LOD (same rule as env_build: every mesh object in the LOD's instance collection + the non-tree ENV meshes).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import common
import qa_cameras

ARGS = common.script_args()
blend = ARGS[ARGS.index("--blend") + 1] if "--blend" in ARGS else "assets/environment.blend"
path = blend if os.path.isabs(blend) else str(common.ROOT / blend)
bpy.ops.wm.open_mainfile(filepath=path)
scene = bpy.context.scene
qa_cameras.ensure(scene)
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
bpy.context.view_layer.update()
cam = next(o for o in bpy.data.objects if o.type == "CAMERA" and "_qa_01_" in o.name)

rows = []
for o in bpy.data.objects:
    if o.type != "MESH" or not o.name.startswith("ENV_tree_") or not o.name.endswith("_LOD0") or o.hide_render:
        continue
    pts = [world_to_camera_view(scene, cam, o.matrix_basis @ Vector(c)) for c in o.bound_box]
    if min(p.z for p in pts) <= 0:
        continue
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    ytop = 1.0 - max(p.y for p in pts)
    if x1 < 0.30 or x0 > 0.82 or ytop > 0.62:
        continue
    d = (o.location - cam.location).length
    rows.append((x0, x1, ytop, d, o))
rows.sort(key=lambda r: r[0])
print(f"\n[env_p10_census] {path}\n  frame x span    top y   dist  species        h_plan  loc (X, Y)        object   note")
for x0, x1, ytop, d, o in rows:
    print(f"  {x0:.3f}-{x1:.3f}   {ytop:.3f}  {d:6.1f}  {o.get('species', ''):14s} {o.get('height_m', 0):5.1f}  "
          f"({o.location.x:6.1f},{o.location.y:6.1f})  {o.name[:-5]:28s} {str(o.get('note', ''))[:48]}")

import env_lib as L
env = bpy.data.collections["ENV"]
tot = {lod: L.collection_tri_count(env, lod=lod) for lod in (0, 1, 2)}
trees = {lod: sum(L.tri_count(o) for o in bpy.data.collections["ENV_tree_instances"].all_objects
                  if o.type == "MESH" and o.name.endswith(f"_LOD{lod}")) for lod in (0, 1, 2)}
print(f"[env_p10_census] ENV tris (env_build rule)  LOD0 {tot[0]:,}  LOD1 {tot[1]:,}  LOD2 {tot[2]:,}   "
      f"(placed tree instances only: {trees[0]:,} / {trees[1]:,} / {trees[2]:,})")

# QA-01-6 wing boxes (env_preview.sky_through_wing's own definition: the wing's roof ring between z 4 and 17 m)
site = common.load_site_local()
for wing, key in (("north", "roof310 h19"), ("south", "roof306 h20")):
    xs, ys = [], []
    for (x, y) in site[key][0]:
        for z in (4.0, 17.0):
            co = world_to_camera_view(scene, cam, Vector((x, y, z)))
            if co.z > 0:
                xs.append(co.x)
                ys.append(1.0 - co.y)
    print(f"[env_p10_census] {wing} wing box (frame, y down): x {max(0, min(xs)):.4f}-{min(1, max(xs)):.4f} "
          f"y {max(0, min(ys)):.4f}-{min(1, max(ys)):.4f}")

# which prototype mesh each placed instance draws, per LOD slot: the cost of a per-species leaf change
use = {}
for o in bpy.data.collections["ENV_tree_instances"].all_objects:
    if o.type != "MESH":
        continue
    slot = o.name[-4:]
    key = (o.get("species", "?"), slot, o.data.name.rsplit("_", 1)[1])
    use[key] = use.get(key, 0) + 1
print("[env_p10_census] instances by (species, object LOD slot, mesh LOD drawn):")
for k in sorted(use):
    print(f"    {k[0]:14s} {k[1]} draws {k[2]}: {use[k]}")
