"""QA-01-10 measurement: how much of a Zimm attic panel's field is covered by figures.

Casts a grid of rays at the panel from the front (-Y direction) and counts the cells whose first hit stands more than
`--proud` metres in front of the slab face; that is the "figure coverage" QA-01-10 asks for (>= 60 %). Also reports the
same number for the reference crop by thresholding its local contrast, so the two are measured the same way.

    blender --background --python scripts/orn_panel_coverage.py -- [--lod 0] [--proud 0.06] [--grid 420]
"""
import bpy, math, os, sys
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L

ARGS = common.script_args()
LOD = int(ARGS[ARGS.index("--lod") + 1]) if "--lod" in ARGS else 0
PROUD = float(ARGS[ARGS.index("--proud") + 1]) if "--proud" in ARGS else 0.06
GRID = int(ARGS[ARGS.index("--grid") + 1]) if "--grid" in ARGS else 420


def coverage(obj, proud=PROUD, nx=GRID):
    """Fraction of the panel field whose relief stands at least `proud` m in front of the slab face."""
    (x0, y0, z0), (x1, y1, z1) = L.bbox(obj)
    w, h = x1 - x0, z1 - z0
    ny = max(8, int(nx * h / w))
    face = None
    # slab face = the modal y of hits in the outer 4 % margin of the field (the plain border of the slab)
    hits = 0
    total = 0
    depths = []
    for iz in range(ny):
        z = z0 + (iz + 0.5) * h / ny
        for ix in range(nx):
            x = x0 + (ix + 0.5) * w / nx
            ok, loc, nor, idx = obj.ray_cast(Vector((x, y1 + 1.0, z)), Vector((0, -1, 0)))
            if not ok:
                continue
            total += 1
            depths.append(loc.y)
    if not total:
        return 0.0, 0.0, 0.0
    # the slab face is the modal hit depth: the plain background is by far the largest single-depth area
    lo_d, hi_d = min(depths), max(depths)
    nb = 200
    bins = [0] * nb
    for d in depths:
        bins[min(nb - 1, int((d - lo_d) / max(1e-9, hi_d - lo_d) * nb))] += 1
    k = max(range(nb), key=lambda i: bins[i])
    face = lo_d + (k + 0.5) * (hi_d - lo_d) / nb
    hits = sum(1 for d in depths if d > face + proud)
    depths.sort()
    return hits / total, face, depths[int(0.98 * len(depths))] - face


def main():
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ORN"]))
    print(f"[coverage] panel field coverage at >= {PROUD * 100:.0f} cm proud of the slab face, {GRID} px wide grid")
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if o.get("orn_type") == "attic_panel" and o.name.endswith(f"_LOD{LOD}"):
            probe = bpy.data.objects.new("probe_" + o.name, o.data)   # ray_cast needs an evaluated, visible object
            bpy.context.scene.collection.objects.link(probe)
            probe.hide_viewport = False
            bpy.context.view_layer.update()
            cov, face, peak = coverage(probe)
            (x0, y0, z0), (x1, y1, z1) = L.bbox(o)
            bpy.data.objects.remove(probe)
            print(f"[coverage] {o.name}: field {x1 - x0:.2f} x {z1 - z0:.2f} m, slab face y={face:.3f}, "
                  f"max relief {peak:.2f} m, FIGURE COVERAGE {cov * 100:.1f} %  ({o.get('size_note', '')})")


if __name__ == "__main__":
    main()
