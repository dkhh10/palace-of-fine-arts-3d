"""ORN diagnostic: measure real relief depth and lit-shading variance of the ornament assets (QA-02-9/10).

    blender --background --python scripts/orn_relief_check.py -- [--blend assets/ornament.blend] [--objects NAME ...]

For each object it ray-casts a grid from the front (+Y) and reports:
  proud depth percentiles above the slab face, fraction of the field standing >= 6/15/25/40 cm proud,
  and the distribution of N.L for the morning sun on a panel whose outward normal is +Y (the flat-light case),
  plus the mean cosine spread (how much the surface normals turn away from the face) which is what makes
  relief read at a near-normal low sun.
Also dumps ARCH socket frames when --sockets is given.
"""
import bpy, sys, os, math, statistics
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def arg(name, default=None):
    return args[args.index(name) + 1] if name in args else default


SUN_AZ, SUN_EL = 118.5, 7.4


def sockets_report():
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ARCH"]), load_ui=False)
    s = common.sun_direction(SUN_AZ, SUN_EL)
    print(f"[chk] sun vector {tuple(round(v,4) for v in s)}")
    for pref in ("SOCKET_attic_panel", "SOCKET_attic_figure", "SOCKET_finial", "SOCKET_urn_"):
        for o in sorted(bpy.data.objects, key=lambda o: o.name):
            if not o.name.startswith(pref):
                continue
            m = o.matrix_world
            n = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
            print(f"[chk] {o.name:28s} loc=({m.translation.x:8.2f},{m.translation.y:8.2f},{m.translation.z:7.2f}) "
                  f"+Y=({n.x:6.3f},{n.y:6.3f},{n.z:6.3f}) s.n={s.dot(n):6.3f} "
                  f"sub={o.get('subtype')} hint={o.get('size_hint')}")


def depth_report(obj, nx=260, nz=120):
    """Ray-cast a grid at the object from +Y; report how far the hit stands proud of the object's min-y plane."""
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
    y0, y1 = min(v.y for v in bb), max(v.y for v in bb)
    z0, z1 = min(v.z for v in bb), max(v.z for v in bb)
    from mathutils.bvhtree import BVHTree
    me = obj.data
    mw = obj.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    s = common.sun_direction(SUN_AZ, SUN_EL)
    depths, cosines = [], []
    misses = 0
    for i in range(nx):
        x = x0 + (i + 0.5) * (x1 - x0) / nx
        for k in range(nz):
            z = z0 + (k + 0.5) * (z1 - z0) / nz
            loc, nor, idx, dist = bvh.ray_cast(Vector((x, y1 + 1.0, z)), Vector((0, -1, 0)))
            if loc is None:
                misses += 1
                continue
            depths.append(loc.y - y0)
            cosines.append(max(0.0, nor.normalized().dot(s)))
    depths.sort()
    n = len(depths)
    if not n:
        print(f"[chk] {obj.name}: no hits")
        return

    def pct(p):
        return depths[min(n - 1, int(p * n))]
    span = y1 - y0
    tris = len(me.polygons)
    print(f"[chk] {obj.name}: bbox {x1-x0:.2f} x {span:.2f} x {z1-z0:.2f} m, tris {tris}, hits {n} miss {misses}")
    print(f"      depth above back plane: p10 {pct(.10):.3f}  p50 {pct(.50):.3f}  p90 {pct(.90):.3f}  max {depths[-1]:.3f}")
    for thr in (0.06, 0.15, 0.25, 0.40, 0.55):
        frac = sum(1 for d in depths if d >= thr) / n
        print(f"      frac >= {thr*100:4.0f} cm proud: {frac*100:5.1f} %")
    mean = statistics.fmean(cosines)
    sd = statistics.pstdev(cosines)
    dark = sum(1 for c in cosines if c < 0.35 * max(cosines)) / len(cosines)
    print(f"      N.L (sun {SUN_AZ}/{SUN_EL} on a +Y face): mean {mean:.3f} sd {sd:.3f} rel-sd {sd/max(1e-6,mean):.3f} "
          f"frac dark(<35% of max) {dark*100:.1f} %")


def arch_objects_report(patterns):
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ARCH"]), load_ui=False)
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if o.type != "MESH" or not any(p in o.name for p in patterns):
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(v[i] for v in bb) for i in range(3)))
        hi = Vector((max(v[i] for v in bb) for i in range(3)))
        print(f"[chk] ARCH {o.name:44s} size {hi.x-lo.x:6.2f} x {hi.y-lo.y:6.2f} x {hi.z-lo.z:6.2f}  "
              f"centre ({0.5*(lo.x+hi.x):7.2f},{0.5*(lo.y+hi.y):7.2f},{0.5*(lo.z+hi.z):7.2f}) tris {len(o.data.polygons)}")


def main():
    if "--arch" in args:
        i = args.index("--arch") + 1
        pats = []
        while i < len(args) and not args[i].startswith("--"):
            pats.append(args[i]); i += 1
        arch_objects_report(pats)
        if "--objects" not in args:
            return
    if "--sockets" in args:
        sockets_report()
        if "--objects" not in args:
            return
    blend = arg("--blend", str(common.ASSET_FILES["ORN"]))
    bpy.ops.wm.open_mainfile(filepath=blend, load_ui=False)
    names = []
    if "--objects" in args:
        i = args.index("--objects") + 1
        while i < len(args) and not args[i].startswith("--"):
            names.append(args[i]); i += 1
    else:
        names = ["ORN_attic_panel_v1_LOD0", "ORN_attic_panel_v1_LOD1", "ORN_attic_figure_v1_LOD0",
                 "ORN_corner_scroll_v1_LOD0", "ORN_capital_rotunda_v1_LOD0"]
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o is None:
            print(f"[chk] MISSING {nm}")
            continue
        depth_report(o)


main()
