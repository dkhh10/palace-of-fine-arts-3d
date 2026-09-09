"""Round 8: where the hero north-wing band's foliage actually comes from, column by column.

QA-04-6's box is cam 01 `1360 480 1860 600` of 1920x1080 (frame x 0.708-0.969, y 0.444-0.556).  In ref 169 the
dark tree mass sits only in the LEFT sliver of that box (frame x 0.705-0.745, measured in `--ref`); the rest is
lit colonnade.  Round 7 pinned every hand-placed tree on the band, so the clearer can no longer sweep the mass
out and the band came back at 91.9 luminance.  This tool says which instances fill which columns, so the A/A2
cluster can be re-derived by plan change instead of by sweep.

    blender -b --python scripts/env_r8_fit.py -- --band      # ray-cast the band in assets/environment.blend
    python3 scripts/env_r8_fit.py --ref                      # ref 169 column profile (no Blender needed)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BAND = (1360, 480, 1860, 600)
RES = (1920, 1080)
# cam-01 render px -> raw ref-169 px (the round-02 align transform, as in env_sheet_r6.ref_box)
REF_XF = (0.7640, 223.2, 0.7667, 97.0)
REF169 = "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"


# r8 review, finding 5: the mass's vertical extent used to be measured over a hard-coded frame-x window
# 0.705-0.745, i.e. over what the same run then called the mass's RIGHT HALF.  It is a parameter now, and the
# default is the span the widened column profile measured (renders/logs/env_r9_ref_profile.log).
# r9 review, finding 4: that span is NOT "dark fraction >= 0.35 throughout".  The profile is
#   0.61:0.16 | 0.62:0.36  0.63:0.44  0.64:0.33  0.65:0.19  0.66:0.25  0.67:0.28  0.68:0.23  0.69:0.39
#   0.70:0.35  0.71:0.58  0.72:0.56  0.73:0.45 | 0.74:0.14
# so 0.62 and 0.73 are the buckets where the profile CROSSES 0.35 (0.16 to its left, 0.14 to its right, i.e. the
# mass's own edges), the window mean is 0.37, and the middle 0.64-0.68 is a thin stretch of 0.19-0.33 - the gap
# between the near cluster and the dark crown right of the dome, not a solid wall of foliage.
MASS_X = (0.62, 0.735)


def ref_profile(dark=60, mass_x=MASS_X):
    """Column profile of ref 169's dark fraction over the band's rows, in frame-x buckets of 0.01, and the mass's
    dark fraction by frame y over the column window `mass_x`."""
    import numpy as np
    from PIL import Image
    try:
        import common
        root = common.MAIN_ROOT if hasattr(common, "MAIN_ROOT") else common.ROOT
    except Exception:
        from pathlib import Path
        root = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
    im = np.asarray(Image.open(str(root / REF169)).convert("L")).astype(float)
    sx, dx, sy, dy = REF_XF
    y0, y1 = int(BAND[1] * sy + dy), int(BAND[3] * sy + dy)
    x0, x1 = int(BAND[0] * sx + dx), int(BAND[2] * sx + dx)
    band = im[y0:y1, x0:x1]
    print(f"[ref] band box (raw px) {x0} {y0} {x1} {y1}   lum {band.mean():.1f}   dark<{dark} {100 * (band < dark).mean():.1f} %")
    prof = (im[y0:y1, :] < dark).mean(axis=0)
    out = []
    for i in range(55, 100):          # r8 review: start left of the box so the mass's left bound is measured
        fx = i / 100.0
        a, b = int(fx * RES[0] * sx + dx), int((fx + 0.01) * RES[0] * sx + dx)
        out.append((fx, float(prof[a:b].mean())))
    print("[ref] dark fraction by frame x: " + "  ".join(f"{fx:.2f}:{v:.2f}" for fx, v in out))
    # vertical extent of the mass, over its own columns
    a, b = int(mass_x[0] * RES[0] * sx + dx), int(mass_x[1] * RES[0] * sx + dx)
    col = (im[:, a:b] < dark).mean(axis=1)
    rows = []
    for i in range(28, 70):
        fy = i / 100.0
        c, d = int(fy * RES[1] * sy + dy), int((fy + 0.01) * RES[1] * sy + dy)
        rows.append((fy, float(col[c:d].mean())))
    print(f"[ref] mass dark fraction by frame y (x {mass_x[0]:.3f}-{mass_x[1]:.3f}): "
          + "  ".join(f"{fy:.2f}:{v:.2f}" for fy, v in rows))
    return out


def band_cast(step=2):
    """Per-column foliage fraction of the band in assets/environment.blend + architecture, and who fills it."""
    import bpy
    from mathutils import Vector
    import common, qa_cameras

    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ENV"]))
    scene = bpy.context.scene
    arch = common.ASSET_FILES["ARCH"]
    if arch.exists():
        common.link_collection(arch, "ARCH", link=True)
    qa_cameras.ensure(scene)
    dg = bpy.context.evaluated_depsgraph_get()
    spec = next(c for c in qa_cameras.CAMERAS if "_qa_01_" in c["name"])
    loc = Vector(spec["loc"])
    f = (Vector(spec["target"]) - loc).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f).normalized()
    hw = 0.5 * 36.0 / spec["lens"]
    hh = hw * 9.0 / 16.0
    W, H = RES
    x0, y0, x1, y1 = BAND
    hist, cols, tot, fol, bld, gnd = {}, [], 0, 0, 0, 0
    for px in range(x0, x1, step):
        cfol = ctot = 0
        for py in range(y0, y1, step):
            sx = ((px + 0.5) / W - 0.5) * 2
            sy = (0.5 - (py + 0.5) / H) * 2 + 2.0 * spec.get("shift_y", 0.0) * (hw / hh)
            d = (f + r * hw * sx + u * hh * sy).normalized()
            ok, hit, nrm, idx, obj, _ = scene.ray_cast(dg, loc, d, distance=4000)
            tot += 1
            ctot += 1
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
                cfol += 1
                hist[nm] = hist.get(nm, 0) + 1
            elif ("terrain" in nm or "ground" in nm or "water" in nm or "bed" in nm
                  or "lawn" in mat or "gravel" in mat or "bed" in mat):
                gnd += 1
            else:
                bld += 1
        cols.append(((px + 0.5) / W, cfol / max(1, ctot)))
    print(f"\n[band] {x0} {y0} {x1} {y1}  foliage {100 * fol / tot:.1f} %  building {100 * bld / tot:.1f} %  "
          f"ground {100 * gnd / tot:.1f} %  sky {100 * (tot - fol - bld - gnd) / tot:.1f} %")
    buckets = {}
    for fx, v in cols:
        b = round(fx, 2)
        buckets.setdefault(b, []).append(v)
    print("[band] foliage fraction by frame x: "
          + "  ".join(f"{b:.2f}:{sum(v) / len(v):.2f}" for b, v in sorted(buckets.items())))
    print("[band] instances filling the box (share of the whole box):")
    for nm, c in sorted(hist.items(), key=lambda kv: -kv[1])[:26]:
        o = bpy.data.objects.get(nm)
        where = f"({o.location.x:7.1f},{o.location.y:7.1f})" if o else ""
        note = (o.get("note", "") if o else "")[:44]
        print(f"   {100 * c / tot:5.2f}%  {nm:44s} {where}  {note}")


def _isnum(v):
    try:
        float(v)
        return True
    except ValueError:
        return False


# ----------------------------------------------------------------------------- placement solver
def solve(target_x, r_off):
    """World (X, Y) that projects to `target_x` in cam 01 and stands `r_off` m outside the colonnade arc.

    cam 01 is on the lagoon-face normal, so its frame-x is a closed form in (X, Y):
        x = 0.5 + 0.5556 * (-0.9902 X - 0.1396 Y) / (0.1396 X - 0.9902 Y + 100.99)
    (loc (-14.1, 100, 1.6) -> target (0,0,1.6), 20 mm on a 36 mm sensor.)  The second constraint is the OSM strip:
    the A2 planting belongs BETWEEN the north wing and the embayment, i.e. OUTSIDE the wing's arc
    (arch_params.COL_ARC_CENTER / COL_ARC_R), which is also what puts the trunks behind the colonnade from the hero.
    """
    import math
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import arch_params as AP
    cx, cy = AP.COL_ARC_CENTER
    R = AP.COL_ARC_R + r_off
    import qa_cameras                     # r8 review: station and lens from the QA camera set, not hand-copied
    spec = next(c for c in qa_cameras.CAMERAS if "_qa_01_" in c["name"])
    lx, ly = spec["loc"][0], spec["loc"][1]
    fx, fy = (spec["target"][0] - lx), (spec["target"][1] - ly)
    n = math.hypot(fx, fy)
    fx, fy = fx / n, fy / n
    rx, ry = fy, -fx                      # f x (0,0,1)
    k = 0.5 * 36.0 / spec["lens"]       # tan(half hfov)

    def frame_x(X, Y):
        dx, dy = X - lx, Y - ly
        z = dx * fx + dy * fy
        return 0.5 + 0.5 * ((dx * rx + dy * ry) / z) / k

    # walk the arc, pick the point whose frame x matches
    best = None
    for i in range(4000):
        a = math.radians(180.0 + i * 120.0 / 4000.0)      # the north wing's quadrant of the arc
        X, Y = cx + R * math.cos(a), cy + R * math.sin(a)
        if Y > 40 or X > 0:
            continue
        e = abs(frame_x(X, Y) - target_x)
        if best is None or e < best[0]:
            best = (e, X, Y)
    _, X, Y = best
    print(f"[solve] frame x {target_x:.3f}, {r_off:+.1f} m outside the arc -> ({X:7.2f}, {Y:7.2f})  "
          f"check x {frame_x(X, Y):.3f}  r {math.hypot(X - cx, Y - cy):.1f}")
    return X, Y


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--ref" in argv:
        i = argv.index("--ref")
        w = [float(v) for v in argv[i + 1:i + 3] if _isnum(v)]
        ref_profile(mass_x=(w[0], w[1]) if len(w) == 2 else MASS_X)
    if "--solve" in argv:
        i = argv.index("--solve")
        for tx in ([float(v) for v in argv[i + 1:] if _isnum(v)] or [0.79, 0.82, 0.89]):
            solve(tx, 8.0)
    if "--band" in argv:
        band_cast()
