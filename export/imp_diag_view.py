"""6c item 1, part C (short GPU): render ONE impostor view in Cycles at the final rig and put it beside the
frame the shipped atlas holds for the same direction, both pushed through the delivery view transform.

    scripts/blender_run.sh 900 -- --background export/out/gate3/gate3_imp.blend --python-exit-code 1 \
        --python export/imp_diag_view.py -- --proto <name> --col C --row R [--scale 4] [--variants asis,diffuse] \
        2>&1 | tee -a renders/logs/imp_diag_view.log       # review r1 finding 3: always tee the run

`asis`   reproduces the Gate 3 bake exactly (the blend's own split-ray world) - if this matches the atlas, the
         encode chain is faithful and the question is what the bake SAW, not how it was written.
`diffuse` re-renders the same view with light_probes.bake_world (the world's diffuse branch on every ray), the
         candidate repair named in docs/briefs/phase6c_bake.md.

Writes out/gate3/impostor_diag_view_<proto>.json and, per variant, a display-referred PNG beside the atlas
frame's own display PNG (out/gate3/impostor/diag_*.png). Nothing is saved back into the blend.
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

argv = g0.script_argv()


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


PROTO = arg("--proto")
COL = int(arg("--col"))
ROW = int(arg("--row"))
SCALE = int(arg("--scale", "4"))
SPP = int(arg("--spp", "64"))
VARIANTS = arg("--variants", "asis,diffuse").split(",")
OUTD = g3.OUT / "impostor"
OUTD.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
MANIFEST = g3.OUT / "manifest.json"
if not MANIFEST.exists():                      # the synced copy lives in MAIN (MANIFEST_IS_IN_MAIN.txt)
    from pathlib import Path as _P
    MANIFEST = _P("/Users/dk/Projects/3d render blender 3rd attempt building/export/out/gate3/manifest.json")
man = json.load(open(MANIFEST))
imp = man["impostors"]
RANGE = float(imp["prototypes"][PROTO]["range"])
jobs = {j["id"]: j for j in g3.read_jobs()["jobs"]}
job = jobs["imp_" + PROTO]
VIEW = dict(man["view"])


def octa_dir(col, row, grid):
    u = col / float(grid - 1) * 2.0 - 1.0
    v = row / float(grid - 1) * 2.0 - 1.0
    au, av = abs(u), abs(v)
    z = 1.0 - au - av
    if z >= 0.0:
        d = Vector((u, v, z))
    else:
        d = Vector(((1.0 - av) * (1.0 if u >= 0 else -1.0), (1.0 - au) * (1.0 if v >= 0 else -1.0), z))
    d.normalize()
    return d


def stats(lin, alpha, tag):
    body = alpha.reshape(-1) > 0.5
    f = lin.reshape(-1, 3)
    if not body.any():
        return dict(tag=tag, body_px=0)
    m = f[body].mean(axis=0)
    mx, mn = float(max(m)), float(min(m))
    h = 0.0
    if mx > mn:
        r, g, b = [float(c) for c in m]
        if mx == r:
            h = (60 * ((g - b) / (mx - mn)) + 360) % 360
        elif mx == g:
            h = 60 * ((b - r) / (mx - mn)) + 120
        else:
            h = 60 * ((r - g) / (mx - mn)) + 240
    return dict(tag=tag, body_px=int(body.sum()), mean_rgb=[round(float(c), 5) for c in m],
                hue_deg=round(h, 1), sat=round((mx - mn) / max(mx, 1e-9), 3), val=round(mx, 5),
                b_over_g=round(float(m[2] / max(m[1], 1e-6)), 3),
                r_over_g=round(float(m[0] / max(m[1], 1e-6)), 3),
                blue_max_px_pct=round(100.0 * float((f[body].argmax(axis=-1) == 2).mean()), 2))


_SAVE_SCENE = None


def save_scene():
    """A scene that exists only to carry the delivery view transform and 8-bit PNG output for save_render."""
    global _SAVE_SCENE
    if _SAVE_SCENE is None:
        sc = bpy.data.scenes.new("DIAG_SAVE")
        v = sc.view_settings
        v.view_transform, v.look = VIEW["view_transform"], VIEW["look"]
        v.exposure, v.gamma = float(VIEW["exposure_ev"]), float(VIEW["gamma"])
        sc.display_settings.display_device = VIEW["display_device"]
        st = sc.render.image_settings
        # Blender 5.2 gates file_format on media_type, and a new scene inherits the blend's MULTI_LAYER_IMAGE
        print("[diag] save scene media_type", st.media_type, "->",
              [i.identifier for i in st.bl_rna.properties["media_type"].enum_items])
        st.media_type = "IMAGE"
        st.file_format, st.color_depth, st.color_mode = "PNG", "8", "RGBA"
        st.compression = 15
        _SAVE_SCENE = sc
    return _SAVE_SCENE


def to_display(rgb, alpha, path):
    """rgb: (h, w, 3) linear PREMULTIPLIED, bottom-up. -> the delivery view transform, as an 8-bit PNG."""
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(f"diag_{path.stem}", w, h, alpha=True, float_buffer=True)
    buf = np.concatenate([rgb.astype(np.float32), alpha.astype(np.float32)[..., None]], axis=-1)
    img.pixels.foreach_set(buf.reshape(-1))
    img.file_format = "PNG"
    # save_render takes the SCENE's image_settings, and this blend's are the multilayer-EXR ones the bake
    # needs, so the save goes through a throwaway scene that carries only the delivery view transform.
    img.save_render(filepath=str(path), scene=save_scene())
    bpy.data.images.remove(img)
    # read the file back (tech_notes: a generated float image can write zeros) as RAW 0-1 display codes
    rd = bpy.data.images.load(str(path))
    rd.colorspace_settings.name = "Non-Color"
    px = np.empty(len(rd.pixels), dtype=np.float32)
    rd.pixels.foreach_get(px)
    back = (px.reshape(rd.size[1], rd.size[0], 4) * 255.0)
    bpy.data.images.remove(rd)
    assert back[..., :3].max() > 0, f"{path}: the view transform wrote black"
    return back


def display_stats(u8, alpha, tag):
    body = alpha.reshape(-1) > 0.5
    f = u8.reshape(-1, u8.shape[-1])[..., :3].astype(np.float32)
    if not body.any():
        return dict(tag=tag, body_px=0)
    m = f[body].mean(axis=0)
    mx, mn = float(max(m)), float(min(m))
    h = 0.0
    if mx > mn:
        r, g, b = [float(c) for c in m]
        if mx == r:
            h = (60 * ((g - b) / (mx - mn)) + 360) % 360
        elif mx == g:
            h = 60 * ((b - r) / (mx - mn)) + 120
        else:
            h = 60 * ((r - g) / (mx - mn)) + 240
    return dict(tag=tag, body_px=int(body.sum()), mean_srgb8=[round(float(c), 1) for c in m],
                hue_srgb_deg=round(h, 1), sat_srgb=round((mx - mn) / max(mx, 1e-9), 3),
                b_over_g_srgb=round(float(m[2] / max(m[1], 1e-6)), 3),
                g_gt_r_pct=round(100.0 * float((f[body][:, 1] > f[body][:, 0]).mean()), 1))


# ------------------------------------------------------------------ the shipped atlas frame, for comparison
# Review r1 finding 3: this report used to be written from scratch on every run, so a second run with other
# variants silently replaced the first and the numbers that carry the verdict survived nowhere. The file is
# now MERGED into - earlier variants are kept, a re-run of the same variant replaces only itself - and every
# run is tee'd into renders/logs/ by the caller. The `asis` / `diffuse` headline numbers in
# docs/decisions.md and README #35 come from the run that was overwritten before this fix; they are marked
# as such in the README and were not re-spent on the GPU.
REPORT = g3.OUT / f"impostor_diag_view_{PROTO}.json"
rep = dict(prototype=PROTO, col=COL, row=ROW, scale=SCALE, spp=SPP, range=RANGE,
           dir_blender=[round(float(c), 4) for c in octa_dir(COL, ROW, imp["grid"])], variants={})
if REPORT.exists():
    try:
        prev = json.loads(REPORT.read_text())
        if (prev.get("col"), prev.get("row")) == (COL, ROW):
            rep["variants"].update(prev.get("variants") or {})
            rep["merged_from_runs"] = (prev.get("merged_from_runs") or 0) + 1
    except Exception as e:
        print(f"[diag] existing {REPORT.name} unreadable ({e}) - starting a fresh report")
rep["runs"] = (rep.get("runs") or [])
vs = scene.view_settings
vs.view_transform, vs.look = VIEW["view_transform"], VIEW["look"]
vs.exposure, vs.gamma = float(VIEW["exposure_ev"]), float(VIEW["gamma"])
scene.display_settings.display_device = VIEW["display_device"]
atlas_png = OUTD / f"gate3_imp_{PROTO}_albedo_2048.png"
F2, G2 = imp["variant_2k"]["frame_px"], imp["variant_2k"]["gutter_px"]
INNER = F2 - 2 * G2
a8 = g3.read_png(atlas_png)
alin = g3.gamma2_decode_u8(a8[..., :3], RANGE)
aal = a8[..., 3].astype(np.float32) / 255.0
y0, x0 = ROW * F2 + G2, COL * F2 + G2
fa_lin = alin[y0:y0 + INNER, x0:x0 + INNER]
fa_al = aal[y0:y0 + INNER, x0:x0 + INNER]
rep["atlas_frame"] = dict(linear=stats(fa_lin, fa_al, "atlas_linear"))
d8 = to_display(fa_lin * fa_al[..., None], fa_al, OUTD / f"diag_{PROTO}_{COL}_{ROW}_atlas.png")
rep["atlas_frame"]["display"] = display_stats(d8, fa_al, "atlas_display")

# ------------------------------------------------------------------ the fresh Cycles renders
lo, hi = Vector(job["bbox_min"]), Vector(job["bbox_max"])
centre = (lo + hi) * 0.5
radius = max((hi - lo).length * 0.5, 1e-3)
dist = radius * 6.0
d = octa_dir(COL, ROW, imp["grid"])
up = Vector((0.0, 1.0, 0.0)) if abs(d.z) > 0.999 else Vector((0.0, 0.0, 1.0))
xax = up.cross(d).normalized()
yax = d.cross(xax).normalized()
cam = bpy.data.objects["GATE3_imp_cam"]
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2.0 * radius * (g3.IMP_FRAME_PX / float(g3.IMP_INNER_PX))
cam.data.clip_start, cam.data.clip_end = 0.01, dist + 4.0 * radius
cam.matrix_world = Matrix(((xax.x, yax.x, d.x, centre.x + d.x * dist),
                           (xax.y, yax.y, d.y, centre.y + d.y * dist),
                           (xax.z, yax.z, d.z, centre.z + d.z * dist),
                           (0.0, 0.0, 0.0, 1.0)))
scene.camera = cam
keep = {PROTO, "GATE3_imp_lawn"}
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = o.name not in keep
r = scene.render
r.resolution_x = r.resolution_y = g3.IMP_FRAME_PX * SCALE
r.resolution_percentage = 100
r.film_transparent = True
vl = bpy.context.view_layer
vl.use_pass_normal = vl.use_pass_z = False
s = r.image_settings


def exr_settings():
    """The bake's output settings. Applied AFTER the rig, because light_presets.apply_final_cycles sets
    file_format = PNG and Blender 5.2 refuses that while media_type is MULTI_LAYER_IMAGE."""
    s.media_type = "MULTI_LAYER_IMAGE"
    s.use_exr_interleave = True
    s.file_format, s.color_depth, s.exr_codec, s.color_mode = "OPEN_EXR_MULTILAYER", "32", "NONE", "RGBA"
    # light_presets.apply_final_cycles sets film_transparent = False; the impostor bake needs it True or the
    # sky fills the frame, alpha comes back 1 everywhere and the "crown" mean is the sky's blue.
    r.film_transparent = True


tmp = OUTD / "diag_view.exr"
world_ship = scene.world
GIN = G2 * SCALE
IN2 = INNER * SCALE

for variant in VARIANTS:
    s.media_type = "IMAGE"                    # let the rig set its PNG default, then take it back
    lights = g0.apply_final_cycles_checked(scene)
    exr_settings()
    c = scene.cycles
    c.use_adaptive_sampling = False
    c.time_limit = 0.0
    c.samples = SPP
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    scene.compositing_node_group = None
    scene.world = world_ship
    wprops = {k: (list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v)
              for k, v in world_ship.items()} if world_ship else {}
    if variant == "diffuse":
        import light_probes as lprobe
        bw = lprobe.bake_world(scene)
        assert bw is not None, "bake_world() returned None: the world carries no sun az/el"
        scene.world = bw
    # the decomposition: which term carries the blue
    for lo in bpy.data.objects:
        if lo.type == "LIGHT":
            lo.hide_render = (variant == "skyonly")
    if variant == "sunonly":
        scene.world = None
    t0 = time.time()
    r.filepath = str(tmp)[:-4]
    bpy.ops.render.render(write_still=True)
    secs = time.time() - t0
    ch = g3.read_exr_channels(tmp)

    def pick(*cands):
        for cd in cands:
            if cd in ch:
                return ch[cd]
        raise KeyError(f"{cands} not in {sorted(ch)}")

    cr, cg, cb = pick("ViewLayer.Combined.R"), pick("ViewLayer.Combined.G"), pick("ViewLayer.Combined.B")
    ca = np.clip(pick("ViewLayer.Combined.A"), 0.0, 1.0)
    pm = np.stack([cr, cg, cb], axis=-1)[GIN:GIN + IN2, GIN:GIN + IN2]
    al = ca[GIN:GIN + IN2, GIN:GIN + IN2]
    inv = np.where(al > 0.02, 1.0 / np.maximum(al, 0.02), 0.0)
    lin = pm * inv[..., None]
    p = OUTD / f"diag_{PROTO}_{COL}_{ROW}_{variant}.png"
    d8 = to_display(pm, al, p)
    rep["variants"][variant] = dict(render_s=round(secs, 1), lights=len(lights),
                                    world=scene.world.name if scene.world else None, world_props=wprops,
                                    linear=stats(lin, al, f"{variant}_linear"),
                                    display=display_stats(d8, al, f"{variant}_display"), png=p.name)
    print(f"[diag] {PROTO} {variant}: {secs:.1f}s  linear {rep['variants'][variant]['linear']}")

if tmp.exists():
    tmp.unlink()
rep["runs"].append(dict(at=time.strftime("%Y-%m-%dT%H:%M:%S"), variants=list(VARIANTS)))
json.dump(rep, open(REPORT, "w"), indent=1)
print(f"[diag] wrote {REPORT} ({len(rep['variants'])} variants: {', '.join(sorted(rep['variants']))})")
