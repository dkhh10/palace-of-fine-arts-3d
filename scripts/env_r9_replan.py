"""Round 9: where every hand-placed PLAN tree stands relative to cam 01 and to the colonnade gallery.

    blender -b --python scripts/env_r9_replan.py -- [--solve 0.684 0.704 ...] [--roff 13.0]

No Blender data is touched (it runs headless only because `qa_cameras` imports bpy/mathutils).  For each PLAN
entry it prints the closed-form cam-01 frame x of the trunk, the crown's frame-x span, the distance along the
view axis and `env_lib.gallery_offset` - the radial distance from the colonnade gallery centreline, which is the
number round 9 found four A-group entries failing.  `--solve` re-derives a world position for a target frame x at
`--roff` metres outside the arc (that is `env_r8_fit.solve`, the round-8 tool, so the A group can be re-placed the
way A2 was instead of being swept there by `shadow_relief`).
"""
import sys, os, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L
import env_trees
import env_r8_fit as FIT
import qa_cameras

ARGS = common.script_args()
ROFF = float(ARGS[ARGS.index("--roff") + 1]) if "--roff" in ARGS else 13.0

SPEC = next(c for c in qa_cameras.CAMERAS if "_qa_01_" in c["name"])
LX, LY = SPEC["loc"][0], SPEC["loc"][1]
_fx, _fy = SPEC["target"][0] - LX, SPEC["target"][1] - LY
_n = math.hypot(_fx, _fy)
FWD = (_fx / _n, _fy / _n)
RGT = (FWD[1], -FWD[0])
KTAN = 0.5 * 36.0 / SPEC["lens"]


def frame_x(x, y):
    dx, dy = x - LX, y - LY
    z = dx * FWD[0] + dy * FWD[1]
    return 0.5 + 0.5 * ((dx * RGT[0] + dy * RGT[1]) / z) / KTAN


def axis_dist(x, y):
    return (x - LX) * FWD[0] + (y - LY) * FWD[1]


def span(sp, x, y, h):
    """Crown frame-x span: the trunk +- the crown radius (env_lib.CROWN_R x height) across the view axis."""
    rad = L.CROWN_R.get(sp, 0.35) * h
    z = max(1e-3, axis_dist(x, y))
    half = 0.5 * (rad / z) / KTAN
    c = frame_x(x, y)
    return c - half, c + half


def main():
    print(f"[env_r9_replan] cam 01 {SPEC['loc']} lens {SPEC['lens']} mm; gallery keep-out {L.GALLERY_KEEPOUT} m")
    print("  group species     (   X,     Y)   h   frame x span     centre   d_axis  gallery_off")
    for (sp, x, y, h, note) in env_trees.PLAN:
        g = L.gallery_offset(x, y)
        gs = "   -  " if g is None else f"{g:6.2f}"
        flag = "  <-- INSIDE THE GALLERY" if (g is not None and g < L.GALLERY_KEEPOUT) else ""
        a, b = span(sp, x, y, h)
        print(f"  {str(note).split(' ')[0]:5s} {sp:12s} ({x:6.1f},{y:6.1f}) {h:4.0f}   "
              f"{a:.3f}-{b:.3f}    {frame_x(x, y):.3f}   {axis_dist(x, y):6.1f}   {gs}{flag}")
    if "--podium" in ARGS:
        # QA-02-13 (env_trees.shadow_relief): no crown within 6 m of the 31 m podium.  Round 9 stops that pass
        # relocating hand-placed trees, so the correction has to live in PLAN.  These are the coordinates the
        # radial push produced, computed with the PLAN height (the tallest the tree can be, so the clearance
        # holds however far the relief later lowers it).
        PODIUM_R, CLEAR = 31.0, 6.0
        print(f"\n[env_r9_replan] QA-02-13 podium ring {PODIUM_R + CLEAR:.0f} m, PLAN heights")
        for (sp, x, y, h, note) in env_trees.PLAN:
            d = math.hypot(x, y)
            rad = L.CROWN_R.get(sp, 0.35) * h
            if d - rad >= PODIUM_R + CLEAR or d < 1e-3:
                continue
            k = (PODIUM_R + CLEAR + rad) / d
            nx, ny = x * k, y * k
            print(f"    {sp:14s} ({x:6.1f},{y:6.1f}) h{h:4.0f} crown {rad:4.1f} reaches r {d - rad:5.1f}"
                  f"  ->  ({nx:6.2f},{ny:6.2f})  frame x {frame_x(x, y):.3f} -> {frame_x(nx, ny):.3f}"
                  f"   [{str(note)[:34]}]")
    if "--solve" in ARGS:
        i = ARGS.index("--solve")
        targets = []
        for v in ARGS[i + 1:]:
            try:
                targets.append(float(v))
            except ValueError:
                break
        print(f"\n[env_r9_replan] solving for frame x {targets} at {ROFF:+.1f} m outside the arc")
        for t in targets:
            X, Y = FIT.solve(t, ROFF)
            g = L.gallery_offset(X, Y)
            print(f"    -> ({X:7.2f}, {Y:7.2f})  frame x {frame_x(X, Y):.3f}  d_axis {axis_dist(X, Y):6.1f}  "
                  f"gallery_off {('-' if g is None else f'{g:.2f}')}")


main()
