"""Phase 10 r2 materials renders (water + foliage + column tint), on the worktree's rebuilt master.

    scripts/blender_run.sh 1500 -- --background --python scripts/mat_p10w_sweep.py -- --jobs before|sweep|accept [--tag X]

  before  one Cycles hero 1920x1080, 32 spp, the shipped library (the BEFORE frame of every table)
  sweep   ONE open master, bordered hero frames (full 1920x1080 canvas, black outside the border):
            water   4 cases, rows 740-1080 (the whole lagoon band, 31 % of a frame), 64 spp
            foliage 4 cases, x .39-.74 / y .28-.62 (env_p10_boxes' boxes 1, 1s and 2), 32 spp
            column  4 cases, COL_BOX 680 280 1240 470 padded (the column mask's box), 32 spp
          Each case sets named nodes on LOCAL copies of the linked library materials (make_local), so the library
          and master on disk are untouched; the shipped values are written into scripts/mat_build.py afterwards.
  accept  hero 1920x1080 64 spp + cam05 and cam06 at 1280x720 32 spp, the shipped library, one open master.
Render recipe = scripts/p8_cycles_refs.py (the QA / p10_cycles_refs recipe): light_presets.apply_final_cycles with
time_limit 0, adaptive sampling OFF, fixed samples, GPU + OIDN, the delivery look as saved in master (asserted).
"""
import bpy, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()
JOBS = args[args.index("--jobs") + 1] if "--jobs" in args else "sweep"
TAG = args[args.index("--tag") + 1] if "--tag" in args else ""
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

WATER_BAND = (0, 740, 1920, 1080)
FOLIAGE_WIN = (740, 290, 1440, 680)          # x .385-.75, y .27-.63 of 1920x1080
COLUMN_WIN = (670, 270, 1250, 480)

OLIVE_A, OLIVE_B = (0.170, 0.150, 0.055), (0.190, 0.165, 0.065)
WATER = [   # tag, WATER_ANISO_X, WATER_BUMP_DIST far end, murk A, murk B, WATER_MURK_GAIN near (To Min)
    ("w0", 0.36, 0.170, None, None, 0.15),                  # shipped
    ("w1", 1.00, 0.170, None, None, 0.15),                  # isotropic ripple
    ("w2", 1.00, 0.170, OLIVE_A, OLIVE_B, 0.45),            # isotropic + olive murk at 3x the near gain
    ("w3", 0.60, 0.170, OLIVE_A, OLIVE_B, 0.45),            # half-way stretch + olive murk
]
FOLIAGE = [  # tag, LEAF_SAT, LEAF_GRADE (applied to MAT_leaf_cypress / _pine / _broadleaf)
    ("f0", 1.00, (1.0, 1.0, 1.0)),
    ("f1", 0.50, (2.0, 2.0, 2.6)),
    ("f2", 0.50, (3.0, 3.0, 4.0)),
    ("f3", 0.35, (3.0, 3.0, 4.5)),
]
LEAVES = ("MAT_leaf_cypress", "MAT_leaf_pine", "MAT_leaf_broadleaf")
COLUMN = [   # tag, hue deg, sat, value  (a Hue/Saturation node after PFA_column in MAT_column_rose)
    ("c0", 0.0, 1.00, 1.00),
    ("c1", -4.0, 0.70, 1.35),
    ("c2", -4.0, 0.60, 1.60),
    ("c3", -3.0, 0.55, 1.90),
]
if "--water" in args:          # optional override: --water tag:aniso:far:gain[:olive]  (repeatable)
    WATER = []
    for i, a in enumerate(args):
        if a == "--water":
            f = args[i + 1].split(":")
            ol = len(f) > 4 and f[4] == "olive"
            WATER.append((f[0], float(f[1]), float(f[2]), OLIVE_A if ol else None, OLIVE_B if ol else None, float(f[3])))


def local(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = next(x for x in bpy.data.materials if x.name.split(".")[0] == name)
    if m.library is not None:
        m.make_local()
        m = next(x for x in bpy.data.materials if x.name.split(".")[0] == name and x.library is None)
    return m


def node(m, name):
    n = m.node_tree.nodes.get(name)
    assert n is not None, f"{m.name} has no node {name}"
    return n


def rgba_inputs(n):
    return [s for s in n.inputs if s.type == "RGBA" and s.name in ("A", "B")]


def setup(scene, cam, rx, ry, spp, win=None):
    light_presets.apply_final_cycles(scene, samples=spp, time_limit=0)
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.samples = spp
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = 100
    scene.camera = bpy.data.objects[cam]
    if win:
        scene.render.use_border = True
        scene.render.use_crop_to_border = False
        scene.render.border_min_x, scene.render.border_max_x = win[0] / rx, win[2] / rx
        scene.render.border_min_y, scene.render.border_max_y = 1.0 - win[3] / ry, 1.0 - win[1] / ry
    else:
        scene.render.use_border = False


def render(scene, fname, note=""):
    fp = OUT / fname
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[p10w] {fname} {scene.cycles.samples} spp {note} {time.time() - t:.1f}s", flush=True)


t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
vs = scene.view_settings
print(f"[p10w] master {len(bpy.data.objects)} objects; look {vs.view_transform}/{vs.look}/{vs.exposure:.4f}", flush=True)
assert vs.view_transform == "AgX" and vs.look == "AgX - High Contrast" and abs(vs.exposure + 2.8331) < 1e-3
HERO = "CAM_qa_01_lagoon_hero"

if JOBS == "before":
    setup(scene, HERO, 1920, 1080, 32)
    render(scene, f"p10w_before{TAG}_cam01_32.png")
elif JOBS == "accept":
    setup(scene, HERO, 1920, 1080, 64)
    render(scene, f"p10w_after{TAG}_cam01_64.png")
    for cam, nm in (("CAM_qa_05_", "cam05"), ("CAM_qa_06_", "cam06")):
        c = next(o.name for o in bpy.data.objects if o.name.startswith(cam))
        setup(scene, c, 1280, 720, 32)
        render(scene, f"p10w_after{TAG}_{nm}_32.png")
elif JOBS == "small":          # cam05 / cam06 only (used for the BEFORE pair)
    for cam, nm in (("CAM_qa_05_", "cam05"), ("CAM_qa_06_", "cam06")):
        c = next(o.name for o in bpy.data.objects if o.name.startswith(cam))
        setup(scene, c, 1280, 720, 32)
        render(scene, f"p10w_before{TAG}_{nm}_32.png")
else:
    parts = args[args.index("--parts") + 1].split(",") if "--parts" in args else ["water", "foliage", "column"]
    if "water" in parts:
        w = local("MAT_water_lagoon")
        an, bd, mk, gn = (node(w, "WATER_ANISO_X"), node(w, "WATER_BUMP_DIST"), node(w, "WATER_MURK"),
                          node(w, "WATER_MURK_GAIN"))
        a_in, b_in = rgba_inputs(mk)
        a0, b0 = tuple(a_in.default_value), tuple(b_in.default_value)
        setup(scene, HERO, 1920, 1080, 64, WATER_BAND)
        for tag, aniso, far, ca, cb, gain in WATER:
            an.outputs[0].default_value = aniso
            bd.inputs["To Max"].default_value = far
            a_in.default_value = (*ca, 1.0) if ca else a0
            b_in.default_value = (*cb, 1.0) if cb else b0
            gn.inputs["To Min"].default_value = gain
            render(scene, f"p10w_sweep{TAG}_{tag}.png", f"aniso {aniso} far {far} murk {ca or 'shipped'} gain {gain}")
        an.outputs[0].default_value = 0.36; bd.inputs["To Max"].default_value = 0.170
        a_in.default_value, b_in.default_value = a0, b0; gn.inputs["To Min"].default_value = 0.15
    if "foliage" in parts:
        mats = [local(n) for n in LEAVES]
        setup(scene, HERO, 1920, 1080, 32, FOLIAGE_WIN)
        for tag, sat, grade in FOLIAGE:
            for m in mats:
                node(m, "LEAF_SAT").outputs[0].default_value = sat
                node(m, "LEAF_GRADE").outputs[0].default_value = (*grade, 1.0)
            render(scene, f"p10w_sweep{TAG}_{tag}.png", f"sat {sat} grade {grade}")
    if "column" in parts:
        m = local("MAT_column_rose")
        nt = m.node_tree
        cgn = next(n for n in nt.nodes if n.type == "GROUP" and n.node_tree and n.node_tree.name.startswith("PFA_column"))
        assert nt.nodes.get("P10_colsat") is None, "library already carries a column tint: sweep is relative to it"
        dsts = [l.to_socket for l in cgn.outputs["Color"].links]
        hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.name = "P10W_sweep"
        nt.links.new(cgn.outputs["Color"], hs.inputs["Color"])
        for d in dsts:
            nt.links.new(hs.outputs["Color"], d)
        setup(scene, HERO, 1920, 1080, 32, COLUMN_WIN)
        for tag, hue, sat, val in COLUMN:
            hs.inputs["Hue"].default_value = 0.5 + hue / 360.0
            hs.inputs["Saturation"].default_value = sat
            hs.inputs["Value"].default_value = val
            render(scene, f"p10w_sweep{TAG}_{tag}.png", f"hue {hue} sat {sat} val {val}")
print(f"[p10w] done {JOBS} in {time.time() - t0:.1f}s", flush=True)
