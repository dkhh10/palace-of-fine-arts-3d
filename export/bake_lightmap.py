"""Gate 0 step 4: Cycles diffuse lightmaps on UV2 (2K EXR) + the three.js encoding, with the full value range.

    scripts/blender_run.sh 3600 -- --background export/out/gate0/gate0_set.blend --python export/bake_lightmap.py

* `light_presets.apply_final_cycles` runs first, through gate0_common.apply_final_cycles_checked, which asserts the
  two Eevee-only rigs are off (every light back at its own `energy_W`, no custom cutoff distance on the vault
  emitters). The file carries 0 LIGHT_shade_fill objects and 2 LIGHT_rotunda_vault_bounce_*.
* Bake type DIFFUSE, direct + indirect ON, **colour OFF**: the map is irradiance/pi, not irradiance x albedo, so the
  viewer multiplies it by the baseColor texture and the sun's DirectionalLight must be specular-only.
* Occluders: the hi-poly GATE0_REF originals, minus the hi twin of whatever is being baked (which is replaced in
  place by its low-poly target). Everything else in the slice stays ray-visible, so the 16-column ring shadows
  itself exactly as in the Cycles reference frame.
* Column: ONE INSTANCE is baked - the low-poly at the world transform of ARCH_rotunda_column_00_LOD0 - not the
  shared mesh at the origin. The other 15 placements need their own bake (Gate 3); see the report.
* Every map is reported as min / max / mean / clipped-pixel count, in the EXR and again after the RGBM8 encoding,
  plus the worst round-trip error, because exposure -2.833 EV means the scene-linear values are large.
"""
import bpy
import os
import sys
import json
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import bake_lib as bl  # noqa: E402

argv = g0.script_argv()
SAMPLES = int(argv[argv.index("--spp") + 1]) if "--spp" in argv else 128
# --rebake a,b,c  bakes only those jobs and re-encodes the rest from their existing EXRs (no GPU for those).
# --encode-only    bakes nothing. Default: bake everything.
REBAKE = (argv[argv.index("--rebake") + 1].split(",") if "--rebake" in argv else None)
if "--encode-only" in argv:
    REBAKE = []
g0.ensure_dirs()
g0.queue_state("running")
scene = bpy.context.scene
lights = g0.apply_final_cycles_checked(scene)
tex = g0.OUT / "tex"
report = {"samples": SAMPLES, "lights": lights}

REF_ALL = {o.name for o in bpy.data.collections["GATE0_REF"].objects}


def rgbm_encode(rgb, rng):
    """linear RGB -> RGBM8 (R,G,B,M) in 0..1, the M channel quantised to 8 bit as the decoder will read it."""
    m = np.clip(rgb.max(axis=-1) / rng, 1.0 / 255.0, 1.0)
    m = np.ceil(m * 255.0) / 255.0
    enc = np.clip(rgb / (rng * m[..., None]), 0.0, 1.0)
    enc = np.round(enc * 255.0) / 255.0
    return enc, m


def rgbm_decode(enc, m, rng):
    return enc * m[..., None] * rng


def px_stats(rgb, ceiling=None):
    lum = rgb.max(axis=-1)
    d = dict(min=round(float(rgb.min()), 6), max=round(float(rgb.max()), 6), mean=round(float(rgb.mean()), 6),
             mean_nonzero=round(float(rgb[rgb > 0].mean()) if (rgb > 0).any() else 0.0, 6),
             p99=round(float(np.percentile(lum, 99)), 6), total_px=int(rgb.shape[0] * rgb.shape[1]))
    if ceiling is not None:
        d["ceiling"] = ceiling
        d["clipped_px"] = int((lum > ceiling).sum())
        d["clipped_pct"] = round(100.0 * float((lum > ceiling).sum()) / d["total_px"], 5)
    return d


def bake_one(key, lo_name, hi_name, size, spp):
    lo = bpy.data.objects[lo_name]
    keep = (REF_ALL - ({hi_name} if hi_name else set())) | {lo.name}
    prev = bl.hide_all_but(keep)
    img = bl.bake_image(f"{key}_lightmap_{size}", size=size, colorspace="Non-Color", float_buffer=True,
                        fill=(0.0, 0.0, 0.0, 1.0))
    bl.attach_target(lo, img, g0.UV2)
    bl.select_only(lo)
    t0 = time.time()
    bl.run_bake("DIFFUSE", samples=spp, selected_to_active=False, margin=16,
                use_pass_direct=True, use_pass_indirect=True, use_pass_color=False, denoise=DENOISE)
    dt = time.time() - t0
    bl.restore_hidden(prev)
    bl.detach_targets()
    return img, dt


# Bake denoising: report which control this Blender exposes rather than assume one.
DENOISE = True
has_scene_denoise = hasattr(scene.cycles, "use_denoising")
has_bake_denoise = hasattr(scene.render.bake, "use_denoising")
report["denoise_control"] = dict(scene_cycles_use_denoising=has_scene_denoise,
                                 bake_use_denoising=has_bake_denoise, requested=DENOISE)
if has_bake_denoise:
    scene.render.bake.use_denoising = DENOISE

JOBS = [
    ("column", f"{g0.LO_COLUMN}_00", g0.COLUMN_HI, g0.TEX_SIZE, SAMPLES),
    ("capital", g0.LO_CAPITAL, g0.CAPITAL_HI, g0.TEX_SIZE, SAMPLES),
    # review finding 2: the ground's coincident hi twin must be passed so hide_all_but drops it. With hi_name=None
    # it stayed ray-visible and self-shadowed the bake (12 tris took 461 s, the slowest job in the slice).
    ("ground", "GATE0_ground", g0.GROUND_NAME_FILE.read_text().strip(), g0.TEX_SIZE, SAMPLES),
    # ORN option (c) from the addendum: a 256 px slot in a per-instance lightmap atlas. Same bake, 1/64 the texels.
    ("capital_atlas256", g0.LO_CAPITAL, g0.CAPITAL_HI, 256, SAMPLES),
]

maps = {}
s = scene.render.image_settings
for key, lo_name, hi_name, size, spp in JOBS:
    step = g0.Step(f"bake_lightmap:{key}@{size}")
    exr_path = tex / f"gate0_{key}_lightmap.exr"
    do_bake = (REBAKE is None) or (key in REBAKE)
    if not do_bake:
        img = bpy.data.images.load(str(exr_path))
        img.colorspace_settings.name = "Non-Color"
        dt = 0.0
        rgb = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)[:, :, :3]
    else:
        img, dt = bake_one(key, lo_name, hi_name, size, spp)
        rgb = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)[:, :, :3]
        img.filepath_raw = str(exr_path)
        img.file_format = "OPEN_EXR"
        keepfmt = (s.file_format, s.color_depth, s.exr_codec)
        s.file_format, s.color_depth, s.exr_codec = "OPEN_EXR", "16", "ZIP"
        img.save()
        s.file_format, s.color_depth, s.exr_codec = keepfmt

    rng = float(max(2.0 ** np.ceil(np.log2(max(rgb.max(), 1e-3))), 1.0))
    # review finding 4: the clipped count has to be taken on the SOURCE values against the encoding's ceiling.
    # Counting it on the decoded buffer is tautological - rgbm_encode clamps to rng by construction.
    clipped_src = int((rgb.max(axis=-1) > rng).sum())
    enc, m = rgbm_encode(rgb, rng)
    dec = rgbm_decode(enc, m, rng)
    err = np.abs(dec - rgb)
    rel = err / np.maximum(rgb, 1e-4)

    out8 = bpy.data.images.new(f"{key}_rgbm", size, size, alpha=True, float_buffer=False, is_data=True)
    out8.colorspace_settings.name = "Non-Color"
    out8.alpha_mode = "CHANNEL_PACKED"      # the M channel is data, not transparency: never premultiply it
    flat = np.concatenate([enc, m[..., None]], axis=-1).astype(np.float32).ravel()
    out8.pixels.foreach_set(flat)
    png_path = tex / f"gate0_{key}_lightmap_rgbm8.png"
    out8.filepath_raw = str(png_path)
    out8.file_format = "PNG"
    keepfmt = (s.file_format, s.color_depth, s.color_mode)
    s.file_format, s.color_depth, s.color_mode = "PNG", "8", "RGBA"
    out8.save()
    s.file_format, s.color_depth, s.color_mode = keepfmt

    # read the PNG back and decode it exactly as the viewer will, so the reported numbers are the shipped ones
    rb = bpy.data.images.load(str(png_path))
    rb.colorspace_settings.name = "Non-Color"
    back = np.array(rb.pixels[:], dtype=np.float32).reshape(size, size, 4)
    dec_file = rgbm_decode(back[:, :, :3], back[:, :, 3], rng)
    bpy.data.images.remove(rb)

    maps[key] = dict(
        size=size, samples=spp, bake_s=round(dt, 1),
        exr=dict(path=str(exr_path), bytes=exr_path.stat().st_size, half_float=True,
                 stats=px_stats(rgb, ceiling=rng),
                 clipped_px_vs_rgbm_range=clipped_src,
                 clipped_pct_vs_rgbm_range=round(100.0 * clipped_src / float(size * size), 5)),
        rgbm8=dict(path=str(png_path), bytes=png_path.stat().st_size, range=rng,
                   note="decode: rgb = tex.rgb * tex.a * range (linear, no sRGB). `clipped` lives on the exr entry: "
                        "the encoder clamps to range by construction, so counting it here would be tautological.",
                   stats=px_stats(dec),
                   roundtrip_abs_max=round(float(err.max()), 6),
                   roundtrip_rel_p99=round(float(np.percentile(rel[rgb > 0.01], 99)) if (rgb > 0.01).any() else 0.0, 6),
                   file_decode_abs_max=round(float(np.abs(dec_file - rgb).max()), 6)),
    )
    step.done(exr_path, png_path, bake_s=round(dt, 1), rng=rng, baked=do_bake,
              exr_max=maps[key]["exr"]["stats"]["max"], exr_mean=maps[key]["exr"]["stats"]["mean"],
              clipped_src=clipped_src)

prev = {}
try:
    prev = json.loads((g0.OUT / "bake_lightmap.json").read_text()).get("maps", {})
except Exception:
    pass
prev.update(maps)
maps = prev
report["maps"] = maps
report["rebaked"] = sorted(k for k, _, _, _, _ in JOBS if REBAKE is None or k in REBAKE)
report["column_other_15"] = (
    "Only ARCH_rotunda_column_00_LOD0's placement is baked at Gate 0. The other 15 share one mesh but not one "
    "lighting environment (the ring is not rotationally symmetric under a single sun), so at Gate 3 each placement "
    f"needs its own UV2 map: 15 x {maps['column']['bake_s']:.0f} s at 2K/{SAMPLES} spp, or one 4K atlas of 16 "
    "1024 px slots with a per-instance UV2 offset (option c) driven from the instance's node.")
(g0.OUT / "bake_lightmap.json").write_text(json.dumps(report, indent=1) + "\n")

g0.manifest_merge(textures={f"{k}_lightmap": dict(path=f"tex/gate0_{k}_lightmap_rgbm8.png", uv=g0.UV2,
                                                  colorspace="linear", encoding="RGBM8",
                                                  rgbm_range=v["rgbm8"]["range"],
                                                  decode="rgb = texel.rgb * texel.a * rgbm_range",
                                                  exr=f"tex/gate0_{k}_lightmap.exr",
                                                  content="Cycles diffuse direct+indirect, colour off "
                                                          "(irradiance/pi); multiply by baseColor in the viewer")
                            for k, v in maps.items()})
g0.queue_state("idle")
print("[gate0] bake_lightmap done")
