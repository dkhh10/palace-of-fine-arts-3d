"""Phase 6c round 3 item 1, step 3: how many OBJECTS and how much of the TEXTURE each card material has.

    scripts/blender_run.sh 600 -- --background master_delivery.blend --python export/foliage_uv_probe.py

CPU only: no render, no GPU, master_delivery.blend opened read-only and never saved.

WHY. `foliage_albedo_check.py` compares two POPULATIONS: the mean of the shipped texture over the texels the
alpha keeps, against the mean of the Diffuse Colour pass over the pixels a station can see. That is only a
fair comparison while the visible cards sample the texture roughly uniformly and while enough separate
objects are in frame for the two per-instance terms the glTF cannot carry - `hsv(val = 1 + (R3-0.5)*val_var)`
from Object Info Random, which is per OBJECT, and the object-space cluster noise - to average to the 1 they
are pinned to. Seven of the eight materials land within 10 % and need no more than that. MAT_reeds does not
(+45 %), and this script measures the two things that decide whether that is an export bug or a sampling
artefact of the comparison:

  * `objects`  - how many separate objects carry the material. A material drawn by three clumps cannot
    average its per-object value term; one drawn by hundreds can.
  * `uv_bbox` / `uv_area_fraction` - the region of the 0-1 texture the material's cards actually address.
    A card set that uses a quarter of the sheet is drawn from a quarter of the texels, so the whole-texture
    mean is not what the renderer averages - and the VIEWER draws those same texels through the same UVs,
    so a difference here is a flaw in the comparison, not in the shipped map.

Writes export/out/gate3/foliage/uv_probe.json.
"""
import json
import os
import sys
import time
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402

SCHEMA = "pfa-phase6c/foliage-uv-probe/1"
OUT = g0.ROOT / "export" / "out" / "gate3" / "foliage"
BINS = 32


def main():
    t0 = time.time()
    assert Path(bpy.data.filepath).name == "master_delivery.blend", \
        f"foliage_uv_probe.py must run on master_delivery.blend, not {bpy.data.filepath!r}"
    par = json.loads((OUT / "params.json").read_text())
    cards = sorted(par["materials"])
    acc = {m: dict(objects=0, faces=0, uv_lo=[9e9, 9e9], uv_hi=[-9e9, -9e9],
                   hist=np.zeros((BINS, BINS), dtype=np.int64)) for m in cards}
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.data.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        slots = [s.material.name if s.material else None for s in o.material_slots]
        if not any(s in acc for s in slots):
            continue
        me = o.data
        uvl = me.uv_layers.active
        if uvl is None:
            continue
        for m in set(s for s in slots if s in acc):
            acc[m]["objects"] += 1
        uv = np.empty(len(uvl.data) * 2, dtype=np.float64)
        uvl.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        mi = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", mi)
        starts = np.empty(len(me.polygons), dtype=np.int32)
        counts = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("loop_start", starts)
        me.polygons.foreach_get("loop_total", counts)
        for si, name in enumerate(slots):
            if name not in acc:
                continue
            sel = np.nonzero(mi == si)[0]
            if not sel.size:
                continue
            loops = np.concatenate([np.arange(starts[p], starts[p] + counts[p]) for p in sel])
            pts = uv[loops]
            a = acc[name]
            a["faces"] += int(sel.size)
            a["uv_lo"] = [min(a["uv_lo"][k], float(pts[:, k].min())) for k in range(2)]
            a["uv_hi"] = [max(a["uv_hi"][k], float(pts[:, k].max())) for k in range(2)]
            b = np.clip((np.mod(pts, 1.0) * BINS).astype(int), 0, BINS - 1)
            np.add.at(a["hist"], (b[:, 1], b[:, 0]), 1)
    del dg
    rep = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/foliage_uv_probe.py", source_blend=bpy.data.filepath,
               bins=BINS, materials={})
    for m in cards:
        a = acc[m]
        h = a["hist"]
        used = int((h > 0).sum())
        rep["materials"][m] = dict(
            objects=a["objects"], faces=a["faces"],
            uv_bbox=[round(v, 4) for v in a["uv_lo"] + a["uv_hi"]] if a["faces"] else None,
            uv_area_fraction=round(used / float(BINS * BINS), 4) if a["faces"] else None,
            uv_note=f"fraction of the {BINS}x{BINS} UV grid any card of this material touches (UVs taken "
                    f"mod 1, so tiling counts once)")
    # ---- IS THE SOURCE THE ONE THAT SHIPS?
    # Every foliage image datablock in master_delivery is PACKED and named `...png.001` - a duplicate. What
    # `foliage_tex.py` reads is the file at `image.filepath` on disk. Those are two different bytes on two
    # different sides of the pipeline, and nothing until now compared them: if a packed datablock has
    # drifted from its file, Cycles renders one albedo and the KTX2 ships another, which is exactly the
    # shape of a "the shipped card is brighter than the render" defect. `img.pixels` is scene-LINEAR (the
    # sRGB decode already applied), so the disk side is decoded the same way before the means are compared.
    src = {}
    for m in cards:
        ai = par["materials"][m]["albedo_image"]
        img = bpy.data.images.get(ai["name"])
        if img is None or not ai.get("path") or not os.path.exists(ai["path"]):
            src[m] = dict(datablock=ai.get("name"), compared=False, why="no datablock or no file on disk")
            continue
        w, h = img.size
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(h, w, 4).astype(np.float64)
        # the disk file, decoded by the SAME loader and the same colour space, so the only thing that can
        # differ is the bytes themselves
        dimg = bpy.data.images.load(ai["path"], check_existing=False)
        dimg.colorspace_settings.name = img.colorspace_settings.name
        dw, dh = dimg.size
        dpx = np.empty(dw * dh * 4, dtype=np.float32)
        dimg.pixels.foreach_get(dpx)
        dpx = dpx.reshape(dh, dw, 4).astype(np.float64)
        bpy.data.images.remove(dimg)
        cut = float(par["materials"][m]["alpha_cutoff"])
        same = (w, h) == (dw, dh)
        msk = dpx[..., 3] > cut
        L = np.array([0.2126, 0.7152, 0.0722])
        src[m] = dict(
            datablock=img.name, packed=bool(img.packed_file), file=os.path.basename(ai["path"]),
            colorspace=img.colorspace_settings.name,
            size_blender=[w, h], size_disk=[dw, dh], compared=same,
            mean_lum_blender=round(float((px[..., :3][msk] @ L).mean()), 6) if same else None,
            mean_lum_disk=round(float((dpx[..., :3][msk] @ L).mean()), 6) if same else None,
            max_abs_rgb_delta=round(float(np.abs(px[..., :3] - dpx[..., :3]).max()), 6) if same else None,
            max_abs_alpha_delta=round(float(np.abs(px[..., 3] - dpx[..., 3]).max()), 6) if same else None)
        if not same:
            src[m]["why"] = "the packed datablock and the file on disk are different sizes"
            continue
        src[m]["blender_over_disk"] = round(src[m]["mean_lum_blender"]
                                            / max(src[m]["mean_lum_disk"], 1e-9), 4)
    rep["albedo_source_check"] = src
    rep["albedo_source_note"] = ("blender_over_disk is the PACKED datablock Cycles renders divided by the "
                                 "FILE export/foliage_tex.py tints and ships. Anything but 1.000 means the "
                                 "two halves of the pipeline are reading different images.")
    (OUT / "uv_probe.json").write_text(json.dumps(rep, indent=1) + "\n")
    for m, v in src.items():
        if v.get("compared"):
            print(f"  SRC {m:20s} blender/disk={v['blender_over_disk']:.4f} "
                  f"max_rgb_d={v['max_abs_rgb_delta']:.4f} max_a_d={v['max_abs_alpha_delta']:.4f}")
    print(f"[uv_probe] {len(cards)} card materials, {round(time.time() - t0, 1)} s "
          f"-> {OUT / 'uv_probe.json'}")
    for m, v in rep["materials"].items():
        print(f"  {m:20s} objects={v['objects']:5d} faces={v['faces']:8d} "
              f"uv_used={v['uv_area_fraction']} bbox={v['uv_bbox']}")


if __name__ == "__main__":
    main()
