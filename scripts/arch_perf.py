"""ARCH performance audit: base vs evaluated triangles, split by LOD tag and by bevel modifier.

    blender -b assets/architecture.blend --background --python scripts/arch_perf.py
    blender -b assets/architecture.blend --background --python scripts/arch_perf.py -- --strip-lod12
        (removes the BEVEL modifier from _LOD1 / _LOD2 objects and saves; LOD0 keeps its bevels for Cycles)

`arch_stats.json`'s tris_LOD* are BASE polygon counts: they do not see the bevel modifiers, which are what the
viewport and the renderer actually evaluate. This script reports both.
"""
import bpy, sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
dg = bpy.context.evaluated_depsgraph_get()


def tris(mesh):
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


def lod_of(name):
    for k in ("_LOD0", "_LOD1", "_LOD2"):
        if name.endswith(k) or k in name:
            return k[1:]
    return "none"


ALL = "--all" in args          # group every object by name prefix (use on master.blend)
rows = collections.defaultdict(lambda: dict(objs=0, base=0, ev=0, bev=0, bev_objs=0))
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    if ALL:
        vis = (not o.hide_render) if "--render" in args else (not o.hide_viewport)
        if not vis:
            continue
        grp = o.name.split("_")[0][:12]
    else:
        if not (o.name.startswith("ARCH_") or o.name.startswith("PH_")):
            continue
        grp = ("PH" if o.name.startswith("PH_") else lod_of(o.name))
    r = rows[grp]
    r["objs"] += 1
    base = sum(max(len(p.vertices) - 2, 1) for p in o.data.polygons)
    r["base"] += base
    has_bev = any(m.type == "BEVEL" for m in o.modifiers)
    ev = tris(o.evaluated_get(dg).to_mesh()) if o.modifiers else base
    if o.modifiers:
        o.evaluated_get(dg).to_mesh_clear()
    r["ev"] += ev
    if has_bev:
        r["bev_objs"] += 1
        r["bev"] += ev - base

print("\n[perf] ARCH triangles (base = saved mesh, ev = evaluated with modifiers on the VIEWPORT depsgraph:\n       a modifier with show_viewport=False is not counted here even though the render still has it)")
print(f"{'group':6} {'objs':>6} {'base tris':>12} {'eval tris':>12} {'bevel adds':>12} {'bevel objs':>11}")
tot = dict(objs=0, base=0, ev=0, bev=0, bev_objs=0)
order = sorted(rows, key=lambda k: -rows[k]["ev"]) if ALL else ["LOD0", "LOD1", "LOD2", "none", "PH"]
for k in order:
    r = rows.get(k)
    if not r:
        continue
    print(f"{k:6} {r['objs']:6d} {r['base']:12,d} {r['ev']:12,d} {r['bev']:12,d} {r['bev_objs']:11d}")
    for f in tot:
        tot[f] += r[f]
print(f"{'TOTAL':6} {tot['objs']:6d} {tot['base']:12,d} {tot['ev']:12,d} {tot['bev']:12,d} {tot['bev_objs']:11d}")
if not ALL:
    render_set = rows["LOD0"]["ev"] + rows["none"]["ev"]
    viewport_set = rows["LOD1"]["ev"] + rows["none"]["ev"]
    print(f"[perf] ARCH render set  (LOD0 + un-LODed): {render_set:,d} evaluated tris")
    print(f"[perf] ARCH viewport set (LOD1 + un-LODed): {viewport_set:,d} evaluated tris")

if "--strip-lod12" in args:
    n = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith("ARCH_"):
            continue
        if lod_of(o.name) not in ("LOD1", "LOD2"):
            continue
        for m in [m for m in o.modifiers if m.type == "BEVEL"]:
            o.modifiers.remove(m)
            n += 1
    print(f"[perf] removed {n} BEVEL modifiers from LOD1/LOD2 objects")
    common.save_blend(common.ASSETS / "architecture.blend")

# ----------------------------------------------------------------------------- timing / bevel policy
if "--time" in args:
    import time
    import qa_cameras
    scene = common.setup_scene()
    qa_cameras.ensure(scene)
    common.configure_eevee(scene, samples=int(opt_samples) if (opt_samples := (args[args.index("--samples") + 1] if "--samples" in args else "16")) else 16)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.filepath = "/tmp/arch_perf_time.png"
    bevels = [m for o in bpy.data.objects if o.type == "MESH" for m in o.modifiers if m.type == "BEVEL"]
    scene.camera = bpy.data.objects["CAM_qa_01_lagoon_hero"]
    bpy.ops.render.render(write_still=False)      # warm-up: the first Eevee render pays the shader compile
    for label, on in (("bevels OFF", False), ("bevels ON", True), ("bevels OFF", False), ("bevels ON", True)):
        for m in bevels:
            m.show_render = on
        for cname in ("CAM_qa_01_lagoon_hero", "CAM_qa_05_south_lawn"):
            cam = bpy.data.objects.get(cname)
            if cam is None:
                print("[perf] no camera", cname)
                continue
            scene.camera = cam
            t = time.time()
            bpy.ops.render.render(write_still=False)
            print(f"[perf] eevee {cname[7:13]} {label}: {time.time() - t:.1f} s")
    for m in bevels:
        m.show_render = True

if "--bevel-viewport-off" in args:
    # The 685 bevelled ARCH objects carry no LOD suffix, so they are in BOTH the viewport (LOD1) set and the render
    # (LOD0) set: there is no _LOD1 copy to strip. The equivalent of "bevel on LOD0 only" is therefore
    # show_viewport = False / show_render = True -- the viewport loses the 261 k bevel triangles, Cycles and Eevee
    # keep every arris the QA-02-3 edge-wear mask needs.
    n = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith("ARCH_"):
            continue
        for m in o.modifiers:
            if m.type == "BEVEL":
                m.show_viewport, m.show_render = False, True
                n += 1
    print(f"[perf] {n} ARCH bevel modifiers set to render-only (show_viewport=False)")
    common.save_blend(common.ASSETS / "architecture.blend")
