"""ROUND 16 (flythrough plan finding 2): what the ORN link put in the flythrough's way.

The round-14 clearance table linked ARCH + ENV only. With ORN linked as well (light_flythrough_check.link_site,
round 16) the approach leg fails at thirteen sampled frames, so this script names the objects and where they are:
for every ORN / ENV object whose evaluated world bounding box comes within `--r` metres of the camera path's last
leg it prints the box, so the lead can tell a route problem (move a station) from a placement problem (an asset
parked at the origin) without a render.

    scripts/blender_run.sh 900 -- --background --python scripts/light_r16_ornprobe.py -- --r 6
"""
import bpy, os, sys, math
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_flythrough_check as fc

args = common.script_args()
R = float(args[args.index("--r") + 1]) if "--r" in args else 6.0

bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["LIGHT"]), load_ui=False)
dg = fc.link_site()
cam = bpy.data.objects.get("CAM_flythrough")
scene = bpy.context.scene
sch = None
if cam is not None and cam.get("schedule"):
    import json
    sch = json.loads(cam["schedule"])

# the frames the step-4 check failed on, plus their neighbourhood
FRAMES = list(range(925, 950, 3)) + list(range(1070, 1126, 4))
pts = []
for f in FRAMES:
    scene.frame_set(f)
    bpy.context.view_layer.update()
    pts.append((f, cam.matrix_world.translation.copy()))
    print(f"[ornprobe] f{f:5d} cam ({pts[-1][1].x:.2f}, {pts[-1][1].y:.2f}, {pts[-1][1].z:.2f})")

seen = {}
for o in bpy.context.view_layer.objects:
    if o.type != "MESH" or not (o.name.startswith("ORN") or o.name.startswith("ENV")):
        continue
    if o.hide_render or not o.visible_get():
        continue
    try:
        bb = [o.matrix_world @ __import__("mathutils").Vector(c) for c in o.bound_box]
    except Exception:
        continue
    lo = [min(v[i] for v in bb) for i in range(3)]
    hi = [max(v[i] for v in bb) for i in range(3)]
    for f, p in pts:
        d = math.sqrt(sum(max(lo[i] - p[i], 0.0, p[i] - hi[i]) ** 2 for i in range(3)))
        if d <= R and (o.name not in seen or d < seen[o.name][0]):
            seen[o.name] = (d, f, lo, hi)
for name, (d, f, lo, hi) in sorted(seen.items(), key=lambda kv: kv[1][0]):
    print(f"[ornprobe] {d:6.2f} m at f{f:5d}  {name:44s} bbox "
          f"({lo[0]:7.2f},{lo[1]:7.2f},{lo[2]:6.2f}) .. ({hi[0]:7.2f},{hi[1]:7.2f},{hi[2]:6.2f})")
print(f"[ornprobe] {len(seen)} objects within {R:g} m of the sampled stations")
