"""Find which exported mesh covers a pixel box at a QA station (QA-11-9, the cam04 ceiling sliver).

    scripts/blender_run.sh 600 -- --background export/out/gate1/gate1_set.blend \
        --python export/qa_cam04_probe.py -- --cam CAM_qa_04_rotunda_ceiling --box 470 140 600 350 --res 1280 720

CPU only: `scene.ray_cast` over a grid of pixels inside the box, tallying the first hit per pixel by object and
by mesh, with the hit distance. Writes export/out/gate1/qa_cam04_probe.json.
"""
import bpy
import os
import sys
import json
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
from mathutils import Vector  # noqa: E402

argv = g0.script_argv()


def arg(name, n, cast=str, default=None):
    if name not in argv:
        return default
    i = argv.index(name)
    vals = [cast(v) for v in argv[i + 1:i + 1 + n]]
    return vals[0] if n == 1 else vals


cam_name = arg("--cam", 1, str, "CAM_qa_04_rotunda_ceiling")
x0, y0, x1, y1 = arg("--box", 4, int, [470, 140, 600, 350])
res_x, res_y = arg("--res", 2, int, [1280, 720])
step_px = arg("--step", 1, int, 3)

scene = bpy.context.scene
for ob in bpy.data.objects:
    ob.hide_viewport = False
bpy.context.view_layer.update()
cam = bpy.data.objects[cam_name]
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = res_x, res_y
dg = bpy.context.evaluated_depsgraph_get()

# camera frame at 1 m, in world space: view_frame gives the four corners (top-right first) in camera space
frame = [cam.matrix_world @ v for v in cam.data.view_frame(scene=scene)]
origin = cam.matrix_world.translation
tr, br, bl, tl = frame
step = g0.Step("qa_cam04_probe")
hits = collections.Counter()
mesh_of = {}
dist = collections.defaultdict(list)
n = 0
for py in range(y0, y1 + 1, step_px):
    for px in range(x0, x1 + 1, step_px):
        u = (px + 0.5) / res_x
        v = (py + 0.5) / res_y            # pixel rows run top-down, and tl->bl is also top-down
        top = tl.lerp(tr, u)
        bot = bl.lerp(br, u)
        target = top.lerp(bot, v)
        d = (target - origin).normalized()
        ok, loc, nor, idx, ob, mtx = scene.ray_cast(dg, origin, d)
        n += 1
        if not ok:
            hits["<sky>"] += 1
            continue
        hits[ob.name] += 1
        mesh_of[ob.name] = ob.data.name
        dist[ob.name].append((loc - origin).length)

rows = []
for name, c in hits.most_common():
    ds = dist.get(name, [])
    rows.append(dict(object=name, mesh=mesh_of.get(name), pixels=c, pct=round(100.0 * c / max(n, 1), 2),
                     dist_min=round(min(ds), 3) if ds else None, dist_max=round(max(ds), 3) if ds else None))
out = dict(camera=cam_name, box=[x0, y0, x1, y1], res=[res_x, res_y], step_px=step_px, samples=n, hits=rows)
(g1.OUT / "qa_cam04_probe.json").write_text(json.dumps(out, indent=1) + "\n")
step.done(g1.OUT / "qa_cam04_probe.json", samples=n, distinct=len(rows))
for r in rows[:12]:
    print(f"  {r['pixels']:6d} px {r['pct']:5.2f}%  {r['object']:44s} {str(r['mesh']):46s} "
          f"{r['dist_min']}-{r['dist_max']} m")

# --- sliver metric: thin triangles are what a COLLAPSE decimation leaves behind -------------------------
# thinness = longest_edge^2 / (2 * area)  (equilateral = 2.31; a 100:1 needle is ~200)
if "--slivers" in argv:
    import math
    names = argv[argv.index("--slivers") + 1].split(",")
    out2 = {}
    for mn in names:
        me = bpy.data.meshes.get(mn)
        if me is None:
            out2[mn] = "missing"
            continue
        me.calc_loop_triangles()
        worst, counts, tot = 0.0, {50: 0, 100: 0, 200: 0}, 0
        for t in me.loop_triangles:
            a_, b_, c_ = (me.vertices[i].co for i in t.vertices)
            e = max((a_ - b_).length, (b_ - c_).length, (c_ - a_).length)
            ar = t.area
            th = (e * e) / (2.0 * ar) if ar > 1e-12 else 1e9
            worst = max(worst, th)
            tot += 1
            for k in counts:
                if th > k:
                    counts[k] += 1
        out2[mn] = dict(tris=tot, worst_thinness=round(worst, 1),
                        over_50=counts[50], over_100=counts[100], over_200=counts[200],
                        pct_over_50=round(100.0 * counts[50] / max(tot, 1), 3))
        print(f"[slivers] {mn}: {out2[mn]}")
    (g1.OUT / "qa_slivers.json").write_text(json.dumps(out2, indent=1) + "\n")
