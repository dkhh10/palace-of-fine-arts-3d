"""Bake plumbing shared by bake_normal.py / bake_pbr.py / bake_lightmap.py (Gate 0)."""
import bpy
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402


def bake_image(name, size=g0.TEX_SIZE, colorspace="Non-Color", float_buffer=True, alpha=False,
               fill=(0.0, 0.0, 0.0, 1.0)):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=float_buffer, is_data=(colorspace != "sRGB"))
    img.colorspace_settings.name = colorspace
    img.generated_color = fill
    return img


def attach_target(obj, img, uv_name):
    """Add (or reuse) a bake target image node in every material slot of obj and make it active."""
    nodes_added = []
    for slot in obj.data.materials:
        if slot is None:
            continue
        nt = slot.node_tree
        n = nt.nodes.get("BAKE_TARGET")
        if n is None:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.name = "BAKE_TARGET"
            n.label = "BAKE_TARGET"
            n.location = (-900, 700)
        uvn = nt.nodes.get("BAKE_TARGET_UV")
        if uvn is None:
            uvn = nt.nodes.new("ShaderNodeUVMap")
            uvn.name = "BAKE_TARGET_UV"
            uvn.location = (-1100, 700)
        uvn.uv_map = uv_name
        if not n.inputs["Vector"].links:
            nt.links.new(uvn.outputs["UV"], n.inputs["Vector"])
        n.image = img
        n.select = True
        nt.nodes.active = n
        nodes_added.append(n)
    obj.data.uv_layers.active = obj.data.uv_layers[uv_name]
    obj.data.uv_layers[uv_name].active_render = True
    return nodes_added


def detach_targets():
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for nm in ("BAKE_TARGET", "BAKE_TARGET_UV"):
            n = m.node_tree.nodes.get(nm)
            if n:
                m.node_tree.nodes.remove(n)


def select_only(active, *others):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in others:
        o.select_set(True)
    active.select_set(True)
    bpy.context.view_layer.objects.active = active


def hide_all_but(keep_names):
    """hide_render for every mesh object not in keep_names (bake occlusion control). Returns the previous state."""
    prev = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        prev[o.name] = (o.hide_render, o.hide_viewport)
        o.hide_render = o.name not in keep_names
        o.hide_viewport = False
    return prev


def restore_hidden(prev):
    for name, (hr, hv) in prev.items():
        o = bpy.data.objects.get(name)
        if o:
            o.hide_render, o.hide_viewport = hr, hv


def deviation(lo, hi):
    """Measured lo->hi surface distance (world units): min / mean / max over the lo vertices. Drives cage_extrusion."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    hi_ev = hi.evaluated_get(dg)
    me = hi_ev.to_mesh()
    verts = [hi.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    tree = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    hi_ev.to_mesh_clear()
    ds = []
    for v in lo.data.vertices:
        co = lo.matrix_world @ v.co
        loc, nor, idx, d = tree.find_nearest(co)
        if d is not None:
            ds.append(d)
    return dict(n=len(ds), min=round(min(ds), 5), mean=round(sum(ds) / max(len(ds), 1), 5), max=round(max(ds), 5))


def run_bake(bake_type, samples, selected_to_active=False, cage=0.0, max_ray=0.0, margin=16,
             use_pass_direct=False, use_pass_indirect=False, use_pass_color=True, normal_space="TANGENT",
             denoise=False, clear=True):
    scene = bpy.context.scene
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = denoise
    b = scene.render.bake
    b.use_selected_to_active = selected_to_active
    b.cage_extrusion = cage
    b.max_ray_distance = max_ray
    b.margin = margin
    b.margin_type = "ADJACENT_FACES"
    b.use_clear = clear
    b.use_pass_direct = use_pass_direct
    b.use_pass_indirect = use_pass_indirect
    b.use_pass_color = use_pass_color
    if bake_type == "NORMAL":
        b.normal_space = normal_space
        b.normal_r, b.normal_g, b.normal_b = "POS_X", "POS_Y", "POS_Z"
    t = time.time()
    bpy.ops.object.bake(type=bake_type)
    return time.time() - t


def save_png(img, path, depth=16):
    path = str(path)
    img.filepath_raw = path
    img.file_format = "PNG"
    s = bpy.context.scene.render.image_settings
    prev = (s.file_format, s.color_depth, s.color_mode, s.compression)
    s.file_format = "PNG"
    s.color_depth = str(depth)
    s.color_mode = "RGBA" if img.alpha_mode != "NONE" and img.channels == 4 else "RGB"
    s.compression = 90
    img.save()
    s.file_format, s.color_depth, s.color_mode, s.compression = prev
    return path


def stats(img, label=""):
    """min / max / mean per channel of a float image buffer (before any encoding)."""
    import numpy as np
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
    rgb = px[:, :3]
    return dict(label=label, w=img.size[0], h=img.size[1],
                min=[round(float(v), 6) for v in rgb.min(axis=0)],
                max=[round(float(v), 6) for v in rgb.max(axis=0)],
                mean=[round(float(v), 6) for v in rgb.mean(axis=0)],
                nonzero_px=int((rgb.sum(axis=1) > 0).sum()), total_px=int(rgb.shape[0]))


RAY_VIS = ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission",
           "visible_volume_scatter", "visible_shadow")


def set_ray_visibility(obj, value):
    """Turn an object's ray visibility on/off and return the previous state.

    The AO bake needs this: in a selected-to-active bake the low-poly target sits on the same surface as the
    hi-poly source, so if it stays ray-visible it occludes every AO ray and the map bakes black (measured: mean
    0.028 on the column before this was added)."""
    prev = {}
    for a in RAY_VIS:
        if hasattr(obj, a):
            prev[a] = getattr(obj, a)
            setattr(obj, a, value)
    return prev


def restore_ray_visibility(obj, prev):
    for a, v in prev.items():
        setattr(obj, a, v)


# ---------------------------------------------------------------- Gate 2 additions
SENTINEL = -1.0


def fill_sentinel(img, value=SENTINEL):
    """Write a value no bake can produce into every texel, so the texels the UV islands never touch are
    identifiable afterwards. Gate 0 measured its statistics over the whole map, so an atlas that covers 40 %
    of its image reported the fill colour as if it were baked data. Bake with use_clear=False after this."""
    import numpy as np
    n = img.size[0] * img.size[1] * 4
    a = np.full(n, float(value), dtype=np.float32)
    a[3::4] = 1.0
    img.pixels.foreach_set(a)


def masked_stats(img, label="", sentinel=SENTINEL):
    """min / max / mean / std per channel over the COVERED texels only, plus the coverage fraction."""
    import numpy as np
    px = np.asarray(img.pixels[:], dtype=np.float32).reshape(-1, 4)
    rgb = px[:, :3]
    # strict: a texel only partly covered by an island comes back as a blend of the bake and the sentinel, so
    # ANY negative channel means the texel is contaminated, not baked data (measured: a -0.5 fringe around every
    # island when the threshold was sentinel/2).
    m = rgb.min(axis=1) > -1e-4
    cov = rgb[m] if m.any() else rgb[:0]
    if cov.size == 0:
        return dict(label=label, w=img.size[0], h=img.size[1], coverage=0.0, covered_px=0,
                    total_px=int(rgb.shape[0]), min=None, max=None, mean=None, std=None)
    return dict(label=label, w=img.size[0], h=img.size[1],
                coverage=round(float(m.mean()), 5), covered_px=int(m.sum()), total_px=int(rgb.shape[0]),
                min=[round(float(v), 6) for v in cov.min(axis=0)],
                max=[round(float(v), 6) for v in cov.max(axis=0)],
                mean=[round(float(v), 6) for v in cov.mean(axis=0)],
                std=[round(float(v), 6) for v in cov.std(axis=0)])


def flood_sentinel(img, fill_rgb, sentinel=SENTINEL):
    """Replace the untouched texels with a constant (the covered mean). Keeps the mip chain and the UASTC
    encoder from pulling a sentinel into the islands' edge blocks."""
    import numpy as np
    px = np.asarray(img.pixels[:], dtype=np.float32).reshape(-1, 4)
    m = px[:, :3].min(axis=1) <= -1e-4
    if m.any():
        px[m, 0], px[m, 1], px[m, 2], px[m, 3] = fill_rgb[0], fill_rgb[1], fill_rgb[2], 1.0
        img.pixels.foreach_set(px.reshape(-1))
    return int(m.sum())


def resize_copy(img, name, size):
    """Box-filtered copy of a float image at `size` x `size`, plus the RMS error of that reduction."""
    import bpy
    import numpy as np
    w, h = img.size
    px = np.asarray(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    f = w // size
    small = px.reshape(h // f, f, w // f, f, 4).mean(axis=(1, 3))
    back = np.repeat(np.repeat(small, f, axis=0), f, axis=1)
    rms = float(np.sqrt(((back[..., :3] - px[..., :3]) ** 2).mean()))
    out = bpy.data.images.get(name)
    if out:
        bpy.data.images.remove(out)
    out = bpy.data.images.new(name, size, size, alpha=False, float_buffer=True, is_data=img.is_float and True)
    out.colorspace_settings.name = img.colorspace_settings.name
    out.pixels.foreach_set(small.reshape(-1))
    return out, round(rms, 6)


def emit_bsdf_input(mat, socket_name):
    """Route a Principled input into an Emission shader so a plain EMIT bake reads it back (Cycles has no
    METALLIC bake type). Returns the state restore_emit() needs."""
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    out = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial"), None)
    if bsdf is None or out is None or not out.inputs["Surface"].links:
        return None
    emis = nt.nodes.new("ShaderNodeEmission")
    emis.name = "BAKE_EMIT_PROBE"
    src = bsdf.inputs[socket_name]
    if src.links:
        nt.links.new(src.links[0].from_socket, emis.inputs["Color"])
    else:
        v = src.default_value
        if hasattr(v, "__len__"):                      # Base Color is an RGBA socket, Metallic a scalar
            emis.inputs["Color"].default_value = (v[0], v[1], v[2], 1.0)
        else:
            emis.inputs["Color"].default_value = (float(v), float(v), float(v), 1.0)
    prev = out.inputs["Surface"].links[0].from_socket
    nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])
    return (nt, emis, out, prev)


def restore_emit(state):
    if not state:
        return
    nt, emis, out, prev = state
    nt.links.new(prev, out.inputs["Surface"])
    nt.nodes.remove(emis)
