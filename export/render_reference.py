"""Gate 0 step 7: the Cycles reference frame the viewer must match.

    scripts/blender_run.sh 2400 -- --background export/out/gate0/gate0_set.blend --python export/render_reference.py

1280x720, 64 spp, CAM_qa_01_lagoon_hero, through light_presets.apply_final_cycles (the Phase 5 final preset) and
the saved compositor COMP_scene_golden_hour, at AgX / AgX - High Contrast / exposure -2.833. It renders the SLICE
AS MODELLED - the GATE0_REF hi-poly originals (16 x 14 396-tri columns, the 64 000-tri capital, the pedestal) with
their original node-tree materials - not the decimated export set, because the reference is the ground truth the
whole bake + viewer pipeline is measured against. The compositor's parameters go into the manifest so the viewer
can reproduce bloom / vignette / mist.

Writes renders/web/gate0_cycles_cam01.png.
"""
import bpy
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import bake_lib as bl  # noqa: E402
import qa_cameras  # noqa: E402

argv = g0.script_argv()
SPP = int(argv[argv.index("--spp") + 1]) if "--spp" in argv else 64
RES = (1280, 720)
g0.ensure_dirs()
g0.queue_state("running")
scene = bpy.context.scene
lights = g0.apply_final_cycles_checked(scene, samples=SPP)
scene.cycles.use_adaptive_sampling = False
scene.cycles.time_limit = 0.0
scene.cycles.samples = SPP

# reference = the originals; the decimated export set must not be in frame
ref_names = {o.name for o in bpy.data.collections["GATE0_REF"].objects}
prev = bl.hide_all_but(ref_names)

qa_cameras.ensure(scene)                     # never trust a stale station
cam = bpy.data.objects[g0.HERO_CAM]
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "8"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_management = "FOLLOW_SCENE"
out = g0.WEB_RENDERS / "gate0_cycles_cam01.png"
scene.render.filepath = str(out)[:-4]
t0 = time.time()
bpy.ops.render.render(write_still=True)
dt = time.time() - t0
bl.restore_hidden(prev)

# the compositor's numbers, so the viewer can match bloom / vignette / mist instead of guessing
comp = {}
ctree = getattr(scene, "compositing_node_group", None)
if scene.use_nodes and ctree:
    for n in ctree.nodes:
        entry = dict(type=n.bl_idname, label=n.label)
        for i in n.inputs:
            if hasattr(i, "default_value") and not i.links:
                v = i.default_value
                entry[i.name] = list(v) if hasattr(v, "__len__") else v
        if n.bl_idname == "CompositorNodeGroup" and n.node_tree:
            entry["group"] = n.node_tree.name
            entry["group_inputs"] = {i.name: (list(i.default_value) if hasattr(i.default_value, "__len__")
                                              else i.default_value)
                                     for i in n.inputs if hasattr(i, "default_value")}
        comp[n.name] = entry

rep = dict(path=str(out), bytes=out.stat().st_size, res=list(RES), samples=SPP, render_s=round(dt, 1),
           camera=g0.HERO_CAM, objects_in_frame=sorted(ref_names),
           view=dict(view_transform=scene.view_settings.view_transform, look=scene.view_settings.look,
                     exposure=scene.view_settings.exposure),
           compositor=comp)
(g0.OUT / "render_reference.json").write_text(json.dumps(rep, indent=1) + "\n")
g0.manifest_merge(reference_frame=dict(path="renders/web/gate0_cycles_cam01.png", res=list(RES), samples=SPP,
                                       camera=g0.HERO_CAM, render_s=round(dt, 1),
                                       content="the hi-poly originals with their node-tree materials, the Phase 5 "
                                               "final Cycles preset and the saved compositor"),
                  compositor=comp)
g0.queue_state("idle")
print(f"[gate0] STEP render_reference wall_s={dt:.1f} {out.name}={out.stat().st_size}B spp={SPP}")
