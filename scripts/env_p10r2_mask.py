"""Phase 10 ENV round 2, item 1 + 3: the hero-shore willow's OWN pixels in cam 01, colour-independent.

    scripts/blender_run.sh 900 -- --background --python scripts/env_p10r2_mask.py -- --tag before [--samples 8]

Method (no colour threshold anywhere):
  * Cycles, cam 01, 1920x1080, LOD0 render geometry (the hero's), transparent film.  The target tree's LOD0 object
    is moved into a scratch collection `P10R2_target`; every other layer collection and every other object is a
    holdout.  The alpha channel is then exactly "the target's own pixels, occluded by everything in front of it"
    (leaf-card alpha cut-outs included, since the tree keeps its own materials).  Two targets, one render each:
      target = the hero-shore willow of the brief (PLAN note "P hero-shore willow, ref 169 x 0.33-...")
      other  = the second hero-shore willow ("P hero-shore willow, ref 169 x 0.44-0.52"), reported, not moved.
  * Silhouette rule (brief item 3): for every mask pixel (alpha > 0.5) a camera ray is classified against the
    rotunda's geometry from arch_params: the ray's entry into the octagonal wall prism (apothem WALL_APOTHEM);
    "arch opening" = entry point inside an outer arch aperture (|along-face| < ARCH_SPAN/2, PODIUM_TOP_Z < z <
    the arch curve) AND the first ARCH_rotunda* hit (viewport LOD, the tree removed) lies more than WALL_THICKNESS +
    0.5 m behind the face plane, or there is none - i.e. the pixel shows the interior or the far side THROUGH the
    arch.  A rotunda surface in front of the plane (column, pedestal) or inside the wall thickness (parapet, reveal)
    is solid stone, allowed like the left column in ref 169.  "drum" = entry z >= DRUM_Z0.  Both counts must be 0.
    Debug PNG per mask: blue = column in front, green = in-plane stone, red = opening, magenta = drum.

Writes renders/previews/environment/p10r2_<tag>_mask_{target,other}.png (8-bit grey = alpha) and
renders/previews/environment/p10r2_<tag>_mask.json (placed transforms, silhouette counts).
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras
import arch_params as A

args = common.script_args()


def arg(name, default=None):
    if name not in args:
        return default
    i = args.index(name) + 1
    return args[i] if i < len(args) and not args[i].startswith("--") else default


TAG = arg("--tag", "before")
SPP = int(arg("--samples", "8"))
BLEND = arg("--blend", str(common.ROOT / "master.blend"))
OUT = common.RENDERS / "previews" / "environment"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1920, 1080
TARGETS = {"target": "P hero-shore willow, ref 169 x 0.33", "other": "P hero-shore willow, ref 169 x 0.44"}

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)
scene = bpy.context.scene
qa_cameras.ensure(scene)
common.set_lod(viewport=1, render=0)
scene.render.engine = "CYCLES"
scene.cycles.samples = SPP
scene.cycles.use_adaptive_sampling = False
scene.cycles.use_denoising = False
try:
    scene.cycles.device = "GPU"
except Exception:
    pass
scene.render.film_transparent = True
scene.render.use_persistent_data = True
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.render.use_border = False
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
cam = next(o for o in bpy.data.objects if o.name.startswith("CAM_qa_01_"))
scene.camera = cam


def find(prefix, lod):
    hits = [o for o in bpy.data.objects if o.name.startswith("ENV_tree_willow_") and o.name.endswith(f"_LOD{lod}")
            and str(o.get("note", "")).startswith(prefix)]
    assert len(hits) == 1, (prefix, [o.name for o in hits])
    return hits[0]


objs = {k: find(p, 0) for k, p in TARGETS.items()}
info = {}
for k, o in objs.items():
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    info[k] = dict(name=o.name, note=o.get("note"), height_m=o.get("height_m"), location=list(o.location),
                   scale=list(o.scale), bbox_z=[min(v.z for v in bb), max(v.z for v in bb)])
    print(f"[p10r2_mask] {k}: {o.name} loc {tuple(round(v, 2) for v in o.location)} scale "
          f"{tuple(round(v, 3) for v in o.scale)} bbox z {info[k]['bbox_z'][0]:.2f}-{info[k]['bbox_z'][1]:.2f}")

tgt_coll = bpy.data.collections.new("P10R2_target")
scene.collection.children.link(tgt_coll)
vl = scene.view_layers[0]


def layer_coll(lc, name):
    if lc.name == name:
        return lc
    for c in lc.children:
        r = layer_coll(c, name)
        if r:
            return r
    return None


def isolate(o):
    """Only `o` renders non-holdout: move it into P10R2_target, hold out every other collection and object."""
    for c in list(o.users_collection):
        c.objects.unlink(o)
    tgt_coll.objects.link(o)
    o.hide_render = False
    for lc in vl.layer_collection.children:
        lc.holdout = lc.name != "P10R2_target"
    for ob in scene.objects:
        ob.is_holdout = ob is not o


def render_alpha(key):
    fp = OUT / f"p10r2_{TAG}_mask_{key}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(fp), check_existing=False)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1]      # row 0 = top
    bpy.data.images.remove(img)
    print(f"[p10r2_mask] {key}: {fp.name} in {time.time() - t:.1f}s, alpha>0.5 px {(px[..., 3] > 0.5).sum()}")
    return px[..., 3]


alphas = {}
for key in ("target", "other"):
    isolate(objs[key])
    alphas[key] = render_alpha(key)
    tgt_coll.objects.unlink(objs[key])

# ---------------------------------------------------------------- item 3: rotunda arch opening / drum under a mask
cm = cam.matrix_world
tr, br, bl, tl = [cm @ v for v in cam.data.view_frame(scene=scene)]          # world corners
O = np.array(cm.translation)
dg = bpy.context.evaluated_depsgraph_get()
rot = [o for o in scene.objects if o.type == "MESH" and o.name.startswith("ARCH_rotunda") and o.visible_get()]
DEEP = A.WALL_THICKNESS + 0.5      # a first hit deeper than this behind the face plane = seen THROUGH the arch


def first_rotunda_hit(d):
    best = math.inf
    for o in rot:
        mi = o.matrix_world.inverted()
        ok, loc, _n, _f = o.ray_cast(mi @ Vector(O), (mi.to_3x3() @ Vector(d)).normalized(), depsgraph=dg)
        if ok:
            best = min(best, ((o.matrix_world @ loc) - Vector(O)).length)
    return best


def classify(alpha, key):
    """Pixels of `alpha` (> 0.5) whose ray, with the tree removed, would show the arch opening or the drum."""
    ys, xs = np.nonzero(alpha > 0.5)
    u, v = (xs + 0.5) / W, (ys + 0.5) / H
    P = np.array(tl)[None, :] + u[:, None] * np.array(tr - tl)[None, :] + v[:, None] * np.array(bl - tl)[None, :]
    D = P - O[None, :]
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    # entry into the octagonal wall prism; compass az -> world (north = -X, east = +Y): n = (-cos az, sin az)
    t_in = np.full(len(D), -np.inf)
    t_out = np.full(len(D), np.inf)
    face = np.zeros(len(D), dtype=int)
    for k in range(8):
        az = math.radians(A.FACE_AZ0 + 45 * k)
        n = np.array([-math.cos(az), math.sin(az)])
        dn = D[:, :2] @ n
        with np.errstate(divide="ignore", invalid="ignore"):
            t = -(O[:2] @ n - A.WALL_APOTHEM) / dn
        ent = dn < 0
        better = ent & (t > t_in)
        t_in = np.where(better, t, t_in)
        face = np.where(better, k, face)
        t_out = np.where(~ent & (t < t_out), t, t_out)
    enters = t_in < t_out
    E = O[None, :] + t_in[:, None] * D
    along = np.zeros(len(D))
    for k in range(8):
        az = math.radians(A.FACE_AZ0 + 45 * k)
        m = face == k
        along[m] = E[m, :2] @ np.array([math.sin(az), math.cos(az)])
    half = A.ARCH_SPAN / 2
    arch_top = A.ARCH_SPRING_Z + np.sqrt(np.clip(half ** 2 - along ** 2, 0, None))
    aperture = enters & (np.abs(along) < half) & (E[:, 2] > A.PODIUM_TOP_Z) & (E[:, 2] < arch_top)
    drum = enters & (E[:, 2] >= A.DRUM_Z0)
    behind = np.full(len(D), np.nan)
    for i in np.nonzero(aperture | drum)[0]:
        behind[i] = first_rotunda_hit(D[i]) - t_in[i]          # inf = nothing of the rotunda behind (sky, hall)
    front = aperture & (behind < -0.05)                         # a column / pedestal in front of the aperture
    in_plane = aperture & (behind >= -0.05) & (behind <= DEEP)   # parapet / reveal stone inside the wall thickness
    opening = aperture & ~(behind <= DEEP)                       # seen through: interior beyond the wall, or beyond
    dbg = np.zeros((H, W, 4), dtype=np.float32)
    for m, c in ((front, (0, 0, 1)), (in_plane, (0, 1, 0)), (opening, (1, 0, 0)), (drum, (1, 0, 1))):
        dbg[ys[m], xs[m]] = (*c, 1)
    img = bpy.data.images.new(f"dbg_{key}", W, H, alpha=True)
    img.pixels = dbg[::-1].ravel()
    img.filepath_raw = str(OUT / f"p10r2_{TAG}_silhouette_{key}.png")
    img.file_format = "PNG"
    img.save()
    return dict(own_px=int(len(D)), rotunda_prism_px=int(enters.sum()), aperture_px=int(aperture.sum()),
                column_in_front_px=int(front.sum()), in_wall_plane_px=int(in_plane.sum()),
                arch_opening_px=int(opening.sum()), drum_px=int(drum.sum()),
                opening_rows=[int(ys[opening].min()), int(ys[opening].max())] if opening.any() else None,
                opening_cols=[int(xs[opening].min()), int(xs[opening].max())] if opening.any() else None)


sil = {k: classify(a, k) for k, a in alphas.items()}
res = dict(tag=TAG, samples=SPP, targets=info, silhouette=sil)
(OUT / f"p10r2_{TAG}_mask.json").write_text(json.dumps(res, indent=1))
for k, v in sil.items():
    print(f"[p10r2_mask] silhouette {k}: {v}")
print(f"[p10r2_mask] done in {time.time() - t0:.1f}s")
