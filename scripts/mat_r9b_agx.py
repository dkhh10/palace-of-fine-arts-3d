"""Round 9b -- the view pipeline's transfer, measured AT THE SHIPPED LOOK (docs/reviews/mat_r9_review.md 1 and 2).

    blender -b --python scripts/mat_r9b_agx.py -- [--exposure -2.8331] [--looks]

`scripts/mat_r9_agx.py` (round 9) built an empty file and called `common.setup_scene()`, which sets
`view_transform` but never `look`, so its whole table was measured at **Base Contrast** while the project renders
at `light_presets.LOOK` = "AgX - High Contrast" (build_master writes it into master.blend via `apply_look`, and
nothing in the render path resets it -- `common.setup_scene` does not touch `look`).  The look is a contrast AND
chroma operator, so a transfer measured at Base is the wrong number for every conclusion round 9 drew from it.

What this measures.  A grid of emission patches is rendered through the SHIPPED colour management (AgX + LOOK +
the master's view exposure).  Every row is one base scene colour on the concrete's own chroma axis; the columns
perturb the scene value by a known factor -- all three channels together (the LUMINANCE transfer, which is what a
near-neutral albedo ratio map has to be inverted through) and each channel alone (the CHROMA transfer, which is
what a coloured albedo tint has to fight).  For each row we print

    t = d log(display) / d log(scene)                        (central difference over x0.90 .. x1.10)

as a function of the row's own DISPLAY luminance, which is the only variable the projection can look up per pixel.
The table is written to assets/textures/projection/agx_transfer.json and read by `mat_projection.build`, which
raises its display-space ratio to the 1/t power so the map is a SCENE-LINEAR albedo multiplier (review finding 3).

`--looks` additionally renders the same chart at Base / Medium High / High Contrast / Punchy and prints the sat and
R-B of the sunlit-level patch at each, which is the round-9 notes' "ask for AgX - Punchy" recommendation checked
(light_presets already measured Punchy BELOW High Contrast on the hero; this is the same result on a chart).

The view exposure default -2.8331 EV is `light_build.EXPOSURE_BIAS` 1.25 on top of the calibrated -4.0831 and is
what every round-7-onward render log records ("[mat_scene] view exposure -2.8331"); pass --exposure to override.
Scene values are therefore quoted as the radiance the shader actually produces, not as pre-exposure numbers.
"""
import bpy, sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets
import mat_lib as ML

args = common.script_args()
EXPOSURE = float(args[args.index("--exposure") + 1]) if "--exposure" in args else -2.8331
DO_LOOKS = "--looks" in args

# The concrete's own chroma axis: the scene colour whose AgX image lands on the hero's sunlit attic.  Round 9's
# chart used (1.30, 0.80, 0.30) at exposure 0; the same radiance at the shipped exposure is that / 2**EXPOSURE.
AXIS = np.array([1.30, 0.80, 0.30])
LEVELS = [0.08, 0.11, 0.145, 0.19, 0.245, 0.31, 0.40, 0.52, 0.68, 0.90, 1.20, 1.60]   # multiples of AXIS
#            -- chosen to span display luminance ~90 (deep sky-lit shade) to ~230 (the brightest lit stone on the
#               hero); the hero's own operating points are the sunlit attic 189.8, the shaded attic 132.9 and the
#               entablature 132.8.
# column perturbations: (label, per-channel scale vector)
COLS = [("base", (1.00, 1.00, 1.00)),
        ("all+", (1.10, 1.10, 1.10)), ("all-", (0.90, 0.90, 0.90)),
        ("R+", (1.10, 1.00, 1.00)), ("R-", (0.90, 1.00, 1.00)),
        ("G+", (1.00, 1.10, 1.00)), ("G-", (1.00, 0.90, 1.00)),
        ("B+", (1.00, 1.00, 1.10)), ("B-", (1.00, 1.00, 0.90))]
PATCH = 32
LN_STEP = np.log(1.10 / 0.90)

lum = lambda c: 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def build_chart():
    bpy.ops.wm.read_homefile(use_empty=True)
    scene = common.setup_scene()
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False
    scene.render.film_transparent = False
    nx, ny = len(COLS), len(LEVELS)
    scene.render.resolution_x, scene.render.resolution_y = nx * PATCH, ny * PATCH
    scene.render.resolution_percentage = 100
    # sensor_fit must be HORIZONTAL: with the default AUTO, `ortho_scale` maps to the LARGER resolution
    # axis, so a portrait chart would put the patch grid off its own pixel grid and every derivative below would be
    # read from a blend of two patches.
    cam_d = bpy.data.cameras.new("C"); cam_d.type = "ORTHO"
    cam_d.sensor_fit = "HORIZONTAL"; cam_d.ortho_scale = nx
    cam = bpy.data.objects.new("C", cam_d); cam.location = (0, 0, 10)
    scene.collection.objects.link(cam); scene.camera = cam
    scale = 2.0 ** (-EXPOSURE)          # so the patch's DISPLAY level is where we want it after the view exposure
    for j, k in enumerate(LEVELS):
        for i, (_, m) in enumerate(COLS):
            bpy.ops.mesh.primitive_plane_add(size=1.0,
                                             location=(i - (nx - 1) / 2.0, (ny - 1) / 2.0 - j, 0))
            o = bpy.context.object
            mat = bpy.data.materials.new(f"E{j}_{i}")
            mat.use_nodes = True
            nt = mat.node_tree
            nt.nodes.clear()
            em = nt.nodes.new("ShaderNodeEmission")
            c = AXIS * k * np.array(m) * scale
            em.inputs[0].default_value = (float(c[0]), float(c[1]), float(c[2]), 1.0)
            em.inputs[1].default_value = 1.0
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            nt.links.new(em.outputs[0], out.inputs["Surface"])
            o.data.materials.append(mat)
    return scene


def render_at(scene, look, tag):
    """Render the chart at one look and return the (levels, cols, 3) array of display RGB in 0..255."""
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = look
    scene.view_settings.gamma = 1.0
    scene.view_settings.exposure = EXPOSURE
    fp = common.RENDERS / "previews" / "materials" / f"r9b_agx_{tag}.png"
    scene.render.filepath = str(fp)
    scene.render.image_settings.color_depth = "8"
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(fp))
    a = np.asarray(img.pixels[:], dtype=np.float64)
    W, H = scene.render.resolution_x, scene.render.resolution_y
    a = a.reshape(H, W, 4)[::-1, :, :3] * 255.0        # bottom-up, already display-referred
    bpy.data.images.remove(img)
    out = np.zeros((len(LEVELS), len(COLS), 3))
    for j in range(len(LEVELS)):
        for i in range(len(COLS)):
            p = a[j * PATCH + 10:j * PATCH + 22, i * PATCH + 10:i * PATCH + 22]
            out[j, i] = p.reshape(-1, 3).mean(axis=0)
    return out


def transfer(a):
    """(rows of dict) t_lum and t_R/t_G/t_B against each row's display luminance."""
    ci = {c[0]: n for n, c in enumerate(COLS)}
    rows = []
    for j, k in enumerate(LEVELS):
        base = a[j, ci["base"]]
        L = float(lum(base))
        t_lum = float(np.log(lum(a[j, ci["all+"]]) / max(lum(a[j, ci["all-"]]), 1e-6)) / LN_STEP)
        t = {}
        for ch, n in (("r", 0), ("g", 1), ("b", 2)):
            hi = a[j, ci[ch.upper() + "+"]][n]
            lo = a[j, ci[ch.upper() + "-"]][n]
            t[ch] = float(np.log(max(hi, 1e-6) / max(lo, 1e-6)) / LN_STEP)
        mx, mn = base.max(), base.min()
        rows.append(dict(level=k, lum=L, R=float(base[0]), G=float(base[1]), B=float(base[2]),
                         sat=float((mx - mn) / mx) if mx > 0 else 0.0, rb=float(base[0] - base[2]),
                         t_lum=t_lum, t_r=t["r"], t_g=t["g"], t_b=t["b"]))
    return rows


scene = build_chart()
a = render_at(scene, light_presets.LOOK, "shipped")
rows = transfer(a)
print(f"[agx] view_transform AgX  look {scene.view_settings.look!r}  exposure {scene.view_settings.exposure:.4f}  "
      f"(round 9 measured this table at look None = Base Contrast)")
print(f"[agx] {'display RGB':>22s} {'lum':>6s} {'sat':>6s} {'R-B':>7s} | {'t_lum':>6s} {'t_R':>6s} {'t_G':>6s} {'t_B':>6s}")
for r in rows:
    print(f"[agx] {r['R']:6.1f},{r['G']:6.1f},{r['B']:6.1f} {r['lum']:6.1f} {r['sat']:6.3f} {r['rb']:+7.1f} | "
          f"{r['t_lum']:6.3f} {r['t_r']:6.3f} {r['t_g']:6.3f} {r['t_b']:6.3f}")

out = ML.TEX_DIR / "projection" / "agx_transfer.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(dict(
    look=light_presets.LOOK, exposure=EXPOSURE, axis=list(AXIS), levels=LEVELS,
    note="t = d log(display) / d log(scene), central difference over x0.90..x1.10, measured at the shipped look",
    rows=rows), indent=2) + "\n")
print(f"[agx] wrote {out}")

if DO_LOOKS:
    # The round-9 notes recommend asking lighting for `AgX - Punchy` "because it raises chroma".  Compared at the
    # SAME SCENE VALUE that is true, but Punchy also costs most of a stop, and chroma on this chart is mostly a
    # level effect -- so the honest comparison is at a MATCHED DISPLAY LUMINANCE, which is what the hero's own
    # 178-201 window pins.  Each look's sat / R-B is therefore interpolated onto display luminance 189.8, the
    # shipped hero's sunlit attic.
    TARGET_L = 189.8
    print(f"[agx] the four looks compared at MATCHED display luminance {TARGET_L:.1f} (not at matched scene value):")
    for look in ("AgX - Base Contrast", "AgX - Medium High Contrast", "AgX - High Contrast", "AgX - Punchy"):
        try:
            b = render_at(scene, look, look.split(" - ")[1].replace(" ", "_").lower())
        except TypeError:
            print(f"[agx]   {look}: not available in this build")
            continue
        rr = transfer(b)
        L = np.array([r["lum"] for r in rr])
        pick = lambda key: float(np.interp(TARGET_L, L, [r[key] for r in rr]))
        print(f"[agx]   {look:28s} at lum {TARGET_L:.1f}: sat {pick('sat'):.3f}  R-B {pick('rb'):+6.1f}  "
              f"t_lum {pick('t_lum'):.3f}  t_B {pick('t_b'):.3f}   "
              f"(same scene value as the shipped look -> lum {float(np.interp(1.0, LEVELS, L)):.1f})")
