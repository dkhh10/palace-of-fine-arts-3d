"""Gate 0 step 3: albedo + roughness from the node trees, 2K, 16-bit PNG, into the low-poly UV1.

    scripts/blender_run.sh 1800 -- --background export/out/gate0/gate0_set.blend --python export/bake_pbr.py

Bake types used (the brief asks which): Cycles **DIFFUSE with use_pass_color only** (direct and indirect off) for
the albedo, and Cycles **ROUGHNESS** for the roughness - not EMIT. Both are look-independent scene-linear values
read straight out of the Principled BSDF, so no view transform and no light ever touches them. The third channel,
the tangent normal, is step 2's (export/bake_normal.py); it is not re-baked here, only listed in the manifest.

Column and capital bake selected-to-active from their LOD0 twin with the measured cage, so the procedural detail of
the hi-poly surface (the node trees are object-space, there are no UV nodes in MAT_column_rose /
MAT_ornament_concrete) lands on the decimated UV layout. The ground has no hi twin and bakes from itself.
"""
import bpy
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import bake_lib as bl  # noqa: E402

g0.ensure_dirs()
g0.queue_state("running")
scene = bpy.context.scene
g0.apply_final_cycles_checked(scene)
report = {}
tex = g0.OUT / "tex"
ground_name = "GATE0_ground"

JOBS = [
    ("column", f"{g0.LO_COLUMN}_00", g0.COLUMN_HI),
    ("capital", g0.LO_CAPITAL, g0.CAPITAL_HI),
    ("ground", ground_name, None),
]

for key, lo_name, hi_name in JOBS:
    step = g0.Step(f"bake_pbr:{key}")
    lo = bpy.data.objects[lo_name]
    hi = bpy.data.objects[hi_name] if hi_name else None
    cage = 0.0
    dev = None
    if hi is not None:
        dev = bl.deviation(lo, hi)
        cage = round(dev["max"] * 1.25, 4)
    prev = bl.hide_all_but({lo.name} | ({hi.name} if hi else set()))

    alb = bl.bake_image(f"{key}_albedo", colorspace="sRGB", float_buffer=True, fill=(0.0, 0.0, 0.0, 1.0))
    bl.attach_target(lo, alb, g0.UV1)
    bl.select_only(lo, *( [hi] if hi else [] ))
    t_alb = bl.run_bake("DIFFUSE", samples=16, selected_to_active=hi is not None, cage=cage, max_ray=cage,
                        margin=16, use_pass_direct=False, use_pass_indirect=False, use_pass_color=True)
    p_alb = bl.save_png(alb, tex / f"gate0_{key}_albedo.png", depth=16)

    rgh = bl.bake_image(f"{key}_roughness", colorspace="Non-Color", float_buffer=True, fill=(0.5, 0.5, 0.5, 1.0))
    bl.attach_target(lo, rgh, g0.UV1)
    bl.select_only(lo, *( [hi] if hi else [] ))
    t_rgh = bl.run_bake("ROUGHNESS", samples=16, selected_to_active=hi is not None, cage=cage, max_ray=cage,
                        margin=16)
    p_rgh = bl.save_png(rgh, tex / f"gate0_{key}_roughness.png", depth=16)

    bl.restore_hidden(prev)
    bl.detach_targets()
    report[key] = dict(lo=lo_name, hi=hi_name, cage_extrusion_m=cage, deviation_m=dev,
                       albedo=dict(path=str(p_alb), bytes=os.path.getsize(p_alb), bake_s=round(t_alb, 1),
                                   bake_type="DIFFUSE/color-only", stats=bl.stats(alb, "albedo")),
                       roughness=dict(path=str(p_rgh), bytes=os.path.getsize(p_rgh), bake_s=round(t_rgh, 1),
                                      bake_type="ROUGHNESS", stats=bl.stats(rgh, "roughness")))
    step.done(p_alb, p_rgh, cage=cage)

(g0.OUT / "bake_pbr.json").write_text(json.dumps(report, indent=1) + "\n")
man_tex = {}
for k in report:
    man_tex[f"{k}_albedo"] = dict(path=f"tex/gate0_{k}_albedo.png", uv=g0.UV1, colorspace="sRGB",
                                  encoding="16-bit PNG, glTF baseColorTexture")
    man_tex[f"{k}_roughness"] = dict(path=f"tex/gate0_{k}_roughness.png", uv=g0.UV1, colorspace="linear",
                                     encoding="16-bit PNG, glTF metallicRoughness green channel (metallic = 0)")
g0.manifest_merge(textures=man_tex)
g0.queue_state("idle")
print("[gate0] bake_pbr done")
