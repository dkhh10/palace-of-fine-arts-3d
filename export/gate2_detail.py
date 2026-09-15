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


sets, per_material, saved = {}, {}, {}
for name in want:
    mat = bpy.data.materials.get(name)
    if mat is None:
        continue
    d = detail_of(mat)
    if d is None:
        per_material[name] = None
        continue
    imgs, scale, coord = d
    # the set key must keep the variant number: concrete_wall_007 (colonnade) and _008 (rotunda) are
    # different textures and an earlier rsplit collapsed them into one.
    nm = sorted(imgs.values(), key=lambda i: i.name)[0].name
    key = re.sub(r"^TEX_", "", re.sub(r"_(diff|rough|disp)(\.\d+)?$", "", nm))
    rec = sets.setdefault(key, dict(maps={}, px=None))
    for role, im in imgs.items():
        if role in rec["maps"]:
            continue
        out = DET / f"detail_{key}_{role}.png"
        prev = (im.filepath_raw, im.file_format)
        s = bpy.context.scene.render.image_settings
        pf = (s.file_format, s.color_depth, s.color_mode)
        s.file_format, s.color_depth = "PNG", "8"
        s.color_mode = "RGB"
        im.filepath_raw = str(out)
        im.file_format = "PNG"
        im.save()
        im.filepath_raw, im.file_format = prev
        s.file_format, s.color_depth, s.color_mode = pf
        rec["maps"][role] = dict(path=f"detail/{out.name}", px=im.size[0],
                                 colorspace=("srgb" if role == "albedo" else "linear"),
                                 source_image=im.name, bytes=os.path.getsize(out))
        rec["px"] = im.size[0]
        saved[out.name] = os.path.getsize(out)
    per_material[name] = dict(set=key, object_scale=scale,
                              tile_m=(round(1.0 / scale, 4) if scale else None),
                              mm_per_texel=(round(1000.0 / scale / rec["px"], 4) if scale and rec["px"] else None),
                              coord_space=coord)

# a tangent normal per set, derived from its own height at the tile's real scale, and everything shipped at
# 1K: 1K over a 2.16 m tile is 2.1 mm per texel, still 18-56x finer than the atlas texel it sits on top of,
# and 5 sets x 3 maps at 1K is 20.0 MB resident against 80.0 MB at 2K.
import bake_lib as bl  # noqa: E402

SHIP_PX = 1024
BUMP_DISTANCE_M = 0.015          # the Bump node's Distance inside PFA_concrete, measured
for key, rec in sets.items():
    tiles = [v["tile_m"] for v in per_material.values() if v and v["set"] == key and v["tile_m"]]
    tile_m = round(sum(tiles) / len(tiles), 4) if tiles else 2.5
    rec["tile_m_used_for_normal"] = tile_m
    h = rec["maps"].get("height")
    if h:
        src = bpy.data.images.load(str(g2.OUT / h["path"]), check_existing=False)
        src.colorspace_settings.name = "Non-Color"
        nimg, info = bl.height_to_normal(src, f"detail_{key}_normal", BUMP_DISTANCE_M,
                                         tile_m / float(h["px"]), sentinel=-1e9)
        out = DET / f"detail_{key}_normal.png"
        bl.save_png(nimg, out, depth=8)
        rec["maps"]["normal"] = dict(path=f"detail/{out.name}", px=h["px"], colorspace="linear",
                                     source_image=f"derived from {h['source_image']}",
                                     bytes=os.path.getsize(out), derived=info)
        saved[out.name] = os.path.getsize(out)
        st = bl.masked_stats(nimg, "detail_normal", sentinel=-1e9)
        rec["maps"]["normal"]["stats"] = st
        print(f"[gate2] detail normal {key}: tile {tile_m} m, k {info['k_slope_per_unit_height']}, "
              f"std {[round(v, 4) for v in st['std']]}")
        bpy.data.images.remove(src)
    for role, mrec in list(rec["maps"].items()):
        if role == "height":
            continue
        img = bpy.data.images.load(str(g2.OUT / mrec["path"]), check_existing=False)
        img.colorspace_settings.name = "sRGB" if mrec["colorspace"] == "srgb" else "Non-Color"
        if img.size[0] > SHIP_PX:
            small, rms = bl.resize_copy(img, f"detail_{key}_{role}_{SHIP_PX}", SHIP_PX)
            small.colorspace_settings.name = img.colorspace_settings.name
            bl.save_png(small, g2.OUT / mrec["path"], depth=8)
            mrec.update(px=SHIP_PX, bytes=os.path.getsize(g2.OUT / mrec["path"]), downsample_rms=rms)
        bpy.data.images.remove(img)
    hrec = rec["maps"].pop("height", None)   # the height ships as the normal, not as itself
    if hrec:
        (g2.OUT / hrec["path"]).unlink(missing_ok=True)
        saved.pop(os.path.basename(hrec["path"]), None)
    rec["ship_px"] = SHIP_PX

report = dict(generator="export/gate2_detail.py", source=str(g2.SRC_BLEND), sets=sets,
              per_material=per_material, files=saved, ship_px=SHIP_PX,
              bump_distance_m=BUMP_DISTANCE_M,
              note="tile the set in OBJECT space at `object_scale` (uv = object_position.xy * object_scale); "
                   "multiply the baked albedo by detail albedo / its own mean, and blend the detail normal "
                   "over the baked one. This is what Phase 5 does - the grain is 1.05-1.32 mm per texel there "
                   "against 38-118 mm for a unique atlas texel, which is why no atlas bake can carry it.")
(g2.OUT / "detail.json").write_text(json.dumps(report, indent=1) + "\n")
for k, v in sets.items():
    print(f"[gate2] detail set {k}: {sorted(v['maps'])} at {v['px']} px")
for m, v in sorted(per_material.items()):
    if v:
        print(f"[gate2]   {m:26s} -> {v['set']:20s} scale {v['object_scale']} "
              f"tile {v['tile_m']} m  {v['mm_per_texel']} mm/texel")
step.done(g2.OUT / "detail.json", sets=len(sets), files=len(saved))
