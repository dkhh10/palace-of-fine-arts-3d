"""Gate 1 step 2: ONE ORN prototype's hi (LOD0) -> lo tangent normal map + AO. One Blender per job.

    scripts/blender_run.sh 900 -- --background export/out/gate1/gate1_set.blend \
        --python export/bake_orn.py -- --job orn_capital_rotunda_v2

Driven by export/bake_queue.sh over export/out/gate1/bake_jobs.json; never start it by hand while another
registered Blender is alive (the queue enforces that, see export/bake_queue.sh).

Geometry note. gate1_set.blend holds the exported prototype mesh (EXPM_<proto>) placed N times at the real
instance transforms, and its hi twin (EXPHI_<proto>) once, at identity, in EXP_ORN_HI. Both meshes are in the
SAME prototype-local space, so the bake pair is made here: a throw-away lo object at identity over the hi twin.
Everything else is hidden from the rays, so no neighbour can bleed into the AO.
"""
import bpy
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
import bake_lib as bl  # noqa: E402

argv = g0.script_argv()
job_id = argv[argv.index("--job") + 1]
jobs = json.loads((g1.OUT / "bake_jobs.json").read_text())
job = next(j for j in jobs["jobs"] if j["id"] == job_id)
g1.ensure_dirs()

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "GPU"
scene.cycles.use_denoising = False
scene.cycles.use_adaptive_sampling = False
step = g0.Step(f"bake_orn:{job_id}")

lo_me = bpy.data.meshes[job["lo"]]
hi = bpy.data.objects[job["hi"]]
hi.matrix_world.identity()
lo = bpy.data.objects.new(f"BAKE_LO_{job_id}", lo_me)
bpy.context.scene.collection.objects.link(lo)
lo.matrix_world.identity()
bpy.context.view_layer.update()

prev = bl.hide_all_but({lo.name, hi.name})
dev = bl.deviation(lo, hi)
cage = round(dev["max"] * 1.25, 4)
size = int(job["size"])

nrm = bl.bake_image(f"{job_id}_normal", size=size, colorspace="Non-Color", float_buffer=True,
                    fill=(0.5, 0.5, 1.0, 1.0))
bl.attach_target(lo, nrm, g1.UV1)
bl.select_only(lo, hi)
t_n = bl.run_bake("NORMAL", samples=4, selected_to_active=True, cage=cage, max_ray=cage, margin=16)
p_n = bl.save_png(nrm, g1.TEX / os.path.basename(job["normal"]), depth=16)

ao = bl.bake_image(f"{job_id}_ao", size=size, colorspace="Non-Color", float_buffer=True, fill=(1.0, 1.0, 1.0, 1.0))
bl.attach_target(lo, ao, g1.UV1)
bl.select_only(lo, hi)
vis = bl.set_ray_visibility(lo, False)      # the lo must not occlude its own AO rays (Gate 0 finding)
t_a = bl.run_bake("AO", samples=128, selected_to_active=True, cage=cage, max_ray=cage, margin=16)
bl.restore_ray_visibility(lo, vis)
p_a = bl.save_png(ao, g1.TEX / os.path.basename(job["ao"]), depth=8)

bl.restore_hidden(prev)
bl.detach_targets()

rec = dict(id=job_id, prototype=job["prototype"], lo=job["lo"], hi=job["hi"], size=size,
           tris=job["tris"], src_tris=job["src_tris"], placements=job["placements"],
           deviation_m=dev, cage_extrusion_m=cage,
           normal=dict(path=str(p_n), bytes=os.path.getsize(p_n), bake_s=round(t_n, 1), stats=bl.stats(nrm)),
           ao=dict(path=str(p_a), bytes=os.path.getsize(p_a), bake_s=round(t_a, 1), stats=bl.stats(ao)),
           finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
(g1.OUT / "bake" ).mkdir(parents=True, exist_ok=True)
(g1.OUT / "bake" / f"{job_id}.json").write_text(json.dumps(rec, indent=1) + "\n")
step.done(p_n, p_a, cage=cage, dev_max=dev["max"], normal_s=round(t_n, 1), ao_s=round(t_a, 1))
