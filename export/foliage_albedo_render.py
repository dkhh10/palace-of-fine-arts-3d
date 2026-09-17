"""Phase 6c round 3 item 1, step 1: the Cycles DIFFUSE COLOUR pass over the QA shrub boxes.

    export/gpu_lock.sh run 900 -- scripts/blender_run.sh 900 -- --background master_delivery.blend \
        --python export/foliage_albedo_render.py -- --spp 16

Read-only on master_delivery.blend (never saved). Writes, per station, an UNCOMPRESSED 32-bit multilayer
EXR carrying Combined (for its alpha), DiffCol and IndexMA:

    export/out/gate3/foliage/albedo_pass_cam02.exr
    export/out/gate3/foliage/albedo_pass_cam05.exr
    export/out/gate3/foliage/albedo_pass.json      (index map, isolation, wall times)

`export/foliage_albedo_check.py` (CPU, no Blender) reads them and writes `albedo_check.json` + the sheet.

WHY THIS EXISTS. QA 16 (docs/qa_round_16.md section 3, "Open 1") measures the viewer's shrub/reed cards at
1.34-1.70x the Cycles reference level at five boxes over four stations, and names EXPORT as the owner on the
grounds that the round-2 tinted albedo pushed the level further out at four of the five. That is an
inference from a *rendered* level, which is albedo x irradiance: it cannot separate a too-bright albedo
(export's bug) from too much light on the card (the viewer's). The Diffuse Colour pass is the albedo alone,
straight out of the renderer whose frame is the reference, so the two can be divided.

THE THREE THINGS THAT MAKE THE NUMBER HONEST.

1. **Isolation.** Every object that carries no foliage-card material is `hide_render`, and the film is
   transparent. Without this, the Combined alpha is 1 everywhere and DiffCol *through* a card's alpha
   cut-out is the albedo of whatever is behind it (Cycles continues the path through a Transparent BSDF and
   writes DiffCol at the first DIFFUSE hit, which is then the lagoon or the colonnade). With it, alpha is
   exactly the cards' own coverage and `alpha > OPAQUE_MIN` selects the texels where a card is solid - which
   is what the brief means by "sample the texture where the cards are opaque".
2. **IndexMA**, from `material.pass_index` assigned here, splits the pass per material. The mapping is not
   trusted on its own: `foliage_albedo_check.py` checks each index's measured HUE against the material's own
   tinted hue, which is an independent dimension (item 40 established the tint fixes the hue), and reports
   the agreement. A wrong index map would show up as a 60 deg hue error on MAT_shrub_dry, the straw one.
3. **Nothing is tone-mapped.** The EXR is scene-linear 32-bit, uncompressed so `gate3_common.read_exr_channels`
   can read it (Blender exposes no way to read a render pass back into Python, and the 5.2 File Output node
   writes multilayer EXR only).

Lighting is left exactly as the Phase 5 final Cycles preset sets it. DiffCol does not depend on it, but
leaving it alone means the Combined layer in the same file is a real (if foliage-only) frame, so the sheet
can show where the boxes fall.
"""
import json
import os
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import qa_cameras  # noqa: E402

SCHEMA = "pfa-phase6c/foliage-albedo-pass/1"
OUT = g0.ROOT / "export" / "out" / "gate3" / "foliage"
RES = (1920, 1080)
CAMS = {"02": "CAM_qa_02_lagoon_ne_threequarter", "05": "CAM_qa_05_south_lawn"}


def main():
    t_start = time.time()
    argv = g0.script_argv()
    spp = int(argv[argv.index("--spp") + 1]) if "--spp" in argv else 16
    assert Path(bpy.data.filepath).name == "master_delivery.blend", \
        f"foliage_albedo_render.py must run on master_delivery.blend, not {bpy.data.filepath!r}"
    OUT.mkdir(parents=True, exist_ok=True)
    par = json.loads((OUT / "params.json").read_text())
    assert par.get("schema") == "pfa-phase6c/foliage-params/1", f"params schema {par.get('schema')!r}"
    cards = sorted(par["materials"])
    assert cards, "params.json lists no card materials"

    # ---- material indices. 0 stays "not a card", so every index is >= 1 and an empty pixel reads 0.
    index_map = {}
    for k, name in enumerate(cards, start=1):
        m = bpy.data.materials.get(name)
        assert m is not None, f"{name} is in params.json but not in master_delivery.blend"
        m.pass_index = k
        index_map[name] = k
    for m in bpy.data.materials:                      # everything else must not collide
        if m.name not in index_map:
            m.pass_index = 0

    # ---- isolation: only objects that carry a card material draw at all.
    # Each kept object also gets a unique `pass_index`, so IndexOB splits the pass per OBJECT. That is what
    # decides whether a material's measured albedo is the texture's or one unlucky instance's: the two terms
    # the glTF cannot carry (`hsv(val)` from Object Info Random, which is per object, and the object-space
    # cluster noise, whose lobes are ~1 m and so are near-constant over one clump) are pinned to 1 in the
    # shipped texture and only average to 1 over many objects IN FRAME.
    keep, hidden, non_mesh = [], 0, 0
    obj_index = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            # a collection-instance empty would still draw its children; nothing else can
            if o.instance_type != "NONE":
                o.hide_render = True
                non_mesh += 1
            continue
        has = any(s.material is not None and s.material.name in index_map for s in o.material_slots)
        o.hide_render = not has
        o.hide_viewport = False
        if has:
            keep.append(o.name)
            o.pass_index = len(keep)
            obj_index[str(len(keep))] = o.name
        else:
            o.pass_index = 0
            hidden += 1
    assert keep, "isolation kept no object: no mesh in master_delivery carries a foliage card material"

    scene = bpy.context.scene
    g0.apply_final_cycles_checked(scene, samples=spp)
    c = scene.cycles
    c.use_adaptive_sampling = False
    c.time_limit = 0.0
    c.samples = spp
    c.use_denoising = False                 # DiffCol is an input pass, never denoised - and this is faster
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    vl = scene.view_layers[0]
    vl.use_pass_combined = True
    vl.use_pass_diffuse_color = True
    vl.use_pass_material_index = True
    vl.use_pass_object_index = True
    # the compositor must not touch the passes (the Phase 5 group is bloom/vignette on the Image only, but
    # it also decides what lands in the file when `use_compositing` is on)
    keep_group = scene.compositing_node_group
    scene.compositing_node_group = None
    scene.render.use_compositing = False
    ims = scene.render.image_settings
    # Blender 5.2 (export/imp_diag_view.py, bake_lm.py): OPEN_EXR_MULTILAYER is only offered once
    # media_type is MULTI_LAYER_IMAGE, and without use_exr_interleave 5.2 writes a MULTI-PART file that
    # gate3_common.read_exr_channels refuses. This has to come AFTER apply_final_cycles_checked, which
    # sets file_format = PNG. No colour-management override: Blender never applies the view transform to
    # an OPEN_EXR save (bake_lm.py:762), so the file is scene-linear.
    ims.media_type = "MULTI_LAYER_IMAGE"
    ims.use_exr_interleave = True
    ims.file_format, ims.color_depth, ims.exr_codec, ims.color_mode = \
        "OPEN_EXR_MULTILAYER", "32", "NONE", "RGBA"   # NONE: read_exr_channels needs uncompressed scanlines

    qa_cameras.ensure(scene)                # never trust a stale station
    rep = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/foliage_albedo_render.py", source_blend=bpy.data.filepath,
               samples=spp, res=list(RES), index_map=index_map,
               alpha_cutoff={k: par["materials"][k]["alpha_cutoff"] for k in cards},
               object_index=obj_index,
               isolation=dict(objects_drawn=len(keep), mesh_objects_hidden=hidden,
                              instancers_hidden=non_mesh,
                              rule="hide_render for every object that carries no card material; "
                                   "film_transparent so the Combined alpha IS the cards' coverage"),
               frames={})
    for tag, cam_name in sorted(CAMS.items()):
        cam = bpy.data.objects.get(cam_name)
        assert cam is not None, f"{cam_name} is not in the scene after qa_cameras.ensure()"
        scene.camera = cam
        fp = OUT / f"albedo_pass_cam{tag}.exr"
        scene.render.filepath = str(fp)[:-4]
        step = g0.Step(f"foliage_albedo:cam{tag}")
        bpy.ops.render.render(write_still=True)
        assert fp.exists(), f"{fp} was not written"
        rep["frames"][tag] = dict(camera=cam_name, exr=fp.name, bytes=fp.stat().st_size,
                                  render_s=round(step.done(fp), 1))
    scene.compositing_node_group = keep_group
    rep["wall_s"] = round(time.time() - t_start, 1)
    (OUT / "albedo_pass.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(f"[foliage_albedo] {len(rep['frames'])} stations, {len(keep)} foliage objects drawn, "
          f"{len(index_map)} card materials -> {OUT / 'albedo_pass.json'}")


if __name__ == "__main__":
    main()
