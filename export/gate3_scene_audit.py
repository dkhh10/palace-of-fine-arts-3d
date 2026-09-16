"""QA-12b-1 read-only audit: is the Gate 3 lightmap bake scene the same light/bounce scene as
master_delivery.blend? Plus a backface sweep for more QA-13-2-shaped defects.

Read-only: no render, no bake, no save. Opens gate3_bake.blend (the blend export/bake_lm.py opens for
every own-map job), applies exactly what `bake_lm.prepare()` applies, records the rig / world / cycles /
bounce-material state, then opens master_delivery.blend and records the same for comparison.

Run:  scripts/blender_run.sh 1800 -- --background --python export/gate3_scene_audit.py
"""
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate0_common as g0  # noqa: E402
import gate3_common as g3  # noqa: E402

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
DELIVERY = MAIN / "master_delivery.blend"
OUT_JSON = g3.OUT / "scene_audit.json"
GRID_W, GRID_H = 240, 135

STATIONS = [
    ("cam01", (-14.1, 100.0, 1.3), (0.0, 0.0, 1.3), 20.0, 0.06),
    ("cam02", (-79.8, 24.4, 1.55), (0.0, 0.0, 23.5), 27.0, 0.0),
    ("cam03", (81.0, 12.04, 1.7), (0.0, 0.0, 9.2), 18.0, 0.0),
    ("cam04", (0.0, 3.0, 1.6), (0.0, 3.0, 40.0), 15.0, 0.0),
    ("cam05", (28.1, 111.8, 1.5), (0.0, 0.0, 21.5), 35.0, 0.0),
    ("cam06", (-205.0, 143.0, 120.0), (0.0, 0.0, 15.0), 50.0, 0.0),
]

# the bounce surfaces the question names
BOUNCE_PREFIXES = ("ARCH_colonnade", "ARCH_rotunda", "ARCH_site", "EXPM_ARCH", "EXPHI_ARCH")


def log(m):
    print(f"[audit] {m}", flush=True)


def img_mean_rgb(im):
    try:
        n = im.size[0] * im.size[1] * im.channels
        if n == 0 or n > 80_000_000:
            return None
        buf = np.empty(n, dtype=np.float32)
        im.pixels.foreach_get(buf)
        a = buf.reshape(-1, im.channels)[:, :3]
        step = max(1, a.shape[0] // 200_000)
        a = a[::step]
        if im.colorspace_settings.name == "sRGB":
            a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
        m = a.mean(axis=0)
        return [round(float(x), 4) for x in m]
    except Exception as e:  # noqa: BLE001
        return f"<unreadable: {e}>"


def mat_row(mat):
    row = {"material": mat.name, "nodes": 0, "base_color": None, "base_color_from": None,
           "images": [], "saturation": None}
    if not mat.use_nodes:
        row["base_color_from"] = "no nodes (viewport diffuse_color)"
        row["base_color"] = [round(float(x), 4) for x in mat.diffuse_color[:3]]
        return row
    nt = mat.node_tree
    row["nodes"] = len(nt.nodes)
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        inp = bsdf.inputs["Base Color"]
        if inp.links:
            src = inp.links[0].from_node
            hop = 0
            while src.type not in ("TEX_IMAGE", "RGB", "ATTRIBUTE") and hop < 8:
                nxt = None
                for i in src.inputs:
                    if i.links:
                        nxt = i.links[0].from_node
                        break
                if nxt is None:
                    break
                src, hop = nxt, hop + 1
            row["base_color_from"] = f"linked -> {src.type}"
            if src.type == "TEX_IMAGE" and src.image is not None:
                row["base_color_from"] = f"image {src.image.name}"
                row["base_color"] = img_mean_rgb(src.image)
            elif src.type == "RGB":
                row["base_color"] = [round(float(x), 4) for x in src.outputs[0].default_value[:3]]
        else:
            row["base_color_from"] = "unlinked default"
            row["base_color"] = [round(float(x), 4) for x in inp.default_value[:3]]
    row["images"] = sorted({n.image.name for n in nt.nodes if n.type == "TEX_IMAGE" and n.image})[:6]
    bc = row["base_color"]
    if isinstance(bc, list) and len(bc) == 3 and max(bc) > 1e-6:
        row["saturation"] = round((max(bc) - min(bc)) / max(bc), 4)
    return row


def rig_state(scene):
    lights = []
    for o in bpy.data.objects:
        if o.type != "LIGHT":
            continue
        d = o.data
        lights.append({
            "name": o.name, "type": d.type, "energy": round(float(d.energy), 3),
            "hide_render": bool(o.hide_render),
            "visible_camera": bool(getattr(o, "visible_camera", True)),
            "visible_diffuse": bool(getattr(o, "visible_diffuse", True)),
            "energy_W": o.get("energy_W"), "energy_W_eevee": o.get("energy_W_eevee"),
            "custom_distance": bool(getattr(d, "use_custom_distance", False)),
            "temperature": round(float(getattr(d, "temperature", 0.0)), 1),
            "use_temperature": bool(getattr(d, "use_temperature", False)),
            "color": [round(float(x), 4) for x in d.color],
            "loc": [round(float(x), 2) for x in o.matrix_world.translation],
        })
    return sorted(lights, key=lambda r: r["name"])


def world_state(scene):
    w = scene.world
    if w is None:
        return {"world": None}
    out = {"world": w.name, "use_nodes": bool(w.use_nodes)}
    if not w.use_nodes:
        return out
    nt = w.node_tree
    sky = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeTexSky"), None)
    bgs = [n for n in nt.nodes if n.bl_idname == "ShaderNodeBackground"]
    out["backgrounds"] = [{"name": n.name,
                           "strength": round(float(n.inputs["Strength"].default_value), 5),
                           "color_linked": bool(n.inputs["Color"].links)} for n in bgs]
    out["light_paths"] = [n.name for n in nt.nodes if n.bl_idname == "ShaderNodeLightPath"]
    if sky is not None:
        out["sky"] = {k: (round(float(getattr(sky, k)), 6) if isinstance(getattr(sky, k), float)
                          else getattr(sky, k))
                      for k in ("sky_type", "sun_disc", "sun_size", "sun_intensity", "sun_elevation",
                                "sun_rotation", "altitude", "air_density", "aerosol_density",
                                "ozone_density")}
        import math
        out["sky"]["sun_elevation_deg"] = round(math.degrees(sky.sun_elevation), 3)
        out["sky"]["sun_rotation_deg"] = round(math.degrees(sky.sun_rotation), 3)
    return out


def cycles_state(scene):
    c = scene.cycles
    keys = ("samples", "use_adaptive_sampling", "adaptive_threshold", "max_bounces", "diffuse_bounces",
            "glossy_bounces", "transmission_bounces", "volume_bounces", "transparent_max_bounces",
            "sample_clamp_direct", "sample_clamp_indirect", "caustics_reflective",
            "caustics_refractive", "blur_glossy", "use_denoising", "denoiser", "time_limit",
            "light_sampling_threshold")
    out = {}
    for k in keys:
        v = getattr(c, k, None)
        out[k] = round(float(v), 5) if isinstance(v, float) else v
    fe = getattr(scene.render, "film_exposure", None)
    out["film_exposure"] = round(float(fe), 5) if fe is not None else None
    vs = scene.view_settings
    out["view_transform"] = vs.view_transform
    out["look"] = vs.look
    out["exposure"] = round(float(vs.exposure), 5)
    out["compositing_node_group"] = None if scene.compositing_node_group is None else \
        scene.compositing_node_group.name
    out["use_compositing"] = bool(scene.render.use_compositing)
    return out


def bounce_materials():
    rows, seen = [], set()
    for o in bpy.data.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        if not any(o.name.startswith(p) or o.data.name.startswith(p) for p in BOUNCE_PREFIXES):
            continue
        for m in o.data.materials:
            if m is None or m.name in seen:
                continue
            seen.add(m.name)
            r = mat_row(m)
            r["example_object"] = o.name
            rows.append(r)
    return sorted(rows, key=lambda r: r["material"])


def backface_sweep(scene):
    """Every object whose visible pixels are seen from behind: the QA-13-2 shape, for the whole set."""
    import bpy_extras  # noqa: F401
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.hide_viewport != ob.hide_render:
            ob.hide_viewport = ob.hide_render
    dg = bpy.context.evaluated_depsgraph_get()
    tot = {}
    for key, loc, tgt, lens, shift in STATIONS:
        d = bpy.data.cameras.new(key + "_bf")
        d.lens, d.sensor_width, d.sensor_fit = lens, 36.0, "HORIZONTAL"
        d.clip_start, d.clip_end, d.shift_y = 0.1, 5000.0, shift
        cam = bpy.data.objects.new(key + "_bf", d)
        cam.location = loc
        if abs(tgt[0] - loc[0]) < 1e-6 and abs(tgt[1] - loc[1]) < 1e-6:
            import math
            cam.rotation_euler = Euler((math.pi, 0.0, 0.0))
        else:
            cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(cam)
        dg = bpy.context.evaluated_depsgraph_get()
        cmw = cam.matrix_world
        orig = cmw.translation.copy()
        tr, br, bl, tl = cam.data.view_frame(scene=scene)
        for iy in range(GRID_H):
            ty = (iy + 0.5) / GRID_H
            left, right = bl.lerp(tl, ty), br.lerp(tr, ty)
            for ix in range(GRID_W):
                p = cmw @ left.lerp(right, (ix + 0.5) / GRID_W)
                dvec = (p - orig).normalized()
                ok, hloc, hn, idx, ob, _ = scene.ray_cast(dg, orig, dvec, distance=6000.0)
                if not ok or ob is None:
                    continue
                nm = ob.original.name if ob.original else ob.name
                e = tot.setdefault(nm, {"px": 0, "back_px": 0})
                e["px"] += 1
                if hn.dot(-dvec) < 0.0:
                    e["back_px"] += 1
        bpy.data.objects.remove(cam, do_unlink=True)
        log(f"backface sweep {key} done")
    rows = []
    for nm, e in tot.items():
        if e["px"] < 200:
            continue
        f = e["back_px"] / e["px"]
        rows.append({"object": nm, "px": e["px"], "backface_px": e["back_px"], "backface_frac": round(f, 4)})
    return sorted(rows, key=lambda r: -r["backface_frac"])


def main():
    t0 = time.time()
    rep = {}

    # ---- the bake scene, exactly as bake_lm.prepare() leaves it
    blend = g3.OUT / "gate3_bake.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    sc = bpy.context.scene
    lights = g0.apply_final_cycles_checked(sc)
    c = sc.cycles
    c.use_adaptive_sampling = False
    c.time_limit = 0.0
    c.samples = g3.SAMPLES_LM
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    sc.compositing_node_group = None
    rep["bake"] = {"blend": str(blend), "apply_final_cycles_lights": len(lights),
                   "lights": rig_state(sc), "world": world_state(sc), "cycles": cycles_state(sc),
                   "bounce_materials": bounce_materials()}
    log(f"bake scene: {len(rep['bake']['lights'])} lights, "
        f"{len(rep['bake']['bounce_materials'])} bounce materials")
    rep["backface_sweep"] = backface_sweep(sc)
    log(f"backface sweep: {len(rep['backface_sweep'])} objects over 200 px")

    # ---- master_delivery, as saved (never modified, never saved)
    assert DELIVERY.exists(), DELIVERY
    bpy.ops.wm.open_mainfile(filepath=str(DELIVERY))
    sd = bpy.context.scene
    rep["delivery"] = {"blend": str(DELIVERY), "lights": rig_state(sd), "world": world_state(sd),
                       "cycles": cycles_state(sd), "bounce_materials": bounce_materials()}
    log(f"delivery scene: {len(rep['delivery']['lights'])} lights")

    # ---- the comparison
    bl_ = {r["name"]: r for r in rep["bake"]["lights"]}
    dl = {r["name"]: r for r in rep["delivery"]["lights"]}
    diffs = []
    for n in sorted(set(bl_) | set(dl)):
        a, b = bl_.get(n), dl.get(n)
        if a is None:
            diffs.append({"light": n, "issue": "missing from the bake scene",
                          "delivery_energy": b["energy"], "delivery_hide_render": b["hide_render"]})
        elif b is None:
            diffs.append({"light": n, "issue": "extra in the bake scene", "bake_energy": a["energy"]})
        else:
            d = {}
            for k in ("energy", "hide_render", "color", "temperature", "use_temperature",
                      "custom_distance", "type", "loc"):
                if a[k] != b[k]:
                    d[k] = {"bake": a[k], "delivery": b[k]}
            if d:
                diffs.append({"light": n, "diff": d})
    rep["light_diff"] = diffs
    cyc = {}
    for k, v in rep["bake"]["cycles"].items():
        w = rep["delivery"]["cycles"].get(k)
        if v != w:
            cyc[k] = {"bake": v, "delivery": w}
    rep["cycles_diff"] = cyc
    wb, wd = rep["bake"]["world"], rep["delivery"]["world"]
    wdiff = {}
    for k in set(wb) | set(wd):
        if wb.get(k) != wd.get(k):
            wdiff[k] = {"bake": wb.get(k), "delivery": wd.get(k)}
    rep["world_diff"] = wdiff
    mb = {r["material"]: r for r in rep["bake"]["bounce_materials"]}
    md = {r["material"]: r for r in rep["delivery"]["bounce_materials"]}
    rep["material_overlap"] = {"bake_only": sorted(set(mb) - set(md))[:40],
                               "delivery_only": sorted(set(md) - set(mb))[:40],
                               "shared": sorted(set(mb) & set(md))[:40]}
    rep["elapsed_s"] = round(time.time() - t0, 1)
    OUT_JSON.write_text(json.dumps(rep, indent=1))
    log(f"lights differing: {len(diffs)}; cycles keys differing: {len(cyc)}; "
        f"world keys differing: {len(wdiff)}")
    log(f"wrote {OUT_JSON} in {rep['elapsed_s']} s")


main()
