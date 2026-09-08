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
    # shift_y is in units of the larger sensor dimension (the 36 mm width), so as a fraction of frame HEIGHT
    # it carries the aspect factor W/H = half_w/half_h = 16/9.  cam 01's shift_y 0.06 = 0.107 of the height
    # (115 px of 1080), not 0.06 (65 px).
    y = 0.5 - 0.5 * (d.dot(u) / z) / half_h + spec.get("shift_y", 0.0) * (half_w / half_h)
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



# ----------------------------------------------------------------------------- sun shadowing (QA-02-7)
# The geometry lives in env_lib so env_trees.shadow_relief and this checker cannot drift apart.
import env_lib as L


def shadow_report(trees, site, az=L.SUN_AZ, el=L.SUN_EL):
    polys = [L.ensure_ccw(L.dedupe_poly(site[k][0])) for k in ("roof310 h19", "roof306 h20")]
    samples = L.wing_samples(polys)
    per, blockers = L.shadowed_fraction(samples, trees, az, el)
    sv = L.sun_vector(az, el)
    print(f"\n=== sun shadowing of the colonnade faces  (az {az} el {el}, sun {sv[0]:+.3f},{sv[1]:+.3f},{sv[2]:+.3f})")
    for (wi, z), (tot, sh) in sorted(per.items()):
        print(f"  {('north', 'south')[wi]:5s} wing z={z:4.0f} m: {sh:3d}/{tot:3d} in tree shadow = "
              f"{100.0 * sh / max(1, tot):5.1f} %")
    lit = {}
    for (wi, z), (tot, sh) in per.items():
        if z >= 12.0:
            t, x = lit.get(wi, (0, 0))
            lit[wi] = (t + tot, x + sh)
    for wi, (tot, sh) in sorted(lit.items()):
        print(f"  -> {('north', 'south')[wi]} wing readable band (z >= 12 m): {100.0 * (1 - sh / max(1, tot)):.1f} % lit")
    print("  worst casters (samples shadowed):")
    for i, n in sorted(blockers.items(), key=lambda kv: -kv[1])[:20]:
        t = trees[i]
        print(f"    {t[0]:15s} ({t[1]:6.0f},{t[2]:6.0f}) h{t[3]:3.0f}   {n:4d}   {str(t[4])[:36]}")
    return per, blockers


# ----------------------------------------------------------------------------- QA-03-10 / QA-03-13 band coverage
# The QA boxes are stated as luminance ratios against ref 169, but luminance in an ENV preview is set by the
# placeholder sun, not by the shipped lighting rig, so it cannot be compared with a master render.  What ENV
# actually controls is how much of the box is foliage rather than architecture or sky, and that is measured here by
# ray-casting the box in assets/environment.blend + assets/architecture.blend.
COVERAGE_BOXES = {
    "cam01_left_wing": ("_qa_01_", (60, 480, 560, 600), (1920, 1080)),      # QA-03-10 / env_measure left_wing
    "cam01_right_wing": ("_qa_01_", (1360, 480, 1860, 600), (1920, 1080)),
    "cam05_rotunda": ("_qa_05_", (301, 27, 998, 713), (1280, 720)),          # QA-03-13, the rotunda silhouette
    "cam01_shore": ("_qa_01_", (700, 640, 1200, 720), (1920, 1080)),         # QA-03-14 shrub row
    "cam05_podium": ("_qa_05_", (320, 566, 1000, 624), (1280, 720)),        # QA-03-13 podium / Greek-key band
    # Round 6.  QA-03-13's "podium / Greek-key band" box is not on the band: projected, the podium wall's top
    # course (world z 3.8-4.3 at r 27.3-37.6) lands on rows 528-552 of cam 05's 720, while 566-624 is the lawn and
    # shore strip in front of it.  The three boxes below measure what the two round-6 defects actually ask for:
    #   cam05_keyband  - the Greek-key course itself must stay visible (QA-03-13, carried into QA-04-4)
    #   cam05_body     - the rotunda ABOVE the shore, i.e. "no crown inside the silhouette"
    #   cam01_podium_base - the podium's base courses (world z 0-1.5 at r 27.3) which ref 169 hides in foliage
    "cam05_keyband": ("_qa_05_", (330, 526, 990, 554), (1280, 720)),
    "cam05_body": ("_qa_05_", (301, 27, 998, 520), (1280, 720)),
    "cam01_podium_base": ("_qa_01_", (620, 648, 1300, 684), (1920, 1080)),
    # QA-04-14: the bottom 12 % of cam 02's frame (rows 634-720 of 720) - world x 40-64, y -1..31, the south
    # embayment 9-26 m in front of the lens.  Round 4 resolved to water and nothing else.
    "cam02_foreground": ("_qa_02_", (0, 634, 1280, 720), (1280, 720)),
}


def coverage(move_back=(), step=2, shift_aspect=True):
    """Fraction of each box that resolves to foliage / architecture / sky.

    `move_back` is a list of ((x, y), (x, y)) pairs: an object standing at the first position is put back at the
    second before measuring, which is how the before/after for the frame-band relief is produced without a rebuild.

    `shift_aspect=False` reproduces the round-4 (incorrect) ray aim, which applied cam 01's shift_y without the
    16/9 aspect factor - about 50 px of 1080 too low.  Kept only so the round-4 numbers can be quoted against the
    corrected ones on the same scene; never use it to judge a build.
    """
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ENV"]))
    scene = bpy.context.scene
    arch = common.ASSET_FILES["ARCH"]
    if arch.exists():
        common.link_collection(arch, "ARCH", link=True)
    for (frm, to) in move_back:
        n = 0
        for o in bpy.data.objects:
            if o.name.startswith("ENV_tree_") and math.hypot(o.location.x - frm[0], o.location.y - frm[1]) < 1.2:
                o.location.x, o.location.y = to[0], to[1]
                n += 1
        print(f"[coverage] put {n} objects back from {frm} to {to}")
    qa_cameras.ensure(scene)
    dg = bpy.context.evaluated_depsgraph_get()
    print(f"\n[coverage] shift_y aspect factor {'ON (correct)' if shift_aspect else 'OFF (round-4 boxes)'}")
    print(f"{'box':18s} {'foliage':>8s} {'building':>9s} {'ground':>8s} {'sky':>6s} {'arch cols':>10s}")
    out = {}
    for name, (cam_key, box, res) in COVERAGE_BOXES.items():
        spec = next(c for c in qa_cameras.CAMERAS if cam_key in c["name"])
        loc = Vector(spec["loc"])
        f = (Vector(spec["target"]) - loc).normalized()
        r = f.cross(Vector((0, 0, 1))).normalized()
        u = r.cross(f).normalized()
        hw = 0.5 * 36.0 / spec["lens"]
        hh = hw * 9.0 / 16.0
        W, H = res
        x0, y0, x1, y1 = box
        tot = fol = bld = gnd = 0
        hist = {}
        # QA-03-13 / QA-04-4 phrase the podium test as "visible over >= 60 % of its LENGTH", so the area
        # fractions are not the acceptance number: a column of the box counts as visible when any sample in it
        # resolves to architecture.
        cols_any, cols_arch = 0, 0
        for px in range(x0, x1, step):
            cols_any += 1
            col_arch = False
            for py in range(y0, y1, step):
                sx = ((px + 0.5) / W - 0.5) * 2
                sy = (0.5 - (py + 0.5) / H) * 2 \
                    + 2.0 * spec.get("shift_y", 0.0) * ((hw / hh) if shift_aspect else 1.0)
                d = (f + r * hw * sx + u * hh * sy).normalized()
                ok, hit, nrm, idx, obj, _ = scene.ray_cast(dg, loc, d, distance=4000)
                tot += 1
                if not ok:
                    continue
                nm = obj.name
                mat = ""
                if obj.type == "MESH" and obj.data.materials:
                    mi = obj.data.polygons[idx].material_index if idx < len(obj.data.polygons) else 0
                    mm = obj.data.materials[min(mi, len(obj.data.materials) - 1)]
                    mat = mm.name if mm else ""
                if "leaf" in mat or "shrub" in mat or "reed" in mat or "forest" in mat or "canopy" in nm:
                    fol += 1
                    hist[nm] = hist.get(nm, 0) + 1
                elif "terrain" in nm or "ground" in nm or "water" in nm or "lawn" in mat or "gravel" in mat:
                    gnd += 1
                else:
                    bld += 1
                    col_arch = True
            cols_arch += 1 if col_arch else 0
        out[name] = (fol / tot, bld / tot, gnd / tot, 1 - (fol + bld + gnd) / tot,
                     cols_arch / max(1, cols_any))
        print(f"{name:18s} {100 * out[name][0]:7.1f}% {100 * out[name][1]:8.1f}% "
              f"{100 * out[name][2]:7.1f}% {100 * out[name][3]:5.1f}% {100 * out[name][4]:9.1f}%")
        if "--who" in common.script_args():          # which instances actually fill the box
            for nm, c in sorted(hist.items(), key=lambda kv: -kv[1])[:12]:
                o = bpy.data.objects.get(nm)
                where = f"({o.location.x:6.1f},{o.location.y:6.1f})" if o else ""
                print(f"      {100 * c / tot:5.2f}% of box  {nm:42s} {where}")
    return out


def box_map(box_name="cam01_left_wing", out=None):
    """Dump a per-pixel object map of one COVERAGE_BOX (step 1) so the cost of an individual instance in the
    QA-03-10 luminance band can be priced against a real hero render without rebuilding the master.

    Writes an .npz with `names` (object per pixel, "" = sky) and `kind` (0 sky, 1 foliage, 2 building, 3 ground).
    """
    import numpy as np
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ENV"]))
    scene = bpy.context.scene
    arch = common.ASSET_FILES["ARCH"]
    if arch.exists():
        common.link_collection(arch, "ARCH", link=True)
    qa_cameras.ensure(scene)
    dg = bpy.context.evaluated_depsgraph_get()
    cam_key, box, res = COVERAGE_BOXES[box_name]
    spec = next(c for c in qa_cameras.CAMERAS if cam_key in c["name"])
    loc = Vector(spec["loc"])
    f = (Vector(spec["target"]) - loc).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f).normalized()
    hw = 0.5 * 36.0 / spec["lens"]
    hh = hw * 9.0 / 16.0
    W, H = res
    x0, y0, x1, y1 = box
    names = np.empty((y1 - y0, x1 - x0), dtype=object)
    kind = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    for py in range(y0, y1):
        for px in range(x0, x1):
            sx = ((px + 0.5) / W - 0.5) * 2
            sy = (0.5 - (py + 0.5) / H) * 2 + 2.0 * spec.get("shift_y", 0.0) * (hw / hh)
            d = (f + r * hw * sx + u * hh * sy).normalized()
            ok, hit, nrm, idx, obj, _ = scene.ray_cast(dg, loc, d, distance=4000)
            if not ok:
                names[py - y0, px - x0] = ""
                continue
            nm = obj.name
            mat = ""
            if obj.type == "MESH" and obj.data.materials:
                mi = obj.data.polygons[idx].material_index if idx < len(obj.data.polygons) else 0
                mm = obj.data.materials[min(mi, len(obj.data.materials) - 1)]
                mat = mm.name if mm else ""
            names[py - y0, px - x0] = nm
            if "leaf" in mat or "shrub" in mat or "reed" in mat or "forest" in mat or "canopy" in nm:
                kind[py - y0, px - x0] = 1
            elif "terrain" in nm or "ground" in nm or "water" in nm or "lawn" in mat or "gravel" in mat:
                kind[py - y0, px - x0] = 3
            else:
                kind[py - y0, px - x0] = 2
    out = out or (common.ROOT / "renders" / "previews" / "environment" / f"boxmap_{box_name}.npz")
    np.savez_compressed(out, names=names.astype("U48"), kind=kind, box=np.array(box))
    print(f"[box_map] {box_name} {x1 - x0}x{y1 - y0} -> {out}")


def shrub_stats(region=(-30.0, 20.0, 30.0, 60.0)):
    """QA-03-14: size spread and spacing irregularity of the shore shrub row in the hero's near-shore crop.

    The crop QA measured (700 640 1200 720 of the 1920 hero) looks at the peninsula shore in front of the rotunda;
    `region` is that patch of ground in world coordinates.  Reports the 10th/90th percentile height ratio and the
    standard deviation of nearest-neighbour spacing as a fraction of its mean.
    """
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ENV"]))
    x0, y0, x1, y1 = region
    pts = []
    for o in bpy.data.objects:
        if not (o.name.startswith("ENV_shrub_") and o.name.endswith("_LOD1")):
            continue
        if not (x0 <= o.location.x <= x1 and y0 <= o.location.y <= y1):
            continue
        me = o.data
        if not me.vertices:
            continue
        zs = [v.co.z * o.scale.z for v in me.vertices]
        pts.append((o.location.x, o.location.y, max(zs) - min(zs)))
    if len(pts) < 8:
        print(f"[shrub_stats] only {len(pts)} shrubs in {region}")
        return
    hs = sorted(p[2] for p in pts)
    n = len(hs)
    lo, hi = hs[int(0.10 * n)], hs[int(0.90 * n)]
    gaps = []
    for i, a in enumerate(pts):
        d = min(math.hypot(a[0] - b[0], a[1] - b[1]) for j, b in enumerate(pts) if j != i)
        gaps.append(d)
    mean = sum(gaps) / len(gaps)
    var = sum((g - mean) ** 2 for g in gaps) / len(gaps)
    sd = math.sqrt(var)
    print(f"\n[shrub_stats] {n} shrubs in world box {region}")
    print(f"  height p10 {lo:.2f} m, p90 {hi:.2f} m, tallest {hs[-1]:.2f} m -> size spread {hi / max(1e-6, lo):.2f}:1"
          f"   (QA-03-14 wants >= 2:1)")
    print(f"  nearest-neighbour spacing mean {mean:.2f} m, sd {sd:.2f} m -> sd/mean {100 * sd / mean:.0f} %"
          f"   (QA-03-14 wants >= 40 %)")
    mid = hs[n // 2]
    win = sum(1 for h in hs if 1.5 <= h <= 4.0) / n
    print(f"  median {mid:.2f} m; {100 * win:.0f} % of the belt inside QA-04-4's 1.5-4 m window")
    print(f"  tallest within the old rostra radius: {max(h for (x, y, h) in pts if math.hypot(x, y) < 54.0):.2f} m"
          f"   (round 03's flat <= 1.2 m rule is superseded by env_build.band_sightline_cap; the acceptance is"
          f" now the Greek-key band's own visibility, measured as cam05_keyband in --coverage)")


def main():
    args = common.script_args()
    if "--shrubs" in args:
        shrub_stats()
        return
    if "--boxmap" in args:
        box_map(args[args.index("--boxmap") + 1] if len(args) > args.index("--boxmap") + 1 else "cam01_left_wing")
        return
    if "--coverage" in args:
        # `--before` and its hard-coded move-back table are gone: the round-4 pairs it listed no longer exist in
        # the plan, so it silently put 0 objects back.  Before/after is now produced from two real renders of two
        # built masters (scripts/env_r5_hero.py + scripts/env_sheet_r5.py).  coverage(move_back=...) still takes
        # a table if a caller wants one.
        if "--both" in args:                 # round-4 boxes then the corrected ones, same scene
            coverage(shift_aspect=False)
        coverage()
        return
    plan = env_trees.PLAN if "--plan" in args else placed_trees()
    if "--shadow" in args:
        az = float(args[args.index("--az") + 1]) if "--az" in args else L.SUN_AZ
        el = float(args[args.index("--el") + 1]) if "--el" in args else L.SUN_EL
        shadow_report(plan, common.load_site_local(), az, el)
        if "--only-shadow" in args:
            return
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
