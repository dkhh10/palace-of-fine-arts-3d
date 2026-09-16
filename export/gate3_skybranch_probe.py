"""QA-12b-1 diagnostic: does a Cycles DIFFUSE bake take the world's CAMERA branch?

The Phase 5 world (scripts/light_calibrate.make_sky_world) gates the sky on a Light Path node:
camera rays and glossy rays get `camera_boost` / `glossy_boost` and their own saturation, everything
else (the light that lands on shaded stone) gets `diffuse_boost` and SKY_DIFFUSE_TINT. If a bake's
world lookups carry the camera flag, every lightmap got the plain blue sky where the render gets the
tinted one - which is the shape of QA-12b-1.

Three measurements, all on a debug world that reports the ray class as a colour
(camera = pure red, glossy = pure blue, everything else = pure green), with every lamp disabled:

  (a) a 256 px DIFFUSE bake (direct + indirect, colour off) of one own-map asset -> mean R:G:B of the
      non-zero texels. Red-dominated => the bake takes the camera branch.
  (b) a 160x90 Cycles frame from cam02 -> mean R:G:B over the ARCH pixels (mask by ray-cast, not by
      colour, so the measurement cannot beg the question). Green-dominated => the render takes the
      diffuse branch.
  (c) the REAL world's diffuse branch vs its camera branch as two 128x64 equirects, plus the mean of
      the shipped sky_diffuse_1024x512.exr, so we know which branch that file actually carries.

Read-only: the blend is opened and never saved. GPU: four small renders, a few minutes.

Run:  scripts/blender_run.sh 1800 -- --background --python export/gate3_skybranch_probe.py
"""
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bake_lib as bl  # noqa: E402
import gate0_common as g0  # noqa: E402
import gate3_common as g3  # noqa: E402

ASSET = "ARCH_site_concrete_podium_merged"   # an own-map asset with a lot of shaded ground-level surface
BAKE_PX = 256
BAKE_SPP = 32
FRAME_W, FRAME_H = 160, 90
FRAME_SPP = 32
EQ_W, EQ_H = 128, 64
CAM02 = dict(loc=(-79.8, 24.4, 1.55), target=(0.0, 0.0, 23.5), lens=27.0, shift_y=0.0)
OUT_DIR = g3.OUT / "skybranch"
OUT_JSON = g3.OUT / "skybranch_probe.json"


def log(m):
    print(f"[skybranch] {m}", flush=True)


def mean_rgb(a, mask=None):
    v = a.reshape(-1, 3) if mask is None else a.reshape(-1, 3)[mask.reshape(-1)]
    if v.size == 0:
        return None
    m = v.mean(axis=0)
    s = float(m.sum())
    return {"rgb": [round(float(x), 6) for x in m],
            "normalised": [round(float(x / s), 4) for x in m] if s > 1e-12 else None,
            "px": int(v.shape[0])}


def main():
    t0 = time.time()
    rep = {"asset": ASSET, "note": "debug world: camera=red, glossy=blue, everything else=green"}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(g3.OUT / "gate3_bake.blend"))
    sc = bpy.context.scene
    g0.apply_final_cycles_checked(sc)
    c = sc.cycles
    c.use_adaptive_sampling = False
    c.time_limit = 0.0
    c.use_denoising = False           # a denoiser would smear the ray-class colours
    sc.compositing_node_group = None
    sc.render.use_compositing = False
    r = sc.render
    r.film_transparent = False
    s = r.image_settings
    s.media_type = "IMAGE"
    s.file_format, s.color_depth, s.exr_codec, s.color_mode = "OPEN_EXR", "32", "ZIP", "RGB"

    def render_to_array(path, w, h, spp):
        sc.cycles.samples = spp
        r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
        r.filepath = str(path)[:-4]
        t = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t
        im = bpy.data.images.load(str(path))
        im.colorspace_settings.name = "Non-Color"
        a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, -1)[:, :, :3].copy()
        bpy.data.images.remove(im)
        return a, dt

    # ---------------------------------------------------------------- (c) the real world's two branches
    real = sc.world
    wt = real.node_tree
    lp = next((n for n in wt.nodes if n.bl_idname == "ShaderNodeLightPath"), None)
    rep["real_world"] = {"world": real.name, "has_light_path": lp is not None}
    if lp is not None:
        saved = [(ln.from_socket.name, ln.to_node.name, list(ln.to_node.inputs).index(ln.to_socket))
                 for o in lp.outputs for ln in o.links]
        saved_defaults = [(node, idx, list(wt.nodes[node].inputs[idx].default_value)
                           if hasattr(wt.nodes[node].inputs[idx].default_value, "__len__")
                           else float(wt.nodes[node].inputs[idx].default_value))
                          for _, node, idx in saved]

        def isolate(const):
            for o in lp.outputs:
                for ln in list(o.links):
                    wt.links.remove(ln)
            for sock, node, idx in saved:
                wt.nodes[node].inputs[idx].default_value = float(const.get(sock, 0.0))

        hidden = [(o, o.hide_render) for o in bpy.data.objects if o.type == "MESH"]
        for o, _ in hidden:
            o.hide_render = True
        cd = bpy.data.cameras.new("SKYBRANCH_pano")
        cd.type = "PANO"
        for holder in (cd, getattr(cd, "cycles", None)):
            if holder is not None and hasattr(holder, "panorama_type"):
                try:
                    holder.panorama_type = "EQUIRECTANGULAR"
                except Exception:
                    pass
        pano = bpy.data.objects.new("SKYBRANCH_pano", cd)
        sc.collection.objects.link(pano)
        pano.location = (0.0, 0.0, 12.0)
        pano.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
        prev_cam = sc.camera
        sc.camera = pano
        for tag, const in (("diffuse", {"Is Diffuse Ray": 1.0}), ("camera", {"Is Camera Ray": 1.0}),
                           ("glossy", {"Is Glossy Ray": 1.0})):
            isolate(const)
            a, dt = render_to_array(OUT_DIR / f"eq_{tag}.exr", EQ_W, EQ_H, 16)
            rep["real_world"][f"equirect_{tag}"] = mean_rgb(a)
            rep["real_world"][f"equirect_{tag}"]["render_s"] = round(dt, 1)
            log(f"real world {tag} branch equirect mean {rep['real_world'][f'equirect_{tag}']['rgb']}")
        # restore the world exactly as it was
        for o in lp.outputs:
            for ln in list(o.links):
                wt.links.remove(ln)
        for (sock, node, idx), (_, _, dv) in zip(saved, saved_defaults):
            wt.nodes[node].inputs[idx].default_value = dv
            wt.links.new(lp.outputs[sock], wt.nodes[node].inputs[idx])
        for o, h in hidden:
            o.hide_render = h
        bpy.data.objects.remove(pano, do_unlink=True)
        sc.camera = prev_cam
        d = rep["real_world"].get("equirect_diffuse", {}).get("rgb")
        cm = rep["real_world"].get("equirect_camera", {}).get("rgb")
        if d and cm:
            rep["real_world"]["diffuse_over_camera"] = [
                round(d[i] / cm[i], 4) if cm[i] > 1e-9 else None for i in range(3)]

    shipped = g3.OUT / f"sky_diffuse_{g3.SKY_DIFFUSE_W}x{g3.SKY_DIFFUSE_H}.exr"
    if shipped.exists():
        a = g3.read_exr32(shipped)
        rep["shipped_sky_diffuse"] = mean_rgb(a)
        rep["shipped_sky_diffuse"]["file"] = shipped.name
        rep["shipped_sky_diffuse"]["branch_claimed_by_bake_lm"] = "diffuse (isolate Is Diffuse Ray = 1)"
        log(f"shipped sky_diffuse mean {rep['shipped_sky_diffuse']['rgb']}")

    # ---------------------------------------------------------------- the debug world
    dbg = bpy.data.worlds.new("DBG_ray_class")
    dbg.use_nodes = True
    nt = dbg.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    lpn = nt.nodes.new("ShaderNodeLightPath")
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[0].default_value = 1.0
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(lpn.outputs["Is Camera Ray"], add.inputs[0])
    nt.links.new(lpn.outputs["Is Glossy Ray"], add.inputs[1])
    nt.links.new(add.outputs[0], sub.inputs[1])
    nt.links.new(lpn.outputs["Is Camera Ray"], comb.inputs["X"])   # R = is camera
    nt.links.new(sub.outputs[0], comb.inputs["Y"])                 # G = neither (the diffuse branch)
    nt.links.new(lpn.outputs["Is Glossy Ray"], comb.inputs["Z"])   # B = is glossy
    nt.links.new(comb.outputs[0], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    sc.world = dbg
    lamps = [o for o in bpy.data.objects if o.type == "LIGHT"]
    for o in lamps:
        o.hide_render = True
    rep["lamps_disabled"] = len(lamps)
    log(f"debug world in, {len(lamps)} lamps disabled")

    # ---------------------------------------------------------------- (a) the bake
    ob = bpy.data.objects[ASSET]
    ob.hide_render = ob.hide_viewport = ob.hide_select = False
    uvname = g3.UV2
    assert ob.data.uv_layers.get(uvname) is not None, f"{ASSET} has no {uvname}"
    img = bl.bake_image("skybranch_bake", size=BAKE_PX, colorspace="Non-Color", float_buffer=True,
                        fill=(0.0, 0.0, 0.0, 1.0))
    bl.attach_target(ob, img, uvname)
    bl.select_only(ob)
    dt = bl.run_bake("DIFFUSE", samples=BAKE_SPP, margin=0, use_pass_direct=True,
                     use_pass_indirect=True, use_pass_color=False, denoise=False)
    bl.detach_targets()
    a = bl.image_array(img)[:, :, :3].copy()
    nz = a.max(axis=-1) > 0.0
    rep["a_bake"] = {"asset": ASSET, "px": BAKE_PX, "spp": BAKE_SPP, "bake_s": round(dt, 1),
                     "nonzero_texels": int(nz.sum()),
                     "nonzero_frac": round(float(nz.mean()), 4),
                     "mean_nonzero": mean_rgb(a, nz), "mean_all": mean_rgb(a)}
    log(f"(a) bake mean over non-zero texels {rep['a_bake']['mean_nonzero']['rgb']} "
        f"normalised {rep['a_bake']['mean_nonzero']['normalised']}")

    # ---------------------------------------------------------------- (b) the frame, ARCH mask by ray-cast
    cd = bpy.data.cameras.new("SKYBRANCH_cam02")
    cd.lens, cd.sensor_width, cd.sensor_fit = CAM02["lens"], 36.0, "HORIZONTAL"
    cd.clip_start, cd.clip_end, cd.shift_y = 0.1, 5000.0, CAM02["shift_y"]
    cam = bpy.data.objects.new("SKYBRANCH_cam02", cd)
    cam.location = CAM02["loc"]
    cam.rotation_euler = (Vector(CAM02["target"]) - Vector(CAM02["loc"])).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    frame, dtf = render_to_array(OUT_DIR / "frame_cam02.exr", FRAME_W, FRAME_H, FRAME_SPP)

    for o in bpy.data.objects:
        if o.type == "MESH" and o.hide_viewport != o.hide_render:
            o.hide_viewport = o.hide_render
    dg = bpy.context.evaluated_depsgraph_get()
    cmw = cam.matrix_world
    orig = cmw.translation.copy()
    tr, br, blc, tl = cd.view_frame(scene=sc)
    mask_arch = np.zeros((FRAME_H, FRAME_W), dtype=bool)
    mask_any = np.zeros((FRAME_H, FRAME_W), dtype=bool)
    for iy in range(FRAME_H):
        ty = (iy + 0.5) / FRAME_H
        left, right = blc.lerp(tl, ty), br.lerp(tr, ty)
        for ix in range(FRAME_W):
            p = cmw @ left.lerp(right, (ix + 0.5) / FRAME_W)
            ok, _, _, _, hob, _ = sc.ray_cast(dg, orig, (p - orig).normalized(), distance=6000.0)
            if not ok or hob is None:
                continue
            nm = hob.original.name if hob.original else hob.name
            mask_any[iy, ix] = True
            if nm.startswith("ARCH_") or nm.startswith("EXPM_ARCH") or nm.startswith("INST_"):
                mask_arch[iy, ix] = True
    rep["b_frame"] = {"station": "cam02", "res": [FRAME_W, FRAME_H], "spp": FRAME_SPP,
                      "render_s": round(dtf, 1),
                      "arch_px": int(mask_arch.sum()), "any_geo_px": int(mask_any.sum()),
                      "mean_arch": mean_rgb(frame, mask_arch),
                      "mean_sky": mean_rgb(frame, ~mask_any)}
    log(f"(b) frame ARCH mean {rep['b_frame']['mean_arch']['rgb']} "
        f"normalised {rep['b_frame']['mean_arch']['normalised']}")
    log(f"(b) frame sky mean {rep['b_frame']['mean_sky']['rgb']} (sanity: should be pure red)")

    ba = rep["a_bake"]["mean_nonzero"]["normalised"]
    fa = rep["b_frame"]["mean_arch"]["normalised"]
    rep["verdict"] = {
        "bake_dominant": ["R", "G", "B"][int(np.argmax(ba))] if ba else None,
        "frame_dominant": ["R", "G", "B"][int(np.argmax(fa))] if fa else None,
        "bake_takes_camera_branch": bool(ba and np.argmax(ba) == 0),
        "frame_takes_diffuse_branch": bool(fa and np.argmax(fa) == 1),
    }
    rep["elapsed_s"] = round(time.time() - t0, 1)
    OUT_JSON.write_text(json.dumps(rep, indent=1))
    log(f"VERDICT {json.dumps(rep['verdict'])}")
    log(f"wrote {OUT_JSON} in {rep['elapsed_s']} s")


main()
