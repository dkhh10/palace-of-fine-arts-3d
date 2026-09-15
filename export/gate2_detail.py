"""Gate 2 addendum (QA-12-1): export the concrete DETAIL texture set and its world tiling.

    scripts/blender_run.sh 900 -- --background --python export/gate2_detail.py

Why this exists. QA-12-1 asks for the Phase 5 concrete surface at walking distance and prescribes baking each
material's bump to a tangent normal map. Measured three ways, that cannot work:

  * Cycles NORMAL bake of the material's own bump, ARCH_site__concrete_podium: std 0.00167 at 2K and 0.00272 at
    4K - it scales with the texel footprint (1.63x for 2x the resolution) and would need ~50x to be usable.
  * the same bump baked as a HEIGHT map and converted to a normal at the map's own resolution
    (bake_lib.height_to_normal), which has no bake differentials in it: also flat, and correctly so - the Bump
    node's Distance is 0.015 m while one atlas texel spans 0.038-0.118 m, and the height field varies by only
    0.041 (std, full range 0-1) from texel to texel.
  * the arithmetic: a 15 mm relief across a 118 mm texel is a 7 degree slope at its theoretical maximum.

The grain is not missing from the bake; it is finer than the bake's Nyquist. In Phase 5 Cycles evaluates the same
Bump per CAMERA pixel - about 2 cm at the cam05 station, 2-6x finer than the atlas - and the detail images
underneath it are 2048 px over a 2.16-2.71 m tile, i.e. **1.06-1.32 mm per texel**, 36-110x finer than any unique
atlas this project can afford. Reproducing it in the viewer therefore means the same thing Phase 5 does: tile the
material's own detail texture in object space, on top of the baked albedo/roughness.

This script exports that detail set - two shared triples for the whole building - and the exact tiling scale per
material, into `out/gate2/detail/` and `manifest.materials.detail`. Memory is independent of the atlases:
2 sets x 3 maps, 8.0 MB resident at 1K or 32.0 MB at 2K, shared by every concrete surface in the scene.
"""
import bpy
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate2_common as g2  # noqa: E402

g2.ensure_dirs()
DET = g2.OUT / "detail"
DET.mkdir(parents=True, exist_ok=True)
step = g0.Step("gate2_detail")
jobs = g2.read_jobs()["jobs"]
want = sorted({m for j in jobs if j["cls"] in (g2.CLS_ARCH, g2.CLS_GROUND) for m in j["src_materials"]})

bpy.ops.wm.open_mainfile(filepath=str(g2.SRC_BLEND), load_ui=False)

ROLE = {"diff": "albedo", "rough": "roughness", "disp": "height"}


def detail_of(mat):
    """The material's detail image triple and the object-space scale it is tiled at."""
    nt = mat.node_tree
    if nt is None:
        return None
    imgs = {}
    for n in nt.nodes:
        if n.bl_idname == "ShaderNodeTexImage" and n.image:
            for k, role in ROLE.items():
                if f"_{k}" in n.image.name:
                    imgs[role] = n.image
    if not imgs:
        return None
    scale = None
    for n in nt.nodes:
        if n.bl_idname == "ShaderNodeVectorMath" and n.operation == "SCALE":
            s = n.inputs["Scale"]
            if not s.links and abs(float(s.default_value) - 1.0) > 1e-6:
                scale = round(float(s.default_value), 6)
    coord = "object" if any(n.bl_idname == "ShaderNodeTexCoord" for n in nt.nodes) else "generated"
    return imgs, scale, coord


import bake_lib as bl  # noqa: E402
import numpy as np  # noqa: E402

# The two concrete sets sit on the building the walker stands next to, so they ship at the source resolution:
# the normal's slope and the albedo's ratio both lose amplitude to any pre-smoothing, and a box reduce to 1024
# costs 30 % of the encoded normal std (0.0235 -> 0.0166 on concrete_wall_007, measured). The ground sets stay
# at 1024. Roughness is low-frequency everywhere and stays at 1024.
SHIP_PX = {"concrete_wall_007": 2048, "concrete_wall_008": 2048}
SHIP_PX_DEFAULT = 1024
ROUGHNESS_PX = 1024
BUMP_DISTANCE_M = 0.015          # the Bump node's Distance inside PFA_concrete, measured

sets, per_material, saved = {}, {}, {}
raw = {}                          # set key -> {role: (h, w, 4) float32 linear, bottom-up}
for name in want:
    mat = bpy.data.materials.get(name)
    if mat is None:
        continue
    d = detail_of(mat)
    if d is None:
        per_material[name] = None
        continue
    imgs, scale, coord = d
    nm = sorted(imgs.values(), key=lambda i: i.name)[0].name
    key = re.sub(r"^TEX_", "", re.sub(r"_(diff|rough|disp)(\.\d+)?$", "", nm))
    rec = sets.setdefault(key, dict(maps={}, px=None))
    for role, im in imgs.items():
        if role in raw.setdefault(key, {}):
            continue
        raw[key][role] = bl.image_array(im)          # linear floats, whatever the file's colorspace was
        rec["px"] = im.size[0]
        if role == "height":
            rec["height_depth"] = im.depth
            rec["height_file"] = (im.filepath_raw or im.filepath or "(packed)").split("/")[-1]
        rec.setdefault("source_images", {})[role] = im.name
    per_material[name] = dict(set=key, object_scale=scale,
                              tile_m=(round(1.0 / scale, 4) if scale else None),
                              mm_per_texel=(round(1000.0 / scale / rec["px"], 4) if scale and rec["px"] else None),
                              coord_space=coord)

# Everything below is numpy -> bytes -> read back from the file. Blender's Image.save() is not in this path:
# it wrote 1024x1024 all-zero 16-bit PNGs for every one of these maps (27 749 B each, extrema 0/0), because a
# generated float image's foreach_set buffer never reached the encoder.
for key, rec in sets.items():
    tiles = [v["tile_m"] for v in per_material.values() if v and v["set"] == key and v["tile_m"]]
    tile_m = round(sum(tiles) / len(tiles), 4) if tiles else 2.5
    rec["tile_m_used_for_normal"] = tile_m
    src_px = rec["px"]
    ship_px = min(SHIP_PX.get(key, SHIP_PX_DEFAULT), src_px)
    f = max(src_px // ship_px, 1)

    # the tangent normal at the slope Cycles shades with: h(x) = Distance * H(x) metres, so the surface slope
    # is dh/dx = Distance * (dH/dtexel) / m_per_texel and n = normalize(-dh/dx, -dh/dy, 1). Differentiate at
    # the SOURCE resolution and reduce the normal afterwards - reducing the height first smooths the slope away.
    hgt = raw[key].get("height")
    if hgt is not None:
        H = hgt[..., 0]
        m_per_texel = tile_m / float(src_px)
        k = BUMP_DISTANCE_M / m_per_texel
        gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5
        gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5
        nx, ny = -gx * k, -gy * k
        nz = np.ones_like(nx)
        ln = np.sqrt(nx * nx + ny * ny + nz * nz)
        n = np.stack([nx / ln, ny / ln, nz / ln], axis=-1)
        if f > 1:
            n = bl.box_reduce(n, f)
            n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
        n = n * 0.5 + 0.5
        rec["maps"]["normal"] = dict(array=n, colorspace="linear", encode="data", px=ship_px,
                                     source_image=f"derived from {rec['source_images']['height']}",
                                     source_bit_depth=rec.get("height_depth"),
                                     k_slope_per_unit_height=round(float(k), 4),
                                     m_per_texel_m=round(float(m_per_texel), 6),
                                     height_std=round(float(H.std()), 6),
                                     height_grad_mean_per_texel=round(float(np.abs(gx).mean()), 6))
    for role in ("albedo", "roughness"):
        a = raw[key].get(role)
        if a is None:
            continue
        # the albedo IS the ratio map: any smoothing here is contrast the viewer can never get back.
        px = ROUGHNESS_PX if role == "roughness" else ship_px
        rf = max(src_px // px, 1)
        a = bl.box_reduce(a, rf)[..., :3] if rf > 1 else a[..., :3]
        rec["maps"][role] = dict(array=a, colorspace=("srgb" if role == "albedo" else "linear"),
                                 encode=("srgb" if role == "albedo" else "data"), px=px,
                                 source_image=rec["source_images"][role])

    for role, m in rec["maps"].items():
        a = np.clip(m.pop("array"), 0.0, 1.0)
        # `mean_linear` is what the viewer divides by: a compressed texture has no readable pixels, so the
        # ratio denominator has to travel in the manifest. It is measured on the LINEAR array, before any
        # sRGB encode, and re-measured from the file below.
        m["mean_linear"] = [round(float(v), 6) for v in a.reshape(-1, 3).mean(axis=0)]
        m["std_linear"] = [round(float(v), 6) for v in a.reshape(-1, 3).std(axis=0)]
        enc = bl.linear_to_srgb(a) if m["encode"] == "srgb" else a
        u8 = np.rint(enc[::-1] * 255.0).astype(np.uint8)          # flip to top-down for the file
        out = DET / f"detail_{key}_{role}.png"
        nbytes = bl.write_png_rgb8(out, u8)
        back = bl.read_png_rgb8(out).astype(np.float32) / 255.0   # VERIFY from the file, not the array
        m.update(path=f"detail/{out.name}", bytes=nbytes,
                 file_mean=[round(float(v), 6) for v in back.reshape(-1, 3).mean(axis=0)],
                 file_std=[round(float(v), 6) for v in back.reshape(-1, 3).std(axis=0)],
                 file_min=int(back.min() * 255), file_max=int(back.max() * 255))
        if m["file_std"][0] < 1e-4 and m["file_std"][1] < 1e-4:
            raise SystemExit(f"[gate2] {out.name} read back FLAT from disk: {m}")
        saved[out.name] = nbytes
        print(f"[gate2] {out.name:44s} {nbytes:8d} B  file mean {m['file_mean']}  std {m['file_std']}  "
              f"range {m['file_min']}-{m['file_max']}  linear mean {m['mean_linear']}")
    rec["maps"].pop("height", None)
    (DET / f"detail_{key}_height.png").unlink(missing_ok=True)
    rec.pop("source_images", None)
    rec["ship_px"] = ship_px

report = dict(generator="export/gate2_detail.py", source=str(g2.SRC_BLEND), sets=sets,
              per_material=per_material, files=saved,
              ship_px={k: v["ship_px"] for k, v in sets.items()},
              bump_distance_m=BUMP_DISTANCE_M,
              note="tile the set in OBJECT space at `object_scale` (uv = object_position.xy * object_scale); "
                   "multiply the baked albedo by detail_albedo / detail.mean_linear, take roughness from the "
                   "detail map, and blend the detail normal over the baked one. `mean_linear` is the ratio "
                   "denominator and is in the manifest because a compressed texture has no readable pixels. "
                   "This is what Phase 5 does - the grain is 1.05-1.32 mm per texel there against 38-118 mm "
                   "for a unique atlas texel, which is why no atlas bake can carry it.")
(g2.OUT / "detail.json").write_text(json.dumps(report, indent=1) + "\n")
for m, v in sorted(per_material.items()):
    if v:
        print(f"[gate2]   {m:26s} -> {v['set']:20s} scale {v['object_scale']} "
              f"tile {v['tile_m']} m  {v['mm_per_texel']} mm/texel")
step.done(g2.OUT / "detail.json", sets=len(sets), files=len(saved))
