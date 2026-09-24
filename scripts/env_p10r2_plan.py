"""Phase 10 ENV round 2: gates + cam-01 prediction for the hero-shore willow (PLAN entry "P hero-shore willow, ref 169").

    scripts/blender_run.sh 300 -- --background --python scripts/env_p10r2_plan.py -- [--cand X Y H W ...] [--add] [--check]

No Blender data is touched (bpy only because qa_cameras / env_trees import it).  For each candidate (and, with
--check, for the shipped PLAN entry with its env_trees.P10R2_WIDEN factor) it prints the plan's rules:
  dry        lagoon signed distance >= 1.0 m (the build's land_snap predicate; the shoreline is at WATER_Z)
  gallery    env_lib.gallery_offset >= GALLERY_KEEPOUT
  ring       QA-02-13 podium ring: |trunk| - crown radius >= 37 m, crown radius = max(CROWN_R, the measured Sapling
             radius P10_REAL_R x CROWN_XY x widen) x h - the widened crown, not the nominal one
  spacing    >= 3.5 m from every other PLAN / P10_ADD trunk
and the cam-01 prediction: trunk frame x, crown frame-x span (measured radius x CROWN_XY x widen, the nominal draw),
the frame row of the crown top (ground - 0.15 + h), plus the cam-02 / cam-05 frame boxes (env_trees._frame_box).
The render (`env_p10r2_mask.py`) is the measurement; this is the pre-build filter.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L
import env_trees as T
import qa_cameras

ARGS = common.script_args()
SPEC = {c["name"][7:9]: c for c in qa_cameras.CAMERAS}
PODIUM_R, CLEAR, SPACING = 31.0, 6.0, 3.5
KEY = "P hero-shore willow, ref 169"


def frame(spec, x, y, z):
    from mathutils import Vector
    f, r, u = T._cam_basis(spec)
    d = Vector((x, y, z)) - Vector(spec["loc"])
    zz = d.dot(f)
    hw = 0.5 * 36.0 / spec["lens"]
    hh = hw * 9.0 / 16.0
    shift = spec.get("shift_y", 0.0) * (hw / hh)
    return 0.5 + 0.5 * (d.dot(r) / zz) / hw, 0.5 - 0.5 * (d.dot(u) / zz) / hh + shift, zz


def real_r(sp, w):
    return max(L.CROWN_R.get(sp, 0.35), T.P10_REAL_R.get(sp, 0.35) * T.CROWN_XY.get(sp, 1.0) * w)


def report(x, y, h, w, lagoon, islets, skip, terrain=None, tag="cand"):
    sp = "willow"
    lag = lagoon.signed(x, y)
    dry = not (lag < 1.0 and not any(f.signed(x, y) < 0 for f in islets))
    g = L.gallery_offset(x, y)
    gok = g is None or g >= L.GALLERY_KEEPOUT
    ring = math.hypot(x, y) - real_r(sp, w) * h
    others = [(p[1], p[2]) for p in T.PLAN if not str(p[4]).startswith(skip)] + [(p[1], p[2]) for p in T.P10_ADD] \
        + [(p[1], p[2]) for p in getattr(T, "P10R2_ADD", []) if p[4] != skip]
    space = min(math.hypot(x - a, y - b) for a, b in others)
    z0 = (terrain(x, y) if terrain else -0.45) - 0.15
    cx, _, d = frame(SPEC["01"], x, y, z0 + 0.6 * h)
    _, ytop, _ = frame(SPEC["01"], x, y, z0 + h)
    half = 0.5 * (real_r(sp, w) * h / d) / (0.5 * 36.0 / SPEC["01"]["lens"])
    boxes = {}
    for k in ("02", "05"):
        s = SPEC[k]
        f, r, u = T._cam_basis(s)
        boxes[k] = T._frame_box(s, f, r, u, x, y, h, sp)
    ok = dry and gok and ring >= PODIUM_R + CLEAR and space >= SPACING
    b2, b5 = boxes["02"], boxes["05"]
    print(f"  {'PASS' if ok else 'fail'} {tag:6s} ({x:6.2f},{y:6.2f}) h{h:4.1f} w{w:4.2f}  lagoon {lag:5.2f} dry {dry}  "
          f"gallery {'-' if g is None else f'{g:.1f}'}  ring {ring:5.1f}  space {space:4.1f}  |  cam01 trunk x {cx:.3f} "
          f"span {cx - half:.3f}-{cx + half:.3f} top row {ytop * 1080:4.0f} d {d:5.1f}  |  cam02 "
          f"{'-' if b2 is None else f'x {b2[0]:.2f}-{b2[1]:.2f} y {b2[2]:.2f}'}  cam05 "
          f"{'-' if b5 is None else f'x {b5[0]:.2f}-{b5[1]:.2f} y {b5[2]:.2f}-{b5[3]:.2f} d {b5[4]:.0f}'}")
    return ok


def main():
    site = common.load_site_local()
    _osm, _lag, _isl, lagoon, islets = L.water_polygons(site)
    bad = 0
    if "--cand" in ARGS:
        v = [float(a) for a in ARGS[ARGS.index("--cand") + 1:] if not a.startswith("--")]
        print("[env_p10r2_plan] candidates (x, y, h, widen)")
        for i in range(0, len(v) - 3, 4):
            # --add: a candidate for an APPENDED instance (every PLAN trunk counts for spacing, the moved willow too)
            report(*v[i:i + 4], lagoon, islets, "\0" if "--add" in ARGS else KEY + " x 0.3")
    if "--check" in ARGS:
        print("[env_p10r2_plan] shipped PLAN entry")
        for (sp, x, y, h, note) in T.PLAN:
            if str(note).startswith(KEY) and note in T.P10R2_WIDEN:
                bad += 0 if report(x, y, h, T.P10R2_WIDEN[note], lagoon, islets, note, tag="PLAN") else 1
        for (sp, x, y, h, note, w) in getattr(T, "P10R2_ADD", []):
            bad += 0 if report(x, y, h, w, lagoon, islets, note, tag="ADD") else 1
        print(f"[env_p10r2_plan] {bad} failing")
    if bad:
        sys.exit(1)


main()
