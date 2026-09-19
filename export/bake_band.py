"""Phase 8b step 2: the band atlas of ONE far-tree prototype (36 views: 12 azimuths x 3 elevations).

    scripts/blender_run.sh 600 -- --background export/out/gate3/band_imp.blend --python-exit-code 1 \
        --python export/bake_band.py -- --proto ENV_tree_broadleaf_s53_LOD1

Run through export/band_queue.sh, which owns the GPU signal (export/out/bake_queue/status.json).

This is export/bake_lm.py's `impostor` block with the octahedral 12x12 sphere replaced by the band's
12 azimuths x 3 elevations at 341 px frames, and nothing else changed:
  * the same nursery (one prototype + the camera-invisible lawn), the same final Cycles rig, 64 spp + OIDN,
    film_transparent - so the atlas holds lit radiance and the viewer's `unlit` rule still applies;
  * the same ORTHO framing, `ortho_scale = 2*radius*(frame_px/inner_px)`, so the bounding-sphere diameter
    lands on the frame's inner size and the octahedral quad (radius_m, centre_z_m, placement) is unchanged;
  * the same COVERAGE alpha: a = clip(Combined.A, 0, 1). No threshold, no dilate, no erode, no premultiplied
    resize (the band is written at its native 341 px: there is no 2x reduction on this path at all);
  * the same un-premultiply floor (0.02) and the same gamma-2 encode - at the prototype's OWN published
    `range`, so a viewer that reads `range` from either `impostors.prototypes` or `impostors.band` decodes
    the band atlas correctly. The band's own p99.9 range and the clip it would have saved are recorded.

Writes: export/out/gate3/band/band_<proto>_albedo_4096.png and band/rec/<proto>.json.
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0      # noqa: E402
import gate3_common as g3      # noqa: E402
import band_common as bc       # noqa: E402

argv = g0.script_argv()
PROTO = argv[argv.index("--proto") + 1]
SPP = int(os.environ.get("PFA_LM_SPP", "0")) or bc.SAMPLES
t_job = time.time()

info = json.loads((bc.BAND_OUT / "band_set.json").read_text())["prototypes"][PROTO]
scene = bpy.context.scene

# ---------------------------------------------------------------- the rig (bake_lm.prepare, verbatim)
lights = g0.apply_final_cycles_checked(scene)
c = scene.cycles
c.use_adaptive_sampling = False
c.time_limit = 0.0
c.samples = SPP
c.use_denoising = True
c.denoiser = "OPENIMAGEDENOISE"
scene.compositing_node_group = None
hidden_hi = [o.name for o in bpy.data.objects if o.name.startswith("EXPHI") and not o.hide_render]
assert not hidden_hi, f"hi-poly twins ray-visible: {hidden_hi}"
assert not g3.BAKE_DIFFUSE_WORLD, "PFA_BAKE_DIFFUSE_WORLD must be off for the band atlas"
rec = dict(prototype=PROTO, started=time.strftime("%Y-%m-%dT%H:%M:%S"),
           rig=dict(lights=len(lights), samples=c.samples, adaptive=c.use_adaptive_sampling,
                    denoiser=c.denoiser, world=scene.world.name if scene.world else None,
                    compositor=scene.compositing_node_group))

keep = {PROTO, "GATE3_imp_lawn"}
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = o.name not in keep
        o.hide_viewport = False

lo = Vector(info["bbox_min"])
hi = Vector(info["bbox_max"])
centre = (lo + hi) * 0.5
radius = max((hi - lo).length * 0.5, 1e-3)
assert abs(radius - info["radius_m"]) < 1e-3, f"{PROTO}: radius {radius} != set {info['radius_m']}"
dist = radius * 6.0
cam = bpy.data.objects["GATE3_imp_cam"]
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2.0 * radius * (bc.FRAME_PX / float(bc.INNER_PX))
cam.data.clip_start = 0.01
cam.data.clip_end = dist + 4.0 * radius
scene.camera = cam
r = scene.render
r.resolution_x = r.resolution_y = bc.FRAME_PX
r.resolution_percentage = 100
r.film_transparent = True
vl = bpy.context.view_layer
vl.use_pass_normal = False          # the contract omits normdepth: the viewer has no 2K normdepth path
vl.use_pass_z = False
s = r.image_settings
s.media_type = "MULTI_LAYER_IMAGE"
s.use_exr_interleave = True
s.file_format, s.color_depth, s.exr_codec, s.color_mode = "OPEN_EXR_MULTILAYER", "32", "NONE", "RGBA"
r.use_persistent_data = True

alb = np.zeros((bc.ATLAS_H, bc.ATLAS_W, 4), dtype=np.float32)      # straight-alpha radiance, BOTTOM-UP
tmp = bc.BAND_OUT / f"{PROTO}_view.exr"
tmp.parent.mkdir(parents=True, exist_ok=True)
t0 = time.time()
views = []
chan_seen = None
for j in range(bc.GRID_EL):
    for i in range(bc.GRID_AZ):
        d = Vector(bc.direction(i, j)).normalized()
        up = Vector((0.0, 0.0, 1.0))
        zax = d                                   # the camera looks along -Z, so +Z points back at it
        xax = up.cross(zax).normalized()
        yax = zax.cross(xax).normalized()
        cam.matrix_world = Matrix((
            (xax.x, yax.x, zax.x, centre.x + d.x * dist),
            (xax.y, yax.y, zax.y, centre.y + d.y * dist),
            (xax.z, yax.z, zax.z, centre.z + d.z * dist),
            (0.0, 0.0, 0.0, 1.0)))
        scene.frame_set(scene.frame_current)
        r.filepath = str(tmp)[:-4]
        tv = time.time()
        bpy.ops.render.render(write_still=True)
        ch = g3.read_exr_channels(tmp)
        if chan_seen is None:
            chan_seen = sorted(ch)

        def pick(*cands):
            for cnd in cands:
                if cnd in ch:
                    return ch[cnd]
            for k in ch:
                if k.endswith(cands[0].split(".")[-1]):
                    return ch[k]
            raise KeyError(f"{cands} not in {sorted(ch)}")

        cr, cg, cb = pick("ViewLayer.Combined.R"), pick("ViewLayer.Combined.G"), pick("ViewLayer.Combined.B")
        a = np.clip(pick("ViewLayer.Combined.A"), 0.0, 1.0)        # COVERAGE: no threshold, no dilate
        inv = np.where(a > bc.ALPHA_FLOOR, 1.0 / np.maximum(a, bc.ALPHA_FLOOR), 0.0)
        y0, y1, x0, x1 = bc.frame_slice(i, j)
        alb[y0:y1, x0:x1, 0] = cr * inv
        alb[y0:y1, x0:x1, 1] = cg * inv
        alb[y0:y1, x0:x1, 2] = cb * inv
        alb[y0:y1, x0:x1, 3] = a
        views.append(dict(az=i, el=j, az_deg=round(i * bc.AZ_STEP_DEG, 1), el_deg=bc.ELEV_DEG[j],
                          dir=[round(float(v), 5) for v in d],
                          octa=list(bc.octa_cell(tuple(d))),
                          cov=round(float((a > 0.01).mean()), 4), s=round(time.time() - tv, 2)))
render_s = time.time() - t0
if tmp.exists():
    tmp.unlink()

# ---------------------------------------------------------------- encode (bake_lm.py `impostor`, verbatim)
rng_octa = float(bc.manifest_impostors()["prototypes"][PROTO]["range"])
body = alb[..., 3] > 0.5
rng_band = (float(max(np.percentile(alb[body][:, :3], 99.9) * 1.1, 1e-3))
            if bool(body.any()) else g3.pick_range(alb[..., :3]))
rng = rng_octa                      # ship at the published range: one constant decodes both atlases
enc = np.concatenate([g3.gamma2_encode(alb[..., :3], rng),
                      np.round(np.clip(alb[..., 3], 0, 1) * 255.0).astype(np.uint8)[..., None]], axis=-1)
p = bc.BAND_OUT / bc.png_name(PROTO)
nb = g3.write_png_rgba8(p, enc)
back = g3.read_png(p)
assert np.array_equal(back, enc), f"{p}: did not read back identical"
dec = g3.gamma2_decode_u8(enc[..., :3], rng)

rec.update(
    views=len(views), render_s=round(render_s, 1), s_per_view=round(render_s / max(len(views), 1), 3),
    layout=dict(grid_az=bc.GRID_AZ, grid_el=bc.GRID_EL, atlas_px=[bc.ATLAS_W, bc.ATLAS_H],
                frame_px=bc.FRAME_PX, gutter_px=bc.GUTTER_PX, inner_px=bc.INNER_PX,
                pad_px=[bc.PAD_X, bc.PAD_Y], elevations_deg=list(bc.ELEV_DEG),
                azimuth0_blender_dir=list(bc.AZIMUTH0_BLENDER_DIR)),
    range=rng, range_octahedral=rng_octa, range_band_p999=round(rng_band, 6),
    range_same_as_octahedral=True,
    clipped_body_texels=int((alb[body][:, :3] > rng).sum()) if bool(body.any()) else 0,
    body_texels=int(body.sum()),
    radius_m=round(float(radius), 4), centre=[round(float(v), 4) for v in centre],
    base_z_m=round(float(lo.z), 4), centre_z_m=round(float(centre.z), 4),
    height_above_base_m=round(float(hi.z - max(lo.z, 0.0)), 4),
    depth_range_m=round(2.0 * radius, 4),
    bbox_m=[round(float(hi[i] - lo[i]), 4) for i in range(3)],
    alpha_coverage=round(float((alb[..., 3] > 0.01).mean()), 4),
    alpha_max=round(float(alb[..., 3].max()), 4),
    png=p.name, png_bytes=nb, channels=chan_seen,
    roundtrip_albedo=g3.roundtrip(alb[..., :3], dec),
    per_view=views, bake_s=round(render_s, 1), wall_s=round(time.time() - t_job, 1))
bc.REC_DIR.mkdir(parents=True, exist_ok=True)
(bc.REC_DIR / f"{PROTO}.json").write_text(json.dumps(rec, indent=1) + "\n")
print(f"[band] {PROTO}: {len(views)} views {render_s:.1f}s ({render_s/max(len(views),1):.2f} s/view) "
      f"range={rng:.4f} (band p99.9 {rng_band:.4f}) cov={rec['alpha_coverage']:.3f} {nb} B")
