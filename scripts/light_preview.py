"""Lighting previews: temp scene = placeholder blockout (or ARCH/ENV when present) + the LIGHT rig, world, look and
compositor from assets/lighting.blend; renders the QA cameras in Eevee and a Cycles hero into renders/previews/lighting/.

    blender -b --python scripts/light_preview.py                       # Eevee QA set + Cycles 128 spp hero
    blender -b --python scripts/light_preview.py -- --hero-only        # just the Cycles hero
    blender -b --python scripts/light_preview.py -- --eevee-only
    blender -b --python scripts/light_preview.py -- --tag evening      # name tag for the outputs
    blender -b --python scripts/light_preview.py -- --look "AgX - Punchy" --exposure -3.5   # A/B overrides
    blender -b --python scripts/light_preview.py -- --sky-sweep        # world only through the hero camera at several
                                                                        # aerosol densities (look test against ref 169)
Outputs are compared with docs/reference_sheet.md ref 169 via scripts/qa_compare.py by the caller.
"""
import bpy, os, sys, math, time, json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp

OUT = common.RENDERS / "previews" / "lighting"
PLACEHOLDER = common.ASSETS / "placeholder_blockout.blend"


def arg(args, key, default=None, cast=str):
    return cast(args[args.index(key) + 1]) if key in args else default


def build_temp_scene():
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    s = bpy.context.scene
    linked = []
    for key in ("ARCH", "ENV", "ORN"):
        path = common.ASSET_FILES[key]
        if path.exists():
            c = common.link_collection(path, key, link=True)
            if c:
                linked.append(key)
    if "ARCH" not in linked:
        c = common.link_collection(PLACEHOLDER, "PLACEHOLDER", link=True)
        if c:
            linked.append("PLACEHOLDER")
    for name in ("PLACEHOLDER_LIGHT",):        # the placeholder's own sun/world must not double-light the scene
        pc = bpy.data.collections.get(name)
        if pc:
            for lc in s.collection.children:
                pass
            pc.hide_render = True
            vl_layer = s.view_layers[0].layer_collection
            def _exclude(lc):
                if lc.collection.name == name:
                    lc.exclude = True
                for ch in lc.children:
                    _exclude(ch)
            _exclude(vl_layer)
    lp.apply_rig(s)
    print("[light_preview] linked:", linked, "world:", s.world.name, "exposure:", round(s.view_settings.exposure, 2))
    return s


def render_cams(s, cams, engine, tag, res=(1280, 720), cycles_samples=128):
    OUT.mkdir(parents=True, exist_ok=True)
    ts = common.timestamp()
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "8"
    outs = []
    for cam in cams:
        s.camera = cam
        short = cam.name.replace("CAM_qa_", "")
        fp = OUT / f"{ts}_{short}_{engine.lower()}{('_' + tag) if tag else ''}.png"
        s.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t
        print(f"[light_preview] {engine} {fp.name} {dt:.1f}s")
        outs.append((fp, dt))
    return outs


def sky_sweep(s, values=(0.5, 1.0, 2.0, 3.0), res=(1280, 720)):
    """World only (all geometry hidden) through the hero camera, one image per aerosol density."""
    cams = common.qa_cameras(s)
    hero = [c for c in cams if "01_lagoon_hero" in c.name][0]
    for o in s.objects:
        if o.type == "MESH":
            o.hide_render = True
    world = s.world
    if world.library:      # linked worlds are read-only: make a local copy for the sweep
        world = world.copy()
        s.world = world
    sky = world.node_tree.nodes["SKY"]
    lp.apply_preview_eevee(s, samples=8)
    outs = []
    for a in values:
        sky.aerosol_density = a
        outs += render_cams(s, [hero], "EEVEE", f"skysweep_aerosol{a:g}", res=res)
    return outs


if __name__ == "__main__":
    args = common.script_args()
    tag = arg(args, "--tag", "")
    s = build_temp_scene()
    if "--look" in args:
        s.view_settings.look = arg(args, "--look")
    if "--exposure" in args:
        s.view_settings.exposure = arg(args, "--exposure", cast=float)
    if "--sky-sweep" in args:
        sky_sweep(s)
        sys.exit(0)
    cams = common.qa_cameras(s)
    hero = [c for c in cams if "01_lagoon_hero" in c.name]
    results = {}
    if "--hero-only" not in args:
        lp.apply_preview_eevee(s, samples=32)
        results["eevee"] = render_cams(s, cams, "EEVEE", tag)
    if "--eevee-only" not in args:
        lp.apply_final_cycles(s, samples=arg(args, "--samples", 128, int))
        s.cycles.adaptive_threshold = 0.05
        results["cycles"] = render_cams(s, hero, "CYCLES", tag)
    print("[light_preview] done", {k: [(str(p.name), round(t, 1)) for p, t in v] for k, v in results.items()})
