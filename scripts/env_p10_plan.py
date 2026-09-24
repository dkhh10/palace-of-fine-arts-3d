"""Phase 10 ENV item 1: where can a crown stand so that cam 01 sees it right of the rotunda, tops near ref 169's row?

    scripts/blender_run.sh 300 -- --background --python scripts/env_p10_plan.py -- [--search] [--check]

No Blender data is touched (bpy only because qa_cameras / env_trees import it).

Why a search at all (numbers, cam 01 = loc (-14.1, 100, 1.3), 20 mm, shift_y 0.06):
  frame y of a point at height z and axis distance d is  y = 0.607 - (z - 1.3) / (1.0125 d).
  Ref 169's crown-top row right of the rotunda (env_p10_boxes box 1s, median over x 0.655-0.740) is 398 px = y 0.369.
  The A cluster stands at d 141-145 m: y 0.369 there needs a crown top at z ~ 36 m, against the species windows
  (cypress 15-25, pine 15-24, cypress_column 18-28 m).  No leaf-card or crown-scale change reaches it, so the mass has
  to come from nearer instances.  Every ray through frame x 0.66-0.74 passes the rotunda at 27-35 m and QA-02-13's
  podium ring wants trunk r - CROWN_R x h >= 37 m, so the only dry land that projects there is the peninsula shore
  in front of the ring, d ~ 60-68 m, where y 0.369 needs a crown top of only ~16-17 m.

Gates for a candidate (the three of `env_r9_replan.gates` + the cam-01 span rule + the other stations):
  dry (lagoon signed >= 1.0), gallery keep-out, podium ring at the PLAN height; cam 01 crown span (measured Sapling
  radius, not CROWN_R) left edge >= 0.658 (the rotunda's right edge at y 0.28-0.52 in the before frame is 0.655) and
  right edge <= 0.765 (QA-04-6's north-wing band starts at 0.760; crowns there in ref 169 reach 0.78); cam 05's
  QA-03-13 silhouette box untouched (with CROWN_SAFETY); cam 02 box printed.
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
# measured Sapling crown radius / height (renders/logs/p9_env_build6.log, LOD0 of each seed, mean)
REAL_R = T.P10_REAL_R
PODIUM_R, CLEAR = 31.0, 6.0
ROT_EDGE, BAND_X0 = 0.658, 0.765


def frame(spec, x, y, z):
    f, r, u = T._cam_basis(spec)
    from mathutils import Vector
    d = Vector((x, y, z)) - Vector(spec["loc"])
    zz = d.dot(f)
    hw = 0.5 * 36.0 / spec["lens"]
    hh = hw * 9.0 / 16.0
    shift = spec.get("shift_y", 0.0) * (hw / hh)
    return 0.5 + 0.5 * (d.dot(r) / zz) / hw, 0.5 - 0.5 * (d.dot(u) / zz) / hh + shift, zz


def crown_r(sp, h, w=1.0):
    """Ring radius: CROWN_R x h, or the measured radius x the P10 crown-width factor when that is larger."""
    return max(L.CROWN_R.get(sp, 0.35), REAL_R[sp] * w) * h


def cam01(sp, x, y, h, w=1.0, ground=-0.45):
    cx, _, d = frame(SPEC["01"], x, y, ground + h * 0.6)
    _, ytop, _ = frame(SPEC["01"], x, y, ground + h)
    half = 0.5 * (REAL_R[sp] * w * h / d) / (0.5 * 36.0 / SPEC["01"]["lens"])
    return cx - half, cx + half, ytop, d


SPACING = 3.5     # m from any PLAN trunk: two trunks closer than this read as one planting mistake


def spaced(x, y):
    return min(math.hypot(x - p[1], y - p[2]) for p in T.PLAN)


def gates(sp, x, y, h, lagoon, islets, w=1.0):
    dry = not (lagoon.signed(x, y) < 1.0 and not any(f.signed(x, y) < 0 for f in islets))
    g = L.gallery_offset(x, y)
    ring = math.hypot(x, y) - crown_r(sp, h, w)
    return dry and spaced(x, y) >= SPACING, (g is None or g >= L.GALLERY_KEEPOUT), ring >= PODIUM_R + CLEAR, ring


def other_cams(sp, x, y, h):
    out = {}
    for k in ("02", "05"):
        s = SPEC[k]
        f, r, u = T._cam_basis(s)
        out[k] = T._frame_box(s, f, r, u, x, y, h, sp)
    return out


def cam05_ok(box):
    if box is None:
        return True
    band = next(b for b in T.FRAME_BANDS if b["cam"] == "_qa_05_")
    if box[4] > band["near"]:
        return True
    return box[1] < band["x0"] or box[0] > band["x1"] or box[2] > band["y1"]


def report(sp, x, y, h, lagoon, islets, tag="", w=1.0):
    dry, gok, pok, ring = gates(sp, x, y, h, lagoon, islets, w)
    x0, x1, ytop, d = cam01(sp, x, y, h, w)
    oc = other_cams(sp, x, y, h)
    b2, b5 = oc["02"], oc["05"]
    ok = dry and gok and pok and x0 >= ROT_EDGE and x1 <= BAND_X0 and cam05_ok(b5)
    print(f"  {'PASS' if ok else 'fail'} {tag:10s} {sp:14s} ({x:6.1f},{y:6.1f}) h{h:5.1f} w{w:4.2f}  lagoon {lagoon.signed(x, y):5.1f}"
          f"  space {spaced(x, y):4.1f}"
          f"  ring {ring:5.1f}  cam01 x {x0:.3f}-{x1:.3f} top y {ytop:.3f} (px {ytop * 1080:4.0f}) d {d:5.1f}"
          f"  cam02 {'-' if b2 is None else f'x {b2[0]:.2f}-{b2[1]:.2f} y {b2[2]:.2f}'}"
          f"  cam05 {'-' if b5 is None else f'x {b5[0]:.2f}-{b5[1]:.2f} y {b5[2]:.2f}-{b5[3]:.2f} d {b5[4]:.0f}'}"
          f"{'' if cam05_ok(b5) else ' <-- QA-03-13'}")
    return ok


def main():
    site = common.load_site_local()
    _osm, _lag, _isl, lagoon, islets = L.water_polygons(site)
    if "--search" in ARGS:
        W = float(ARGS[ARGS.index("--w") + 1]) if "--w" in ARGS else 1.0
        for sp, hs in (("cypress", (15.0, 16.0, 17.0, 18.0)), ("cypress_column", (18.0, 19.0, 20.0, 21.0)),
                       ("pine", (15.0, 16.0, 17.0))):
            w = W if sp == "cypress_column" else 1.0
            print(f"\n[env_p10_plan] {sp}: passing positions, frame-x centre 0.66-0.75, d 55-75 m")
            for h in hs:
                best = []
                for i in range(0, 41):
                    t = 0.66 + 0.0025 * i
                    k = (t - 0.5) * 2 * (0.5 * 36.0 / SPEC["01"]["lens"])
                    for dd in range(55, 76):
                        s = SPEC["01"]
                        fx, fy = s["target"][0] - s["loc"][0], s["target"][1] - s["loc"][1]
                        n = math.hypot(fx, fy)
                        fx, fy = fx / n, fy / n
                        rx, ry = fy, -fx
                        x = s["loc"][0] + dd * fx + k * dd * rx
                        y = s["loc"][1] + dd * fy + k * dd * ry
                        dry, gok, pok, ring = gates(sp, x, y, h, lagoon, islets, w)
                        x0, x1, ytop, d = cam01(sp, x, y, h, w)
                        if dry and gok and pok and x0 >= ROT_EDGE and x1 <= BAND_X0 and cam05_ok(other_cams(sp, x, y, h)["05"]):
                            best.append((abs(ytop - 0.369) + (abs(x0 - float(ARGS[ARGS.index("--x0") + 1])) if "--x0" in ARGS else 0.0), x, y))
                best.sort()
                for _, x, y in best[:int(ARGS[ARGS.index("--n") + 1]) if "--n" in ARGS else 3]:
                    report(sp, round(x, 1), round(y, 1), h, lagoon, islets, "cand", w)
    if "--check" in ARGS or "--search" not in ARGS:
        print("\n[env_p10_plan] env_trees.P10_ADD")
        bad = 0
        for (sp, x, y, h, note, w) in getattr(T, "P10_ADD", []):
            bad += 0 if report(sp, x, y, h, lagoon, islets, note.split(" ")[0], w) else 1
        print(f"[env_p10_plan] {bad} failing P10_ADD entr{'y' if bad == 1 else 'ies'}")
        if bad:
            sys.exit(1)


main()
