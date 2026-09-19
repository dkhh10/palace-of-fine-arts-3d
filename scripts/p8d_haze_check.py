"""Phase 8d review-r2 finding 4: does the backdrop's haze albedo lift the palace in CYCLES, and does the 8d
shade term double-darken the hall on top of Cycles' real cast shadow?

    blender --background --python scripts/p8d_haze_check.py -- --blend <scratch.blend> --cam 01 [--no8d] --out <png>

Renders one QA station from a SCRATCH COPY of master_delivery.blend with the delivery look, Cycles, fixed (not
adaptive) samples so the A and B frames are bit-comparable, and optionally with the three terms
`mat_build.backdrop_atmosphere` adds to every MAT_backdrop_* material switched off:

    haze   the Base Color / Roughness / Specular mix toward HAZE_TINT   -> Mix factor 0
    lots   the per-lot albedo spread (world-noise scale + hue shift)    -> VectorMath SCALE 1.0, Hue 0.5
    shade  the palace's own shadow (albedo scale + desaturation)        -> VectorMath SCALE 1.0, Saturation 1.0

Nothing else changes: the 8d base-colour values (the building's desaturation, the skylight's lift, the forest's
albedo) stay in both variants, because the question is about the three ADDED terms only.

The bypass is structural and ASSERTED, never best-effort: `backdrop_atmosphere` always relinks Base Color,
Roughness and Specular IOR Level to its own Mix nodes last, and inserts a known number of scale/hue-sat nodes in
front of them per material (the table below mirrors `apply_backdrop_atmosphere`'s arguments).  Every step checks
the node type it expects and the run aborts if the graph is not what this script thinks it is -- a silently
half-applied bypass would produce a wrong measurement, which is worse than no measurement.
"""
import bpy, sys, os, time

# walking BACK from the haze Mix's A input: shade (hsv sat, scale) then lots (hsv hue, scale), as inserted
STEPS = {
    "MAT_backdrop_building": ["hsv_sat", "scale", "hsv_hue", "scale"],
    "MAT_backdrop_roof":     ["hsv_sat", "scale", "hsv_hue", "scale"],
    "MAT_backdrop_roof_tile": ["hsv_hue", "scale"],
    "MAT_backdrop_skylight": ["hsv_sat", "scale"],
    "MAT_backdrop_asphalt":  ["scale"],
    "MAT_backdrop_lawn":     ["scale"],
    "MAT_backdrop_forest":   ["hsv_hue", "scale"],
    "MAT_backdrop_hill":     ["scale"],
}


def principled(mat):
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            return n
    return None


def unlink(nt, socket):
    for l in list(socket.links):
        nt.links.remove(l)


def bypass_8d():
    total = {"haze": 0, "scale": 0, "hsv": 0, "materials": 0}
    for name, steps in STEPS.items():
        m = bpy.data.materials.get(name)
        if m is None:
            raise SystemExit(f"[haze_check] {name} not in the scratch file - is it the 8d master_delivery?")
        nt = m.node_tree
        b = principled(m)
        assert b is not None, name
        src_a = None
        for inp in ("Base Color", "Roughness", "Specular IOR Level"):
            if inp not in b.inputs:
                continue
            sk = b.inputs[inp]
            if not sk.is_linked:
                continue
            mix = sk.links[0].from_node
            if mix.bl_idname != "ShaderNodeMix":
                raise SystemExit(f"[haze_check] {name}.{inp} is fed by {mix.bl_idname}, expected the haze Mix")
            # ShaderNodeMix carries one socket per data type, ALL named "Factor" / "A" / "B": picking by name
            # alone silently returns the float ones and the RGBA link is missed (that is what aborted the first
            # run).  Select by socket type, matched to the node's data_type.
            want = {"RGBA": "RGBA", "FLOAT": "VALUE", "VECTOR": "VECTOR"}[mix.data_type]
            fac = [i for i in mix.inputs if i.name == "Factor" and i.type == "VALUE"][0]
            if not fac.is_linked:
                raise SystemExit(f"[haze_check] {name}.{inp} haze Mix factor is not linked")
            unlink(nt, fac)
            fac.default_value = 0.0
            total["haze"] += 1
            if inp == "Base Color":
                a_in = [i for i in mix.inputs if i.name == "A" and i.type == want][0]
                src_a = a_in.links[0].from_node if a_in.is_linked else None
        node = src_a
        for step in steps:
            if node is None:
                raise SystemExit(f"[haze_check] {name}: chain ended before step {step}")
            if step == "scale":
                if node.bl_idname != "ShaderNodeVectorMath" or node.operation != "SCALE":
                    raise SystemExit(f"[haze_check] {name}: expected VectorMath/SCALE, got {node.bl_idname}/"
                                     f"{getattr(node, 'operation', '')}")
                sk = node.inputs["Scale"]
                unlink(nt, sk)
                sk.default_value = 1.0
                total["scale"] += 1
                nxt = node.inputs[0]
            else:
                if node.bl_idname != "ShaderNodeHueSaturation":
                    raise SystemExit(f"[haze_check] {name}: expected HueSaturation, got {node.bl_idname}")
                sk = node.inputs["Hue" if step == "hsv_hue" else "Saturation"]
                unlink(nt, sk)
                sk.default_value = 0.5 if step == "hsv_hue" else 1.0
                total["hsv"] += 1
                nxt = node.inputs["Color"]
            node = nxt.links[0].from_node if nxt.is_linked else None
        total["materials"] += 1
    print(f"[haze_check] 8d terms bypassed: {total}")


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    blend = a[a.index("--blend") + 1]
    cam = a[a.index("--cam") + 1]
    out = a[a.index("--out") + 1]
    no8d = "--no8d" in a
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 32
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    vs = scene.view_settings
    print(f"[haze_check] delivery look as found: view_transform={vs.view_transform!r} look={vs.look!r} "
          f"exposure={vs.exposure:.4f}")
    assert "AgX" in vs.view_transform, vs.view_transform
    if no8d:
        bypass_8d()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import light_presets
    light_presets.apply_final_cycles(scene, samples=samples, time_limit=0)
    scene.cycles.use_adaptive_sampling = False          # A and B must spend the same samples everywhere
    scene.cycles.samples = samples
    cams = [o for o in bpy.data.objects if o.type == "CAMERA" and f"_qa_{cam}_" in o.name]
    assert len(cams) == 1, [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    scene.camera = cams[0]
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.filepath = out
    scene.render.image_settings.file_format = "PNG"
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[haze_check] {'B (8d OFF)' if no8d else 'A (as merged)'} cam{cam} {samples} spp -> {out} "
          f"in {time.time() - t0:.1f}s")


main()
