"""QA round renderer (QA / Critic owned). Renders an EXISTING master.blend from the fixed QA cameras; never edits assets.

    blender -b --python scripts/qa_render_round.py -- --round 01 --eevee            # six cams, Eevee 1280x720, 32 spp, LOD1
    (the Cycles pass is "--final", not "--cycles": Blender prefix-matches --cycles-* even after "--")
    blender -b --python scripts/qa_render_round.py -- --round 01 --final [--samples 128] [--res 1920 1080] [--cams 01]
    blender -b --python scripts/qa_render_round.py -- --round 01 --eevee --cams 01 02   # subset

Outputs: renders/previews/qa/round<NN>_<cam>.png (Eevee) and round<NN>_<cam>_cycles.png (Cycles). The timestamped
files that common.render_previews writes are renamed to the round names (no duplicates in the repo); those are what
qa_compare.py consumes. Run the two passes as separate Blender invocations so each stays inside a foreground timeout.
"""
import bpy, sys, os, time, shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    vals = args[i:i + n]
    return vals[0] if n == 1 else vals


ROUND = arg("--round", "01")
BLEND = Path(arg("--blend", str(common.ROOT / "master.blend")))
CAMS = arg("--cams", None, n=6)
if CAMS:
    CAMS = [c for c in CAMS if not c.startswith("--")]
    CAMS = [f"_{c}_" for c in CAMS]
SAMPLES = int(arg("--samples", 128))
RES = [int(v) for v in arg("--res", ["1920", "1080"], n=2)]
OUT_DIR = common.RENDERS / "previews" / "qa"
OUT_DIR.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
print(f"[qa_render] opened {BLEND.name} in {time.time() - t0:.1f}s; objects {len(bpy.data.objects)}")
scene = bpy.context.scene

if not any(o.name.startswith("CAM_qa_") for o in bpy.data.objects):
    qa_cameras.ensure(scene)
    print("[qa_render] QA cameras were missing; recreated")


def round_name(fp, suffix=""):
    """<ts>_<cam>[_tag].png  ->  round<NN>_<cam><suffix>.png"""
    short = fp.stem.split("_", 2)[2] if fp.stem.count("_") >= 2 else fp.stem
    short = short.replace("_round" + ROUND, "")
    return OUT_DIR / f"round{ROUND}_{short}{suffix}.png"


if "--eevee" in args:
    # Lead decision (round 02 -> 03): the Eevee preview pass renders LOD1, not LOD0. The 2-7x slowdown between
    # rounds 01 and 02 was the LOD0 *render* set (ORN instances 26.7 M + ENV 17.9 M tris), not new geometry.
    # The --final Cycles pass below is left at LOD0 (render=0), which is what the deliverable finals use.
    common.set_lod(viewport=1, render=1)
    print("[qa_render] eevee pass: LOD1 for both viewport and render")
    try:
        import light_presets
        light_presets.apply_preview_eevee(scene, samples=32)
    except Exception as e:
        print("[qa_render] apply_preview_eevee failed, falling back to common.configure_eevee:", e)
    outs = common.render_previews("qa", cameras=CAMS, res=(1280, 720), samples=32, tag=f"round{ROUND}")
    for fp in outs:
        dst = round_name(fp)
        shutil.move(fp, dst)
        print(f"[qa_render] -> {dst.name}")

if "--final" in args:
    import light_presets
    light_presets.apply_final_cycles(scene, samples=SAMPLES, time_limit=float(arg("--time-limit", 0.0)))
    common.setup_scene(scene)
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_x, scene.render.resolution_y = RES
    cams = [o for o in bpy.data.objects if o.name.startswith("CAM_qa_")]
    if CAMS:
        cams = [c for c in cams if any(k in c.name for k in CAMS)]
    for cam in sorted(cams, key=lambda c: c.name):
        scene.camera = cam
        short = cam.name.replace("CAM_qa_", "")
        ts = common.timestamp()
        fp = OUT_DIR / f"{ts}_{short}_round{ROUND}_cycles{SAMPLES}.png"
        scene.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[qa_render] cycles {short} {RES[0]}x{RES[1]} {SAMPLES} spp in {time.time() - t:.1f}s")
        dst = OUT_DIR / f"round{ROUND}_{short}_cycles.png"
        shutil.move(fp, dst)
        print(f"[qa_render] -> {dst.name}")

print(f"[qa_render] done in {time.time() - t0:.1f}s")
