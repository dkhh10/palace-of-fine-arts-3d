"""Sight-line check for the planting plan (QA-01-6).

Projects every planted tree of `env_trees.PLAN` into the QA cameras and reports which trees land inside a
camera's "must stay clear" zone. Run headless:

    blender -b --python scripts/env_sightlines.py
    blender -b --python scripts/env_sightlines.py -- --cam 02 --zone 0.60 1.00
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, qa_cameras, env_trees

# camera -> (x0, x1) of the frame band that must stay clear of near trees, and the near distance in metres
CLEAR_ZONES = {
    "CAM_qa_02_lagoon_ne_threequarter": (0.60, 0.88, 60.0),
    "CAM_qa_03_colonnade_walk": (0.00, 0.30, 60.0),
}
CROWN_R = {"cypress_column": 0.20, "redwood": 0.22, "cypress": 0.34, "pine": 0.36, "eucalyptus": 0.34,
           "willow": 0.45, "broadleaf": 0.42}


def basis(loc, target):
    f = (Vector(target) - Vector(loc)).normalized()
    r = f.cross(Vector((0.0, 0.0, 1.0))).normalized()
    u = r.cross(f).normalized()
    return f, r, u


def project(spec, p):
    """World point -> (frame x, frame y in 0..1, distance along the axis). Sensor 36 mm horizontal, 16:9."""
    f, r, u = basis(spec["loc"], spec["target"])
    d = Vector(p) - Vector(spec["loc"])
    z = d.dot(f)
    if z <= 0.05:
        return None
    half_w = 0.5 * 36.0 / spec["lens"]                 # tan(half hfov)
    half_h = half_w * 9.0 / 16.0
    x = 0.5 + 0.5 * (d.dot(r) / z) / half_w
    y = 0.5 - 0.5 * (d.dot(u) / z) / half_h + spec.get("shift_y", 0.0)
    return x, y, z


def tree_frame_box(spec, tree):
    sp, X, Y, H = tree[0], tree[1], tree[2], tree[3]
    rad = CROWN_R.get(sp, 0.35) * H
    pts = []
    for dx, dy in ((rad, 0), (-rad, 0), (0, rad), (0, -rad)):
        for z in (0.0, H * 0.55, H):
            q = project(spec, (X + dx, Y + dy, -0.5 + z))
            if q:
                pts.append(q)
    if not pts:
        return None
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts), min(p[2] for p in pts))


def placed_trees():
    """Actual planted positions from assets/environment.blend (PLAN positions are snapped onto land at build time)."""
    path = str(common.ASSET_FILES["ENV"])
    with bpy.data.libraries.load(path) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith("ENV_tree_") and n.endswith("_LOD0")]
    out = []
    for o in bpy.data.objects:
        if not (o.name.startswith("ENV_tree_") and o.name.endswith("_LOD0")):
            continue
        out.append((o.get("species", "?"), o.location.x, o.location.y, float(o.get("height_m", 20.0)),
                    str(o.get("note", ""))))
    return out


def main():
    args = common.script_args()
    plan = env_trees.PLAN if "--plan" in args else placed_trees()
    specs = {c["name"]: c for c in qa_cameras.CAMERAS}
    zones = dict(CLEAR_ZONES)
    if "--cam" in args:
        i = args.index("--cam")
        name = [n for n in specs if f"_qa_{args[i + 1]}_" in n][0]
        x0, x1 = (float(args[args.index("--zone") + 1]), float(args[args.index("--zone") + 2])) if "--zone" in args else (0.0, 1.0)
        zones = {name: (x0, x1, 1e9)}
    for name, (x0, x1, near) in zones.items():
        spec = specs[name]
        print(f"\n=== {name}  loc={spec['loc']} lens={spec['lens']}  clear zone x {x0:.2f}-{x1:.2f} within {near:g} m")
        hits = []
        for i, tree in enumerate(plan):
            box = tree_frame_box(spec, tree)
            if not box:
                continue
            bx0, bx1, by0, by1, dist = box
            if dist > near or bx1 < x0 or bx0 > x1 or by1 < 0.0 or by0 > 1.0:
                continue
            overlap = (min(bx1, x1) - max(bx0, x0)) / max(1e-6, x1 - x0)
            hits.append((overlap, i, tree, box))
        hits.sort(reverse=True)
        for overlap, i, tree, box in hits:
            print(f"  #{i:3d} {tree[0]:15s} ({tree[1]:6.1f},{tree[2]:6.1f}) h{tree[3]:4.0f}  d={box[4]:6.1f} m  "
                  f"x {box[0]:5.2f}..{box[1]:5.2f}  y {box[2]:5.2f}..{box[3]:5.2f}  zone cover {overlap * 100:4.0f}%   {tree[4][:40]}")
        if not hits:
            print("  clear")


main()
