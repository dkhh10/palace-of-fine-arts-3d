"""Gate 0 step 3 and Gate 2 (--gate2): albedo + roughness from the node trees, 2K, 16-bit PNG, into the low-poly UV1.

    scripts/blender_run.sh 1800 -- --background export/out/gate0/gate0_set.blend --python export/bake_pbr.py

Bake types used (the brief asks which): Cycles **DIFFUSE with use_pass_color only** (direct and indirect off) for
the albedo, and Cycles **ROUGHNESS** for the roughness - not EMIT. Both are look-independent scene-linear values
read straight out of the Principled BSDF, so no view transform and no light ever touches them. The third channel,
the tangent normal, is step 2's (export/bake_normal.py); it is not re-baked here, only listed in the manifest.

Column and capital bake selected-to-active from their LOD0 twin with the measured cage, so the procedural detail of
the hi-poly surface (the node trees are object-space, there are no UV nodes in MAT_column_rose /
MAT_ornament_concrete) lands on the decimated UV layout. The ground has no hi twin and bakes from itself.
"""
import bpy
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import bake_lib as bl  # noqa: E402


# ---------------------------------------------------------------- Gate 2: one atlas group / ORN prototype
if "--gate2" in g0.script_argv():
    import gate2_common as g2
    import time
    from mathutils import Matrix

    argv = g0.script_argv()
    job_id = argv[argv.index("--job") + 1]
    jobs = g2.read_jobs()
    job = next(j for j in jobs["jobs"] if j["id"] == job_id)
    # --maps lets a later round re-bake one channel without redoing the others (QA-12-1 re-baked only the
    # normals of ten groups); --bake-px overrides the bake resolution for a measurement.
    want_maps = (argv[argv.index("--maps") + 1].split(",") if "--maps" in argv else list(g2.MAPS))
    px_override = int(argv[argv.index("--bake-px") + 1]) if "--bake-px" in argv else None
    tag = argv[argv.index("--tag") + 1] if "--tag" in argv else ""
    g2.ensure_dirs()
    opened = os.path.basename(bpy.data.filepath)
    if opened != job["blend"]:
        raise SystemExit(f"[gate2] job {job_id} wants {job['blend']}, Blender opened {opened}")

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    step = g0.Step(f"bake_pbr_gate2:{job_id}")
    rec = dict(id=job_id, group=job["group"], cls=job["cls"], meshes=job["meshes"],
               reps=job["reps"], sizes=job["sizes"], started=time.strftime("%Y-%m-%dT%H:%M:%S"))

    sta = job["cls"] == g2.CLS_ORN
    if sta:
        lo = bpy.data.objects[job["lo_object"]]
        hi = bpy.data.objects[job["hi_object"]]
        m = Matrix(job["matrix"]) if job.get("matrix") else Matrix.Identity(4)
        lo.matrix_world = m
        hi.matrix_world = m
        bpy.context.view_layer.update()
        prev_hidden = bl.hide_all_but({lo.name, hi.name})
        dev = bl.deviation(lo, hi)
        cage = round(dev["max"] * 1.25, 4)
        targets, extra = [lo], [hi]
        rec.update(deviation_m=dev, cage_extrusion_m=cage, placement_matrix=job.get("matrix"))
    else:
        targets = [bpy.data.objects[r["object"]] for r in job["reps"]]
        for ob in targets:
            ob.hide_render = ob.hide_viewport = ob.hide_select = False
        prev_hidden, extra, cage = None, [], 0.0
    bpy.context.view_layer.update()

    # Review finding 2: Cycles' DIFFUSE colour pass weights base colour by (1 - Metallic), so a material with
    # a metallic input bakes its albedo dark and the viewer, which also applies `metallic`, attenuates it a
    # second time. For those materials the albedo is read through the same Emission rewire the metallic map
    # uses, which returns the Base Color itself.
    albedo_via_emit = bool(job.get("metallic"))
    # QA-12-1: for ARCH / ground the tangent normal is derived from a BAKED HEIGHT map rather than from a
    # Cycles NORMAL bake - see bake_lib.emit_bump_height for the measurement that forced it.
    normal_via_height = job["cls"] in (g2.CLS_ARCH, g2.CLS_GROUND) and not sta
    BAKE = dict(albedo=(("EMIT" if albedo_via_emit else "DIFFUSE"), g2.SAMPLES_ALBEDO, "sRGB", (0.5, 0.5, 0.5)),
                roughness=("ROUGHNESS", g2.SAMPLES_ROUGHNESS, "Non-Color", (0.5, 0.5, 0.5)),
                normal=("NORMAL", g2.SAMPLES_NORMAL, "Non-Color", (0.5, 0.5, 1.0)))
    margin = 8 if (len(job["meshes"]) > 1 and not sta) else g2.BAKE_MARGIN_PX
    rec["margin_px"] = margin
    rec["maps"] = {}
    for kind in g2.MAPS:
        if kind not in want_maps:
            continue
        btype, samples, cspace, neutral = BAKE[kind]
        bake_px = px_override or int(job["normal_px"] if kind == "normal" and job.get("normal_px")
                                     else job["size"])
        ship_px = bake_px if px_override else int(job["sizes"].get(kind, job["size"]))
        if kind == "normal" and job.get("normal_px") and not px_override:
            ship_px = int(job["normal_px"])
        img = bl.bake_image(f"{job_id}_{kind}", size=bake_px, colorspace=cspace, float_buffer=True)
        bl.fill_sentinel(img)
        for ob in targets:
            bl.attach_target(ob, img, g2.UV1)
        bl.select_only(targets[0], *(targets[1:] + extra))
        kw = dict(samples=samples, selected_to_active=sta, cage=cage, max_ray=cage, margin=margin)
        emit_states = []
        if kind == "normal" and normal_via_height:
            btype, samples = "EMIT", 4
            hstates = [bl.emit_bump_height(bpy.data.materials[n]) for n in job["src_materials"]]
            hstates = [h for h in hstates if h]
            if not hstates:
                normal_via_height = False
        if kind == "albedo":
            if albedo_via_emit:
                emit_states = [bl.emit_bsdf_input(bpy.data.materials[n], "Base Color")
                               for n in job["metallic"]]
            else:
                kw.update(use_pass_direct=False, use_pass_indirect=False, use_pass_color=True)
        try:
            wall = bl.run_bake(btype, clear=False, **kw)   # the sentinel fill IS the clear
        finally:
            for es in emit_states:
                bl.restore_emit(es)
            if kind == "normal" and normal_via_height:
                for hs in hstates:
                    bl.restore_bump_height(hs)
        st = bl.masked_stats(img, kind)
        height_info = None
        if kind == "normal" and normal_via_height:
            area = float(job.get("area_m2") or 0.0)
            cov = max(float(st.get("coverage") or 0.0), 1e-4)
            m_per_texel = (area / (cov * bake_px * bake_px)) ** 0.5 if area > 0 else 0.01
            dist = hstates[0][7]
            img, height_info = bl.height_to_normal(img, f"{job_id}_normal_from_height", dist, m_per_texel)
            st = bl.masked_stats(img, kind)
            st["from_height"] = True
            print(f"[gate2] {job_id} normal<-height: m/texel {m_per_texel:.4f} distance {dist} "
                  f"k {height_info['k_slope_per_unit_height']} height std {height_info['height_std']}")
        mean = st["mean"] or list(neutral)
        n_flood = bl.flood_sentinel(img, mean if kind != "normal" else neutral)
        out_img, rms = (img, 0.0)
        if ship_px != bake_px:
            out_img, rms = bl.resize_copy(img, f"{job_id}_{kind}_{ship_px}", ship_px)
        path = g2.TEX / g2.tex_name(job_id + tag, kind)
        bl.save_png(out_img, path, depth=16)
        rec["maps"][kind] = dict(path=str(path), bytes=os.path.getsize(path), bake_s=round(wall, 1),
                                 bake_px=bake_px, ship_px=ship_px, downsample_rms=rms,
                                 bake_type=btype + ("/EMIT(Base Color), metallic material"
                                                    if (kind == "albedo" and albedo_via_emit)
                                                    else "/color-only" if kind == "albedo" else ""),
                                 selected_to_active=sta, samples=samples, colorspace=cspace,
                                 flooded_px=n_flood, stats=st, height=height_info)
        print(f"[gate2] {job_id} {kind}: {wall:.1f} s {bake_px}->{ship_px} "
              f"coverage={st['coverage']} mean={st['mean']} bytes={os.path.getsize(path)}")
        bl.detach_targets()

    # metallic, only where a source material actually drives it (Cycles has no METALLIC bake type)
    if job.get("metallic") and "metallic" in want_maps + (["metallic"] if not tag else []):
        states = [bl.emit_bsdf_input(bpy.data.materials[n], "Metallic") for n in job["metallic"]]
        img = bl.bake_image(f"{job_id}_metallic", size=1024, colorspace="Non-Color", float_buffer=True)
        bl.fill_sentinel(img)
        for ob in targets:
            bl.attach_target(ob, img, g2.UV1)
        bl.select_only(targets[0], *(targets[1:] + extra))
        wall = bl.run_bake("EMIT", samples=4, selected_to_active=sta, cage=cage, max_ray=cage,
                           margin=margin, clear=False)
        st = bl.masked_stats(img, "metallic")
        bl.flood_sentinel(img, st["mean"] or (0.0, 0.0, 0.0))
        path = g2.TEX / g2.tex_name(job_id, "metallic")
        bl.save_png(img, path, depth=8)
        rec["maps"]["metallic"] = dict(path=str(path), bytes=os.path.getsize(path), bake_s=round(wall, 1),
                                       bake_px=1024, ship_px=1024, downsample_rms=0.0, bake_type="EMIT(Metallic)",
                                       selected_to_active=sta, samples=4, colorspace="Non-Color",
                                       flooded_px=0, stats=st)
        print(f"[gate2] {job_id} metallic: {wall:.1f} s mean={st['mean']} std={st['std']}")
        for s2 in states:
            bl.restore_emit(s2)
        bl.detach_targets()

    if prev_hidden:
        bl.restore_hidden(prev_hidden)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    rec["wall_s"] = round(sum(m["bake_s"] for m in rec["maps"].values()), 1)
    recp = g2.OUT / "bake" / f"{job_id}{tag}.json"
    if want_maps != list(g2.MAPS) and not tag and recp.exists():
        old = json.loads(recp.read_text())          # a partial re-bake keeps the maps it did not touch
        old["maps"].update(rec["maps"])
        old.update({k: v for k, v in rec.items() if k != "maps"})
        rec = old
        rec["wall_s"] = round(sum(m["bake_s"] for m in rec["maps"].values()), 1)
    recp.write_text(json.dumps(rec, indent=1) + "\n")
    step.done(*[m["path"] for m in rec["maps"].values() if os.path.exists(m["path"])], wall=rec["wall_s"])
    print(f"[gate2] bake_pbr {job_id} done")

else:
    g0.ensure_dirs()
    g0.queue_state("running")
    scene = bpy.context.scene
    g0.apply_final_cycles_checked(scene)
    report = {}
    tex = g0.OUT / "tex"
    ground_name = "GATE0_ground"

    JOBS = [
        ("column", f"{g0.LO_COLUMN}_00", g0.COLUMN_HI),
        ("capital", g0.LO_CAPITAL, g0.CAPITAL_HI),
        ("ground", ground_name, None),
    ]

    for key, lo_name, hi_name in JOBS:
        step = g0.Step(f"bake_pbr:{key}")
        lo = bpy.data.objects[lo_name]
        hi = bpy.data.objects[hi_name] if hi_name else None
        cage = 0.0
        dev = None
        if hi is not None:
            dev = bl.deviation(lo, hi)
            cage = round(dev["max"] * 1.25, 4)
        prev = bl.hide_all_but({lo.name} | ({hi.name} if hi else set()))

        alb = bl.bake_image(f"{key}_albedo", colorspace="sRGB", float_buffer=True, fill=(0.0, 0.0, 0.0, 1.0))
        bl.attach_target(lo, alb, g0.UV1)
        bl.select_only(lo, *( [hi] if hi else [] ))
        t_alb = bl.run_bake("DIFFUSE", samples=16, selected_to_active=hi is not None, cage=cage, max_ray=cage,
                            margin=16, use_pass_direct=False, use_pass_indirect=False, use_pass_color=True)
        p_alb = bl.save_png(alb, tex / f"gate0_{key}_albedo.png", depth=16)

        rgh = bl.bake_image(f"{key}_roughness", colorspace="Non-Color", float_buffer=True, fill=(0.5, 0.5, 0.5, 1.0))
        bl.attach_target(lo, rgh, g0.UV1)
        bl.select_only(lo, *( [hi] if hi else [] ))
        t_rgh = bl.run_bake("ROUGHNESS", samples=16, selected_to_active=hi is not None, cage=cage, max_ray=cage,
                            margin=16)
        p_rgh = bl.save_png(rgh, tex / f"gate0_{key}_roughness.png", depth=16)

        bl.restore_hidden(prev)
        bl.detach_targets()
        report[key] = dict(lo=lo_name, hi=hi_name, cage_extrusion_m=cage, deviation_m=dev,
                           albedo=dict(path=str(p_alb), bytes=os.path.getsize(p_alb), bake_s=round(t_alb, 1),
                                       bake_type="DIFFUSE/color-only", stats=bl.stats(alb, "albedo")),
                           roughness=dict(path=str(p_rgh), bytes=os.path.getsize(p_rgh), bake_s=round(t_rgh, 1),
                                          bake_type="ROUGHNESS", stats=bl.stats(rgh, "roughness")))
        step.done(p_alb, p_rgh, cage=cage)

    (g0.OUT / "bake_pbr.json").write_text(json.dumps(report, indent=1) + "\n")
    man_tex = {}
    for k in report:
        man_tex[f"{k}_albedo"] = dict(path=f"tex/gate0_{k}_albedo.png", uv=g0.UV1, colorspace="sRGB",
                                      encoding="16-bit PNG, glTF baseColorTexture")
        man_tex[f"{k}_roughness"] = dict(path=f"tex/gate0_{k}_roughness.png", uv=g0.UV1, colorspace="linear",
                                         encoding="16-bit PNG, glTF metallicRoughness green channel (metallic = 0)")
    g0.manifest_merge(textures=man_tex)
    g0.queue_state("idle")
    print("[gate0] bake_pbr done")
