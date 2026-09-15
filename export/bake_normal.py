"""Gate 0 step 2: hi (LOD0) -> lo tangent-space normal map + AO, 2K, from gate0_set.blend.

    scripts/blender_run.sh 1800 -- --background export/out/gate0/gate0_set.blend --python export/bake_normal.py

The cage extrusion is MEASURED, not guessed: for every low-poly vertex the distance to the nearest point on the
hi-poly surface is computed with a BVH tree; cage_extrusion = 1.25 x that maximum (and max_ray_distance the same),
printed per asset. The ground has no hi/lo pair, so its normal map is a plain (not selected-to-active) bake of its
own shading normal, which captures MAT_concrete_podium's procedural bump.
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
lights = g0.apply_final_cycles_checked(scene)
scene.cycles.use_denoising = False
report = {}
tex = g0.OUT / "tex"

PAIRS = [
    ("column", f"{g0.LO_COLUMN}_00", g0.COLUMN_HI),
    ("capital", g0.LO_CAPITAL, g0.CAPITAL_HI),
]

for key, lo_name, hi_name in PAIRS:
    step = g0.Step(f"bake_normal:{key}")
    lo = bpy.data.objects[lo_name]
    hi = bpy.data.objects[hi_name]
    dev = bl.deviation(lo, hi)
    cage = round(dev["max"] * 1.25, 4)
    # only this pair is visible, so nothing else can block a cage ray
    prev = bl.hide_all_but({lo.name, hi.name})
    nrm = bl.bake_image(f"{key}_normal", colorspace="Non-Color", float_buffer=True, fill=(0.5, 0.5, 1.0, 1.0))
    bl.attach_target(lo, nrm, g0.UV1)
    bl.select_only(lo, hi)
    t_n = bl.run_bake("NORMAL", samples=4, selected_to_active=True, cage=cage, max_ray=cage, margin=16)
    p_n = bl.save_png(nrm, tex / f"gate0_{key}_normal.png", depth=16)

    ao = bl.bake_image(f"{key}_ao", colorspace="Non-Color", float_buffer=True, fill=(1.0, 1.0, 1.0, 1.0))
    bl.attach_target(lo, ao, g0.UV1)
    bl.select_only(lo, hi)
    vis = bl.set_ray_visibility(lo, False)      # the lo must not occlude its own AO rays
    t_a = bl.run_bake("AO", samples=128, selected_to_active=True, cage=cage, max_ray=cage, margin=16)
    bl.restore_ray_visibility(lo, vis)
    p_a = bl.save_png(ao, tex / f"gate0_{key}_ao.png", depth=8)
    bl.restore_hidden(prev)
    bl.detach_targets()
    report[key] = dict(lo=lo_name, hi=hi_name, deviation_m=dev, cage_extrusion_m=cage,
                       normal=dict(path=str(p_n), bytes=os.path.getsize(p_n), bake_s=round(t_n, 1),
                                   stats=bl.stats(nrm, "normal")),
                       ao=dict(path=str(p_a), bytes=os.path.getsize(p_a), bake_s=round(t_a, 1),
                               stats=bl.stats(ao, "ao")))
    step.done(p_n, p_a, cage=cage, dev_max=dev["max"])

# ground: its own shading normal (no hi/lo pair)
step = g0.Step("bake_normal:ground")
gnd = bpy.data.objects["GATE0_ground"]
prev = bl.hide_all_but({gnd.name})
nrm = bl.bake_image("ground_normal", colorspace="Non-Color", float_buffer=True, fill=(0.5, 0.5, 1.0, 1.0))
bl.attach_target(gnd, nrm, g0.UV1)
bl.select_only(gnd)
t_n = bl.run_bake("NORMAL", samples=4, selected_to_active=False, margin=16)
p_n = bl.save_png(nrm, tex / "gate0_ground_normal.png", depth=16)
ao = bl.bake_image("ground_ao", colorspace="Non-Color", float_buffer=True, fill=(1.0, 1.0, 1.0, 1.0))
bl.attach_target(gnd, ao, g0.UV1)
bl.select_only(gnd)
t_a = bl.run_bake("AO", samples=128, selected_to_active=False, margin=16)
p_a = bl.save_png(ao, tex / "gate0_ground_ao.png", depth=8)
bl.restore_hidden(prev)
bl.detach_targets()
report["ground"] = dict(lo=gnd.name, hi=None, deviation_m=None, cage_extrusion_m=0.0,
                        normal=dict(path=str(p_n), bytes=os.path.getsize(p_n), bake_s=round(t_n, 1),
                                    stats=bl.stats(nrm, "normal")),
                        ao=dict(path=str(p_a), bytes=os.path.getsize(p_a), bake_s=round(t_a, 1),
                                stats=bl.stats(ao, "ao")))
step.done(p_n, p_a)

(g0.OUT / "bake_normal.json").write_text(json.dumps(report, indent=1) + "\n")
g0.manifest_merge(textures={f"{k}_normal": dict(path=f"tex/gate0_{k}_normal.png", uv=g0.UV1, encoding="tangent-normal RGB, 16-bit PNG, Non-Color")
                            for k in report} | {f"{k}_ao": dict(path=f"tex/gate0_{k}_ao.png", uv=g0.UV1, encoding="grey 8-bit PNG, Non-Color")
                                                for k in report})
g0.queue_state("idle")
print("[gate0] bake_normal done")
