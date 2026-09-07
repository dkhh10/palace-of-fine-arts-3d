"""Look development without re-rendering (Lighting & Rendering specialist), for QA-01-12.

Exposure, the AgX look and the view transform all act AFTER the compositor, so one 32-bit EXR of the composited hero
can be re-graded for free. Render once, then sweep:

    blender -b --python scripts/light_lookdev.py -- --render --cam 01 --samples 48 --res 1280 720   # -> EXR
    blender -b --python scripts/light_lookdev.py -- --sweep --exposures -3.9 -3.5 -3.2 --looks "AgX - Base Contrast" "AgX - Punchy"

The sweep writes renders/previews/lighting/lookdev/<cam>_e<EV>_<look>.png, which scripts/light_measure.py samples.
Sky/haze parameter changes are NOT gradeable this way (they change the render); those go through light_preview /
qa_render_round.
"""
import bpy, os, sys, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp

OUT = common.RENDERS / "previews" / "lighting" / "lookdev"


def render_exr(cam="01", samples=48, res=(1280, 720), blend=None, tag=""):
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend or common.ROOT / "master.blend"), load_ui=False)
    s = bpy.context.scene
    lp.apply_final_cycles(s, samples=samples)
    lp.apply_look(s, link=False)
    s.render.resolution_x, s.render.resolution_y = res
    cams = [o for o in bpy.data.objects if o.name.startswith(f"CAM_qa_{cam}")]
    s.camera = cams[0]
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.render.image_settings.exr_codec = "ZIP"
    fp = OUT / f"hero_{cam}{tag}.exr"
    s.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[light_lookdev] {fp.name} {res[0]}x{res[1]} {samples} spp in {time.time() - t:.1f}s")
    return fp


def sweep(exr, exposures, looks, view="AgX", tag=""):
    """Re-grade a rendered EXR: load it, then save it through each (exposure, look) with the scene's view settings."""
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_homefile(use_empty=True)
    s = bpy.context.scene
    img = bpy.data.images.load(str(exr))
    img.colorspace_settings.name = "Linear Rec.709"
    s.view_settings.view_transform = view
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "8"
    outs = []
    for look in looks:
        s.view_settings.look = look
        short = look.replace("AgX - ", "").replace(" ", "").lower() if look != "None" else "none"
        for ev in exposures:
            s.view_settings.exposure = ev
            fp = OUT / f"{Path(exr).stem}{tag}_e{ev:+.2f}_{short}.png"
            img.save_render(filepath=str(fp), scene=s)
            outs.append(fp)
    print(f"[light_lookdev] {len(outs)} grades from {Path(exr).name}")
    for o in outs:
        print("   ", o)
    return outs


if __name__ == "__main__":
    args = common.script_args()

    def arg(k, d=None):
        return args[args.index(k) + 1] if k in args else d

    def arglist(k):
        if k not in args:
            return None
        i = args.index(k) + 1
        out = []
        while i < len(args) and not args[i].startswith("--"):
            out.append(args[i]); i += 1
        return out

    cam = arg("--cam", "01")
    tag = arg("--tag", "")
    exr = OUT / f"hero_{cam}{tag}.exr"
    if "--render" in args:
        res = [int(v) for v in (arglist("--res") or ["1280", "720"])]
        exr = render_exr(cam, int(arg("--samples", 48)), tuple(res), tag=tag)
    if "--sweep" in args:
        exposures = [float(v) for v in (arglist("--exposures") or ["-3.9"])]
        looks = arglist("--looks") or ["AgX - Base Contrast"]
        sweep(exr, exposures, looks, view=arg("--view", "AgX"))
