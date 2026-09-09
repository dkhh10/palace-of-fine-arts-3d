"""ORN round 5: what a DEEPER attic-panel relief would cost, measured instead of guessed (no render).

    scripts/blender_run.sh 1800 -- --background --python scripts/orn_r5_reliefcost.py -- [--object NAME] [--scales 1.0,1.25,1.5]

The relief is deepened by scaling the mesh along +Y about the slab face (exactly what the builder's `proud`
parameter does). For each factor the script reports the front-surface area of the panel and the resulting depth
percentiles. Tris scale with surface area at constant density, so the cost per LOD is
    tris(f) = tris(now) * area(f) / area(1.0)
which is printed against each tier budget. Also verifies the round-5 LOD2 rebuild kept the silhouette.
"""
import bpy, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L

ARGS = common.script_args()
NAME = ARGS[ARGS.index("--object") + 1] if "--object" in ARGS else "ORN_attic_panel_v2_LOD0"
SCALES = [float(s) for s in (ARGS[ARGS.index("--scales") + 1] if "--scales" in ARGS else "1.0,1.25,1.5").split(",")]
SLAB = 0.16          # the panel's backing slab: relief is everything in front of y = SLAB

bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ORN"]), load_ui=False)


def front_area(obj):
    """Area of the faces that face outward (+Y), computed from the vertex coordinates (polygon.normal / .area are
    cached and do NOT follow a mesh.transform, which silently made every scale factor read the same)."""
    me = obj.data
    co = [v.co for v in me.vertices]
    a = 0.0
    for poly in me.polygons:
        vi = list(poly.vertices)
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(vi)):                      # Newell
            p1, p2 = co[vi[i]], co[vi[(i + 1) % len(vi)]]
            n.x += (p1.y - p2.y) * (p1.z + p2.z)
            n.y += (p1.z - p2.z) * (p1.x + p2.x)
            n.z += (p1.x - p2.x) * (p1.y + p2.y)
        if n.y > 0.0:
            a += 0.5 * n.length      # TRUE area of the outward-facing faces (the projected +Y area is invariant
                                     # under a Y scale, so it cannot measure the cost of deeper relief)
    return a


def depth_stats(obj):
    ys = sorted(v.co.y for v in obj.data.vertices)
    n = len(ys)
    return ys[int(0.5 * n)], ys[int(0.9 * n)], ys[-1]


src = bpy.data.objects[NAME]
base_tris = L.tri_count(src)
budgets = L.BUDGETS["attic_panel"]
print(f"[cost] {NAME}: {base_tris} tris, budgets {budgets}")
rows = []
for f in SCALES:
    tmp = L.duplicate(src, f"{NAME}__s{f}", src.users_collection[0])
    tmp.data.transform(Matrix.Translation((0, SLAB, 0)) @ Matrix.Diagonal((1.0, f, 1.0, 1.0))
                       @ Matrix.Translation((0, -SLAB, 0)))
    area = front_area(tmp)
    p50, p90, mx = depth_stats(tmp)
    rows.append((f, area, p50, p90, mx))
    L.remove_object(tmp)
a0 = rows[0][1]
print(f"[cost] relief measured in front of the {SLAB:.2f} m slab face")
for f, area, p50, p90, mx in rows:
    r = area / a0
    print(f"  proud x{f:.2f}: relief above the slab p50 {(p50-SLAB)*1000:6.1f}  p90 {(p90-SLAB)*1000:6.1f}  "
          f"max {(mx-SLAB)*1000:6.1f} mm | front area {area:7.2f} m2 (x{r:.3f}) | tris at constant density "
          f"LOD0 {base_tris*r:8.0f} / LOD1 {budgets[1]*r:7.0f} / LOD2 {budgets[2]*r:6.0f}  "
          f"(budgets {budgets[0]}/{budgets[1]}/{budgets[2]}) "
          f"{'OK' if base_tris*r <= budgets[0] else 'OVER LOD0 BUDGET'}")

print("\n[cost] LOD2 silhouette after the round-5 rebuild (vertex-y percentiles, LOD1 vs LOD2)")
for v in (1, 2, 3):
    for lod in (1, 2):
        o = bpy.data.objects.get(f"ORN_attic_panel_v{v}_LOD{lod}")
        if o is None:
            continue
        p50, p90, mx = depth_stats(o)
        (x0, y0, z0), (x1, y1, z1) = L.bbox(o)
        print(f"  ORN_attic_panel_v{v}_LOD{lod}: {L.tri_count(o):7d} tris  bbox {x1-x0:.2f} x {y1-y0:.2f} x {z1-z0:.2f} m  "
              f"vertex y p50 {p50*1000:6.1f} p90 {p90*1000:6.1f} max {mx*1000:6.1f} mm")
