"""Gate 3 worker: one queue job per run. Opened by export/bake_queue.sh --gate3 on the job's own blend.

    scripts/blender_run.sh 1800 -- --background <blend> --python-exit-code 1 \
        --python export/bake_lm.py -- --job <id>

Job kinds: own / own_gate1uv2 (a 2K or 4K UV2 lightmap), slot (a batch of 248 px per-instance slots),
vertex (VERTEX_COLORS irradiance on the near trees), impostor (144 octahedral views of one tree prototype),
probe (the hero cube), sky (the diffuse-branch equirect, QA-12b-1).

Every map leaves this script through numpy (export/gate3_common) and is read back from the file before any
number is recorded: `Image.save()` on a generated float image writes zeros (docs/tech_notes.md "Phase 6").
"""
import bpy
import os
import sys
import json
import math
import time

import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0      # noqa: E402
import gate3_common as g3      # noqa: E402
import bake_lib as bl          # noqa: E402

argv = g0.script_argv()
JOB_ID = argv[argv.index("--job") + 1]
SPP_OVERRIDE = int(os.environ.get("PFA_LM_SPP", "0"))
jobs = {j["id"]: j for j in g3.read_jobs()["jobs"]}
job = jobs[JOB_ID]
g3.ensure_dirs()
scene = bpy.context.scene
t_job = time.time()
rec = dict(id=JOB_ID, kind=job["kind"], started=time.strftime("%Y-%m-%dT%H:%M:%S"))


def prepare(samples):
    """The final Cycles rig, asserted, with the bake/render overrides this gate needs."""
    if SPP_OVERRIDE:
        samples = SPP_OVERRIDE
    lights = g0.apply_final_cycles_checked(scene)
    c = scene.cycles
    c.use_adaptive_sampling = False
    c.time_limit = 0.0
    c.samples = samples
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    scene.compositing_node_group = None
    hidden_hi = [o.name for o in bpy.data.objects if o.name.startswith("EXPHI") and not o.hide_render]
    assert not hidden_hi, f"hi-poly twins ray-visible: {hidden_hi}"
    rec["rig"] = dict(lights=len(lights), samples=c.samples, adaptive=c.use_adaptive_sampling,
                      denoiser=c.denoiser, compositor=scene.compositing_node_group)
    return lights


def encode_and_write(key, rgb, out_dir=None, exr=True):
    """rgb: (h, w, 3) float32 BOTTOM-UP scene-linear irradiance/pi. Writes the EXR + both 8-bit encodings,
    reads every file back from disk and returns the record."""
    out_dir = out_dir or g3.TEX
    rng = g3.pick_range(rgb)
    d = dict(range=rng, size=[int(rgb.shape[1]), int(rgb.shape[0])], stats=g3.px_stats(rgb, ceiling=rng))
    if exr:
        p = out_dir / f"{key}.exr"
        g3.write_exr32(p, rgb)
        back = g3.read_exr32(p)
        assert back.shape == rgb.shape, f"{p}: shape {back.shape} != {rgb.shape}"
        d["exr"] = dict(path=p.name, bytes=p.stat().st_size,
                        read_back_abs_max=round(float(np.abs(back - rgb).max()), 8))
    for enc, fn, dec in (("rgbm8", g3.rgbm_encode, g3.rgbm_decode_u8),
                         ("gamma2", g3.gamma2_encode, g3.gamma2_decode_u8)):
        a = fn(rgb, rng)
        p = out_dir / f"{key}_{enc}.png"
        nb = (g3.write_png_rgba8 if a.shape[-1] == 4 else g3.write_png_rgb8)(p, a)
        rb = g3.read_png(p)
        assert rb.shape == a.shape and np.array_equal(rb, a), f"{p}: did not read back identical"
        d[enc] = dict(path=p.name, bytes=nb, roundtrip=g3.roundtrip(rgb, dec(rb, rng)))
    return d


# ================================================================ own / own_gate1uv2
if job["kind"] in ("own", "own_gate1uv2"):
    prepare(g3.SAMPLES_LM)
    ob = bpy.data.objects[job["object"]]
    ob.hide_render = ob.hide_viewport = ob.hide_select = False
    size, uvname = int(job["size"]), job["uv2"]
    assert ob.data.uv_layers.get(uvname) is not None, f"{ob.name} has no UV layer {uvname}"
    img = bl.bake_image(f"{JOB_ID}_{size}", size=size, colorspace="Non-Color", float_buffer=True,
                        fill=(0.0, 0.0, 0.0, 1.0))
    bl.attach_target(ob, img, uvname)
    bl.select_only(ob)
    dt = bl.run_bake("DIFFUSE", samples=SPP_OVERRIDE or g3.SAMPLES_LM, margin=g3.MARGIN_OWN,
                     use_pass_direct=True, use_pass_indirect=True, use_pass_color=False, denoise=True)
    bl.detach_targets()
    rgb = bl.image_array(img)[:, :, :3].copy()
    key = ("gate3_lm_" if job["kind"] == "own" else "gate3_lmg1_") + job["object"]
    rec.update(object=job["object"], mesh=job["mesh"], size=size, uv=uvname, bake_s=round(dt, 1),
               map=encode_and_write(key, rgb), key=key)
    print(f"[gate3] {JOB_ID}: {dt:.1f}s max={rec['map']['stats']['max']:.3f} "
          f"mean={rec['map']['stats']['mean']:.3f} range={rec['map']['range']}")

# ================================================================ slot batch
elif job["kind"] == "slot":
    prepare(g3.SAMPLES_LM)
    arrays, rows = {}, []
    for it in job["items"]:
        ob = bpy.data.objects[it["object"]]
        ob.hide_render = ob.hide_viewport = ob.hide_select = False
        assert ob.data.uv_layers.get(g3.UV2) is not None, f"{ob.name} has no {g3.UV2}"
        img = bl.bake_image(f"slot_{it['slot']}", size=g3.USABLE_PX, colorspace="Non-Color",
                            float_buffer=True, fill=(0.0, 0.0, 0.0, 1.0))
        bl.attach_target(ob, img, g3.UV2)
        bl.select_only(ob)
        dt = bl.run_bake("DIFFUSE", samples=SPP_OVERRIDE or g3.SAMPLES_LM, margin=g3.MARGIN_SLOT,
                         use_pass_direct=True, use_pass_indirect=True, use_pass_color=False, denoise=True)
        bl.detach_targets()
        a = bl.image_array(img)[:, :, :3].copy()
        arrays[str(it["slot"])] = a
        rows.append(dict(object=it["object"], slot=it["slot"], bake_s=round(dt, 2),
                         max=round(float(a.max()), 4), mean=round(float(a.mean()), 4)))
        bpy.data.images.remove(img)
    p = g3.OUT / "slots" / f"{JOB_ID}.npz"
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(str(p), **arrays)
    back = np.load(str(p))
    assert sorted(back.files) == sorted(arrays), f"{p}: slot set changed on write"
    rec.update(pool=job["pool"], atlas=job["atlas"], n=len(rows), npz=p.name, npz_bytes=p.stat().st_size,
               slot_px=g3.USABLE_PX, items=rows,
               bake_s=round(sum(r["bake_s"] for r in rows), 1),
               s_per_instance=round(sum(r["bake_s"] for r in rows) / max(len(rows), 1), 2))
    print(f"[gate3] {JOB_ID}: {len(rows)} slots, {rec['bake_s']:.1f}s, {rec['s_per_instance']:.2f} s/instance")

# ================================================================ vertex irradiance
elif job["kind"] == "vertex":
    prepare(g3.SAMPLES_VERTEX)
    scene.render.bake.target = "VERTEX_COLORS"
    arrays, rows = {}, []
    obs_by_mesh = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data is not None:
            obs_by_mesh.setdefault(o.data.name, []).append(o.name)
    for name in job["objects"]:
        ob = bpy.data.objects.get(name)
        if ob is None:
            rows.append(dict(object=name, missing=True))
            continue
        me = ob.data
        if me.name in arrays:
            rows.append(dict(object=name, mesh=me.name, shared_with=arrays[me.name][1], bake_s=0.0))
            continue
        ca = me.color_attributes.get("COLOR_0")
        if ca is None:
            ca = me.color_attributes.new(name="COLOR_0", type="FLOAT_COLOR", domain="POINT")
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = list(me.color_attributes).index(ca)
        bl.select_only(ob)
        t0 = time.time()
        b = scene.render.bake
        b.use_selected_to_active = False
        b.use_clear = True
        b.use_pass_direct = True
        b.use_pass_indirect = True
        b.use_pass_color = False
        scene.cycles.samples = SPP_OVERRIDE or g3.SAMPLES_VERTEX
        scene.cycles.use_adaptive_sampling = False
        bpy.ops.object.bake(type="DIFFUSE")
        dt = time.time() - t0
        n = len(me.vertices)
        buf = np.empty(n * 4, dtype=np.float32)
        ca.data.foreach_get("color", buf)
        v = buf.reshape(n, 4)[:, :3].copy()
        arrays[me.name] = (v, name)
        rows.append(dict(object=name, mesh=me.name, verts=n, bake_s=round(dt, 1),
                         placements=len(obs_by_mesh.get(me.name, [])),
                         max=round(float(v.max()), 4), mean=round(float(v.mean()), 4)))
        print(f"[gate3] {JOB_ID}: {name} {n} verts {dt:.1f}s max={v.max():.3f}")
    scene.render.bake.target = "IMAGE_TEXTURES"
    p = g3.OUT / "vertex" / f"{JOB_ID}.npz"
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(str(p), **{k: v for k, (v, _) in arrays.items()})
    back = np.load(str(p))
    assert sorted(back.files) == sorted(arrays)
    rec.update(npz=p.name, npz_bytes=p.stat().st_size, meshes=len(arrays), items=rows,
               bake_s=round(sum(r.get("bake_s", 0.0) for r in rows), 1))

# ================================================================ impostor
elif job["kind"] == "impostor":
    prepare(g3.SAMPLES_IMPOSTOR)
    scene.render.film_transparent = True
    proto = job["prototype"]
    keep = {proto, "GATE3_imp_lawn"}
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep
            o.hide_viewport = False
    lo = Vector(job["bbox_min"])
    hi = Vector(job["bbox_max"])
    centre = (lo + hi) * 0.5
    radius = max((hi - lo).length * 0.5, 1e-3)
    dist = radius * 6.0
    cam = bpy.data.objects["GATE3_imp_cam"]
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2.0 * radius * (g3.IMP_FRAME_PX / float(g3.IMP_INNER_PX))
    cam.data.clip_start = 0.01
    cam.data.clip_end = dist + 4.0 * radius
    scene.camera = cam
    r = scene.render
    r.resolution_x = r.resolution_y = g3.IMP_FRAME_PX
    r.resolution_percentage = 100
    r.film_transparent = True
    vl = bpy.context.view_layer
    vl.use_pass_normal = True
    vl.use_pass_z = True
    s = r.image_settings
    # Blender 5.2: OPEN_EXR_MULTILAYER is only offered once media_type is MULTI_LAYER_IMAGE.
    s.media_type = "MULTI_LAYER_IMAGE"
    s.use_exr_interleave = True      # single-part, channels interleaved: 5.2 writes MULTI-PART without it
    s.file_format, s.color_depth, s.exr_codec, s.color_mode = "OPEN_EXR_MULTILAYER", "32", "NONE", "RGBA"
    scene.render.use_persistent_data = True
    N = g3.IMP_GRID
    MAXV = int(os.environ.get("PFA_IMP_MAX_VIEWS", "0"))
    IMP_ALPHA_FLOOR = 0.02
    A = g3.IMP_ATLAS_PX
    F = g3.IMP_FRAME_PX
    alb = np.zeros((A, A, 4), dtype=np.float32)       # straight-alpha radiance, bottom-up
    nrm = np.zeros((A, A, 4), dtype=np.float32)
    tmp = g3.OUT / "impostor" / f"{JOB_ID}_view.exr"
    t0 = time.time()
    nrender = 0
    chan_seen = None
    for row in range(N):
        if MAXV and nrender >= MAXV:
            break
        for col in range(N):
            if MAXV and nrender >= MAXV:
                break
            u = col / float(N - 1) * 2.0 - 1.0
            v = row / float(N - 1) * 2.0 - 1.0
            au, av = abs(u), abs(v)
            z = 1.0 - au - av                      # octahedral decode, the inverse of the manifest's encode
            if z >= 0.0:
                d = Vector((u, v, z))
            else:
                d = Vector(((1.0 - av) * (1.0 if u >= 0 else -1.0),
                            (1.0 - au) * (1.0 if v >= 0 else -1.0), z))
            d.normalize()
            up = Vector((0.0, 0.0, 1.0))
            if abs(d.z) > 0.999:
                up = Vector((0.0, 1.0, 0.0))
            zax = d                                   # camera looks along -Z, so +Z points back at the viewer
            xax = up.cross(zax).normalized()
            yax = zax.cross(xax).normalized()
            m = Matrix((
                (xax.x, yax.x, zax.x, centre.x + d.x * dist),
                (xax.y, yax.y, zax.y, centre.y + d.y * dist),
                (xax.z, yax.z, zax.z, centre.z + d.z * dist),
                (0.0, 0.0, 0.0, 1.0)))
            cam.matrix_world = m
            scene.frame_set(scene.frame_current)
            r.filepath = str(tmp)[:-4]
            bpy.ops.render.render(write_still=True)
            nrender += 1
            ch = g3.read_exr_channels(tmp)
            if chan_seen is None:
                chan_seen = sorted(ch)

            def pick(*cands):
                for c in cands:
                    if c in ch:
                        return ch[c]
                for k in ch:
                    if k.endswith(cands[0].split(".")[-1]):
                        return ch[k]
                raise KeyError(f"{cands} not in {sorted(ch)}")

            cr, cg, cb = pick("ViewLayer.Combined.R"), pick("ViewLayer.Combined.G"), pick("ViewLayer.Combined.B")
            ca = pick("ViewLayer.Combined.A")
            nx, ny, nz = pick("ViewLayer.Normal.X"), pick("ViewLayer.Normal.Y"), pick("ViewLayer.Normal.Z")
            zz = pick("ViewLayer.Depth.Z", "ViewLayer.Depth.V")
            a = np.clip(ca, 0.0, 1.0)
            # Un-premultiply with a floor on alpha. With 1e-4 a near-transparent leaf-card edge divides the
            # radiance by 1e-4 and the atlas maximum ran to 4 digits: the prototype range was picked at 512
            # while the opaque crown sits at 0.25-5, so the 8-bit codes came out at a mean of 5/255 (32 %
            # quantisation on the body). 0.02 caps the amplification at 50x.
            inv = np.where(a > IMP_ALPHA_FLOOR, 1.0 / np.maximum(a, IMP_ALPHA_FLOOR), 0.0)
            y0, x0 = row * F, col * F
            alb[y0:y0 + F, x0:x0 + F, 0] = cr * inv
            alb[y0:y0 + F, x0:x0 + F, 1] = cg * inv
            alb[y0:y0 + F, x0:x0 + F, 2] = cb * inv
            alb[y0:y0 + F, x0:x0 + F, 3] = a
            nl = np.stack([nx, ny, nz], axis=-1)
            ln = np.linalg.norm(nl, axis=-1, keepdims=True)
            nl = np.where(ln > 1e-6, nl / np.maximum(ln, 1e-6), 0.0)
            dn = np.clip((np.where(np.isfinite(zz), zz, dist + radius) - (dist - radius)) / (2.0 * radius), 0.0, 1.0)
            nrm[y0:y0 + F, x0:x0 + F, :3] = nl * 0.5 + 0.5
            nrm[y0:y0 + F, x0:x0 + F, 3] = np.where(a > 1e-4, dn, 1.0)
    render_s = time.time() - t0
    if tmp.exists():
        tmp.unlink()

    def reduce2(arr):
        """premultiply -> 2x2 box -> un-premultiply, so the alpha edge does not halo."""
        h, w = arr.shape[0] // 2, arr.shape[1] // 2
        pm = arr.copy()
        pm[..., :3] *= pm[..., 3:4]
        red = pm.reshape(h, 2, w, 2, 4).mean(axis=(1, 3))
        aa = red[..., 3:4]
        red[..., :3] = np.where(aa > 1e-4, red[..., :3] / np.maximum(aa, 1e-4), 0.0)
        return red

    alb1k, nrm1k = reduce2(alb), reduce2(nrm)
    # the range is the OPAQUE crown's own maximum (alpha > 0.5) with 10 % headroom, not the atlas max:
    # the semi-transparent edge is where the outliers live and it must not set the code scale.
    body = alb[..., 3] > 0.5
    # p99.9 of the opaque crown, not its max: ENV_tree_cypress_s17_LOD1 had ONE texel at 233 (a sun glint
    # through a leaf card) and the max rule set its range to 256, which put the whole crown at a code mean
    # of 8/255. The 0.1 % above the range clip; everything else gains 5x of code space.
    rng = (float(max(np.percentile(alb[body][:, :3], 99.9) * 1.1, 1e-3))
           if bool(body.any()) else g3.pick_range(alb[..., :3]))
    clipped_body = int((alb[body][:, :3] > rng).sum())
    out = {}
    for tag, arr, px in (("2048", alb, A), ("1024", alb1k, A // 2)):
        enc = np.concatenate([g3.gamma2_encode(arr[..., :3], rng),
                              np.round(np.clip(arr[..., 3], 0, 1) * 255.0).astype(np.uint8)[..., None]], axis=-1)
        p = g3.OUT / "impostor" / f"gate3_imp_{proto}_albedo_{tag}.png"
        nb = g3.write_png_rgba8(p, enc)
        assert np.array_equal(g3.read_png(p), enc), f"{p}: did not read back identical"
        out[f"albedo_{tag}"] = dict(path=p.name, bytes=nb,
                                    roundtrip=g3.roundtrip(arr[..., :3], g3.gamma2_decode_u8(enc[..., :3], rng)))
    for tag, arr in (("2048", nrm), ("1024", nrm1k)):
        enc = np.round(np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8)
        p = g3.OUT / "impostor" / f"gate3_imp_{proto}_normdepth_{tag}.png"
        nb = g3.write_png_rgba8(p, enc)
        assert np.array_equal(g3.read_png(p), enc), f"{p}: did not read back identical"
        out[f"normdepth_{tag}"] = dict(path=p.name, bytes=nb)
    cov = float((alb[..., 3] > 0.01).mean())
    rec.update(prototype=proto, views=nrender, render_s=round(render_s, 1),
               s_per_view=round(render_s / max(nrender, 1), 3), range=rng,
               radius_m=round(radius, 4), centre=[round(float(v), 4) for v in centre],
               bbox_m=[round(float(hi[i] - lo[i]), 4) for i in range(3)],
               centre_above_base_m=round(float(centre.z - lo.z), 4),
               depth_range_m=round(2.0 * radius, 4), alpha_coverage=round(cov, 4),
               channels=chan_seen, files=out, bake_s=round(render_s, 1))
    print(f"[gate3] {JOB_ID}: {nrender} views {render_s:.1f}s ({render_s/max(nrender,1):.2f} s/view) "
          f"range={rng} alpha_cov={cov:.3f}")

# ================================================================ probe / sky
elif job["kind"] in ("probe", "sky"):
    prepare(g3.SAMPLES_PROBE if job["kind"] == "probe" else 16)
    wt = scene.world.node_tree
    lp = next(n for n in wt.nodes if n.bl_idname == "ShaderNodeLightPath")
    saved = [(l.from_socket.name, l.to_node.name, list(l.to_node.inputs).index(l.to_socket))
             for l in [l for o in lp.outputs for l in o.links]]

    def isolate(const):
        for o in lp.outputs:
            for l in list(o.links):
                wt.links.remove(l)
        for sock, node, idx in saved:
            wt.nodes[node].inputs[idx].default_value = float(const.get(sock, 0.0))

    r = scene.render
    s = r.image_settings
    r.film_transparent = False
    # no colour-management override is needed: Blender never applies the view transform to an OPEN_EXR save,
    # and every .hdr here is written from numpy, not by Blender.
    s.media_type = "IMAGE"
    s.file_format, s.color_depth, s.exr_codec, s.color_mode = "OPEN_EXR", "32", "ZIP", "RGB"

    def render_to_array(path, w, h):
        r.filepath = str(path)[:-4]
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t0
        im = bpy.data.images.load(str(path))
        im.colorspace_settings.name = "Non-Color"
        a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, -1)[:, :, :3].copy()
        bpy.data.images.remove(im)
        return a, dt

    if job["kind"] == "sky":
        isolate({"Is Diffuse Ray": 1.0})
        for o in bpy.data.objects:
            if o.type == "MESH":
                o.hide_render = True
        cd = bpy.data.cameras.new("GATE3_pano")
        pano = bpy.data.objects.new("GATE3_pano", cd)
        scene.collection.objects.link(pano)
        cd.type = "PANO"
        for holder in (cd, getattr(cd, "cycles", None)):
            if holder is not None and hasattr(holder, "panorama_type"):
                try:
                    holder.panorama_type = "EQUIRECTANGULAR"
                except Exception:
                    pass
        ptype = getattr(cd, "panorama_type", None) or getattr(getattr(cd, "cycles", None), "panorama_type", None)
        assert ptype == "EQUIRECTANGULAR", f"panorama type is {ptype!r}"
        pano.location = (0.0, 0.0, 12.0)
        pano.rotation_euler = (math.pi / 2.0, 0.0, 0.0)     # image centre = world +Y, as Gate 0's equirects
        scene.camera = pano
        w, h = g3.SKY_DIFFUSE_W, g3.SKY_DIFFUSE_H
        r.resolution_x, r.resolution_y = w, h
        exr = g3.OUT / f"sky_diffuse_{w}x{h}.exr"
        a, dt = render_to_array(exr, w, h)
        hdr = g3.OUT / f"sky_diffuse_{w}x{h}.hdr"
        nb = g3.write_hdr(hdr, a)
        back = g3.read_hdr(hdr)
        sel = a > 0.01 * float(a.max())
        rel = float(np.percentile(np.abs(back[sel] - a[sel]) / np.maximum(a[sel], 1e-6), 99)) if sel.any() else 0.0
        lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        rec.update(render_s=round(dt, 1), exr=exr.name, exr_bytes=exr.stat().st_size,
                   hdr=hdr.name, hdr_bytes=nb, w=w, h=h, branch="diffuse",
                   hdr_rel_p99=round(rel, 5),
                   upper_mean=round(float(lum[h // 2:].mean()), 5), lower_mean=round(float(lum[:h // 2].mean()), 5),
                   stats=g3.px_stats(a), bake_s=round(dt, 1))
        print(f"[gate3] {JOB_ID}: diffuse equirect {w}x{h} {dt:.1f}s max={a.max():.3f} mean={a.mean():.4f}")
    else:
        isolate({"Is Glossy Ray": 1.0})
        man2 = json.loads((g3.GATE2_OUT / "manifest.json").read_text())
        st = man2["stations"][man2["hero_camera"]]
        wz = float(man2["water"]["water_z"])
        pos = Vector((st["location"][0], st["location"][1], 2.0 * wz - st["location"][2]))
        # A mirror probe is the world seen from the mirrored station with everything BELOW the water plane
        # culled - that geometry is not in a reflection. Measured why this is not optional: with the water
        # surface and the lagoon bed left in, the +Y (up) face came back at mean 0.0003 / max 0.002, i.e.
        # black, because the camera sits 2.6 m under the water it is reflecting.
        culled = []
        for o in bpy.data.objects:
            if o.type != "MESH" or o.hide_render:
                continue
            if o.name in ("ENV_lagoon_water", "ENV_backdrop_bay", "ENV_lagoon_bed"):
                o.hide_render = True
                culled.append(o.name)
                continue
            zs = [(o.matrix_world @ Vector(c)).z for c in o.bound_box]
            if max(zs) <= wz + 1e-4:
                o.hide_render = True
                culled.append(o.name)
        rec["culled_below_water"] = dict(n=len(culled), names=sorted(culled)[:20], water_z=wz)
        print(f"[gate3] probe: {len(culled)} objects culled at or below z={wz}")
        cd = bpy.data.cameras.new("GATE3_probe")
        pc = bpy.data.objects.new("GATE3_probe", cd)
        scene.collection.objects.link(pc)
        cd.type = "PERSP"
        cd.sensor_fit = "AUTO"
        cd.angle = math.pi / 2.0
        cd.clip_start, cd.clip_end = 0.05, 5000.0
        scene.camera = pc
        px = g3.PROBE_RENDER_PX
        r.resolution_x = r.resolution_y = px
        # three.js cube faces: forward / up in THREE coords, converted to Blender with (x, y, z)_three -> (x, -z, y)
        faces_three = dict(px=((1, 0, 0), (0, -1, 0)), nx=((-1, 0, 0), (0, -1, 0)),
                           py=((0, 1, 0), (0, 0, 1)), ny=((0, -1, 0), (0, 0, -1)),
                           pz=((0, 0, 1), (0, -1, 0)), nz=((0, 0, -1), (0, -1, 0)))
        out, tot = {}, 0.0
        for name in g3.PROBE_FACES:
            f3, u3 = faces_three[name]
            fb = Vector((f3[0], -f3[2], f3[1]))
            ub = Vector((u3[0], -u3[2], u3[1]))
            zax = -fb
            xax = ub.cross(zax).normalized()
            yax = zax.cross(xax).normalized()
            pc.matrix_world = Matrix(((xax.x, yax.x, zax.x, pos.x),
                                      (xax.y, yax.y, zax.y, pos.y),
                                      (xax.z, yax.z, zax.z, pos.z),
                                      (0.0, 0.0, 0.0, 1.0)))
            exr = g3.OUT / "probe" / f"gate3_probe_hero_{name}.exr"
            a, dt = render_to_array(exr, px, px)
            tot += dt
            small = a.reshape(g3.PROBE_SHIP_PX, px // g3.PROBE_SHIP_PX,
                              g3.PROBE_SHIP_PX, px // g3.PROBE_SHIP_PX, 3).mean(axis=(1, 3))
            hdr = g3.OUT / "probe" / f"gate3_probe_hero_{name}.hdr"
            nb = g3.write_hdr(hdr, small)
            back = g3.read_hdr(hdr)
            sel = small > 0.01 * float(max(small.max(), 1e-6))
            rel = float(np.percentile(np.abs(back[sel] - small[sel]) / np.maximum(small[sel], 1e-6), 99)) \
                if sel.any() else 0.0
            out[name] = dict(exr=exr.name, exr_bytes=exr.stat().st_size, hdr=hdr.name, hdr_bytes=nb,
                             render_s=round(dt, 1), hdr_rel_p99=round(rel, 5),
                             mean=round(float(a.mean()), 5), max=round(float(a.max()), 4))
            print(f"[gate3] probe {name}: {dt:.1f}s mean={a.mean():.4f} max={a.max():.3f}")
        rec.update(station=man2["hero_camera"], position_blender=[round(float(v), 4) for v in pos],
                   position_gltf=[round(float(pos.x), 4), round(float(pos.z), 4), round(float(-pos.y), 4)],
                   rendered_px=px, ship_px=g3.PROBE_SHIP_PX, samples=g3.SAMPLES_PROBE,
                   faces=out, bake_s=round(tot, 1), world_branch="glossy")
    for sock, node, idx in saved:
        wt.links.new(lp.outputs[sock], wt.nodes[node].inputs[idx])
else:
    raise SystemExit(f"unknown job kind {job['kind']}")

rec["wall_s"] = round(time.time() - t_job, 1)
(g3.REC / f"{JOB_ID}.json").write_text(json.dumps(rec, indent=1) + "\n")
print(f"[gate3] job {JOB_ID} done in {rec['wall_s']} s")
