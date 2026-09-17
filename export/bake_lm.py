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
    world_before = scene.world.name if scene.world else None
    diffuse_world = False
    if g3.BAKE_DIFFUSE_WORLD and job["kind"] in g3.BAKE_DIFFUSE_WORLD_KINDS:
        # QA-12b-1, see gate3_common.BAKE_DIFFUSE_WORLD. The same sky built split_rays=False, exactly as
        # light_probes.bake does for Eevee's probe capture; its parameters come from the live world's own
        # custom properties, so this bakes whatever rig the blend carries.
        import light_probes as lprobe
        bw = lprobe.bake_world(scene)
        assert bw is not None, ("PFA_BAKE_DIFFUSE_WORLD is set but light_probes.bake_world() returned None "
                                f"for world {world_before!r} - it carries no sun_azimuth_deg/sun_elevation_deg")
        scene.world = bw
        diffuse_world = True
        print(f"[gate3] {JOB_ID}: world {world_before!r} -> {bw.name!r} (diffuse branch on every ray)")
    rec["rig"] = dict(lights=len(lights), samples=c.samples, adaptive=c.use_adaptive_sampling,
                      denoiser=c.denoiser, compositor=scene.compositing_node_group,
                      world=scene.world.name if scene.world else None, world_before=world_before,
                      diffuse_world=diffuse_world)
    return lights


def cutout_override(mats, mode):
    """Gate 4 review fix 3. Wrap each material so the BAKED surface has a diffuse BSDF everywhere while the
    scene's shadowing stays exactly what the cut-out casts:

        mode "shadow": Light Path > Is Shadow Ray picks the ORIGINAL chain for shadow rays and an opaque grey
                       Principled for every other ray. `visible_shadow` stays ON, so a card casts its real
                       leaf-shaped shadow on itself, on its neighbours and on the ground.
        mode "camray":  the same with Is Camera Ray (a bake's primary hit is a camera ray), which would also
                       leave the cut-out in place for the diffuse bounces between cards. MEASURED ONLY.

    Materials are shared datablocks, so wrapping them covers EVERY placement in the scene at once: the result
    cannot depend on how the placements were split across queue jobs. Returns the undo list; nothing is saved.
    """
    flag = {"shadow": "Is Shadow Ray", "camray": "Is Camera Ray"}[mode]
    undo = []
    for mat in mats:
        nt = mat.node_tree
        if nt is None:
            continue
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
        if out is None or not out.inputs["Surface"].links:
            continue
        src = out.inputs["Surface"].links[0].from_socket
        lp = nt.nodes.new("ShaderNodeLightPath")
        grey = nt.nodes.new("ShaderNodeBsdfPrincipled")
        grey.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
        grey.inputs["Roughness"].default_value = 1.0
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs[flag], mix.inputs[0])
        a, b = (grey.outputs["BSDF"], src) if mode == "shadow" else (src, grey.outputs["BSDF"])
        nt.links.new(a, mix.inputs[1])          # Fac = 0
        nt.links.new(b, mix.inputs[2])          # Fac = 1
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        undo.append((nt, out, src, [lp, grey, mix]))
    return undo


def cutout_restore(undo):
    for nt, out, src, nodes in undo:
        nt.links.new(src, out.inputs["Surface"])
        for n in nodes:
            nt.nodes.remove(n)


def materials_of(names):
    """The distinct materials used by these objects, and how many objects in the blend share them."""
    mats, seen = [], set()
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None or ob.type != "MESH":
            continue
        for s in ob.material_slots:
            if s.material is not None and s.material.name not in seen:
                seen.add(s.material.name)
                mats.append(s.material)
    users = sum(1 for o in bpy.data.objects
                if o.type == "MESH" and any(s.material is not None and s.material.name in seen
                                            for s in o.material_slots))
    return mats, users


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
    if job.get("flip_normals_for_bake") or job["object"] in g3.FLIP_NORMALS_FOR_BAKE:
        # QA-13-2, see gate3_common.FLIP_NORMALS_FOR_BAKE for the measurement. Bake-process only:
        # this blend is never saved, so the exported geometry, UV1 and UV2 are untouched.
        me_ = ob.data

        def _face_uv_sets(m):
            lay_ = m.uv_layers[uvname]
            b = np.empty(len(m.loops) * 2, dtype=np.float32)
            try:
                lay_.uv.foreach_get("vector", b)
            except Exception:
                lay_.data.foreach_get("uv", b)
            b = b.reshape(-1, 2)
            return [tuple(sorted(tuple(map(float, b[li])) for li in pl.loop_indices))
                    for pl in m.polygons]

        def _nz(m):
            return float(np.mean([pl.normal.z for pl in m.polygons]))

        uv_before, nz_before = _face_uv_sets(me_), _nz(me_)
        bl.select_only(ob)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode="OBJECT")
        uv_after, nz_after = _face_uv_sets(me_), _nz(me_)
        assert uv_after == uv_before, \
            f"{ob.name}: flip_normals moved the {uvname} layout - the map would not land on the glb"
        assert nz_after < 0.0 < nz_before or nz_before < 0.0 < nz_after, \
            f"{ob.name}: flip_normals did not reverse the facing (mean n.z {nz_before} -> {nz_after})"
        rec["flip_normals_for_bake"] = dict(polys=len(me_.polygons), mean_normal_z_before=round(nz_before, 4),
                                            mean_normal_z_after=round(nz_after, 4), uv_layout_identical=True)
        print(f"[gate3] {JOB_ID}: normals flipped for the bake, mean n.z {nz_before:.3f} -> {nz_after:.3f}, "
              f"{uvname} layout identical on all {len(me_.polygons)} faces")
    if os.environ.get("PFA_LM_DRYRUN"):
        # CPU-only validation of everything that happens before the first ray: no bake image, no GPU,
        # no record written. Used to prove the QA-13-2 flip path while another agent holds the GPU.
        print(f"[gate3] {JOB_ID}: DRY RUN ok (no bake) {json.dumps(rec.get('flip_normals_for_bake', {}))}")
        raise SystemExit(0)
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
    # Gate 4 review finding 6: the same cut-out zeros are in the 14 near trees' COLOR_0 (77-99 % exact
    # zeros -> black vertex patches). With `override` set, the leaf materials take the same shadow-ray wrap
    # as the cards, over the union of EVERY vertex job's objects so the two jobs see one identical scene.
    tree_undo = []
    if job.get("override"):
        scope = [n for j in jobs.values() if j["kind"] == "vertex" for n in j["objects"]]
        tmats, tusers = materials_of(scope)
        tree_undo = cutout_override(tmats, job["override"])
        rec["override"] = dict(mode=job["override"], scope_objects=len(scope),
                               materials=[m.name for m in tmats], wrapped=len(tree_undo),
                               mesh_objects_sharing_those_materials=tusers)
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
        nzv = v.sum(axis=1) > 0.0
        rows.append(dict(object=name, mesh=me.name, verts=n, bake_s=round(dt, 1),
                         placements=len(obs_by_mesh.get(me.name, [])),
                         max=round(float(v.max()), 4), mean=round(float(v.mean()), 4),
                         coverage=round(float(nzv.mean()), 4),
                         mean_nonzero=round(float(v[nzv].mean()) if nzv.any() else 0.0, 6)))
        print(f"[gate3] {JOB_ID}: {name} {n} verts {dt:.1f}s max={v.max():.3f} cov={nzv.mean():.3f}")
    cutout_restore(tree_undo)
    scene.render.bake.target = "IMAGE_TEXTURES"
    p = g3.OUT / "vertex" / f"{JOB_ID}.npz"
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(str(p), **{k: v for k, (v, _) in arrays.items()})
    back = np.load(str(p))
    assert sorted(back.files) == sorted(arrays)
    rec.update(npz=p.name, npz_bytes=p.stat().st_size, meshes=len(arrays), items=rows,
               bake_s=round(sum(r.get("bake_s", 0.0) for r in rows), 1))

# ================================================================ per-PROTOTYPE vertex bake (6c item 2)
elif job["kind"] == "proto":
    # One prototype per job, ISOLATED: the 16 far-tree LOD2 prototypes sit on top of each other at the world
    # origin in trees_far_lod2.blend and 12 m apart on one lawn in the E_bake blend, exactly as the impostor
    # bake had them, so every other mesh but `isolate` is hidden from render before the bake.
    #   world "white"  + lights "off"   -> vertex AO: under a uniform environment of radiance 1 a DIFFUSE
    #                                     bake with the colour pass off returns irradiance/pi in [0, 1], and
    #                                     1 is the unoccluded value (asserted on a calibration plane far from
    #                                     the tree, which is what `cal` records).
    #   world "scene" + lights "scene" -> E_bake: the same measurement under the rig the atlas was baked at.
    # Same shadow-ray cut-out override as `vertex` / `instance`, over the union of every `proto` job's
    # objects, so a value cannot depend on the job split.
    lights = prepare(int(job.get("samples", g3.SAMPLES_VERTEX)))
    keep = set(job["objects"]) | set(job.get("isolate", []))
    hidden = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name not in keep and not o.hide_render:
            o.hide_render = True
            hidden.append(o.name)
    cal = None
    if job.get("world") == "white":
        for o in bpy.data.objects:
            if o.type == "LIGHT":
                o.hide_render = True
        w = bpy.data.worlds.new("GATE3_ao_white")
        w.use_nodes = True
        bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
        bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        bg.inputs["Strength"].default_value = 1.0
        scene.world = w
        rec["rig"]["world"] = w.name
        rec["rig"]["lights_hidden"] = sum(1 for o in bpy.data.objects if o.type == "LIGHT")
        # the unoccluded reference, 1 km away with nothing above it
        bpy.ops.mesh.primitive_plane_add(size=2.0, location=(1000.0, 1000.0, 0.0))
        calo = bpy.context.active_object
        calo.name = "GATE3_ao_cal"
        calmat = bpy.data.materials.new("MAT_GATE3_ao_cal")
        calmat.use_nodes = True
        _cb = next(n for n in calmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        _cb.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
        _cb.inputs["Roughness"].default_value = 1.0
        calo.data.materials.append(calmat)
        keep.add(calo.name)
    scope = [n for j in jobs.values() if j["kind"] == "proto" and j.get("group") == job.get("group")
             for n in j["objects"]]
    smats, susers = materials_of(scope)
    undo = cutout_override(smats, job.get("override", "shadow")) if job.get("override") else []
    rec["override"] = dict(mode=job.get("override"), scope_objects=len(scope),
                           materials=[m.name for m in smats], wrapped=len(undo),
                           mesh_objects_sharing_those_materials=susers)
    scene.render.bake.target = "VERTEX_COLORS"
    b = scene.render.bake
    b.use_selected_to_active = False
    b.use_clear = True
    b.use_pass_direct = bool(job.get("direct", True))
    b.use_pass_indirect = bool(job.get("indirect", True))
    b.use_pass_color = False
    arrays, rows = {}, []
    targets = list(job["objects"]) + ([ "GATE3_ao_cal" ] if job.get("world") == "white" else [])
    for name in targets:
        ob = bpy.data.objects.get(name)
        assert ob is not None and ob.type == "MESH", f"{JOB_ID}: {name} is not a mesh in this blend"
        me = ob.data
        ca = me.color_attributes.get("COLOR_0")
        if ca is None:
            ca = me.color_attributes.new(name="COLOR_0", type="FLOAT_COLOR", domain="POINT")
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = list(me.color_attributes).index(ca)
        bl.select_only(ob)
        t0 = time.time()
        bpy.ops.object.bake(type="DIFFUSE")
        dt = time.time() - t0
        n = len(me.vertices)
        buf = np.empty(n * 4, dtype=np.float32)
        ca.data.foreach_get("color", buf)
        v = buf.reshape(n, 4)[:, :3].copy()
        nz = v.sum(axis=1) > 0.0
        row = dict(object=name, mesh=me.name, verts=n, bake_s=round(dt, 1),
                   loc=[round(float(x), 4) for x in ob.matrix_world.translation],
                   min=[float(x) for x in v.min(axis=0)], max=[float(x) for x in v.max(axis=0)],
                   mean=[float(x) for x in v.mean(axis=0)],
                   mean_nonzero=[float(x) for x in (v[nz].mean(axis=0) if nz.any() else np.zeros(3))],
                   coverage=round(float(nz.mean()), 4))
        if name == "GATE3_ao_cal":
            cal = row
        else:
            arrays[me.name] = v
            rows.append(row)
        print(f"[gate3] {JOB_ID}: {name} {n} verts {dt:.1f}s "
              f"mean={v.mean():.4f} max={v.max():.4f} cov={nz.mean():.3f}")
    cutout_restore(undo)
    scene.render.bake.target = "IMAGE_TEXTURES"
    p = g3.OUT / job.get("out", "proto") / f"{JOB_ID}.npz"
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(str(p), **arrays)
    back = np.load(str(p))
    assert sorted(back.files) == sorted(arrays), f"{p}: array set changed on write"
    rec.update(group=job.get("group"), npz=str(p.relative_to(g3.OUT)), npz_bytes=p.stat().st_size,
               world_mode=job.get("world", "scene"), isolate=sorted(job.get("isolate", [])),
               hidden_from_render=len(hidden), samples=scene.cycles.samples,
               direct=b.use_pass_direct, indirect=b.use_pass_indirect, cal=cal, items=rows,
               bake_s=round(sum(r["bake_s"] for r in rows), 1))

# ================================================================ instance irradiance (per PLACEMENT)
elif job["kind"] == "instance":
    # Gate 4, docs/decisions.md 2026-09-16 "Shrub/reed irradiance is baked PER PLACEMENT, not per mesh".
    # One scene-linear RGB per placement = the mesh's vertex-averaged DIFFUSE direct+indirect irradiance
    # (colour off) at that instance's own world transform. The mesh data is made single-user HERE, in the
    # bake process only - this blend is never saved, so the export set's shared meshes are untouched.
    prepare(g3.SAMPLES_VERTEX)
    scene.render.bake.target = "VERTEX_COLORS"
    b = scene.render.bake
    b.use_selected_to_active = False
    b.use_clear = True
    b.use_pass_direct = True
    b.use_pass_indirect = True
    b.use_pass_color = False
    scene.cycles.samples = SPP_OVERRIDE or g3.SAMPLES_VERTEX
    scene.cycles.use_adaptive_sampling = False
    vl = bpy.context.view_layer
    chunk = int(job.get("chunk", 100))
    variants = list(job.get("variants", ["opaque"]))
    single_idx = job.get("single_chunk_index")
    keep_arrays = bool(job.get("keep_arrays"))

    obs, src_mesh, missing = [], {}, []
    for name in job["objects"]:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != "MESH":
            missing.append(dict(object=name, why="absent" if ob is None else f"type {ob.type}"))
            continue
        if name not in vl.objects:
            missing.append(dict(object=name, why="not in view layer"))
            continue
        ob.hide_render = ob.hide_viewport = ob.hide_select = False
        src_mesh[name] = ob.data.name
        ob.data = ob.data.copy()
        me = ob.data
        ca = me.color_attributes.get("COLOR_0")
        if ca is None:
            ca = me.color_attributes.new(name="COLOR_0", type="FLOAT_COLOR", domain="POINT")
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = list(me.color_attributes).index(ca)
        obs.append(ob)
    assert obs, f"{JOB_ID}: no bakeable object in {len(job['objects'])} names"

    def read_rgb(ob_):
        me_ = ob_.data
        ca_ = me_.color_attributes["COLOR_0"]
        n_ = len(me_.vertices)
        buf_ = np.empty(n_ * 4, dtype=np.float32)
        ca_.data.foreach_get("color", buf_)
        return buf_.reshape(n_, 4)[:, :3].copy()

    # The override SCOPE is every placement of every card mesh, not this job's slice: `scope` names the file
    # whose object list defines it (review fix 3 - the values must not depend on the job split).
    scope_names = list(job["objects"])
    scope_src = job.get("override_scope")
    if scope_src:
        scope_names = [d["object"] for d in json.loads((g3.OUT / scope_src).read_text())["objects"]]
    scope_mats, scope_users = materials_of(scope_names)
    rec["override_scope"] = dict(source=scope_src or "job objects", objects=len(scope_names),
                                 materials=[m.name for m in scope_mats],
                                 mesh_objects_sharing_those_materials=scope_users)

    override = bpy.data.materials.new("MAT_INST_IRR_OPAQUE")
    override.use_nodes = True
    _bsdf = next(n for n in override.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    _bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    _bsdf.inputs["Roughness"].default_value = 1.0

    results, arrays = {}, {}
    for variant in variants:
        assert variant in ("asis", "opaque", "shadow", "camray"), variant
        saved, undo, appended = {}, [], []
        if variant in ("shadow", "camray"):
            # A leaf card's own material is alpha cut-out: at a vertex that falls in a transparent texel the
            # DIFFUSE bake returns 0 (measured on the 14 near trees: 77-99 % of their COLOR_0 verts are
            # exactly zero; on a 36-tri card, inst_probe measured 10.7 % coverage and 1 black placement in
            # 12). The wrap below gives the baked surface a diffuse BSDF while the CUT-OUT still casts every
            # shadow, and it is applied to the whole scope, so the split cannot change a value.
            undo = cutout_override(scope_mats, variant)
        elif variant == "opaque":
            # Superseded by "shadow" (review fix 3): visible_shadow = False removes the card's real self- and
            # neighbour shadow, which measured a median +64 % against `asis` on the vertices lit in both.
            for ob in obs:
                saved[ob.name] = ([s.material for s in ob.material_slots], ob.visible_shadow)
                if not ob.material_slots:
                    ob.data.materials.append(override)
                    appended.append(ob)
                else:
                    for s in ob.material_slots:
                        s.material = override
                ob.visible_shadow = False
        rows, t0 = [], time.time()
        for ci in range(0, len(obs), chunk):
            part = obs[ci:ci + chunk]
            one_by_one = single_idx is not None and ci // chunk == int(single_idx)
            for grp in ([[o] for o in part] if one_by_one else [part]):
                for o in bpy.context.selected_objects:
                    o.select_set(False)
                for o in grp:
                    o.select_set(True)
                vl.objects.active = grp[0]
                bpy.ops.object.bake(type="DIFFUSE")
            for o in part:
                v = read_rgb(o)
                nz = v.sum(axis=1) > 0.0
                mean = v.mean(axis=0) if len(v) else np.zeros(3, np.float32)
                mnz = v[nz].mean(axis=0) if nz.any() else np.zeros(3, np.float32)
                rows.append(dict(object=o.name, mesh=src_mesh[o.name], verts=int(len(v)),
                                 loc=[round(float(x), 4) for x in o.matrix_world.translation],
                                 mean=[float(x) for x in mean], mean_nonzero=[float(x) for x in mnz],
                                 coverage=round(float(nz.mean()) if len(v) else 0.0, 4),
                                 max=float(v.max()) if len(v) else 0.0,
                                 how="single" if one_by_one else "batch"))
                if keep_arrays:
                    arrays[f"{variant}:{o.name}"] = v
            print(f"[gate3] {JOB_ID} {variant}: {ci + len(part)}/{len(obs)} "
                  f"({time.time() - t0:.0f}s, {'single' if one_by_one else 'batch'})")
        results[variant] = dict(items=rows, bake_s=round(time.time() - t0, 1),
                                s_per_placement=round((time.time() - t0) / max(len(rows), 1), 3),
                                zero_placements=sum(1 for r in rows if max(r["mean_nonzero"]) <= 0.0),
                                coverage_mean=round(sum(r["coverage"] for r in rows) / max(len(rows), 1), 4))
        cutout_restore(undo)
        if variant == "opaque":
            for ob in obs:
                mats, vis = saved[ob.name]
                for s, m in zip(ob.material_slots, mats):
                    s.material = m
                ob.visible_shadow = vis
            for ob in appended:                   # review note 9: zip() over an empty saved list restores nothing
                ob.data.materials.pop(index=len(ob.data.materials) - 1)
    scene.render.bake.target = "IMAGE_TEXTURES"
    if arrays:
        p = g3.OUT / "instance" / f"{JOB_ID}.npz"
        p.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(str(p), **arrays)
        back = np.load(str(p))
        assert sorted(back.files) == sorted(arrays), f"{p}: array set changed on write"
        rec.update(npz=p.name, npz_bytes=p.stat().st_size)
    rec.update(placements=len(obs), missing=missing, chunk=chunk, variants=variants,
               samples=scene.cycles.samples, single_chunk_index=single_idx, results=results,
               bake_s=round(sum(r["bake_s"] for r in results.values()), 1))

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
            # a = 0.5 IS the billboard centre plane: z runs from dist-radius (near) to dist+radius (far) and
            # depth_range_m = 2*radius, so the viewer recovers depth_from_centre_m = (a - 0.5)*depth_range_m,
            # positive AWAY from the camera. `dist` is deliberately not exported: nothing outside this loop
            # needs the camera stand-off (manifest_v4 `impostors.encode.normal_depth` says exactly this).
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
               # The placement contract is the prototype's OWN z = 0 (the nursery ground plane the trees
               # stand on and the plane tree_far's trunk_base maps to), never the bbox bottom: 14 of the 16
               # prototypes have bbox_min.z = 0 but ENV_tree_willow_s37_LOD1 is -2.67 m and _s11 -0.72 m
               # (drooping fronds that are buried in the master), and scaling by a bbox height that includes
               # them makes the willow impostors 19 % / 6 % too small and lifts them off their trunks.
               base_z_m=round(float(lo.z), 4),
               centre_z_m=round(float(centre.z), 4),
               height_above_base_m=round(float(hi.z - max(lo.z, 0.0)), 4),
               centre_above_base_m=round(float(centre.z - lo.z), 4),   # diagnostic only, NOT the contract
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
