"""QA deliverables / viewport inspection of an EXISTING master.blend (QA / Critic owned; read-only, never saves).

    blender -b --python scripts/qa_inspect.py [-- --blend master.blend]

Prints one JSON line: open time, object counts, LOD1 triangle estimate (sum of mesh loop triangles over objects visible
at LOD1, instanced collections counted once per instance), flythrough objects, light probes, Cycles / Eevee / colour
management settings as saved in the file. Exits by itself.
"""
import bpy, sys, os, time, json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
blend = Path(args[args.index("--blend") + 1]) if "--blend" in args else common.ROOT / "master.blend"

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
t_open = time.time() - t0
sc = bpy.context.scene
objs = bpy.data.objects


def mesh_tris(me):
    return sum(max(0, p.loop_total - 2) for p in me.polygons)


cache = {}
def tris_of(ob):
    if ob.type != "MESH" or ob.data is None:
        return 0
    if ob.data.name not in cache:
        cache[ob.data.name] = mesh_tris(ob.data)
    return cache[ob.data.name]


def visible_lod1(name):
    return not (name.endswith("_LOD0") or name.endswith("_LOD2"))


tri_direct = 0
tri_inst = 0
n_inst = 0
for ob in objs:
    if ob.hide_viewport:
        continue
    if ob.instance_type == "COLLECTION" and ob.instance_collection:
        n_inst += 1
        tri_inst += sum(tris_of(o) for o in ob.instance_collection.all_objects if visible_lod1(o.name) and not o.hide_viewport)
    elif visible_lod1(ob.name):
        tri_direct += tris_of(ob)

fly = sorted(o.name for o in objs if "flythrough" in o.name.lower())
curves = [o.name for o in objs if o.type == "CURVE"]
probes = sorted(o.name for o in objs if o.type == "LIGHT_PROBE")
cams = sorted(o.name for o in objs if o.type == "CAMERA")
cy = sc.cycles
ee = sc.eevee
vs = sc.view_settings
info = dict(
    blend=str(blend.name), size_mb=round(blend.stat().st_size / 1e6, 1), open_s=round(t_open, 2),
    objects=len(objs), collection_instances=n_inst, materials=len(bpy.data.materials),
    placeholder_materials=[m.name for m in bpy.data.materials if "placeholder" in m.name.lower()],
    lod1_tris_direct_M=round(tri_direct / 1e6, 2), lod1_tris_instanced_M=round(tri_inst / 1e6, 2),
    lod1_tris_total_M=round((tri_direct + tri_inst) / 1e6, 2),
    flythrough_objects=fly, curve_objects=curves[:10], light_probes=probes, cameras=cams,
    engine=sc.render.engine, res=[sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage],
    cycles=dict(device=cy.device, samples=cy.samples, adaptive=cy.use_adaptive_sampling,
                adaptive_threshold=cy.adaptive_threshold, adaptive_min=cy.adaptive_min_samples,
                denoise=cy.use_denoising, denoiser=cy.denoiser, time_limit=cy.time_limit),
    eevee=dict(taa_samples=ee.taa_samples, taa_render_samples=ee.taa_render_samples,
               raytracing=getattr(ee, "use_raytracing", None), shadow_ray_count=getattr(ee, "shadow_ray_count", None)),
    color=dict(view_transform=vs.view_transform, look=vs.look, exposure=round(vs.exposure, 4), gamma=vs.gamma),
    frame_range=[sc.frame_start, sc.frame_end], fps=sc.render.fps,
    active_camera=sc.camera.name if sc.camera else None,
)
print("[qa_inspect] " + json.dumps(info))
