"""Gate 0 step 7: the Cycles reference frame the viewer must match.

    scripts/blender_run.sh 2400 -- --background export/out/gate0/gate0_set.blend --python export/render_reference.py

TWO frames, 1280x720, 64 spp, CAM_qa_01_lagoon_hero, through light_presets.apply_final_cycles (the Phase 5 final
preset) at AgX / AgX - High Contrast / exposure -2.833:
  gate0_cycles_cam01.png         with the saved compositor COMP_scene_golden_hour (the Phase 5 look)
  gate0_cycles_cam01_nocomp.png  with scene.compositing_node_group = None and nothing else changed
The pair separates a colour-pipeline error in the viewer (which shows in both) from the missing haze/bloom/vignette
(which shows only against the composited frame). Blender 5.2 note: scene.use_nodes = False does NOT detach the
compositor; only setting compositing_node_group to None does. It renders the SLICE
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
keep_group = scene.compositing_node_group
frames = {}
for key, group in (("with_compositor", keep_group), ("no_compositor", None)):
    scene.compositing_node_group = group
    name = "gate0_cycles_cam01.png" if key == "with_compositor" else "gate0_cycles_cam01_nocomp.png"
    fp = g0.WEB_RENDERS / name
    scene.render.filepath = str(fp)[:-4]
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    frames[key] = dict(path=f"renders/web/{name}", bytes=fp.stat().st_size, render_s=round(time.time() - t0, 1),
                       compositor=(group.name if group else None))
    print(f"[gate0] STEP render_reference:{key} wall_s={frames[key]['render_s']} {name}={frames[key]['bytes']}B")
scene.compositing_node_group = keep_group
out = g0.WEB_RENDERS / "gate0_cycles_cam01.png"
dt = frames["with_compositor"]["render_s"]
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

rep = dict(frames=frames, path=str(out), bytes=out.stat().st_size, res=list(RES), samples=SPP,
           render_s=round(dt, 1),
           camera=g0.HERO_CAM, objects_in_frame=sorted(ref_names),
           view=dict(view_transform=scene.view_settings.view_transform, look=scene.view_settings.look,
                     exposure=scene.view_settings.exposure),
           compositor=comp)
(g0.OUT / "render_reference.json").write_text(json.dumps(rep, indent=1) + "\n")
# --- the equirect rotation the viewer needs after the Y-up swap, derived, then checked against the image ------
# The equirects are written with u_img = 0.5 + atan2(x_B, y_B)/360 (u = 0.5 is Blender +Y, u grows toward +X).
# Blender -> glTF/three is (x, y, z) -> (x, z, -y), so a three.js direction d corresponds to x_B = d.x, y_B = -d.z:
#     u_img = 0.5 + atan2(d.x, -d.z)/360 = 0.5 + (atan2(d.z, d.x) + 90 deg)/360 = equirectUv(d).u + 0.25
# i.e. three.js' own equirect lookup is 90 deg / 0.25 of the width short, so the environment is rotated +90 deg.
import numpy as np  # noqa: E402
sky_exr = g0.OUT / "sky_camera_4096x2048.exr"
sky_check = {}
if sky_exr.exists():
    im = bpy.data.images.load(str(sky_exr))
    a = np.array(im.pixels[:], dtype=np.float32).reshape(2048, 4096, 4)[:, :, :3]
    bpy.data.images.remove(im)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    # bpy Image.pixels starts at the BOTTOM-left, so numpy row 0 is the file's LAST row.
    bottom_half = float(lum[:1024].mean())      # numpy rows 0..1023  = the file's lower half
    top_half = float(lum[1024:].mean())         # numpy rows 1024..   = the file's upper half
    iy, ix = np.unravel_index(int(np.argmax(lum)), lum.shape)
    sky_check = dict(file_top_half_mean=round(top_half, 4), file_bottom_half_mean=round(bottom_half, 4),
                     top_row_is_zenith=bool(top_half > bottom_half),
                     brightest_v_from_file_top=round(1.0 - (iy + 0.5) / 2048.0, 5),
                     brightest_u=round((ix + 0.5) / 4096.0, 5))

g0.manifest_merge(reference_frame=dict(path="renders/web/gate0_cycles_cam01.png", res=list(RES), samples=SPP,
                                       camera=g0.HERO_CAM, render_s=round(dt, 1),
                                       content="the hi-poly originals with their node-tree materials, the Phase 5 "
                                               "final Cycles preset and the saved compositor"),
                  reference=dict(res=list(RES), samples=SPP, camera=g0.HERO_CAM,
                                 content="the hi-poly GATE0_REF originals with their node-tree materials, "
                                         "light_presets.apply_final_cycles, AgX / AgX - High Contrast / -2.833 EV",
                                 note="score the viewer against no_compositor first: a gap that survives there is "
                                      "the colour/lighting pipeline (exposure, the LUT, the lightmap PI), and a "
                                      "gap that only appears against with_compositor is the missing haze, bloom "
                                      "and vignette listed under `compositor`",
                                 **frames),
                  compositor=comp)
g0.manifest_merge(sky=dict(rotation_deg=90.0, u_offset=0.25,
                           sample_u="u = 0.5 + atan2(d.x, -d.z)/360 for a three.js direction d, which is three.js' "
                                    "built-in equirectUv(d).u + 0.25",
                           sample_v="v = 0.5 - asin(d.y)/180 measured from the FILE'S TOP row (top row = zenith)",
                           rotation_note="apply as a +90 deg rotation about the three.js Y axis on the background "
                                         "and on the PMREM environment (scene.backgroundRotation / "
                                         "environmentRotation), or as a +0.25 offset on u; derived from the "
                                         "Blender-to-glTF swap (x, y, z) -> (x, z, -y), not fitted",
                           orientation_check=sky_check))
g0.queue_state("idle")
print(f"[gate0] STEP render_reference wall_s={dt:.1f} {out.name}={out.stat().st_size}B spp={SPP}")
print("[gate0] sky orientation check:", json.dumps(sky_check))
